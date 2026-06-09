#!/usr/bin/env python3
"""
Step 3 Demo: 工具模块实际使用演示
"""
import asyncio
import os
import sys

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from app.tools.financial_report_tool import FinancialAnalysisTool, FinancialReportTool
from app.tools.news_summary_tool import NewsAnalysisTool, NewsSummaryTool
from app.tools.stock_price_tool import StockHistoryTool, StockPriceTool
from app.utils.logger import get_logger

logger = get_logger("demo_step3")


async def demo_stock_tools():
    """演示股票相关工具"""
    print("=" * 60)
    print("Demo: 股票相关工具")
    print("=" * 60)

    # 股票价格查询
    print("\n1. 股票价格查询...")
    stock_tool = StockPriceTool()

    symbols = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"]
    for symbol in symbols:
        result = await stock_tool.execute(symbol=symbol)
        if result.success:
            data = result.data
            print(f"   {symbol}: ${data.get('price', 0):.2f} ({data.get('change_percent', 0):+.2f}%)")

    # 股票历史数据
    print("\n2. 股票历史数据...")
    history_tool = StockHistoryTool()

    result = await history_tool.execute(symbol="TSLA", period="1m")
    if result.success:
        data = result.data
        history = data.get("history", [])
        print(f"   TSLA 历史数据: {len(history)} 个数据点")
        if history:
            latest = history[-1]
            print(f"   最新: {latest.get('date')} - ${latest.get('close', 0):.2f}")


async def demo_financial_tools():
    """演示财务相关工具"""
    print("\n" + "=" * 60)
    print("Demo: 财务相关工具")
    print("=" * 60)

    # 财务报告查询
    print("\n1. 财务报告查询...")
    report_tool = FinancialReportTool()

    symbols = ["AAPL", "TSLA", "GOOGL"]
    for symbol in symbols:
        result = await report_tool.execute(symbol=symbol, report_type="summary")
        if result.success:
            data = result.data
            print(f"   {symbol}: {data.get('name')} - {data.get('industry')}")

    # 财务分析
    print("\n2. 财务分析...")
    analysis_tool = FinancialAnalysisTool()

    for symbol in symbols:
        result = await analysis_tool.execute(symbol=symbol, analysis_type="comprehensive")
        if result.success:
            data = result.data
            analysis = data.get("analysis", {})
            print(f"   {symbol}:")
            print(f"     摘要: {analysis.get('summary', '')[:60]}...")
            print(f"     建议: {analysis.get('recommendation', '')}")


async def demo_news_tools():
    """演示新闻相关工具"""
    print("\n" + "=" * 60)
    print("Demo: 新闻相关工具")
    print("=" * 60)

    # 新闻摘要
    print("\n1. 新闻摘要...")
    news_tool = NewsSummaryTool()

    queries = ["Tesla", "Apple", "Google"]
    for query in queries:
        result = await news_tool.execute(query=query, max_results=2)
        if result.success:
            data = result.data
            results = data.get("results", [])
            summary = data.get("summary", "")
            print(f"\n   {query}:")
            print(f"     结果数: {len(results)}")
            print(f"     摘要: {summary[:80]}...")

    # 新闻分析
    print("\n2. 新闻分析...")
    analysis_tool = NewsAnalysisTool()

    for query in queries:
        result = await analysis_tool.execute(query=query, period="7d")
        if result.success:
            data = result.data
            analysis = data.get("analysis", {})
            print(f"\n   {query}:")
            print(f"     情感分数: {analysis.get('sentiment_score', 0)}")
            print(f"     趋势: {analysis.get('trend', '')}")
            print(f"     主题数: {len(analysis.get('key_themes', []))}")


async def demo_integrated_workflow():
    """演示集成工作流程"""
    print("\n" + "=" * 60)
    print("Demo: 集成工作流程")
    print("=" * 60)

    # 模拟一个完整的金融分析流程
    symbol = "AAPL"
    print(f"\n分析 {symbol} 的完整流程...")

    # 1. 获取股票价格
    print("\n1. 获取股票价格...")
    stock_tool = StockPriceTool()
    stock_result = await stock_tool.execute(symbol=symbol)
    if stock_result.success:
        stock_data = stock_result.data
        print(f"   价格: ${stock_data.get('price', 0):.2f}")
        print(f"   变动: {stock_data.get('change_percent', 0):.2f}%")

    # 2. 获取财务数据
    print("\n2. 获取财务数据...")
    report_tool = FinancialReportTool()
    report_result = await report_tool.execute(symbol=symbol, report_type="summary")
    if report_result.success:
        report_data = report_result.data
        print(f"   公司: {report_data.get('name')}")
        print(f"   行业: {report_data.get('industry')}")

    # 3. 获取新闻
    print("\n3. 获取相关新闻...")
    news_tool = NewsSummaryTool()
    news_result = await news_tool.execute(query="Apple", max_results=3)
    if news_result.success:
        news_data = news_result.data
        results = news_data.get("results", [])
        print(f"   新闻数: {len(results)}")
        for i, article in enumerate(results[:2]):
            print(f"     {i+1}. {article.get('title', '')[:50]}...")

    # 4. 进行财务分析
    print("\n4. 进行财务分析...")
    analysis_tool = FinancialAnalysisTool()
    analysis_result = await analysis_tool.execute(symbol=symbol, analysis_type="comprehensive")
    if analysis_result.success:
        analysis_data = analysis_result.data
        analysis = analysis_data.get("analysis", {})
        print(f"   摘要: {analysis.get('summary', '')[:60]}...")
        print(f"   建议: {analysis.get('recommendation', '')}")

        # 显示优势和劣势
        strengths = analysis.get("strengths", [])
        weaknesses = analysis.get("weaknesses", [])
        if strengths:
            print(f"   优势: {', '.join(strengths[:2])}")
        if weaknesses:
            print(f"   劣势: {', '.join(weaknesses[:2])}")

    # 5. 进行新闻分析
    print("\n5. 进行新闻分析...")
    news_analysis_tool = NewsAnalysisTool()
    news_analysis_result = await news_analysis_tool.execute(query="Apple", period="7d")
    if news_analysis_result.success:
        news_analysis = news_analysis_result.data.get("analysis", {})
        print(f"   情感分数: {news_analysis.get('sentiment_score', 0)}")
        print(f"   趋势: {news_analysis.get('trend', '')}")

    print("\n" + "=" * 60)
    print("集成工作流程演示完成!")
    print("=" * 60)


async def main():
    """主演示函数"""
    print("Step 3 Demo: 工具模块实际使用演示")
    print("=" * 60)

    # 演示股票工具
    await demo_stock_tools()

    # 演示财务工具
    await demo_financial_tools()

    # 演示新闻工具
    await demo_news_tools()

    # 演示集成工作流程
    await demo_integrated_workflow()

    print("\n" + "=" * 60)
    print("Step 3 Demo 完成!")
    print("=" * 60)
    print("\n工具模块功能:")
    print("  - StockPriceTool: 实时股价查询")
    print("  - StockHistoryTool: 历史股价数据")
    print("  - FinancialReportTool: 财务报告查询")
    print("  - FinancialAnalysisTool: 财务分析")
    print("  - NewsSummaryTool: 新闻摘要")
    print("  - NewsAnalysisTool: 新闻分析")


if __name__ == "__main__":
    asyncio.run(main())
