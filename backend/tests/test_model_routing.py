"""Complexity-based model routing (SmartRouter cost optimization).

Pins the "dynamic model selection" behaviour so it stays real and defensible:
- each complexity tier can target a different model / provider,
- per-model credentials (api_base + api_key) are resolved at call time,
- the model selected for a run is applied to ALL agent stages (not just planner),
- explicit per-agent overrides (e.g. the fallback chain) still win,
- concurrent runs stay isolated via a ContextVar (no cross-run model bleed).
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.infrastructure.config import (
    SmartRouterConfig,
    get_model_credentials,
)
from app.infrastructure.llm_client import _ROUTE_MODEL, LiteLLMRouter
from app.infrastructure.smart_router import SmartRouter


def test_get_model_credentials_known_and_unknown(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "zk")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dk")

    base, key = get_model_credentials("openai/glm-4-flash")
    assert base == "https://open.bigmodel.cn/api/paas/v4"
    assert key == "zk"

    # bare model name (no provider prefix) also resolves
    base, key = get_model_credentials("deepseek-chat")
    assert base == "https://api.deepseek.com/v1"
    assert key == "dk"

    # unknown model -> fall back to active provider defaults
    assert get_model_credentials("some/unknown-model") == (None, None)


def test_smart_router_config_reads_env_tiers(monkeypatch):
    monkeypatch.setenv("LLM_LIGHTWEIGHT_MODEL", "openai/glm-4-flash")
    monkeypatch.setenv("LLM_STANDARD_MODEL", "openai/deepseek-chat")
    monkeypatch.setenv("LLM_HIGH_QUALITY_MODEL", "openai/mimo-v2.5-pro")

    c = SmartRouterConfig()
    assert c.lightweight_model == "openai/glm-4-flash"
    assert c.standard_model == "openai/deepseek-chat"
    assert c.high_quality_model == "openai/mimo-v2.5-pro"


def test_explicit_tier_config_beats_env(monkeypatch):
    monkeypatch.setenv("LLM_LIGHTWEIGHT_MODEL", "env-model")
    c = SmartRouterConfig(lightweight_model="explicit-model")
    assert c.lightweight_model == "explicit-model"


def test_select_model_by_complexity():
    c = SmartRouterConfig(
        lightweight_model="L",
        standard_model="S",
        high_quality_model="H",
        complexity_thresholds={"high": 0.7, "medium": 0.3},
    )
    r = SmartRouter(config=c)
    assert r._select_model(0.1) == "L"  # below medium -> lightweight
    assert r._select_model(0.5) == "S"  # medium tier -> standard
    assert r._select_model(0.9) == "H"  # high tier -> high quality


def test_route_model_applies_to_all_agents():
    router = LiteLLMRouter()
    token = router.set_route_model("openai/glm-4-flash")
    try:
        for agent in ["planner", "executor", "reasoner", "report", "chart"]:
            assert router._get_agent_params(agent)["model"] == "openai/glm-4-flash", (
                f"{agent} did not use the route model"
            )
    finally:
        router.reset_route_model(token)
    # after reset the run-scoped model is gone
    assert _ROUTE_MODEL.get() is None


def test_explicit_override_beats_route_model():
    router = LiteLLMRouter()
    token = router.set_route_model("openai/glm-4-flash")
    router.set_agent_model_override("planner", "openai/mimo-v2.5-pro")
    try:
        # explicit override (e.g. fallback chain) wins for that agent
        assert router._get_agent_params("planner")["model"] == "openai/mimo-v2.5-pro"
        # other agents still follow the route model
        assert router._get_agent_params("reasoner")["model"] == "openai/glm-4-flash"
    finally:
        router.clear_model_overrides()
        router.reset_route_model(token)


@pytest.mark.asyncio
async def test_route_model_isolated_across_concurrent_runs():
    """Two concurrent runs must not overwrite each other's selected model."""
    router = LiteLLMRouter()
    seen: dict[str, str] = {}

    async def run(name: str, model: str):
        token = router.set_route_model(model)
        await asyncio.sleep(0.01)  # let the other run interleave
        seen[name + "_planner"] = router._get_agent_params("planner")["model"]
        await asyncio.sleep(0.01)
        seen[name + "_reasoner"] = router._get_agent_params("reasoner")["model"]
        router.reset_route_model(token)

    await asyncio.gather(
        run("a", "openai/glm-4-flash"),
        run("b", "openai/mimo-v2.5-pro"),
    )

    assert seen["a_planner"] == "openai/glm-4-flash"
    assert seen["a_reasoner"] == "openai/glm-4-flash"
    assert seen["b_planner"] == "openai/mimo-v2.5-pro"
    assert seen["b_reasoner"] == "openai/mimo-v2.5-pro"


@pytest.mark.asyncio
async def test_call_litellm_uses_per_model_credentials(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "zk-123")
    captured: dict = {}

    async def fake_acompletion(**params):
        captured.update(params)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    monkeypatch.setattr(
        "app.infrastructure.llm_client.litellm.acompletion", fake_acompletion
    )

    router = LiteLLMRouter()
    await router._call_litellm(
        [{"role": "user", "content": "hi"}], model="openai/glm-4-flash"
    )

    assert captured["model"] == "openai/glm-4-flash"
    assert captured["api_base"] == "https://open.bigmodel.cn/api/paas/v4"
    assert captured["api_key"] == "zk-123"


@pytest.mark.asyncio
async def test_call_litellm_falls_back_to_default_creds(monkeypatch):
    """Unknown model -> use the active provider's default base/key (unchanged)."""
    captured: dict = {}

    async def fake_acompletion(**params):
        captured.update(params)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    monkeypatch.setattr(
        "app.infrastructure.llm_client.litellm.acompletion", fake_acompletion
    )

    router = LiteLLMRouter()
    await router._call_litellm(
        [{"role": "user", "content": "hi"}], model="openai/mystery-model"
    )

    assert captured["model"] == "openai/mystery-model"
    assert captured["api_key"] == router.llm_config.api_key
