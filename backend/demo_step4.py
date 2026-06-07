#!/usr/bin/env python3
"""
Step 4 Demo: API 接口使用演示
"""
import requests
import json
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_URL = "http://localhost:8000"


def test_system_api():
    """测试系统API"""
    print("=" * 60)
    print("测试系统API")
    print("=" * 60)
    
    try:
        # 健康检查
        print("\n1. 健康检查...")
        response = requests.get(f"{BASE_URL}/ping")
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] 状态: {data.get('status')}")
        else:
            print(f"   [FAIL] 状态码: {response.status_code}")
            return False
        
        # 系统状态
        print("\n2. 系统状态...")
        response = requests.get(f"{BASE_URL}/api/system/status")
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] 状态: {data.get('status')}")
            print(f"   [OK] 版本: {data.get('version')}")
            print(f"   [OK] 运行时间: {data.get('uptime', 0):.0f}秒")
        else:
            print(f"   [FAIL] 状态码: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 系统API测试失败: {e}")
        return False


def test_tools_api():
    """测试工具API"""
    print("\n" + "=" * 60)
    print("测试工具API")
    print("=" * 60)
    
    try:
        # 工具列表
        print("\n1. 获取工具列表...")
        response = requests.get(f"{BASE_URL}/api/tools/list")
        if response.status_code == 200:
            data = response.json()
            tools = data.get("tools", [])
            print(f"   [OK] 工具数: {data.get('total', 0)}")
            for tool in tools[:5]:
                print(f"     - {tool.get('name')}: {tool.get('description', '')[:40]}...")
        else:
            print(f"   [FAIL] 状态码: {response.status_code}")
        
        # 股票价格查询
        print("\n2. 股票价格查询...")
        response = requests.post(
            f"{BASE_URL}/api/tools/stock/price",
            json={"symbol": "AAPL"}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] {data.get('symbol')}: ${data.get('price', 0):.2f}")
            print(f"   [OK] 变动: {data.get('change_percent', 0):.2f}%")
        else:
            print(f"   [FAIL] 状态码: {response.status_code}")
        
        # 财务报告查询
        print("\n3. 财务报告查询...")
        response = requests.post(
            f"{BASE_URL}/api/tools/financial/report",
            json={"symbol": "TSLA", "report_type": "summary"}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] 公司: {data.get('name')}")
            print(f"   [OK] 行业: {data.get('industry')}")
        else:
            print(f"   [FAIL] 状态码: {response.status_code}")
        
        # 新闻搜索
        print("\n4. 新闻搜索...")
        response = requests.post(
            f"{BASE_URL}/api/tools/news/search",
            json={"query": "Tesla", "max_results": 3}
        )
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"   [OK] 结果数: {data.get('total_results', 0)}")
            for i, article in enumerate(results[:2]):
                print(f"     {i+1}. {article.get('title', '')[:50]}...")
        else:
            print(f"   [FAIL] 状态码: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 工具API测试失败: {e}")
        return False


def test_task_api():
    """测试任务API"""
    print("\n" + "=" * 60)
    print("测试任务API")
    print("=" * 60)
    
    try:
        # 创建任务
        print("\n1. 创建任务...")
        response = requests.post(
            f"{BASE_URL}/api/task/create",
            json={"query": "Analyze Tesla stock performance in Q4 2024", "priority": 1}
        )
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            print(f"   [OK] 任务ID: {task_id}")
            print(f"   [OK] 状态: {data.get('status')}")
            
            # 查询任务状态
            print("\n2. 查询任务状态...")
            response = requests.get(f"{BASE_URL}/api/task/{task_id}/status")
            if response.status_code == 200:
                status_data = response.json()
                print(f"   [OK] 状态: {status_data.get('status')}")
                print(f"   [OK] 进度: {status_data.get('progress', 0)}%")
            
            # 任务列表
            print("\n3. 任务列表...")
            response = requests.get(f"{BASE_URL}/api/task/list")
            if response.status_code == 200:
                list_data = response.json()
                tasks = list_data.get("tasks", [])
                print(f"   [OK] 任务数: {len(tasks)}")
            
            return task_id
        else:
            print(f"   [FAIL] 状态码: {response.status_code}")
            return None
        
    except Exception as e:
        print(f"[FAIL] 任务API测试失败: {e}")
        return None


def test_chat_api():
    """测试聊天API"""
    print("\n" + "=" * 60)
    print("测试聊天API")
    print("=" * 60)
    
    try:
        # 创建会话
        print("\n1. 创建会话...")
        response = requests.post(f"{BASE_URL}/api/chat/conversations")
        if response.status_code == 200:
            data = response.json()
            conversation_id = data.get("conversation_id")
            print(f"   [OK] 会话ID: {conversation_id}")
            
            # 发送消息
            print("\n2. 发送消息...")
            response = requests.post(
                f"{BASE_URL}/api/chat/conversations/{conversation_id}/messages",
                json={"message": "What is the stock price of Apple?"}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   [OK] 回复: {data.get('response', '')[:80]}...")
                print(f"   [OK] 置信度: {data.get('confidence', 0)}")
            
            # 获取会话历史
            print("\n3. 获取会话历史...")
            response = requests.get(f"{BASE_URL}/api/chat/conversations/{conversation_id}")
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                print(f"   [OK] 消息数: {data.get('total_messages', 0)}")
            
            return conversation_id
        else:
            print(f"   [FAIL] 状态码: {response.status_code}")
            return None
        
    except Exception as e:
        print(f"[FAIL] 聊天API测试失败: {e}")
        return None


def test_report_api(task_id):
    """测试报告API"""
    print("\n" + "=" * 60)
    print("测试报告API")
    print("=" * 60)
    
    if not task_id:
        print("[SKIP] 没有可用的任务ID")
        return
    
    try:
        # 获取报告摘要
        print("\n1. 获取报告摘要...")
        response = requests.get(f"{BASE_URL}/api/report/{task_id}/summary")
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] 标题: {data.get('report_title', '')[:50]}...")
            print(f"   [OK] 置信度: {data.get('confidence', 0)}")
        elif response.status_code == 400:
            print(f"   [SKIP] 任务未完成")
        else:
            print(f"   [FAIL] 状态码: {response.status_code}")
        
    except Exception as e:
        print(f"[FAIL] 报告API测试失败: {e}")


def main():
    """主测试函数"""
    print("Step 4 Demo: API 接口使用演示")
    print("=" * 60)
    print(f"目标地址: {BASE_URL}")
    print("=" * 60)
    
    # 测试系统API
    if not test_system_api():
        print("\n无法连接到服务器，请确保后端服务已启动")
        print("启动命令: cd backend && python -m app.main")
        return
    
    # 测试工具API
    test_tools_api()
    
    # 测试任务API
    task_id = test_task_api()
    
    # 测试聊天API
    test_chat_api()
    
    # 测试报告API
    test_report_api(task_id)
    
    print("\n" + "=" * 60)
    print("Step 4 Demo 完成!")
    print("=" * 60)
    print("\nAPI 文档:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")


if __name__ == "__main__":
    main()