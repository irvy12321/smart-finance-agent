"""
新闻摘要工具 - 支持新闻搜索和摘要生成
"""
from datetime import datetime

import aiohttp

from app.tools.base_tool import BaseTool, ToolResult
from app.utils.logger import get_logger

logger = get_logger("news_summary_tool")

# 模拟新闻数据（生产环境应接入真实API）
MOCK_NEWS_DATA = {
    "Tesla": [
        {
            "title": "Tesla Reports Strong Q4 2024 Earnings, Revenue Up 25%",
            "description": "Tesla Inc. reported better-than-expected fourth quarter results, with revenue increasing 25% year-over-year to $25.2 billion.",
            "source": "Reuters",
            "date": "2025-01-25",
            "url": "https://example.com/tesla-q4-2024",
            "sentiment": "positive",
        },
        {
            "title": "Tesla Expands Cybertruck Production Amid Strong Demand",
            "description": "Tesla is ramping up production of its Cybertruck model as demand continues to exceed expectations.",
            "source": "Bloomberg",
            "date": "2025-01-20",
            "url": "https://example.com/tesla-cybertruck",
            "sentiment": "positive",
        },
        {
            "title": "Tesla Faces Increased Competition in EV Market",
            "description": "Traditional automakers are accelerating their electric vehicle plans, putting pressure on Tesla's market share.",
            "source": "CNBC",
            "date": "2025-01-18",
            "url": "https://example.com/tesla-competition",
            "sentiment": "neutral",
        },
    ],
    "Apple": [
        {
            "title": "Apple iPhone Sales Grow 10% in Holiday Quarter",
            "description": "Apple Inc. reported a 10% increase in iPhone sales during the holiday quarter, driven by strong demand for iPhone 15.",
            "source": "Wall Street Journal",
            "date": "2025-01-24",
            "url": "https://example.com/apple-iphone-sales",
            "sentiment": "positive",
        },
        {
            "title": "Apple Services Revenue Hits All-Time High",
            "description": "Apple's services division, including App Store and Apple Music, reached a record $22 billion in revenue.",
            "source": "Financial Times",
            "date": "2025-01-22",
            "url": "https://example.com/apple-services",
            "sentiment": "positive",
        },
        {
            "title": "Apple Vision Pro Launch Drives Interest in AR/VR",
            "description": "Apple's entry into the mixed reality market with Vision Pro is generating significant consumer interest.",
            "source": "TechCrunch",
            "date": "2025-01-20",
            "url": "https://example.com/apple-vision-pro",
            "sentiment": "positive",
        },
    ],
    "Google": [
        {
            "title": "Google Cloud Revenue Surges 30% Year-Over-Year",
            "description": "Alphabet's Google Cloud division reported a 30% increase in revenue, continuing its strong growth trajectory.",
            "source": "Reuters",
            "date": "2025-01-23",
            "url": "https://example.com/google-cloud",
            "sentiment": "positive",
        },
        {
            "title": "Google AI Integration Boosts Search Revenue",
            "description": "Google's integration of AI into its search products is driving increased advertising revenue.",
            "source": "Bloomberg",
            "date": "2025-01-21",
            "url": "https://example.com/google-ai-search",
            "sentiment": "positive",
        },
        {
            "title": "Google Faces Antitrust Scrutiny in Multiple Markets",
            "description": "Regulators in the US and Europe are increasing scrutiny of Google's market dominance.",
            "source": "Financial Times",
            "date": "2025-01-19",
            "url": "https://example.com/google-antitrust",
            "sentiment": "negative",
        },
    ],
    "Microsoft": [
        {
            "title": "Microsoft Azure Gains Cloud Market Share",
            "description": "Microsoft's Azure cloud platform continues to gain market share, driven by strong enterprise adoption.",
            "source": "CNBC",
            "date": "2025-01-22",
            "url": "https://example.com/microsoft-azure",
            "sentiment": "positive",
        },
        {
            "title": "Microsoft AI Copilot Drives Office 365 Growth",
            "description": "Microsoft's AI-powered Copilot features are driving increased adoption of Office 365.",
            "source": "Wall Street Journal",
            "date": "2025-01-20",
            "url": "https://example.com/microsoft-copilot",
            "sentiment": "positive",
        },
        {
            "title": "Microsoft Gaming Revenue Increases After Activision Acquisition",
            "description": "Microsoft's gaming division saw significant revenue growth following the Activision Blizzard acquisition.",
            "source": "Bloomberg",
            "date": "2025-01-18",
            "url": "https://example.com/microsoft-gaming",
            "sentiment": "positive",
        },
    ],
    "Amazon": [
        {
            "title": "Amazon AWS Remains Cloud Market Leader",
            "description": "Amazon Web Services maintained its position as the leading cloud service provider with strong revenue growth.",
            "source": "Reuters",
            "date": "2025-01-21",
            "url": "https://example.com/amazon-aws",
            "sentiment": "positive",
        },
        {
            "title": "Amazon Prime Membership Reaches New Milestone",
            "description": "Amazon announced that Prime membership has exceeded 200 million globally.",
            "source": "Financial Times",
            "date": "2025-01-19",
            "url": "https://example.com/amazon-prime",
            "sentiment": "positive",
        },
        {
            "title": "Amazon Expands Same-Day Delivery Service",
            "description": "Amazon is expanding its same-day delivery service to more cities across the United States.",
            "source": "CNBC",
            "date": "2025-01-17",
            "url": "https://example.com/amazon-delivery",
            "sentiment": "positive",
        },
    ],
}


class NewsSummaryTool(BaseTool):
    name = "news_summary"
    description = "Searches for recent news and generates summaries for a given topic or company"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)
        kwargs.get("topic", "")  # 可选：指定主题

        if not query:
            return ToolResult(success=False, error="No query provided", tool_name=self.name)

        try:
            # 尝试使用真实API
            if self.api_key:
                return await self._search_real_news(query, max_results)
            else:
                return await self._get_mock_news(query, max_results)
        except Exception as e:
            logger.error(f"News search failed for {query}: {e}")
            return await self._get_mock_news(query, max_results)

    async def _search_real_news(self, query: str, max_results: int) -> ToolResult:
        """从真实API搜索新闻（使用NewsAPI）"""
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": max_results,
            "apiKey": self.api_key,
        }

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                articles = data.get("articles", [])

                results = []
                for article in articles:
                    results.append({
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "source": article.get("source", {}).get("name", ""),
                        "date": article.get("publishedAt", "")[:10],
                        "url": article.get("url", ""),
                        "sentiment": self._analyze_sentiment(article.get("title", "") + " " + article.get("description", "")),
                    })

                summary = self._generate_summary(results, query)

                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "results": results,
                        "summary": summary,
                        "total_results": len(results),
                        "timestamp": datetime.now().isoformat(),
                    },
                    tool_name=self.name,
                )

    async def _get_mock_news(self, query: str, max_results: int) -> ToolResult:
        """获取模拟新闻数据"""
        # 查找匹配的关键词
        results = []
        for keyword, articles in MOCK_NEWS_DATA.items():
            if keyword.lower() in query.lower():
                results.extend(articles)

        # 如果没有匹配，返回通用新闻
        if not results:
            results = [
                {
                    "title": f"Latest news about: {query}",
                    "description": f"This is simulated news data for {query}. Configure NEWS_API_KEY for real results.",
                    "source": "Simulated",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "url": "",
                    "sentiment": "neutral",
                },
            ]

        # 限制结果数量
        results = results[:max_results]

        # 生成摘要
        summary = self._generate_summary(results, query)

        return ToolResult(
            success=True,
            data={
                "query": query,
                "results": results,
                "summary": summary,
                "total_results": len(results),
                "timestamp": datetime.now().isoformat(),
                "source": "mock_data",
                "note": "Simulated data. Configure NEWS_API_KEY for real results.",
            },
            tool_name=self.name,
        )

    def _analyze_sentiment(self, text: str) -> str:
        """分析文本情感（简单实现）"""
        positive_words = ["strong", "growth", "increase", "surge", "record", "positive", "gain", "up", "high", "success"]
        negative_words = ["weak", "decline", "decrease", "drop", "loss", "negative", "down", "low", "fail", "struggle"]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _generate_summary(self, articles: list, query: str) -> str:
        """生成新闻摘要"""
        if not articles:
            return f"No news found for: {query}"

        # 统计情感
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        for article in articles:
            sentiment = article.get("sentiment", "neutral")
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1

        # 生成摘要
        summary_parts = [f"Found {len(articles)} news articles about {query}."]

        if sentiments["positive"] > sentiments["negative"]:
            summary_parts.append("Overall sentiment is positive.")
        elif sentiments["negative"] > sentiments["positive"]:
            summary_parts.append("Overall sentiment is negative.")
        else:
            summary_parts.append("Sentiment is mixed.")

        # 提取关键点
        key_points = []
        for article in articles[:3]:
            if article.get("description"):
                key_points.append(article["description"][:100] + "...")

        if key_points:
            summary_parts.append("Key points:")
            for point in key_points:
                summary_parts.append(f"- {point}")

        return " ".join(summary_parts)

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """降级执行"""
        query = kwargs.get("query", "unknown")
        logger.warning(f"News summary fallback for: {query}")
        return await self._get_mock_news(query, 3)


class NewsAnalysisTool(BaseTool):
    name = "news_analysis"
    description = "Analyzes news sentiment and trends for a given topic or company"

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        period = kwargs.get("period", "7d")  # 1d, 7d, 30d

        if not query:
            return ToolResult(success=False, error="No query provided", tool_name=self.name)

        try:
            # 获取新闻数据
            news_tool = NewsSummaryTool()
            news_result = await news_tool.execute(query=query, max_results=10)

            if not news_result.success:
                return ToolResult(success=False, error="Failed to fetch news", tool_name=self.name)

            data = news_result.data
            analysis = self._analyze_news(data, query, period)

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "period": period,
                    "analysis": analysis,
                    "timestamp": datetime.now().isoformat(),
                },
                tool_name=self.name,
            )
        except Exception as e:
            logger.error(f"News analysis failed for {query}: {e}")
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def _analyze_news(self, data: dict, query: str, period: str) -> dict:
        """分析新闻数据"""
        articles = data.get("results", [])

        # 统计情感
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        sources = {}
        topics = []

        for article in articles:
            # 情感统计
            sentiment = article.get("sentiment", "neutral")
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1

            # 来源统计
            source = article.get("source", "Unknown")
            sources[source] = sources.get(source, 0) + 1

            # 提取主题
            if article.get("title"):
                topics.append(article["title"])

        # 计算情感分数
        total = sum(sentiments.values())
        if total > 0:
            sentiment_score = (sentiments["positive"] - sentiments["negative"]) / total
        else:
            sentiment_score = 0

        # 生成趋势分析
        if sentiment_score > 0.3:
            trend = "positive"
            trend_description = f"News coverage for {query} is predominantly positive."
        elif sentiment_score < -0.3:
            trend = "negative"
            trend_description = f"News coverage for {query} shows concerning trends."
        else:
            trend = "neutral"
            trend_description = f"News coverage for {query} is balanced."

        # 识别关键主题
        key_themes = self._extract_themes(topics)

        return {
            "sentiment_score": round(sentiment_score, 2),
            "sentiment_distribution": sentiments,
            "trend": trend,
            "trend_description": trend_description,
            "top_sources": dict(sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]),
            "key_themes": key_themes,
            "total_articles": len(articles),
            "period": period,
        }

    def _extract_themes(self, topics: list) -> list:
        """提取关键主题（简单实现）"""
        # 简单的关键词提取
        common_words = set()
        for topic in topics:
            words = topic.lower().split()
            common_words.update(words)

        # 过滤停用词
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                      "have", "has", "had", "do", "does", "did", "will", "would", "could",
                      "should", "may", "might", "must", "shall", "can", "need", "dare",
                      "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
                      "from", "as", "into", "through", "during", "before", "after", "above",
                      "below", "between", "out", "off", "over", "under", "again", "further",
                      "then", "once", "and", "but", "or", "nor", "not", "so", "yet", "both",
                      "either", "neither", "each", "every", "all", "any", "few", "more",
                      "most", "other", "some", "such", "no", "only", "own", "same", "than",
                      "too", "very", "just", "because", "if", "when", "where", "how", "what",
                      "which", "who", "whom", "this", "that", "these", "those", "i", "me",
                      "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours",
                      "yourself", "yourselves", "he", "him", "his", "himself", "she", "her",
                      "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs",
                      "themselves", "about", "up", "down", "news", "latest", "report"}

        themes = [word for word in common_words if word not in stop_words and len(word) > 3]
        return themes[:10]

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """降级执行"""
        query = kwargs.get("query", "unknown")
        logger.warning(f"News analysis fallback for: {query}")
        return ToolResult(
            success=True,
            data={
                "query": query,
                "period": "7d",
                "analysis": {
                    "sentiment_score": 0,
                    "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                    "trend": "neutral",
                    "trend_description": f"Unable to analyze news trends for {query}.",
                    "top_sources": {},
                    "key_themes": [],
                    "total_articles": 0,
                    "period": "7d",
                },
                "timestamp": datetime.now().isoformat(),
            },
            tool_name=self.name,
        )
