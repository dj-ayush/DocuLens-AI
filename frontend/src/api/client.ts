import type {
  AnswerResponse,
  ConversationTurn,
  IngestionResult,
  StandardAPIResponse,
} from '../types/api'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'
const RETRY_DELAY_MS = 1500

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  try {
    return await fetch(input, init)
  } catch (error) {
    await wait(RETRY_DELAY_MS)
    try {
      return await fetch(input, init)
    } catch {
      throw error
    }
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  const json = (await response.json()) as StandardAPIResponse<T>

  if (!response.ok || json.status === 'error') {
    throw new Error(json.message ?? 'Request failed.')
  }

  return json.data
}

export async function getHealth(): Promise<string> {
  return handleResponse<string>(await apiFetch(`${API_BASE}/health`))
}

export async function getProviders(): Promise<string[]> {
  return handleResponse<string[]>(await apiFetch(`${API_BASE}/llm`))
}

export async function getModels(provider: string): Promise<string[]> {
  const normalized = provider.toLowerCase()
  return handleResponse<string[]>(
    await apiFetch(`${API_BASE}/llm/${normalized}`),
  )
}

export async function uploadPdf(
  provider: string,
  file: File,
): Promise<IngestionResult> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('model_provider', provider.toLowerCase())

  return handleResponse<IngestionResult>(
    await apiFetch(`${API_BASE}/upload_and_process_pdfs`, {
      method: 'POST',
      body: formData,
    }),
  )
}

export async function getVectorStoreCount(provider: string): Promise<number> {
  return handleResponse<number>(
    await apiFetch(`${API_BASE}/vector_store/count/${provider.toLowerCase()}`),
  )
}

export async function sendChat(
  provider: string,
  modelName: string,
  message: string,
  history: ConversationTurn[],
): Promise<AnswerResponse> {
  return handleResponse<AnswerResponse>(
    await apiFetch(`${API_BASE}/chat`, {
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
