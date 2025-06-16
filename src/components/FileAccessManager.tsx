
import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Shield, Users, Save, X } from "lucide-react";
import { toast } from "@/components/ui/use-toast";
import { apiRequest } from "@/lib/api";

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

interface FileAccessManagerProps {
  fileId: string | number;
  fileName: string;
  currentRestrictedUsers: string[];
  isAdmin: boolean;
}

const FileAccessManager: React.FC<FileAccessManagerProps> = ({
  fileId,
  fileName,
  currentRestrictedUsers,
  isAdmin
}) => {
  const [users, setUsers] = useState<User[]>([]);
  const [restrictedUserIds, setRestrictedUserIds] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  // Fetch all users when dialog opens
  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const usersData = await apiRequest('/api/users');
      setUsers(usersData);
      
      // Get current restrictions
      const restrictionsData = await apiRequest(`/api/files/${fileId}/restrictions`);
      setRestrictedUserIds(restrictionsData.restricted_user_ids || []);
    } catch (error) {
      console.error('Error fetching users:', error);
      toast({
        title: "Error",
        description: "Failed to load users",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUserToggle = (userId: number, isRestricted: boolean) => {
    if (isRestricted) {
      setRestrictedUserIds(prev => [...prev, userId]);
    } else {
      setRestrictedUserIds(prev => prev.filter(id => id !== userId));
    }
  };

  const handleSaveRestrictions = async () => {
    try {
      setIsLoading(true);
      await apiRequest(`/api/files/${fileId}/restrictions`, {
        method: 'POST',
        body: JSON.stringify({ user_ids: restrictedUserIds })
      });
      
      toast({
        title: "Success",
        description: "File access restrictions updated successfully",
      });
      
      setIsOpen(false);
    } catch (error) {
      console.error('Error updating restrictions:', error);
      toast({
        title: "Error",
        description: "Failed to update file restrictions",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchUsers();
    }
  }, [isOpen]);

  if (!isAdmin) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Shield className="w-4 h-4 mr-2" />
          Manage Access
          {currentRestrictedUsers.length > 0 && (
            <Badge variant="secondary" className="ml-2">
              {currentRestrictedUsers.length} restricted
            </Badge>
          )}
        </Button>
      </DialogTrigger>
      
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            File Access Control
          </DialogTitle>
          <p className="text-sm text-muted-foreground">
            Manage who can access "{fileName}"
          </p>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            <Users className="w-4 h-4 inline mr-1" />
            Select users to restrict access to this file:
          </div>
          
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="space-y-3 max-h-60 overflow-y-auto">
              {users
                .filter(user => user.role !== 'admin') // Admins can't be restricted
                .map(user => (
                  <div key={user.id} className="flex items-center space-x-3 p-2 rounded-lg hover:bg-accent">
                    <Checkbox
                      id={`user-${user.id}`}
                      checked={restrictedUserIds.includes(user.id)}
                      onCheckedChange={(checked) => handleUserToggle(user.id, checked as boolean)}
                    />
                    <div className="flex-1">
                      <label htmlFor={`user-${user.id}`} className="flex items-center justify-between cursor-pointer">
                        <div>
                          <div className="font-medium">{user.username}</div>
                          <div className="text-sm text-muted-foreground">{user.email}</div>
                        </div>
                        <Badge variant={user.role === 'manager' ? 'default' : 'secondary'}>
                          {user.role}
                        </Badge>
                      </label>
                    </div>
                  </div>
                ))}
            </div>
          )}
          
          <div className="flex gap-2 pt-4 border-t">
            <Button 
              onClick={handleSaveRestrictions} 
              disabled={isLoading}
              className="flex-1"
            >
              <Save className="w-4 h-4 mr-2" />
              Save Changes
            </Button>
            <Button 
              variant="outline" 
              onClick={() => setIsOpen(false)}
              disabled={isLoading}
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default FileAccessManager;
