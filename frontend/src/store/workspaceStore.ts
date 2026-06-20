import { create } from 'zustand'

export interface WorkspaceInfo {
  path: string
  name: string
  opened_at: string
}

interface WorkspaceState {
  current: WorkspaceInfo | null
  recent: WorkspaceInfo[]
  loading: boolean
  error: string | null

  fetchCurrent: () => Promise<void>
  fetchRecent: () => Promise<void>
  openWorkspace: (path: string) => Promise<WorkspaceInfo>
  closeWorkspace: () => Promise<void>
  switchWorkspace: (path: string) => Promise<WorkspaceInfo>
}

const API_BASE = '/api/v1/workspace'

const useWorkspaceStore = create<WorkspaceState>()((set) => ({
  current: null,
  recent: [],
  loading: false,
  error: null,

  fetchCurrent: async () => {
    try {
      const res = await fetch(API_BASE)
      if (res.ok) {
        const data = await res.json()
        set({ current: data, error: null })
      } else {
        set({ current: null })
      }
    } catch {
      set({ error: 'Failed to fetch workspace' })
    }
  },

  fetchRecent: async () => {
    try {
      const res = await fetch(`${API_BASE}/recent`)
      if (res.ok) {
        const data = await res.json()
        set({ recent: data })
      }
    } catch {
      // silently fail
    }
  },

  openWorkspace: async (path: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(API_BASE, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to open workspace')
      }
      const data = await res.json()
      set({ current: data, loading: false })
      // Refresh recent list
      const recentRes = await fetch(`${API_BASE}/recent`)
      if (recentRes.ok) {
        set({ recent: await recentRes.json() })
      }
      return data
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to open workspace'
      set({ error: msg, loading: false })
      throw err
    }
  },

  closeWorkspace: async () => {
    try {
      await fetch(API_BASE, { method: 'DELETE' })
      set({ current: null, error: null })
    } catch {
      set({ error: 'Failed to close workspace' })
    }
  },

  switchWorkspace: async (path: string) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to switch workspace')
      }
      const data = await res.json()
      set({ current: data, loading: false })
      const recentRes = await fetch(`${API_BASE}/recent`)
      if (recentRes.ok) {
        set({ recent: await recentRes.json() })
      }
      return data
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to switch workspace'
      set({ error: msg, loading: false })
      throw err
    }
  },
}))

export default useWorkspaceStore
