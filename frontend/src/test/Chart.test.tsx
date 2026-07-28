import { render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

interface MockChartProps {
  data: { datasets: Array<{ backgroundColor: string[] }> }
}

const mocks = vi.hoisted(() => ({
  bar: vi.fn((_props: MockChartProps) => <div data-testid="bar-chart" />),
  line: vi.fn((_props: MockChartProps) => <div data-testid="line-chart" />),
}))

vi.mock('react-chartjs-2', () => ({
  Bar: mocks.bar,
  Line: mocks.line,
}))

import Chart from '../components/Chart'

describe('Chart', () => {
  beforeEach(() => vi.clearAllMocks())

  it('passes visible palette colors to bar charts', () => {
    render(<Chart type="bar" labels={['A', 'B']} values={[10, 20]} title="Test" />)

    const props = mocks.bar.mock.calls[0][0]
    expect(props.data.datasets[0].backgroundColor).toEqual(['#5b9dff', '#10b981'])
    expect(props.data.datasets[0].backgroundColor).not.toContain('rgba(99,102,241,1)88')
  })
})
