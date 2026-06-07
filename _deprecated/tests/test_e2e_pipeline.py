"""
E2E Pipeline Tests
Tests full Orchestrator pipeline with 3 real-world queries
All tests run offline with fully mocked LLM
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.orchestrator import RunResult

MOCK_EXECUTOR_SYNTHESIZE_RESPONSE = (
    "## AI Industry Analysis\n\n"
    "The AI industry is experiencing unprecedented growth driven by generative AI adoption. "
    "Key players are investing heavily in AI infrastructure. "
    "The market is expected to reach $500B by 2027."
)


# ============================================================
# Mock response factories for each query type
# ============================================================

def _planner_response_multi_tool():
    """Plan with news + RAG + synthesis"""
    return json.dumps({
        "reasoning": "Multi-source research needed",
        "subtasks": [
            {
                "task_id": "task_1",
                "tool_name": "news_search",
                "params": {"query": "AI industry latest news 2025"},
                "description": "Search recent AI industry news",
                "depends_on": [],
                "priority": 3,
                "tool_priority_score": 0.9,
                "reasoning": "news for current events",
                "confidence": 0.85,
            },
            {
                "task_id": "task_2",
                "tool_name": "rag_retrieve",
                "params": {"query": "AI industry analysis history"},
                "description": "Retrieve historical analysis",
                "depends_on": [],
                "priority": 3,
                "tool_priority_score": 0.7,
                "reasoning": "local knowledge for context",
                "confidence": 0.7,
            },
            {
                "task_id": "task_3",
                "tool_name": "llm_synthesize",
                "params": {"prompt": "Comprehensive AI industry analysis"},
                "description": "Synthesize all findings",
                "depends_on": ["task_1", "task_2"],
                "priority": 1,
                "tool_priority_score": 0.95,
                "reasoning": "final synthesis",
                "confidence": 0.9,
            },
        ],
    })


def _planner_response_comparison():
    """Plan for company comparison with multiple data tasks"""
    return json.dumps({
        "reasoning": "Comparison requires multiple data sources per company",
        "subtasks": [
            {
                "task_id": "task_1",
                "tool_name": "news_search",
                "params": {"query": "Apple AI strategy 2025"},
                "description": "Search Apple AI news",
                "depends_on": [],
                "priority": 3,
                "tool_priority_score": 0.85,
                "reasoning": "current Apple AI developments",
                "confidence": 0.8,
            },
            {
                "task_id": "task_2",
                "tool_name": "news_search",
                "params": {"query": "Microsoft AI strategy 2025"},
                "description": "Search Microsoft AI news",
                "depends_on": [],
                "priority": 3,
                "tool_priority_score": 0.85,
                "reasoning": "current Microsoft AI developments",
                "confidence": 0.8,
            },
            {
                "task_id": "task_3",
                "tool_name": "rag_retrieve",
                "params": {"query": "Google AI strategy comparison"},
                "description": "Search Google AI in knowledge base",
                "depends_on": [],
                "priority": 3,
                "tool_priority_score": 0.7,
                "reasoning": "historical Google AI context",
                "confidence": 0.7,
            },
            {
                "task_id": "task_4",
                "tool_name": "llm_synthesize",
                "params": {"prompt": "Compare Apple vs Microsoft vs Google AI strategies"},
                "description": "Comparative synthesis",
                "depends_on": ["task_1", "task_2", "task_3"],
                "priority": 1,
                "tool_priority_score": 0.95,
                "reasoning": "final comparison",
                "confidence": 0.9,
            },
        ],
    })


def _planner_response_simple():
    """Simple plan for Q&A"""
    return json.dumps({
        "reasoning": "Simple explanation query - RAG plus synthesis",
        "subtasks": [
            {
                "task_id": "task_1",
                "tool_name": "rag_retrieve",
                "params": {"query": "FAISS vector database explanation"},
                "description": "Search for FAISS documentation",
                "depends_on": [],
                "priority": 3,
                "tool_priority_score": 0.8,
                "reasoning": "RAG best for technical explanations",
                "confidence": 0.8,
            },
            {
                "task_id": "task_2",
                "tool_name": "llm_synthesize",
                "params": {"prompt": "Explain FAISS in simple terms"},
                "description": "Generate explanation",
                "depends_on": ["task_1"],
                "priority": 1,
                "tool_priority_score": 0.95,
                "reasoning": "synthesis for clear explanation",
                "confidence": 0.9,
            },
        ],
    })


def _reasoner_response():
    return json.dumps({
        "reasoning": "Analysis shows strong market position across key metrics.",
        "key_insights": ["Market leadership in key segments", "Strong growth trajectory"],
        "confidence": 0.8,
        "critique": "Limited real-time data",
        "charts": [
            {
                "chart_type": "bar",
                "title": "Market Comparison",
                "x_label": "Company",
                "y_label": "Market Share (%)",
                "data": [
                    {"label": "Company A", "value": 35},
                    {"label": "Company B", "value": 28},
                    {"label": "Company C", "value": 22},
                ],
            }
        ],
    })


def _report_response():
    return json.dumps({
        "title": "Comprehensive Analysis Report",
        "summary": "Detailed analysis reveals significant trends and opportunities in the market.",
        "key_findings": [
            "Strong growth in AI sector",
            "Competitive landscape intensifying",
            "Regulatory environment evolving",
        ],
        "risk_factors": [
            {"factor": "Market Volatility", "severity": "medium", "description": "Uncertain macro conditions"},
        ],
        "market_trends": [
            "AI adoption accelerating",
            "Cloud infrastructure demand growing",
        ],
        "recommendations": [
            "Diversify portfolio exposure",
            "Monitor regulatory developments",
        ],
    })


def _make_router_side_effect(planner_resp, reasoner_resp=None, report_resp=None, synth_resp=None):
    """Create router.complete side_effect for specific pipeline stages"""
    reasoner_resp = reasoner_resp or _reasoner_response()
    report_resp = report_resp or _report_response()
    synth_resp = synth_resp or MOCK_EXECUTOR_SYNTHESIZE_RESPONSE

    async def router_complete(agent_name, prompt="", system="", **kwargs):
        if agent_name == "planner":
            return planner_resp
        elif agent_name == "reasoner":
            return reasoner_resp
        elif agent_name == "report":
            return report_resp
        elif agent_name == "executor":
            return synth_resp
        return '{"result": "mock"}'

    return router_complete


# ============================================================
# E2E Test Cases
# ============================================================

@pytest.mark.asyncio
async def test_e2e_ai_industry_analysis(test_orchestrator, mock_router):
    """E2E Case 1: AI行业分析 - full pipeline validation"""
    mock_router.complete = AsyncMock(
        side_effect=_make_router_side_effect(_planner_response_multi_tool())
    )

    result = await test_orchestrator.run("分析最新AI行业发展")

    # Basic result structure
    assert isinstance(result, RunResult)
    assert result.query == "分析最新AI行业发展"

    # Plan validation
    assert result.plan is not None
    assert result.subtask_count >= 2

    # DAG validation: synthesize depends on data tasks
    tool_names = [st.tool_name for st in result.plan.subtasks]
    assert "llm_synthesize" in tool_names

    # Execution validation
    assert result.exec_result is not None
    assert len(result.exec_result.task_results) > 0

    # Report validation
    assert result.report is not None
    assert result.report.title
    assert result.report.summary

    # Trace validation
    assert result.trace_id


@pytest.mark.asyncio
async def test_e2e_three_company_comparison(test_orchestrator, mock_router):
    """E2E Case 2: 三公司对比 - multi-task parallel execution"""
    mock_router.complete = AsyncMock(
        side_effect=_make_router_side_effect(_planner_response_comparison())
    )

    result = await test_orchestrator.run("比较苹果 vs 微软 vs 谷歌AI战略")

    # Must have multiple subtasks for comparison
    assert result.plan is not None
    assert result.subtask_count >= 3

    # Must have multiple tool types
    tool_types = {st.tool_name for st in result.plan.subtasks}
    assert len(tool_types) >= 2

    # All tasks should execute
    assert result.exec_result is not None
    assert len(result.exec_result.task_results) == result.subtask_count

    # Report must exist
    assert result.report is not None
    assert result.report.title


@pytest.mark.asyncio
async def test_e2e_faiss_explanation(test_orchestrator, mock_router):
    """E2E Case 3: FAISS解释 - simple Q&A pipeline"""
    mock_router.complete = AsyncMock(
        side_effect=_make_router_side_effect(_planner_response_simple())
    )

    result = await test_orchestrator.run("什么是FAISS，它在系统中如何使用")

    # Should have at least 2 tasks (RAG + synthesis)
    assert result.plan is not None
    assert result.subtask_count >= 2

    # Should produce a report
    assert result.report is not None
    assert result.report.summary

    # Should complete within reasonable time
    assert result.total_duration_ms < 5000  # 5 seconds max for mocked run


@pytest.mark.asyncio
async def test_e2e_report_has_analysis(test_orchestrator, mock_router):
    """Report must contain structured analysis fields"""
    mock_router.complete = AsyncMock(
        side_effect=_make_router_side_effect(_planner_response_multi_tool())
    )

    result = await test_orchestrator.run("AI行业分析")

    if result.report:
        analysis = result.report.analysis
        assert isinstance(analysis.key_findings, list)
        assert isinstance(analysis.risk_factors, list)
        assert isinstance(analysis.recommendations, list)


@pytest.mark.asyncio
async def test_e2e_markdown_report_generation(test_orchestrator, mock_router):
    """Report must generate valid markdown"""
    mock_router.complete = AsyncMock(
        side_effect=_make_router_side_effect(_planner_response_multi_tool())
    )

    result = await test_orchestrator.run("AI行业分析")

    if result.report:
        md = result.report.to_markdown()
        assert len(md) > 100
        assert result.report.title in md


@pytest.mark.asyncio
async def test_e2e_dag_has_dependency_edges(test_orchestrator, mock_router):
    """DAG must have proper dependency structure"""
    mock_router.complete = AsyncMock(
        side_effect=_make_router_side_effect(_planner_response_multi_tool())
    )

    result = await test_orchestrator.run("AI analysis")

    if result.plan:
        task_ids = {st.task_id for st in result.plan.subtasks}
        for st in result.plan.subtasks:
            for dep in st.depends_on:
                assert dep in task_ids, f"Dependency {dep} not in task IDs"
