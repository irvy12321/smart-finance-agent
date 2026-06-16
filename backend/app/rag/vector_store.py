"""
FAISS 向量存储 - 支持增量添加 + 磁盘持久化
"""

import json
import os

import faiss
import numpy as np

from app.utils.logger import get_logger

logger = get_logger("vector_store")


class VectorStore:
    def __init__(self, dim: int, persist_dir: str | None = None):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.texts: list[str] = []
        self.metadata: list[dict] = []
        self.persist_dir = persist_dir
        self._loaded = False

    def add(
        self,
        embeddings: np.ndarray,
        texts: list[str],
        metadata: list[dict] | None = None,
    ):
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.texts.extend(texts)
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{}] * len(texts))
        logger.info(f"VectorStore: added {len(texts)} items, total={self.index.ntotal}")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[dict]:
        if self.index.ntotal == 0:
            return []
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_embedding, k)
        results = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx < 0:
                continue
            results.append(
                {
                    "text": self.texts[idx],
                    "score": float(score),
                    "metadata": self.metadata[idx],
                    "index": int(idx),
                }
            )
        return results

    def save(self, path: str | None = None):
        """持久化到磁盘"""
        save_dir = path or self.persist_dir
        if not save_dir:
            logger.warning("No persist_dir configured, skipping save")
            return

        os.makedirs(save_dir, exist_ok=True)
        # 保存 FAISS 索引
        faiss.write_index(self.index, os.path.join(save_dir, "faiss.index"))
        # 保存文本和元数据
        with open(os.path.join(save_dir, "texts.json"), "w", encoding="utf-8") as f:
            json.dump(self.texts, f, ensure_ascii=False)
        with open(os.path.join(save_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False)
        # 保存维度信息
        with open(os.path.join(save_dir, "config.json"), "w") as f:
            json.dump({"dim": self.dim}, f)

        logger.info(f"VectorStore saved to {save_dir}: {self.index.ntotal} vectors")

    def load(self, path: str | None = None) -> bool:
        """从磁盘加载"""
        load_dir = path or self.persist_dir
        if not load_dir:
            return False

        index_path = os.path.join(load_dir, "faiss.index")
        texts_path = os.path.join(load_dir, "texts.json")
        meta_path = os.path.join(load_dir, "metadata.json")
        config_path = os.path.join(load_dir, "config.json")

        if not all(
            os.path.exists(p) for p in [index_path, texts_path, meta_path, config_path]
        ):
            logger.info(f"No existing data at {load_dir}, starting fresh")
            return False

        try:
            with open(config_path) as f:
                config = json.load(f)
            if config.get("dim") != self.dim:
                logger.warning(
                    f"Dimension mismatch: stored={config.get('dim')}, current={self.dim}"
                )
                return False

            self.index = faiss.read_index(index_path)
            with open(texts_path, encoding="utf-8") as f:
                self.texts = json.load(f)
            with open(meta_path, encoding="utf-8") as f:
                self.metadata = json.load(f)

            self._loaded = True
            logger.info(
                f"VectorStore loaded from {load_dir}: {self.index.ntotal} vectors"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load VectorStore: {e}")
            return False

    @property
    def size(self) -> int:
        return self.index.ntotal

    def clear(self):
        """清空所有数据"""
        self.index = faiss.IndexFlatIP(self.dim)
        self.texts.clear()
        self.metadata.clear()
        logger.info("VectorStore cleared")
