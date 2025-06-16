
import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText, Database, Globe, CheckCircle2, Clock, AlertCircle } from "lucide-react";

interface DataSource {
  id: string;
  name: string;
  type: "pdf" | "csv" | "xlsx" | "url";
  ragType?: "numerical" | "semantic";
  status: "ready" | "processing" | "error";
  description: string;
}

// Mock data - replace with actual data from your backend
const mockDataSources: DataSource[] = [
  {
    id: "1",
    name: "Product Manual 2024.pdf",
    type: "pdf",
    status: "ready",
    description: "Product documentation"
  },
  {
    id: "2",
    name: "Sales Data Q4.xlsx",
    type: "xlsx",
    ragType: "numerical",
    status: "ready",
    description: "Sales performance data"
  },
  {
    id: "3",
    name: "Customer Feedback.csv",
    type: "csv",
    ragType: "semantic",
    status: "processing",
    description: "Customer survey responses"
  },
  {
    id: "4",
    name: "Company Website",
    type: "url",
    status: "ready",
    description: "Main website content"
  },
  {
    id: "5",
    name: "Financial Report 2023.pdf",
    type: "pdf",
    status: "error",
    description: "Annual financial statements"
  }
];

interface DataSourceSelectorProps {
  selectedSources: string[];
  onSourcesChange: (sources: string[]) => void;
}

export const DataSourceSelector = ({ selectedSources, onSourcesChange }: DataSourceSelectorProps) => {
  const [dataSources] = useState<DataSource[]>(mockDataSources);

  const getIcon = (type: string) => {
    switch (type) {
      case "pdf": return <FileText className="w-4 h-4 text-red-500" />;
      case "csv": return <Database className="w-4 h-4 text-green-500" />;
      case "xlsx": return <Database className="w-4 h-4 text-blue-500" />;
      case "url": return <Globe className="w-4 h-4 text-purple-500" />;
      default: return <FileText className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "ready": return <CheckCircle2 className="w-3 h-3 text-green-500" />;
      case "processing": return <Clock className="w-3 h-3 text-yellow-500 animate-pulse" />;
      case "error": return <AlertCircle className="w-3 h-3 text-red-500" />;
      default: return null;
    }
  };

  const handleSourceToggle = (sourceId: string) => {
    const source = dataSources.find(s => s.id === sourceId);
    if (source?.status !== "ready") return; // Don't allow selection of non-ready sources

    if (selectedSources.includes(sourceId)) {
      onSourcesChange(selectedSources.filter(id => id !== sourceId));
    } else {
      onSourcesChange([...selectedSources, sourceId]);
    }
  };

  const selectAll = () => {
    const readySources = dataSources.filter(source => source.status === "ready").map(source => source.id);
    onSourcesChange(readySources);
  };

  const clearAll = () => {
    onSourcesChange([]);
  };

  const readySources = dataSources.filter(source => source.status === "ready");

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={selectAll}
          disabled={readySources.length === 0}
          className="text-xs"
        >
          Select All Ready
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={clearAll}
          disabled={selectedSources.length === 0}
          className="text-xs"
        >
          Clear All
        </Button>
      </div>

      {/* Selected Count */}
      {selectedSources.length > 0 && (
        <div className="text-xs text-slate-600">
          {selectedSources.length} source{selectedSources.length !== 1 ? "s" : ""} selected
        </div>
      )}

      {/* Data Sources List */}
      <div className="space-y-2">
        {dataSources.map((source) => {
          const isSelected = selectedSources.includes(source.id);
          const isDisabled = source.status !== "ready";
          
          return (
            <Card 
              key={source.id}
              className={`p-3 cursor-pointer transition-all ${
                isSelected ? "ring-2 ring-blue-500 bg-blue-50" : "hover:bg-slate-50"
              } ${isDisabled ? "opacity-50 cursor-not-allowed" : ""}`}
              onClick={() => !isDisabled && handleSourceToggle(source.id)}
            >
              <div className="flex items-start gap-3">
                <Checkbox
                  checked={isSelected}
                  disabled={isDisabled}
                  onChange={() => {}} // Handled by card click
                />
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {getIcon(source.type)}
                    <span className="text-sm font-medium text-slate-700 truncate">
                      {source.name}
                    </span>
                    {getStatusIcon(source.status)}
                  </div>
                  
                  <p className="text-xs text-slate-500 mb-2 line-clamp-2">
                    {source.description}
                  </p>
                  
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {source.type.toUpperCase()}
                    </Badge>
                    {source.ragType && (
                      <Badge variant="secondary" className="text-xs">
                        {source.ragType}
                      </Badge>
                    )}
                    <Badge 
                      variant={source.status === "ready" ? "default" : source.status === "error" ? "destructive" : "secondary"}
                      className="text-xs"
                    >
                      {source.status}
                    </Badge>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {dataSources.length === 0 && (
        <div className="text-center py-8 text-slate-500">
          <Database className="w-8 h-8 mx-auto mb-2 text-slate-300" />
          <p className="text-sm">No data sources available</p>
          <p className="text-xs">Upload some files to get started</p>
        </div>
      )}
    </div>
  );
};
