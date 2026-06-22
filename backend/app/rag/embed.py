"""
Embedding / retrieval module - dev/prod mode switch.

Neither mode produces true neural semantic embeddings; both are lexical:
- dev:  HashEmbedder   (MD5 hashed pseudo-vectors, fast, no semantics)
- prod: BM25Embedder   (BM25 / TF-IDF over word + char n-grams, lexical only)

This is intentionally honest naming: there is no bge-m3 / sentence-transformers
model loaded. If true semantic search is required, swap BM25Embedder for a real
sentence-transformers backend and update the configured ``dim`` accordingly.
"""

import hashlib
from abc import ABC, abstractmethod

import numpy as np

from app.infrastructure.config import get_embedding_config, get_rag_config
from app.utils.logger import get_logger

logger = get_logger("embed")


class BaseEmbedder(ABC):
    """Embedding 抽象基类"""

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> np.ndarray:
        pass

    @property
    @abstractmethod
    def dim(self) -> int:
        pass

    def get_state(self) -> dict:
        """Serializable fitted state. Stateless embedders return ``{}``."""
        return {}

    def load_state(self, state: dict) -> None:
        """Restore fitted state produced by :meth:`get_state` (no-op by default)."""
        return None


class HashEmbedder(BaseEmbedder):
    """开发模式: 基于 MD5 哈希的伪向量嵌入 (无语义, 仅用于测试)"""

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    @property
    def dim(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> np.ndarray:
        vec = np.zeros(self._dim, dtype=np.float32)
        tokens = text.lower().split()
        for i, token in enumerate(tokens):
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if (h // self._dim) % 2 == 0 else -1.0
            vec[idx] += sign * (1.0 / (1 + i % 10))
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return np.array([self.embed_text(t) for t in texts], dtype=np.float32)


class BM25Embedder(BaseEmbedder):
    """BM25 / TF-IDF lexical retrieval over word + char n-grams.

    NOT a semantic embedding model: similarity is purely lexical (token overlap),
    not meaning-based. ``model_name``/``device``/``batch_size`` are accepted for
    interface compatibility but unused (no model is downloaded or run).
    """

    def __init__(self, model_name: str = "", device: str = "cpu", batch_size: int = 32):
        self._dim_value = 384
        self._vocab: dict[str, int] = {}
        self._idf: np.ndarray | None = None
        self._corpus_size = 0
        self._doc_freq: dict[str, int] = {}
        # Corpus average document length (in tokens), used by BM25 length
        # normalization. 1.0 until the vocab is fitted.
        self._avgdl = 1.0

    def _tokenize(self, text: str) -> list[str]:
        """分词 + 字符 n-gram"""
        import re

        text = text.lower()
        # 单词分词
        words = re.findall(r"\b[a-z0-9]+\b", text)
        # 过滤停用词
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "out",
            "off",
            "over",
            "under",
            "again",
            "further",
            "then",
            "once",
            "and",
            "but",
            "or",
            "nor",
            "not",
            "so",
            "yet",
            "both",
            "either",
            "neither",
            "each",
            "every",
            "all",
            "any",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "only",
            "own",
            "same",
            "than",
            "too",
            "very",
            "just",
            "because",
            "if",
            "when",
            "where",
            "how",
            "what",
            "which",
            "who",
            "whom",
            "this",
            "that",
            "these",
            "those",
            "i",
            "me",
            "my",
            "myself",
            "we",
            "our",
            "ours",
            "ourselves",
            "you",
            "your",
            "yours",
            "yourself",
            "yourselves",
            "he",
            "him",
            "his",
            "himself",
            "she",
            "her",
            "hers",
            "herself",
            "it",
            "its",
            "itself",
            "they",
            "them",
            "their",
            "theirs",
            "themselves",
        }
        words = [w for w in words if w not in stop_words and len(w) > 2]

        # 添加字符 n-gram (3-gram)
        ngrams = []
        for word in words:
            for i in range(len(word) - 2):
                ngrams.append(word[i : i + 3])

        return words + ngrams

    def _build_vocab(self, texts: list[str]):
        """从语料构建词表"""
        vocab = {}
        doc_freq = {}
        total_len = 0
        for text in texts:
            token_list = self._tokenize(text)
            total_len += len(token_list)
            for token in set(token_list):
                if token not in vocab:
                    vocab[token] = len(vocab)
                doc_freq[token] = doc_freq.get(token, 0) + 1

        self._vocab = vocab
        self._doc_freq = doc_freq
        self._corpus_size = len(texts)
        self._avgdl = (total_len / len(texts)) if texts else 1.0

        # 计算 IDF
        import math

        idf = np.zeros(len(vocab), dtype=np.float32)
        for token, idx in vocab.items():
            df = doc_freq.get(token, 0)
            idf[idx] = math.log((self._corpus_size + 1) / (df + 1)) + 1
        self._idf = idf

    def _text_to_vector(self, text: str) -> np.ndarray:
        """将文本转为 BM25 向量"""
        n_terms = len(self._vocab)
        tf = np.zeros(n_terms, dtype=np.float32)
        tokens = self._tokenize(text)
        for token in tokens:
            if token in self._vocab:
                tf[self._vocab[token]] += 1

        # BM25 TF normalization with document-length normalization:
        #   tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))
        # dl = this document's token count, avgdl = corpus average doc length.
        k1 = 1.5
        b = 0.75
        dl = len(tokens)
        avgdl = self._avgdl if self._avgdl > 0 else 1.0
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))

        return tf_norm * (self._idf if self._idf is not None else np.ones(n_terms))

    @property
    def dim(self) -> int:
        return self._dim_value

    def get_state(self) -> dict:
        """Serialize the fitted vocab/IDF so the same lexical space can be
        restored after a restart (otherwise reloaded FAISS vectors and freshly
        embedded queries would live in different, incompatible spaces)."""
        if self._idf is None:
            return {}
        return {
            "vocab": self._vocab,
            "idf": self._idf.astype(np.float32).tolist(),
            "doc_freq": self._doc_freq,
            "corpus_size": self._corpus_size,
            "avgdl": self._avgdl,
            "dim": self._dim_value,
        }

    def load_state(self, state: dict) -> None:
        if not state or "idf" not in state:
            return
        self._vocab = {str(k): int(v) for k, v in state.get("vocab", {}).items()}
        self._idf = np.asarray(state["idf"], dtype=np.float32)
        self._doc_freq = {str(k): int(v) for k, v in state.get("doc_freq", {}).items()}
        self._corpus_size = int(state.get("corpus_size", 0))
        self._avgdl = float(state.get("avgdl", 1.0)) or 1.0

    def _pad_or_truncate(self, vec: np.ndarray) -> np.ndarray:
        """将向量填充或截断到目标维度"""
        if len(vec) == self._dim_value:
            return vec
        elif len(vec) < self._dim_value:
            return np.pad(vec, (0, self._dim_value - len(vec)))
        else:
            return vec[: self._dim_value]

    def embed_text(self, text: str) -> np.ndarray:
        if self._idf is None:
            self._build_vocab([text])

        vec = self._text_to_vector(text)
        vec = self._pad_or_truncate(vec)
        # 归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(np.float32)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        if self._idf is None:
            self._build_vocab(texts)

        vecs = []
        for text in texts:
            vec = self._text_to_vector(text)
            vec = self._pad_or_truncate(vec)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vecs.append(vec)
        return np.array(vecs, dtype=np.float32)


def create_embedder() -> BaseEmbedder:
    """
    工厂函数: 根据配置创建对应的 Embedder
    - embedding.mode == "dev" -> HashEmbedder
    - embedding.mode == "prod" -> BGEEmbedder
    """
    embed_config = get_embedding_config()
    rag_config = get_rag_config()

    if embed_config.mode == "prod":
        logger.info(
            "Creating BM25Embedder (mode=prod, lexical BM25 retrieval - not semantic)"
        )
        return BM25Embedder(
            model_name=embed_config.model_name,
            device=embed_config.device,
            batch_size=embed_config.batch_size,
        )
    else:
        logger.info(f"Creating HashEmbedder (mode=dev, dim={rag_config.embedding_dim})")
        return HashEmbedder(dimension=rag_config.embedding_dim)


class Embedder(BaseEmbedder):
    """
    向后兼容的 Embedder 类
    优先使用工厂函数, 保留此类以兼容现有代码
    """

    def __init__(self, dim: int | None = None):
        config = get_embedding_config()
        rag_config = get_rag_config()

        if config.mode == "prod":
            self._inner = BM25Embedder(
                model_name=config.model_name,
                device=config.device,
                batch_size=config.batch_size,
            )
        else:
            self._inner = HashEmbedder(dimension=dim or rag_config.embedding_dim)

    @property
    def dim(self) -> int:
        return self._inner.dim

    def embed_text(self, text: str) -> np.ndarray:
        return self._inner.embed_text(text)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return self._inner.embed_batch(texts)

    def get_state(self) -> dict:
        return self._inner.get_state()

    def load_state(self, state: dict) -> None:
        self._inner.load_state(state)


# Backwards-compatible alias. Historically this class was named ``BGEEmbedder``
# and claimed to be bge-m3 semantic embeddings, which it never was.
BGEEmbedder = BM25Embedder
