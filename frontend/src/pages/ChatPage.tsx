import { useState, useRef, useEffect, useCallback } from 'react'
import MessageList from '../components/MessageList'
import PromptInput from '../components/PromptInput'
import ToolCallCard from '../components/ToolCallCard'
import PermissionDialog from '../components/PermissionDialog'
import useSessionStore from '../store/sessionStore'
import useWorkspaceStore from '../store/workspaceStore'
import type { ToolCall } from '../store/sessionStore'
import useSSE from '../hooks/useSSE'
import useWebSocket from '../hooks/useWebSocket'

const API_BASE = '/api/v1'

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sseReady, setSseReady] = useState(false)
  const { messages, toolCalls, appendDelta, addToolCall, updateToolResult, clear } = useSessionStore()
  const [pendingPermission, setPendingPermission] = useState<Record<string, unknown> | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const pendingRunRef = useRef<string | null>(null)

  // Initialize SSE connection for streaming events
  useSSE(sessionId, {
    onConnected: () => {
      setSseReady(true)
    },
    onTextDelta: (data: Record<string, string>) => {
      setError(null)
      appendDelta(data.id || 'msg-1', data.text)
    },
    onToolCall: (data: Record<string, unknown>) => {
      addToolCall({
        id: data.id as string,
        name: data.name as string,
        arguments: data.arguments as Record<string, unknown>,
        status: 'running',
      })
    },
    onToolResult: (data: Record<string, unknown>) => {
      const id = data.id as string
      const result = data.result as string
      if (id && result !== undefined) {
        updateToolResult(id, result)
      }
    },
    onAgentEnd: () => {
      setIsLoading(false)
    },
  })

  // Initialize WebSocket for permission dialogs
  useWebSocket(sessionId, {
    onPermissionRequest: (data: Record<string, unknown>) => {
      setPendingPermission(data)
    },
  })

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, toolCalls])

  const handleNewSession = useCallback(() => {
    clear()
    setSessionId('')
    setSseReady(false)
    setError(null)
    pendingRunRef.current = null
  }, [clear])

  // When SSE becomes ready, fire a pending agent run
  useEffect(() => {
    if (sseReady && pendingRunRef.current) {
      const prompt = pendingRunRef.current
      pendingRunRef.current = null
      doRun(prompt)
    }
  }, [sseReady])

  const doRun = useCallback(async (prompt: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const runRes = await fetch(`${API_BASE}/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, prompt }),
      })
      if (!runRes.ok) {
        const errData = await runRes.json()
        throw new Error(errData.detail || `Agent run failed: ${runRes.status}`)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start agent'
      setError(msg)
      setIsLoading(false)
    }
  }, [sessionId])

  const handleSend = useCallback(async (prompt: string) => {
    if (isLoading) return

    try {
      // Step 1: Create a new session if needed
      let sid = sessionId
      if (!sid) {
        const createRes = await fetch(`${API_BASE}/session/create`, {
          method: 'POST',
        })
        if (!createRes.ok) {
          throw new Error(`Failed to create session: ${createRes.status}`)
        }
        const createData = await createRes.json()
        sid = createData.session_id
        setSessionId(sid)
        setSseReady(false)
        // Defer run until SSE connects
        pendingRunRef.current = prompt
        return
      }

      // Step 2: Session exists — SSE should already be connected
      if (!sseReady) {
        pendingRunRef.current = prompt
        return
      }

      await doRun(prompt)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start agent'
      setError(msg)
      setIsLoading(false)
    }
  }, [sessionId, isLoading, sseReady, doRun])

  const handlePermissionResponse = async (action: string, id: string) => {
    try {
      const ws = new WebSocket(
        `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${API_BASE}/ws/permission/${sessionId}`
      )
      ws.onopen = () => {
        ws.send(JSON.stringify({ action, id }))
        ws.close()
      }
    } catch (err) {
      console.error('Failed to send permission response:', err)
    }
    setPendingPermission(null)
  }

  const { current: workspace } = useWorkspaceStore()

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <header className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white shrink-0">
            Rubbish
          </h1>
          {workspace && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 truncate">
              <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              <span className="truncate max-w-[200px]">{workspace.name}</span>
            </div>
          )}
        </div>
        <button
          onClick={handleNewSession}
          className="text-xs px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600
                     text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          + New Session
        </button>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {error && (
          <div className="px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        <MessageList messages={messages} />

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-400 px-1">
            <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" />
            <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
            <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
            <span className="ml-1">Thinking...</span>
          </div>
        )}

        {toolCalls.size > 0 && (
          <div className="space-y-2">
            {Array.from(toolCalls.entries()).map(([id, call]: [string, ToolCall]) => (
              <ToolCallCard key={id} toolCall={call} />
            ))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Permission Dialog */}
      {pendingPermission && (
        <PermissionDialog
          toolCall={pendingPermission as unknown as { id: string; name: string; arguments: Record<string, unknown> }}
          onAllow={() => handlePermissionResponse('allow', pendingPermission.id as string)}
          onDeny={() => handlePermissionResponse('deny', pendingPermission.id as string)}
        />
      )}

      {/* Input */}
      <footer className="border-t border-gray-200 dark:border-gray-700 px-4 py-3">
        <PromptInput onSend={handleSend} disabled={isLoading} />
      </footer>
    </div>
  )
}
