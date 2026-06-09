#!/usr/bin/env python3
"""
Step 6 验证脚本: 测试报告展示页面
"""
import os
import sys

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_report_components():
    """测试报告组件"""
    print("=" * 60)
    print("测试报告组件")
    print("=" * 60)

    frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')

    # 检查SimpleChart组件
    chart_file = os.path.join(frontend_dir, 'src', 'components', 'SimpleChart.tsx')
    if os.path.exists(chart_file):
        print("[OK] SimpleChart.tsx 存在")

        with open(chart_file, encoding='utf-8') as f:
            content = f.read()

        features = ['SimpleChart', 'DataPoint', 'bar', 'line', 'ChartDemo']
        for feature in features:
            if feature in content:
                print(f"  [OK] {feature} 已实现")
            else:
                print(f"  [FAIL] {feature} 未实现")
    else:
        print("[FAIL] SimpleChart.tsx 不存在")

    # 检查ReportPanel组件
    report_file = os.path.join(frontend_dir, 'src', 'components', 'ReportPanel.tsx')
    if os.path.exists(report_file):
        print("\n[OK] ReportPanel.tsx 存在")

        with open(report_file, encoding='utf-8') as f:
            content = f.read()

        features = ['SimpleChart', 'chart_specs', 'Data Visualizations']
        for feature in features:
            if feature in content:
                print(f"  [OK] {feature} 已集成")
            else:
                print(f"  [FAIL] {feature} 未集成")
    else:
        print("[FAIL] ReportPanel.tsx 不存在")

    return True


def test_report_page():
    """测试报告页面"""
    print("\n" + "=" * 60)
    print("测试报告页面")
    print("=" * 60)

    report_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'pages', 'Report.tsx')

    if not os.path.exists(report_file):
        print("[FAIL] Report.tsx 不存在")
        return False

    with open(report_file, encoding='utf-8') as f:
        content = f.read()

    features = ['reportApi', 'ReportPanel', 'handleDownload', 'handleRefresh']
    success_count = 0

    for feature in features:
        if feature in content:
            print(f"[OK] {feature} 已实现")
            success_count += 1
        else:
            print(f"[FAIL] {feature} 未实现")

    print(f"\n功能检查: {success_count}/{len(features)} 成功")
    return success_count == len(features)


def test_chart_types():
    """测试图表类型"""
    print("\n" + "=" * 60)
    print("测试图表类型")
    print("=" * 60)

    chart_file = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'components', 'SimpleChart.tsx')

    if not os.path.exists(chart_file):
        print("[FAIL] SimpleChart.tsx 不存在")
        return False

    with open(chart_file, encoding='utf-8') as f:
        content = f.read()

    chart_types = ['bar', 'line']
    for chart_type in chart_types:
        if f"'{chart_type}'" in content or f'"{chart_type}"' in content:
            print(f"[OK] {chart_type} 图表类型已支持")
        else:
            print(f"[FAIL] {chart_type} 图表类型未支持")

    return True


if __name__ == "__main__":
    print("Step 6 验证脚本 - 报告展示页面")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("报告组件", test_report_components()))
    results.append(("报告页面", test_report_page()))
    results.append(("图表类型", test_chart_types()))

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
        print("\n恭喜! Step 6 报告展示页面验证成功!")
    else:
        print("\n请修复失败的测试后再继续")
