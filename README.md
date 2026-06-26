# Smart Finance Agent

[![CI](https://github.com/irvy12321/smart-finance-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/irvy12321/smart-finance-agent/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node.js-20+-green.svg)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 Multi-Agent 架构的智能金融分析平台，使用 FastAPI 后端 + React 前端。

> 架构总览、数据流与关键设计取舍见 [`DESIGN.md`](DESIGN.md)；可量化证据见下文「[RAG 检索质量评测](#rag-检索质量评测-rag-retrieval-evaluation)」与「[编排可靠性](#编排可靠性-orchestration-reliability)」两节。

## 功能特性

- **Multi-Agent 架构**: Planner → Executor → Reasoner 协同工作
- **RAG 支持**: 基于 FAISS 的向量检索增强生成
- **金融工具**: 股票价格查询、财务报告分析、新闻摘要
- **实时聊天**: AI 金融助手对话界面
- **报告生成**: 自动生成结构化金融分析报告
- **数据可视化**: 图表展示和数据可视化
- **系统监控**: 实时系统状态和性能指标

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
│   │   ├── api/               # API 路由
│   │   │   ├── task.py        # 任务管理 API
│   │   │   ├── report.py      # 报告查询 API
│   │   │   ├── system.py      # 系统状态 API
│   │   │   ├── tools.py       # 工具调用 API
│   │   │   └── chat.py        # 聊天 API (支持 orchestrator 全流水线)
│   │   ├── core/              # 核心业务逻辑
│   │   │   ├── orchestrator.py # 3-Layer 编排器
│   │   │   ├── planner.py     # 规划器 Agent
│   │   │   ├── executor.py    # 执行器 Agent
│   │   │   └── reasoner.py    # 推理器 Agent
│   │   ├── rag/               # RAG 模块
│   │   ├── tools/             # 工具模块
│   │   ├── infrastructure/    # 基础设施 (LLM 客户端、配置)
│   │   └── utils/             # 工具函数
│   ├── data/                  # SQLite 数据
│   └── requirements.txt       # Python 依赖
│
├── frontend/                   # React 前端 (唯一前端)
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   ├── components/        # UI 组件
│   │   ├── services/          # API 服务
│   │   └── hooks/             # 自定义 Hooks
│   ├── package.json           # Node 依赖
│   └── vite.config.ts         # Vite 配置
│
├── _deprecated/                # 旧版代码 (已隔离，不再使用)
├── Dockerfile                  # 后端 Docker 镜像
├── docker-compose.yml          # 开发环境编排
├── docker-compose.prod.yml     # 生产环境编排
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
POST /api/chat/conversations/{id}/messages # 发送消息
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
    model: str = "openai/mimo-v2.5-pro"
    temperature: float = 0.3
    max_tokens: int = 4096
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
│       └── test_orchestrator.py  # Agent 流程测试
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

**死锁恢复**（注入失败的上游依赖，scenarios=50, seed=42）：

| scenarios | recovered | recovery_rate |
|----------:|----------:|--------------:|
| 50 | 50 | **100.0%** |

解读：上游任务失败时，编排器不会整图跳过，而是解锁「仅被该失败依赖阻塞」的下游任务，**100% 的停滞任务图仍能继续推进**。

确定性单测见 `tests/test_reliability.py`（无网络/torch 依赖，可进 CI）。

## RAG 检索质量评测 (RAG Retrieval Evaluation)

检索层提供三种 embedder（见 `backend/app/rag/embed.py`）：

| 模式 | 类 | 类型 | 说明 |
|------|-----|------|------|
| `dev` | `HashEmbedder` | 词法 | MD5 伪向量，无语义，仅用于本地快测 |
| `prod` | `BM25Embedder` | 词法 | BM25 / TF-IDF（词 + 字符 n-gram），靠 token 重叠 |
| `semantic` | `SemanticEmbedder` | **语义** | 真实稠密向量（`sentence-transformers`，或免 torch 的 `model2vec` 静态向量），按语义匹配 |

`SemanticEmbedder` 是**可选依赖**：未安装任一后端时构造会抛出带安装提示的 `ImportError`，词法模式不受影响、CI 也不依赖它。

### 评测集与指标

- 评测语料：`backend/app/rag/eval_data/`（`corpus.json` + `queries.json`），50 篇金融知识文档 + 32 条带 gold 标注的查询；查询按 `lexical`（与文档共享词汇）/`semantic`（改写、词汇重叠低）分类，便于公平对比词法 vs 语义检索。
- 指标实现：`backend/app/rag/eval.py` —— `Recall@k`、`Precision@k`、`MRR`、`nDCG@k`（macro 平均）。

### 运行评测

```bash
cd backend
# 仅词法（无需额外依赖）
python scripts/rag_eval.py --no-semantic
# 含语义后端（推荐免 torch 的 model2vec）
pip install model2vec
python scripts/rag_eval.py
```

### 实测结果（50 文档 / 32 查询）

| Embedder | R@1 | R@3 | R@5 | P@5 | MRR | nDCG@5 |
|----------|-----|-----|-----|-----|-----|--------|
| hash (dev, 词法) | 0.250 | 0.500 | 0.562 | 0.113 | 0.391 | 0.420 |
| bm25 (prod, 词法) | 0.750 | 0.906 | 0.938 | 0.188 | 0.834 | 0.854 |
| semantic (model2vec) | **0.844** | **1.000** | **1.000** | **0.200** | **0.917** | **0.938** |

按查询类型拆分（Recall@5 / MRR）——语义检索在「改写型」查询上的优势最明显：

| Embedder | lexical 查询 | semantic 查询 |
|----------|-------------|---------------|
| hash | 0.667 / 0.481 | 0.522 / 0.356 |
| bm25 | 0.889 / 0.849 | 0.957 / 0.829 |
| semantic | 1.000 / 0.944 | 1.000 / 0.906 |

结论：BM25 相对 hash 基线在 Recall@5 上 +0.376、MRR +0.443；语义向量再把改写型查询的 Recall@5 从 0.957 提到 1.000，验证了「词法 → 语义」升级路径的实际收益。指标计算正确性与「BM25 > hash」基线由 `backend/tests/test_rag_eval.py` 守护（确定性、不依赖 torch，纳入 CI）。

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

3. **验证**：`curl http://localhost:8000/ping` 返回 `{"status":"ok"}`；前端经 nginx 暴露在 80/443。

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
