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
  ResearchReport: ({ isLoading, errorMessage }: { isLoading: boolean; errorMessage?: string | null }) => (
    <div data-testid="report-state">{errorMessage || (isLoading ? 'loading' : 'idle')}</div>
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

  it('shows the restart interruption instead of treating a saved task as a report', async () => {
    localStorage.setItem('research_center_state', JSON.stringify({
      selectedSymbol: 'AAPL',
      taskId: 'interrupted-task',
      isResearching: false,
      steps: [{ name: 'Planner', status: 'completed', color: 'text-primary-300' }],
      totalDuration: 5200,
      startedAt: Date.now() - 5200,
    }))
    mocks.getStatus.mockResolvedValue({
      task_id: 'interrupted-task',
      status: 'failed',
      progress: 30,
      current_stage: 'interrupted',
      message: 'Task was interrupted by a backend restart.',
    })

    render(
      <MemoryRouter>
        <ResearchCenter />
      </MemoryRouter>,
    )

    await waitFor(() => expect(mocks.getStatus).toHaveBeenCalledWith('interrupted-task'))
    await waitFor(() => expect(screen.getByTestId('report-state')).toHaveTextContent(
      'The task was interrupted by a service restart. Please create a new research task.',
    ))
  })
})
