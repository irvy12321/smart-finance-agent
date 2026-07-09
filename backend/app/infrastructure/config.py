import os
from pathlib import Path

import yaml

# Load .env file at module level for config access
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
_backend_env = Path(__file__).parent.parent / ".env"
if _backend_env.exists():
    load_dotenv(_backend_env)


# Provider configurations
PROVIDER_CONFIGS = {
    "mimo": {
        "model": "openai/mimo-v2.5-pro",
        "api_base": "https://api.xiaomimimo.com/v1",
        "api_key_env": "MIMO_API_KEY",
    },
    "deepseek": {
        "model": "deepseek/deepseek-chat",
        "api_base": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
}


# Per-model endpoint registry: maps a bare model name to its OpenAI-compatible
# base URL and the env var holding its API key. This lets SmartRouter route
# different complexity tiers to models from different providers (cost control):
# cheap/free models for simple queries, stronger models only for complex ones.
MODEL_ENDPOINTS = {
    # Lightweight tier — Zhipu GLM (OpenAI-compatible)
    "glm-4-flash": {
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
    },
    "glm-4-air": {
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
    },
    "glm-4-plus": {
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
    },
    # Standard tier — DeepSeek (OpenAI-compatible)
    "deepseek-chat": {
        "api_base": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "deepseek-reasoner": {
        "api_base": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    # High-quality tier — Xiaomi MiMo (OpenAI-compatible)
    "mimo-v2.5-pro": {
        "api_base": "https://api.xiaomimimo.com/v1",
        "api_key_env": "MIMO_API_KEY",
    },
}


def _strip_model_prefix(model: str) -> str:
    """'openai/glm-4-flash' -> 'glm-4-flash'; bare names pass through."""
    return model.split("/", 1)[1] if "/" in model else model


def get_model_credentials(model: str) -> tuple[str | None, str | None]:
    """Resolve (api_base, api_key) for a specific model name.

    Returns (None, None) when the model is not in the registry so callers
    fall back to the active provider's default credentials. This keeps
    behaviour unchanged for the default single-model setup.
    """
    entry = MODEL_ENDPOINTS.get(_strip_model_prefix(model))
    if not entry:
        return None, None
    return entry["api_base"], os.getenv(entry["api_key_env"], "")


def get_active_provider() -> str:
    """Get active LLM provider from environment"""
    return os.getenv("LLM_PROVIDER", "mimo").lower()


def get_provider_config() -> dict:
    """Get configuration for active provider"""
    provider = get_active_provider()
    if provider not in PROVIDER_CONFIGS:
        raise ValueError(
            f"Unknown provider: {provider}. Available: {list(PROVIDER_CONFIGS.keys())}"
        )
    return PROVIDER_CONFIGS[provider]


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_")

    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 300
    max_retries: int = 3
    api_key: str = ""
    api_base: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-configure from active provider if not explicitly set
        if not self.model or not self.api_key or not self.api_base:
            provider_config = get_provider_config()
            if not self.model:
                self.model = provider_config["model"]
            if not self.api_key:
                self.api_key = os.getenv(provider_config["api_key_env"], "")
            if not self.api_base:
                self.api_base = provider_config["api_base"]


class AgentModelConfig(BaseSettings):
    """每个 Agent 的模型分配配置"""

    planner_model: str = ""
    planner_temperature: float = 0.3
    executor_model: str = ""
    executor_temperature: float = 0.3
    reasoner_model: str = ""
    reasoner_temperature: float = 0.5
    report_model: str = ""
    report_temperature: float = 0.7
    chart_model: str = ""
    chart_temperature: float = 0.3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-fill from provider config if empty
        provider_config = get_provider_config()
        default_model = provider_config["model"]
        for field in [
            "planner_model",
            "executor_model",
            "reasoner_model",
            "report_model",
            "chart_model",
        ]:
            if not getattr(self, field):
                setattr(self, field, default_model)


class EmbeddingConfig(BaseSettings):
    """Embedding 配置: dev=hash mock, prod=bge-m3"""

    mode: str = "dev"  # "dev" or "prod"
    model_name: str = "BAAI/bge-m3"
    dim: int = 1024  # bge-m3 default dimension
    batch_size: int = 32
    device: str = "cpu"  # "cpu" or "cuda"


class CrawlerConfig(BaseSettings):
    timeout: int = 15
    max_content_length: int = 8000
    user_agent: str = "SmartFinanceAgent/1.0"


class SmartRouterConfig(BaseSettings):
    """智能路由配置"""

    complexity_thresholds: dict = Field(
        default_factory=lambda: {"high": 0.7, "medium": 0.3}
    )
    lightweight_model: str = ""
    standard_model: str = ""
    high_quality_model: str = ""
    fallback_models: list[str] = Field(default_factory=list)
    tool_reliability: dict = Field(
        default_factory=lambda: {
            "news_search": 0.9,
            "rag_retrieve": 0.85,
            "crawler": 0.7,
            "llm_synthesize": 0.95,
        }
    )
    reliability_alpha: float = 0.3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        provider_config = get_provider_config()
        default_model = provider_config["model"]
        # Precedence per tier: explicit config (yaml) > env var > provider default.
        # Defaulting to the provider model keeps single-model setups working when
        # no tier models / keys are configured.
        self.lightweight_model = (
            self.lightweight_model
            or os.getenv("LLM_LIGHTWEIGHT_MODEL", "")
            or default_model
        )
        self.standard_model = (
            self.standard_model or os.getenv("LLM_STANDARD_MODEL", "") or default_model
        )
        self.high_quality_model = (
            self.high_quality_model
            or os.getenv("LLM_HIGH_QUALITY_MODEL", "")
            or default_model
        )
        if not self.fallback_models:
            self.fallback_models = [default_model]


class RAGConfig(BaseSettings):
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedding_dim: int = 384
    top_k: int = 5
    # Reranker (Cross-Encoder 精排). 默认关闭——需安装 sentence-transformers.
    reranker_enabled: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Query rewrite (LLM 多路改写 + HyDE). 默认关闭——需 LLM 可用.
    query_rewrite_enabled: bool = False
    query_rewrite_num_variants: int = 3
    hyde_enabled: bool = False


class MemoryConfig(BaseSettings):
    # 短期记忆滑动窗口 (轮数); 溢出部分折叠进滚动摘要
    short_term_max_turns: int = 10
    summary_max_chars: int = 1000
    # 长期记忆 (FAISS 向量存储, 独立于 RAG 知识库)
    long_term_enabled: bool = True
    long_term_top_k: int = 3
    # 用户画像 (SQLite user_profiles 表, 确定性规则提取)
    user_profile_enabled: bool = True


_CONFIG_DIR = Path(__file__).parent


def _load_yaml(filename: str) -> dict:
    path = _CONFIG_DIR / filename
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_llm_config() -> LLMConfig:
    overrides = _load_yaml("config_llm.yaml")
    valid_fields = set(LLMConfig.model_fields.keys())
    return LLMConfig(**{k: v for k, v in overrides.items() if k in valid_fields})


def get_agent_model_config() -> AgentModelConfig:
    overrides = _load_yaml("config_llm.yaml")
    agent_overrides = overrides.get("agent_models", {})
    valid_fields = set(AgentModelConfig.model_fields.keys())
    return AgentModelConfig(
        **{k: v for k, v in agent_overrides.items() if k in valid_fields}
    )


def get_embedding_config() -> EmbeddingConfig:
    overrides = _load_yaml("config_rag.yaml")
    embedding_overrides = overrides.get("embedding", {})
    valid_fields = set(EmbeddingConfig.model_fields.keys())
    return EmbeddingConfig(
        **{k: v for k, v in embedding_overrides.items() if k in valid_fields}
    )


def get_crawler_config() -> CrawlerConfig:
    overrides = _load_yaml("config_crawler.yaml")
    valid_fields = set(CrawlerConfig.model_fields.keys())
    return CrawlerConfig(**{k: v for k, v in overrides.items() if k in valid_fields})


def get_rag_config() -> RAGConfig:
    overrides = _load_yaml("config_rag.yaml")
    valid_fields = set(RAGConfig.model_fields.keys())
    rag_overrides = {
        k: v for k, v in overrides.items() if k != "embedding" and k in valid_fields
    }
    return RAGConfig(**rag_overrides)


def get_memory_config() -> MemoryConfig:
    overrides = _load_yaml("config_memory.yaml")
    valid_fields = set(MemoryConfig.model_fields.keys())
    return MemoryConfig(**{k: v for k, v in overrides.items() if k in valid_fields})


def get_smart_router_config() -> SmartRouterConfig:
    overrides = _load_yaml("config_llm.yaml")
    sr_overrides = overrides.get("smart_router", {})
    valid_fields = set(SmartRouterConfig.model_fields.keys())
    return SmartRouterConfig(
        **{k: v for k, v in sr_overrides.items() if k in valid_fields}
    )
