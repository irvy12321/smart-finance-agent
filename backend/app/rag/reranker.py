"""Reranker module — Cross-Encoder精排 + 自动降级.

设计:
* ``CrossEncoderReranker``: 加载 ``cross-encoder/ms-marco-MiniLM-L-6-v2`` 对
  (query, doc) 对做精排，输出按相关度重排序的 top_k.
* ``NoOpReranker``: 降级用，直接返回原顺序，零依赖.
* ``create_reranker()`` 工厂: 根据 RAGConfig.reranker_enabled 决定是否启用；
  模型加载失败（sentence-transformers 未装 / 模型下载失败 / 任何异常）
  自动降级到 NoOpReranker，绝不抛错.

侵入度极低: 调用方只依赖 ``reranker.rerank(query, docs, top_k)`` 这个统一接口，
两个实现满足同一接口，切换无副作用.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.infrastructure.config import get_rag_config
from app.utils.logger import get_logger

logger = get_logger("reranker")


class _RerankerLike(Protocol):
    """统一 reranker 接口. 两个实现都满足这个形状."""

    @property
    def is_available(self) -> bool: ...

    def rerank(
        self, query: str, docs: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """对 docs 按 (query, doc) 相关度重排序，返回前 top_k 条.

        输入 docs 元素形状与 Retriever.retrieve() 返回一致:
            {"text": str, "score": float, "metadata": dict, "index": int}
        输出同形状，score 字段被替换为 reranker 归一化分数 (0~1).
        """
        ...


class NoOpReranker:
    """降级 reranker: 不重排，直接截断 top_k.

    保留原 score，仅在长度上截断。用于:
    * reranker_enabled=False
    * CrossEncoder 模型加载失败
    * 任何运行时异常的兜底
    """

    @property
    def is_available(self) -> bool:
        return False

    def rerank(
        self, query: str, docs: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        return list(docs[:top_k])


class CrossEncoderReranker:
    """Cross-Encoder 精排.

    使用 sentence-transformers 的 CrossEncoder 对 (query, doc) 对打分.
    模型加载在 __init__ 完成，失败则 is_available=False 但不抛错（
    create_reranker 会捕获并降级）.
    """

    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None
        self._available = False
        try:
            from sentence_transformers import CrossEncoder  # type: ignore

            self._model = CrossEncoder(self.model_name)
            self._available = True
            logger.info(f"CrossEncoderReranker loaded: {self.model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed; reranker disabled "
                "(pip install sentence-transformers to enable)"
            )
        except Exception as e:  # 模型下载/加载失败
            logger.warning(
                f"CrossEncoder load failed ({type(e).__name__}: {e}); reranker disabled"
            )
            self._model = None

    @property
    def is_available(self) -> bool:
        return self._available and self._model is not None

    def rerank(
        self, query: str, docs: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        if not self.is_available or not docs:
            return list(docs[:top_k])

        # 构造 (query, doc_text) 对
        pairs = [(query, d.get("text", "")) for d in docs]
        try:
            raw_scores = self._model.predict(pairs)  # np.ndarray
        except Exception as e:
            logger.warning(
                f"CrossEncoder predict failed ({type(e).__name__}: {e}); "
                f"falling back to original order"
            )
            return list(docs[:top_k])

        # 归一化到 0~1（sigmoid），稳定排序
        import numpy as np

        scores = np.asarray(raw_scores, dtype=float).reshape(-1)
        probs = 1.0 / (1.0 + np.exp(-scores))  # sigmoid

        # 按分数降序排，保留原 doc 内容
        order = np.argsort(-probs)
        results: list[dict[str, Any]] = []
        for rank, idx in enumerate(order[:top_k]):
            doc = dict(docs[int(idx)])  # 浅拷贝
            doc["score"] = float(probs[int(idx)])
            doc["rerank_rank"] = rank
            results.append(doc)
        return results


def create_reranker() -> _RerankerLike:
    """工厂: 根据 RAGConfig.reranker_enabled 决定是否启用 CrossEncoder.

    任何加载失败都降级到 NoOpReranker，保证调用方零异常.
    """
    config = get_rag_config()
    enabled = getattr(config, "reranker_enabled", False)
    if not enabled:
        logger.info("Reranker disabled by config (reranker_enabled=False)")
        return NoOpReranker()

    model_name = getattr(config, "reranker_model", None) or None
    try:
        reranker = CrossEncoderReranker(model_name=model_name)
        if reranker.is_available:
            return reranker
        logger.info("CrossEncoder unavailable, degrading to NoOpReranker")
        return NoOpReranker()
    except Exception as e:
        logger.warning(
            f"create_reranker unexpected error ({type(e).__name__}: {e}); "
            f"degrading to NoOpReranker"
        )
        return NoOpReranker()
