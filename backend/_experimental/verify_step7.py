#!/usr/bin/env python3
"""
Step 7 验证脚本: 测试系统状态Dashboard
"""
import os
import sys

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_system_overview_page():
    """测试SystemOverview页面"""
    print("=" * 60)
    print("测试SystemOverview页面")
    print("=" * 60)

    page_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'pages', 'SystemOverview.tsx')

    if not os.path.exists(page_file):
        print("[FAIL] SystemOverview.tsx 不存在")
        return False

    with open(page_file, encoding='utf-8') as f:
        content = f.read()

    # 检查必要的功能
    required_features = [
        'systemApi',
        'taskApi',
        'SimpleChart',
        'agentStatus',
        'metrics',
        'autoRefresh',
        'taskStatusData',
        'agentPerformanceData',
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


def test_dashboard_components():
    """测试Dashboard组件"""
    print("\n" + "=" * 60)
    print("测试Dashboard组件")
    print("=" * 60)

    frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')

    # 检查必要的组件
    required_components = [
        'src/components/SimpleChart.tsx',
        'src/components/ReportPanel.tsx',
        'src/components/StockPriceCard.tsx',
        'src/components/Sidebar.tsx',
    ]

    success_count = 0
    for component in required_components:
        file_path = os.path.join(frontend_dir, component)
        if os.path.exists(file_path):
            print(f"[OK] {component} 存在")
            success_count += 1
        else:
            print(f"[FAIL] {component} 不存在")

    print(f"\n组件检查: {success_count}/{len(required_components)} 成功")
    return success_count == len(required_components)


def test_navigation():
    """测试导航"""
    print("\n" + "=" * 60)
    print("测试导航")
    print("=" * 60)

    sidebar_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'components', 'Sidebar.tsx')

    if not os.path.exists(sidebar_file):
        print("[FAIL] Sidebar.tsx 不存在")
        return False

    with open(sidebar_file, encoding='utf-8') as f:
        content = f.read()

    # 检查导航项
    nav_items = ['Dashboard', 'Research', 'Chat', 'System']

    success_count = 0
    for item in nav_items:
        if item in content:
            print(f"[OK] {item} 导航项存在")
            success_count += 1
        else:
            print(f"[FAIL] {item} 导航项不存在")

    print(f"\n导航检查: {success_count}/{len(nav_items)} 成功")
    return success_count == len(nav_items)


if __name__ == "__main__":
    print("Step 7 验证脚本 - 系统状态Dashboard")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("SystemOverview页面", test_system_overview_page()))
    results.append(("Dashboard组件", test_dashboard_components()))
    results.append(("导航", test_navigation()))

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
        print("\n恭喜! Step 7 系统状态Dashboard验证成功!")
    else:
        print("\n请修复失败的测试后再继续")
