"""
基准测试 - 3-Layer 架构验证
收集: 失败比例/Agent延迟/Token预算消耗
"""
import asyncio
import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.orchestrator import Orchestrator


async def main():
    query = "What are the key risks for Tesla investors in 2024?"

    print("=" * 60)
    print("  3-Layer Architecture Benchmark")
    print("=" * 60)
    print(f"Query: {query}")
    print()

    orch = Orchestrator(use_router=True)
    start = time.perf_counter()
    result = await orch.run(query)
    total_ms = (time.perf_counter() - start) * 1000

    # 基本统计
    print(f"Total Time: {total_ms/1000:.1f}s")
    print(f"Tasks: {result.subtask_count} total, {result.successful_tasks} success, {result.failed_tasks} failed")
    print(f"Success Rate: {result.successful_tasks/max(result.subtask_count,1)*100:.0f}%")
    print()

    # Layer 1: Planner
    print("--- Layer 1: Planner ---")
    if result.plan:
        for st in result.plan.subtasks:
            print(f"  {st.task_id}: [{st.tool_name}] p={st.priority} {st.description[:60]}")
    print()

    # Layer 2: Executor
    print("--- Layer 2: Executor ---")
    if result.exec_result:
        for tr in result.exec_result.task_results:
            icon = "OK" if tr.success else "FAIL"
            print(f"  [{icon}] {tr.task_id} ({tr.tool_name}) {tr.duration_ms:.0f}ms")
    print()

    # Layer 3: Synthesizer
    print("--- Layer 3: Synthesizer ---")
    if result.reasoning_result:
        print(f"  Reasoner: confidence={result.reasoning_result.confidence:.1%}, insights={len(result.reasoning_result.key_insights)}, charts={len(result.reasoning_result.chart_specs)}")
    if result.report:
        print(f"  Report: {result.report.title}")
        print(f"  Summary: {result.report.summary[:80]}...")
        print(f"  Findings: {len(result.report.analysis.key_findings)}")
        print(f"  Risks: {len(result.report.analysis.risk_factors)}")
        print(f"  Recommendations: {len(result.report.analysis.recommendations)}")
    print(f"  Charts rendered: {len(result.chart_paths)}")
    print()

    # Token Budget
    stats = orch.get_llm_stats()
    if "router" in stats:
        rs = stats["router"]
        print("--- Token Budget ---")
        print(f"  Total calls: {rs['call_count']}")
        print(f"  Total tokens: {rs['total_tokens']}")
        if "token_budget" in rs:
            for agent, budget in rs["token_budget"].items():
                if budget["max_tokens"] > 0:
                    print(f"  {agent}: {budget['used_tokens']}/{budget['max_tokens']} ({budget['utilization']})")
    print()

    # Report Preview
    if result.report:
        print("--- Report Preview ---")
        print(result.report.to_markdown()[:500])
        print("...")

    # 保存结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "total_ms": total_ms,
        "success_rate": result.successful_tasks / max(result.subtask_count, 1),
        "total_tokens": rs.get("total_tokens", 0) if "router" in (rs := stats.get("router", {})) else 0,
        "agent_stats": rs.get("agent_stats", {}),
        "token_budget": rs.get("token_budget", {}),
    }
    with open(os.path.join(os.path.dirname(__file__), "benchmark_result.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print("  Benchmark Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
