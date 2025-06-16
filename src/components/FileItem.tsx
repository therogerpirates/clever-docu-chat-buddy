
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  FileText, 
  Database, 
  Globe, 
  Trash2, 
  RefreshCw, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  Download,
  Eye
} from "lucide-react";

interface FileData {
  id: string;
  name: string;
  type: "pdf" | "csv" | "xlsx" | "url";
  description: string;
  ragType?: "numerical" | "semantic";
  uploadDate: Date;
  status: "processing" | "ready" | "error";
  size?: string;
  url?: string;
}

interface FileItemProps {
  file: FileData;
  onDelete: (fileId: string) => void;
  onReupload: (fileId: string) => void;
  onStatusChange?: (fileId: string, status: "processing" | "ready" | "error") => void;
}

export const FileItem = ({ file, onDelete, onReupload, onStatusChange }: FileItemProps) => {
  // Handle reupload with status tracking
  const handleReupload = async () => {
    try {
      // Update status to processing
      onStatusChange?.(file.id, 'processing');
      
      // Call the reupload function
      await onReupload(file.id);
      
      // Update status to ready on success
      onStatusChange?.(file.id, 'ready');
    } catch (error) {
      console.error('Error reuploading file:', error);
      // Update status to error on failure
      onStatusChange?.(file.id, 'error');
    }
  };
  const getIcon = () => {
    switch (file.type) {
      case "pdf": return <FileText className="w-5 h-5 text-red-500" />;
      case "csv": return <Database className="w-5 h-5 text-green-500" />;
      case "xlsx": return <Database className="w-5 h-5 text-blue-500" />;
      case "url": return <Globe className="w-5 h-5 text-purple-500" />;
      default: return <FileText className="w-5 h-5 text-muted-foreground" />;
    }
  };

  const getStatusIcon = () => {
    switch (file.status) {
      case "ready": return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case "processing": return <Clock className="w-4 h-4 text-yellow-500 animate-pulse" />;
      case "error": return <AlertCircle className="w-4 h-4 text-red-500" />;
    }
  };

  const getStatusColor = () => {
    switch (file.status) {
      case "ready": return "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800";
      case "processing": return "text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-950/30 border-yellow-200 dark:border-yellow-800";
      case "error": return "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800";
    }
  };

  return (
    <Card className={`transition-all hover:shadow-md ${getStatusColor()}`}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4 flex-1 min-w-0">
            <div className="flex-shrink-0">
              {getIcon()}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-semibold text-foreground truncate">{file.name}</h3>
                {getStatusIcon()}
              </div>
              
              <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                {file.description}
              </p>
              
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <Badge variant="outline" className="text-xs">
                  {file.type.toUpperCase()}
                </Badge>
                
                {file.ragType && (
                  <Badge variant="secondary" className="text-xs">
                    {file.ragType === "numerical" ? "SQL RAG" : "Semantic RAG"}
                  </Badge>
                )}
                
                <Badge 
                  variant={file.status === "ready" ? "default" : file.status === "error" ? "destructive" : "secondary"}
                  className="text-xs"
                >
                  {file.status.charAt(0).toUpperCase() + file.status.slice(1)}
                </Badge>
                
                {file.size && (
                  <span className="text-xs text-muted-foreground">{file.size}</span>
                )}
              </div>
              
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <span>Uploaded: {file.uploadDate.toLocaleDateString()}</span>
                {file.url && (
                  <a 
                    href={file.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-primary hover:text-primary/80 underline"
                  >
                    View Source
                  </a>
                )}
              </div>
            </div>
          </div>
          
          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-shrink-0 ml-4">
            {file.status === "ready" && (
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                <Eye className="w-4 h-4" />
              </Button>
            )}
            
            {file.type !== "url" && file.status === "ready" && (
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                <Download className="w-4 h-4" />
              </Button>
            )}
            
            {file.status === "error" && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => onReupload(file.id)}
                className="text-yellow-600 dark:text-yellow-400 hover:text-yellow-700 dark:hover:text-yellow-300"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            )}
            
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => onDelete(file.id)}
              className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
