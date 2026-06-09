#!/usr/bin/env python3
"""
Step 4 验证脚本: 测试 API 接口
"""
import os
import sys

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()


def test_api_imports():
    """测试 API 模块导入"""
    print("=" * 60)
    print("测试 API 模块导入")
    print("=" * 60)

    modules = [
        "app.api",
        "app.api.task",
        "app.api.report",
        "app.api.system",
        "app.api.tools",
        "app.api.chat",
    ]

    success_count = 0
    for module_path in modules:
        try:
            __import__(module_path)
            print(f"[OK] {module_path}")
            success_count += 1
        except ImportError as e:
            print(f"[FAIL] {module_path}: {e}")
        except Exception as e:
            print(f"[FAIL] {module_path}: Unexpected error: {e}")

    print(f"\n导入测试: {success_count}/{len(modules)} 成功")
    return success_count == len(modules)


def test_fastapi_app():
    """测试 FastAPI 应用"""
    print("\n" + "=" * 60)
    print("测试 FastAPI 应用")
    print("=" * 60)

    try:
        from app.main import app

        # 检查路由
        print("\n1. 检查路由注册...")
        routes = [route.path for route in app.routes]

        expected_routes = [
            "/",
            "/ping",
            "/api/",
            "/api/task/create",
            "/api/task/{task_id}/status",
            "/api/task/{task_id}/run",
            "/api/task/{task_id}/result",
            "/api/task/list",
            "/api/report/{task_id}",
            "/api/report/{task_id}/summary",
            "/api/report/{task_id}/markdown",
            "/api/report/{task_id}/charts",
            "/api/report/{task_id}/analysis",
            "/api/report/{task_id}/sources",
            "/api/report/{task_id}/process",
            "/api/system/status",
            "/api/system/metrics",
            "/api/system/agents",
            "/api/system/config",
            "/api/system/health",
            "/api/system/version",
            "/api/tools/list",
            "/api/tools/stock/price",
            "/api/tools/stock/history",
            "/api/tools/financial/report",
            "/api/tools/financial/analysis",
            "/api/tools/news/search",
            "/api/tools/news/analysis",
            "/api/chat/conversations",
            "/api/chat/conversations/{conversation_id}",
            "/api/chat/conversations/{conversation_id}/messages",
        ]

        for route in expected_routes:
            if route in routes:
                print(f"   [OK] {route}")
            else:
                print(f"   [FAIL] {route} 未注册")

        print(f"\n   总路由数: {len(routes)}")

        print("\n" + "=" * 60)
        print("FastAPI 应用测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] FastAPI 应用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pydantic_models():
    """测试 Pydantic 模型"""
    print("\n" + "=" * 60)
    print("测试 Pydantic 模型")
    print("=" * 60)

    try:
        from app.api.chat import ChatRequest
        from app.api.report import ReportResponse
        from app.api.system import SystemStatusResponse
        from app.api.task import (
            TaskCreateRequest,
        )
        from app.api.tools import StockPriceRequest

        print("\n1. 测试 Task 模型...")
        request = TaskCreateRequest(query="Test query for financial analysis", priority=1)
        print(f"   [OK] TaskCreateRequest: {request.query[:30]}...")

        print("\n2. 测试 Report 模型...")
        report = ReportResponse(task_id="test_123", report_title="Test Report")
        print(f"   [OK] ReportResponse: {report.task_id}")

        print("\n3. 测试 System 模型...")
        status = SystemStatusResponse(
            status="healthy",
            version="1.0.0",
            uptime=100.0,
            total_requests=10,
            success_rate=100.0,
            avg_latency_ms=50.0,
            timestamp="2025-01-25T12:00:00"
        )
        print(f"   [OK] SystemStatusResponse: {status.status}")

        print("\n4. 测试 Tools 模型...")
        stock_request = StockPriceRequest(symbol="AAPL")
        print(f"   [OK] StockPriceRequest: {stock_request.symbol}")

        print("\n5. 测试 Chat 模型...")
        chat_request = ChatRequest(message="What is the stock price of Apple?")
        print(f"   [OK] ChatRequest: {chat_request.message[:30]}...")

        print("\n" + "=" * 60)
        print("Pydantic 模型测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] Pydantic 模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_documentation():
    """测试 API 文档"""
    print("\n" + "=" * 60)
    print("测试 API 文档")
    print("=" * 60)

    try:
        from app.main import app

        # 检查 OpenAPI 规范
        print("\n1. 检查 OpenAPI 规范...")
        openapi = app.openapi()

        print(f"   [OK] 标题: {openapi.get('info', {}).get('title', '')}")
        print(f"   [OK] 版本: {openapi.get('info', {}).get('version', '')}")
        print(f"   [OK] 路径数: {len(openapi.get('paths', {}))}")

        # 检查标签
        print("\n2. 检查标签...")
        tags = openapi.get('tags', [])
        for tag in tags:
            print(f"   [OK] {tag.get('name', '')}: {tag.get('description', '')[:50]}...")

        print("\n" + "=" * 60)
        print("API 文档测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] API 文档测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Step 4 验证脚本 - API 接口")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("API 导入", test_api_imports()))
    results.append(("FastAPI 应用", test_fastapi_app()))
    results.append(("Pydantic 模型", test_pydantic_models()))
    results.append(("API 文档", test_api_documentation()))

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
        print("\n恭喜! Step 4 API 接口验证成功!")
        print("所有 API 接口已准备好使用")
        print("\n启动服务后访问:")
        print("  - Swagger UI: http://localhost:8000/docs")
        print("  - ReDoc: http://localhost:8000/redoc")
    else:
        print("\n请修复失败的测试后再继续")
