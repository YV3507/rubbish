import { useState } from 'react'

interface ToolCall {
  name: string
  arguments: Record<string, any>
  result?: string
  status?: 'running' | 'completed' | 'failed'
}

interface Props {
  toolCall: ToolCall
}

const statusStyles: Record<string, { bg: string; dot: string; label: string }> = {
  running: { bg: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700', dot: 'bg-yellow-400 animate-pulse', label: 'Running' },
  completed: { bg: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700', dot: 'bg-green-500', label: 'Done' },
  failed: { bg: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700', dot: 'bg-red-500', label: 'Failed' },
}

const defaultStyle = { bg: 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800', dot: 'bg-gray-400', label: 'Pending' }

export default function ToolCallCard({ toolCall }: Props) {
  const [expanded, setExpanded] = useState(false)
  const style = statusStyles[toolCall.status || ''] || defaultStyle

  return (
    <div className={`border rounded-lg ${style.bg}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
      >
        <span className={`w-2 h-2 rounded-full ${style.dot}`} />
        <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300">
          Tool
        </span>
        <span className="font-mono">{toolCall.name}</span>
        <span className="text-xs text-gray-400 ml-1">{style.label}</span>
        <span className="ml-auto">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="px-3 pb-2 text-xs font-mono text-gray-600 dark:text-gray-400">
          <pre className="whitespace-pre-wrap">
            {JSON.stringify(toolCall.arguments, null, 2)}
          </pre>
          {toolCall.result && (
            <div className="mt-2 border-t border-gray-200 dark:border-gray-700 pt-2">
              <strong>Result:</strong>
              <pre className="whitespace-pre-wrap mt-1">{toolCall.result}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
