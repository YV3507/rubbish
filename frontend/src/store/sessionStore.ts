import { create } from 'zustand'

export interface Message {
  id: string
  role: string
  content: string
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: string
  status?: 'running' | 'completed' | 'failed'
}

interface SessionState {
  messages: Message[]
  toolCalls: Map<string, ToolCall>
  sessionId: string | null

  // Actions
  appendDelta: (id: string, text: string) => void
  addToolCall: (call: ToolCall) => void
  updateToolResult: (id: string, result: string) => void
  handlePermission: (id: string, allowed: boolean) => void
  setSessionId: (id: string) => void
  clear: () => void
}

const useSessionStore = create<SessionState>()((set) => ({
  messages: [],
  toolCalls: new Map(),
  sessionId: null,

  appendDelta: (id: string, text: string) => {
    set((state: SessionState) => {
      const existing = state.messages.find((m: Message) => m.id === id)
      if (existing) {
        return {
          messages: state.messages.map((m: Message) =>
            m.id === id ? { ...m, content: m.content + text } : m
          ),
        }
      }
      return {
        messages: [...state.messages, { id, role: 'assistant' as const, content: text }],
      }
    })
  },

  addToolCall: (call: ToolCall) => {
    set((state: SessionState) => {
      const newCalls = new Map(state.toolCalls)
      newCalls.set(call.id, call)
      return { toolCalls: newCalls }
    })
  },

  updateToolResult: (id: string, result: string) => {
    set((state: SessionState) => {
      const newCalls = new Map(state.toolCalls)
      const existing = newCalls.get(id)
      if (existing) {
        newCalls.set(id, { ...existing, result, status: 'completed' })
      }
      return { toolCalls: newCalls }
    })
  },

  handlePermission: (_id: string, _allowed: boolean) => {
    // Forward to WebSocket — stub
  },

  setSessionId: (id: string) => set({ sessionId: id }),

  clear: () => set({ messages: [], toolCalls: new Map(), sessionId: null }),
}))

export default useSessionStore
