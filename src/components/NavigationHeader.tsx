
import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { MessageSquare, Upload, Files, Bot, LogOut, User } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

export const NavigationHeader = () => {
  const location = useLocation();
  const { user, logout, isAdmin, isManager } = useAuth();

  const navItems = [
    { path: "/", label: "Chat", icon: MessageSquare },
    { path: "/upload", label: "Upload", icon: Upload, requiresRole: ["admin", "manager"] },
    { path: "/files", label: "Files", icon: Files },
  ].filter(item => 
    !item.requiresRole || 
    item.requiresRole.includes(user?.role || "")
  );

  const handleLogout = () => {
    logout();
  };

  return (
    <header className="bg-card shadow-sm border-b border-border">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 text-xl font-bold text-foreground">
            <Bot className="w-6 h-6 text-primary" />
            DocChat AI
          </Link>

          {/* Navigation and User Controls */}
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

            {/* User Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  {user?.username}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>
                  <div className="flex flex-col">
                    <span>{user?.username}</span>
                    <span className="text-xs text-muted-foreground capitalize">
                      {user?.role}
                    </span>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="w-4 h-4 mr-2" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </header>
  );
};
