
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { NavigationHeader } from "@/components/NavigationHeader";
import FileItem from "@/components/FileItem";
import { Search, Upload, Database, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "@/components/ui/use-toast";
import { fetchFiles as apiFetchFiles, deleteFile as apiDeleteFile, reprocessFile as apiReprocessFile } from "@/lib/api";

interface FileData {
  id: string | number;
  file_uuid: string;
  name: string;
  type: "pdf" | "csv" | "xlsx" | "url";
  description: string;
  rag_type?: "sql" | "semantic";
  upload_date: string;
  status: "processing" | "ready" | "error";
  size?: string;
  url?: string;
  metadata?: Record<string, any>;
  uploaded_by?: string;
  can_edit?: boolean;
  is_restricted?: boolean;
  restricted_users?: string[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const Files = () => {
  const [files, setFiles] = useState<FileData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | "ready" | "processing" | "error">("all");

  // Fetch files from the backend
  const fetchFiles = async () => {
    setIsLoading(true);
    try {
      const data = await apiFetchFiles();
      setFiles(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching files:', error);
      // Extract error message from different error formats
      let errorMessage = 'Failed to load files';
      
      if (error instanceof Error) {
        // If error has a data property with error details
        if ((error as any).data) {
          const errorData = (error as any).data;
          if (errorData.details) {
            errorMessage = errorData.details;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          } else if (errorData.message) {
            errorMessage = errorData.message;
          } else if (typeof errorData === 'string') {
            errorMessage = errorData;
          } else if (typeof errorData === 'object') {
            errorMessage = JSON.stringify(errorData);
          }
        } else {
          errorMessage = error.message || errorMessage;
        }
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else if (error && typeof error === 'object') {
        errorMessage = JSON.stringify(error);
      }
      
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Delete a file
  const handleDelete = async (fileId: string | number) => {
    if (!window.confirm('Are you sure you want to delete this file? This action cannot be undone.')) {
      return;
    }
    
    try {
      await apiDeleteFile(fileId);
      
      // Refresh the files list
      await fetchFiles();
      
      toast({
        title: "Success",
        description: "File deleted successfully",
      });
    } catch (error) {
      console.error('Error deleting file:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete file';
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  // Handle file status change
  const handleStatusChange = (fileId: string | number, status: "processing" | "ready" | "error") => {
    setFiles(prevFiles => 
      prevFiles.map(file => 
        file.id === fileId ? { ...file, status } : file
      )
    );
  };

  // Re-process a file
  const handleReupload = async (fileId: string | number) => {
    try {
      // Optimistically update the UI to show processing status
      handleStatusChange(fileId, 'processing');
      
      await apiReprocessFile(fileId);
      
      toast({
        title: "Reprocessing Started",
        description: "The file is being reprocessed. Its status will update automatically.",
      });

      // Refresh the file list to get the latest statuses
      setTimeout(fetchFiles, 3000); // Give backend some time to start processing

    } catch (error) {
      console.error('Error reprocessing file:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to reprocess file';
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
      // Revert status on error by refetching all files
      fetchFiles();
    }
  };

  // Load files on component mount
  useEffect(() => {
    fetchFiles();
  }, []);

  const filteredFiles = files.filter(file => {
    const matchesSearch = file.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (file.description || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === "all" || file.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const getStatusCounts = () => {
    const counts = files.reduce((acc, file) => {
      acc[file.status] = (acc[file.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    return {
      total: files.length,
      ready: counts.ready || 0,
      processing: counts.processing || 0,
      error: counts.error || 0
    };
  };

  const statusCounts = getStatusCounts();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <NavigationHeader />
      
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold text-foreground mb-2">File Management</h1>
              <p className="text-muted-foreground">Manage your uploaded documents and data sources</p>
            </div>
            <Link to="/upload">
              <Button className="bg-primary hover:bg-primary/90">
                <Upload className="w-4 h-4 mr-2" />
                Upload Files
              </Button>
            </Link>
          </div>

          {/* Status Overview */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Files</p>
                    <p className="text-2xl font-bold text-foreground">{statusCounts.total}</p>
                  </div>
                  <Database className="w-8 h-8 text-primary" />
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Ready</p>
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400">{statusCounts.ready}</p>
                  </div>
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Processing</p>
                    <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{statusCounts.processing}</p>
                  </div>
                  <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse"></div>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Errors</p>
                    <p className="text-2xl font-bold text-red-600 dark:text-red-400">{statusCounts.error}</p>
                  </div>
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Search and Filter */}
          <Card className="mb-6">
            <CardContent className="p-4">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Search files by name or description..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <div className="flex gap-2">
                  {["all", "ready", "processing", "error"].map((status) => (
                    <Button
                      key={status}
                      variant={filterStatus === status ? "default" : "outline"}
                      size="sm"
                      onClick={() => setFilterStatus(status as any)}
                    >
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </Button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Files List */}
        <div className="space-y-4">
          {filteredFiles.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <Database className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-muted-foreground mb-2">No files found</h3>
                <p className="text-muted-foreground">
                  {searchTerm || filterStatus !== 'all' 
                    ? 'No matching files found. Try adjusting your search or filter.'
                    : 'Upload your first file to get started.'}
                </p>
                <Link to="/upload" className="mt-4 inline-block">
                  <Button className="bg-primary hover:bg-primary/90">
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Files
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {filteredFiles.map((file) => {
                // Map the API response to the expected FileItem props
                const fileItemProps = {
                  id: String(file.id),
                  name: file.name,
                  type: file.type as "pdf" | "csv" | "xlsx" | "url",
                  description: file.description || '',
                  ragType: file.rag_type as "sql" | "semantic" | undefined,
                  uploadDate: new Date(file.upload_date),
                  status: file.status,
                  size: file.size,
                  url: file.url,
                  uploaded_by: file.uploaded_by,
                  can_edit: file.can_edit,
                  is_restricted: file.is_restricted,
                  restricted_users: file.restricted_users,
                };
                
                return (
                  <FileItem
                    key={file.id}
                    file={fileItemProps}
                    onDelete={() => handleDelete(file.id)}
                    onReupload={() => handleReupload(file.id)}
                    onStatusChange={(fileId, status) => handleStatusChange(fileId, status)}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Files;
