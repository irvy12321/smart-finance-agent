# Smart Finance Agent

[![CI](https://github.com/irvy12321/smart-finance-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/irvy12321/smart-finance-agent/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node.js-20+-green.svg)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 Multi-Agent 架构的智能金融分析平台，使用 FastAPI 后端 + React 前端。

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

- **Python**: 3.8+
- **Node.js**: 16+
- **npm**: 8+

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

### 自动部署到 ECS（CI/CD：push → SSH → ECS）

仓库已内置自动部署流水线（`.github/workflows/ci.yml` 的 `deploy` 任务）：**push 到 `master` 且测试全绿后**，自动「SSH 到 ECS → 拉取最新代码 → `docker compose -f docker-compose.prod.yml up -d --build` 重建并重启」。

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

3. **ECS 前置条件**（一次性）：已装 Docker + Docker Compose v2 + git；已 `git clone` 本仓库到 `ECS_PROJECT_DIR`；该目录下存在 `backend/.env`（生产密钥，含 `CORS_ORIGINS` 等）。

配好后，下一次 push 到 `master`（测试通过）即自动部署。部署用 `git reset --hard origin/master` 保证 ECS 与仓库一致，再就地构建镜像并重启。

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

- 检查 Python 版本 (3.8+)
- 检查依赖是否安装完整
- 检查端口 8000 是否被占用

### 2. 前端启动失败

- 检查 Node.js 版本 (16+)
- 删除 node_modules 重新安装
- 检查端口 3000 是否被占用

### 3. API 调用失败

- 确保后端服务已启动
- 检查 CORS 配置
- 查看浏览器控制台错误信息

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add feature xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

## 许可证

MIT License

## 联系方式

- 项目链接: https://github.com/yourusername/smart-finance-agent
- 问题反馈: https://github.com/yourusername/smart-finance-agent/issues