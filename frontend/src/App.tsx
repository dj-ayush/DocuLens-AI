import { ChatArea } from './components/ChatArea'
import { Sidebar } from './components/Sidebar'
import { ChatProvider } from './context/ChatContext'

export default function App() {
  return (
    <ChatProvider>
      <div className="flex h-full overflow-hidden bg-surface">
        <Sidebar />
        <main className="flex min-w-0 flex-1 flex-col">
          <ChatArea />
        </main>
      </div>
    </ChatProvider>
  )
}
