"""
Embedding 模块 - 支持 dev/prod 模式切换
- dev: HashEmbedder (MD5哈希伪向量, 快速, 无语义)
- prod: BGEEmbedder (BAAI/bge-m3, 真实语义)
"""
import hashlib
from abc import ABC, abstractmethod
import numpy as np
from infrastructure.config import get_embedding_config, get_rag_config
from utils.logger import get_logger

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


class BGEEmbedder(BaseEmbedder):
    """生产模式: 使用 sentence-transformers 加载 BAAI/bge-m3"""

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu", batch_size: int = 32):
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._model = None
        self._dim_value = 1024  # bge-m3 default

    def _load_model(self):
        """延迟加载模型 (首次调用时加载)"""
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self._model_name} on {self._device}")
            self._model = SentenceTransformer(self._model_name, device=self._device)
            # 获取实际输出维度
            test_vec = self._model.encode(["test"], normalize_embeddings=True)
            self._dim_value = test_vec.shape[1]
            logger.info(f"Embedding model loaded: dim={self._dim_value}")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model {self._model_name}: {e}")
            raise

    @property
    def dim(self) -> int:
        return self._dim_value

    def embed_text(self, text: str) -> np.ndarray:
        self._load_model()
        vec = self._model.encode([text], normalize_embeddings=True, batch_size=1)
        return vec[0].astype(np.float32)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        self._load_model()
        vecs = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=self._batch_size,
            show_progress_bar=len(texts) > 100,
        )
        return vecs.astype(np.float32)


def create_embedder() -> BaseEmbedder:
    """
    工厂函数: 根据配置创建对应的 Embedder
    - embedding.mode == "dev" -> HashEmbedder
    - embedding.mode == "prod" -> BGEEmbedder
    """
    embed_config = get_embedding_config()
    rag_config = get_rag_config()

    if embed_config.mode == "prod":
        logger.info(f"Creating BGEEmbedder (mode=prod, model={embed_config.model_name})")
        return BGEEmbedder(
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
            self._inner = BGEEmbedder(
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
