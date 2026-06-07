"""
Component Tests - Planner
Verifies: subtask generation, dependency resolution, tool selection
All tests run offline with mocked LLM
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.planner import PlannerAgent, Plan, SubTask
from infrastructure.smart_router import RouteDecision


MOCK_PLAN_RESPONSE = json.dumps({
    "reasoning": "Need news search, RAG retrieval, and synthesis",
    "subtasks": [
        {
            "task_id": "task_1",
            "tool_name": "news_search",
            "params": {"query": "latest AI news"},
            "description": "Search for recent AI news",
            "depends_on": [],
            "priority": 3,
            "tool_priority_score": 0.9,
            "reasoning": "news_search best for current data",
            "confidence": 0.85,
        },
        {
            "task_id": "task_2",
            "tool_name": "rag_retrieve",
            "params": {"query": "AI analysis"},
            "description": "Retrieve local documents",
            "depends_on": [],
            "priority": 3,
            "tool_priority_score": 0.7,
            "reasoning": "local docs for context",
            "confidence": 0.7,
        },
        {
            "task_id": "task_3",
            "tool_name": "llm_synthesize",
            "params": {"prompt": "Synthesize findings"},
            "description": "Final synthesis",
            "depends_on": ["task_1", "task_2"],
            "priority": 1,
            "tool_priority_score": 0.95,
            "reasoning": "final synthesis needed",
            "confidence": 0.9,
        },
    ],
})

MOCK_SIMPLE_PLAN_RESPONSE = json.dumps({
    "reasoning": "Simple query - one data task plus synthesis",
    "subtasks": [
        {
            "task_id": "task_1",
            "tool_name": "news_search",
            "params": {"query": "Bitcoin price"},
            "description": "Search news",
            "depends_on": [],
            "priority": 3,
            "tool_priority_score": 0.8,
            "reasoning": "news for current price",
            "confidence": 0.8,
        },
        {
            "task_id": "task_2",
            "tool_name": "llm_synthesize",
            "params": {"prompt": "Summarize"},
            "description": "Synthesize",
            "depends_on": ["task_1"],
            "priority": 1,
            "tool_priority_score": 0.95,
            "reasoning": "final answer",
            "confidence": 0.9,
        },
    ],
})


def _make_planner(mock_router):
    """Helper to create PlannerAgent with mocked router"""
    with patch("core.planner.LLMClient") as MockLLM, \
         patch("core.planner.LiteLLMRouter") as MockRouter:
        MockLLM.get_instance.return_value = AsyncMock()
        MockRouter.get_instance.return_value = mock_router
        planner = PlannerAgent(llm_client=MockLLM.get_instance(), router=mock_router)
    return planner


@pytest.mark.asyncio
async def test_planner_generates_min_two_subtasks(mock_router):
    """Planner must generate >= 2 subtasks"""
    mock_router.complete = AsyncMock(return_value=MOCK_PLAN_RESPONSE)
    planner = _make_planner(mock_router)

    plan = await planner.plan("Analyze Tesla's latest financial performance")

    assert isinstance(plan, Plan)
    assert len(plan.subtasks) >= 2


@pytest.mark.asyncio
async def test_planner_subtask_structure(mock_router):
    """Each subtask must have required fields"""
    mock_router.complete = AsyncMock(return_value=MOCK_PLAN_RESPONSE)
    planner = _make_planner(mock_router)

    plan = await planner.plan("Analyze AI industry")

    for st in plan.subtasks:
        assert isinstance(st, SubTask)
        assert st.task_id, "task_id must not be empty"
        assert st.tool_name, "tool_name must not be empty"
        assert st.description, "description must not be empty"
        assert isinstance(st.params, dict)
        assert isinstance(st.depends_on, list)
        assert 1 <= st.priority <= 3


@pytest.mark.asyncio
async def test_planner_dependency_graph(mock_router):
    """Synthesize task should depend on data gathering tasks"""
    mock_router.complete = AsyncMock(return_value=MOCK_PLAN_RESPONSE)
    planner = _make_planner(mock_router)

    plan = await planner.plan("Compare AI companies")

    all_task_ids = {st.task_id for st in plan.subtasks}
    synthesize_tasks = [st for st in plan.subtasks if st.tool_name == "llm_synthesize"]

    assert len(synthesize_tasks) >= 1, "Must have at least one llm_synthesize task"
    for syn in synthesize_tasks:
        for dep in syn.depends_on:
            assert dep in all_task_ids, f"Dependency {dep} not found in task IDs"


@pytest.mark.asyncio
async def test_planner_uses_route_decision(mock_router):
    """Planner should accept and use RouteDecision"""
    mock_router.complete = AsyncMock(return_value=MOCK_SIMPLE_PLAN_RESPONSE)
    planner = _make_planner(mock_router)

    route = RouteDecision(
        complexity=0.4,
        task_type="hybrid",
        tool_scores={"news_search": 0.8, "rag_retrieve": 0.6, "crawler": 0.5, "llm_synthesize": 0.95},
        selected_model="test-model",
        plan_hint="standard",
    )

    plan = await planner.plan("Bitcoin price today", route_decision=route)

    assert isinstance(plan, Plan)
    assert plan.route_decision is route


@pytest.mark.asyncio
async def test_planner_preserves_query(mock_router):
    """Plan must store original query"""
    mock_router.complete = AsyncMock(return_value=MOCK_SIMPLE_PLAN_RESPONSE)
    planner = _make_planner(mock_router)

    query = "What is FAISS?"
    plan = await planner.plan(query)

    assert plan.original_query == query


@pytest.mark.asyncio
async def test_planner_has_reasoning(mock_router):
    """Plan must include reasoning"""
    mock_router.complete = AsyncMock(return_value=MOCK_PLAN_RESPONSE)
    planner = _make_planner(mock_router)

    plan = await planner.plan("AI industry analysis")

    assert plan.reasoning, "Plan reasoning must not be empty"
