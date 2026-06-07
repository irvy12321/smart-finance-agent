"""
pytest conftest.py - Shared fixtures for offline testing
All tests run without external API calls
"""
import sys
import os
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# pytest-asyncio configuration
# ============================================================

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================
# Mock LLM Response Factories
# ============================================================

def make_mock_llm_response(content: str, model: str = "test-model", tokens: int = 100):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message = MagicMock()
    resp.choices[0].message.content = content
    resp.choices[0].message.reasoning_content = None
    resp.choices[0].finish_reason = "stop"
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = tokens // 2
    resp.usage.completion_tokens = tokens // 2
    resp.usage.total_tokens = tokens
    return resp


# ============================================================
# Mock JSON responses for each pipeline stage
# ============================================================

MOCK_PLANNER_RESPONSE = json.dumps({
    "reasoning": "Need news search, RAG retrieval, and synthesis for comprehensive analysis",
    "subtasks": [
        {
            "task_id": "task_1",
            "tool_name": "news_search",
            "params": {"query": "latest AI industry news"},
            "description": "Search for recent AI industry news",
            "depends_on": [],
            "priority": 3,
            "tool_priority_score": 0.9,
            "reasoning": "news_search best for current data",
            "confidence": 0.85,
        },
        {
            "task_id": "task_2",
            "tool_name": "rag_retrieve",
            "params": {"query": "AI industry analysis"},
            "description": "Retrieve local knowledge base documents",
            "depends_on": [],
            "priority": 3,
            "tool_priority_score": 0.7,
            "reasoning": "local docs for historical context",
            "confidence": 0.7,
        },
        {
            "task_id": "task_3",
            "tool_name": "llm_synthesize",
            "params": {"prompt": "Synthesize all findings into a comprehensive analysis"},
            "description": "Final synthesis",
            "depends_on": ["task_1", "task_2"],
            "priority": 1,
            "tool_priority_score": 0.95,
            "reasoning": "final synthesis always needed",
            "confidence": 0.9,
        },
    ],
})

MOCK_REASONER_RESPONSE = json.dumps({
    "reasoning": "Based on the data, AI industry shows strong growth with increasing adoption across sectors.",
    "key_insights": ["AI chip demand growing 40% YoY", "Enterprise AI adoption accelerating"],
    "confidence": 0.8,
    "critique": "Limited by available real-time data",
    "charts": [
        {
            "chart_type": "bar",
            "title": "AI Market Growth",
            "x_label": "Sector",
            "y_label": "Revenue ($B)",
            "data": [
                {"label": "Hardware", "value": 80},
                {"label": "Software", "value": 120},
                {"label": "Services", "value": 60},
            ],
        }
    ],
})

MOCK_REPORT_RESPONSE = json.dumps({
    "title": "AI Industry Analysis Report",
    "summary": "The AI industry continues rapid growth with expanding applications across sectors.",
    "key_findings": [
        "AI chip demand outpacing supply",
        "Enterprise adoption accelerating",
        "Regulatory frameworks emerging globally",
    ],
    "risk_factors": [
        {"factor": "Supply Chain", "severity": "high", "description": "Semiconductor shortages"},
    ],
    "market_trends": [
        "Generative AI driving new investments",
        "Edge AI gaining momentum",
    ],
    "recommendations": [
        "Increase AI infrastructure investment",
        "Monitor regulatory developments",
    ],
})

MOCK_EXECUTOR_SYNTHESIZE_RESPONSE = (
    "## AI Industry Analysis\n\n"
    "The AI industry is experiencing unprecedented growth driven by generative AI adoption. "
    "Key players are investing heavily in AI infrastructure. "
    "The market is expected to reach $500B by 2027."
)


# ============================================================
# Fixtures: mock_llm
# ============================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLMClient that never calls real APIs"""
    mock = AsyncMock()
    mock.chat = AsyncMock(return_value=MagicMock(
        content="Mock LLM response",
        model="test-model",
        usage={"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100},
        latency_ms=10.0,
        trace_id="test_trace",
    ))
    mock.complete = AsyncMock(return_value="Mock LLM complete response")
    mock.get_stats = MagicMock(return_value={
        "call_count": 0, "total_tokens": 0, "model": "test-model"
    })
    mock._call_count = 0
    mock._total_tokens = 0
    return mock


@pytest.fixture
def mock_router():
    """Mock LiteLLMRouter that returns structured JSON for each agent stage"""
    mock = AsyncMock()

    async def router_complete(agent_name, prompt="", system="", **kwargs):
        if agent_name == "planner":
            return MOCK_PLANNER_RESPONSE
        elif agent_name == "reasoner":
            return MOCK_REASONER_RESPONSE
        elif agent_name == "report":
            return MOCK_REPORT_RESPONSE
        elif agent_name == "executor":
            return MOCK_EXECUTOR_SYNTHESIZE_RESPONSE
        return '{"result": "mock"}'

    mock.complete = AsyncMock(side_effect=router_complete)
    mock.call_agent = AsyncMock(return_value=MagicMock(
        content=MOCK_PLANNER_RESPONSE,
        model="test-model",
        usage={"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100},
        latency_ms=10.0,
        trace_id="test_trace",
    ))
    mock.set_agent_model_override = MagicMock()
    mock.clear_model_overrides = MagicMock()
    mock.get_stats = MagicMock(return_value={
        "call_count": 0, "total_tokens": 0, "agent_stats": {}
    })
    mock._call_count = 0
    mock._total_tokens = 0
    mock._agent_stats = {}
    mock._model_overrides = {}

    # Token budget manager mock
    mock.token_budget = MagicMock()
    mock.token_budget.get_max_tokens = MagicMock(return_value=4096)
    mock.token_budget.record_usage = MagicMock()
    mock.token_budget.get_all_status = MagicMock(return_value={})

    return mock


# ============================================================
# Fixtures: mock_tools
# ============================================================

@pytest.fixture
def mock_news_tool():
    """Mock news_search tool"""
    from tools.base_tool import BaseTool, ToolResult

    class MockNewsTool(BaseTool):
        name = "news_search"
        description = "Mock news search tool"

        async def execute(self, **kwargs) -> ToolResult:
            query = kwargs.get("query", "")
            return ToolResult(
                success=True,
                data=[{"title": f"News about: {query}", "description": "Test news", "url": ""}],
                tool_name=self.name,
            )

    return MockNewsTool()


@pytest.fixture
def mock_rag_tool():
    """Mock rag_retrieve tool"""
    from tools.base_tool import BaseTool, ToolResult

    class MockRAGTool(BaseTool):
        name = "rag_retrieve"
        description = "Mock RAG tool"

        async def execute(self, **kwargs) -> ToolResult:
            query = kwargs.get("query", "")
            return ToolResult(
                success=True,
                data={"results": [{"text": f"Document about: {query}", "score": 0.95}]},
                tool_name=self.name,
            )

    return MockRAGTool()


@pytest.fixture
def mock_crawler_tool():
    """Mock crawler tool"""
    from tools.base_tool import BaseTool, ToolResult

    class MockCrawlerTool(BaseTool):
        name = "crawler"
        description = "Mock crawler tool"

        async def execute(self, **kwargs) -> ToolResult:
            url = kwargs.get("url", "")
            return ToolResult(
                success=True,
                data={"url": url, "content": f"Content from {url}", "length": 100},
                tool_name=self.name,
            )

    return MockCrawlerTool()


@pytest.fixture
def tool_registry_with_mocks(mock_news_tool, mock_rag_tool, mock_crawler_tool):
    """Fresh ToolRegistry with mock tools registered"""
    from tools.registry import ToolRegistry

    ToolRegistry._instance = None
    registry = ToolRegistry()
    registry.register(mock_news_tool)
    registry.register(mock_rag_tool)
    registry.register(mock_crawler_tool)

    yield registry

    ToolRegistry._instance = None


# ============================================================
# Fixtures: test_orchestrator
# ============================================================

@pytest.fixture
def test_orchestrator(mock_router, mock_llm_client, tool_registry_with_mocks):
    """Fully mocked Orchestrator for E2E testing - no external API calls"""
    from core.orchestrator import Orchestrator
    from core.agent_status import EventBus, TaskStateTracker

    # Reset singletons
    EventBus._instance = None
    TaskStateTracker._instance = None

    # Patch LLMClient.get_instance and LiteLLMRouter.get_instance
    with patch("infrastructure.llm_client.LLMClient") as MockLLM, \
         patch("infrastructure.llm_client.LiteLLMRouter") as MockRouter, \
         patch("core.orchestrator.LLMClient") as MockLLM2, \
         patch("core.orchestrator.LiteLLMRouter") as MockRouter2, \
         patch("core.planner.LLMClient") as MockLLM3, \
         patch("core.planner.LiteLLMRouter") as MockRouter3, \
         patch("core.executor.LLMClient") as MockLLM4, \
         patch("core.executor.LiteLLMRouter") as MockRouter4, \
         patch("core.reasoner.LLMClient") as MockLLM5, \
         patch("core.reasoner.LiteLLMRouter") as MockRouter5, \
         patch("core.report_agent.LLMClient") as MockLLM6, \
         patch("core.report_agent.LiteLLMRouter") as MockRouter6, \
         patch("core.orchestrator.record_task_result"):

        MockLLM.get_instance.return_value = mock_llm_client
        MockRouter.get_instance.return_value = mock_router
        MockLLM2.get_instance.return_value = mock_llm_client
        MockRouter2.get_instance.return_value = mock_router
        MockLLM3.get_instance.return_value = mock_llm_client
        MockRouter3.get_instance.return_value = mock_router
        MockLLM4.get_instance.return_value = mock_llm_client
        MockRouter4.get_instance.return_value = mock_router
        MockLLM5.get_instance.return_value = mock_llm_client
        MockRouter5.get_instance.return_value = mock_router
        MockLLM6.get_instance.return_value = mock_llm_client
        MockRouter6.get_instance.return_value = mock_router

        orch = Orchestrator(use_router=True)

        yield orch

    # Cleanup
    EventBus._instance = None
    TaskStateTracker._instance = None
