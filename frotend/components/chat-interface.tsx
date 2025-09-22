"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Send, Bot, User, Loader2, Settings, Zap, Database, Globe } from "lucide-react"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  tools?: string[]
}

const mockMessages: Message[] = [
  {
    id: "1",
    role: "assistant",
    content:
      "Hello! I'm your LLM assistant with access to multiple MCP servers. I can help you with database operations, web scraping, file management, image processing, and code analysis. What would you like to do?",
    timestamp: new Date(Date.now() - 300000),
  },
  {
    id: "2",
    role: "user",
    content: "Can you help me query my database to find all users created in the last week?",
    timestamp: new Date(Date.now() - 240000),
  },
  {
    id: "3",
    role: "assistant",
    content:
      "I'll help you query your database for users created in the last week. Let me use the database server to execute this query.",
    timestamp: new Date(Date.now() - 180000),
    tools: ["query_database"],
  },
]

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>(mockMessages)
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    // Simulate AI response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I understand your request. Let me process that using the available MCP tools...",
        timestamp: new Date(),
        tools: ["query_database", "analyze_code"],
      }
      setMessages((prev) => [...prev, assistantMessage])
      setIsLoading(false)
    }, 2000)
  }

  const getToolIcon = (tool: string) => {
    if (tool.includes("database")) return <Database className="w-3 h-3" />
    if (tool.includes("web") || tool.includes("scrape")) return <Globe className="w-3 h-3" />
    return <Zap className="w-3 h-3" />
  }

  return (
    <Card className="h-full glass-effect flex flex-col">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Chat Interface</CardTitle>
          <Button variant="ghost" size="sm">
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0">
        <ScrollArea className="flex-1 p-6">
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {message.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-primary-foreground" />
                  </div>
                )}

                <div className={`max-w-[80%] ${message.role === "user" ? "order-first" : ""}`}>
                  <div
                    className={`rounded-lg p-3 ${
                      message.role === "user" ? "bg-primary text-primary-foreground ml-auto" : "bg-muted"
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>

                    {message.tools && message.tools.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {message.tools.map((tool, index) => (
                          <Badge key={index} variant="secondary" className="text-xs flex items-center gap-1">
                            {getToolIcon(tool)}
                            {tool}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  <p className="text-xs text-muted-foreground mt-1 px-1">{message.timestamp.toLocaleTimeString()}</p>
                </div>

                {message.role === "user" && (
                  <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-secondary-foreground" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3 justify-start">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary-foreground" />
                </div>
                <div className="bg-muted rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm text-muted-foreground">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="p-6 border-t border-border/50">
          <div className="flex gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything about your data, code, or use any available tools..."
              className="min-h-[60px] resize-none"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
            />
            <Button onClick={handleSend} disabled={!input.trim() || isLoading} className="self-end">
              <Send className="w-4 h-4" />
            </Button>
          </div>

          <div className="flex items-center gap-2 mt-2">
            <Badge variant="outline" className="text-xs">
              5 servers connected
            </Badge>
            <Badge variant="outline" className="text-xs">
              15 tools available
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
