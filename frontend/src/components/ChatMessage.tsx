import type { ChatMessage as ChatMessageType } from '../types/api'
import {
  buildResponseMeta,
  getSnippetForSource,
} from '../utils/ragFormatters'
import { RagDetails } from './RagDetails'
import { SourceCard } from './SourceCard'

interface ChatMessageProps {
  message: ChatMessageType
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const chunks = message.response?.retrieval?.retrieved_chunks ?? []

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      {isUser ? (
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-[14px] leading-relaxed text-white">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      ) : (
        <div className="w-full max-w-[92%] md:max-w-[85%]">
          <div className="rounded-2xl rounded-bl-md border border-border bg-white px-5 py-4 shadow-[var(--shadow-subtle)]">
            {message.pending ? (
              <p className="text-[14px] text-secondary">Thinking…</p>
            ) : message.error ? (
              <p className="text-[14px] text-red-600">{message.error}</p>
            ) : (
              <>
                <p className="whitespace-pre-wrap text-[14px] leading-[1.7] text-primary">
                  {message.content}
                </p>

                {message.response ? (
                  <>
                    <p className="mt-4 text-[11px] tracking-wide text-secondary">
                      {buildResponseMeta(message.response)}
                    </p>

                    {message.response.grounded && message.response.sources.length ? (
                      <div className="mt-3 space-y-2">
                        {message.response.sources.map((source) => (
                          <SourceCard
                            key={
                              source.chunk_id ??
                              `${source.document_name}-${source.page_start}`
                            }
                            source={source}
                            snippet={getSnippetForSource(source, chunks)}
                          />
                        ))}
                      </div>
                    ) : null}

                    <RagDetails
                      response={message.response}
                      responseTimeMs={message.responseTimeMs}
                    />
                  </>
                ) : null}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
