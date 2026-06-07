# Step 1: 后端 Orchestrator + Planner + Executor + Reasoner 基础框架

## 概述

Step 1 完成了后端核心架构的搭建，包括：

- **Orchestrator**: 3层架构的多Agent协同调度器
- **PlannerAgent**: 任务规划器，将用户查询分解为可执行的子任务
- **ExecutorAgent**: 任务执行器，支持并行执行和容错
- **Reasoner**: 推理引擎，提供多步推理和图表规格生成

## 架构说明

```
用户查询
    ↓
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Planner   │→ │   Executor  │→ │   Reasoner  │    │
│  │  (Layer 1)  │  │  (Layer 2)  │  │  (Layer 3)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
    ↓
  结果输出
```

### Layer 1: Planner (任务规划)
- 分析用户查询的复杂度
- 选择合适的工具和策略
- 生成子任务计划（Plan）

### Layer 2: Executor (任务执行)
- 按依赖关系并行执行子任务
- 支持容错和降级
- 收集执行结果

### Layer 3: Reasoner (推理分析)
- 对执行结果进行多步推理
- 生成关键洞察和图表规格
- 输出置信度评估

## 文件结构

```
backend/
├── app/
│   ├── core/
│   │   ├── orchestrator.py      # Orchestrator 主类
│   │   ├── planner.py           # PlannerAgent 实现
│   │   ├── executor.py          # ExecutorAgent 实现
│   │   ├── reasoner.py          # Reasoner 实现
│   │   ├── agent_status.py      # Agent 状态管理
│   │   ├── report_agent.py      # 报告生成器
│   │   ├── chart_renderer.py    # 图表渲染器
│   │   └── fallback_manager.py  # 降级管理器
│   ├── infrastructure/
│   │   ├── llm_client.py        # LLM 客户端
│   │   ├── smart_router.py      # 智能路由器
│   │   └── config.py            # 配置管理
│   ├── tools/
│   │   ├── registry.py          # 工具注册表
│   │   ├── crawler_tool.py      # 爬虫工具
│   │   ├── news_tool.py         # 新闻搜索工具
│   │   └── rag_tool.py          # RAG 工具
│   ├── utils/
│   │   ├── logger.py            # 日志工具
│   │   ├── tracing.py           # 追踪工具
│   │   └── exceptions.py        # 自定义异常
│   └── main.py                  # FastAPI 应用入口
├── verify_step1.py              # 验证脚本
├── demo_step1.py                # 演示脚本
└── .env                         # 环境变量配置
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并配置 API 密钥：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

### 3. 运行验证脚本

```bash
python verify_step1.py
```

这个脚本会测试：
- 模块导入
- 组件初始化
- 数据结构
- 工具注册表

### 4. 运行演示脚本

```bash
python demo_step1.py
```

这个脚本会执行一个完整的任务流程，展示：
- Orchestrator 初始化
- 任务规划和执行
- 推理和报告生成

### 5. 启动 API 服务

```bash
python -m app.main
```

服务将在 `http://localhost:8000` 启动，可以访问：
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/ping

## API 接口

### 创建任务

```http
POST /api/task/create
Content-Type: application/json

{
  "query": "Analyze the current market trend for tech stocks",
  "priority": 1
}
```

### 运行任务

```http
POST /api/task/{task_id}/run
```

### 查询任务状态

```http
GET /api/task/{task_id}/status
```

### 获取任务结果

```http
GET /api/task/{task_id}/result
```

### 获取报告

```http
GET /api/report/{task_id}
```

## 核心类说明

### Orchestrator

```python
from app.core.orchestrator import Orchestrator

# 初始化
orchestrator = Orchestrator(use_router=False)

# 运行任务（同步）
result = await orchestrator.run("your query")

# 运行任务（流式）
async for event in orchestrator.run_with_streaming("your query"):
    print(event)
```

### Plan 和 SubTask

```python
from app.core.planner import Plan, SubTask

# 创建子任务
subtask = SubTask(
    task_id="task_1",
    tool_name="news_search",
    params={"query": "Tesla earnings"},
    description="Search for Tesla earnings news",
    priority=1,
    confidence=0.8
)

# 创建计划
plan = Plan(
    original_query="Analyze Tesla",
    subtasks=[subtask],
    reasoning="Plan reasoning..."
)
```

### ReasoningResult

```python
from app.core.reasoner import ReasoningResult, ChartSpec

# 创建推理结果
result = ReasoningResult(
    reasoning="Step-by-step analysis...",
    critique="Uncertainty analysis...",
    confidence=0.85,
    key_insights=["Insight 1", "Insight 2"],
    chart_specs=[
        ChartSpec(
            chart_type="bar",
            title="Stock Performance",
            x_label="Company",
            y_label="Return (%)",
            data=[{"label": "AAPL", "value": 15}, {"label": "GOOGL", "value": 12}]
        )
    ]
)
```

## 下一步

Step 1 完成后，可以继续：

- **Step 2**: 搭建 RAG 模块，支持 embedding + FAISS
- **Step 3**: 搭建工具（股票价格查询、财务报告分析、新闻摘要）
- **Step 4**: 封装完整的 API 接口
- **Step 5**: 前端 Chat 页面开发

## 注意事项

1. 需要有效的 LLM API 密钥才能运行完整的任务流程
2. 验证脚本（verify_step1.py）不需要 API 密钥，可以用于测试基础架构
3. 所有组件都支持异步操作，适合高并发场景