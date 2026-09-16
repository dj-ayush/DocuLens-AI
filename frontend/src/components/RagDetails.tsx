import { useState } from 'react'

import type { AnswerResponse } from '../types/api'
import { countChunksByMethod } from '../utils/ragFormatters'

interface RagDetailsProps {
  response: AnswerResponse
  responseTimeMs?: number
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="text-[11px] text-secondary">{label}</span>
      <span className="max-w-[60%] text-right text-[11px] font-medium text-primary">
        {value}
      </span>
    </div>
  )
}

export function RagDetails({ response, responseTimeMs }: RagDetailsProps) {
  const [open, setOpen] = useState(false)
  const chunks = response.retrieval?.retrieved_chunks ?? []
  const methodCounts = countChunksByMethod(chunks)
  const methods = Array.from(new Set(chunks.map((chunk) => chunk.retrieval_method)))
  const topScore = chunks.length
    ? Math.max(...chunks.map((chunk) => chunk.score)).toFixed(3)
    : '—'

  const pageNumbers = chunks
    .map((chunk) => chunk.metadata?.page_start ?? chunk.metadata?.page_number)
    .filter((page): page is number => typeof page === 'number')

  const pageRange =
    pageNumbers.length > 0
      ? (() => {
          const min = Math.min(...pageNumbers)
          const max = Math.max(...pageNumbers)
          return min === max ? `${min}` : `${min}–${max}`
        })()
      : '—'

  return (
    <div className="mt-3 border-t border-border pt-3">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="text-[11px] font-medium text-accent hover:underline"
      >
        RAG Details {open ? '▾' : '▸'}
      </button>

      {open ? (
        <div className="mt-2 divide-y divide-border rounded-lg border border-border bg-surface/50 px-3">
          <DetailRow
            label="Retrieval method"
            value={methods.length ? methods.join(', ') : '—'}
          />
          <DetailRow
            label="Semantic candidates"
            value={String(methodCounts.semantic)}
          />
          <DetailRow
            label="Keyword candidates"
            value={String(methodCounts.keyword)}
          />
          <DetailRow label="Final chunks" value={String(chunks.length)} />
          <DetailRow label="Pages retrieved" value={pageRange} />
          <DetailRow label="Relevance score" value={topScore} />
          <DetailRow label="Grounded" value={response.grounded ? 'Yes' : 'No'} />
          <DetailRow label="Confidence" value={response.confidence} />
          <DetailRow
            label="Response time"
            value={responseTimeMs != null ? `${responseTimeMs} ms` : '—'}
          />
          {response.retrieval?.normalized_query ? (
            <DetailRow
              label="Normalized query"
              value={response.retrieval.normalized_query}
            />
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
