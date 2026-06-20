import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import ToolCallCard from '../components/ToolCallCard'

const toolCall = {
  name: 'bash',
  arguments: { command: 'ls -la' },
  result: 'file1.txt\nfile2.txt',
}

describe('ToolCallCard', () => {
  it('renders tool name', () => {
    render(<ToolCallCard toolCall={toolCall} />)
    expect(screen.getByText('bash')).toBeDefined()
  })

  it('expands to show arguments on click', () => {
    render(<ToolCallCard toolCall={toolCall} />)
    fireEvent.click(screen.getByText('bash'))
    expect(screen.getByText(/"command"/)).toBeDefined()
  })

  it('shows result when expanded', () => {
    render(<ToolCallCard toolCall={toolCall} />)
    fireEvent.click(screen.getByText('bash'))
    expect(screen.getByText(/file1.txt/)).toBeDefined()
  })
})
