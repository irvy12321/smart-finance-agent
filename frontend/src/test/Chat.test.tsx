import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Chat from '../pages/Chat'
import { chatApi } from '../services/api'

vi.mock('../services/api', () => ({
  chatApi: {
    createConversation: vi.fn(),
    sendMessage: vi.fn(),
    getHistory: vi.fn(),
    listConversations: vi.fn(),
    deleteConversation: vi.fn(),
  },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 7, username: 'demo', email: 'demo@example.com', role: 'admin', is_active: true },
  }),
}))

const successfulResponse = {
  conversation_id: 'owned-2',
  message: { role: 'assistant' as const, content: 'Recovered response', timestamp: '2026-07-27T14:00:01' },
  response: 'Recovered response',
  sources: [],
  confidence: 0.8,
  timestamp: '2026-07-27T14:00:01',
}

function renderChat() {
  return render(
    <MemoryRouter>
      <Chat />
    </MemoryRouter>
  )
}

describe('Chat conversation ownership recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    vi.mocked(chatApi.listConversations).mockResolvedValue({ conversations: [], total: 0 })
    vi.mocked(chatApi.createConversation).mockResolvedValue({
      conversation_id: 'owned-2',
      created_at: '2026-07-27T14:00:00',
      message: 'created',
    })
    vi.mocked(chatApi.sendMessage).mockResolvedValue(successfulResponse)
    Element.prototype.scrollIntoView = vi.fn()
  })

  it('ignores the legacy unscoped conversation state', async () => {
    localStorage.setItem('chat_state', JSON.stringify({
      conversationId: 'other-user-conversation',
      messages: [{ role: 'assistant', content: 'Other user message', timestamp: '2026-07-27T13:00:00' }],
    }))

    const user = userEvent.setup()
    renderChat()
    expect(screen.queryByText('Other user message')).not.toBeInTheDocument()

    const input = screen.getByPlaceholderText('Type a message...')
    await user.type(input, 'hello{enter}')

    await waitFor(() => {
      expect(chatApi.sendMessage).toHaveBeenCalledWith('owned-2', 'hello')
    })
  })

  it('creates a fresh conversation and retries once after a stale 403', async () => {
    localStorage.setItem('chat_state:7', JSON.stringify({
      conversationId: 'stale-1',
      messages: [],
    }))
    vi.mocked(chatApi.sendMessage)
      .mockRejectedValueOnce({ response: { status: 403 } })
      .mockResolvedValueOnce(successfulResponse)

    const user = userEvent.setup()
    renderChat()
    await user.type(screen.getByPlaceholderText('Type a message...'), 'analyze Tesla{enter}')

    expect(await screen.findByText('Recovered response')).toBeInTheDocument()
    expect(chatApi.sendMessage).toHaveBeenNthCalledWith(1, 'stale-1', 'analyze Tesla')
    expect(chatApi.sendMessage).toHaveBeenNthCalledWith(2, 'owned-2', 'analyze Tesla')
    expect(chatApi.createConversation).toHaveBeenCalledTimes(1)
  })
})
