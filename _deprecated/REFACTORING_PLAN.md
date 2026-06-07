# Smart Finance Agent - 前后端分离重构方案

## 当前项目结构分析

### 后端逻辑（需要保留并迁移到FastAPI）
- `core/` - 核心业务逻辑（Planner/Executor/Reasoner/Orchestrator）
- `rag/` - RAG检索增强生成逻辑
- `tools/` - 工具注册和实现
- `utils/` - 工具函数（日志、异常处理等）
- `infrastructure/` - 基础设施（LLM客户端、配置）
- `app/main.py` - CLI入口（可作为后端入口参考）

### UI层（需要迁移到React）
- `app/ui.py` - Streamlit主UI
- `app/ui_components.py` - UI组件
- `app/ui/` - 更多UI组件

### 需要删除/隔离的文件
- `app/ui.py` - Streamlit UI（迁移到React后可删除）
- `app/ui_components.py` - Streamlit组件（迁移到React后可删除）
- `app/ui/` - Streamlit组件目录（迁移到React后可删除）

## 新的目录结构

```
smart-finance-agent/
├── backend/                    # FastAPI后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI应用入口
│   │   ├── api/               # API路由
│   │   │   ├── __init__.py
│   │   │   ├── task.py        # 任务相关API
│   │   │   ├── report.py      # 报告相关API
│   │   │   └── system.py      # 系统状态API
│   │   ├── core/              # 核心业务逻辑（从原core/迁移）
│   │   ├── rag/               # RAG逻辑（从原rag/迁移）
│   │   ├── tools/             # 工具实现（从原tools/迁移）
│   │   ├── utils/             # 工具函数（从原utils/迁移）
│   │   └── infrastructure/    # 基础设施（从原infrastructure/迁移）
│   ├── requirements.txt
│   └── config/
├── frontend/                  # React前端
│   ├── src/
│   │   ├── components/        # React组件
│   │   ├── pages/             # 页面组件
│   │   ├── services/          # API服务
│   │   ├── hooks/             # 自定义hooks
│   │   └── utils/             # 前端工具函数
│   ├── package.json
│   └── public/
├── docker-compose.yml         # 可选：容器化部署
└── README.md
```

## 迁移步骤

### 第一步：创建后端FastAPI框架
1. 创建`backend/`目录结构
2. 创建FastAPI应用入口
3. 设计API接口（/api/task/create, /api/task/status, /api/task/run, /api/report/get）

### 第二步：迁移核心业务逻辑
1. 将`core/`目录复制到`backend/app/core/`
2. 将`rag/`目录复制到`backend/app/rag/`
3. 将`tools/`目录复制到`backend/app/tools/`
4. 将`utils/`目录复制到`backend/app/utils/`
5. 将`infrastructure/`目录复制到`backend/app/infrastructure/`

### 第三步：实现API路由
1. 创建任务管理API（创建、状态查询、执行）
2. 创建报告获取API
3. 创建系统状态API

### 第四步：创建React前端
1. 初始化React项目（使用Vite或Create React App）
2. 安装Tailwind CSS
3. 创建基础组件结构

### 第五步：实现前端组件
1. 创建Planner卡片组件
2. 创建Executor卡片组件
3. 创建Reasoner卡片组件
4. 创建Report面板组件
5. 创建Dashboard主页面

### 第六步：配置前后端通信
1. 配置API代理
2. 实现API调用服务
3. 处理状态管理和数据流

## API设计

### 任务相关API
- `POST /api/task/create` - 创建新任务
- `GET /api/task/{task_id}/status` - 获取任务状态
- `POST /api/task/{task_id}/run` - 执行任务
- `GET /api/task/{task_id}/result` - 获取任务结果

### 报告相关API
- `GET /api/report/{task_id}` - 获取研究报告

### 系统状态API
- `GET /api/system/status` - 获取系统状态
- `GET /api/system/metrics` - 获取系统指标

## 文件迁移清单

### 需要移动的文件
- `core/*` → `backend/app/core/*`
- `rag/*` → `backend/app/rag/*`
- `tools/*` → `backend/app/tools/*`
- `utils/*` → `backend/app/utils/*`
- `infrastructure/*` → `backend/app/infrastructure/*`

### 需要删除的文件（迁移完成后）
- `app/ui.py`
- `app/ui_components.py`
- `app/ui/`目录

### 需要改造的文件
- `app/main.py` → 改造为FastAPI入口
- `requirements.txt` → 更新依赖（添加FastAPI、uvicorn等）

## 注意事项
1. 保持原有业务逻辑不变
2. 保持Agent设计（Planner/Executor/Reasoner）不变
3. 不简化功能，只做架构解耦
4. 确保重构后系统可运行