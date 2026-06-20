import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import PermissionDialog from '../components/PermissionDialog'

const mockToolCall = {
  id: 'tc-1',
  name: 'edit',
  arguments: { file_path: '/test.txt', new_str: 'hello' },
}

describe('PermissionDialog', () => {
  it('renders tool name and arguments', () => {
    render(
      <PermissionDialog
        toolCall={mockToolCall}
        onAllow={vi.fn()}
        onDeny={vi.fn()}
      />
    )
    expect(screen.getByText('edit')).toBeDefined()
    expect(screen.getByText(/"file_path"/)).toBeDefined()
  })

  it('calls onAllow when Allow clicked', () => {
    const onAllow = vi.fn()
    const onDeny = vi.fn()
    render(
      <PermissionDialog
        toolCall={mockToolCall}
        onAllow={onAllow}
        onDeny={onDeny}
      />
    )
    fireEvent.click(screen.getByText('Allow'))
    expect(onAllow).toHaveBeenCalled()
    expect(onDeny).not.toHaveBeenCalled()
  })

  it('calls onDeny when Deny clicked', () => {
    const onAllow = vi.fn()
    const onDeny = vi.fn()
    render(
      <PermissionDialog
        toolCall={mockToolCall}
        onAllow={onAllow}
        onDeny={onDeny}
      />
    )
    fireEvent.click(screen.getByText('Deny'))
    expect(onDeny).toHaveBeenCalled()
    expect(onAllow).not.toHaveBeenCalled()
  })
})
