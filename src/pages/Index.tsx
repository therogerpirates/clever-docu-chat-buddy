import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
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
      // Call the backend API
      const apiUrl = 'http://localhost:8000/api/chat';
      console.log('Sending request to:', apiUrl);
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        mode: 'cors',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          messages: [...messages, userMessage].map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          system_prompt: SYSTEM_PROMPT,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to get response from server');
      }

      const data = await response.json();
      
      // Add AI response to messages
      console.log('API Response:', data); // Log the full response for debugging
      
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
      if (error instanceof Error) {
        errorMessage = error.message;
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
          errorMessage = 'Failed to connect to the server. Please check if the backend is running and accessible.';
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

  return (
    <div className="min-h-screen bg-gradient-main">
      <NavigationHeader />
      
      <div className="container mx-auto px-4 py-6">
        <div className="max-w-4xl mx-auto h-[calc(100vh-8rem)]">
          {/* Chat Interface */}
          <Card className="h-full flex flex-col border-border shadow-lg">
            {/* Chat Header */}
            <div className="p-4 border-b border-border bg-muted/30 rounded-t-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-primary" />
                  <h2 className="font-semibold text-foreground">Document Assistant</h2>
                </div>
                <div className="text-sm text-muted-foreground">
                  Chat with AI Assistant
                </div>
              </div>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                {isLoading && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Bot className="w-4 h-4 animate-pulse" />
                    <span className="text-sm">AI is thinking...</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="p-4 border-t border-border bg-muted/30">
              <div className="flex gap-2">
                <Input
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about your documents..."
                  disabled={isLoading}
                  className="flex-1"
                  data-lov-id="chat-input"
                />
                <Button 
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isLoading}
                  className="bg-primary hover:bg-primary/90"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Index;
