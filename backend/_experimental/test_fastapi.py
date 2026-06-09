#!/usr/bin/env python3
"""
测试 FastAPI 应用启动
"""
import os
import sys

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()


def test_fastapi_app():
    """测试 FastAPI 应用是否能够正常导入和初始化"""
    print("=" * 60)
    print("测试 FastAPI 应用")
    print("=" * 60)

    try:
        # 测试导入
        print("\n1. 测试导入 FastAPI 应用...")
        from app.main import app
        print("   [OK] FastAPI 应用导入成功")

        # 测试路由
        print("\n2. 测试路由注册...")
        routes = [route.path for route in app.routes]
        expected_routes = [
            "/",
            "/ping",
            "/api/system/status",
            "/api/task/create",
            "/api/task/{task_id}/status",
            "/api/task/{task_id}/run",
            "/api/task/{task_id}/result",
            "/api/report/{task_id}",
            "/api/tasks",
        ]

        for route in expected_routes:
            if route in routes:
                print(f"   [OK] {route}")
            else:
                print(f"   [FAIL] {route} 未注册")

        print("\n" + "=" * 60)
        print("FastAPI 应用测试通过!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] FastAPI 应用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("FastAPI 应用测试")
    print("=" * 60)

    result = test_fastapi_app()

    if result:
        print("\n可以使用以下命令启动应用:")
        print("  python -m app.main")
        print("\n或者:")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("\n请修复问题后再启动应用")
