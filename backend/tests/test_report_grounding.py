from app.core.executor import ExecutionResult
from app.core.planner import Plan
from app.core.report_agent import ReportAgent


def test_report_agent_removes_numbers_not_present_in_context():
    allowed = ReportAgent._extract_number_tokens(
        "AAPL price is 182.52 and the daily change is -1.26%."
    )
    report_data = {
        "summary": "AAPL trades at 182.52 with a fabricated 999.99 target.",
        "key_findings": ["Daily change was -1.260%, not 12%."],
        "risk_factors": [
            {
                "factor": "Valuation",
                "severity": "medium",
                "description": "Unsupported PE is 33.3.",
            }
        ],
    }

    cleaned = ReportAgent._remove_unsupported_numbers(report_data, allowed)

    combined = str(cleaned)
    assert "182.52" in combined
    assert "-1.260%" in combined
    assert "999.99" not in combined
    assert "12%" not in combined
    assert "33.3" not in combined
    assert "[unsupported number removed]" in combined


def test_report_agent_normalizes_equivalent_number_formats():
    allowed = ReportAgent._extract_number_tokens("Revenue was 1,230.50.")

    assert "1230.5" in allowed
    cleaned = ReportAgent._remove_unsupported_numbers(
        {"summary": "Revenue was 1230.500 and unsupported value was 1231."},
        allowed,
    )

    assert "1230.500" in cleaned["summary"]
    assert "1231" not in cleaned["summary"]


def test_report_agent_filters_prompt_placeholders():
    agent = ReportAgent(llm_client=None)
    plan = Plan(original_query="Analyze AAPL", subtasks=[])
    exec_result = ExecutionResult(
        plan=plan,
        task_results=[],
        final_answer="AAPL research completed with available tool outputs.",
    )
    report_data = {
        "title": "报告标题",
        "summary": "200字以内的简洁摘要，使用实际数据",
        "key_findings": ["来自数据的具体发现", "另一个真实发现"],
        "risk_factors": [{"factor": "名称", "severity": "high", "description": "简述"}],
        "market_trends": ["趋势1"],
        "recommendations": ["建议1"],
    }

    cleaned = agent._sanitize_report_data(
        report_data,
        query="Analyze AAPL",
        exec_result=exec_result,
        reasoning_result=None,
        language="zh",
    )
    combined = str(cleaned)

    assert "来自数据的具体发现" not in combined
    assert "另一个真实发现" not in combined
    assert "趋势1" not in combined
    assert "建议1" not in combined
    assert cleaned["summary"] == "AAPL research completed with available tool outputs."


def test_report_agent_does_not_preserve_prompt_echo_on_invalid_json():
    agent = ReportAgent(llm_client=None)
    plan = Plan(original_query="Analyze AAPL", subtasks=[])
    exec_result = ExecutionResult(
        plan=plan,
        task_results=[],
        final_answer="AAPL research completed with grounded tool output.",
    )

    parsed = agent._parse_response(
        "首先，用户指令是：我是一个报告生成器。只输出有效 JSON，结构如下："
        '{"title": string, "summary": string, "key_findings": string[]}'
    )
    cleaned = agent._sanitize_report_data(
        parsed,
        query="Analyze AAPL",
        exec_result=exec_result,
        reasoning_result=None,
        language="zh",
    )
    combined = str(cleaned)

    assert "报告生成器" not in combined
    assert "只输出有效 JSON" not in combined
    assert cleaned["summary"] == "AAPL research completed with grounded tool output."


def test_report_agent_finds_valid_json_after_schema_echo():
    agent = ReportAgent(llm_client=None)

    parsed = agent._parse_response(
        'Output ONLY valid JSON with this schema: {"title": string, "summary": string}\n'
        '{"title":"AAPL Report","summary":"AAPL price is 182.52.",'
        '"key_findings":["AAPL price is 182.52."],'
        '"risk_factors":[],"market_trends":[],"recommendations":[]}'
    )

    assert parsed["title"] == "AAPL Report"
    assert parsed["summary"] == "AAPL price is 182.52."


def test_report_agent_skips_valid_prompt_example_json():
    agent = ReportAgent(llm_client=None)

    parsed = agent._parse_response(
        '{"title":"Report Title","summary":"concise summary under 200 chars using ACTUAL data",'
        '"key_findings":["specific finding from data","another real finding"],'
        '"risk_factors":[{"factor":"Name","severity":"high","description":"brief"}],'
        '"market_trends":["trend 1"],"recommendations":["rec 1"]}\n'
        '{"title":"AAPL Report","summary":"AAPL price is 182.52.",'
        '"key_findings":["AAPL price is 182.52."],'
        '"risk_factors":[],"market_trends":[],"recommendations":[]}'
    )

    assert parsed["title"] == "AAPL Report"
    assert parsed["summary"] == "AAPL price is 182.52."
