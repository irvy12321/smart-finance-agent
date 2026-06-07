#!/usr/bin/env python3
"""
Step 5 验证脚本: 测试前端组件
"""
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_frontend_files():
    """测试前端文件是否存在"""
    print("=" * 60)
    print("测试前端文件")
    print("=" * 60)
    
    frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    src_dir = os.path.join(frontend_dir, 'src')
    
    expected_files = [
        'src/App.tsx',
        'src/main.tsx',
        'src/index.css',
        'src/pages/Dashboard.tsx',
        'src/pages/Research.tsx',
        'src/pages/Report.tsx',
        'src/pages/SystemOverview.tsx',
        'src/pages/Chat.tsx',
        'src/components/Sidebar.tsx',
        'src/components/PlannerCard.tsx',
        'src/components/ExecutorCard.tsx',
        'src/components/ReasonerCard.tsx',
        'src/components/ReportPanel.tsx',
        'src/components/StockPriceCard.tsx',
        'src/services/api.ts',
    ]
    
    success_count = 0
    for file_path in expected_files:
        full_path = os.path.join(frontend_dir, file_path)
        if os.path.exists(full_path):
            print(f"[OK] {file_path}")
            success_count += 1
        else:
            print(f"[FAIL] {file_path} 不存在")
    
    print(f"\n文件检查: {success_count}/{len(expected_files)} 成功")
    return success_count == len(expected_files)


def test_api_service():
    """测试API服务文件"""
    print("\n" + "=" * 60)
    print("测试API服务文件")
    print("=" * 60)
    
    api_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'services', 'api.ts')
    
    if not os.path.exists(api_file):
        print("[FAIL] api.ts 文件不存在")
        return False
    
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查必要的API定义
    required_apis = [
        'taskApi',
        'reportApi',
        'systemApi',
        'toolsApi',
        'chatApi',
    ]
    
    success_count = 0
    for api_name in required_apis:
        if api_name in content:
            print(f"[OK] {api_name} 已定义")
            success_count += 1
        else:
            print(f"[FAIL] {api_name} 未定义")
    
    print(f"\nAPI检查: {success_count}/{len(required_apis)} 成功")
    return success_count == len(required_apis)


def test_chat_page():
    """测试Chat页面文件"""
    print("\n" + "=" * 60)
    print("测试Chat页面文件")
    print("=" * 60)
    
    chat_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'pages', 'Chat.tsx')
    
    if not os.path.exists(chat_file):
        print("[FAIL] Chat.tsx 文件不存在")
        return False
    
    with open(chat_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查必要的组件和功能
    required_features = [
        'chatApi',
        'Message',
        'Conversation',
        'handleSend',
        'quickActions',
        'Bot',
        'User',
    ]
    
    success_count = 0
    for feature in required_features:
        if feature in content:
            print(f"[OK] {feature} 已实现")
            success_count += 1
        else:
            print(f"[FAIL] {feature} 未实现")
    
    print(f"\n功能检查: {success_count}/{len(required_features)} 成功")
    return success_count == len(required_features)


def test_stock_component():
    """测试股票组件"""
    print("\n" + "=" * 60)
    print("测试股票组件")
    print("=" * 60)
    
    stock_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'components', 'StockPriceCard.tsx')
    
    if not os.path.exists(stock_file):
        print("[FAIL] StockPriceCard.tsx 文件不存在")
        return False
    
    with open(stock_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查必要的功能
    required_features = [
        'toolsApi',
        'getStockPrice',
        'StockData',
        'handleSearch',
        'popularStocks',
    ]
    
    success_count = 0
    for feature in required_features:
        if feature in content:
            print(f"[OK] {feature} 已实现")
            success_count += 1
        else:
            print(f"[FAIL] {feature} 未实现")
    
    print(f"\n功能检查: {success_count}/{len(required_features)} 成功")
    return success_count == len(required_features)


def test_app_routing():
    """测试App路由配置"""
    print("\n" + "=" * 60)
    print("测试App路由配置")
    print("=" * 60)
    
    app_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'App.tsx')
    
    if not os.path.exists(app_file):
        print("[FAIL] App.tsx 文件不存在")
        return False
    
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查路由配置
    required_routes = [
        '/chat',
        'Chat',
        'Route',
    ]
    
    success_count = 0
    for route in required_routes:
        if route in content:
            print(f"[OK] {route} 路由已配置")
            success_count += 1
        else:
            print(f"[FAIL] {route} 路由未配置")
    
    print(f"\n路由检查: {success_count}/{len(required_routes)} 成功")
    return success_count == len(required_routes)


if __name__ == "__main__":
    print("Step 5 验证脚本 - 前端组件")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("前端文件", test_frontend_files()))
    results.append(("API服务", test_api_service()))
    results.append(("Chat页面", test_chat_page()))
    results.append(("股票组件", test_stock_component()))
    results.append(("App路由", test_app_routing()))
    
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
        print("\n恭喜! Step 5 前端组件验证成功!")
        print("\n启动前端开发服务器:")
        print("  cd frontend")
        print("  npm install")
        print("  npm run dev")
    else:
        print("\n请修复失败的测试后再继续")