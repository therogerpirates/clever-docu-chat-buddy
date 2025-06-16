
import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileText, Database, Globe, MoreVertical, Trash2, RefreshCw, AlertCircle, CheckCircle, Clock } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { formatDistanceToNow } from "date-fns";
import { useAuth } from "@/contexts/AuthContext";
import FileAccessManager from "./FileAccessManager";

interface FileItemProps {
  file: {
    id: string;
    name: string;
    type: "pdf" | "csv" | "xlsx" | "url";
    description: string;
    ragType?: "numerical" | "semantic";
    uploadDate: Date;
    status: "processing" | "ready" | "error";
    size?: string;
    url?: string;
    uploaded_by?: string;
    can_edit?: boolean;
    is_restricted?: boolean;
    restricted_users?: string[];
  };
  onDelete: (fileId: string) => void;
  onReupload: (fileId: string) => void;
  onStatusChange: (fileId: string, status: "processing" | "ready" | "error") => void;
}

const FileItem: React.FC<FileItemProps> = ({ file, onDelete, onReupload, onStatusChange }) => {
  const { isAdmin } = useAuth();

  const getFileIcon = (type: string) => {
    switch (type) {
      case "pdf":
        return <FileText className="w-5 h-5 text-red-500" />;
      case "csv":
        return <Database className="w-5 h-5 text-green-500" />;
      case "xlsx":
        return <Database className="w-5 h-5 text-blue-500" />;
      case "url":
        return <Globe className="w-5 h-5 text-purple-500" />;
      default:
        return <FileText className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "ready":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "processing":
        return <Clock className="w-4 h-4 text-yellow-500 animate-pulse" />;
      case "error":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "ready":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
      case "processing":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
      case "error":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    }
  };

  const formatFileType = (type: string) => {
    switch (type) {
      case "pdf":
        return "PDF";
      case "csv":
        return "CSV";
      case "xlsx":
        return "Excel";
      case "url":
        return "Website";
      default:
        return type.toUpperCase();
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <div className="flex-shrink-0 mt-1">
              {getFileIcon(file.type)}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold text-foreground truncate" title={file.name}>
                  {file.name}
                </h3>
                {file.is_restricted && (
                  <Badge variant="destructive" className="text-xs">
                    Restricted
                  </Badge>
                )}
              </div>
              
              <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                {file.description}
              </p>
              
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="outline" className="text-xs">
                  {formatFileType(file.type)}
                </Badge>
                
                {file.ragType && (
                  <Badge variant="secondary" className="text-xs">
                    {file.ragType === "numerical" ? "SQL RAG" : "Semantic RAG"}
                  </Badge>
                )}
                
                <div className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${getStatusColor(file.status)}`}>
                  {getStatusIcon(file.status)}
                  {file.status.charAt(0).toUpperCase() + file.status.slice(1)}
                </div>
                
                {file.size && (
                  <span>{file.size}</span>
                )}
                
                <span>
                  {formatDistanceToNow(file.uploadDate, { addSuffix: true })}
                </span>
                
                {file.uploaded_by && (
                  <span>by {file.uploaded_by}</span>
                )}
              </div>

              {file.restricted_users && file.restricted_users.length > 0 && isAdmin && (
                <div className="mt-2 text-xs text-muted-foreground">
                  <span className="font-medium">Restricted users:</span> {file.restricted_users.join(", ")}
                </div>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {isAdmin && (
              <FileAccessManager
                fileId={file.id}
                fileName={file.name}
                currentRestrictedUsers={file.restricted_users || []}
                isAdmin={isAdmin}
              />
            )}
            
            {file.can_edit && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm">
                    <MoreVertical className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {file.status === "error" && (
                    <DropdownMenuItem onClick={() => onReupload(file.id)}>
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Retry Processing
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={() => onDelete(file.id)}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default FileItem;
