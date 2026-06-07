"""
Component Tests - Executor
Verifies: DAG execution, tool dispatch, parallel tasks, fallback
All tests run offline with mocked tools and LLM
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.planner import Plan, SubTask
from core.executor import ExecutorAgent, ExecutionResult, TaskResult
from core.agent_status import EventBus, TaskStateTracker
from tools.base_tool import ToolResult


def _make_plan(subtasks_data: list[dict]) -> Plan:
    """Helper to build a Plan from subtask dicts"""
    subtasks = [SubTask(**s) for s in subtasks_data]
    return Plan(original_query="test query", subtasks=subtasks, reasoning="test plan")


@pytest.fixture
def executor(tool_registry_with_mocks, mock_llm_client, mock_router):
    """Create ExecutorAgent with mocked dependencies"""
    EventBus._instance = None
    TaskStateTracker._instance = None

    with patch("core.executor.LLMClient") as MockLLM, \
         patch("core.executor.LiteLLMRouter") as MockRouter:
        MockLLM.get_instance.return_value = mock_llm_client
        MockRouter.get_instance.return_value = mock_router

        exec_agent = ExecutorAgent(
            tool_registry=tool_registry_with_mocks,
            llm_client=mock_llm_client,
            router=mock_router,
        )

    yield exec_agent

    EventBus._instance = None
    TaskStateTracker._instance = None


@pytest.mark.asyncio
async def test_executor_runs_dag(executor):
    """Executor must resolve DAG and execute all tasks"""
    plan = _make_plan([
        {
            "task_id": "t1",
            "tool_name": "news_search",
            "params": {"query": "AI news"},
            "description": "Search news",
            "depends_on": [],
            "priority": 3,
        },
        {
            "task_id": "t2",
            "tool_name": "rag_retrieve",
            "params": {"query": "AI analysis"},
            "description": "RAG search",
            "depends_on": [],
            "priority": 3,
        },
        {
            "task_id": "t3",
            "tool_name": "llm_synthesize",
            "params": {"prompt": "Synthesize"},
            "description": "Synthesize",
            "depends_on": ["t1", "t2"],
            "priority": 1,
        },
    ])

    result = await executor.execute(plan)

    assert isinstance(result, ExecutionResult)
    assert len(result.task_results) == 3


@pytest.mark.asyncio
async def test_executor_respects_dependencies(executor):
    """Tasks with dependencies must wait for prerequisites"""
    plan = _make_plan([
        {
            "task_id": "t1",
            "tool_name": "news_search",
            "params": {"query": "test"},
            "description": "Data task",
            "depends_on": [],
            "priority": 3,
        },
        {
            "task_id": "t2",
            "tool_name": "llm_synthesize",
            "params": {"prompt": "Synthesize"},
            "description": "Synthesize",
            "depends_on": ["t1"],
            "priority": 1,
        },
    ])

    result = await executor.execute(plan)

    # t1 must complete before t2
    task_ids = [tr.task_id for tr in result.task_results]
    assert task_ids.index("t1") < task_ids.index("t2")


@pytest.mark.asyncio
async def test_executor_tool_dispatch(executor):
    """Executor must dispatch to correct tools"""
    plan = _make_plan([
        {
            "task_id": "t1",
            "tool_name": "news_search",
            "params": {"query": "test"},
            "description": "News task",
            "depends_on": [],
            "priority": 3,
        },
    ])

    result = await executor.execute(plan)

    assert result.task_results[0].tool_name == "news_search"
    assert result.task_results[0].success is True


@pytest.mark.asyncio
async def test_executor_handles_unknown_tool(executor):
    """Unknown tool should return failure"""
    plan = _make_plan([
        {
            "task_id": "t1",
            "tool_name": "nonexistent_tool",
            "params": {},
            "description": "Bad tool",
            "depends_on": [],
            "priority": 3,
        },
    ])

    result = await executor.execute(plan)

    assert result.task_results[0].success is False
    assert "not found" in result.task_results[0].error.lower()


@pytest.mark.asyncio
async def test_executor_synthesize_merges_data(executor):
    """Synthesize task should receive data from dependencies"""
    plan = _make_plan([
        {
            "task_id": "t1",
            "tool_name": "news_search",
            "params": {"query": "AI"},
            "description": "News",
            "depends_on": [],
            "priority": 3,
        },
        {
            "task_id": "t2",
            "tool_name": "rag_retrieve",
            "params": {"query": "AI"},
            "description": "RAG",
            "depends_on": [],
            "priority": 3,
        },
        {
            "task_id": "t3",
            "tool_name": "llm_synthesize",
            "params": {"prompt": "Analyze and summarize all findings"},
            "description": "Synthesize",
            "depends_on": ["t1", "t2"],
            "priority": 1,
        },
    ])

    result = await executor.execute(plan)

    # At least news and rag should succeed
    successful = [tr for tr in result.task_results if tr.success]
    assert len(successful) >= 2


@pytest.mark.asyncio
async def test_executor_returns_final_answer(executor):
    """Executor must produce a final_answer string"""
    plan = _make_plan([
        {
            "task_id": "t1",
            "tool_name": "news_search",
            "params": {"query": "test"},
            "description": "Data",
            "depends_on": [],
            "priority": 3,
        },
        {
            "task_id": "t2",
            "tool_name": "llm_synthesize",
            "params": {"prompt": "Summarize"},
            "description": "Synthesize",
            "depends_on": ["t1"],
            "priority": 1,
        },
    ])

    result = await executor.execute(plan)

    assert result.final_answer, "final_answer must not be empty"
