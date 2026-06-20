import { useState, useRef, ChangeEvent, KeyboardEvent } from 'react'

interface Props {
  onSend: (prompt: string) => void
  disabled?: boolean
}

export default function PromptInput({ onSend, disabled = false }: Props) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    onSend(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex gap-2 items-end">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Type a message..."
        rows={1}
        className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-600 
                   bg-white dark:bg-gray-800 px-3 py-2 text-sm
                   text-gray-900 dark:text-gray-100
                   placeholder-gray-400 dark:placeholder-gray-500
                   focus:outline-none focus:ring-2 focus:ring-blue-500
                   disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <button
        onClick={handleSubmit}
        disabled={!input.trim() || disabled}
        className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm
                   hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {disabled ? 'Thinking...' : 'Send'}
      </button>
    </div>
  )
}
