import { useEffect, useRef } from 'react'

interface WebSocketHandlers {
  onPermissionRequest?: (data: Record<string, unknown>) => void
  onToolConfirm?: (data: Record<string, unknown>) => void
  onError?: (error: Event) => void
}

export default function useWebSocket(sessionId: string, handlers: WebSocketHandlers) {
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!sessionId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/permission/${sessionId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>
        switch (data.type) {
          case 'permission_request':
            handlers.onPermissionRequest?.(data)
            break
          case 'tool_confirm':
            handlers.onToolConfirm?.(data)
            break
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onerror = (error: Event) => {
      handlers.onError?.(error)
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [sessionId])
}
