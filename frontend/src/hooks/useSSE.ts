import { useEffect, useRef } from 'react'

interface SSEHandlers {
  onConnected?: (data: Record<string, string>) => void
  onTextDelta?: (data: Record<string, string>) => void
  onToolCall?: (data: Record<string, unknown>) => void
  onToolResult?: (data: Record<string, unknown>) => void
  onAgentEnd?: (data: Record<string, unknown>) => void
  onError?: (data: unknown) => void
}

export default function useSSE(sessionId: string, handlers: SSEHandlers) {
  const eventSourceRef = useRef<EventSource | null>(null)
  const connectedRef = useRef(false)

  useEffect(() => {
    if (!sessionId) return

    const es = new EventSource(`/api/v1/session/${sessionId}/stream`)
    eventSourceRef.current = es
    connectedRef.current = false

    es.addEventListener('connected', (event: MessageEvent) => {
      connectedRef.current = true
      handlers.onConnected?.(JSON.parse(event.data))
    })

    es.addEventListener('text_delta', (event: MessageEvent) => {
      handlers.onTextDelta?.(JSON.parse(event.data))
    })

    es.addEventListener('tool_call', (event: MessageEvent) => {
      handlers.onToolCall?.(JSON.parse(event.data))
    })

    es.addEventListener('tool_result', (event: MessageEvent) => {
      handlers.onToolResult?.(JSON.parse(event.data))
    })

    es.addEventListener('agent_end', (event: MessageEvent) => {
      handlers.onAgentEnd?.(JSON.parse(event.data))
      es.close()
    })

    es.addEventListener('error', (event: Event) => {
      handlers.onError?.(event)
    })

    return () => {
      es.close()
      eventSourceRef.current = null
      connectedRef.current = false
    }
  }, [sessionId])
}

export { useSSE }
