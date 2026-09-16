import type {
  AnswerResponse,
  ConversationTurn,
  IngestionResult,
  StandardAPIResponse,
} from '../types/api'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

async function handleResponse<T>(response: Response): Promise<T> {
  const json = (await response.json()) as StandardAPIResponse<T>

  if (!response.ok || json.status === 'error') {
    throw new Error(json.message ?? 'Request failed.')
  }

  return json.data
}

export async function getHealth(): Promise<string> {
  return handleResponse<string>(await fetch(`${API_BASE}/health`))
}

export async function getProviders(): Promise<string[]> {
  return handleResponse<string[]>(await fetch(`${API_BASE}/llm`))
}

export async function getModels(provider: string): Promise<string[]> {
  const normalized = provider.toLowerCase()
  return handleResponse<string[]>(await fetch(`${API_BASE}/llm/${normalized}`))
}

export async function uploadPdf(
  provider: string,
  file: File,
): Promise<IngestionResult> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('model_provider', provider.toLowerCase())

  return handleResponse<IngestionResult>(
    await fetch(`${API_BASE}/upload_and_process_pdfs`, {
      method: 'POST',
      body: formData,
    }),
  )
}

export async function getVectorStoreCount(provider: string): Promise<number> {
  return handleResponse<number>(
    await fetch(`${API_BASE}/vector_store/count/${provider.toLowerCase()}`),
  )
}

export async function sendChat(
  provider: string,
  modelName: string,
  message: string,
  history: ConversationTurn[],
): Promise<AnswerResponse> {
  return handleResponse<AnswerResponse>(
    await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_provider: provider,
        model_name: modelName,
        message,
        history,
      }),
    }),
  )
}
