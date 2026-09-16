export interface StandardAPIResponse<T = unknown> {
  status: 'success' | 'error'
  data: T
  message?: string | null
}

export interface ConversationTurn {
  question: string
  answer: string
}

export interface SourceCitation {
  document_id?: string | null
  document_name?: string | null
  page_number?: number | null
  page_start?: number | null
  page_end?: number | null
  chunk_id?: string | null
  score: number
  retrieval_method: string
}

export interface RetrievedChunk {
  page_content: string
  metadata: Record<string, unknown>
  score: number
  retrieval_method: string
}

export interface RetrievalResult {
  normalized_query: string
  retrieved_chunks: RetrievedChunk[]
  selected_context: string
  grounded: boolean
}

export interface AnswerResponse {
  answer: string
  grounded: boolean
  confidence: 'high' | 'medium' | 'low'
  sources: SourceCitation[]
  retrieval: RetrievalResult | null
}

export interface IngestionResult {
  document_id: string
  filename: string
  page_count: number
  chunk_count: number
  status: 'processed'
  warnings: string[]
}

export interface ChatHistoryRecord {
  id: string
  question: string
  answer: string
  modelProvider: string
  modelName: string
  pdfFiles: string[]
  timestamp: string
  response?: AnswerResponse
  responseTimeMs?: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  response?: AnswerResponse
  responseTimeMs?: number
  pending?: boolean
  error?: string
}
