import os
from pathlib import Path

import yaml

# Load .env file at module level for config access
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

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


def get_active_provider() -> str:
    """Get active LLM provider from environment"""
    return os.getenv("LLM_PROVIDER", "mimo").lower()


def get_provider_config() -> dict:
    """Get configuration for active provider"""
    provider = get_active_provider()
    if provider not in PROVIDER_CONFIGS:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(PROVIDER_CONFIGS.keys())}")
    return PROVIDER_CONFIGS[provider]


class LLMConfig(BaseSettings):
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

    class Config:
        env_prefix = "LLM_"


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
        for field in ["planner_model", "executor_model", "reasoner_model", "report_model", "chart_model"]:
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
    complexity_thresholds: dict = Field(default_factory=lambda: {"high": 0.7, "medium": 0.3})
    lightweight_model: str = ""
    standard_model: str = ""
    high_quality_model: str = ""
    fallback_models: list[str] = Field(default_factory=list)
    tool_reliability: dict = Field(default_factory=lambda: {
        "news_search": 0.9,
        "rag_retrieve": 0.85,
        "crawler": 0.7,
        "llm_synthesize": 0.95,
    })
    reliability_alpha: float = 0.3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        provider_config = get_provider_config()
        default_model = provider_config["model"]
        if not self.lightweight_model:
            self.lightweight_model = default_model
        if not self.standard_model:
            self.standard_model = default_model
        if not self.high_quality_model:
            self.high_quality_model = default_model
        if not self.fallback_models:
            self.fallback_models = [default_model]


class RAGConfig(BaseSettings):
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedding_dim: int = 384
    top_k: int = 5


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
    return AgentModelConfig(**{k: v for k, v in agent_overrides.items() if k in valid_fields})


def get_embedding_config() -> EmbeddingConfig:
    overrides = _load_yaml("config_rag.yaml")
    embedding_overrides = overrides.get("embedding", {})
    valid_fields = set(EmbeddingConfig.model_fields.keys())
    return EmbeddingConfig(**{k: v for k, v in embedding_overrides.items() if k in valid_fields})


def get_crawler_config() -> CrawlerConfig:
    overrides = _load_yaml("config_crawler.yaml")
    valid_fields = set(CrawlerConfig.model_fields.keys())
    return CrawlerConfig(**{k: v for k, v in overrides.items() if k in valid_fields})


def get_rag_config() -> RAGConfig:
    overrides = _load_yaml("config_rag.yaml")
    valid_fields = set(RAGConfig.model_fields.keys())
    rag_overrides = {k: v for k, v in overrides.items() if k != "embedding" and k in valid_fields}
    return RAGConfig(**rag_overrides)


def get_smart_router_config() -> SmartRouterConfig:
    overrides = _load_yaml("config_llm.yaml")
    sr_overrides = overrides.get("smart_router", {})
    valid_fields = set(SmartRouterConfig.model_fields.keys())
    return SmartRouterConfig(**{k: v for k, v in sr_overrides.items() if k in valid_fields})
