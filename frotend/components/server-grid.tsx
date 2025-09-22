"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
  Database,
  Globe,
  FileText,
  ImageIcon,
  Code,
  ChevronDown,
  ChevronRight,
  Circle,
  CheckCircle2,
  XCircle,
} from "lucide-react"

const mockServers = [
  {
    id: "database-server",
    name: "Database Server",
    description: "PostgreSQL and MongoDB operations",
    status: "connected",
    icon: Database,
    tools: [
      { name: "query_database", description: "Execute SQL queries", type: "database" },
      { name: "create_table", description: "Create new database tables", type: "database" },
      { name: "backup_data", description: "Create database backups", type: "utility" },
    ],
  },
  {
    id: "web-server",
    name: "Web Scraper",
    description: "Web scraping and content extraction",
    status: "connected",
    icon: Globe,
    tools: [
      { name: "scrape_url", description: "Extract content from web pages", type: "web" },
      { name: "get_page_metadata", description: "Get page title, description, etc.", type: "web" },
      { name: "download_file", description: "Download files from URLs", type: "utility" },
    ],
  },
  {
    id: "file-server",
    name: "File Operations",
    description: "File system operations and management",
    status: "disconnected",
    icon: FileText,
    tools: [
      { name: "read_file", description: "Read file contents", type: "file" },
      { name: "write_file", description: "Write data to files", type: "file" },
      { name: "list_directory", description: "List directory contents", type: "file" },
    ],
  },
  {
    id: "image-server",
    name: "Image Processing",
    description: "Image generation and manipulation",
    status: "connected",
    icon: ImageIcon,
    tools: [
      { name: "generate_image", description: "Generate images from text", type: "ai" },
      { name: "resize_image", description: "Resize and crop images", type: "image" },
      { name: "extract_text", description: "OCR text extraction", type: "ai" },
    ],
  },
  {
    id: "code-server",
    name: "Code Assistant",
    description: "Code analysis and generation tools",
    status: "connected",
    icon: Code,
    tools: [
      { name: "analyze_code", description: "Analyze code quality and structure", type: "code" },
      { name: "generate_tests", description: "Generate unit tests", type: "code" },
      { name: "refactor_code", description: "Suggest code improvements", type: "code" },
    ],
  },
]

const getStatusIcon = (status: string) => {
  switch (status) {
    case "connected":
      return <CheckCircle2 className="w-4 h-4 text-green-500" />
    case "disconnected":
      return <XCircle className="w-4 h-4 text-red-500" />
    default:
      return <Circle className="w-4 h-4 text-yellow-500" />
  }
}

const getToolTypeColor = (type: string) => {
  switch (type) {
    case "database":
      return "bg-blue-500/20 text-blue-400 border-blue-500/30"
    case "web":
      return "bg-green-500/20 text-green-400 border-green-500/30"
    case "file":
      return "bg-purple-500/20 text-purple-400 border-purple-500/30"
    case "ai":
      return "bg-pink-500/20 text-pink-400 border-pink-500/30"
    case "image":
      return "bg-orange-500/20 text-orange-400 border-orange-500/30"
    case "code":
      return "bg-cyan-500/20 text-cyan-400 border-cyan-500/30"
    default:
      return "bg-gray-500/20 text-gray-400 border-gray-500/30"
  }
}

export function ServerGrid() {
  const [expandedServers, setExpandedServers] = useState<string[]>(["database-server"])

  const toggleServer = (serverId: string) => {
    setExpandedServers((prev) => (prev.includes(serverId) ? prev.filter((id) => id !== serverId) : [...prev, serverId]))
  }

  return (
    <Card className="h-full glass-effect">
      <CardHeader>
        <CardTitle className="text-lg">MCP Servers</CardTitle>
        <CardDescription>Connected servers and available tools</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[calc(100vh-16rem)]">
          <div className="space-y-2 p-6 pt-0">
            {mockServers.map((server) => {
              const Icon = server.icon
              const isExpanded = expandedServers.includes(server.id)

              return (
                <Collapsible key={server.id} open={isExpanded} onOpenChange={() => toggleServer(server.id)}>
                  <CollapsibleTrigger asChild>
                    <Card className="cursor-pointer hover:bg-accent/50 transition-colors">
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center">
                              <Icon className="w-4 h-4 text-secondary-foreground" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <h3 className="font-medium text-sm truncate">{server.name}</h3>
                                {getStatusIcon(server.status)}
                              </div>
                              <p className="text-xs text-muted-foreground truncate">{server.description}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {server.tools.length} tools
                            </Badge>
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-muted-foreground" />
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </CollapsibleTrigger>

                  <CollapsibleContent className="space-y-2 mt-2 ml-4">
                    {server.tools.map((tool, index) => (
                      <Card key={index} className="bg-muted/30">
                        <CardContent className="p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <code className="text-xs font-mono text-primary">{tool.name}</code>
                                <Badge variant="outline" className={`text-xs ${getToolTypeColor(tool.type)}`}>
                                  {tool.type}
                                </Badge>
                              </div>
                              <p className="text-xs text-muted-foreground mt-1">{tool.description}</p>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-xs"
                              disabled={server.status !== "connected"}
                            >
                              Use
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </CollapsibleContent>
                </Collapsible>
              )
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
