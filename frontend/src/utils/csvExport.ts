import type { ChatHistoryRecord } from '../types/api'

function escapeCsv(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

export function buildChatHistoryCsv(history: ChatHistoryRecord[]): string {
  const header = [
    'Question',
    'Answer',
    'Model',
    'Model Name',
    'PDF File',
    'Timestamp',
  ]

  const rows = history.map((item) => [
    item.question,
    item.answer,
    item.modelProvider,
    item.modelName,
    item.pdfFiles.join(', '),
    item.timestamp,
  ])

  return [header, ...rows]
    .map((row) => row.map((cell) => escapeCsv(String(cell ?? ''))).join(','))
    .join('\n')
}

export function downloadChatHistoryCsv(history: ChatHistoryRecord[]): void {
  const csv = buildChatHistoryCsv(history)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'chat_history.csv'
  link.click()
  URL.revokeObjectURL(url)
}
