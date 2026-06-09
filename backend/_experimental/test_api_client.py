#!/usr/bin/env python3
"""
API 测试客户端
"""

import requests

BASE_URL = "http://localhost:8000"


def test_health():
    """测试健康检查接口"""
    print("=" * 60)
    print("测试健康检查接口")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/ping")
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] 状态: {data.get('status')}")
            print(f"[OK] 消息: {data.get('message')}")
            return True
        else:
            print(f"[FAIL] 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        return False


def test_create_task():
    """测试创建任务接口"""
    print("\n" + "=" * 60)
    print("测试创建任务接口")
    print("=" * 60)

    try:
        payload = {
            "query": "Analyze the current market trend for tech stocks in Q4 2024",
            "priority": 1
        }

        response = requests.post(
            f"{BASE_URL}/api/task/create",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[OK] 任务ID: {data.get('task_id')}")
            print(f"[OK] 状态: {data.get('status')}")
            print(f"[OK] 消息: {data.get('message')}")
            return data.get('task_id')
        else:
            print(f"[FAIL] 状态码: {response.status_code}")
            print(f"[FAIL] 响应: {response.text}")
            return None
    except Exception as e:
        print(f"[FAIL] 请求失败: {e}")
        return None


def test_task_status(task_id):
    """测试任务状态接口"""
    print("\n" + "=" * 60)
    print("测试任务状态接口")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/api/task/{task_id}/status")

        if response.status_code == 200:
            data = response.json()
            print(f"[OK] 任务ID: {data.get('task_id')}")
            print(f"[OK] 状态: {data.get('status')}")
            print(f"[OK] 进度: {data.get('progress')}%")
            print(f"[OK] 当前阶段: {data.get('current_stage')}")
            return data.get('status')
        else:
            print(f"[FAIL] 状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"[FAIL] 请求失败: {e}")
        return None


def test_system_status():
    """测试系统状态接口"""
    print("\n" + "=" * 60)
    print("测试系统状态接口")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/api/system/status")

        if response.status_code == 200:
            data = response.json()
            print(f"[OK] 状态: {data.get('status')}")
            print(f"[OK] 版本: {data.get('version')}")
            print(f"[OK] 总请求数: {data.get('total_requests')}")
            return True
        else:
            print(f"[FAIL] 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] 请求失败: {e}")
        return False


def test_list_tasks():
    """测试任务列表接口"""
    print("\n" + "=" * 60)
    print("测试任务列表接口")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/api/tasks")

        if response.status_code == 200:
            data = response.json()
            tasks = data.get('tasks', [])
            print(f"[OK] 任务数量: {len(tasks)}")
            for task in tasks[:3]:  # 只显示前3个
                print(f"  - {task.get('task_id')}: {task.get('status')}")
            return True
        else:
            print(f"[FAIL] 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] 请求失败: {e}")
        return False


def main():
    """主测试函数"""
    print("API 测试客户端")
    print("=" * 60)
    print(f"目标地址: {BASE_URL}")
    print("=" * 60)

    # 测试健康检查
    if not test_health():
        print("\n无法连接到服务器，请确保后端服务已启动")
        print("启动命令: cd backend && python -m app.main")
        return

    # 测试系统状态
    test_system_status()

    # 测试任务列表
    test_list_tasks()

    # 测试创建任务
    task_id = test_create_task()

    if task_id:
        # 测试任务状态
        test_task_status(task_id)

    print("\n" + "=" * 60)
    print("API 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
