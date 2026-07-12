from app.core.reasoner import Reasoner


def test_reasoner_invalid_json_has_low_confidence():
    reasoner = Reasoner(llm_client=object())

    result = reasoner._parse_response(
        "I cannot produce the requested JSON, but here is an explanation."
    )

    assert result.confidence == 0.0
    assert result.key_insights == []


def test_reasoner_finds_valid_json_after_schema_echo():
    reasoner = Reasoner(llm_client=object())

    result = reasoner._parse_response(
        'Output ONLY valid JSON: {"reasoning": string, "confidence": 0.8}\n'
        '{"reasoning":"AAPL data was returned by tools.",'
        '"key_insights":["AAPL data was returned by tools."],'
        '"confidence":0.72,"critique":"Limited context.","charts":[]}'
    )

    assert result.reasoning == "AAPL data was returned by tools."
    assert result.key_insights == ["AAPL data was returned by tools."]
    assert result.confidence == 0.72


def test_reasoner_skips_valid_prompt_example_json():
    reasoner = Reasoner(llm_client=object())

    result = reasoner._parse_response(
        '{"reasoning":"concise step-by-step analysis",'
        '"key_insights":["insight 1","insight 2"],'
        '"confidence":0.8,"critique":"what might be uncertain",'
        '"charts":[{"chart_type":"bar","title":"Title","x_label":"X","y_label":"Y",'
        '"data":[{"label":"A","value":100},{"label":"B","value":200}]}]}\n'
        '{"reasoning":"AAPL data was returned by tools.",'
        '"key_insights":["AAPL data was returned by tools."],'
        '"confidence":0.72,"critique":"Limited context.","charts":[]}'
    )

    assert result.reasoning == "AAPL data was returned by tools."
    assert result.key_insights == ["AAPL data was returned by tools."]
    assert result.confidence == 0.72
    assert result.chart_specs == []
