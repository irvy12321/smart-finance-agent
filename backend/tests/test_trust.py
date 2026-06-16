from app.core.trust import (
    MOCK_WARNING,
    DataEnvelope,
    aggregate_confidence,
)


def test_envelope_real_has_no_warning():
    env = DataEnvelope(value=182.5, source="alpha_vantage")
    assert env.is_mock is False
    assert env.warning == ""
    d = env.to_dict()
    assert d["source"] == "alpha_vantage"
    assert d["warning"] == ""
    assert "fetched_at" in d


def test_envelope_mock_carries_warning():
    env = DataEnvelope(value=1.0, source="mock", is_mock=True)
    assert env.warning == MOCK_WARNING
    assert env.to_dict()["is_mock"] is True


def test_aggregate_all_real_is_high_confidence():
    envs = [
        DataEnvelope(1, "alpha_vantage"),
        DataEnvelope(2, "fmp"),
        DataEnvelope(3, "newsapi"),
    ]
    agg = aggregate_confidence(envs)
    assert agg["data_confidence"] == 1.0
    assert agg["mock_ratio"] == 0.0
    assert agg["source_reliability"] == "high"
    assert agg["sources"] == ["alpha_vantage", "fmp", "newsapi"]


def test_aggregate_mixed_is_medium():
    envs = [
        DataEnvelope(1, "alpha_vantage"),
        DataEnvelope(2, "mock", is_mock=True),
    ]
    agg = aggregate_confidence(envs)
    assert agg["data_confidence"] == 0.5
    assert agg["mock_ratio"] == 0.5
    assert agg["source_reliability"] == "medium"


def test_aggregate_all_mock_is_low():
    envs = [DataEnvelope(1, "mock", is_mock=True)]
    agg = aggregate_confidence(envs)
    assert agg["data_confidence"] == 0.0
    assert agg["source_reliability"] == "low"


def test_aggregate_empty():
    agg = aggregate_confidence([])
    assert agg["data_confidence"] == 0.0
    assert agg["mock_ratio"] == 1.0
    assert agg["source_reliability"] == "low"
