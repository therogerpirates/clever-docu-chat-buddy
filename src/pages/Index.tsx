import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiRequest } from "@/lib/api";
import { Bot, User, Send, Loader2 } from "lucide-react";
import { ChatMessage, type ChatMessageType } from "@/components/ChatMessage";
import { useToast } from "@/components/ui/use-toast";
import { NavigationHeader } from "@/components/NavigationHeader";

// System prompt to guide the AI's behavior
const SYSTEM_PROMPT = `You are a helpful AI assistant that provides accurate and concise responses 
based on the provided context. If you don't know the answer, say so instead of making something up.`;

// Mock data for all available files
const allDataSources = [
  { id: "1", name: "Product Manual 2024.pdf", type: "pdf", status: "ready" },
  { id: "2", name: "Sales Data Q4.xlsx", type: "xlsx", status: "ready" },
  { id: "3", name: "Customer Feedback.csv", type: "csv", status: "ready" },
  { id: "4", name: "Company Website", type: "url", status: "ready" },
  { id: "5", name: "Financial Report 2023.pdf", type: "pdf", status: "ready" }
];

const Index = () => {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle sending a message
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      content: inputMessage,
      role: 'user',
      timestamp: new Date(),
    };

    // Add user message to chat
    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);

    try {
      // Call the backend API using apiRequest which handles authentication
      const data = await apiRequest('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          messages: [...messages, userMessage].map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          system_prompt: SYSTEM_PROMPT,
        }),
      });
      
      // Add AI response to messages
      console.log('API Response:', data); // Log the full response for debugging
      
      if (!data) {
        throw new Error('No response data received from server');
      }
      
      const botMessage: ChatMessageType = {
        id: `ai-${Date.now()}`,
        content: data.response || 'No response from the assistant',
        role: 'assistant',
        timestamp: new Date(),
        sources: data.sources || []
      };
      
      setMessages(prev => [...prev, botMessage]);
      
      // Log any errors from the response
      if (data.error) {
        console.error('Error from API:', data.error);
        toast({
          title: "API Error",
          description: data.error,
          variant: "destructive",
        });
      }
      
    } catch (error) {
      console.error('Error sending message:', error);
      
      let errorMessage = 'Failed to send message';
      let errorDetails = '';
      
      if (error instanceof Error) {
        console.error('Error details:', {
          name: error.name,
          message: error.message,
          stack: error.stack,
          // @ts-ignore - Accessing non-standard properties
          status: error.status,
          // @ts-ignore - Accessing non-standard properties
          data: error.data
        });
        
        errorMessage = error.message || 'An unknown error occurred';
        
        // Handle network errors
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
          errorMessage = 'Failed to connect to the server. Please check if the backend is running and accessible.';
        } 
        // Handle API errors with status codes
        // @ts-ignore - Accessing non-standard properties
        else if (error.status) {
          // @ts-ignore - Accessing non-standard properties
          errorDetails = `Status: ${error.status} - ${error.data?.error || error.data?.message || 'Unknown error'}`;
        }
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="min-h-screen bg-background">
      <NavigationHeader />
      
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        {!hasMessages ? (
          // Centered initial state (like ChatGPT)
          <div className="flex-1 flex flex-col items-center justify-center px-4">
            <div className="w-full max-w-2xl space-y-6 animate-fade-in">
              <div className="text-center space-y-2">
                <Bot className="w-12 h-12 mx-auto text-primary animate-pulse" />
                <h1 className="text-2xl font-semibold text-foreground">
                  Document Assistant
                </h1>
                <p className="text-muted-foreground">
                  Ask me anything about your documents
                </p>
              </div>
              
              {/* Centered Input */}
              <div className="relative">
                <Input
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Message Document Assistant..."
                  disabled={isLoading}
                  className="w-full pr-12 py-3 text-base border-2 border-border focus:border-primary transition-all duration-200 shadow-sm hover:shadow-md"
                  data-lov-id="chat-input"
                />
                <Button 
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isLoading}
                  size="sm"
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 p-0 bg-primary hover:bg-primary/90 transition-all duration-200"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </div>
        ) : (
          // Chat mode (like ChatGPT with messages)
          <>
            {/* Messages Area */}
            <div className="flex-1 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="max-w-3xl mx-auto px-4 py-6 space-y-6 animate-fade-in">
                  {messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
                  ))}
                  {isLoading && (
                    <div className="flex items-start gap-3 animate-fade-in">
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                        <Bot className="w-4 h-4 text-primary animate-pulse" />
                      </div>
                      <div className="bg-card border border-border rounded-lg p-3">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>
            </div>

            {/* Bottom Input */}
            <div className="border-t border-border bg-background/80 backdrop-blur-sm">
              <div className="max-w-3xl mx-auto p-4">
                <div className="relative">
                  <Input
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Message Document Assistant..."
                    disabled={isLoading}
                    className="w-full pr-12 py-3 text-base border-2 border-border focus:border-primary transition-all duration-200 shadow-sm hover:shadow-md"
                    data-lov-id="chat-input"
                  />
                  <Button 
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim() || isLoading}
                    size="sm"
                    className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 p-0 bg-primary hover:bg-primary/90 transition-all duration-200"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Index;
