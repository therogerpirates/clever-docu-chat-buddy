import { useState } from "react";
import { uploadFile } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { NavigationHeader } from "@/components/NavigationHeader";
import { FileUploadZone } from "@/components/FileUploadZone";
import { Upload as UploadIcon, FileText, Database, Globe, CheckCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface FileUpload {
  file?: File;
  url?: string;
  type: "pdf" | "csv" | "xlsx" | "url";
  description: string;
  ragType?: "numerical" | "semantic";
}

const Upload = () => {
  const [uploadData, setUploadData] = useState<FileUpload>({
    type: "pdf",
    description: "",
  });
  const [isUploading, setIsUploading] = useState(false);
  const { toast } = useToast();

  const handleFileSelect = (file: File) => {
    const extension = file.name.split('.').pop()?.toLowerCase();
    let detectedType: "pdf" | "csv" | "xlsx" = "pdf";
    
    if (extension === "csv") detectedType = "csv";
    else if (extension === "xlsx" || extension === "xls") detectedType = "xlsx";
    
    setUploadData(prev => ({
      ...prev,
      file,
      type: detectedType,
      // Set ragType based on file type
      ragType: detectedType === "pdf" ? "semantic" : 
               (detectedType === "csv" || detectedType === "xlsx") ? "semantic" : undefined
    }));
  };

  const handleUpload = async () => {
    console.log('Starting file upload...');
    
    if (uploadData.type === "url" && !uploadData.url) {
      const errorMsg = "Please enter a URL";
      console.error(errorMsg);
      toast({
        title: "Error",
        description: errorMsg,
        variant: "destructive"
      });
      return;
    }
    
    if (uploadData.type !== "url" && !uploadData.file) {
      const errorMsg = "Please select a file";
      console.error(errorMsg);
      toast({
        title: "Error", 
        description: errorMsg,
        variant: "destructive"
      });
      return;
    }

    if (!uploadData.description.trim()) {
      const errorMsg = "Please provide a description";
      console.error(errorMsg);
      toast({
        title: "Error",
        description: errorMsg,
        variant: "destructive"
      });
      return;
    }

    setIsUploading(true);

    try {
      const formData = new FormData();
      
      if (uploadData.file) {
        console.log('Appending file to form data:', {
          name: uploadData.file.name,
          size: uploadData.file.size,
          type: uploadData.file.type
        });
        formData.append('file', uploadData.file);
      } else if (uploadData.url) {
        console.log('Appending URL to form data:', uploadData.url);
        formData.append('url', uploadData.url);
      }
      
      console.log('Appending description:', uploadData.description);
      formData.append('description', uploadData.description);
      
      if (uploadData.ragType) {
        console.log('Appending RAG type:', uploadData.ragType);
        formData.append('rag_type', uploadData.ragType);
      }

      // Log form data entries (won't show file content)
      for (let [key, value] of formData.entries()) {
        console.log(`FormData - ${key}:`, value);
      }

      console.log('Sending file upload request...');
      const responseData = await uploadFile(formData);
      console.log('Upload successful:', responseData);

      console.log('Upload successful:', responseData);

      toast({
        title: "Success!",
        description: `${uploadData.type.toUpperCase()} has been uploaded and is being processed.`,
      });
      
      // Reset form
      setUploadData({
        type: "pdf",
        description: "",
        file: undefined,
        url: undefined,
        ragType: undefined
      });
      
    } catch (error) {
      console.error('Upload error:', error);
      const errorMessage = error instanceof Error ? error.message : "Failed to upload file. Please try again.";
      
      toast({
        title: "Upload Failed",
        description: errorMessage,
        variant: "destructive"
      });
    } finally {
      setIsUploading(false);
    }
  };

  const isDataFile = uploadData.type === "csv" || uploadData.type === "xlsx";

  return (
    <div className="min-h-screen bg-background">
      <NavigationHeader />
      
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-foreground mb-2">Upload Documents</h1>
            <p className="text-muted-foreground">Add new data sources to your knowledge base</p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UploadIcon className="w-5 h-5 text-primary" />
                Document Upload
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* File Type Selection */}
              <div>
                <Label className="text-sm font-medium text-foreground mb-3 block">
                  What type of data source are you uploading?
                </Label>
                <RadioGroup
                  value={uploadData.type}
                  onValueChange={(value: "pdf" | "csv" | "xlsx" | "url") => 
                    setUploadData(prev => ({ ...prev, type: value, file: undefined, url: undefined }))
                  }
                  className="grid grid-cols-2 gap-4"
                >
                  <div className="flex items-center space-x-2 p-3 border border-border rounded-lg hover:bg-accent">
                    <RadioGroupItem value="pdf" id="pdf" />
                    <Label htmlFor="pdf" className="flex items-center gap-2 cursor-pointer">
                      <FileText className="w-4 h-4 text-red-500" />
                      PDF Document
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 p-3 border border-border rounded-lg hover:bg-accent">
                    <RadioGroupItem value="csv" id="csv" />
                    <Label htmlFor="csv" className="flex items-center gap-2 cursor-pointer">
                      <Database className="w-4 h-4 text-green-500" />
                      CSV File
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 p-3 border border-border rounded-lg hover:bg-accent">
                    <RadioGroupItem value="xlsx" id="xlsx" />
                    <Label htmlFor="xlsx" className="flex items-center gap-2 cursor-pointer">
                      <Database className="w-4 h-4 text-blue-500" />
                      Excel File
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 p-3 border border-border rounded-lg hover:bg-accent">
                    <RadioGroupItem value="url" id="url" />
                    <Label htmlFor="url" className="flex items-center gap-2 cursor-pointer">
                      <Globe className="w-4 h-4 text-purple-500" />
                      Website URL
                    </Label>
                  </div>
                </RadioGroup>
              </div>

              {/* File Upload or URL Input */}
              {uploadData.type === "url" ? (
                <div>
                  <Label htmlFor="url-input" className="text-sm font-medium text-foreground">
                    Website URL
                  </Label>
                  <Input
                    id="url-input"
                    type="url"
                    placeholder="https://example.com"
                    value={uploadData.url || ""}
                    onChange={(e) => setUploadData(prev => ({ ...prev, url: e.target.value }))}
                    className="mt-1"
                  />
                </div>
              ) : (
                <FileUploadZone
                  onFileSelect={handleFileSelect}
                  acceptedTypes={uploadData.type}
                  selectedFile={uploadData.file}
                />
              )}

              {/* RAG Type Selection for Data Files */}
              {isDataFile && (
                <div className="p-4 bg-primary/10 border border-primary/20 rounded-lg">
                  <Label className="text-sm font-medium text-foreground mb-3 block">
                    How should this data be processed?
                  </Label>
                  <RadioGroup
                    value={uploadData.ragType}
                    onValueChange={(value: "numerical" | "semantic") => 
                      setUploadData(prev => ({ ...prev, ragType: value }))
                    }
                    className="space-y-2"
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="numerical" id="numerical" />
                      <Label htmlFor="numerical" className="cursor-pointer">
                        <div>
                          <div className="font-medium">Numerical Data (SQL RAG)</div>
                          <div className="text-sm text-muted-foreground">For structured data with numbers, dates, and categorical values</div>
                        </div>
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="semantic" id="semantic" />
                      <Label htmlFor="semantic" className="cursor-pointer">
                        <div>
                          <div className="font-medium">Text Data (Semantic RAG)</div>
                          <div className="text-sm text-muted-foreground">For documents with descriptive text content</div>
                        </div>
                      </Label>
                    </div>
                  </RadioGroup>
                </div>
              )}

              {/* Description */}
              <div>
                <Label htmlFor="description" className="text-sm font-medium text-foreground">
                  Description
                </Label>
                <Textarea
                  id="description"
                  placeholder="Describe the content and purpose of this data source..."
                  value={uploadData.description}
                  onChange={(e) => setUploadData(prev => ({ ...prev, description: e.target.value }))}
                  className="mt-1"
                  rows={3}
                />
              </div>

              {/* Upload Button */}
              <Button 
                onClick={handleUpload}
                disabled={isUploading}
                className="w-full bg-primary hover:bg-primary/90"
                size="lg"
              >
                {isUploading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                    Processing...
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <UploadIcon className="w-4 h-4" />
                    Upload & Process
                  </div>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Upload;
