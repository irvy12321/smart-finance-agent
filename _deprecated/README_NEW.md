# Smart Finance Agent - 前后端分离版本

## 项目结构

```
smart-finance-agent/
├── backend/                    # FastAPI后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI应用入口
│   │   ├── api/               # API路由
│   │   ├── core/              # 核心业务逻辑
│   │   ├── rag/               # RAG逻辑
│   │   ├── tools/             # 工具实现
│   │   ├── utils/             # 工具函数
│   │   └── infrastructure/    # 基础设施
│   └── requirements.txt
├── frontend/                  # React前端
│   ├── src/
│   │   ├── components/        # React组件
│   │   ├── pages/             # 页面组件
│   │   ├── services/          # API服务
│   │   ├── hooks/             # 自定义hooks
│   │   └── utils/             # 前端工具函数
│   └── package.json
├── start-backend.bat          # 后端启动脚本
├── start-frontend.bat         # 前端启动脚本
└── README.md
```

## 快速开始

### 1. 启动后端服务器

```bash
# 方式一：使用启动脚本
start-backend.bat

# 方式二：手动启动
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端API将在 http://localhost:8000 启动

### 2. 启动前端开发服务器

```bash
# 方式一：使用启动脚本
start-frontend.bat

# 方式二：手动启动
cd frontend
npm install
npm run dev
```

前端应用将在 http://localhost:3000 启动

## API文档

启动后端服务器后，可以访问以下地址查看API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要API端点

### 任务管理
- `POST /api/task/create` - 创建新任务
- `GET /api/task/{task_id}/status` - 获取任务状态
- `POST /api/task/{task_id}/run` - 执行任务
- `GET /api/task/{task_id}/result` - 获取任务结果
- `GET /api/task/list` - 列出所有任务

### 报告管理
- `GET /api/report/{task_id}` - 获取完整报告
- `GET /api/report/{task_id}/summary` - 获取报告摘要
- `GET /api/report/{task_id}/markdown` - 获取Markdown格式报告
- `GET /api/report/{task_id}/charts` - 获取图表数据

### 系统状态
- `GET /api/system/status` - 获取系统状态
- `GET /api/system/metrics` - 获取系统指标
- `GET /api/system/agents` - 获取Agent状态
- `GET /api/system/health` - 健康检查

## 开发说明

### 后端开发
- 使用FastAPI框架
- 保留原有核心业务逻辑（Planner/Executor/Reasoner）
- 所有功能通过API暴露
- 支持异步任务执行

### 前端开发
- 使用React + TypeScript
- 使用Tailwind CSS进行样式设计
- 使用Vite作为构建工具
- 通过API获取所有数据

## 部署

### 开发环境
1. 启动后端：`cd backend && python -m uvicorn app.main:app --reload`
2. 启动前端：`cd frontend && npm run dev`

### 生产环境
1. 构建前端：`cd frontend && npm run build`
2. 启动后端：`cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. 使用Nginx或类似工具托管前端静态文件

## 注意事项

1. 确保Python 3.8+和Node.js 16+已安装
2. 后端需要配置.env文件（参考原项目.env.example）
3. 前端开发服务器默认运行在3000端口
4. 后端API服务器默认运行在8000端口
5. 前端通过代理访问后端API（已配置Vite代理）