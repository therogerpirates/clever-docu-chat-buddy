import { useCallback, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileText, X } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface FileUploadZoneProps {
  onFileSelect: (file: File) => void;
  acceptedTypes: "pdf" | "csv" | "xlsx";
  selectedFile?: File;
}

export const FileUploadZone = ({ onFileSelect, acceptedTypes, selectedFile }: FileUploadZoneProps) => {
  const [isUploading, setIsUploading] = useState(false);
  const { toast } = useToast();

  const getAcceptString = () => {
    switch (acceptedTypes) {
      case "pdf": return ".pdf";
      case "csv": return ".csv";
      case "xlsx": return ".xlsx,.xls";
      default: return ".pdf,.csv,.xlsx,.xls";
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileSelect = (file: File) => {
    if (!file.name.match(/\.(csv|xlsx|xls|pdf)$/i)) {
      toast({
        title: "Invalid file type",
        description: "Please upload a CSV, Excel, or PDF file",
        variant: "destructive",
      });
      return;
    }
    onFileSelect(file);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const clearFile = () => {
    const fileInput = document.getElementById("file-input") as HTMLInputElement;
    if (fileInput) {
      fileInput.value = "";
    }
    onFileSelect(null as any);
  };

  return (
    <div className="space-y-4">
      {selectedFile ? (
        <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-green-600 dark:text-green-400" />
              <div>
                <p className="font-medium text-green-800 dark:text-green-200">{selectedFile.name}</p>
                <p className="text-sm text-green-600 dark:text-green-400">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFile}
              className="text-green-700 dark:text-green-300 hover:text-green-800 dark:hover:text-green-200 hover:bg-green-100 dark:hover:bg-green-900"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </Card>
      ) : (
        <Card
          className={`p-8 border-2 border-dashed border-border hover:border-primary transition-colors cursor-pointer ${
            isUploading ? "opacity-50 cursor-not-allowed" : ""
          }`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <div className="text-center">
            <Upload className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">
              {isUploading ? "Uploading..." : `Upload ${acceptedTypes.toUpperCase()} File`}
            </h3>
            <p className="text-muted-foreground mb-4">
              Drag and drop your file here, or click to browse
            </p>
            
            <input
              id="file-input"
              type="file"
              accept={getAcceptString()}
              onChange={handleFileInput}
              className="hidden"
              disabled={isUploading}
            />
            <Button
              type="button"
              variant="outline"
              onClick={() => document.getElementById("file-input")?.click()}
              className="border-primary/30 text-primary hover:bg-primary/10"
              disabled={isUploading}
            >
              Choose File
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};
