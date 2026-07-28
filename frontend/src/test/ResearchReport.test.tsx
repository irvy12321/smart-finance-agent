import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getReport: vi.fn(),
}))

vi.mock('../services/api', () => ({
  reportApi: { get: mocks.getReport },
}))

import ResearchReport from '../components/research/ResearchReport'

describe('ResearchReport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not request a report for a task with a terminal error', async () => {
    render(
      <ResearchReport
        symbol="AAPL"
        taskId="interrupted-task"
        isLoading={false}
        errorMessage="Task interrupted. Create a new task."
      />,
    )

    expect(screen.getByText('Task interrupted. Create a new task.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Refresh' })).not.toBeInTheDocument()
    await waitFor(() => expect(mocks.getReport).not.toHaveBeenCalled())
  })
})
