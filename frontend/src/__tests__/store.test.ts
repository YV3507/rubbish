import { describe, it, expect, beforeEach } from 'vitest'
import useSessionStore from '../store/sessionStore'

describe('sessionStore', () => {
  beforeEach(() => {
    useSessionStore.getState().clear()
  })

  it('starts with empty state', () => {
    const state = useSessionStore.getState()
    expect(state.messages).toEqual([])
    expect(state.sessionId).toBeNull()
  })

  it('appendDelta creates or appends to a message', () => {
    useSessionStore.getState().appendDelta('msg-1', 'Hello')
    let state = useSessionStore.getState()
    expect(state.messages).toHaveLength(1)
    expect(state.messages[0].content).toBe('Hello')

    useSessionStore.getState().appendDelta('msg-1', ' World')
    state = useSessionStore.getState()
    expect(state.messages[0].content).toBe('Hello World')
  })

  it('addToolCall stores a tool call', () => {
    const call = { id: 'tc-1', name: 'edit', arguments: {} }
    useSessionStore.getState().addToolCall(call)
    const state = useSessionStore.getState()
    expect(state.toolCalls.get('tc-1')).toEqual(call)
  })

  it('updateToolResult updates existing tool call', () => {
    useSessionStore.getState().addToolCall({
      id: 'tc-1', name: 'bash', arguments: { command: 'ls' },
    })
    useSessionStore.getState().updateToolResult('tc-1', 'file1.txt')
    const state = useSessionStore.getState()
    expect(state.toolCalls.get('tc-1')?.result).toBe('file1.txt')
  })

  it('clear resets state', () => {
    useSessionStore.getState().appendDelta('msg-1', 'test')
    useSessionStore.getState().setSessionId('sess-1')
    useSessionStore.getState().clear()
    const state = useSessionStore.getState()
    expect(state.messages).toEqual([])
    expect(state.sessionId).toBeNull()
  })

  it('setSessionId updates session ID', () => {
    useSessionStore.getState().setSessionId('sess-123')
    expect(useSessionStore.getState().sessionId).toBe('sess-123')
  })
})
