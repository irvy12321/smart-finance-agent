# Step 3: 工具模块

## 概述

Step 3 完成了工具模块的搭建，包含以下工具：

- **StockPriceTool**: 实时股价查询
- **StockHistoryTool**: 历史股价数据
- **FinancialReportTool**: 财务报告查询
- **FinancialAnalysisTool**: 财务分析
- **NewsSummaryTool**: 新闻摘要
- **NewsAnalysisTool**: 新闻分析

## 文件结构

```
backend/
├── app/
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base_tool.py              # 工具基类
│   │   ├── registry.py               # 工具注册表
│   │   ├── crawler_tool.py           # 爬虫工具
│   │   ├── news_tool.py              # 新闻工具
│   │   ├── rag_tool.py               # RAG工具
│   │   ├── stock_price_tool.py       # 股票价格工具
│   │   ├── financial_report_tool.py  # 财务报告工具
│   │   └── news_summary_tool.py      # 新闻摘要工具
│   └── core/
│       └── orchestrator.py           # 已更新，注册新工具
├── verify_step3.py                   # 验证脚本
├── demo_step3.py                     # 演示脚本
└── STEP3_README.md                   # 本文档
```

## 快速开始

### 1. 验证工具模块

```bash
cd backend
python verify_step3.py
```

### 2. 运行工具演示

```bash
cd backend
python demo_step3.py
```

### 3. 在代码中使用工具

```python
import asyncio
from app.tools.stock_price_tool import StockPriceTool
from app.tools.financial_report_tool import FinancialReportTool
from app.tools.news_summary_tool import NewsSummaryTool

async def main():
    # 股票价格查询
    stock_tool = StockPriceTool()
    result = await stock_tool.execute(symbol="AAPL")
    print(result)
    
    # 财务报告查询
    report_tool = FinancialReportTool()
    result = await report_tool.execute(symbol="TSLA", report_type="summary")
    print(result)
    
    # 新闻查询
    news_tool = NewsSummaryTool()
    result = await news_tool.execute(query="Tesla", max_results=5)
    print(result)

asyncio.run(main())
```

## 工具详细说明

### 1. StockPriceTool

**功能**: 实时股价查询

**参数**:
- `symbol` (str): 股票代码，如 "AAPL", "TSLA"

**返回数据**:
```python
{
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "price": 182.52,
    "change": 1.25,
    "change_percent": 0.69,
    "volume": 52345678,
    "market_cap": 2.85e12,
    "pe_ratio": 28.5,
    "52w_high": 199.62,
    "52w_low": 124.17,
    "timestamp": "2025-01-25T12:00:00",
    "source": "mock_data"
}
```

**使用示例**:
```python
from app.tools.stock_price_tool import StockPriceTool
import asyncio

async def query_stock():
    tool = StockPriceTool()
    result = await tool.execute(symbol="AAPL")
    if result.success:
        print(f"AAPL: ${result.data['price']:.2f}")
    return result

result = asyncio.run(query_stock())
```

### 2. StockHistoryTool

**功能**: 历史股价数据

**参数**:
- `symbol` (str): 股票代码
- `period` (str): 时间周期，可选值: "1d", "1w", "1m", "3m", "6m", "1y"

**返回数据**:
```python
{
    "symbol": "TSLA",
    "period": "1m",
    "history": [
        {
            "date": "2025-01-01",
            "open": 245.00,
            "high": 248.50,
            "low": 242.00,
            "close": 247.00,
            "volume": 87654321
        },
        ...
    ]
}
```

**使用示例**:
```python
from app.tools.stock_price_tool import StockHistoryTool
import asyncio

async def query_history():
    tool = StockHistoryTool()
    result = await tool.execute(symbol="TSLA", period="1m")
    if result.success:
        history = result.data['history']
        print(f"TSLA 历史数据: {len(history)} 个数据点")
    return result

result = asyncio.run(query_history())
```

### 3. FinancialReportTool

**功能**: 财务报告查询

**参数**:
- `symbol` (str): 股票代码
- `report_type` (str): 报告类型，可选值: "summary", "detailed", "quarterly"

**返回数据 (summary)**:
```python
{
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "financials": {
        "revenue": {"2024": 383.29e9, "2023": 383.29e9},
        "net_income": {"2024": 97.00e9, "2023": 96.99e9},
        "eps": {"2024": 6.13, "2023": 6.15},
        "pe_ratio": {"2024": 28.5, "2023": 29.2}
    }
}
```

**使用示例**:
```python
from app.tools.financial_report_tool import FinancialReportTool
import asyncio

async def query_financial():
    tool = FinancialReportTool()
    result = await tool.execute(symbol="AAPL", report_type="summary")
    if result.success:
        print(f"公司: {result.data['name']}")
        print(f"行业: {result.data['industry']}")
    return result

result = asyncio.run(query_financial())
```

### 4. FinancialAnalysisTool

**功能**: 财务分析

**参数**:
- `symbol` (str): 股票代码
- `analysis_type` (str): 分析类型，可选值: "comprehensive", "valuation", "profitability", "growth"

**返回数据**:
```python
{
    "symbol": "AAPL",
    "analysis_type": "comprehensive",
    "analysis": {
        "summary": "Apple Inc. shows mixed financial signals.",
        "strengths": ["High return on equity"],
        "weaknesses": ["High debt-to-equity ratio"],
        "opportunities": ["Potentially undervalued"],
        "threats": [],
        "metrics": {
            "revenue_growth": 0.05,
            "net_income_growth": 0.03,
            "pe_ratio": 28.5,
            "return_on_equity": 1.60,
            "debt_to_equity": 1.76
        },
        "recommendation": "Hold and monitor"
    }
}
```

**使用示例**:
```python
from app.tools.financial_report_tool import FinancialAnalysisTool
import asyncio

async def analyze_stock():
    tool = FinancialAnalysisTool()
    result = await tool.execute(symbol="AAPL", analysis_type="comprehensive")
    if result.success:
        analysis = result.data['analysis']
        print(f"摘要: {analysis['summary']}")
        print(f"建议: {analysis['recommendation']}")
    return result

result = asyncio.run(analyze_stock())
```

### 5. NewsSummaryTool

**功能**: 新闻搜索和摘要

**参数**:
- `query` (str): 搜索查询
- `max_results` (int): 最大结果数，默认5
- `topic` (str): 可选，指定主题

**返回数据**:
```python
{
    "query": "Tesla",
    "results": [
        {
            "title": "Tesla Reports Strong Q4 2024 Earnings",
            "description": "Tesla Inc. reported better-than-expected results...",
            "source": "Reuters",
            "date": "2025-01-25",
            "url": "https://example.com/tesla-q4-2024",
            "sentiment": "positive"
        },
        ...
    ],
    "summary": "Found 3 news articles about Tesla. Overall sentiment is positive.",
    "total_results": 3
}
```

**使用示例**:
```python
from app.tools.news_summary_tool import NewsSummaryTool
import asyncio

async def search_news():
    tool = NewsSummaryTool()
    result = await tool.execute(query="Tesla", max_results=3)
    if result.success:
        data = result.data
        print(f"结果数: {data['total_results']}")
        print(f"摘要: {data['summary']}")
    return result

result = asyncio.run(search_news())
```

### 6. NewsAnalysisTool

**功能**: 新闻趋势分析

**参数**:
- `query` (str): 搜索查询
- `period` (str): 分析周期，可选值: "1d", "7d", "30d"

**返回数据**:
```python
{
    "query": "Tesla",
    "period": "7d",
    "analysis": {
        "sentiment_score": 0.67,
        "sentiment_distribution": {
            "positive": 2,
            "negative": 0,
            "neutral": 1
        },
        "trend": "positive",
        "trend_description": "News coverage for Tesla is predominantly positive.",
        "top_sources": {
            "Reuters": 1,
            "Bloomberg": 1,
            "CNBC": 1
        },
        "key_themes": ["earnings", "revenue", "growth"],
        "total_articles": 3
    }
}
```

**使用示例**:
```python
from app.tools.news_summary_tool import NewsAnalysisTool
import asyncio

async def analyze_news():
    tool = NewsAnalysisTool()
    result = await tool.execute(query="Tesla", period="7d")
    if result.success:
        analysis = result.data['analysis']
        print(f"情感分数: {analysis['sentiment_score']}")
        print(f"趋势: {analysis['trend']}")
    return result

result = asyncio.run(analyze_news())
```

## 配置说明

### API 配置

在 `.env` 文件中配置API密钥：

```bash
# 股票数据API（可选）
ALPHA_VANTAGE_API_KEY=your_api_key

# 新闻API（可选）
NEWS_API_KEY=your_news_api_key
```

### 模拟数据

所有工具都支持模拟数据，无需配置API密钥即可运行。

## 集成到 Orchestrator

工具已经集成到 Orchestrator 中：

```python
class Orchestrator:
    def _register_tools(self):
        tools = [
            CrawlerTool(),
            NewsTool(),
            RAGTool(),
            StockPriceTool(),
            StockHistoryTool(),
            FinancialReportTool(),
            FinancialAnalysisTool(),
            NewsSummaryTool(),
            NewsAnalysisTool(),
        ]
        for tool in tools:
            self.registry.register(tool)
```

## 工具注册表

所有工具都注册在 `ToolRegistry` 中：

```python
from app.tools.registry import ToolRegistry

registry = ToolRegistry()

# 列出所有工具
tools = registry.list_tools()
for tool in tools:
    print(f"{tool['name']}: {tool['description']}")
```

## 降级处理

所有工具都实现了降级处理：

```python
class StockPriceTool(BaseTool):
    async def fallback_execute(self, **kwargs) -> ToolResult:
        """降级执行：返回模拟数据"""
        symbol = kwargs.get("symbol", "UNKNOWN").upper()
        return await self._get_mock_price(symbol)
```

## 性能优化

### 1. 批量查询

```python
# 批量查询多个股票
symbols = ["AAPL", "TSLA", "GOOGL"]
results = await asyncio.gather(*[
    stock_tool.execute(symbol=symbol)
    for symbol in symbols
])
```

### 2. 缓存

建议对频繁查询的数据进行缓存：

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_stock_price(symbol: str):
    # 缓存股票价格
    pass
```

## 故障排除

### 1. API 密钥错误

确保在 `.env` 文件中正确配置API密钥。

### 2. 网络连接问题

检查网络连接，确保可以访问外部API。

### 3. 模拟数据

如果无法访问真实API，工具会自动使用模拟数据。

## 下一步

Step 3 完成后，可以继续：

- **Step 4**: 封装完整的 API 接口
- **Step 5**: 前端 Chat 页面开发

## 参考资料

- [Alpha Vantage API](https://www.alphavantage.co/)
- [NewsAPI](https://newsapi.org/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)