# Smart Finance Agent - 文件迁移清单

## 需要移动的文件（已复制到backend/app/）

### 核心业务逻辑
- `core/*` → `backend/app/core/*`
  - `orchestrator.py` - 主要协调器
  - `planner.py` - 任务规划器
  - `executor.py` - 执行器
  - `reasoner.py` - 推理器
  - `report_agent.py` - 报告生成器
  - `chart_renderer.py` - 图表渲染器
  - `fallback_manager.py` - 降级管理器
  - `agent_status.py` - Agent状态管理
  - `metrics_dashboard.py` - 指标仪表板
  - `dashboard_integration.py` - 仪表板集成
  - `token_budget.py` - Token预算管理
  - `observability/` - 可观测性模块
  - `profiling/` - 性能分析模块
  - `replay/` - 重放模块

### RAG相关
- `rag/*` → `backend/app/rag/*`
  - `retriever.py` - 检索器
  - `chunker.py` - 分块器
  - `embed.py` - 嵌入模块
  - `loader.py` - 加载器
  - `memory.py` - 记忆模块
  - `vector_store.py` - 向量存储

### 工具实现
- `tools/*` → `backend/app/tools/*`
  - `base_tool.py` - 基础工具类
  - `crawler_tool.py` - 爬虫工具
  - `news_tool.py` - 新闻工具
  - `rag_tool.py` - RAG工具
  - `registry.py` - 工具注册表

### 工具函数
- `utils/*` → `backend/app/utils/*`
  - `logger.py` - 日志工具
  - `exceptions.py` - 异常定义
  - `tracing.py` - 追踪工具
  - `retry.py` - 重试机制
  - `circuit_breaker.py` - 熔断器

### 基础设施
- `infrastructure/*` → `backend/app/infrastructure/*`
  - `llm_client.py` - LLM客户端
  - `smart_router.py` - 智能路由器
  - `config.py` - 配置管理
  - `config_llm.yaml` - LLM配置
  - `config_rag.yaml` - RAG配置
  - `config_crawler.yaml` - 爬虫配置

## 需要删除的文件（迁移完成后）

### Streamlit UI文件
- `app/ui.py` - Streamlit主UI（已迁移到React）
- `app/ui_components.py` - Streamlit组件（已迁移到React）
- `app/ui/` - Streamlit组件目录（已迁移到React）

### 原始入口文件
- `app/main.py` - 原CLI入口（已改造为FastAPI入口）

## 需要改造的文件

### 后端文件
1. `app/main.py` → 改造为FastAPI入口
   - 移除Streamlit相关代码
   - 添加FastAPI应用初始化
   - 添加API路由配置
   - 添加CORS中间件

2. `requirements.txt` → 更新依赖
   - 添加FastAPI依赖
   - 添加uvicorn依赖
   - 移除streamlit依赖

### 前端文件（新建）
1. `frontend/package.json` - React项目配置
2. `frontend/vite.config.ts` - Vite配置
3. `frontend/tailwind.config.js` - Tailwind配置
4. `frontend/src/App.tsx` - 主应用组件
5. `frontend/src/main.tsx` - 应用入口
6. `frontend/src/index.css` - 全局样式
7. `frontend/src/components/*.tsx` - UI组件
8. `frontend/src/pages/*.tsx` - 页面组件
9. `frontend/src/services/api.ts` - API服务
10. `frontend/src/hooks/useApi.ts` - 自定义hooks
11. `frontend/src/utils/utils.ts` - 工具函数

## 新增文件

### 启动脚本
1. `start-backend.bat` - 后端启动脚本
2. `start-frontend.bat` - 前端启动脚本

### 文档
1. `README_NEW.md` - 新项目说明文档
2. `REFACTORING_PLAN.md` - 重构方案文档
3. `FILE_MIGRATION_CHECKLIST.md` - 本文件

## 验证清单

### 后端验证
- [ ] FastAPI服务器能正常启动
- [ ] API端点能正常访问
- [ ] 核心业务逻辑正常工作
- [ ] 任务创建和执行功能正常
- [ ] 报告生成功能正常

### 前端验证
- [ ] React开发服务器能正常启动
- [ ] 页面能正常加载
- [ ] 组件能正常渲染
- [ ] API调用能正常工作
- [ ] 状态管理正常

### 集成验证
- [ ] 前后端能正常通信
- [ ] 任务流程完整执行
- [ ] 报告正确显示
- [ ] 错误处理正常

## 注意事项

1. **不要删除原始文件**：在验证新系统完全正常工作前，保留原始文件作为备份
2. **环境变量**：确保backend目录有正确的.env配置文件
3. **依赖安装**：确保安装了所有必要的Python和Node.js依赖
4. **端口配置**：后端默认8000端口，前端默认3000端口
5. **代理配置**：前端已配置Vite代理，开发环境可直接访问后端API