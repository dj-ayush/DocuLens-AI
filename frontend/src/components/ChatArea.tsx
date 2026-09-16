import { useEffect, useRef } from 'react'

import { useChat } from '../context/ChatContext'
import { ChatBubbleIcon } from './icons'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'

const EXAMPLE_QUESTIONS = [
  'What is this document about?',
  'Summarize the key points',
  'Explain the main concepts',
]

function EmptyState({ onExampleClick }: { onExampleClick: (question: string) => void }) {
  const { activeDocument, isChatting, isUploading } = useChat()
  const canAsk = Boolean(activeDocument) && !isChatting && !isUploading

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl border border-border bg-white text-secondary shadow-[var(--shadow-subtle)]">
        <ChatBubbleIcon className="h-7 w-7" />
      </div>
      <h3 className="text-[15px] font-medium text-primary">
        Ask questions about your PDF
      </h3>
      <p className="mt-1.5 max-w-sm text-center text-[13px] leading-relaxed text-secondary">
        with grounded source citations
      </p>
      {canAsk ? (
        <div className="mt-8 flex max-w-lg flex-wrap justify-center gap-2">
          {EXAMPLE_QUESTIONS.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => onExampleClick(question)}
              className="rounded-full border border-border bg-white px-3.5 py-1.5 text-[12px] text-primary transition-colors hover:border-accent/30 hover:bg-surface"
            >
              {question}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function ChatArea() {
  const {
    activeDocument,
    messages,
    error,
    clearError,
    setSidebarOpen,
    sendMessage,
  } = useChat()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-surface">
      <header className="shrink-0 border-b border-border bg-white px-4 py-4 md:px-8">
        <div className="mx-auto flex max-w-3xl items-start gap-3">
          <button
            type="button"
            className="mt-0.5 rounded-md border border-border px-2.5 py-1 text-[12px] font-medium text-secondary lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            Menu
          </button>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-[15px] font-medium text-primary">
              {activeDocument
                ? `Active document: ${activeDocument.filename}`
                : 'No active document'}
            </h2>
            <p className="mt-0.5 text-[13px] text-secondary">
              Grounded document chat
            </p>
          </div>
        </div>
      </header>

      {error ? (
        <div className="mx-auto mt-4 flex w-full max-w-3xl items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-[13px] text-red-700">
          <span>{error}</span>
          <button
            type="button"
            onClick={clearError}
            className="ml-4 shrink-0 font-medium hover:underline"
          >
            Dismiss
          </button>
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {!messages.length ? (
          <EmptyState onExampleClick={(question) => void sendMessage(question)} />
        ) : (
          <div className="mx-auto max-w-3xl px-4 py-8 md:px-8">
            <div className="flex flex-col gap-8">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
            </div>
            <div ref={bottomRef} className="h-4" />
          </div>
        )}
      </div>

      <ChatInput />
    </div>
  )
}
