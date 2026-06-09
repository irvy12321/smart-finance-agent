import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_llm():
    with patch("app.core.orchestrator.LLMClient") as mock:
        instance = MagicMock()
        instance.chat = AsyncMock(return_value=MagicMock(content="Test response"))
        mock.get_instance.return_value = instance
        yield instance


@pytest.fixture
def mock_tools():
    with patch("app.core.orchestrator.ToolRegistry") as mock:
        registry = MagicMock()
        registry.get_tool.return_value = MagicMock()
        mock.return_value = registry
        yield registry


@pytest.fixture
def mock_planner():
    with patch("app.core.orchestrator.PlannerAgent") as mock:
        planner = MagicMock()
        plan = MagicMock()
        plan.subtasks = [
            MagicMock(id="t1", tool="stock_price", description="Get stock price", priority=1, depends_on=[]),
            MagicMock(id="t2", tool="news", description="Get news", priority=2, depends_on=["t1"]),
        ]
        plan.reasoning = "Test plan reasoning"
        planner.create_plan = AsyncMock(return_value=plan)
        mock.return_value = planner
        yield planner


@pytest.fixture
def mock_executor():
    with patch("app.core.orchestrator.ExecutorAgent") as mock:
        executor = MagicMock()
        result = MagicMock()
        result.task_results = [
            MagicMock(task_id="t1", tool_name="stock_price", success=True, duration_ms=100, result={"price": 150}),
            MagicMock(task_id="t2", tool_name="news", success=True, duration_ms=200, result={"articles": []}),
        ]
        result.total_duration_ms = 300
        result.success_count = 2
        result.failure_count = 0
        executor.execute_plan = AsyncMock(return_value=result)
        mock.return_value = executor
        yield executor


@pytest.fixture
def mock_reasoner():
    with patch("app.core.orchestrator.Reasoner") as mock:
        reasoner = MagicMock()
        result = MagicMock()
        result.confidence = 0.85
        result.insights = ["insight1", "insight2"]
        result.summary = "Test reasoning summary"
        reasoner.analyze = AsyncMock(return_value=result)
        mock.return_value = reasoner
        yield reasoner


@pytest.fixture
def mock_report_agent():
    with patch("app.core.orchestrator.ReportAgent") as mock:
        agent = MagicMock()
        report = MagicMock()
        report.summary = "Test report summary"
        report.markdown = "# Test Report\n## 摘要\nThis is a test report"
        report.title = "Test Report"
        report.key_findings = ["finding1", "finding2"]
        report.risk_factors = [{"factor": "risk1", "severity": "medium"}]
        report.market_trends = ["trend1"]
        report.recommendations = ["recommendation1"]
        agent.generate_report = AsyncMock(return_value=report)
        mock.return_value = agent
        yield agent


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    with patch("app.core.orchestrator.LLMClient") as mock_llm, \
         patch("app.core.orchestrator.ToolRegistry") as mock_registry, \
         patch("app.core.orchestrator.PlannerAgent") as mock_planner, \
         patch("app.core.orchestrator.ExecutorAgent") as mock_executor, \
         patch("app.core.orchestrator.Reasoner") as mock_reasoner, \
         patch("app.core.orchestrator.ReportAgent") as mock_report, \
         patch("app.core.orchestrator.ChartRenderer") as mock_chart, \
         patch("app.core.orchestrator.FallbackManager") as mock_fallback, \
         patch("app.core.orchestrator.ConversationMemory") as mock_memory, \
         patch("app.core.orchestrator.EventBus") as mock_event_bus, \
         patch("app.core.orchestrator.TaskStateTracker") as mock_tracker, \
         patch("app.core.orchestrator.LiteLLMRouter") as mock_router, \
         patch("app.core.orchestrator.SmartRouter") as mock_smart_router:

        mock_llm.get_instance.return_value = MagicMock()
        mock_router.get_instance.return_value = MagicMock()
        mock_event_bus.get_instance.return_value = MagicMock()
        mock_tracker.get_instance.return_value = MagicMock()

        from app.core.orchestrator import Orchestrator
        orch = Orchestrator(use_router=True)

        assert orch is not None
        assert orch.planner is not None
        assert orch.executor is not None
        assert orch.reasoner is not None
        assert orch.report_agent is not None


@pytest.mark.asyncio
async def test_orchestrator_run_pipeline(
    mock_llm, mock_tools, mock_planner, mock_executor, mock_reasoner, mock_report_agent
):
    with patch("app.core.orchestrator.LLMClient.get_instance", return_value=mock_llm), \
         patch("app.core.orchestrator.ToolRegistry", return_value=mock_tools), \
         patch("app.core.orchestrator.PlannerAgent", return_value=mock_planner), \
         patch("app.core.orchestrator.ExecutorAgent", return_value=mock_executor), \
         patch("app.core.orchestrator.Reasoner", return_value=mock_reasoner), \
         patch("app.core.orchestrator.ReportAgent", return_value=mock_report_agent), \
         patch("app.core.orchestrator.ChartRenderer", return_value=MagicMock()), \
         patch("app.core.orchestrator.FallbackManager", return_value=MagicMock()), \
         patch("app.core.orchestrator.ConversationMemory", return_value=MagicMock()), \
         patch("app.core.orchestrator.EventBus.get_instance", return_value=MagicMock()), \
         patch("app.core.orchestrator.TaskStateTracker.get_instance", return_value=MagicMock()), \
         patch("app.core.orchestrator.LiteLLMRouter.get_instance", return_value=MagicMock()), \
         patch("app.core.orchestrator.SmartRouter", return_value=MagicMock()):

        from app.core.orchestrator import Orchestrator
        orch = Orchestrator(use_router=False)

        result = await orch.run("Analyze AAPL stock price")

        assert result is not None
        assert result.query == "Analyze AAPL stock price"
        assert result.answer is not None
        assert result.plan is not None
        assert result.exec_result is not None
        assert result.reasoning_result is not None
        assert result.report is not None


@pytest.mark.asyncio
async def test_planner_agent():
    with patch("app.core.planner.LLMClient") as mock_llm_class:
        mock_llm = MagicMock()
        mock_llm.chat = AsyncMock(return_value=MagicMock(content='{"subtasks": [{"id": "t1", "tool": "stock_price", "description": "Get price", "priority": 1}]}'))
        mock_llm_class.get_instance.return_value = mock_llm

        from app.core.planner import PlannerAgent
        planner = PlannerAgent(mock_llm, None)

        plan = await planner.create_plan("What is AAPL stock price?")

        assert plan is not None
        assert len(plan.subtasks) > 0


@pytest.mark.asyncio
async def test_executor_agent():
    with patch("app.core.executor.ToolRegistry") as mock_registry:
        mock_tool = MagicMock()
        mock_tool.execute = AsyncMock(return_value={"result": "success"})
        mock_registry.return_value.get_tool.return_value = mock_tool

        from app.core.executor import ExecutorAgent, SubTask
        mock_llm = MagicMock()
        executor = ExecutorAgent(mock_registry(), mock_llm, None)

        subtask = SubTask(id="t1", tool="stock_price", description="Get price", priority=1, depends_on=[])
        plan = MagicMock()
        plan.subtasks = [subtask]

        result = await executor.execute_plan(plan)

        assert result is not None
        assert len(result.task_results) > 0


def test_tool_registry():
    with patch("app.tools.registry.CrawlerTool") as mock_crawler, \
         patch("app.tools.registry.NewsTool") as mock_news, \
         patch("app.tools.registry.RAGTool") as mock_rag, \
         patch("app.tools.registry.StockPriceTool") as mock_stock, \
         patch("app.tools.registry.StockHistoryTool") as mock_history, \
         patch("app.tools.registry.FinancialReportTool") as mock_report, \
         patch("app.tools.registry.FinancialAnalysisTool") as mock_analysis, \
         patch("app.tools.registry.NewsSummaryTool") as mock_summary, \
         patch("app.tools.registry.NewsAnalysisTool") as mock_news_analysis:

        from app.tools.registry import ToolRegistry
        registry = ToolRegistry()

        assert registry is not None


def test_fallback_manager():
    with patch("app.core.fallback_manager.ToolRegistry") as mock_registry, \
         patch("app.core.fallback_manager.LLMClient") as mock_llm:

        from app.core.fallback_manager import FallbackManager
        manager = FallbackManager(mock_registry(), mock_llm(), None)

        assert manager is not None