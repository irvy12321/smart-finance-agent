import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.orchestrator import Orchestrator
from utils.logger import get_logger

logger = get_logger("main")


async def run_cli():
    orchestrator = Orchestrator(use_router=True)

    print("\n" + "=" * 60)
    print("  Smart Finance Research Agent")
    print("  Multi-Agent System with LiteLLM Router")
    print("=" * 60)
    print("Type your research question (or 'quit' to exit):\n")

    while True:
        try:
            query = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query or query.lower() in ("quit", "exit", "q"):
            break

        print("\nProcessing...\n")

        try:
            result = await orchestrator.run(query)

            print("\n" + "-" * 60)
            print("RESEARCH REPORT")
            print("-" * 60)

            if result.report:
                print(result.report.to_markdown())
            else:
                print(f"\n{result.answer}\n")

            print("-" * 60)
            print(f"Tasks: {result.subtask_count} total, {result.successful_tasks} succeeded, {result.failed_tasks} failed")
            print(f"Time: {result.total_duration_ms:.0f}ms | Trace: {result.trace_id}")

            if result.reasoning_result:
                print(f"Reasoning Confidence: {result.reasoning_result.confidence:.1%}")
                if result.reasoning_result.key_insights:
                    print("Key Insights:")
                    for insight in result.reasoning_result.key_insights:
                        print(f"  - {insight}")

            # 显示 LLM 统计
            stats = orchestrator.get_llm_stats()
            if "router" in stats:
                print(f"LLM Stats: {stats['router']['call_count']} calls, {stats['router']['total_tokens']} tokens")

            print("-" * 60 + "\n")

        except Exception as e:
            logger.error(f"Run failed: {e}")
            print(f"\nError: {e}\n")

    print("Goodbye!")


def run_streamlit():
    import subprocess
    ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", ui_path])


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "cli"

    if mode == "ui":
        run_streamlit()
    else:
        asyncio.run(run_cli())
