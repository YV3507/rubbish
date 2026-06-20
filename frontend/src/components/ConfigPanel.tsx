import { useEffect, useState, useCallback, ChangeEvent } from 'react'

interface ConfigEntry {
  key: string
  value: string | number | boolean
  type: 'int' | 'float' | 'string' | 'bool'
}

type ConfigDict = Record<string, string | number | boolean>

export default function ConfigPanel() {
  const [config, setConfig] = useState<ConfigEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/config')
      const data: ConfigDict = await res.json()
      const entries: ConfigEntry[] = Object.entries(data).map(([key, value]) => ({
        key,
        value,
        type: typeof value === 'number'
          ? Number.isInteger(value) ? 'int' : 'float'
          : typeof value === 'boolean' ? 'bool' : 'string',
      }))
      setConfig(entries)
    } catch {
      setMessage('Failed to load configuration')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchConfig() }, [fetchConfig])

  const updateValue = (key: string, raw: string) => {
    setConfig((prev: ConfigEntry[]) =>
      prev.map((e: ConfigEntry) => {
        if (e.key !== key) return e
        let value: string | number | boolean = raw
        if (e.type === 'int') value = parseInt(raw) || 0
        else if (e.type === 'float') value = parseFloat(raw) || 0
        else if (e.type === 'bool') value = raw === 'true'
        return { ...e, value }
      })
    )
  }

  const saveConfig = async () => {
    setSaving(true)
    setMessage('')
    const overrides: ConfigDict = {}
    config.forEach((e: ConfigEntry) => { overrides[e.key] = e.value })
    try {
      await fetch('/api/v1/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ overrides }),
      })
      setMessage('Configuration saved!')
    } catch {
      setMessage('Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  const resetConfig = async () => {
    setSaving(true)
    setMessage('')
    try {
      const res = await fetch('/api/v1/config/reset', { method: 'POST' })
      const data: ConfigDict = await res.json()
      const entries: ConfigEntry[] = Object.entries(data).map(([key, value]) => ({
        key,
        value,
        type: typeof value === 'number'
          ? Number.isInteger(value) ? 'int' : 'float'
          : typeof value === 'boolean' ? 'bool' : 'string',
      }))
      setConfig(entries)
      setMessage('Reset to defaults')
    } catch {
      setMessage('Failed to reset configuration')
    } finally {
      setSaving(false)
    }
  }

  const groupLabel = (key: string) => {
    const prefix = key.split('_')[0]
    const labels: Record<string, string> = {
      agent: 'Agent',
      llm: 'LLM / Provider',
      tool: 'Tool Executor',
      session: 'Session / Compactor',
      stormbreaker: 'StormBreaker',
      compute: 'Compute Node',
      frontend: 'Frontend',
    }
    return labels[prefix] || 'General'
  }

  const groupNames = [...new Set(config.map((e: ConfigEntry) => groupLabel(e.key)))]
  const groups: Record<string, ConfigEntry[]> = {}
  for (const label of groupNames) {
    groups[label] = config.filter((e: ConfigEntry) => groupLabel(e.key) === label)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <p className="text-gray-400">Loading configuration...</p>
      </div>
    )
  }

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Configuration
        </h2>
        <div className="flex gap-2">
          <button
            onClick={resetConfig}
            disabled={saving}
            className="px-3 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-gray-600
                       text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Reset
          </button>
          <button
            onClick={saveConfig}
            disabled={saving}
            className="px-3 py-1.5 text-xs rounded-lg bg-blue-500 text-white hover:bg-blue-600
                       disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {message && (
        <div className="mb-4 px-3 py-2 rounded-lg bg-green-50 dark:bg-green-900/30
                        text-sm text-green-700 dark:text-green-300">
          {message}
        </div>
      )}

      {Object.keys(groups).map((group: string) => (
        <div key={group} className="mb-6">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
            {group}
          </h3>
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
            {(groups[group] || []).map((entry: ConfigEntry) => (
              <div key={entry.key} className="flex items-center justify-between px-4 py-2.5">
                <label
                  htmlFor={`cfg-${entry.key}`}
                  className="text-sm font-mono text-gray-700 dark:text-gray-300"
                >
                  {entry.key}
                </label>
                {entry.type === 'bool' ? (
                  <input
                    id={`cfg-${entry.key}`}
                    type="checkbox"
                    checked={!!entry.value}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => updateValue(entry.key, String(e.target.checked))}
                    className="rounded border-gray-300 dark:border-gray-600 text-blue-500
                               focus:ring-blue-500"
                  />
                ) : (
                  <input
                    id={`cfg-${entry.key}`}
                    type={entry.type === 'int' ? 'number' : 'text'}
                    value={String(entry.value)}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => updateValue(entry.key, e.target.value)}
                    className="w-32 text-right text-sm px-2 py-1 rounded border border-gray-300
                               dark:border-gray-600 bg-white dark:bg-gray-700
                               text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
