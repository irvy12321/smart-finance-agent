# Step 7: 系统状态 Dashboard

## 概述

Step 7 完成了系统状态Dashboard的搭建，提供以下功能：

- **实时监控**: 系统状态和性能指标
- **图表展示**: 任务分布和Agent延迟
- **Agent状态**: 各Agent运行状态
- **任务统计**: 任务执行情况
- **性能指标**: 延迟、成功率、吞吐量

## 文件结构

```
frontend/
├── src/
│   ├── pages/
│   │   └── SystemOverview.tsx    # 系统状态页面（已增强）
│   ├── components/
│   │   └── SimpleChart.tsx       # 图表组件
│   └── services/
│       └── api.ts                # API服务
└── ...
```

## 快速开始

### 1. 验证Dashboard

```bash
cd backend
python verify_step7.py
```

### 2. 访问系统状态页面

启动前端后访问: http://localhost:3000/system

## 功能说明

### 1. 系统状态卡片

| 指标 | 说明 | 数据源 |
|------|------|--------|
| Status | 系统运行状态 | `systemApi.getStatus()` |
| Uptime | 系统运行时间 | `systemApi.getStatus()` |
| Total Requests | 总请求数 | `systemApi.getMetrics()` |
| Success Rate | 成功率 | `systemApi.getMetrics()` |

### 2. 图表展示

#### 任务状态分布
- **类型**: 柱状图
- **数据**: 各状态任务数量
- **颜色**: 绿色(完成)、蓝色(运行)、黄色(待定)、红色(失败)

#### Agent延迟
- **类型**: 柱状图
- **数据**: 各Agent平均延迟
- **用途**: 识别性能瓶颈

### 3. Agent状态

显示所有Agent的运行状态：

| Agent | 说明 | 指标 |
|-------|------|------|
| Planner | 任务规划器 | 状态、调用次数、延迟、成功率 |
| Executor | 任务执行器 | 状态、调用次数、延迟、成功率 |
| Reasoner | 推理引擎 | 状态、调用次数、延迟、成功率 |
| Report Agent | 报告生成器 | 状态、调用次数、延迟、成功率 |

### 4. 任务统计

| 统计项 | 说明 |
|--------|------|
| Total | 总任务数 |
| Completed | 已完成任务 |
| Running | 运行中任务 |
| Pending | 待处理任务 |
| Failed | 失败任务 |

### 5. 性能指标

| 指标 | 说明 |
|------|------|
| Avg Latency | 平均延迟 |
| Success Rate | 成功率 |
| Total Tasks | 总任务数 |
| Throughput | 吞吐量 (请求/小时) |

### 6. 最近任务

- 显示最近5个任务
- 包括任务ID、查询、状态、时间
- 点击可查看报告

### 7. 系统配置

显示当前系统配置：
- LLM模型
- Embedding模式
- Temperature
- 功能开关

## API接口

### 系统状态API

```typescript
// 获取系统状态
const status = await systemApi.getStatus()
// 返回: { status, version, uptime, total_requests, success_rate, avg_latency_ms }

// 获取系统指标
const metrics = await systemApi.getMetrics()
// 返回: { total_requests, successful_requests, failed_requests, success_rate, ... }

// 获取Agent状态
const agents = await systemApi.getAgentStatus()
// 返回: { planner: {...}, executor: {...}, reasoner: {...}, report_agent: {...} }

// 获取系统配置
const config = await systemApi.getConfig()
// 返回: { model, embedding, features, version }

// 健康检查
const health = await systemApi.getHealth()
// 返回: { status, timestamp, uptime }
```

### 任务API

```typescript
// 获取任务列表
const tasks = await taskApi.list()
// 返回: { tasks: [{ task_id, query, status, created_at, updated_at }] }

// 获取任务状态
const status = await taskApi.getStatus(taskId)
// 返回: { task_id, status, progress, current_stage, message }
```

## 实时监控

### 自动刷新

```tsx
const [autoRefresh, setAutoRefresh] = useState(false)

useEffect(() => {
  let interval: NodeJS.Timeout | null = null
  if (autoRefresh) {
    interval = setInterval(fetchSystemData, 5000) // 每5秒刷新
  }
  return () => {
    if (interval) clearInterval(interval)
  }
}, [autoRefresh])
```

### 手动刷新

```tsx
<button onClick={fetchSystemData}>
  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
  Refresh
</button>
```

## 使用示例

### 1. 获取系统数据

```tsx
const fetchSystemData = async () => {
  try {
    const [statusRes, metricsRes, agentsRes, tasksRes] = await Promise.all([
      systemApi.getStatus(),
      systemApi.getMetrics(),
      systemApi.getAgentStatus(),
      taskApi.list(),
    ])
    
    setSystemStatus(statusRes)
    setMetrics(metricsRes)
    setAgentStatus(agentsRes)
    setTasks(tasksRes.tasks || [])
  } catch (err) {
    setError(err.message)
  }
}
```

### 2. 显示图表

```tsx
const taskStatusData = [
  { label: 'Completed', value: metrics?.completed_tasks || 0, color: '#10b981' },
  { label: 'Running', value: metrics?.running_tasks || 0, color: '#6366f1' },
  { label: 'Pending', value: metrics?.pending_tasks || 0, color: '#f59e0b' },
  { label: 'Failed', value: metrics?.failed_tasks || 0, color: '#ef4444' },
]

<SimpleChart 
  data={taskStatusData} 
  type="bar" 
  title="Task Status Distribution"
  height={200}
/>
```

### 3. 显示Agent状态

```tsx
{agentStatus && Object.entries(agentStatus).map(([agent, status]) => (
  <div key={agent} className="p-4 bg-dark-bg rounded-lg border border-dark-border">
    <div className="flex items-center gap-2 mb-3">
      <div className={`w-2 h-2 rounded-full ${
        status.status === 'ready' ? 'bg-green-500' : 'bg-yellow-500'
      }`} />
      <h3 className="text-sm font-semibold text-primary-200 capitalize">
        {agent.replace('_', ' ')}
      </h3>
    </div>
    <div className="space-y-2">
      <div className="flex justify-between">
        <span className="text-xs text-primary-400">Status</span>
        <span className="text-xs font-medium text-primary-200">{status.status}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-xs text-primary-400">Calls</span>
        <span className="text-xs font-medium text-primary-200">{status.total_calls}</span>
      </div>
    </div>
  </div>
))}
```

## 样式定制

### 颜色方案

```typescript
const colors = {
  success: '#10b981',  // 绿色
  running: '#6366f1',  // 蓝色
  pending: '#f59e0b',  // 黄色
  failed: '#ef4444',   // 红色
  info: '#06b6d4',     // 青色
}
```

### 卡片样式

```tsx
<div className="card hover:border-primary-500/30 transition-colors">
  {/* 内容 */}
</div>
```

## 性能优化

### 1. 数据缓存

- 使用useState缓存数据
- 避免重复请求
- 使用Promise.all并行请求

### 2. 自动刷新优化

- 仅在页面可见时刷新
- 使用适当的刷新间隔
- 提供手动刷新选项

### 3. 渲染优化

- 使用React.memo优化组件
- 避免不必要的重渲染
- 使用虚拟列表（大量数据）

## 故障排除

### 1. 数据不显示

检查：
- API服务是否正常
- 网络连接是否正常
- 数据格式是否正确

### 2. 图表不渲染

检查：
- 数据数组是否为空
- 数据格式是否正确
- 容器是否有足够高度

### 3. 自动刷新不工作

检查：
- autoRefresh状态是否正确
- interval是否正确设置
- 组件是否正确卸载

## 下一步

Step 7 完成后，可以继续：

- **Step 8**: 配置启动脚本和说明文档

## 参考资料

- [React Hooks](https://react.dev/reference/react/hooks)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Lucide React](https://lucide.dev/)
- [Axios](https://axios-http.com/docs/intro)