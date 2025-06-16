
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Bot, User } from "lucide-react";

export interface ChatMessageType {
  id: string;
  content: string;
  role: "user" | "assistant" | "system";
  timestamp: Date;
  sources?: string[];
}

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  const isBot = message.role === "assistant" || message.role === "system";

  return (
    <div className={`flex gap-3 ${isBot ? "justify-start" : "justify-end"}`}>
      {isBot && (
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 text-primary" />
        </div>
      )}
      
      <div className={`max-w-[80%] ${!isBot ? "flex-row-reverse" : ""}`}>
        <Card className={`p-3 ${isBot ? "bg-card border-border" : "bg-primary text-primary-foreground border-primary"}`}>
          <p className="text-sm leading-relaxed">{message.content}</p>
          
          {message.sources && message.sources.length > 0 && (
            <div className="mt-2 pt-2 border-t border-border/20">
              <p className={`text-xs ${isBot ? "text-muted-foreground" : "text-primary-foreground/70"} mb-1`}>Sources:</p>
              <div className="flex flex-wrap gap-1">
                {message.sources.map((source, index) => (
                  <Badge key={index} variant={isBot ? "outline" : "secondary"} className="text-xs">
                    {source}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </Card>
        
        <p className={`text-xs text-muted-foreground mt-1 ${!isBot ? "text-right" : ""}`}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>

      {!isBot && (
        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-muted-foreground" />
        </div>
      )}
    </div>
  );
};
