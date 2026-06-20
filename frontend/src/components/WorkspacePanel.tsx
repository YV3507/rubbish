import { useEffect, useState, useCallback } from 'react'
import useWorkspaceStore, { WorkspaceInfo } from '../store/workspaceStore'

export default function WorkspacePanel() {
  const {
    current,
    recent,
    loading,
    error,
    fetchCurrent,
    fetchRecent,
    openWorkspace,
    closeWorkspace,
  } = useWorkspaceStore()

  const [pathInput, setPathInput] = useState('')
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    fetchCurrent()
    fetchRecent()
  }, [fetchCurrent, fetchRecent])

  const handleOpen = useCallback(async () => {
    if (!pathInput.trim()) return
    try {
      await openWorkspace(pathInput.trim())
      setPathInput('')
    } catch {
      // error is already set in store
    }
  }, [pathInput, openWorkspace])

  const handleClose = useCallback(async () => {
    await closeWorkspace()
  }, [closeWorkspace])

  const handleRecentClick = useCallback(async (w: WorkspaceInfo) => {
    try {
      await openWorkspace(w.path)
    } catch {
      // error is already set in store
    }
  }, [openWorkspace])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleOpen()
    }
  }, [handleOpen])

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Workspace
        </h2>
        {current && (
          <button
            onClick={handleClose}
            className="px-3 py-1.5 text-xs rounded-lg border border-red-300 dark:border-red-600
                       text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30"
          >
            Close
          </button>
        )}
      </div>

      {/* Current workspace */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
          Current
        </h3>
        {current ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center gap-3">
              <svg className="w-5 h-5 text-blue-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {current.name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate font-mono">
                  {current.path}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-400 dark:text-gray-500 italic">
            No workspace open
          </p>
        )}
      </div>

      {/* Open new workspace */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
          Open Workspace
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={pathInput}
            onChange={(e) => setPathInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter directory path..."
            className="flex-1 text-sm px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       placeholder:text-gray-400 dark:placeholder:text-gray-500"
          />
          <button
            onClick={handleOpen}
            disabled={loading || !pathInput.trim()}
            className="px-4 py-2 text-sm rounded-lg bg-blue-500 text-white
                       hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Opening...' : 'Open'}
          </button>
        </div>
        {error && (
          <p className="mt-2 text-xs text-red-500">{error}</p>
        )}
      </div>

      {/* Recent workspaces */}
      {recent.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
            Recent
          </h3>
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
            {recent.map((w) => (
              <button
                key={w.path}
                onClick={() => handleRecentClick(w)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                  current?.path === w.path ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                }`}
              >
                <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {w.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate font-mono">
                    {w.path}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
