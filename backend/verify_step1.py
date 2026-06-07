#!/usr/bin/env python3
"""
Step 1 验证脚本: 测试模块导入和初始化
"""
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def test_imports():
    """测试所有核心模块的导入"""
    print("=" * 60)
    print("测试模块导入")
    print("=" * 60)
    
    modules = [
        ("app.core.orchestrator", "Orchestrator"),
        ("app.core.planner", "PlannerAgent, Plan, SubTask"),
        ("app.core.executor", "ExecutorAgent, ExecutionResult"),
        ("app.core.reasoner", "Reasoner, ReasoningResult"),
        ("app.infrastructure.llm_client", "LLMClient, LiteLLMRouter"),
        ("app.infrastructure.smart_router", "SmartRouter"),
        ("app.tools.registry", "ToolRegistry"),
        ("app.utils.logger", "get_logger"),
        ("app.utils.tracing", "TraceContext"),
    ]
    
    success_count = 0
    for module_path, imports in modules:
        try:
            module = __import__(module_path, fromlist=imports.split(", "))
            print(f"[OK] {module_path}: {imports}")
            success_count += 1
        except ImportError as e:
            print(f"[FAIL] {module_path}: {e}")
        except Exception as e:
            print(f"[FAIL] {module_path}: Unexpected error: {e}")
    
    print(f"\n导入测试: {success_count}/{len(modules)} 成功")
    return success_count == len(modules)


def test_initialization():
    """测试核心组件的初始化"""
    print("\n" + "=" * 60)
    print("测试组件初始化")
    print("=" * 60)
    
    try:
        from app.core.orchestrator import Orchestrator
        from app.core.planner import PlannerAgent
        from app.core.executor import ExecutorAgent
        from app.core.reasoner import Reasoner
        from app.tools.registry import ToolRegistry
        
        # 测试 ToolRegistry
        print("\n1. 测试 ToolRegistry...")
        registry = ToolRegistry()
        print(f"   [OK] ToolRegistry 初始化成功")
        
        # 测试 PlannerAgent
        print("\n2. 测试 PlannerAgent...")
        planner = PlannerAgent()
        print(f"   [OK] PlannerAgent 初始化成功")
        
        # 测试 ExecutorAgent
        print("\n3. 测试 ExecutorAgent...")
        executor = ExecutorAgent()
        print(f"   [OK] ExecutorAgent 初始化成功")
        
        # 测试 Reasoner
        print("\n4. 测试 Reasoner...")
        reasoner = Reasoner()
        print(f"   [OK] Reasoner 初始化成功")
        
        # 测试 Orchestrator
        print("\n5. 测试 Orchestrator...")
        orchestrator = Orchestrator(use_router=False)
        print(f"   [OK] Orchestrator 初始化成功")
        
        print("\n" + "=" * 60)
        print("所有组件初始化测试通过!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_structures():
    """测试数据结构"""
    print("\n" + "=" * 60)
    print("测试数据结构")
    print("=" * 60)
    
    try:
        from app.core.planner import Plan, SubTask
        from app.core.executor import ExecutionResult
        from app.core.reasoner import ReasoningResult, ChartSpec
        
        # 测试 SubTask
        print("\n1. 测试 SubTask...")
        subtask = SubTask(
            task_id="test_1",
            tool_name="news_search",
            params={"query": "test"},
            description="Test task",
            priority=1,
            confidence=0.8
        )
        print(f"   [OK] SubTask: {subtask.task_id} - {subtask.tool_name}")
        
        # 测试 Plan
        print("\n2. 测试 Plan...")
        plan = Plan(
            original_query="test query",
            subtasks=[subtask],
            reasoning="test reasoning"
        )
        print(f"   [OK] Plan: {len(plan.subtasks)} subtasks")
        
        # 测试 ReasoningResult
        print("\n3. 测试 ReasoningResult...")
        reasoning_result = ReasoningResult(
            reasoning="test reasoning",
            critique="test critique",
            confidence=0.85,
            key_insights=["insight 1", "insight 2"],
            chart_specs=[]
        )
        print(f"   [OK] ReasoningResult: confidence={reasoning_result.confidence}")
        
        # 测试 ChartSpec
        print("\n4. 测试 ChartSpec...")
        chart_spec = ChartSpec(
            chart_type="bar",
            title="Test Chart",
            x_label="X",
            y_label="Y",
            data=[{"label": "A", "value": 100}, {"label": "B", "value": 200}]
        )
        print(f"   [OK] ChartSpec: {chart_spec.title} ({chart_spec.chart_type})")
        
        print("\n" + "=" * 60)
        print("所有数据结构测试通过!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] 数据结构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_registry():
    """测试工具注册表"""
    print("\n" + "=" * 60)
    print("测试工具注册表")
    print("=" * 60)
    
    try:
        from app.tools.registry import ToolRegistry
        from app.tools.crawler_tool import CrawlerTool
        from app.tools.news_tool import NewsTool
        from app.tools.rag_tool import RAGTool
        
        # 创建工具注册表
        registry = ToolRegistry()
        
        # 注册工具
        print("\n1. 注册工具...")
        tools = [CrawlerTool(), NewsTool(), RAGTool()]
        for tool in tools:
            registry.register(tool)
            print(f"   [OK] 注册: {tool.name} - {tool.description[:50]}...")
        
        # 列出工具
        print("\n2. 已注册工具:")
        for tool_info in registry.list_tools():
            print(f"   - {tool_info['name']}: {tool_info['description'][:50]}...")
        
        # 获取工具
        print("\n3. 获取工具...")
        for tool_name in ["crawler", "news_search", "rag_retrieve"]:
            tool = registry.get(tool_name)
            if tool:
                print(f"   [OK] {tool_name}: {tool.description[:50]}...")
            else:
                print(f"   [FAIL] {tool_name}: 未找到")
        
        print("\n" + "=" * 60)
        print("工具注册表测试通过!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] 工具注册表测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Step 1 验证脚本")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("模块导入", test_imports()))
    results.append(("组件初始化", test_initialization()))
    results.append(("数据结构", test_data_structures()))
    results.append(("工具注册表", test_tool_registry()))
    
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
        print("\n恭喜! Step 1 基础框架验证成功!")
        print("可以运行 demo_step1.py 进行完整的任务演示（需要LLM API密钥）")
    else:
        print("\n请修复失败的测试后再继续")