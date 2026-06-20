import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import PromptInput from '../components/PromptInput'

describe('PromptInput', () => {
  it('renders textarea and send button', () => {
    render(<PromptInput onSend={vi.fn()} />)
    expect(screen.getByPlaceholderText('Type a message...')).toBeDefined()
    expect(screen.getByText('Send')).toBeDefined()
  })

  it('calls onSend with input value', () => {
    const onSend = vi.fn()
    render(<PromptInput onSend={onSend} />)

    const textarea = screen.getByPlaceholderText('Type a message...')
    fireEvent.change(textarea, { target: { value: 'test prompt' } })
    fireEvent.click(screen.getByText('Send'))

    expect(onSend).toHaveBeenCalledWith('test prompt')
  })

  it('does not call onSend with empty input', () => {
    const onSend = vi.fn()
    render(<PromptInput onSend={onSend} />)
    fireEvent.click(screen.getByText('Send'))
    expect(onSend).not.toHaveBeenCalled()
  })

  it('clear input after send', () => {
    const onSend = vi.fn()
    render(<PromptInput onSend={onSend} />)

    const textarea = screen.getByPlaceholderText('Type a message...') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'prompt' } })
    fireEvent.click(screen.getByText('Send'))

    expect(textarea.value).toBe('')
  })
})
