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
