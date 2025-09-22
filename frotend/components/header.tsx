import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Settings, User, Zap } from "lucide-react"

export function Header() {
  return (
    <header className="border-b border-border/50 glass-effect">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <Zap className="w-4 h-4 text-primary-foreground" />
              </div>
              <h1 className="text-xl font-semibold text-foreground">LLM Studio</h1>
            </div>
            <Badge variant="secondary" className="text-xs">
              MCP Protocol v1.0
            </Badge>
          </div>

          <nav className="hidden md:flex items-center gap-6">
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Servers
            </a>
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Tools
            </a>
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Models
            </a>
            <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Playground
            </a>
          </nav>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm">
              <Settings className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm">
              <User className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </header>
  )
}
