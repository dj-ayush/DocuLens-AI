import type { ReactNode } from 'react'

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

type MarkdownBlock =
  | { type: 'paragraph'; text: string }
  | { type: 'heading'; level: number; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'code'; text: string }

function isBlockStart(line: string): boolean {
  return (
    line.trim().startsWith('```') ||
    /^(#{1,6})\s+/.test(line) ||
    /^[-*]\s+/.test(line) ||
    /^\d+\.\s+/.test(line)
  )
}

function parseMarkdown(markdown: string): MarkdownBlock[] {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  const blocks: MarkdownBlock[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    const trimmed = line.trim()

    if (!trimmed) {
      index += 1
      continue
    }

    if (trimmed.startsWith('```')) {
      const codeLines: string[] = []
      index += 1

      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        codeLines.push(lines[index])
        index += 1
      }

      if (index < lines.length) index += 1
      blocks.push({ type: 'code', text: codeLines.join('\n') })
      continue
    }

    const headingMatch = /^(#{1,6})\s+(.+)$/.exec(trimmed)
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2],
      })
      index += 1
      continue
    }

    if (/^[-*]\s+/.test(trimmed)) {
      const items: string[] = []

      while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^[-*]\s+/, ''))
        index += 1
      }

      blocks.push({ type: 'ul', items })
      continue
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = []

      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^\d+\.\s+/, ''))
        index += 1
      }

      blocks.push({ type: 'ol', items })
      continue
    }

    const paragraphLines: string[] = []
    while (
      index < lines.length &&
      lines[index].trim() &&
      !isBlockStart(lines[index])
    ) {
      paragraphLines.push(lines[index].trim())
      index += 1
    }

    blocks.push({ type: 'paragraph', text: paragraphLines.join(' ') })
  }

  return blocks
}

function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = []
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g
  let lastIndex = 0

  for (const match of text.matchAll(pattern)) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }

    const token = match[0]
    const key = `${match.index}-${token}`

    if (token.startsWith('**')) {
      parts.push(<strong key={key}>{token.slice(2, -2)}</strong>)
    } else if (token.startsWith('*')) {
      parts.push(<em key={key}>{token.slice(1, -1)}</em>)
    } else {
      parts.push(
        <code key={key} className="rounded bg-surface px-1 py-0.5 text-[13px]">
          {token.slice(1, -1)}
        </code>,
      )
    }

    lastIndex = match.index + token.length
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts
}

function MarkdownContent({ content }: { content: string }) {
  const blocks = parseMarkdown(content)

  return (
    <div className="space-y-3 text-[14px] leading-[1.7] text-primary">
      {blocks.map((block, index) => {
        if (block.type === 'heading') {
          const headingClass =
            block.level <= 2
              ? 'text-[16px] font-semibold text-primary'
              : 'text-[14px] font-semibold text-primary'

          return (
            <h3 key={index} className={headingClass}>
              {renderInline(block.text)}
            </h3>
          )
        }

        if (block.type === 'ul') {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{renderInline(item)}</li>
              ))}
            </ul>
          )
        }

        if (block.type === 'ol') {
          return (
            <ol key={index} className="list-decimal space-y-1 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{renderInline(item)}</li>
              ))}
            </ol>
          )
        }

        if (block.type === 'code') {
          return (
            <pre
              key={index}
              className="overflow-x-auto rounded-lg border border-border bg-surface p-3 text-[13px] leading-relaxed text-primary"
            >
              <code>{block.text}</code>
            </pre>
          )
        }

        return <p key={index}>{renderInline(block.text)}</p>
      })}
    </div>
  )
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
                <MarkdownContent content={message.content} />

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
