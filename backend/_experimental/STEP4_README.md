# Step 4: API 接口封装

## 概述

Step 4 完成了API接口的封装，提供以下功能：

- **Task API**: 任务管理
- **Report API**: 报告查询
- **System API**: 系统状态
- **Tools API**: 工具调用
- **Chat API**: 聊天接口

## 文件结构

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── task.py       # 任务API
│   │   ├── report.py     # 报告API
│   │   ├── system.py     # 系统API
│   │   ├── tools.py      # 工具API
│   │   └── chat.py       # 聊天API
│   └── main.py           # FastAPI应用入口
├── verify_step4.py       # 验证脚本
├── demo_step4.py         # 演示脚本
└── STEP4_README.md       # 本文档
```

## 快速开始

### 1. 启动后端服务

```bash
cd backend
python -m app.main
```

### 2. 访问API文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. 验证API接口

```bash
python verify_step4.py
```

### 4. 运行API演示

```bash
python demo_step4.py
```

## API接口详细说明

### 1. Task API

#### 创建任务
```http
POST /api/task/create
Content-Type: application/json

{
  "query": "Analyze Tesla stock performance in Q4 2024",
  "priority": 1
}
```

**响应**:
```json
{
  "task_id": "abc12345",
  "status": "pending",
  "message": "Task created successfully. Use /api/task/abc12345/run to start execution."
}
```

#### 执行任务
```http
POST /api/task/{task_id}/run
```

**响应**:
```json
{
  "message": "Task execution started",
  "task_id": "abc12345"
}
```

#### 查询状态
```http
GET /api/task/{task_id}/status
```

**响应**:
```json
{
  "task_id": "abc12345",
  "status": "running",
  "progress": 45.0,
  "current_stage": "executing",
  "message": "Task is running"
}
```

#### 获取结果
```http
GET /api/task/{task_id}/result
```

**响应**:
```json
{
  "task_id": "abc12345",
  "status": "completed",
  "query": "Analyze Tesla stock performance in Q4 2024",
  "answer": "...",
  "report_markdown": "...",
  "summary": "...",
  "key_findings": [...],
  "confidence": 0.85
}
```

#### 任务列表
```http
GET /api/task/list
```

**响应**:
```json
{
  "tasks": [
    {
      "task_id": "abc12345",
      "query": "Analyze Tesla stock performance",
      "status": "completed",
      "created_at": "2025-01-25T12:00:00",
      "updated_at": "2025-01-25T12:05:00"
    }
  ]
}
```

### 2. Report API

#### 完整报告
```http
GET /api/report/{task_id}
```

#### 报告摘要
```http
GET /api/report/{task_id}/summary
```

#### Markdown格式
```http
GET /api/report/{task_id}/markdown
```

#### 图表数据
```http
GET /api/report/{task_id}/charts
```

#### 详细分析
```http
GET /api/report/{task_id}/analysis
```

#### 数据来源
```http
GET /api/report/{task_id}/sources
```

#### 执行过程
```http
GET /api/report/{task_id}/process
```

### 3. System API

#### 系统状态
```http
GET /api/system/status
```

**响应**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600.0,
  "total_requests": 100,
  "success_rate": 99.0,
  "avg_latency_ms": 150.0,
  "timestamp": "2025-01-25T12:00:00"
}
```

#### 系统指标
```http
GET /api/system/metrics
```

#### Agent状态
```http
GET /api/system/agents
```

#### 系统配置
```http
GET /api/system/config
```

#### 健康检查
```http
GET /api/system/health
```

#### 版本信息
```http
GET /api/system/version
```

### 4. Tools API

#### 工具列表
```http
GET /api/tools/list
```

**响应**:
```json
{
  "tools": [
    {"name": "stock_price", "description": "Queries real-time stock price"},
    {"name": "financial_report", "description": "Retrieves financial report"}
  ],
  "total": 9
}
```

#### 股票价格查询
```http
POST /api/tools/stock/price
Content-Type: application/json

{
  "symbol": "AAPL"
}
```

**响应**:
```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "price": 182.52,
  "change": 1.25,
  "change_percent": 0.69,
  "volume": 52345678,
  "market_cap": 2.85e12,
  "pe_ratio": 28.5,
  "high_52w": 199.62,
  "low_52w": 124.17,
  "timestamp": "2025-01-25T12:00:00",
  "source": "mock_data"
}
```

#### 股票历史数据
```http
POST /api/tools/stock/history
Content-Type: application/json

{
  "symbol": "TSLA",
  "period": "1m"
}
```

#### 财务报告查询
```http
POST /api/tools/financial/report
Content-Type: application/json

{
  "symbol": "TSLA",
  "report_type": "summary"
}
```

#### 财务分析
```http
POST /api/tools/financial/analysis
Content-Type: application/json

{
  "symbol": "AAPL",
  "analysis_type": "comprehensive"
}
```

#### 新闻搜索
```http
POST /api/tools/news/search
Content-Type: application/json

{
  "query": "Tesla",
  "max_results": 5
}
```

#### 新闻分析
```http
POST /api/tools/news/analysis
Content-Type: application/json

{
  "query": "Tesla",
  "period": "7d"
}
```

### 5. Chat API

#### 创建会话
```http
POST /api/chat/conversations
```

**响应**:
```json
{
  "conversation_id": "conv12345",
  "created_at": "2025-01-25T12:00:00",
  "message": "Conversation created successfully"
}
```

#### 发送消息
```http
POST /api/chat/conversations/{conversation_id}/messages
Content-Type: application/json

{
  "message": "What is the stock price of Apple?"
}
```

**响应**:
```json
{
  "conversation_id": "conv12345",
  "message": {
    "role": "assistant",
    "content": "I can help you with stock information...",
    "timestamp": "2025-01-25T12:00:01"
  },
  "response": "I can help you with stock information...",
  "sources": [],
  "confidence": 0.85,
  "timestamp": "2025-01-25T12:00:01"
}
```

#### 会话历史
```http
GET /api/chat/conversations/{conversation_id}
```

#### 会话列表
```http
GET /api/chat/conversations
```

#### 删除会话
```http
DELETE /api/chat/conversations/{conversation_id}
```

## 使用示例

### Python示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 创建任务
response = requests.post(
    f"{BASE_URL}/api/task/create",
    json={"query": "Analyze Tesla stock", "priority": 1}
)
task_id = response.json()["task_id"]

# 执行任务
requests.post(f"{BASE_URL}/api/task/{task_id}/run")

# 查询状态
status = requests.get(f"{BASE_URL}/api/task/{task_id}/status").json()
print(f"Status: {status['status']}, Progress: {status['progress']}%")

# 获取结果
result = requests.get(f"{BASE_URL}/api/task/{task_id}/result").json()
print(f"Answer: {result['answer'][:100]}...")
```

### cURL示例

```bash
# 创建任务
curl -X POST http://localhost:8000/api/task/create \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze Tesla stock", "priority": 1}'

# 查询股票价格
curl -X POST http://localhost:8000/api/tools/stock/price \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'

# 搜索新闻
curl -X POST http://localhost:8000/api/tools/news/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Tesla", "max_results": 5}'
```

## 配置说明

### CORS配置

在 `app/main.py` 中配置CORS：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API文档配置

```python
app = FastAPI(
    title="Smart Finance Agent API",
    description="AI-powered financial research and analysis platform",
    version="1.0.0",
)
```

## 下一步

Step 4 完成后，可以继续：

- **Step 5**: 前端 Chat 页面开发
- **Step 6**: 报告展示页面
- **Step 7**: 系统状态 Dashboard

## 参考资料

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [OpenAPI 规范](https://swagger.io/specification/)