"""
Prompt 模板管理器
- 模板来源: backend/prompts/*.yaml (每个 agent 一个文件, key → prompt 文本)
- 渲染: Jinja2 (仅当传入变量时); 无变量则原样返回
- 降级: 文件缺失 / key 缺失 / 渲染失败 → 返回代码内置默认值 (调用方传入)
"""

import threading
from pathlib import Path

import yaml

from app.utils.logger import get_logger

logger = get_logger("prompt_manager")

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class PromptManager:
    """YAML prompt 模板加载器 (惰性加载 + 缓存, 线程安全)"""

    _instance: "PromptManager | None" = None
    _lock = threading.Lock()

    def __init__(self, prompts_dir: Path | None = None):
        self.prompts_dir = prompts_dir or _PROMPTS_DIR
        self._cache: dict[str, dict] = {}

    @classmethod
    def get_instance(cls) -> "PromptManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load(self, agent: str) -> dict:
        if agent in self._cache:
            return self._cache[agent]
        data: dict = {}
        path = self.prompts_dir / f"{agent}.yaml"
        try:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception as e:
            logger.warning(f"Failed to load prompt template {path}: {e}")
        self._cache[agent] = data
        return data

    def get(self, agent: str, key: str, default: str = "", **variables) -> str:
        """获取模板文本; 传入变量时用 Jinja2 渲染; 任何失败降级到 default"""
        template = self._load(agent).get(key)
        if not isinstance(template, str) or not template.strip():
            template = default
        if not variables:
            return template
        try:
            from jinja2 import Template

            return Template(template).render(**variables)
        except Exception as e:
            logger.warning(f"Prompt render failed for {agent}.{key}: {e}")
            return default

    def reload(self):
        self._cache.clear()


def get_prompt(agent: str, key: str, default: str = "", **variables) -> str:
    return PromptManager.get_instance().get(agent, key, default=default, **variables)
