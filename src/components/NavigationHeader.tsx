
import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { MessageSquare, Upload, Files, Bot } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

export const NavigationHeader = () => {
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Chat", icon: MessageSquare },
    { path: "/upload", label: "Upload", icon: Upload },
    { path: "/files", label: "Files", icon: Files },
  ];

  return (
    <header className="bg-card shadow-sm border-b border-border">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 text-xl font-bold text-foreground">
            <Bot className="w-6 h-6 text-primary" />
            DocChat AI
          </Link>

          {/* Navigation and Theme Toggle */}
          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                
                return (
                  <Link key={item.path} to={item.path}>
                    <Button
                      variant={isActive ? "default" : "ghost"}
                      className={`flex items-center gap-2 ${
                        isActive ? "bg-primary hover:bg-primary/90 text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {item.label}
                    </Button>
                  </Link>
                );
              })}
            </nav>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  );
};
