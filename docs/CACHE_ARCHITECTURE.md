# Tool 缓存架构设计

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        API 请求层                                │
│  /tools/stock/price  /tools/news/search  /tools/financial/...  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Tool 执行层                               │
│  StockPriceTool     NewsTool     CrawlerTool     FinancialTool  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        缓存层 (MemoryTTLCache)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ stock_price │  │    news     │  │   crawler   │  ...       │
│  │   TTL: 60s  │  │  TTL: 300s  │  │  TTL: 300s  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  特性:                                                          │
│  - LRU 淘汰策略                                                │
│  - 线程安全                                                    │
│  - 自动过期                                                    │
│  - 命中率统计                                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │    缓存命中?       │
                    └─────────┬─────────┘
                         是 ↙     ↘ 否
                          │         │
                          ▼         ▼
                    ┌─────────┐  ┌─────────────┐
                    │ 返回缓存 │  │  调用外部API  │
                    └─────────┘  └──────┬──────┘
                                        │
                                        ▼
                                 ┌─────────────┐
                                 │  存入缓存    │
                                 └─────────────┘
```

## 缓存配置

| Tool | 缓存键前缀 | TTL | 说明 |
|------|-----------|-----|------|
| StockPriceTool | `stock_price:{symbol}` | 60秒 | 股价变化频繁 |
| StockHistoryTool | `stock_history:{symbol}:{period}` | 300秒 | 历史数据稳定 |
| NewsTool | `news:{query}` | 300秒 | 新闻更新频率低 |
| CrawlerTool | `crawler:{url}` | 300秒 | 网页内容稳定 |
| FinancialReportTool | `financial:{symbol}` | 300秒 | 财报数据稳定 |
| FinancialAnalysisTool | `analysis:{symbol}` | 300秒 | 分析结果稳定 |

## 性能提升评估

### 假设条件
- 日活跃用户: 100
- 每用户每日查询: 20 次
- 重复查询比例: 30% (同一股票多次查询)

### 计算

**每日总查询数**: 100 × 20 = 2000 次

**重复查询数**: 2000 × 30% = 600 次

**缓存命中后节省的 API 调用**: 600 次/天

### 成本节省

| API | 每次调用成本 | 每日节省 | 每月节省 |
|-----|------------|---------|---------|
| Alpha Vantage (股价) | ~0.001 USD | 0.60 USD | 18 USD |
| NewsAPI | ~0.0005 USD | 0.30 USD | 9 USD |
| FMP (财报) | ~0.002 USD | 1.20 USD | 36 USD |
| **总计** | - | **2.10 USD** | **63 USD** |

### 延迟改善

| 操作 | 无缓存延迟 | 有缓存延迟 | 改善 |
|------|-----------|-----------|------|
| 股价查询 | 200-500ms | <1ms | 99%+ |
| 新闻搜索 | 300-800ms | <1ms | 99%+ |
| 网页爬取 | 500-2000ms | <1ms | 99%+ |
| 财报查询 | 200-600ms | <1ms | 99%+ |

## 监控 API

### 获取缓存统计
```bash
GET /api/system/cache
```

响应:
```json
{
  "size": 42,
  "max_size": 1000,
  "hits": 156,
  "misses": 44,
  "hit_rate": 78.0,
  "total_requests": 200
}
```

### 清空缓存
```bash
POST /api/system/cache/clear
```

响应:
```json
{
  "message": "Cleared 42 cache entries"
}
```

## 扩展性

### 升级到 Redis

如需升级到 Redis，只需实现相同的缓存接口:

```python
class RedisTTLCache:
    def get(self, key: str) -> tuple[bool, Any]:
        ...

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        ...

    def delete(self, key: str) -> bool:
        ...

    def clear(self) -> int:
        ...

    @property
    def stats(self) -> dict:
        ...
```

然后在 `get_cache()` 函数中切换实现:

```python
def get_cache():
    if os.getenv("REDIS_URL"):
        return RedisTTLCache(os.getenv("REDIS_URL"))
    return MemoryTTLCache()
```
