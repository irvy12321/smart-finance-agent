"""Re-run failed E2E cases with debug logging"""
import asyncio
import sys
import os
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from utils.logger import get_logger
logger = get_logger("rerun_test")
import logging
logging.getLogger().setLevel(logging.INFO)

async def run_case(name, query):
    print(f"\n{'='*60}")
    print(f"  {name}: {query}")
    print(f"{'='*60}")
    t0 = time.perf_counter()
    try:
        from core.orchestrator import Orchestrator
        orch = Orchestrator(use_router=True)
        result = await orch.run(query)
        elapsed = time.perf_counter() - t0

        print(f"\n  Duration: {elapsed:.1f}s (internal: {result.total_duration_ms:.0f}ms)")
        print(f"  Subtasks: {result.subtask_count}")
        print(f"  Successful: {result.successful_tasks}")
        print(f"  Failed: {result.failed_tasks}")

        if result.plan:
            print(f"\n  Plan reasoning: {result.plan_reasoning[:200]}")
            print(f"\n  Subtasks:")
            for st in result.plan.subtasks:
                deps = f" -> depends_on: {st.depends_on}" if st.depends_on else ""
                print(f"    {st.task_id}: [{st.tool_name}] {st.description}{deps}")

        if result.exec_result:
            print(f"\n  Execution results:")
            for tr in result.exec_result.task_results:
                status = "OK" if tr.success else "FAIL"
                print(f"    [{status}] {tr.task_id} ({tr.tool_name}) {tr.duration_ms:.0f}ms [{tr.status.value}]")
                if tr.error:
                    print(f"      error: {tr.error[:200]}")

        if result.report:
            print(f"\n  Report: {result.report.title}")
            print(f"  Summary: {result.report.summary[:200]}")
            print(f"  Key findings: {result.report.analysis.key_findings}")
            print(f"  Risks: {len(result.report.analysis.risk_factors)}")
            print(f"  Recommendations: {len(result.report.analysis.recommendations)}")

        passed = result.subtask_count >= 2 and result.report is not None and len(result.report.analysis.key_findings) > 0
        print(f"\n  Result: {'PASSED' if passed else 'FAILED'}")
        return passed

    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f"\n  EXCEPTION after {elapsed:.1f}s: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

async def main():
    results = {}
    # Re-run Case B with slightly different phrasing (may help planner)
    results["Case B"] = await run_case("Case B (Comparison)", "比较苹果 vs 微软 vs 谷歌AI战略")
    # Re-run Case C
    results["Case C"] = await run_case("Case C (Q&A)", "什么是FAISS，它在系统中如何使用")

    print(f"\n{'='*60}")
    print(f"  RE-RUN SUMMARY")
    print(f"{'='*60}")
    for name, passed in results.items():
        print(f"  {name}: {'PASSED' if passed else 'FAILED'}")
    print(f"  Overall: {sum(results.values())}/{len(results)} passed")

if __name__ == "__main__":
    asyncio.run(main())
