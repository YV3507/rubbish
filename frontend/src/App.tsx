import { useState, useEffect, useCallback } from 'react'
import ChatPage from './pages/ChatPage'
import ConfigPanel from './components/ConfigPanel'
import WorkspacePanel from './components/WorkspacePanel'
import useWorkspaceStore from './store/workspaceStore'

type View = 'chat' | 'workspace' | 'settings'

export default function App() {
  const [view, setView] = useState<View>('chat')
  const [showShutdownConfirm, setShowShutdownConfirm] = useState(false)
  const [shuttingDown, setShuttingDown] = useState(false)
  const { current, fetchCurrent } = useWorkspaceStore()

  useEffect(() => {
    fetchCurrent()
  }, [fetchCurrent])

  const handleShutdown = useCallback(async () => {
    setShuttingDown(true)
    try {
      await fetch('/api/v1/shutdown', { method: 'POST' })
    } catch {
      // Backend may close connection before response — that's expected
    }
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Shutdown overlay */}
      {shuttingDown && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 dark:bg-gray-900/80">
          <div className="text-center">
            <svg className="w-10 h-10 mx-auto mb-4 text-gray-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <p className="text-sm text-gray-600 dark:text-gray-400">Shutting down backend...</p>
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">Close this window or run '.\run.ps1 stop' to clean up.</p>
          </div>
        </div>
      )}

      {/* Shutdown confirmation dialog */}
      {showShutdownConfirm && !shuttingDown && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 p-6 max-w-sm mx-4">
            <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
              Shut Down Rubbish?
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-5">
              This will stop the backend server. You can restart it with <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">.\run.ps1 all</code>.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowShutdownConfirm(false)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600
                           text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowShutdownConfirm(false); handleShutdown() }}
                className="px-4 py-2 text-sm rounded-lg bg-red-500 text-white hover:bg-red-600"
              >
                Shut Down
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top navigation bar */}
      <nav className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="max-w-4xl mx-auto flex items-center h-10 px-4 gap-3">
          <span className="text-sm font-bold text-gray-800 dark:text-gray-200 mr-2">
            Rubbish
          </span>
          <button
            onClick={() => setView('chat')}
            className={`text-sm px-2 py-1 rounded ${
              view === 'chat'
                ? 'text-blue-500 border-b-2 border-blue-500'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
          >
            Chat
          </button>
          <button
            onClick={() => setView('workspace')}
            className={`text-sm px-2 py-1 rounded flex items-center gap-1.5 ${
              view === 'workspace'
                ? 'text-blue-500 border-b-2 border-blue-500'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            Workspace
          </button>
          <button
            onClick={() => setView('settings')}
            className={`text-sm px-2 py-1 rounded ${
              view === 'settings'
                ? 'text-blue-500 border-b-2 border-blue-500'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }`}
          >
            Settings
          </button>

          {/* Right side: workspace indicator + shutdown */}
          <div className="ml-auto flex items-center gap-1">
            {current && (
              <div className="hidden sm:flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 truncate max-w-[180px]">
                <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span className="truncate">{current.name}</span>
              </div>
            )}
            <button
              onClick={() => setShowShutdownConfirm(true)}
              className="p-1.5 rounded text-gray-400 hover:text-red-500 hover:bg-red-50
                         dark:hover:bg-red-900/20 transition-colors"
              title="Shut down backend"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </button>
          </div>
        </div>
      </nav>

      {view === 'chat' && <ChatPage />}
      {view === 'workspace' && <WorkspacePanel />}
      {view === 'settings' && <ConfigPanel />}
    </div>
  )
}
