import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeAll } from 'vitest'
import App from '../App'

// jsdom doesn't implement scrollIntoView
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

// Mock fetch for config panel
vi.stubGlobal('fetch', vi.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({ agent_max_turns: 50 }),
  })
))

describe('App', () => {
  it('renders the nav bar', () => {
    render(<App />)
    const nav = screen.getByRole('navigation')
    expect(within(nav).getByText('Rubbish')).toBeDefined()
  })

  it('shows chat view by default', () => {
    render(<App />)
    expect(screen.getByText('Chat')).toBeDefined()
  })

  it('switches to settings view', async () => {
    render(<App />)
    const settingsBtn = screen.getByText('Settings')
    fireEvent.click(settingsBtn)
    expect(await screen.findByText('Configuration')).toBeDefined()
  })
})
