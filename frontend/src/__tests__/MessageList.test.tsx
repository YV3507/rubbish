import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import MessageList from '../components/MessageList'

describe('MessageList', () => {
  it('shows welcome when empty', () => {
    render(<MessageList messages={[]} />)
    expect(screen.getByText('Welcome to Rubbish')).toBeDefined()
  })

  it('renders user messages on the right', () => {
    const messages = [{ id: '1', role: 'user', content: 'hello' }]
    render(<MessageList messages={messages} />)
    expect(screen.getByText('hello')).toBeDefined()
  })

  it('renders assistant messages on the left', () => {
    const messages = [{ id: '2', role: 'assistant', content: 'world' }]
    render(<MessageList messages={messages} />)
    expect(screen.getByText('world')).toBeDefined()
  })
})
