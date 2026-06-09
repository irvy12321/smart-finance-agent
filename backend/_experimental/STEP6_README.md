# Step 6: 报告展示页面

## 概述

Step 6 完成了报告展示页面的增强，添加了图表展示功能：

- **SimpleChart**: 通用图表组件
- **图表类型**: 柱状图、折线图
- **交互特性**: 悬停高亮、数值显示
- **响应式设计**: 自适应布局

## 文件结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── SimpleChart.tsx      # 图表组件
│   │   └── ReportPanel.tsx      # 报前面板（已更新）
│   └── pages/
│       └── Report.tsx           # 报告页面
└── ...
```

## 快速开始

### 1. 验证组件

```bash
cd backend
python verify_step6.py
```

### 2. 使用图表组件

```tsx
import SimpleChart from '../components/SimpleChart'

function MyComponent() {
  const data = [
    { label: 'Jan', value: 1200 },
    { label: 'Feb', value: 1800 },
    { label: 'Mar', value: 1500 },
  ]

  return (
    <SimpleChart 
      data={data} 
      type="bar" 
      title="Monthly Revenue" 
    />
  )
}
```

## 组件说明

### SimpleChart组件

**文件**: `src/components/SimpleChart.tsx`

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `data` | `DataPoint[]` | - | 数据点数组 |
| `type` | `'bar' \| 'line'` | `'bar'` | 图表类型 |
| `title` | `string` | - | 图表标题 |
| `height` | `number` | `200` | 图表高度 |
| `showLabels` | `boolean` | `true` | 显示标签 |
| `showValues` | `boolean` | `true` | 显示数值 |

#### DataPoint接口

```typescript
interface DataPoint {
  label: string      // 标签
  value: number      // 数值
  color?: string     // 可选颜色
}
```

#### 使用示例

```tsx
import SimpleChart from '../components/SimpleChart'

// 柱状图
<SimpleChart
  data={[
    { label: 'AAPL', value: 182.52 },
    { label: 'TSLA', value: 248.42 },
    { label: 'GOOGL', value: 141.80 },
  ]}
  type="bar"
  title="Stock Prices"
  height={250}
/>

// 折线图
<SimpleChart
  data={[
    { label: 'Week 1', value: 150 },
    { label: 'Week 2', value: 180 },
    { label: 'Week 3', value: 165 },
    { label: 'Week 4', value: 210 },
  ]}
  type="line"
  title="Weekly Trend"
  showValues={false}
/>

// 自定义颜色
<SimpleChart
  data={[
    { label: 'Success', value: 85, color: '#10b981' },
    { label: 'Failed', value: 15, color: '#ef4444' },
  ]}
  type="bar"
  title="Task Status"
/>
```

### ReportPanel组件

**文件**: `src/components/ReportPanel.tsx`

#### 新增功能

- 集成SimpleChart组件
- 支持chart_specs数据
- 数据可视化区域

#### Props

```typescript
interface ReportPanelProps {
  report: {
    report_title?: string
    summary?: string
    key_findings?: string[]
    risk_factors?: Array<{ factor: string; severity: string; description: string }>
    market_trends?: string[]
    recommendations?: string[]
    confidence?: number
    total_tasks?: number
    success_tasks?: number
    failed_tasks?: number
    elapsed?: number
    chart_specs?: Array<{
      chart_type: string
      title: string
      x_label: string
      y_label: string
      data: Array<{ label: string; value: number }>
    }>
  } | null
  loading?: boolean
}
```

#### 使用示例

```tsx
import ReportPanel from '../components/ReportPanel'

function ReportPage() {
  const [report, setReport] = useState(null)

  return <ReportPanel report={report} loading={false} />
}
```

## 图表类型

### 1. 柱状图 (Bar Chart)

**适用场景**:
- 比较不同类别的数据
- 展示数据分布
- 显示排名

**示例**:
```tsx
const data = [
  { label: 'AAPL', value: 182.52 },
  { label: 'TSLA', value: 248.42 },
  { label: 'GOOGL', value: 141.80 },
  { label: 'MSFT', value: 378.91 },
]

<SimpleChart data={data} type="bar" title="Stock Prices" />
```

### 2. 折线图 (Line Chart)

**适用场景**:
- 展示趋势变化
- 时间序列数据
- 连续数据可视化

**示例**:
```tsx
const data = [
  { label: 'Jan', value: 1200 },
  { label: 'Feb', value: 1800 },
  { label: 'Mar', value: 1500 },
  { label: 'Apr', value: 2200 },
  { label: 'May', value: 1900 },
  { label: 'Jun', value: 2500 },
]

<SimpleChart data={data} type="line" title="Revenue Trend" />
```

## 交互特性

### 1. 悬停效果

- 高亮当前数据点
- 显示详细数值
- 颜色变化反馈

### 2. 数值显示

- 柱状图顶部显示数值
- 折线图悬停显示数值
- 支持自定义格式

### 3. 标签显示

- X轴类别标签
- 支持长文本截断
- 响应式布局

## 样式定制

### 颜色方案

```typescript
const defaultColors = [
  '#6366f1', // primary
  '#10b981', // green
  '#f59e0b', // yellow
  '#ef4444', // red
  '#8b5cf6', // purple
  '#06b6d4', // cyan
  '#f97316', // orange
  '#ec4899', // pink
]
```

### 自定义颜色

```tsx
const data = [
  { label: 'Success', value: 85, color: '#10b981' },
  { label: 'Warning', value: 10, color: '#f59e0b' },
  { label: 'Error', value: 5, color: '#ef4444' },
]

<SimpleChart data={data} type="bar" />
```

## 集成示例

### 1. 在Report页面中使用

```tsx
import ReportPanel from '../components/ReportPanel'
import { reportApi } from '../services/api'

function ReportPage({ taskId }) {
  const [report, setReport] = useState(null)

  useEffect(() => {
    const fetchReport = async () => {
      const data = await reportApi.get(taskId)
      setReport(data)
    }
    fetchReport()
  }, [taskId])

  return <ReportPanel report={report} />
}
```

### 2. 在Dashboard中使用

```tsx
import SimpleChart from '../components/SimpleChart'

function Dashboard() {
  const taskData = [
    { label: 'Completed', value: 15 },
    { label: 'Running', value: 3 },
    { label: 'Pending', value: 5 },
    { label: 'Failed', value: 2 },
  ]

  return (
    <div>
      <h2>Task Statistics</h2>
      <SimpleChart data={taskData} type="bar" />
    </div>
  )
}
```

### 3. 在StockPriceCard中使用

```tsx
import SimpleChart from '../components/SimpleChart'
import { toolsApi } from '../services/api'

function StockChart({ symbol }) {
  const [history, setHistory] = useState([])

  useEffect(() => {
    const fetchHistory = async () => {
      const data = await toolsApi.getStockHistory(symbol, '1m')
      setHistory(data.history.map(item => ({
        label: item.date.slice(5),
        value: item.close,
      })))
    }
    fetchHistory()
  }, [symbol])

  return (
    <SimpleChart 
      data={history} 
      type="line" 
      title={`${symbol} Price History`}
    />
  )
}
```

## 性能优化

### 1. 数据点限制

- 建议不超过50个数据点
- 大数据集可进行采样
- 使用分页或滚动加载

### 2. 渲染优化

- 使用CSS transforms
- 避免频繁重绘
- 使用requestAnimationFrame

### 3. 内存优化

- 及时清理事件监听器
- 避免内存泄漏
- 使用虚拟滚动（大量数据）

## 故障排除

### 1. 图表不显示

检查：
- data数组是否为空
- 数据格式是否正确
- 容器是否有足够高度

### 2. 数值显示异常

检查：
- value是否为有效数字
- 是否超出显示范围
- 格式化函数是否正确

### 3. 交互不工作

检查：
- 事件监听器是否正确绑定
- 状态更新是否正常
- CSS样式是否冲突

## 下一步

Step 6 完成后，可以继续：

- **Step 7**: 系统状态Dashboard
- **Step 8**: 配置启动脚本和说明文档

## 参考资料

- [SVG 文档](https://developer.mozilla.org/en-US/docs/Web/SVG)
- [CSS Transforms](https://developer.mozilla.org/en-US/docs/Web/CSS/transform)
- [React Hooks](https://react.dev/reference/react/hooks)
- [Tailwind CSS](https://tailwindcss.com/docs)