import type { SourceCitation } from '../types/api'

interface SourceCardProps {
  source: SourceCitation
  snippet: string
}

export function SourceCard({ source, snippet }: SourceCardProps) {
  const page = source.page_start ?? source.page_number

  return (
    <article className="rounded-lg border border-border bg-surface/60 px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-[12px] font-medium text-primary">
          {source.document_name ?? 'Document'}
          {page != null ? (
            <span className="font-normal text-secondary"> · p.{page}</span>
          ) : null}
        </p>
        <span className="shrink-0 text-[10px] uppercase tracking-wide text-secondary">
          {source.retrieval_method}
        </span>
      </div>
      {snippet ? (
        <p className="mt-1.5 line-clamp-2 text-[12px] leading-relaxed text-secondary">
          {snippet}
        </p>
      ) : null}
    </article>
  )
}
