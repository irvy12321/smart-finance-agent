#!/usr/bin/env python3
"""
Step 8 验证脚本: 测试启动脚本和说明文档
"""
import os


def test_startup_scripts():
    """测试启动脚本"""
    print("=" * 60)
    print("测试启动脚本")
    print("=" * 60)

    root_dir = os.path.dirname(os.path.dirname(__file__))

    scripts = [
        'start-backend.bat',
        'start-frontend.bat',
        'start-all.bat',
    ]

    success_count = 0
    for script in scripts:
        script_path = os.path.join(root_dir, script)
        if os.path.exists(script_path):
            print(f"[OK] {script} 存在")

            with open(script_path, encoding='utf-8') as f:
                content = f.read()

            # 检查关键内容
            if 'backend' in content.lower() or 'frontend' in content.lower():
                print("  [OK] 内容正确")
                success_count += 1
            else:
                print("  [FAIL] 内容不正确")
        else:
            print(f"[FAIL] {script} 不存在")

    print(f"\n脚本检查: {success_count}/{len(scripts)} 成功")
    return success_count == len(scripts)


def test_readme():
    """测试README文件"""
    print("\n" + "=" * 60)
    print("测试README文件")
    print("=" * 60)

    root_dir = os.path.dirname(os.path.dirname(__file__))
    readme_path = os.path.join(root_dir, 'README.md')

    if not os.path.exists(readme_path):
        print("[FAIL] README.md 不存在")
        return False

    with open(readme_path, encoding='utf-8') as f:
        content = f.read()

    # 检查关键章节
    sections = [
        'Smart Finance Agent',
        '功能特性',
        '快速开始',
        '项目结构',
        'API 接口',
        '使用示例',
        '配置说明',
        '部署',
    ]

    success_count = 0
    for section in sections:
        if section in content:
            print(f"[OK] {section} 章节存在")
            success_count += 1
        else:
            print(f"[FAIL] {section} 章节不存在")

    print(f"\n章节检查: {success_count}/{len(sections)} 成功")
    return success_count == len(sections)


def test_documentation():
    """测试文档文件"""
    print("\n" + "=" * 60)
    print("测试文档文件")
    print("=" * 60)

    root_dir = os.path.dirname(os.path.dirname(__file__))

    docs = [
        'README.md',
        'backend/STEP1_COMPLETE.md',
        'backend/STEP2_COMPLETE.md',
        'backend/STEP3_COMPLETE.md',
        'backend/STEP4_COMPLETE.md',
        'backend/STEP5_COMPLETE.md',
        'backend/STEP6_COMPLETE.md',
        'backend/STEP7_COMPLETE.md',
    ]

    success_count = 0
    for doc in docs:
        doc_path = os.path.join(root_dir, doc)
        if os.path.exists(doc_path):
            print(f"[OK] {doc} 存在")
            success_count += 1
        else:
            print(f"[FAIL] {doc} 不存在")

    print(f"\n文档检查: {success_count}/{len(docs)} 成功")
    return success_count == len(docs)


def test_project_structure():
    """测试项目结构"""
    print("\n" + "=" * 60)
    print("测试项目结构")
    print("=" * 60)

    root_dir = os.path.dirname(os.path.dirname(__file__))

    # 检查后端结构
    backend_dirs = [
        'backend/app',
        'backend/app/api',
        'backend/app/core',
        'backend/app/rag',
        'backend/app/tools',
        'backend/app/utils',
        'backend/app/infrastructure',
    ]

    print("后端目录:")
    backend_ok = 0
    for dir_path in backend_dirs:
        full_path = os.path.join(root_dir, dir_path)
        if os.path.exists(full_path) and os.path.isdir(full_path):
            print(f"  [OK] {dir_path}")
            backend_ok += 1
        else:
            print(f"  [FAIL] {dir_path}")

    # 检查前端结构
    frontend_dirs = [
        'frontend/src',
        'frontend/src/pages',
        'frontend/src/components',
        'frontend/src/services',
        'frontend/src/hooks',
    ]

    print("\n前端目录:")
    frontend_ok = 0
    for dir_path in frontend_dirs:
        full_path = os.path.join(root_dir, dir_path)
        if os.path.exists(full_path) and os.path.isdir(full_path):
            print(f"  [OK] {dir_path}")
            frontend_ok += 1
        else:
            print(f"  [FAIL] {dir_path}")

    total = len(backend_dirs) + len(frontend_dirs)
    success = backend_ok + frontend_ok
    print(f"\n目录检查: {success}/{total} 成功")
    return success == total


if __name__ == "__main__":
    print("Step 8 验证脚本 - 启动脚本和说明文档")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("启动脚本", test_startup_scripts()))
    results.append(("README", test_readme()))
    results.append(("文档文件", test_documentation()))
    results.append(("项目结构", test_project_structure()))

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
        print("\n恭喜! Step 8 启动脚本和说明文档验证成功!")
        print("\n项目已准备就绪!")
        print("\n启动方式:")
        print("  1. 双击 start-all.bat 一键启动")
        print("  2. 或分别运行 start-backend.bat 和 start-frontend.bat")
    else:
        print("\n请修复失败的测试后再继续")
