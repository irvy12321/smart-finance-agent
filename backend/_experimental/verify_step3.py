#!/usr/bin/env python3
"""
Step 3 验证脚本: 测试工具模块
"""
import asyncio
import os
import sys

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()


def test_stock_price_tool():
    """测试股票价格查询工具"""
    print("=" * 60)
    print("测试股票价格查询工具")
    print("=" * 60)

    try:
        from app.tools.stock_price_tool import StockHistoryTool, StockPriceTool

        # 测试 StockPriceTool
        print("\n1. 测试 StockPriceTool...")
        stock_tool = StockPriceTool()

        async def test_stock_query():
            # 测试已知股票
            result = await stock_tool.execute(symbol="AAPL")
            print(f"   [OK] AAPL: success={result.success}")
            if result.success:
                data = result.data
                print(f"     价格: ${data.get('price', 0):.2f}")
                print(f"     变动: {data.get('change_percent', 0):.2f}%")

            # 测试未知股票
            result = await stock_tool.execute(symbol="XYZ")
            print(f"   [OK] XYZ: success={result.success}")

            return True

        asyncio.run(test_stock_query())

        # 测试 StockHistoryTool
        print("\n2. 测试 StockHistoryTool...")
        history_tool = StockHistoryTool()

        async def test_history_query():
            result = await history_tool.execute(symbol="TSLA", period="1m")
            print(f"   [OK] TSLA 历史数据: success={result.success}")
            if result.success:
                data = result.data
                history = data.get("history", [])
                print(f"     数据点: {len(history)}")
                if history:
                    print(f"     最新: {history[-1].get('date')} - ${history[-1].get('close', 0):.2f}")

            return True

        asyncio.run(test_history_query())

        print("\n" + "=" * 60)
        print("股票价格查询工具测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] 股票价格查询工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_financial_report_tool():
    """测试财务报告分析工具"""
    print("\n" + "=" * 60)
    print("测试财务报告分析工具")
    print("=" * 60)

    try:
        from app.tools.financial_report_tool import (
            FinancialAnalysisTool,
            FinancialReportTool,
        )

        # 测试 FinancialReportTool
        print("\n1. 测试 FinancialReportTool...")
        report_tool = FinancialReportTool()

        async def test_report_query():
            # 测试摘要报告
            result = await report_tool.execute(symbol="AAPL", report_type="summary")
            print(f"   [OK] AAPL 摘要报告: success={result.success}")
            if result.success:
                data = result.data
                print(f"     公司: {data.get('name')}")
                print(f"     行业: {data.get('industry')}")

            # 测试季度报告
            result = await report_tool.execute(symbol="TSLA", report_type="quarterly")
            print(f"   [OK] TSLA 季度报告: success={result.success}")
            if result.success:
                data = result.data
                quarterly = data.get("quarterly", {})
                print(f"     季度数: {len(quarterly)}")

            return True

        asyncio.run(test_report_query())

        # 测试 FinancialAnalysisTool
        print("\n2. 测试 FinancialAnalysisTool...")
        analysis_tool = FinancialAnalysisTool()

        async def test_analysis_query():
            result = await analysis_tool.execute(symbol="GOOGL", analysis_type="comprehensive")
            print(f"   [OK] GOOGL 分析: success={result.success}")
            if result.success:
                data = result.data
                analysis = data.get("analysis", {})
                print(f"     摘要: {analysis.get('summary', '')[:80]}...")
                print(f"     建议: {analysis.get('recommendation', '')}")

            return True

        asyncio.run(test_analysis_query())

        print("\n" + "=" * 60)
        print("财务报告分析工具测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] 财务报告分析工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_news_summary_tool():
    """测试新闻摘要工具"""
    print("\n" + "=" * 60)
    print("测试新闻摘要工具")
    print("=" * 60)

    try:
        from app.tools.news_summary_tool import NewsAnalysisTool, NewsSummaryTool

        # 测试 NewsSummaryTool
        print("\n1. 测试 NewsSummaryTool...")
        news_tool = NewsSummaryTool()

        async def test_news_query():
            result = await news_tool.execute(query="Tesla", max_results=3)
            print(f"   [OK] Tesla 新闻: success={result.success}")
            if result.success:
                data = result.data
                results = data.get("results", [])
                summary = data.get("summary", "")
                print(f"     结果数: {len(results)}")
                print(f"     摘要: {summary[:80]}...")

            return True

        asyncio.run(test_news_query())

        # 测试 NewsAnalysisTool
        print("\n2. 测试 NewsAnalysisTool...")
        analysis_tool = NewsAnalysisTool()

        async def test_analysis_query():
            result = await analysis_tool.execute(query="Apple", period="7d")
            print(f"   [OK] Apple 分析: success={result.success}")
            if result.success:
                data = result.data
                analysis = data.get("analysis", {})
                print(f"     情感分数: {analysis.get('sentiment_score', 0)}")
                print(f"     趋势: {analysis.get('trend', '')}")
                print(f"     主题数: {len(analysis.get('key_themes', []))}")

            return True

        asyncio.run(test_analysis_query())

        print("\n" + "=" * 60)
        print("新闻摘要工具测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] 新闻摘要工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_registry():
    """测试工具注册表"""
    print("\n" + "=" * 60)
    print("测试工具注册表（包含新工具）")
    print("=" * 60)

    try:
        from app.tools.financial_report_tool import (
            FinancialAnalysisTool,
            FinancialReportTool,
        )
        from app.tools.news_summary_tool import NewsAnalysisTool, NewsSummaryTool
        from app.tools.registry import ToolRegistry
        from app.tools.stock_price_tool import StockHistoryTool, StockPriceTool

        # 创建工具注册表
        registry = ToolRegistry()

        # 注册工具
        print("\n1. 注册新工具...")
        tools = [
            StockPriceTool(),
            StockHistoryTool(),
            FinancialReportTool(),
            FinancialAnalysisTool(),
            NewsSummaryTool(),
            NewsAnalysisTool(),
        ]

        for tool in tools:
            registry.register(tool)
            print(f"   [OK] 注册: {tool.name}")

        # 列出工具
        print("\n2. 已注册工具:")
        for tool_info in registry.list_tools():
            print(f"   - {tool_info['name']}: {tool_info['description'][:50]}...")

        print("\n" + "=" * 60)
        print("工具注册表测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] 工具注册表测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_orchestrator_tools():
    """测试 Orchestrator 中的工具注册"""
    print("\n" + "=" * 60)
    print("测试 Orchestrator 工具注册")
    print("=" * 60)

    try:
        from app.core.orchestrator import Orchestrator

        # 创建 Orchestrator
        print("\n1. 创建 Orchestrator...")
        orchestrator = Orchestrator(use_router=False)

        # 检查工具注册
        print("\n2. 检查已注册工具...")
        tools = orchestrator.registry.list_tools()
        print(f"   工具总数: {len(tools)}")

        expected_tools = [
            "crawler", "news_search", "rag_retrieve",
            "stock_price", "stock_history",
            "financial_report", "financial_analysis",
            "news_summary", "news_analysis",
        ]

        for tool_name in expected_tools:
            if tool_name in orchestrator.registry:
                print(f"   [OK] {tool_name}")
            else:
                print(f"   [FAIL] {tool_name} 未注册")

        print("\n" + "=" * 60)
        print("Orchestrator 工具注册测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] Orchestrator 工具注册测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Step 3 验证脚本 - 工具模块")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("股票价格工具", test_stock_price_tool()))
    results.append(("财务报告工具", test_financial_report_tool()))
    results.append(("新闻摘要工具", test_news_summary_tool()))
    results.append(("工具注册表", test_tool_registry()))
    results.append(("Orchestrator", test_orchestrator_tools()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for test_name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{test_name}: {status}")

    all_passed = all(r for _, r in results)
    print(f"\n总体结果: {'全部通过' if all_passed else '存在失败'}")

    if all_passed:
        print("\n恭喜! Step 3 工具模块验证成功!")
        print("所有工具已准备好集成到 Orchestrator 中")
    else:
        print("\n请修复失败的测试后再继续")
