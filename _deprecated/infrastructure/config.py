import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import yaml


class LLMConfig(BaseSettings):
    model: str = "openai/mimo-v2.5-pro"
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 3
    api_key: str = Field(default_factory=lambda: os.getenv("MIMO_API_KEY", ""))
    api_base: str = "https://api.xiaomimimo.com/v1"

    class Config:
        env_prefix = "LLM_"


class AgentModelConfig(BaseSettings):
    """每个 Agent 的模型分配配置"""
    planner_model: str = "openai/mimo-v2.5-pro"
    planner_temperature: float = 0.3
    executor_model: str = "openai/mimo-v2.5-pro"
    executor_temperature: float = 0.3
    reasoner_model: str = "openai/mimo-v2.5-pro"
    reasoner_temperature: float = 0.5
    report_model: str = "openai/mimo-v2.5-pro"
    report_temperature: float = 0.7
    chart_model: str = "openai/mimo-v2.5-pro"
    chart_temperature: float = 0.3


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
    lightweight_model: str = "openai/mimo-v2.5-pro"
    standard_model: str = "openai/mimo-v2.5-pro"
    high_quality_model: str = "openai/mimo-v2.5-pro"
    fallback_models: list[str] = Field(default_factory=lambda: ["openai/mimo-v2.5-pro"])
    tool_reliability: dict = Field(default_factory=lambda: {
        "news_search": 0.9,
        "rag_retrieve": 0.85,
        "crawler": 0.7,
        "llm_synthesize": 0.95,
    })
    reliability_alpha: float = 0.3


class RAGConfig(BaseSettings):
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedding_dim: int = 384
    top_k: int = 5


_CONFIG_DIR = Path(__file__).parent


def _load_yaml(filename: str) -> dict:
    path = _CONFIG_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
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
