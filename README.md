# Smart Finance Agent

[![CI](https://github.com/irvy12321/smart-finance-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/irvy12321/smart-finance-agent/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node.js-20+-green.svg)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 Multi-Agent 架构的智能金融分析平台，使用 FastAPI 后端 + React 前端。

**项目规模**：后端 15k+ / 前端 10k+ 行，51 个 REST 接口，182 个单元测试（后端 137 pytest / 前端 45 Vitest，CI 全绿）；注册 10 个取数 / 分析工具，覆盖行情、财务、新闻、知识库（RAG）、网页爬虫 5 类数据源。

**核心链路**：用户一句自然语言 → Planner 拆解为带依赖的任务 DAG（Kahn 拓扑排序 + 成环拒绝）→ Executor 按拓扑批次 asyncio 并行执行（超时隔离 / 熔断 / 四级降级 / 死锁恢复）→ Reasoner 综合推理（低置信度触发 Self-Critique）→ 输出带数据溯源与可信度标注的研究报告。

> 架构总览、数据流与关键设计取舍见 [`DESIGN.md`](DESIGN.md)；可量化证据见下文「[RAG 检索质量评测](#rag-检索质量评测-rag-retrieval-evaluation)」与「[编排可靠性](#编排可靠性-orchestration-reliability)」两节。

## 功能特性

- **Multi-Agent 架构**: Planner → Executor → Reasoner 协同工作，Reasoner 内置 Self-Critique 自我批评循环（低置信度触发 critique→refine，失败自动降级）
- **RAG 支持**: 基于 FAISS 的向量检索增强生成，含查询多路改写 / HyDE、Cross-Encoder 精排（失败自动降级）与语义切块
- **三层记忆**: 短期滑动窗口+滚动摘要、长期 FAISS 向量记忆（与知识库隔离）、用户画像（规则提取，不调 LLM）
- **Prompt / Context 工程**: Agent prompt 全部 YAML 模板化（Jinja2，缺失降级内置常量）；对话历史确定性压缩；输入/输出双向 token 预算
- **评估体系**: golden dataset + EvalRunner 端到端输出质量评估（含防幻觉数字校验），全确定性计算
- **金融工具**: 股票价格查询、财务报告分析、新闻摘要
- **MCP Server**: 全部 10 个注册工具经 Model Context Protocol（stdio）对外暴露，任何 MCP 客户端（Claude Desktop / Cursor / Agent 运行时）可直接调用，与编排器共用同一套工具注册
- **实时聊天**: AI 金融助手对话界面；金融研究类提问自动持久化为完整研究报告，回复附报告链接可查证执行过程
- **报告生成**: 自动生成结构化金融分析报告
- **数据可视化**: 图表展示和数据可视化
- **系统监控**: Prometheus 指标 + LLM 调用脱敏日志/全量事件持久化 SQLite + OpenTelemetry 链路追踪（开关式，默认 no-op）

## 快速开始

### 前置要求

- **Python**: 3.12+（CI 在 3.12 上验证）
- **Node.js**: 20+
- **npm**: 10+

### 一键启动（Windows）

```bash
# 双击运行 start-all.bat
start-all.bat
```

### 手动启动

#### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 访问应用

- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 用户管理

### 默认账户

系统首次启动时会自动创建默认管理员账户 `admin`。密码取自环境变量 `DEFAULT_ADMIN_PASSWORD`；若未设置，则**随机生成一个一次性强口令并打印到启动日志**（不再使用硬编码弱口令）。

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | `$DEFAULT_ADMIN_PASSWORD`（未设置时为启动日志中的随机口令） | admin |

### 角色权限

| 角色 | 说明 | 权限 |
|------|------|------|
| **admin** | 管理员 | 全部功能（用户管理、系统配置、删除文档） |
| **analyst** | 分析师 | 研究、聊天、工具、知识库（不含用户管理） |
| **viewer** | 查看者 | 仅查看报告和系统状态 |

### 创建用户

#### 方式一：通过 API（推荐）

```bash
# 1. 管理员登录获取 token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<DEFAULT_ADMIN_PASSWORD>"}'

# 2. 创建指定角色用户
curl -X POST http://localhost:8000/api/auth/admin/create-user \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "analyst1", "email": "analyst1@test.com", "password": "Analyst@123", "role": "analyst"}'

# 3. 查看所有用户
curl http://localhost:8000/api/auth/admin/users \
  -H "Authorization: Bearer <admin_token>"
```

#### 方式二：通过数据库

```bash
cd backend
python -c "
import sqlite3, bcrypt
from datetime import datetime
conn = sqlite3.connect('data/chat.db')
now = datetime.now().isoformat()
hashed = bcrypt.hashpw('password123'.encode(), bcrypt.gensalt()).decode()
conn.execute('INSERT INTO users (username, email, hashed_password, is_active, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
    ('analyst1', 'analyst1@test.com', hashed, True, 'analyst', now, now))
conn.commit()
conn.close()
print('Created!')
"
```

### ECS 部署后创建用户

部署到 ECS 后，通过 API 创建用户：

```bash
# 替换为你的域名
curl -X POST https://your-domain.com/api/auth/admin/create-user \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "analyst1", "email": "analyst1@test.com", "password": "Analyst@123", "role": "analyst"}'
```

## 项目结构

```
smart-finance-agent/
├── backend/                    # FastAPI 后端 (唯一后端)
│   ├── app/
│   │   ├── api/               # API 路由（8 个路由文件 / 51 个接口）
│   │   │   ├── auth.py        # 认证 / 用户管理 API（JWT + RBAC）
│   │   │   ├── research.py    # 股票研究主线 API
│   │   │   ├── task.py        # 任务管理 API
│   │   │   ├── report.py      # 报告查询 API
│   │   │   ├── system.py      # 系统状态 API
│   │   │   ├── tools.py       # 工具调用 API
│   │   │   ├── rag.py         # 知识库管理 API
│   │   │   └── chat.py        # 聊天 API (支持 orchestrator 全流水线, 研究结果持久化为报告)
│   │   ├── core/              # 核心业务逻辑
│   │   │   ├── orchestrator.py # 3-Layer 编排器（长期记忆召回 + 事件持久化 + OTel span）
│   │   │   ├── planner.py     # 规划器 Agent（prompt 模板化）
│   │   │   ├── executor.py    # 执行器 Agent
│   │   │   ├── reasoner.py    # 推理器 Agent（Self-Critique 循环）
│   │   │   ├── evaluation.py  # 端到端评估（golden set + 4 指标）
│   │   │   ├── reliability.py # 确定性故障注入评测 harness
│   │   │   ├── memory.py      # 长期记忆（独立 FAISS）+ 用户画像
│   │   │   ├── prompt_manager.py  # YAML prompt 模板加载（Jinja2 + 降级）
│   │   │   ├── context_manager.py # 对话历史压缩
│   │   │   └── llm_call_logger.py # LLM 调用脱敏日志 → SQLite
│   │   ├── rag/               # RAG 模块（含 reranker / query_rewriter / 语义切块 / eval_data 评测集）
│   │   ├── tools/             # 工具模块（10 个注册工具，defaults.py 统一注册）
│   │   ├── mcp_server.py      # MCP Server（stdio 暴露 ToolRegistry 全部工具）
│   │   ├── infrastructure/    # 基础设施 (LLM 客户端、配置、otel.py、smart_router)
│   │   ├── auth/              # JWT / RBAC 依赖
│   │   ├── monitoring/        # Prometheus 指标与中间件
│   │   └── utils/             # 熔断器 / 重试 / 日志 / 异常
│   ├── prompts/               # Agent prompt 模板 (planner/reasoner/report.yaml)
│   ├── data/                  # SQLite 数据 + golden_dataset.json + memory/（长期记忆）
│   ├── scripts/               # 评测脚本（rag_eval.py / reliability_eval.py）
│   ├── tests/                 # 148 个后端单测（pytest）
│   └── requirements.txt       # Python 依赖
│
├── frontend/                   # React 前端 (唯一前端)
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   ├── components/        # UI 组件
│   │   ├── services/          # API 服务
│   │   ├── hooks/             # 自定义 Hooks
│   │   └── test/              # 45 个前端测试（Vitest）
│   ├── package.json           # Node 依赖
│   └── vite.config.ts         # Vite 配置
│
├── .github/                    # CI/CD workflows（lint / test / build / deploy）
├── nginx/                      # Nginx 反代配置
├── _deprecated/                # 旧版代码 (已隔离，不再使用)
├── Dockerfile                  # 后端 Docker 镜像
├── docker-compose.yml          # 开发环境编排
├── docker-compose.prod.yml     # 生产环境编排
├── docker-compose.monitoring.yml # Prometheus/Grafana 监控栈
├── start-all.bat               # Windows 一键启动
└── README.md
```

## API 接口

### 股票研究主线 (Research Copilot)

面向"AI 股票研究助手"的统一入口：输入股票代码，依次执行 **取数 → 规则计算 → 可信度聚合 → LLM 解释**，返回带数据来源与可信度的研究报告。

```http
POST /api/research/{symbol}        # 例: POST /api/research/AAPL (需 Admin/Analyst)
```

返回结构（节选）：

```jsonc
{
  "symbol": "AAPL",
  "data": { "price": { "source": "alpha_vantage", "is_mock": false, ... }, ... },
  "indicators": { "sma_5": ..., "rsi_14": ..., "pe_ratio": ... },  // 纯 Python 计算，数据不足返回 null
  "trust": { "data_confidence": 0.0-1.0, "source_reliability": "high|medium|low", "mock_ratio": 0-1 },
  "report": { "summary": "...", "summary_source": "llm|rule_based", "key_findings": [ ... ] },
  "disclaimer": "For research and educational purposes only — not investment advice. ..."
}
```

设计要点：数据层显式标注 `source/is_mock`；数值只由计算层产生，LLM 仅做解释、禁止编造数字；报告附数据可信度与统一免责声明。

数据兜底策略（`ALLOW_MOCK_DATA`，默认 `true`）：
- **默认（`true`）**：无 key / API 失败 / 免费额度用尽时，自动回退到**带显式标记的模拟数据**（`is_mock=true`、`source="mock"`、`SIMULATED DATA` 警告），并相应降低 `data_confidence`。这样开箱即用、演示永远有数据，且绝不伪装成真实数据。
- **严格模式（`ALLOW_MOCK_DATA=false`）**：取不到真实数据时直接显式报错，不回退模拟数据。

### 任务管理

```http
POST /api/task/create          # 创建任务
POST /api/task/{id}/run        # 执行任务
GET  /api/task/{id}/status     # 查询状态
GET  /api/task/{id}/result     # 获取结果
GET  /api/task/list            # 任务列表
```

### 报告查询

```http
GET /api/report/{id}           # 完整报告
GET /api/report/{id}/summary   # 报告摘要
GET /api/report/{id}/markdown  # Markdown 格式
GET /api/report/{id}/charts    # 图表数据
GET /api/report/{id}/analysis  # 详细分析
```

### 工具调用

```http
POST /api/tools/stock/price        # 股票价格
POST /api/tools/stock/history      # 股票历史
POST /api/tools/financial/report   # 财务报告
POST /api/tools/financial/analysis # 财务分析
POST /api/tools/news/search        # 新闻搜索
POST /api/tools/news/analysis      # 新闻分析
```

### 聊天接口

```http
POST /api/chat/conversations              # 创建会话
POST /api/chat/conversations/{id}/messages # 发送消息 (金融研究类查询自动生成报告, 响应含 report_task_id, 可经 /api/report/{id} 查看)
GET  /api/chat/conversations/{id}         # 会话历史
GET  /api/chat/conversations              # 会话列表
```

### 系统状态

```http
GET /api/system/status         # 系统状态
GET /api/system/metrics        # 系统指标
GET /api/system/agents         # Agent 状态
GET /api/system/config         # 系统配置
GET /api/system/health         # 健康检查
```

## MCP Server (Model Context Protocol)

除 REST API 外，全部 10 个工具也通过 MCP (stdio) 对外暴露（`backend/app/mcp_server.py`），任何 MCP 客户端（Claude Desktop、Cursor、Agent 运行时等）都可直接调用，与编排器共用同一个 `ToolRegistry`（`app/tools/defaults.py` 统一注册）。

```bash
cd backend
python -m app.mcp_server   # 以 stdio 方式启动 MCP server
```

MCP 客户端配置示例（Claude Desktop `mcpServers`）：

```json
{
  "smart-finance-agent": {
    "command": "python",
    "args": ["-m", "app.mcp_server"],
    "cwd": "<repo>/backend"
  }
}
```

- `tools/list` 返回全部工具及各自的 JSON Schema 入参定义（`TOOL_INPUT_SCHEMAS`）
- `tools/call` 路由到对应 `BaseTool.execute()`，`ToolResult`（含 `success/is_mock/source`）序列化为 JSON 返回
- stdio 模式下 stdout 是 JSON-RPC 信道，启动时所有日志自动改路到 stderr，避免污染协议流
- 测试见 `backend/tests/test_mcp_server.py`（内存级 MCP 客户端端到端验证）

## 使用示例

### 1. 创建研究任务

```bash
curl -X POST http://localhost:8000/api/task/create \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze Tesla stock performance in Q4 2024", "priority": 1}'
```

### 2. 查询股票价格

```bash
curl -X POST http://localhost:8000/api/tools/stock/price \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

### 3. 搜索新闻

```bash
curl -X POST http://localhost:8000/api/tools/news/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Tesla earnings", "max_results": 5}'
```

## 配置说明

### 环境变量

在 `backend/.env` 中配置（参考 `backend/.env.example`）：

```bash
# LLM Provider (mimo 或 deepseek)
LLM_PROVIDER=mimo

# MiMo API Key
MIMO_API_KEY=your_mimo_api_key

# DeepSeek API Key (备选)
DEEPSEEK_API_KEY=your_deepseek_api_key

# News API Key (可选)
NEWS_API_KEY=your_news_api_key
```

### 模型配置

在 `backend/app/infrastructure/config.py` 中配置：

```python
class LLMConfig(BaseSettings):
    model: str = ""          # 为空时自动取自 LLM_PROVIDER 对应的 provider 配置
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 300
    max_retries: int = 3
```

## 开发指南

### 后端开发

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python -m uvicorn app.main:app --reload
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 测试

### 运行所有测试

```bash
# Windows (PowerShell)
.\run_tests.ps1

# Windows (CMD)
run_tests.bat
```

### 后端测试 (pytest)

```bash
cd backend

# 运行所有测试
pytest tests/

# 运行测试并生成覆盖率报告
pytest tests/ --cov=app --cov-report=html:coverage/html --cov-report=term-missing

# 运行特定测试文件
pytest tests/test_chat_api.py

# 运行带标记的测试
pytest tests/ -m "not slow"
```

### 前端测试 (Vitest)

```bash
cd frontend

# 运行所有测试
npm test

# 运行测试并监听文件变化
npm run test:watch

# 运行测试并生成覆盖率报告
npm run test:coverage
```

### 测试覆盖率报告

运行测试后，覆盖率报告将生成在以下位置：

- **后端**: `coverage/backend/html/index.html`
- **前端**: `frontend/coverage/index.html`

在浏览器中打开 HTML 文件查看详细的覆盖率报告。

### 测试结构

```
smart-finance-agent/
├── backend/
│   └── tests/                    # 后端测试
│       ├── conftest.py           # 测试配置和 fixtures
│       ├── test_chat_api.py      # 聊天 API 测试
│       ├── test_task_api.py      # 任务 API 测试
│       ├── test_auth_api.py      # 认证 API 测试
│       ├── test_system_api.py    # 系统 API 测试
│       ├── test_orchestrator.py  # Agent 流程测试
│       ├── test_mcp_server.py    # MCP Server 测试（内存 client 端到端）
│       └── test_evaluation_thresholds.py # 评估阈值门禁测试
│
├── frontend/
│   └── src/
│       └── test/                 # 前端测试
│           ├── setup.ts          # 测试配置
│           ├── api.test.ts       # API 服务测试
│           ├── useApi.test.ts    # useApi Hook 测试
│           ├── AuthContext.test.tsx  # Auth Context 测试
│           ├── ErrorBoundary.test.tsx  # ErrorBoundary 测试
│           ├── ProtectedRoute.test.tsx # ProtectedRoute 测试
│           ├── Sidebar.test.tsx  # Sidebar 测试
│           └── StockPriceCard.test.tsx # StockPriceCard 测试
│
├── pytest.ini                    # pytest 配置
└── run_tests.ps1                 # 测试运行脚本
```

## 编排可靠性 (Orchestration Reliability)

编排层有三套真实的容错原语：**降级链**（`FallbackManager`：crawler → news_search → rag_retrieve → 静态兜底）、**熔断器**（`CircuitBreaker`：CLOSED/OPEN/HALF_OPEN 三态）、**死锁恢复**（`ExecutorAgent._try_resolve_deadlock`：上游失败后解锁仅被失败依赖阻塞的下游任务）。

`ExecutorAgent` 进入降级链时会把已经失败、超时或被 OPEN 熔断器短路的原工具加入 `skip_tools`，因此真实执行顺序不会隐式重试原工具：`crawler → news_search → rag_retrieve → static` 中，crawler 已失败后从 news_search 开始；其他三条链同理。每个真实备用步骤先检查自己独立的熔断器，再以单步超时执行，成功或失败只更新自己的熔断状态；static 步骤不使用熔断器。主工具超时由 `TOOL_EXEC_TIMEOUT` 配置，备用步骤超时由 `FALLBACK_STEP_TIMEOUT` 配置，默认均为 30 秒；代码调用方还可通过 `step_timeouts` 为单个备用步骤覆盖超时。

Prometheus 的 `tool_calls_total`、`tool_call_duration_seconds` 和 `tool_errors_total` 按实际调用的主工具或备用工具名记录，`tool_circuit_breaker_state` 按工具分别暴露 CLOSED=0、OPEN=1、HALF_OPEN=2。熔断跳过不会增加调用数，超时与异常仍会记录耗时和错误类型。

为了让这些原语「能用数据说话」，`app/core/reliability.py` 提供了一个**确定性故障注入** harness：用 seeded RNG 让工具按指定概率失败，全程无网络/LLM 调用，结果可复现、可进 CI 断言。运行评测：

```bash
cd backend
PYTHONPATH=. python scripts/reliability_eval.py   # 打印下列曲线并导出 data/reliability_eval/results.json
```

**降级曲线 — 单点故障**（主工具按 p(fail) 失败，备选工具健康；trials=400, seed=42）：

| p(fail) | served | hard_fail | real_recovery | static |
|--------:|-------:|----------:|--------------:|-------:|
| 0.00 | 1.000 | 0.000 | 0.000 | 0.000 |
| 0.25 | 1.000 | 0.000 | 0.260 | 0.000 |
| 0.50 | 1.000 | 0.000 | 0.492 | 0.000 |
| 0.75 | 1.000 | 0.000 | 0.750 | 0.000 |
| 1.00 | 1.000 | 0.000 | 1.000 | 0.000 |

解读：主工具即使 100% 挂掉，**硬失败率始终为 0**——每一次主工具失败都被真实备选工具接住（real_recovery 随 p 线性上升至 1.0）。

**降级曲线 — 级联故障**（主工具与备选工具一起按 p(fail) 退化；trials=400, seed=42）：

| p(fail) | served | hard_fail | real_recovery | static |
|--------:|-------:|----------:|--------------:|-------:|
| 0.00 | 1.000 | 0.000 | 0.000 | 0.000 |
| 0.25 | 1.000 | 0.000 | 0.242 | 0.020 |
| 0.50 | 1.000 | 0.000 | 0.352 | 0.133 |
| 0.75 | 1.000 | 0.000 | 0.270 | 0.430 |
| 1.00 | 1.000 | 0.000 | 0.000 | 1.000 |

解读：当所有工具同时退化（相关性故障），系统沿降级链逐级回落，**最终被静态兜底接住，served 仍保持 1.000**——p=1.0 时全部落到带标注的静态降级，绝不返回空结果。

**熔断保护**（被测工具完全宕机，failure_threshold=5, total_calls=100）：

| total_calls | failure_threshold | invoked | short_circuited | protection_rate |
|------------:|------------------:|--------:|----------------:|----------------:|
| 100 | 5 | 5 | 95 | **95.0%** |

解读：熔断器在 5 次失败后打开，余下 95 次调用被**直接短路**，避免对已宕机工具发起无谓重试（节省 95% 的 doomed 调用）。

生产默认仍保持连续失败阈值 5、恢复等待 60 秒、HALF_OPEN 单次探测 1 次；备用工具使用相同状态机，但状态按工具名隔离。

**死锁恢复**（注入失败的上游依赖，scenarios=50, seed=42）：

| scenarios | recovered | recovery_rate |
|----------:|----------:|--------------:|
| 50 | 50 | **100.0%** |

解读：上游任务失败时，编排器不会整图跳过，而是解锁「仅被该失败依赖阻塞」的下游任务，**100% 的停滞任务图仍能继续推进**。

确定性单测见 `tests/test_reliability.py`（无网络/torch 依赖，可进 CI）。

## RAG 检索质量评测 (RAG Retrieval Evaluation)

检索层明确区分词法表示与真实语义嵌入（见 `backend/app/rag/embed.py`）：

| 模式 | 实现 | 类型 | 用途 |
|------|------|------|------|
| `dev` | `HashEmbedder` | 伪向量/词法 | 快速测试，不表达语义 |
| `prod` | `BM25Embedder` | 词法 | 本地和 CI 默认，不下载模型 |
| `semantic` | [`BAAI/bge-small-zh-v1.5`](https://huggingface.co/BAAI/bge-small-zh-v1.5) | 真实语义 | 中文金融问答生产检索 |

生产模型固定到 revision `7999e1d3359715c523056ef9478215996d62a620`：中文模型、512 维、23,953,920 参数，本机缓存文件约 96.4 MB。查询编码会加官方建议的中文检索指令，文档编码不加。FAISS 的 `config.json` 保存模型、后端、revision、维度、归一化和查询指令组成的 SHA-256 指纹；旧索引或不匹配索引绝不会直接加载，可按 `index_mismatch_policy` 从已持久化 chunk 文本安全重建，或设为 `error` 严格拒绝。

模型选择也做了同体量实测：`bge-small-zh-v1.0` 同为 512 维、约 96.4 MB，在本评估集的 Recall@5/MRR 为 `0.9091/0.8166`，中文改写 MRR 为 `0.8917`；v1.5 分别为 `0.9545/0.8795` 和 `0.9583`，因此选择 v1.5。当前环境无法联网下载新的多语言候选，所以未对未运行的模型填写推测数字；已有 `model2vec/potion` 默认模型也不是中文生产替代品。

### 启用方式

本地和普通 CI 保持 `prod` 词法模式，因此不会安装 PyTorch 或下载模型。要在本地显式运行语义模式：

```powershell
cd backend
python -m pip install -r requirements-semantic.txt
$env:RAG_EMBEDDING_MODE = "semantic"
$env:RAG_EMBEDDING_LOCAL_FILES_ONLY = "true"
$env:RAG_SEMANTIC_FAILURE_POLICY = "error"
```

生产 `backend/Dockerfile` 默认安装语义依赖并在构建期预取固定 revision；运行期设置 `HF_HUB_OFFLINE=1`、`local_files_only=true` 和严格失败策略。模型或依赖缺失会使初始化明确失败。只有显式设置 `RAG_SEMANTIC_FAILURE_POLICY=lexical_fallback` 才会降级 BM25，降级原因会出现在日志、`GET /api/rag/stats` 和 `RAGTool` 的 `retrieval_status` 中。

### 真实评测

评测集为 62 篇金融文档、44 条 gold 查询，其中新增 12 条中文同义/口语改写；指标均为确定性 Python 计算。复现命令：

```powershell
cd backend
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
python scripts/rag_eval.py --local-files-only
```

2026-07-15 在 CPU 上的实际结果：

| Embedder | R@1 | R@3 | R@5 | P@5 | MRR | nDCG@5 |
|----------|-----|-----|-----|-----|-----|--------|
| hash (dev, 伪向量) | 0.1818 | 0.3409 | 0.3864 | 0.0773 | 0.2808 | 0.2938 |
| BM25 (prod, 词法) | 0.5455 | 0.6591 | 0.6818 | 0.1364 | 0.6074 | 0.6210 |
| BGE small zh v1.5 (语义) | **0.8182** | **0.9318** | **0.9545** | **0.1909** | **0.8795** | **0.8987** |

中文改写子集上，BM25 的 Recall@5/MRR 为 `0/0`，BGE 为 `1.0000/0.9583`。这反映当前 BM25 tokenizer 不处理中文词元，而不是把字符匹配称为语义能力。完整原始结果写入 `backend/data/rag_eval/results.json`（gitignored）。

本机 CPU 部署测量：冷进程导入依赖并加载模型 `6.661s`，加载后 RSS `428.8 MB`，完成 32 条批量编码后 RSS `503.9 MB`；单独的热模型构造为 `0.414s`。生产当前配置有两个 Uvicorn worker，最坏需要按约 1 GB 模型进程内存预算评估，且 `sentence-transformers`/CPU PyTorch 会显著增加镜像体积。

### 检索管线增强（查询改写 / 精排 / 语义切块）

在混合检索基础上，检索管线扩展为「**查询改写 → 混合检索 → Cross-Encoder 精排**」：

- **查询改写**（`backend/app/rag/query_rewriter.py`）：LLM 生成多个查询变体做多路检索合并去重；另支持 HyDE（先生成假设文档再用其向量检索）。LLM 不可用时降级单路。
- **精排**（`backend/app/rag/reranker.py`）：`cross-encoder/ms-marco-MiniLM-L-6-v2` 对候选文档精排；模型加载失败自动降级 `NoOpReranker`，绝不影响主流程。开关见 `RAGConfig.reranker_enabled`。
- **语义切块**（`chunker.py` 的 `semantic_chunk`）：按相邻段落 embedding 相似度在语义跳变处断开；无 embedder 时降级 size-based 切块。

## Agent 输出质量评估 (Agent Evaluation)

`backend/app/core/evaluation.py` + `backend/data/golden_dataset.json`（10 个 case：simple 3 / standard 4 / detailed 3）提供端到端输出质量评估，直调 `orchestrator.run()`，对业务代码零侵入：

- 指标：`task_success_rate`、`tool_accuracy`、`retrieval_recall@k`、`answer_groundedness`（回答必须包含 expected 数字、不得出现 forbidden 数字——防幻觉校验）
- 全部为**确定性 Python 计算**，不用 LLM-as-judge，可复现、可进回归
- 验证数据集与导入：`python -m app.core.evaluation --dry-run`
- **回归门禁**：`--min-task-success / --min-tool-accuracy / --min-retrieval-recall / --min-groundedness` 阈值参数，任一聚合指标低于阈值即退出码非 0，CI 可直接卡住 prompt / planner / RAG 回归（见 `.github/workflows/ci.yml` 的 `agent-eval` job，默认只跑 dry-run，配置仓库变量 `AGENT_EVAL_ENABLED=true` + LLM secrets 后启用全量评估）

## 记忆系统 (Memory)

三层记忆（配置见 `MemoryConfig`，`config_memory.yaml` 可覆盖）：

1. **短期**（`rag/memory.py`）：滑动窗口 + 滚动摘要——超窗旧消息折叠进摘要，不直接丢弃
2. **长期**（`core/memory.py`）：FAISS 向量记忆，持久化到 `data/memory/vector_store`（与 RAG 知识库物理隔离）；orchestrator 推理前语义召回注入上下文，报告完成后归档
3. **用户画像**：确定性规则提取（ticker 正则 + 主题关键词，不调 LLM），存 SQLite `user_profiles` 表，注入直接对话 system prompt

所有记忆操作失败只记 warning，不影响主流水线。

## 可观测性 (Observability)

- **Prometheus 指标** + 内存指标（原有）
- **LLM 调用日志**（`core/llm_call_logger.py`）：每次 LLM 调用 prompt/response 脱敏（API key / Bearer token）+ 截断后写 SQLite `llm_call_logs` 表，成功失败都记，带 trace_id；开关 `LLM_CALL_LOG_ENABLED`
- **事件持久化**：EventBus 全量事件写 `event_log` 表，可按 trace_id 回放整条执行链
- **OpenTelemetry**（`infrastructure/otel.py`）：LLM 调用与四个 Agent 主方法均有 span；`OTEL_ENABLED=true` 才启用，未开启或未装 SDK 时全部 no-op

## CI/CD

本项目使用 GitHub Actions 进行持续集成和持续部署。

### 工作流概述

每次 Push 或 Pull Request 到 `main` 或 `develop` 分支时，会自动运行以下检查：

| 阶段 | 前端 | 后端 |
|------|------|------|
| Lint | ESLint | Ruff |
| Test | Vitest | pytest |
| Build | Vite Build | - |
| Coverage | ✅ | ✅ |
| Agent Eval | - | golden set 回归门禁（dry-run 常开；全量评估需 `AGENT_EVAL_ENABLED=true`） |

### 工作流文件

- `.github/workflows/ci.yml` - 主要 CI 工作流
- `.github/dependabot.yml` - 依赖自动更新
- `.github/CODEOWNERS` - 代码所有者
- `.github/pull_request_template.md` - PR 模板
- `.github/ISSUE_TEMPLATE/` - Issue 模板

### 本地运行 CI 检查

在提交代码前，建议本地运行以下检查：

```bash
# Frontend
cd frontend
npm run lint        # Lint 检查
npm test            # 运行测试
npm run build       # 构建检查

# Backend
cd backend
ruff check .        # Lint 检查
ruff format --check .  # 格式检查
pytest tests/       # 运行测试
```

### 覆盖率报告

CI 运行后，覆盖率报告会作为 workflow artifacts 保存。在 PR 中会自动评论覆盖率摘要。

### 依赖更新

Dependabot 会每周一自动检查并创建依赖更新 PR。

## 部署

### ECS 部署 checklist（生产）

> 目标：把代码推到 GitHub 后，在 ECS 上一条命令拉起。镜像构建已在 CI（push 到 `master` 时的 `Docker Build` job）验证可构建。

1. **准备环境变量**：在 ECS 的 `backend/.env` 中填好（这些值绝不进 Git）：

   ```bash
   JWT_SECRET_KEY=<python -c "import secrets;print(secrets.token_urlsafe(64))">
   DEFAULT_ADMIN_PASSWORD=<自定义强口令>
   ENVIRONMENT=production
   CORS_ORIGINS=https://你的域名          # ⚠️ 默认是 localhost，不改前端会被 CORS 拦截
   MIMO_API_KEY=<你的 key>                # 或 DEEPSEEK_API_KEY，二选一
   ALPHA_VANTAGE_API_KEY=<可选，真实股价>
   ALLOW_MOCK_DATA=true                   # 缺真实数据时回退带标记的模拟数据；严格模式设 false
   ```

2. **拉起服务**（在 ECS 项目根目录）：

   ```bash
   git pull
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

3. **验证**：`curl http://localhost:8000/ping` 返回 `{"status":"ok"}`；前端默认经 nginx 暴露在宿主机 80，按 Docker 文档配置 TLS 后再开放 443。

4. **首次创建管理员后**：用上面「ECS 部署后创建用户」的接口添加其它账号，并尽快修改 admin 口令。

### 自动部署到 ECS（CI/CD：push → SSH 送源码 → ECS 构建）

仓库已内置自动部署流水线（`.github/workflows/ci.yml` 的 `deploy` 任务）：**push 到 `master` 且测试全绿后**，自动「在 runner 上打包源码 → SSH 把源码传到 ECS → 在 ECS 上 `docker compose -f docker-compose.prod.yml build` 并重启」。

> 为什么不在 ECS 上 `git pull`？国内阿里云 ECS 通常无法稳定连接 github.com（443 超时），所以这里改为由 GitHub runner 把源码经 SSH 直接送到 ECS（ECS 访问 PyPI/npm/DockerHub 正常，构建不受影响）。构建在 ECS 上以 `nohup` 后台运行，流水线轮询其结果，对构建期间 sshd 短暂卡顿有容错。

该任务默认**休眠**，只有在仓库变量 `DEPLOY_ENABLED=true` 时才运行（没配好凭据前不会让 CI 变红）。启用步骤：

1. **在 GitHub 配置 Secrets**（仓库 Settings → Secrets and variables → Actions → New repository secret，值加密、不进代码、日志自动打码）：

   | Secret | 说明 / 示例 |
   | --- | --- |
   | `ECS_HOST` | ECS 公网 IP 或域名 |
   | `ECS_SSH_USER` | SSH 用户名，如 `root` |
   | `ECS_SSH_PASSWORD` | SSH 登录密码 |
   | `ECS_SSH_PORT` | SSH 端口（可选，默认 22） |
   | `ECS_PROJECT_DIR` | ECS 上仓库路径，如 `/root/smart-finance-agent` |

2. **配置开关变量**：同页 → Variables 标签 → New repository variable → `DEPLOY_ENABLED` = `true`。

3. **ECS 前置条件**（一次性）：已装 Docker + Docker Compose v2；`ECS_PROJECT_DIR` 目录存在且其中有 `docker-compose.prod.yml`（首次可手动 `git clone` 一次，之后流水线会把最新源码覆盖进来，无需 ECS 联网 GitHub）；该目录下存在 `backend/.env`（生产密钥，含 `CORS_ORIGINS` 等，部署不会覆盖它）。

配好后，下一次 push 到 `master`（测试通过）即自动部署：runner 把源码 `tar` 后经 SSH 解包到 `ECS_PROJECT_DIR`（保留 `backend/.env`），再就地 `docker compose build` 并重启。

### Docker 部署（本地）

```bash
# 开发环境 (backend + frontend)
docker-compose up --build

# 生产环境
docker-compose -f docker-compose.prod.yml up --build
```

### 手动部署

```bash
# 后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run build
# 将 dist 目录部署到 Nginx
```

## 故障排除

### 1. 后端启动失败

- 检查 Python 版本 (3.12+)
- 检查依赖是否安装完整
- 检查端口 8000 是否被占用

### 2. 前端启动失败

- 检查 Node.js 版本 (20+)
- 删除 node_modules 重新安装
- 检查端口 3000 是否被占用

### 3. API 调用失败

- 确保后端服务已启动
- 检查 CORS 配置
- 查看浏览器控制台错误信息

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 安装 pre-commit 钩子 (`pip install pre-commit && pre-commit install`)，提交时自动运行 ruff 与基础检查
4. 提交更改 (`git commit -m 'Add feature xxx'`)
5. 推送到分支 (`git push origin feature/xxx`)
6. 创建 Pull Request

## 许可证

MIT License

## 联系方式

- 项目链接: https://github.com/irvy12321/smart-finance-agent
- 问题反馈: https://github.com/irvy12321/smart-finance-agent/issues
