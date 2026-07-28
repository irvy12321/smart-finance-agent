import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  run: vi.fn(),
  getStatus: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}))

vi.mock('../services/api', () => ({
  taskApi: {
    create: mocks.create,
    run: mocks.run,
    getStatus: mocks.getStatus,
  },
}))

vi.mock('../components/ui/ToastContext', () => ({
  useToast: () => ({ error: mocks.toastError, success: mocks.toastSuccess }),
}))

vi.mock('../components/layout', () => ({
  PageHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('../components/research', () => ({
  StockPool: ({ onSelect }: { onSelect: (symbol: string) => void }) => (
    <button onClick={() => onSelect('AAPL')}>Pick AAPL</button>
  ),
  ResearchReport: ({ isLoading }: { isLoading: boolean }) => (
    <div data-testid="report-state">{isLoading ? 'loading' : 'idle'}</div>
  ),
  AgentExecution: () => <div>Agent execution</div>,
}))

import ResearchCenter from '../pages/ResearchCenter'

describe('ResearchCenter task recovery', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    mocks.create.mockResolvedValue({ task_id: 'task-123' })
    mocks.getStatus.mockResolvedValue({
      task_id: 'task-123',
      status: 'running',
      progress: 10,
      current_stage: 'planning',
      message: 'Planning',
    })
  })

  it('keeps polling when the task start response times out', async () => {
    mocks.run.mockRejectedValue(Object.assign(new Error('timeout'), { code: 'ECONNABORTED' }))
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ResearchCenter />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'Pick AAPL' }))
    await user.click(screen.getByRole('button', { name: 'New Task' }))

    await waitFor(() => expect(mocks.run).toHaveBeenCalledWith('task-123'))
    await waitFor(() => expect(mocks.getStatus).toHaveBeenCalledWith('task-123'))
    expect(screen.getByTestId('report-state')).toHaveTextContent('loading')
    expect(mocks.toastError).not.toHaveBeenCalled()
  })
})
