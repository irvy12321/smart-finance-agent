import contextlib
import contextvars
import time
import uuid
from dataclasses import dataclass, field

import litellm

from app.infrastructure.config import (
    AgentModelConfig,
    LLMConfig,
    get_active_provider,
    get_agent_model_config,
    get_llm_config,
    get_model_credentials,
)
from app.monitoring.prometheus import (
    llm_errors_total,
    llm_in_progress,
    llm_request_duration_seconds,
    llm_requests_total,
    llm_tokens_total,
)
from app.utils.exceptions import LLMClientError
from app.utils.logger import get_logger
from app.utils.retry import async_retry

logger = get_logger("llm_client")

litellm.suppress_debug_info = True

# Log active provider on module load
_active_provider = get_active_provider()
logger.info(f"LLM Provider: {_active_provider}")

# Per-run model selected by SmartRouter (complexity-based tier). Stored in a
# ContextVar so concurrent runs (each its own asyncio task) stay isolated and
# never overwrite each other's model choice. None => use per-agent defaults.
_ROUTE_MODEL: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "route_model", default=None
)


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    trace_id: str = ""


class LLMClient:
    """基础 LLM 客户端 (向后兼容)"""

    _instance: "LLMClient | None" = None

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or get_llm_config()
        self._call_count = 0
        self._total_tokens = 0
        logger.info(f"LLMClient initialized with model={self.config.model}")

    @classmethod
    def get_instance(cls, config: LLMConfig | None = None) -> "LLMClient":
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    @async_retry(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(Exception,),
        # Do not waste retries on errors that will never succeed on retry.
        exclude=(
            litellm.AuthenticationError,
            litellm.BadRequestError,
            litellm.NotFoundError,
        ),
    )
    async def _call_litellm(self, messages: list[dict], **kwargs) -> dict:
        call_params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "timeout": kwargs.get("timeout", self.config.timeout),
            "api_key": self.config.api_key,
        }
        if self.config.api_base:
            call_params["api_base"] = self.config.api_base

        response = await litellm.acompletion(**call_params)
        return response

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        trace_id: str | None = None,
    ) -> LLMResponse:
        trace_id = trace_id or uuid.uuid4().hex[:12]
        start = time.perf_counter()

        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        logger.info(
            f"[trace:{trace_id}] LLM call model={self.config.model} "
            f"messages={len(messages)}"
        )

        try:
            response = await self._call_litellm(messages, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000

            content = response.choices[0].message.content or ""
            # MiMo 推理模型: content 为空时检查 reasoning_content
            if not content:
                msg = response.choices[0].message
                if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                    logger.info(
                        f"[trace:{trace_id}] content empty, falling back to reasoning_content"
                    )
                    content = msg.reasoning_content
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

            self._call_count += 1
            self._total_tokens += usage["total_tokens"]

            logger.info(
                f"[trace:{trace_id}] LLM done in {latency_ms:.0f}ms "
                f"tokens={usage['total_tokens']}"
            )

            return LLMResponse(
                content=content,
                model=self.config.model,
                usage=usage,
                latency_ms=latency_ms,
                trace_id=trace_id,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            error_msg = str(e)

            # Provide user-friendly error messages
            if (
                "401" in error_msg
                or "Unauthorized" in error_msg
                or "invalid api key" in error_msg.lower()
            ):
                user_msg = "LLM authentication failed. Please check MIMO_API_KEY in backend/.env"
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                user_msg = "LLM rate limit exceeded. Please wait and try again"
            elif "timeout" in error_msg.lower():
                user_msg = "LLM request timed out. Please try again"
            else:
                user_msg = f"LLM call failed: {error_msg}"

            logger.error(
                f"[trace:{trace_id}] LLM failed after {latency_ms:.0f}ms: {error_msg}"
            )
            raise LLMClientError(user_msg) from e

    async def complete(self, prompt: str, system: str = "", **kwargs) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = await self.chat(messages, **kwargs)
        return resp.content

    def get_stats(self) -> dict:
        return {
            "call_count": self._call_count,
            "total_tokens": self._total_tokens,
            "model": self.config.model,
        }


class LiteLLMRouter:
    """
    多模型路由器 - 根据 Agent 名称路由到不同的模型/参数配置
    支持: planner, executor, reasoner, report 四个 Agent 的独立模型配置
    """

    _instance: "LiteLLMRouter | None" = None

    def __init__(
        self,
        llm_config: LLMConfig | None = None,
        agent_config: AgentModelConfig | None = None,
    ):
        self.llm_config = llm_config or get_llm_config()
        self.agent_config = agent_config or get_agent_model_config()
        self._call_count = 0
        self._total_tokens = 0
        self._agent_stats: dict[str, dict] = {}
        self._model_overrides: dict[str, str] = {}
        # Token 预算管理
        from app.core.token_budget import TokenBudgetManager

        self.token_budget = TokenBudgetManager()
        logger.info(
            "LiteLLMRouter initialized with multi-agent model routing + token budget"
        )

    @classmethod
    def get_instance(cls) -> "LiteLLMRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_agent_params(self, agent_name: str) -> dict:
        """获取指定 Agent 的模型参数 (支持 override)"""
        model_map = {
            "planner": (
                self.agent_config.planner_model,
                self.agent_config.planner_temperature,
            ),
            "executor": (
                self.agent_config.executor_model,
                self.agent_config.executor_temperature,
            ),
            "reasoner": (
                self.agent_config.reasoner_model,
                self.agent_config.reasoner_temperature,
            ),
            "report": (
                self.agent_config.report_model,
                self.agent_config.report_temperature,
            ),
            "chart": (
                self.agent_config.chart_model,
                self.agent_config.chart_temperature,
            ),
        }
        model, temp = model_map.get(
            agent_name, (self.llm_config.model, self.llm_config.temperature)
        )
        # SmartRouter 复杂度路由: 本次运行选中的模型作用于所有 Agent 阶段
        route_model = _ROUTE_MODEL.get()
        if route_model:
            model = route_model
        # 显式 override (如 fallback 链) 优先级最高
        if agent_name in self._model_overrides:
            model = self._model_overrides[agent_name]
        return {"model": model, "temperature": temp}

    def set_route_model(self, model: str) -> contextvars.Token:
        """绑定本次运行 (当前 asyncio task) 由复杂度选中的模型。

        返回的 token 用于 reset_route_model 还原, 避免跨运行串台。
        """
        logger.info(f"Route model bound for this run: {model}")
        return _ROUTE_MODEL.set(model or None)

    def reset_route_model(self, token: contextvars.Token | None) -> None:
        """还原 set_route_model 设置的运行级模型。"""
        if token is None:
            return
        with contextlib.suppress(ValueError, LookupError):
            _ROUTE_MODEL.reset(token)

    def set_agent_model_override(self, agent_name: str, model: str):
        """临时覆盖某个 Agent 的模型 (用于 SmartRouter 决策)"""
        self._model_overrides[agent_name] = model
        logger.info(f"Model override: {agent_name} -> {model}")

    def clear_model_overrides(self):
        """清除所有模型 override"""
        self._model_overrides.clear()

    @async_retry(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(Exception,),
        # Do not waste retries on errors that will never succeed on retry.
        exclude=(
            litellm.AuthenticationError,
            litellm.BadRequestError,
            litellm.NotFoundError,
        ),
    )
    async def _call_litellm(self, messages: list[dict], **kwargs) -> dict:
        model = kwargs["model"]
        # Resolve per-model credentials so different complexity tiers can target
        # different providers. Falls back to the active provider defaults when
        # the model is not in the endpoint registry (single-model setups).
        model_api_base, model_api_key = get_model_credentials(model)
        call_params = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.llm_config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.llm_config.max_tokens),
            "timeout": kwargs.get("timeout", self.llm_config.timeout),
            "api_key": model_api_key or self.llm_config.api_key,
        }
        api_base = model_api_base or self.llm_config.api_base
        if api_base:
            call_params["api_base"] = api_base

        response = await litellm.acompletion(**call_params)
        return response

    async def call_agent(
        self,
        agent_name: str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        trace_id: str | None = None,
    ) -> LLMResponse:
        """
        调用指定 Agent 的模型，自动应用 token 预算限制
        agent_name: "planner" | "executor" | "reasoner" | "report" | "chart"
        """
        trace_id = trace_id or uuid.uuid4().hex[:12]
        start = time.perf_counter()

        agent_params = self._get_agent_params(agent_name)
        kwargs = {
            "model": agent_params["model"],
            "temperature": agent_params["temperature"],
        }

        # Token 预算控制: 取 min(用户指定, 预算剩余)
        budget_limit = self.token_budget.get_max_tokens(agent_name)
        if budget_limit <= 0:
            budget_limit = self.llm_config.max_tokens
        if max_tokens is not None:
            kwargs["max_tokens"] = min(max_tokens, budget_limit)
        else:
            kwargs["max_tokens"] = budget_limit

        logger.info(
            f"[trace:{trace_id}] Agent '{agent_name}' call model={kwargs['model']} "
            f"temp={kwargs['temperature']} max_tokens={kwargs['max_tokens']} messages={len(messages)}"
        )

        # Track LLM request metrics
        model = kwargs["model"]
        llm_requests_total.labels(model=model).inc()
        llm_in_progress.labels(model=model).inc()

        try:
            response = await self._call_litellm(messages, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000

            # Record LLM duration
            llm_request_duration_seconds.labels(model=model).observe(latency_ms / 1000)

            msg = response.choices[0].message
            content = msg.content or ""
            # MiMo 推理模型: content 为空时检查 reasoning_content
            if (
                not content
                and hasattr(msg, "reasoning_content")
                and msg.reasoning_content
            ):
                logger.info(
                    f"[trace:{trace_id}] content empty, falling back to reasoning_content"
                )
                content = msg.reasoning_content

            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

            if not content and usage["completion_tokens"] > 0:
                logger.warning(
                    f"[trace:{trace_id}] Empty content with {usage['completion_tokens']} tokens. "
                    f"finish_reason={response.choices[0].finish_reason} "
                    f"message_keys={list(msg.__dict__.keys())}"
                )

            self._call_count += 1
            self._total_tokens += usage["total_tokens"]

            # per-agent 统计
            if agent_name not in self._agent_stats:
                self._agent_stats[agent_name] = {
                    "calls": 0,
                    "tokens": 0,
                    "latency_total_ms": 0,
                }
            self._agent_stats[agent_name]["calls"] += 1
            self._agent_stats[agent_name]["tokens"] += usage["total_tokens"]
            self._agent_stats[agent_name]["latency_total_ms"] += latency_ms

            # 记录 token 预算消耗
            self.token_budget.record_usage(agent_name, usage["total_tokens"])

            # Record Prometheus token metrics
            llm_tokens_total.labels(model=model, type="prompt").inc(
                usage["prompt_tokens"]
            )
            llm_tokens_total.labels(model=model, type="completion").inc(
                usage["completion_tokens"]
            )
            llm_tokens_total.labels(model=model, type="total").inc(
                usage["total_tokens"]
            )
            llm_in_progress.labels(model=model).dec()

            # 记录 metrics
            from app.core.observability.metrics import record_agent_call

            record_agent_call(
                agent_name=agent_name,
                tokens=usage["total_tokens"],
                latency_ms=latency_ms,
                trace_id=trace_id,
            )

            logger.info(
                f"[trace:{trace_id}] Agent '{agent_name}' done in {latency_ms:.0f}ms "
                f"tokens={usage['total_tokens']}"
            )

            return LLMResponse(
                content=content,
                model=kwargs["model"],
                usage=usage,
                latency_ms=latency_ms,
                trace_id=trace_id,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            error_msg = str(e)

            # Record LLM error metrics
            llm_in_progress.labels(model=model).dec()
            error_type = type(e).__name__
            llm_errors_total.labels(model=model, error_type=error_type).inc()

            # Provide user-friendly error messages
            if (
                "401" in error_msg
                or "Unauthorized" in error_msg
                or "invalid api key" in error_msg.lower()
            ):
                user_msg = f"Agent '{agent_name}' authentication failed. Please check MIMO_API_KEY in backend/.env"
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                user_msg = f"Agent '{agent_name}' rate limit exceeded. Please wait and try again"
            elif "timeout" in error_msg.lower():
                user_msg = f"Agent '{agent_name}' request timed out. Please try again"
            else:
                user_msg = f"Agent '{agent_name}' LLM call failed: {error_msg}"

            # 记录错误 metrics
            from app.core.observability.metrics import record_agent_error

            record_agent_error(agent_name, error_msg, trace_id=trace_id)

            logger.error(
                f"[trace:{trace_id}] Agent '{agent_name}' failed after {latency_ms:.0f}ms: {error_msg}"
            )
            raise LLMClientError(user_msg) from e

    async def complete(
        self,
        agent_name: str,
        prompt: str,
        system: str = "",
        **kwargs,
    ) -> str:
        """便捷方法: 构建 messages 并调用指定 Agent"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = await self.call_agent(agent_name, messages, **kwargs)
        return resp.content

    async def call_agent_with_fallback(
        self,
        agent_name: str,
        messages: list[dict[str, str]],
        fallback_models: list[str],
        max_tokens: int | None = None,
        trace_id: str | None = None,
    ) -> LLMResponse:
        """带 fallback 模型链的 Agent 调用"""
        agent_params = self._get_agent_params(agent_name)
        primary_model = agent_params["model"]
        all_models = [primary_model] + [
            m for m in fallback_models if m != primary_model
        ]

        last_error = None
        for model in all_models:
            try:
                # 临时设置模型
                old_override = self._model_overrides.get(agent_name)
                self._model_overrides[agent_name] = model

                result = await self.call_agent(
                    agent_name, messages, max_tokens=max_tokens, trace_id=trace_id
                )

                # 恢复原 override
                if old_override is not None:
                    self._model_overrides[agent_name] = old_override
                elif agent_name in self._model_overrides:
                    del self._model_overrides[agent_name]

                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Fallback: model {model} failed for {agent_name}: {e}")
                # 恢复原 override
                if old_override is not None:
                    self._model_overrides[agent_name] = old_override
                elif agent_name in self._model_overrides:
                    del self._model_overrides[agent_name]

        raise last_error

    def get_stats(self) -> dict:
        return {
            "call_count": self._call_count,
            "total_tokens": self._total_tokens,
            "agent_stats": dict(self._agent_stats),
            "token_budget": self.token_budget.get_all_status(),
        }
