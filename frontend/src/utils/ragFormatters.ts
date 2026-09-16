import type { AnswerResponse, RetrievedChunk, SourceCitation } from '../types/api'

function capitalize(value: string): string {
  if (!value) return value
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export function formatRetrievalMethodLabel(sources: SourceCitation[]): string {
  if (!sources.length) return 'No retrieval'

  const methods = new Set(sources.map((source) => source.retrieval_method))
  if (methods.has('hybrid')) return 'Hybrid Retrieval'
  if (methods.size === 1) return `${capitalize(Array.from(methods)[0])} Retrieval`
  return `${Array.from(methods).map(capitalize).join(', ')} Retrieval`
}

export function formatPageRange(sources: SourceCitation[]): string {
  const pages = sources
    .map((source) => source.page_start ?? source.page_number)
    .filter((page): page is number => typeof page === 'number')

  if (!pages.length) return '—'

  const endPages = sources
    .map((source) => source.page_end ?? source.page_number ?? source.page_start)
    .filter((page): page is number => typeof page === 'number')

  const minPage = Math.min(...pages)
  const maxPage = Math.max(...endPages)

  return minPage === maxPage ? `${minPage}` : `${minPage}–${maxPage}`
}

export function countChunksByMethod(chunks: RetrievedChunk[]) {
  return chunks.reduce(
    (counts, chunk) => {
      if (chunk.retrieval_method === 'semantic') counts.semantic += 1
      else if (chunk.retrieval_method === 'keyword') counts.keyword += 1
      else if (chunk.retrieval_method === 'hybrid') counts.hybrid += 1
      return counts
    },
    { semantic: 0, keyword: 0, hybrid: 0 },
  )
}

export function getSnippetForSource(
  source: SourceCitation,
  chunks: RetrievedChunk[],
): string {
  const match = chunks.find((chunk) => chunk.metadata?.chunk_id === source.chunk_id)
  return match?.page_content ?? ''
}

export function buildResponseMeta(response: AnswerResponse): string {
  const parts: string[] = []

  parts.push(response.grounded ? '✓ Grounded' : 'Not grounded')

  if (response.grounded && response.sources.length) {
    parts.push(formatRetrievalMethodLabel(response.sources))
    parts.push(`${response.sources.length} Source${response.sources.length === 1 ? '' : 's'}`)
    parts.push(`Pages ${formatPageRange(response.sources)}`)
  }

  return parts.join('   ·   ')
}
