# Step 5: 前端 Chat 页面

## 概述

Step 5 完成了前端Chat页面的搭建，包含以下功能：

- **Chat页面**: 完整的聊天界面
- **StockPriceCard**: 股票价格查询组件
- **API服务**: Tools API和Chat API
- **路由配置**: Chat路由和导航

## 文件结构

```
frontend/
├── src/
│   ├── App.tsx                    # 主应用路由
│   ├── main.tsx                   # 应用入口
│   ├── index.css                  # 全局样式
│   ├── pages/
│   │   ├── Dashboard.tsx          # 主页
│   │   ├── Research.tsx           # 研究页
│   │   ├── Report.tsx             # 报告页
│   │   ├── SystemOverview.tsx     # 系统状态页
│   │   └── Chat.tsx               # 聊天页
│   ├── components/
│   │   ├── Sidebar.tsx            # 侧边导航栏
│   │   ├── StockPriceCard.tsx     # 股票价格卡片
│   │   ├── PlannerCard.tsx        # 规划器卡片
│   │   ├── ExecutorCard.tsx       # 执行器卡片
│   │   ├── ReasonerCard.tsx       # 推理器卡片
│   │   └── ReportPanel.tsx        # 报前面板
│   ├── services/
│   │   └── api.ts                 # API服务层
│   ├── hooks/
│   └── utils/
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

### 3. 访问应用

- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000

## 页面说明

### 1. Chat页面

**路径**: `/chat`

**功能**:
- 创建新会话
- 发送和接收消息
- 会话历史管理
- 快捷操作按钮

**快捷操作**:
- **Stock Price**: 查询股票价格
- **Financial Analysis**: 获取财务分析
- **Latest News**: 搜索最新新闻
- **Market Trends**: 分析市场趋势

**使用示例**:
```
用户: What is the stock price of AAPL?
助手: I can help you with stock information...

用户: Analyze Tesla stock
助手: I can help you with financial analysis...
```

### 2. Dashboard页面

**路径**: `/`

**功能**:
- 任务统计
- 快捷操作
- 股票价格查询
- 最近任务列表

### 3. Research页面

**路径**: `/research`

**功能**:
- 创建研究任务
- 执行任务
- 查看任务状态

### 4. Report页面

**路径**: `/report/:taskId`

**功能**:
- 查看研究报告
- 查看任务详情
- 查看图表数据

### 5. SystemOverview页面

**路径**: `/system`

**功能**:
- 系统状态监控
- Agent状态查看
- 系统指标统计

## 组件说明

### 1. Chat页面组件

**文件**: `src/pages/Chat.tsx`

**功能**:
- 消息发送和接收
- 会话管理
- 快捷操作
- 消息历史

**主要状态**:
- `messages`: 消息列表
- `input`: 输入内容
- `loading`: 加载状态
- `conversationId`: 当前会话ID
- `conversations`: 会话列表

**主要函数**:
- `handleSend()`: 发送消息
- `createNewConversation()`: 创建新会话
- `loadConversation()`: 加载会话
- `deleteConversation()`: 删除会话

### 2. StockPriceCard组件

**文件**: `src/components/StockPriceCard.tsx`

**功能**:
- 股票价格查询
- 热门股票快捷选择
- 详细数据展示

**Props**:
- `onStockSelect`: 股票选择回调

**数据展示**:
- 价格和变动
- 成交量
- 市值
- P/E比率
- 52周范围

### 3. Sidebar组件

**文件**: `src/components/Sidebar.tsx`

**功能**:
- 导航菜单
- 系统状态显示
- 配置信息

**导航项**:
- Dashboard: 主页
- Research: 研究页
- Chat: 聊天页
- System: 系统状态

## API服务

### Tools API

```typescript
// 获取工具列表
toolsApi.list()

// 获取股票价格
toolsApi.getStockPrice(symbol: string)

// 获取股票历史
toolsApi.getStockHistory(symbol: string, period: string)

// 获取财务报告
toolsApi.getFinancialReport(symbol: string, reportType: string)

// 获取财务分析
toolsApi.getFinancialAnalysis(symbol: string, analysisType: string)

// 搜索新闻
toolsApi.searchNews(query: string, maxResults: number)

// 获取新闻分析
toolsApi.getNewsAnalysis(query: string, period: string)
```

### Chat API

```typescript
// 创建会话
chatApi.createConversation()

// 发送消息
chatApi.sendMessage(conversationId: string, message: string)

// 获取历史
chatApi.getHistory(conversationId: string)

// 列出会话
chatApi.listConversations()

// 删除会话
chatApi.deleteConversation(conversationId: string)
```

## 配置说明

### Vite配置

**文件**: `vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### Tailwind配置

**文件**: `tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dark': {
          'bg': '#0a0a0f',
          'card': '#1a1a2e',
          'border': '#2a2a3e',
        },
        'primary': {
          '50': '#f0f0f5',
          '100': '#e0e0e0',
          '200': '#c0c0d0',
          '300': '#a0a0b0',
          '400': '#8888a0',
          '500': '#6366f1',
        },
      },
    },
  },
  plugins: [],
}
```

## 使用示例

### 1. 股票价格查询

```typescript
import { toolsApi } from '../services/api'

// 查询AAPL股票价格
const stockData = await toolsApi.getStockPrice('AAPL')
console.log(stockData)
// {
//   symbol: 'AAPL',
//   name: 'Apple Inc.',
//   price: 182.52,
//   change: 1.25,
//   change_percent: 0.69,
//   ...
// }
```

### 2. 聊天功能

```typescript
import { chatApi } from '../services/api'

// 创建会话
const conversation = await chatApi.createConversation()
const conversationId = conversation.conversation_id

// 发送消息
const response = await chatApi.sendMessage(conversationId, 'What is the stock price of AAPL?')
console.log(response.response)

// 获取历史
const history = await chatApi.getHistory(conversationId)
console.log(history.messages)
```

### 3. 使用StockPriceCard组件

```tsx
import StockPriceCard from '../components/StockPriceCard'

function MyComponent() {
  const handleStockSelect = (symbol: string) => {
    console.log('Selected stock:', symbol)
  }

  return (
    <StockPriceCard onStockSelect={handleStockSelect} />
  )
}
```

## 样式说明

### 颜色方案

- **主色调**: `#6366f1` (Primary-500)
- **背景色**: `#0a0a0f` (Dark-BG)
- **卡片背景**: `#1a1a2e` (Dark-Card)
- **边框颜色**: `#2a2a3e` (Dark-Border)

### 组件样式

- **卡片**: `card` 类
- **按钮**: `btn-primary` 类
- **徽章**: `badge` 类
- **状态点**: `status-dot` 类

## 下一步

Step 5 完成后，可以继续：

- **Step 6**: 报告展示页面
- **Step 7**: 系统状态Dashboard
- **Step 8**: 配置启动脚本和说明文档

## 参考资料

- [React 文档](https://react.dev/)
- [Vite 文档](https://vitejs.dev/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
- [Lucide React](https://lucide.dev/)
- [React Router](https://reactrouter.com/)