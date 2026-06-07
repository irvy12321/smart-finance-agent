import numpy as np
from rag.embed import create_embedder, BaseEmbedder
from rag.vector_store import VectorStore
from rag.chunker import chunk_text
from infrastructure.config import get_rag_config
from utils.logger import get_logger

logger = get_logger("retriever")


class Retriever:
    def __init__(self, embedder: BaseEmbedder | None = None):
        config = get_rag_config()
        self.embedder = embedder or create_embedder()
        # 使用实际 embedder 的维度创建 VectorStore
        self.store = VectorStore(dim=self.embedder.dim)
        self.top_k = config.top_k
        logger.info(f"Retriever initialized: dim={self.embedder.dim}, top_k={self.top_k}")

    def add_document(self, text: str, metadata: dict | None = None):
        chunks = chunk_text(text)
        if not chunks:
            return
        embeddings = self.embedder.embed_batch(chunks)
        meta = [metadata or {}] * len(chunks)
        self.store.add(embeddings, chunks, meta)
        logger.info(f"Added document: {len(chunks)} chunks indexed")

    def add_texts(self, texts: list[str], metadata: list[dict] | None = None):
        embeddings = self.embedder.embed_batch(texts)
        self.store.add(embeddings, texts, metadata)

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        k = top_k or self.top_k
        query_vec = self.embedder.embed_text(query)
        results = self.store.search(query_vec, top_k=k)
        logger.info(f"Retrieved {len(results)} results for query: {query[:50]}...")
        return results

    @property
    def doc_count(self) -> int:
        return self.store.size
