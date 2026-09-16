import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import {
  getHealth,
  getModels,
  getProviders,
  getVectorStoreCount,
  sendChat,
  uploadPdf,
} from '../api/client'
import type {
  ChatHistoryRecord,
  ChatMessage,
  ConversationTurn,
  IngestionResult,
} from '../types/api'

interface ChatContextValue {
  providers: string[]
  models: string[]
  provider: string
  model: string
  setProvider: (provider: string) => void
  setModel: (model: string) => void
  activeDocument: IngestionResult | null
  uploadedFile: File | null
  messages: ChatMessage[]
  chatHistory: ChatHistoryRecord[]
  vectorCount: number | null
  healthOk: boolean
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  isUploading: boolean
  isChatting: boolean
  error: string | null
  clearError: () => void
  newChat: () => void
  clearSession: () => void
  undoLastMessage: () => void
  uploadDocument: (file: File) => Promise<void>
  sendMessage: (message: string) => Promise<void>
  downloadHistory: () => void
}

const ChatContext = createContext<ChatContextValue | null>(null)

function createId(): string {
  return crypto.randomUUID()
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const [providers, setProviders] = useState<string[]>([])
  const [models, setModels] = useState<string[]>([])
  const [provider, setProviderState] = useState('')
  const [model, setModel] = useState('')
  const [activeDocument, setActiveDocument] = useState<IngestionResult | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatHistory, setChatHistory] = useState<ChatHistoryRecord[]>([])
  const [vectorCount, setVectorCount] = useState<number | null>(null)
  const [healthOk, setHealthOk] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isChatting, setIsChatting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const lastProviderRef = useRef('')

  const clearError = useCallback(() => setError(null), [])

  useEffect(() => {
    void (async () => {
      try {
        await getHealth()
        setHealthOk(true)
        const providerList = await getProviders()
        setProviders(providerList)
        if (providerList.length) {
          setProviderState(providerList[0])
        }
      } catch (err) {
        setHealthOk(false)
        setError(err instanceof Error ? err.message : 'Unable to reach backend.')
      }
    })()
  }, [])

  useEffect(() => {
    if (!provider) {
      setModels([])
      setModel('')
      return
    }

    void (async () => {
      try {
        const modelList = await getModels(provider)
        setModels(modelList)
        setModel((current) => (modelList.includes(current) ? current : modelList[0] ?? ''))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load models.')
      }
    })()
  }, [provider])

  const refreshVectorCount = useCallback(async (selectedProvider: string) => {
    try {
      const count = await getVectorStoreCount(selectedProvider)
      setVectorCount(count)
    } catch {
      setVectorCount(null)
    }
  }, [])

  const setProvider = useCallback((nextProvider: string) => {
    setProviderState(nextProvider)
  }, [])

  useEffect(() => {
    if (!provider || !uploadedFile || !model) {
      lastProviderRef.current = provider
      return
    }

    const previousProvider = lastProviderRef.current
    lastProviderRef.current = provider

    if (!previousProvider || previousProvider === provider) {
      return
    }

    void (async () => {
      setIsUploading(true)
      setError(null)
      try {
        const result = await uploadPdf(provider, uploadedFile)
        setActiveDocument(result)
        await refreshVectorCount(provider)
      } catch (err) {
        setActiveDocument(null)
        setVectorCount(null)
        setError(err instanceof Error ? err.message : 'Unable to process PDF.')
      } finally {
        setIsUploading(false)
      }
    })()
  }, [provider, uploadedFile, model, refreshVectorCount])

  const uploadDocument = useCallback(
    async (file: File) => {
      if (!provider || !model) {
        setError('Select a provider and model before uploading.')
        return
      }

      setUploadedFile(file)
      setIsUploading(true)
      setError(null)

      try {
        const result = await uploadPdf(provider, file)
        setActiveDocument(result)
        await refreshVectorCount(provider)
      } catch (err) {
        setActiveDocument(null)
        setError(err instanceof Error ? err.message : 'Unable to process PDF.')
      } finally {
        setIsUploading(false)
      }
    },
    [provider, model, refreshVectorCount],
  )

  const newChat = useCallback(() => {
    setMessages([])
    setChatHistory([])
    setError(null)
  }, [])

  const clearSession = useCallback(() => {
    setMessages([])
    setChatHistory([])
    setActiveDocument(null)
    setUploadedFile(null)
    setVectorCount(null)
    setError(null)
  }, [])

  const undoLastMessage = useCallback(() => {
    setMessages((current) => {
      if (current.length < 2) return current
      return current.slice(0, -2)
    })
    setChatHistory((current) => current.slice(0, -1))
  }, [])

  const sendMessage = useCallback(
    async (message: string) => {
      if (!provider || !model || !activeDocument) {
        setError('Upload and process a PDF before chatting.')
        return
      }

      const userMessage: ChatMessage = {
        id: createId(),
        role: 'user',
        content: message,
      }

      const pendingMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        content: '',
        pending: true,
      }

      setMessages((current) => [...current, userMessage, pendingMessage])
      setIsChatting(true)
      setError(null)

      const history: ConversationTurn[] = chatHistory.slice(-10).map((item) => ({
        question: item.question,
        answer: item.answer,
      }))

      const startedAt = performance.now()

      try {
        const response = await sendChat(provider, model, message, history)
        const responseTimeMs = Math.round(performance.now() - startedAt)

        setMessages((current) =>
          current.map((entry) =>
            entry.id === pendingMessage.id
              ? {
                  ...entry,
                  content: response.answer,
                  response,
                  responseTimeMs,
                  pending: false,
                }
              : entry,
          ),
        )

        setChatHistory((current) => [
          ...current,
          {
            id: createId(),
            question: message,
            answer: response.answer,
            modelProvider: provider,
            modelName: model,
            pdfFiles: activeDocument ? [activeDocument.filename] : [],
            timestamp: new Date().toISOString(),
            response,
            responseTimeMs,
          },
        ])
      } catch (err) {
        const messageText = err instanceof Error ? err.message : 'Unable to generate a response.'
        setMessages((current) =>
          current.map((entry) =>
            entry.id === pendingMessage.id
              ? {
                  ...entry,
                  content: messageText,
                  pending: false,
                  error: messageText,
                }
              : entry,
          ),
        )
        setError(messageText)
      } finally {
        setIsChatting(false)
      }
    },
    [activeDocument, chatHistory, model, provider],
  )

  const downloadHistory = useCallback(() => {
    import('../utils/csvExport').then(({ downloadChatHistoryCsv }) => {
      downloadChatHistoryCsv(chatHistory)
    })
  }, [chatHistory])

  const value = useMemo<ChatContextValue>(
    () => ({
      providers,
      models,
      provider,
      model,
      setProvider,
      setModel,
      activeDocument,
      uploadedFile,
      messages,
      chatHistory,
      vectorCount,
      healthOk,
      sidebarOpen,
      setSidebarOpen,
      isUploading,
      isChatting,
      error,
      clearError,
      newChat,
      clearSession,
      undoLastMessage,
      uploadDocument,
      sendMessage,
      downloadHistory,
    }),
    [
      providers,
      models,
      provider,
      model,
      activeDocument,
      uploadedFile,
      messages,
      chatHistory,
      vectorCount,
      healthOk,
      sidebarOpen,
      isUploading,
      isChatting,
      error,
      clearError,
      newChat,
      clearSession,
      undoLastMessage,
      uploadDocument,
      sendMessage,
      downloadHistory,
      setProvider,
    ],
  )

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat(): ChatContextValue {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within ChatProvider')
  }
  return context
}
