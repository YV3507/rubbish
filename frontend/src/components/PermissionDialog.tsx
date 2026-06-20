import React from 'react'

interface Props {
  toolCall: {
    id: string
    name: string
    arguments: Record<string, unknown>
  }
  onAllow: () => void
  onDeny: () => void
}

export default function PermissionDialog({ toolCall, onAllow, onDeny }: Props) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Tool Permission Required
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          The agent wants to execute:
        </p>
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 mb-4">
          <p className="font-mono text-sm font-medium text-gray-900 dark:text-white">
            {toolCall.name}
          </p>
          <pre className="mt-2 text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
            {JSON.stringify(toolCall.arguments, null, 2)}
          </pre>
        </div>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onDeny}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600
                       text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Deny
          </button>
          <button
            onClick={onAllow}
            className="px-4 py-2 text-sm rounded-lg bg-blue-500 text-white hover:bg-blue-600"
          >
            Allow
          </button>
        </div>
      </div>
    </div>
  )
}
