#!/usr/bin/env python3
"""
Step 1 Demo: 测试 Orchestrator + Planner + Executor + Reasoner 基础框架
"""
import asyncio
import os
import sys

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from app.core.orchestrator import Orchestrator
from app.utils.logger import get_logger

logger = get_logger("demo")


async def demo_task():
    """演示一个完整的任务流程"""
    print("=" * 60)
    print("Smart Finance Agent - Step 1 Demo")
    print("=" * 60)

    # 初始化 Orchestrator
    print("\n1. 初始化 Orchestrator...")
    orchestrator = Orchestrator(use_router=False)  # 不使用路由器，直接调用LLM

    # 测试查询
    query = "Analyze the current market trend for tech stocks in Q4 2024"

    print(f"\n2. 执行查询: {query}")
    print("-" * 60)

    try:
        # 运行任务
        result = await orchestrator.run(query)

        print("\n3. 执行结果:")
        print("-" * 60)
        print(f"查询: {result.query}")
        print(f"成功任务数: {result.successful_tasks}")
        print(f"失败任务数: {result.failed_tasks}")
        print(f"总任务数: {result.subtask_count}")
        print(f"总耗时: {result.total_duration_ms:.0f}ms")
        print(f"追踪ID: {result.trace_id}")

        print("\n4. 计划推理:")
        print("-" * 60)
        print(result.plan_reasoning[:500] if result.plan_reasoning else "无")

        print("\n5. 最终答案 (前500字符):")
        print("-" * 60)
        print(result.answer[:500] if result.answer else "无")

        if result.report:
            print("\n6. 报告摘要:")
            print("-" * 60)
            print(f"标题: {result.report.title}")
            print(f"摘要: {result.report.summary[:300]}...")

            print("\n7. 关键发现:")
            print("-" * 60)
            for i, finding in enumerate(result.report.analysis.key_findings[:5], 1):
                print(f"  {i}. {finding}")

        if result.reasoning_result:
            print("\n8. 推理结果:")
            print("-" * 60)
            print(f"置信度: {result.reasoning_result.confidence:.1%}")
            print(f"关键洞察数: {len(result.reasoning_result.key_insights)}")
            print(f"图表规格数: {len(result.reasoning_result.chart_specs)}")

            if result.reasoning_result.key_insights:
                print("\n关键洞察:")
                for i, insight in enumerate(result.reasoning_result.key_insights[:3], 1):
                    print(f"  {i}. {insight}")

        print("\n" + "=" * 60)
        print("Demo 完成!")
        print("=" * 60)

        return result

    except Exception as e:
        print(f"\n错误: {e}")
        logger.error(f"Demo failed: {e}", exc_info=True)
        return None


async def demo_streaming():
    """演示流式输出"""
    print("\n\n" + "=" * 60)
    print("流式输出 Demo")
    print("=" * 60)

    orchestrator = Orchestrator(use_router=False)
    query = "What are the key factors affecting semiconductor stocks?"

    print(f"\n查询: {query}")
    print("-" * 60)

    try:
        async for event in orchestrator.run_with_streaming(query):
            stage = event.get("stage", "")
            message = event.get("message", "")

            if stage == "planning":
                print(f"\n[规划] {message}")
            elif stage == "plan_ready":
                subtasks = event.get("subtasks", [])
                print(f"\n[计划就绪] {len(subtasks)} 个子任务:")
                for st in subtasks:
                    print(f"  - {st['id']}: {st['tool']} - {st['desc'][:50]}...")
            elif stage == "task_start":
                print(f"\n[任务开始] {event.get('task_id')}: {event.get('tool')}")
            elif stage == "task_done":
                status = "成功" if event.get("success") else "失败"
                print(f"\n[任务完成] {event.get('task_id')}: {status} ({event.get('duration_ms', 0):.0f}ms)")
            elif stage == "reasoning":
                print(f"\n[推理] {message}")
            elif stage == "reasoning_done":
                print(f"\n[推理完成] 置信度: {event.get('confidence', 0):.1%}")
            elif stage == "reporting":
                print(f"\n[报告生成] {message}")
            elif stage == "complete":
                print(f"\n[完成] 总耗时: {event.get('total_duration_ms', 0):.0f}ms")

        print("\n" + "=" * 60)
        print("流式输出 Demo 完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n错误: {e}")
        logger.error(f"Streaming demo failed: {e}", exc_info=True)


if __name__ == "__main__":
    print("开始 Step 1 Demo...")
    print("注意: 此Demo需要有效的LLM API密钥才能正常运行")
    print("请确保在 backend/.env 文件中配置了 MIMO_API_KEY\n")

    # 运行基础demo
    asyncio.run(demo_task())

    # 运行流式输出demo
    asyncio.run(demo_streaming())
