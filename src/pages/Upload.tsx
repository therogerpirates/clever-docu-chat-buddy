import { useState } from "react";
import { uploadFile, uploadWebsite } from "@/lib/api";
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
    console.log('Starting upload process...');
    
    // Validate inputs
    if (uploadData.type === "url") {
      if (!uploadData.url?.trim()) {
        const errorMsg = "Please enter a valid URL";
        console.error(errorMsg);
        toast({
          title: "Error",
          description: errorMsg,
          variant: "destructive"
        });
        return;
      }
      
      // Basic URL validation
      try {
        new URL(uploadData.url);
      } catch (e) {
        const errorMsg = "Please enter a valid URL (include http:// or https://)";
        console.error(errorMsg);
        toast({
          title: "Error",
          description: errorMsg,
          variant: "destructive"
        });
        return;
      }
    } else if (!uploadData.file) {
      const errorMsg = "Please select a file to upload";
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
      if (uploadData.type === "url" && uploadData.url) {
        // Handle website URL upload
        console.log('Processing URL:', uploadData.url);
        // Ensure URL has a protocol
        const processedUrl = uploadData.url.startsWith('http') 
          ? uploadData.url 
          : `https://${uploadData.url}`;
        
        console.log('Sending website upload request...');
        const responseData = await uploadWebsite(
          processedUrl,
          uploadData.description
        );
        console.log('Website upload successful:', responseData);
      } else if (uploadData.file) {
        // Handle file upload
        const formData = new FormData();
        formData.append('description', uploadData.description);
        formData.append('rag_type', uploadData.ragType || 'semantic');
        formData.append('file', uploadData.file);
        
        console.log('Processing file:', {
          name: uploadData.file.name,
          size: uploadData.file.size,
          type: uploadData.file.type
        });
        
        console.log('Sending file upload request...');
        const responseData = await uploadFile(formData);
        console.log('File upload successful:', responseData);
      } else {
        throw new Error('No file or URL provided');
      }

      const successMessage = uploadData.type === "url"
        ? "Website is being processed. You'll be notified when it's ready."
        : `${uploadData.type.toUpperCase()} has been uploaded and is being processed.`;

      toast({
        title: "Success!",
        description: successMessage,
      });
      
      // Reset form
      setUploadData({
        type: "pdf",
        description: "",
        file: undefined,
        url: undefined,
        ragType: "semantic"
      });
      
    } catch (error: unknown) {
      console.error('Upload error:', error);
      
      // Helper function to safely extract error message
      const extractErrorMessage = (err: unknown): string => {
        if (typeof err === 'string') return err;
        if (err instanceof Error) return err.message;
        if (err && typeof err === 'object') {
          // Handle Axios error response
          if ('response' in err && err.response) {
            const response = (err as any).response;
            if (response.data) {
              if (typeof response.data === 'string') return response.data;
              if (typeof response.data.detail === 'string') return response.data.detail;
              if (typeof response.data.message === 'string') return response.data.message;
            }
            return response.statusText || 'Unknown error occurred';
          }
          // Handle other object-like errors
          if ('message' in err && typeof (err as any).message === 'string') {
            return (err as any).message;
          }
          // Try to stringify if possible
          try {
            return JSON.stringify(err);
          } catch (e) {
            return 'Unknown error occurred';
          }
        }
        return 'An unknown error occurred';
      };
      
      const errorMessage = extractErrorMessage(error).replace(/["']/g, '').trim();
      
      // Log detailed error information for debugging
      const errorDetails: Record<string, unknown> = { message: errorMessage };
      
      if (error && typeof error === 'object') {
        if ('message' in error) errorDetails.message = (error as any).message;
        if ('status' in error) errorDetails.status = (error as any).status;
        if ('data' in error) errorDetails.data = (error as any).data;
        if ('stack' in error) errorDetails.stack = (error as any).stack;
      }
      
      console.error('Upload error details:', errorDetails);
      
      toast({
        title: "Upload Failed",
        description: errorMessage || 'An unknown error occurred',
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
