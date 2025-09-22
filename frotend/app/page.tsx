import { Header } from "@/components/header"
import { ServerGrid } from "@/components/server-grid"
import { ChatInterface } from "@/components/chat-interface"

export default function Home() {
  return (
    <div className="min-h-screen gradient-bg">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[calc(100vh-12rem)]">
          <div className="lg:col-span-1">
            <ServerGrid />
          </div>
          <div className="lg:col-span-2">
            <ChatInterface />
          </div>
        </div>
      </main>
    </div>
  )
}
