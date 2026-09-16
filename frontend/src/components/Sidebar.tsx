import { useRef } from 'react'

import { useChat } from '../context/ChatContext'
import { PdfIcon } from './icons'

function SidebarPanel({ onNavigate }: { onNavigate?: () => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const {
    providers,
    models,
    provider,
    model,
    setProvider,
    setModel,
    activeDocument,
    chatHistory,
    vectorCount,
    healthOk,
    isUploading,
    newChat,
    clearSession,
    undoLastMessage,
    uploadDocument,
    downloadHistory,
  } = useChat()

  return (
    <div className="flex h-full flex-col">
      <div className="px-5 pb-4 pt-5">
        <h1 className="text-[15px] font-semibold tracking-tight text-primary">
          DocuLens AI
        </h1>
        <p className="mt-0.5 text-[13px] text-secondary">
          Document chat with grounded answers
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        <button
          type="button"
          onClick={() => {
            newChat()
            onNavigate?.()
          }}
          className="w-full rounded-lg bg-accent px-4 py-2.5 text-[13px] font-medium text-white transition-colors hover:bg-[#1a65e6]"
        >
          + New Chat
        </button>

        <div className="space-y-2">
          <p className="px-1 text-[11px] font-medium uppercase tracking-wider text-secondary">
            Model
          </p>
          <select
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
            className="w-full rounded-lg border border-border bg-white px-3 py-2 text-[13px] text-primary outline-none focus:border-accent"
          >
            {providers.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <select
            value={model}
            onChange={(event) => setModel(event.target.value)}
            disabled={!provider}
            className="w-full rounded-lg border border-border bg-white px-3 py-2 text-[13px] text-primary outline-none focus:border-accent disabled:bg-surface disabled:text-secondary"
          >
            {models.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>

        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) {
                void uploadDocument(file)
              }
              event.target.value = ''
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={!provider || !model || isUploading}
            className="w-full rounded-lg border border-border bg-white px-4 py-2.5 text-[13px] font-medium text-primary shadow-[var(--shadow-subtle)] transition-colors hover:border-accent/40 hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isUploading ? 'Processing PDF…' : 'Upload PDF'}
          </button>
        </div>

        {activeDocument ? (
          <div className="flex items-start gap-3 rounded-lg border border-border bg-white px-3 py-3">
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-50 text-red-500">
              <PdfIcon className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-medium text-primary">
                {activeDocument.filename}
              </p>
              <p className="mt-0.5 text-[12px] text-secondary">
                {activeDocument.page_count} pages
              </p>
              <span className="mt-1.5 inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-600">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Active
              </span>
            </div>
          </div>
        ) : null}

        {activeDocument?.warnings.length ? (
          <div className="space-y-1 px-1">
            {activeDocument.warnings.map((warning) => (
              <p key={warning} className="text-[11px] leading-relaxed text-amber-700">
                {warning}
              </p>
            ))}
          </div>
        ) : null}

        <div className="min-h-0 flex-1">
          <p className="mb-2 px-1 text-[11px] font-medium uppercase tracking-wider text-secondary">
            Chat History
          </p>
          {chatHistory.length ? (
            <ul className="space-y-0.5">
              {chatHistory.map((item) => (
                <li
                  key={item.id}
                  className="truncate rounded-md px-2 py-1.5 text-[13px] text-primary hover:bg-surface"
                  title={item.question}
                >
                  {item.question}
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-2 text-[13px] text-secondary">No messages yet</p>
          )}
        </div>
      </div>

      <div className="shrink-0 space-y-3 border-t border-border px-4 py-4">
        <div className="flex items-center justify-between px-1 text-[12px]">
          <span className="font-medium text-secondary">RAG</span>
          <span className="flex items-center gap-1.5 text-primary">
            <span
              className={`h-1.5 w-1.5 rounded-full ${healthOk ? 'bg-emerald-500' : 'bg-red-400'}`}
            />
            {healthOk ? 'Online' : 'Offline'}
            {vectorCount != null ? (
              <span className="text-secondary">· {vectorCount} chunks</span>
            ) : null}
          </span>
        </div>

        <button
          type="button"
          onClick={downloadHistory}
          className="w-full rounded-lg border border-border bg-white px-4 py-2 text-[13px] font-medium text-primary transition-colors hover:bg-surface"
        >
          Download Chat History
        </button>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={undoLastMessage}
            disabled={!chatHistory.length}
            className="flex-1 rounded-md px-2 py-1.5 text-[11px] font-medium text-secondary transition-colors hover:bg-surface hover:text-primary disabled:opacity-40"
          >
            Undo
          </button>
          <button
            type="button"
            onClick={clearSession}
            className="flex-1 rounded-md px-2 py-1.5 text-[11px] font-medium text-secondary transition-colors hover:bg-surface hover:text-primary"
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  )
}

export function Sidebar() {
  const { sidebarOpen, setSidebarOpen } = useChat()

  return (
    <>
      <aside className="hidden h-full w-[288px] shrink-0 border-r border-border bg-white lg:flex lg:flex-col">
        <SidebarPanel />
      </aside>

      {sidebarOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close sidebar"
            className="absolute inset-0 bg-slate-900/20"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative z-50 flex h-full w-[288px] max-w-[85vw] flex-col border-r border-border bg-white shadow-lg">
            <SidebarPanel onNavigate={() => setSidebarOpen(false)} />
          </aside>
        </div>
      ) : null}
    </>
  )
}
