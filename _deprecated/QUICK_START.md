# Smart Finance Agent - 快速启动指南

## 前提条件

1. Python 3.8+ 已安装
2. Node.js 16+ 已安装
3. npm 或 yarn 已安装

## 启动步骤

### 1. 启动后端服务器

**Windows用户：**
```bash
# 双击运行 start-backend.bat
# 或者手动执行：
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Linux/Mac用户：**
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端API将在 http://localhost:8000 启动

### 2. 启动前端开发服务器

**Windows用户：**
```bash
# 双击运行 start-frontend.bat
# 或者手动执行：
cd frontend
npm install
npm run dev
```

**Linux/Mac用户：**
```bash
cd frontend
npm install
npm run dev
```

前端应用将在 http://localhost:3000 启动

### 3. 访问应用

1. 打开浏览器访问 http://localhost:3000
2. 在Research页面输入研究查询
3. 查看Dashboard中的任务状态
4. 在Report页面查看详细报告

## API文档

启动后端服务器后，可以访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 常见问题

### 1. 端口被占用
如果端口8000或3000被占用，可以修改配置：
- 后端：修改 `start-backend.bat` 中的端口号
- 前端：修改 `frontend/vite.config.ts` 中的端口号

### 2. 依赖安装失败
确保使用正确的Python和Node.js版本：
```bash
python --version  # 应该是3.8+
node --version    # 应该是16+
npm --version     # 应该是8+
```

### 3. API连接失败
确保：
1. 后端服务器已启动
2. 前端代理配置正确（已配置在vite.config.ts中）
3. 没有防火墙阻止连接

### 4. 环境变量配置
复制 `.env.example` 到 `.env` 并配置必要的API密钥：
```bash
cp backend/.env.example backend/.env
# 编辑 .env 文件配置API密钥
```

## 开发模式

### 后端开发
- 代码修改后自动重载（使用 --reload 参数）
- API文档自动生成
- 支持热重载

### 前端开发
- 代码修改后自动刷新
- 支持热模块替换（HMR）
- 错误提示友好

## 生产部署

### 构建前端
```bash
cd frontend
npm run build
```

### 部署后端
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 使用Nginx托管前端
将 `frontend/dist` 目录配置到Nginx中，配置反向代理到后端API。

## 技术支持

如有问题，请检查：
1. 控制台错误信息
2. 网络请求状态
3. 依赖版本兼容性
4. 环境变量配置