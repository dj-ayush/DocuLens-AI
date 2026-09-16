import { useState, type FormEvent } from 'react'

import { useChat } from '../context/ChatContext'
import { SendIcon } from './icons'

export function ChatInput() {
  const { activeDocument, isChatting, isUploading, sendMessage } = useChat()
  const [input, setInput] = useState('')

  const disabled = !activeDocument || isChatting || isUploading

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || disabled) return

    setInput('')
    await sendMessage(trimmed)
  }

  return (
    <div className="sticky bottom-0 shrink-0 border-t border-border bg-white px-4 py-4 shadow-[var(--shadow-composer)] md:px-8">
      <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-xl border border-border bg-white p-2 shadow-[var(--shadow-subtle)] focus-within:border-accent/50">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask anything about your document…"
            disabled={disabled}
            rows={1}
            className="max-h-32 min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2.5 text-[14px] leading-relaxed text-primary outline-none placeholder:text-secondary disabled:cursor-not-allowed disabled:opacity-50"
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void handleSubmit(event)
              }
            }}
          />
          <button
            type="submit"
            disabled={disabled || !input.trim()}
            aria-label="Send message"
            className="mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent text-white transition-colors hover:bg-[#1a65e6] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
          >
            <SendIcon />
          </button>
        </div>
        <p className="mt-2 px-1 text-center text-[11px] text-secondary">
          Answers are generated from your uploaded document.
        </p>
      </form>
    </div>
  )
}
