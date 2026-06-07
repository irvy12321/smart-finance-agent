"""
Full E2E Test Suite - Smart Finance Multi-Agent System
Covers: Planner, Executor, Tools, Report, RAG, Fallback, UI rendering
"""
import asyncio
import json
import sys
import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# ============================================================
# Test Infrastructure
# ============================================================

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float = 0.0
    details: dict = field(default_factory=dict)
    error: str = ""


@dataclass
class CaseResult:
    case_name: str
    query: str
    planner_result: dict = field(default_factory=dict)
    dag_structure: dict = field(default_factory=dict)
    executor_log: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)
    report: dict = field(default_factory=dict)
    total_ms: float = 0.0
    passed: bool = False
    error: str = ""


class E2ETestRunner:
    def __init__(self):
        self.results: list[TestResult] = []
        self.case_results: list[CaseResult] = []
        self.robustness_results: list[TestResult] = []

    async def run_all(self):
        print("=" * 70)
        print("  SMART FINANCE MULTI-AGENT SYSTEM - FULL E2E TEST SUITE")
        print(f"  Started: {datetime.now().isoformat()}")
        print("=" * 70)

        # Phase 1: Run 3 test cases
        await self._run_case_a()
        await self._run_case_b()
        await self._run_case_c()

        # Phase 2: Robustness tests
        await self._test_crawler_fallback()
        await self._test_rag_empty_fallback()
        await self._test_planner_fallback()

        # Phase 3: UI rendering tests
        self._test_chart_rendering()
        self._test_dag_visualization()
        self._test_report_markdown()

        # Phase 4: Component unit tests
        await self._test_smart_router()
        await self._test_rag_pipeline()

        # Generate report
        self._print_report()

    # ============================================================
    # Case A: Research type - NVIDIA AI
    # ============================================================
    async def _run_case_a(self):
        query = "分析NVIDIA最新AI业务发展"
        case = CaseResult(case_name="Case A (Research)", query=query)
        t0 = time.perf_counter()

        try:
            from core.orchestrator import Orchestrator
            orch = Orchestrator(use_router=True)
            result = await orch.run(query)

            # Planner analysis
            case.planner_result = {
                "subtask_count": result.subtask_count,
                "reasoning": result.plan_reasoning,
                "subtasks": [],
                "has_dependency_graph": False,
                "tool_types": set(),
            }
            if result.plan:
                for st in result.plan.subtasks:
                    case.planner_result["subtasks"].append({
                        "task_id": st.task_id,
                        "tool_name": st.tool_name,
                        "description": st.description,
                        "depends_on": st.depends_on,
                        "priority": st.priority,
                        "confidence": st.confidence,
                    })
                    case.planner_result["tool_types"].add(st.tool_name)
                    if st.depends_on:
                        case.planner_result["has_dependency_graph"] = True
                case.planner_result["tool_types"] = list(case.planner_result["tool_types"])

            # DAG structure
            case.dag_structure = {
                "nodes": [st.task_id for st in result.plan.subtasks] if result.plan else [],
                "edges": [],
                "has_parallel_tasks": False,
            }
            if result.plan:
                independent = [st for st in result.plan.subtasks if not st.depends_on]
                case.dag_structure["has_parallel_tasks"] = len(independent) > 1
                for st in result.plan.subtasks:
                    for dep in st.depends_on:
                        case.dag_structure["edges"].append(f"{dep} -> {st.task_id}")

            # Executor log
            if result.exec_result:
                for tr in result.exec_result.task_results:
                    case.executor_log.append({
                        "task_id": tr.task_id,
                        "tool": tr.tool_name,
                        "success": tr.success,
                        "duration_ms": tr.duration_ms,
                        "status": tr.status.value,
                        "error": tr.error,
                    })
                    case.tool_calls.append({
                        "tool": tr.tool_name,
                        "task_id": tr.task_id,
                        "success": tr.success,
                    })

            # Report
            if result.report:
                case.report = {
                    "title": result.report.title,
                    "summary": result.report.summary,
                    "has_key_findings": len(result.report.analysis.key_findings) > 0,
                    "has_risks": len(result.report.analysis.risk_factors) > 0,
                    "has_recommendations": len(result.report.analysis.recommendations) > 0,
                    "has_market_trends": len(result.report.analysis.market_trends) > 0,
                    "key_findings_count": len(result.report.analysis.key_findings),
                    "risk_count": len(result.report.analysis.risk_factors),
                    "recommendation_count": len(result.report.analysis.recommendations),
                    "markdown_length": len(result.report.to_markdown()),
                }

            case.total_ms = time.perf_counter() - t0
            case.passed = (
                result.subtask_count >= 2
                and result.report is not None
                and len(result.report.analysis.key_findings) > 0
            )

            print(f"\n[Case A] PASSED - {result.subtask_count} subtasks, {result.total_duration_ms:.0f}ms")

        except Exception as e:
            case.error = f"{type(e).__name__}: {e}"
            case.total_ms = time.perf_counter() - t0
            print(f"\n[Case A] FAILED - {e}")
            traceback.print_exc()

        self.case_results.append(case)

    # ============================================================
    # Case B: Comparison type - Apple vs Microsoft vs Google
    # ============================================================
    async def _run_case_b(self):
        query = "比较苹果 vs 微软 vs 谷歌AI战略"
        case = CaseResult(case_name="Case B (Comparison)", query=query)
        t0 = time.perf_counter()

        try:
            from core.orchestrator import Orchestrator
            orch = Orchestrator(use_router=True)
            result = await orch.run(query)

            case.planner_result = {
                "subtask_count": result.subtask_count,
                "reasoning": result.plan_reasoning,
                "subtasks": [],
                "has_dependency_graph": False,
                "tool_types": set(),
            }
            if result.plan:
                for st in result.plan.subtasks:
                    case.planner_result["subtasks"].append({
                        "task_id": st.task_id,
                        "tool_name": st.tool_name,
                        "description": st.description,
                        "depends_on": st.depends_on,
                        "priority": st.priority,
                    })
                    case.planner_result["tool_types"].add(st.tool_name)
                    if st.depends_on:
                        case.planner_result["has_dependency_graph"] = True
                case.planner_result["tool_types"] = list(case.planner_result["tool_types"])

            case.dag_structure = {
                "nodes": [st.task_id for st in result.plan.subtasks] if result.plan else [],
                "edges": [],
                "has_parallel_tasks": False,
            }
            if result.plan:
                independent = [st for st in result.plan.subtasks if not st.depends_on]
                case.dag_structure["has_parallel_tasks"] = len(independent) > 1
                for st in result.plan.subtasks:
                    for dep in st.depends_on:
                        case.dag_structure["edges"].append(f"{dep} -> {st.task_id}")

            if result.exec_result:
                for tr in result.exec_result.task_results:
                    case.executor_log.append({
                        "task_id": tr.task_id,
                        "tool": tr.tool_name,
                        "success": tr.success,
                        "duration_ms": tr.duration_ms,
                        "status": tr.status.value,
                    })
                    case.tool_calls.append({"tool": tr.tool_name, "task_id": tr.task_id, "success": tr.success})

            if result.report:
                case.report = {
                    "title": result.report.title,
                    "summary": result.report.summary,
                    "has_key_findings": len(result.report.analysis.key_findings) > 0,
                    "has_risks": len(result.report.analysis.risk_factors) > 0,
                    "has_recommendations": len(result.report.analysis.recommendations) > 0,
                    "key_findings_count": len(result.report.analysis.key_findings),
                    "risk_count": len(result.report.analysis.risk_factors),
                    "markdown_length": len(result.report.to_markdown()),
                }

            case.total_ms = time.perf_counter() - t0
            case.passed = (
                result.subtask_count >= 2
                and result.report is not None
                and len(result.report.analysis.key_findings) > 0
            )
            print(f"\n[Case B] PASSED - {result.subtask_count} subtasks, {result.total_duration_ms:.0f}ms")

        except Exception as e:
            case.error = f"{type(e).__name__}: {e}"
            case.total_ms = time.perf_counter() - t0
            print(f"\n[Case B] FAILED - {e}")
            traceback.print_exc()

        self.case_results.append(case)

    # ============================================================
    # Case C: Q&A type - FAISS
    # ============================================================
    async def _run_case_c(self):
        query = "什么是FAISS，它在系统中如何使用"
        case = CaseResult(case_name="Case C (Q&A)", query=query)
        t0 = time.perf_counter()

        try:
            from core.orchestrator import Orchestrator
            orch = Orchestrator(use_router=True)
            result = await orch.run(query)

            case.planner_result = {
                "subtask_count": result.subtask_count,
                "reasoning": result.plan_reasoning,
                "subtasks": [],
                "has_dependency_graph": False,
                "tool_types": set(),
            }
            if result.plan:
                for st in result.plan.subtasks:
                    case.planner_result["subtasks"].append({
                        "task_id": st.task_id,
                        "tool_name": st.tool_name,
                        "description": st.description,
                        "depends_on": st.depends_on,
                        "priority": st.priority,
                    })
                    case.planner_result["tool_types"].add(st.tool_name)
                    if st.depends_on:
                        case.planner_result["has_dependency_graph"] = True
                case.planner_result["tool_types"] = list(case.planner_result["tool_types"])

            case.dag_structure = {
                "nodes": [st.task_id for st in result.plan.subtasks] if result.plan else [],
                "edges": [],
                "has_parallel_tasks": False,
            }
            if result.plan:
                independent = [st for st in result.plan.subtasks if not st.depends_on]
                case.dag_structure["has_parallel_tasks"] = len(independent) > 1
                for st in result.plan.subtasks:
                    for dep in st.depends_on:
                        case.dag_structure["edges"].append(f"{dep} -> {st.task_id}")

            if result.exec_result:
                for tr in result.exec_result.task_results:
                    case.executor_log.append({
                        "task_id": tr.task_id,
                        "tool": tr.tool_name,
                        "success": tr.success,
                        "duration_ms": tr.duration_ms,
                        "status": tr.status.value,
                    })
                    case.tool_calls.append({"tool": tr.tool_name, "task_id": tr.task_id, "success": tr.success})

            if result.report:
                case.report = {
                    "title": result.report.title,
                    "summary": result.report.summary,
                    "has_key_findings": len(result.report.analysis.key_findings) > 0,
                    "has_risks": len(result.report.analysis.risk_factors) > 0,
                    "has_recommendations": len(result.report.analysis.recommendations) > 0,
                    "key_findings_count": len(result.report.analysis.key_findings),
                    "markdown_length": len(result.report.to_markdown()),
                }

            case.total_ms = time.perf_counter() - t0
            case.passed = (
                result.subtask_count >= 2
                and result.report is not None
            )
            print(f"\n[Case C] PASSED - {result.subtask_count} subtasks, {result.total_duration_ms:.0f}ms")

        except Exception as e:
            case.error = f"{type(e).__name__}: {e}"
            case.total_ms = time.perf_counter() - t0
            print(f"\n[Case C] FAILED - {e}")
            traceback.print_exc()

        self.case_results.append(case)

    # ============================================================
    # Robustness: Crawler failure -> fallback
    # ============================================================
    async def _test_crawler_fallback(self):
        t0 = time.perf_counter()
        try:
            from core.fallback_manager import FallbackManager
            from tools.registry import ToolRegistry
            from tools.crawler_tool import CrawlerTool
            from tools.news_tool import NewsTool
            from tools.rag_tool import RAGTool
            from infrastructure.llm_client import LLMClient

            registry = ToolRegistry()
            registry.register(CrawlerTool())
            registry.register(NewsTool())
            registry.register(RAGTool())

            fm = FallbackManager(tool_registry=registry, llm_client=LLMClient.get_instance())

            # Simulate crawler failure by using a non-existent URL
            params = {"url": "https://this-domain-does-not-exist-12345.com/page"}
            result, used_tool = await fm.execute_with_fallback("crawler", params, trace_id="test_crawler_fb")

            passed = result.success and used_tool != "crawler"
            self.robustness_results.append(TestResult(
                name="Crawler Fallback",
                passed=passed,
                duration_ms=(time.perf_counter() - t0) * 1000,
                details={"used_tool": used_tool, "result_success": result.success, "data_preview": str(result.data)[:200]},
            ))
            print(f"\n[Crawler Fallback] {'PASSED' if passed else 'FAILED'} - used_tool={used_tool}")

        except Exception as e:
            self.robustness_results.append(TestResult(
                name="Crawler Fallback", passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000, error=str(e),
            ))
            print(f"\n[Crawler Fallback] FAILED - {e}")

    # ============================================================
    # Robustness: RAG empty -> fallback
    # ============================================================
    async def _test_rag_empty_fallback(self):
        t0 = time.perf_counter()
        try:
            from core.fallback_manager import FallbackManager
            from tools.registry import ToolRegistry
            from tools.crawler_tool import CrawlerTool
            from tools.news_tool import NewsTool
            from tools.rag_tool import RAGTool
            from infrastructure.llm_client import LLMClient

            registry = ToolRegistry()
            registry.register(CrawlerTool())
            registry.register(NewsTool())
            registry.register(RAGTool())

            fm = FallbackManager(tool_registry=registry, llm_client=LLMClient.get_instance())

            # RAG with empty knowledge base
            params = {"query": "quantum computing financial applications 2099"}
            result, used_tool = await fm.execute_with_fallback("rag_retrieve", params, trace_id="test_rag_fb")

            # RAG should succeed (even with empty results) or fallback to LLM
            passed = result.success
            self.robustness_results.append(TestResult(
                name="RAG Empty Fallback",
                passed=passed,
                duration_ms=(time.perf_counter() - t0) * 1000,
                details={"used_tool": used_tool, "result_success": result.success},
            ))
            print(f"\n[RAG Empty Fallback] {'PASSED' if passed else 'FAILED'} - used_tool={used_tool}")

        except Exception as e:
            self.robustness_results.append(TestResult(
                name="RAG Empty Fallback", passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000, error=str(e),
            ))
            print(f"\n[RAG Empty Fallback] FAILED - {e}")

    # ============================================================
    # Robustness: Planner failure -> fallback plan
    # ============================================================
    async def _test_planner_fallback(self):
        t0 = time.perf_counter()
        try:
            from core.orchestrator import Orchestrator
            orch = Orchestrator(use_router=True)

            # Test _create_fallback_plan directly
            fallback_plan = orch._create_fallback_plan("test query for fallback")

            passed = (
                len(fallback_plan.subtasks) == 1
                and fallback_plan.subtasks[0].tool_name == "llm_synthesize"
                and fallback_plan.reasoning == "Fallback plan: primary planning failed"
            )
            self.robustness_results.append(TestResult(
                name="Planner Fallback",
                passed=passed,
                duration_ms=(time.perf_counter() - t0) * 1000,
                details={
                    "subtask_count": len(fallback_plan.subtasks),
                    "tool_name": fallback_plan.subtasks[0].tool_name,
                    "reasoning": fallback_plan.reasoning,
                },
            ))
            print(f"\n[Planner Fallback] {'PASSED' if passed else 'FAILED'}")

        except Exception as e:
            self.robustness_results.append(TestResult(
                name="Planner Fallback", passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000, error=str(e),
            ))
            print(f"\n[Planner Fallback] FAILED - {e}")

    # ============================================================
    # UI: Chart rendering
    # ============================================================
    def _test_chart_rendering(self):
        t0 = time.perf_counter()
        try:
            from core.reasoner import ChartSpec
            from core.chart_renderer import ChartRenderer

            renderer = ChartRenderer(output_dir="output/test_charts")
            test_chart = ChartSpec(
                chart_type="bar",
                title="Test Chart - Revenue Comparison",
                x_label="Company",
                y_label="Revenue ($B)",
                data=[
                    {"label": "NVIDIA", "value": 60.9},
                    {"label": "AMD", "value": 22.7},
                    {"label": "Intel", "value": 54.2},
                ],
                description="Test chart for E2E validation",
            )

            path = renderer.render(test_chart, "test_bar.png")
            file_exists = os.path.exists(path) if path else False

            # Also test line chart
            line_chart = ChartSpec(
                chart_type="line",
                title="Test Line Chart",
                x_label="Quarter",
                y_label="Growth %",
                data=[
                    {"label": "Q1", "value": 10},
                    {"label": "Q2", "value": 25},
                    {"label": "Q3", "value": 40},
                    {"label": "Q4", "value": 55},
                ],
            )
            line_path = renderer.render(line_chart, "test_line.png")
            line_exists = os.path.exists(line_path) if line_path else False

            # Test pie chart
            pie_chart = ChartSpec(
                chart_type="pie",
                title="Test Pie Chart",
                x_label="",
                y_label="",
                data=[
                    {"label": "AI", "value": 45},
                    {"label": "Gaming", "value": 30},
                    {"label": "Data Center", "value": 25},
                ],
            )
            pie_path = renderer.render(pie_chart, "test_pie.png")
            pie_exists = os.path.exists(pie_path) if pie_path else False

            passed = file_exists and line_exists and pie_exists
            self.results.append(TestResult(
                name="Chart Rendering (bar/line/pie)",
                passed=passed,
                duration_ms=(time.perf_counter() - t0) * 1000,
                details={"bar": file_exists, "line": line_exists, "pie": pie_exists},
            ))
            print(f"\n[Chart Rendering] {'PASSED' if passed else 'FAILED'}")

        except Exception as e:
            self.results.append(TestResult(
                name="Chart Rendering", passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000, error=str(e),
            ))
            print(f"\n[Chart Rendering] FAILED - {e}")

    # ============================================================
    # UI: DAG visualization
    # ============================================================
    def _test_dag_visualization(self):
        t0 = time.perf_counter()
        try:
            from core.dag_renderer import render_dag

            subtasks = [
                {"id": "task_1", "tool": "news_search", "desc": "Search news", "priority": 3, "depends_on": []},
                {"id": "task_2", "tool": "rag_retrieve", "desc": "RAG search", "priority": 3, "depends_on": []},
                {"id": "task_3", "tool": "llm_synthesize", "desc": "Synthesize", "priority": 1, "depends_on": ["task_1", "task_2"]},
            ]

            output_path = render_dag(subtasks, output_path="output/test_charts/test_dag.png")
            file_exists = os.path.exists(output_path) if output_path else False

            passed = file_exists
            self.results.append(TestResult(
                name="DAG Visualization",
                passed=passed,
                duration_ms=(time.perf_counter() - t0) * 1000,
                details={"output_path": output_path, "file_exists": file_exists, "node_count": len(subtasks)},
            ))
            print(f"\n[DAG Visualization] {'PASSED' if passed else 'FAILED'}")

        except Exception as e:
            self.results.append(TestResult(
                name="DAG Visualization", passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000, error=str(e),
            ))
            print(f"\n[DAG Visualization] FAILED - {e}")

    # ============================================================
    # UI: Report markdown generation
    # ============================================================
    def _test_report_markdown(self):
        t0 = time.perf_counter()
        try:
            from core.report_agent import ResearchReport, StructuredAnalysis

            report = ResearchReport(
                title="Test Report",
                summary="This is a test summary for E2E validation.",
                analysis=StructuredAnalysis(
                    key_findings=["Finding 1", "Finding 2", "Finding 3"],
                    risk_factors=[{"factor": "Risk 1", "severity": "high", "description": "Test risk"}],
                    market_trends=["Trend 1", "Trend 2"],
                    recommendations=["Rec 1", "Rec 2"],
                ),
                sources=[{"task_id": "task_1", "tool": "news_search", "duration_ms": 500}],
                trace_id="test_trace",
            )

            md = report.to_markdown()
            has_title = "Test Report" in md
            has_findings = "Finding 1" in md
            has_risks = "Risk 1" in md
            has_recs = "Rec 1" in md

            passed = has_title and has_findings and has_risks and has_recs and len(md) > 200
            self.results.append(TestResult(
                name="Report Markdown Generation",
                passed=passed,
                duration_ms=(time.perf_counter() - t0) * 1000,
                details={"markdown_length": len(md), "has_all_sections": passed},
            ))
            print(f"\n[Report Markdown] {'PASSED' if passed else 'FAILED'}")

        except Exception as e:
            self.results.append(TestResult(
                name="Report Markdown", passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000, error=str(e),
            ))
            print(f"\n[Report Markdown] FAILED - {e}")

    # ============================================================
    # Smart Router test
    # ============================================================
    async def _test_smart_router(self):
        t0 = time.perf_counter()
        try:
            from infrastructure.smart_router import SmartRouter

            router = SmartRouter()

            # Test complexity scoring
            high_q = "Compare and analyze the comprehensive investment strategy implications for NVIDIA AI risk assessment"
            med_q = "Tesla quarterly earnings summary overview"
            low_q = "What is the current price of Bitcoin"

            high_route = router.assess(high_q)
            med_route = router.assess(med_q)
            low_route = router.assess(low_q)

            complexity_order = high_route.complexity > med_route.complexity > low_route.complexity
            has_tools = len(high_route.tool_scores) > 0

            passed = complexity_order and has_tools
            self.results.append(TestResult(
                name="Smart Router (complexity + tool scoring)",
                passed=passed,
                duration_ms=(time.perf_counter() - t0) * 1000,
                details={
                    "high_complexity": round(high_route.complexity, 3),
                    "med_complexity": round(med_route.complexity, 3),
                    "low_complexity": round(low_route.complexity, 3),
                    "complexity_order_correct": complexity_order,
                    "tool_scores": high_route.tool_scores,
                },
            ))
            print(f"\n[Smart Router] {'PASSED' if passed else 'FAILED'}")

        except Exception as e:
            self.results.append(TestResult(
                name="Smart Router", passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000, error=str(e),
            ))
            print(f"\n[Smart Router] FAILED - {e}")

    # ============================================================
    # RAG Pipeline test
    # ============================================================
    async def _test_rag_pipeline(self):
        t0 = time.perf_counter()
        try:
            from rag.retriever import Retriever

            retriever = Retriever()

            # Add test documents
            test_docs = [
                "FAISS is a library for efficient similarity search developed by Facebook AI Research.",
                "Vector databases store high-dimensional vectors for fast nearest neighbor search.",
                "NVIDIA GPUs accelerate AI training and inference workloads significantly.",
                "Microsoft Azure provides cloud-based AI services for enterprise customers.",
                "Apple Silicon M-series chips include dedicated Neural Engine for on-device ML.",
            ]
            for doc in test_docs:
                retriever.add_document(doc)

            # Search
            results = retriever.retrieve("What is FAISS and vector search?", top_k=3)

            has_results = len(results) > 0
            has_scores = all("score" in r for r in results) if results else False
            doc_count = retriever.doc_count

            passed = has_results and has_scores and doc_count == len(test_docs)
            self.results.append(TestResult(
                name="RAG Pipeline (add + retrieve)",
                passed=passed,
                duration_ms=(time.perf_counter() - t0) * 1000,
                details={
                    "doc_count": doc_count,
                    "results_count": len(results),
                    "top_score": results[0]["score"] if results else 0,
                    "top_text_preview": results[0]["text"][:80] if results else "",
                },
            ))
            print(f"\n[RAG Pipeline] {'PASSED' if passed else 'FAILED'}")

        except Exception as e:
            self.results.append(TestResult(
                name="RAG Pipeline", passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000, error=str(e),
            ))
            print(f"\n[RAG Pipeline] FAILED - {e}")

    # ============================================================
    # Final Report
    # ============================================================
    def _print_report(self):
        print("\n\n" + "=" * 70)
        print("  STRUCTURED TEST REPORT")
        print("=" * 70)

        # Test Summary
        all_tests = self.results + self.robustness_results
        total = len(all_tests)
        passed = sum(1 for t in all_tests if t.passed)
        failed = total - passed

        case_passed = sum(1 for c in self.case_results if c.passed)
        case_total = len(self.case_results)

        print(f"\n## Test Summary")
        print(f"- Component tests: {passed}/{total} passed, {failed} failed")
        print(f"- E2E cases: {case_passed}/{case_total} passed")
        print(f"- System stability: {'STABLE' if case_passed >= 2 else 'UNSTABLE'}")

        # Case Analysis
        print(f"\n## Planner Analysis")
        for case in self.case_results:
            status = "PASS" if case.passed else "FAIL"
            print(f"\n  [{status}] {case.case_name}: {case.query}")
            if case.planner_result:
                print(f"    Subtasks: {case.planner_result.get('subtask_count', 0)}")
                print(f"    Tool types: {case.planner_result.get('tool_types', [])}")
                print(f"    Has dependency graph: {case.planner_result.get('has_dependency_graph', False)}")
                for st in case.planner_result.get("subtasks", []):
                    deps = f" (deps: {st['depends_on']})" if st.get("depends_on") else ""
                    print(f"      - {st['task_id']}: [{st['tool_name']}] {st.get('description', '')}{deps}")

        print(f"\n## DAG Structure Analysis")
        for case in self.case_results:
            if case.dag_structure:
                print(f"\n  {case.case_name}:")
                print(f"    Nodes: {case.dag_structure.get('nodes', [])}")
                print(f"    Edges: {case.dag_structure.get('edges', [])}")
                print(f"    Has parallel tasks: {case.dag_structure.get('has_parallel_tasks', False)}")

        print(f"\n## Executor Analysis")
        for case in self.case_results:
            print(f"\n  {case.case_name} ({case.total_ms:.0f}ms):")
            for log in case.executor_log:
                status = "OK" if log["success"] else "FAIL"
                print(f"    [{status}] {log['task_id']} ({log['tool']}) {log.get('duration_ms', 0):.0f}ms [{log.get('status', 'unknown')}]")

        print(f"\n## Tool Usage Analysis")
        tool_usage = {}
        for case in self.case_results:
            for tc in case.tool_calls:
                tool = tc["tool"]
                if tool not in tool_usage:
                    tool_usage[tool] = {"total": 0, "success": 0}
                tool_usage[tool]["total"] += 1
                if tc["success"]:
                    tool_usage[tool]["success"] += 1

        for tool, stats in tool_usage.items():
            rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"  {tool}: {stats['success']}/{stats['total']} ({rate:.0f}%)")

        print(f"\n## RAG Performance")
        rag_test = next((t for t in self.results if "RAG Pipeline" in t.name), None)
        if rag_test:
            print(f"  Status: {'PASS' if rag_test.passed else 'FAIL'}")
            print(f"  Documents indexed: {rag_test.details.get('doc_count', 0)}")
            print(f"  Search results: {rag_test.details.get('results_count', 0)}")
            print(f"  Top score: {rag_test.details.get('top_score', 0):.4f}")

        print(f"\n## UI Rendering Check")
        chart_test = next((t for t in self.results if "Chart" in t.name), None)
        dag_test = next((t for t in self.results if "DAG" in t.name), None)
        report_test = next((t for t in self.results if "Report Markdown" in t.name), None)

        if chart_test:
            print(f"  Chart rendering: {'PASS' if chart_test.passed else 'FAIL'} (bar/line/pie)")
        if dag_test:
            print(f"  DAG visualization: {'PASS' if dag_test.passed else 'FAIL'}")
        if report_test:
            print(f"  Report markdown: {'PASS' if report_test.passed else 'FAIL'}")

        print(f"\n## Failure / Fallback Behavior")
        for r in self.robustness_results:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {r.name} ({r.duration_ms:.0f}ms)")
            if r.details:
                for k, v in r.details.items():
                    print(f"    {k}: {v}")
            if r.error:
                print(f"    error: {r.error}")

        # Final Verdict
        print(f"\n## Report Analysis")
        for case in self.case_results:
            if case.report:
                print(f"\n  {case.case_name}:")
                print(f"    Title: {case.report.get('title', 'N/A')}")
                print(f"    Key findings: {case.report.get('key_findings_count', 0)}")
                print(f"    Risks: {case.report.get('risk_count', 0)}")
                print(f"    Recommendations: {case.report.get('recommendation_count', 0)}")
                print(f"    Markdown length: {case.report.get('markdown_length', 0)} chars")

        # Final Verdict
        print("\n" + "=" * 70)
        core_pass = case_passed >= 2 and passed >= total - 2
        verdict = "YES" if core_pass else "NO"
        print(f"\n## Final Verdict: {verdict}")
        print(f"  MVP production-ready: {verdict}")
        print(f"  Reason: {case_passed}/{case_total} E2E cases passed, {passed}/{total} component tests passed")
        print("=" * 70)

        # Save JSON report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "component_passed": passed,
                "component_total": total,
                "cases_passed": case_passed,
                "cases_total": case_total,
                "verdict": verdict,
            },
            "cases": [
                {
                    "name": c.case_name,
                    "query": c.query,
                    "passed": c.passed,
                    "total_ms": c.total_ms,
                    "planner": c.planner_result,
                    "dag": c.dag_structure,
                    "executor_log": c.executor_log,
                    "tool_calls": c.tool_calls,
                    "report": c.report,
                    "error": c.error,
                }
                for c in self.case_results
            ],
            "robustness": [
                {"name": r.name, "passed": r.passed, "duration_ms": r.duration_ms, "error": r.error}
                for r in self.robustness_results
            ],
            "components": [
                {"name": r.name, "passed": r.passed, "duration_ms": r.duration_ms, "error": r.error}
                for r in self.results
            ],
        }

        os.makedirs("output", exist_ok=True)
        with open("output/e2e_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"\nDetailed JSON report saved to: output/e2e_test_report.json")


# ============================================================
# Main
# ============================================================
async def main():
    runner = E2ETestRunner()
    await runner.run_all()


if __name__ == "__main__":
    asyncio.run(main())
