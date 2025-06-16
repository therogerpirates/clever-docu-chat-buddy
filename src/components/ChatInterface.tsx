import { useState, useRef, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, User, Send, Loader2, FileText, FileSpreadsheet, File } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  sources?: string[];
  model?: string;
}

interface ChatResponse {
  response: string;
  model: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
  sources?: string[];
}

export const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // System prompt to guide the AI's behavior
  const systemPrompt = `You are a helpful AI assistant that provides accurate and concise responses based on the provided context.
  If the context is provided, use it to answer the question. If you don't know the answer, say so instead of making something up.`;

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle sending a message
  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      console.log("Sending message to backend:", userMessage);
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [...messages, { role: "user", content: userMessage }],
          system_prompt: systemPrompt,
          use_rag: true,
          rag_limit: 3,
          min_score: 0.5
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error("Error response:", errorData);
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Received response from backend:", data);

      if (!data.response) {
        throw new Error("No response received from the AI");
      }

      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: data.response, 
        sources: data.sources || [],
        model: data.model
      }]);
    } catch (error) {
      console.error("Chat error:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to get response from AI",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto h-[600px] flex flex-col">
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div key={index} className="space-y-2">
              <div
                className={`flex items-start gap-3 ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {message.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-primary" />
                  </div>
                )}
                <div className="flex-1">
                  <div
                    className={`inline-block max-w-[90%] rounded-lg p-3 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                  {message.role === "assistant" && message.sources && message.sources.length > 0 && (
                    <div className="mt-2 space-y-1">
                      <p className="text-xs font-medium text-muted-foreground">Sources:</p>
                      <div className="flex flex-wrap gap-2">
                        {message.sources.map((source, idx) => {
                          // Extract filename and source info
                          const match = source.match(/(.+?)\s*\((.+?)(?:,\s*(.+?))?\)/);
                          const filename = match ? match[1] : source;
                          const sourceInfo = match ? match[2] : '';
                          
                          // Determine file type for icon
                          const fileExt = filename.split('.').pop()?.toLowerCase();
                          let fileIcon = <File className="w-3 h-3" />;
                          
                          if (fileExt === 'pdf') {
                            fileIcon = <FileText className="w-3 h-3" />;
                          } else if (['xlsx', 'xls', 'csv'].includes(fileExt || '')) {
                            fileIcon = <FileSpreadsheet className="w-3 h-3" />;
                          }
                          
                          return (
                            <div 
                              key={idx} 
                              className="flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-muted/50 text-muted-foreground"
                              title={source}
                            >
                              {fileIcon}
                              <span className="truncate max-w-[120px]">
                                {filename}
                              </span>
                              {sourceInfo && (
                                <span className="text-muted-foreground/70">
                                  ({sourceInfo})
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
                {message.role === "user" && (
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="w-5 h-5 text-primary" />
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="w-5 h-5 text-primary" />
              </div>
              <div className="bg-muted rounded-lg p-3">
                <p>Thinking...</p>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <form 
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }} 
        className="p-4 border-t"
      >
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </form>
    </Card>
  );
}; 