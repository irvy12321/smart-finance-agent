# Smart Finance Agent

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

## 部署

### Docker 部署

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