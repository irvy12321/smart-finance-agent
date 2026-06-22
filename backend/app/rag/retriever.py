from app.infrastructure.config import get_rag_config
from app.rag.chunker import chunk_text
from app.rag.embed import BaseEmbedder, create_embedder
from app.rag.vector_store import VectorStore
from app.utils.logger import get_logger

logger = get_logger("retriever")

# 与 RAG API 共享同一个持久化目录
_RAG_DATA_DIR = None


def _get_persist_dir() -> str:
    """获取 RAG 向量存储持久化目录（与 RAG API 一致）"""
    global _RAG_DATA_DIR
    if _RAG_DATA_DIR is None:
        from pathlib import Path

        _RAG_DATA_DIR = (
            Path(__file__).parent.parent.parent / "data" / "rag" / "vector_store"
        )
    return str(_RAG_DATA_DIR)


def _keyword_search(
    query: str, texts: list[str], metadata: list[dict], top_k: int = 5
) -> list[dict]:
    """关键词搜索（BM25 风格）"""
    import math
    import re

    # 分词（更宽松）
    def tokenize(text):
        tokens = set(re.findall(r"\b[a-z0-9]+\b", text.lower()))
        # 添加子串匹配
        words = text.lower().split()
        for word in words:
            if len(word) > 3:
                tokens.add(word)
        return tokens

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    # 计算 IDF
    n_docs = len(texts)
    doc_freq = {}
    doc_tokens_list = []
    for text in texts:
        tokens = tokenize(text)
        doc_tokens_list.append(tokens)
        for token in tokens:
            doc_freq[token] = doc_freq.get(token, 0) + 1

    # 计算每个文档的相关性分数
    scores = []
    for i, (text, doc_tokens) in enumerate(zip(texts, doc_tokens_list, strict=False)):
        # 词重叠（包含子串匹配）
        overlap = set()
        for qt in query_tokens:
            for dt in doc_tokens:
                if qt in dt or dt in qt:
                    overlap.add(qt)
                    overlap.add(dt)
            if qt in doc_tokens:
                overlap.add(qt)

        if not overlap:
            scores.append((0, i))
            continue

        # BM25 风格分数
        score = 0
        for token in overlap:
            tf = 1
            idf = math.log((n_docs + 1) / (doc_freq.get(token, 1) + 1)) + 1
            score += tf * idf

        # 文本包含查询词的额外加分
        query_lower = query.lower()
        text_lower = text.lower()
        for word in query_lower.split():
            if word in text_lower:
                score *= 1.5

        scores.append((score, i))

    # 排序并返回 top_k
    scores.sort(reverse=True)
    results = []
    for score, idx in scores[:top_k]:
        if score > 0:
            results.append(
                {
                    "text": texts[idx],
                    "score": min(score / 10, 1.0),
                    "metadata": metadata[idx] if idx < len(metadata) else {},
                    "index": idx,
                }
            )
    return results


class Retriever:
    def __init__(self, embedder: BaseEmbedder | None = None):
        config = get_rag_config()
        self.embedder = embedder or create_embedder()
        # 使用与 RAG API 相同的持久化目录
        persist_dir = _get_persist_dir()
        self.store = VectorStore(
            dim=self.embedder.dim, persist_dir=persist_dir, embedder=self.embedder
        )
        self.store.load()
        self.top_k = config.top_k
        logger.info(
            f"Retriever initialized: dim={self.embedder.dim}, top_k={self.top_k}, persist_dir={persist_dir}, loaded={self.store.size} vectors"
        )

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

        # 先尝试向量搜索
        vector_results = []
        if self.store.size > 0:
            query_vec = self.embedder.embed_text(query)
            vector_results = self.store.search(query_vec, top_k=k)

        # 检查向量搜索结果质量
        best_score = max([r.get("score", 0) for r in vector_results], default=0)

        # 如果向量搜索结果分数较低，使用关键词搜索
        keyword_results = []
        if best_score < 0.1 and self.store.size > 0:
            keyword_results = _keyword_search(
                query, self.store.texts, self.store.metadata, top_k=k
            )

        # 如果关键词搜索有结果，优先使用
        if keyword_results:
            results = keyword_results
        else:
            # 过滤掉分数为0的结果
            results = [r for r in vector_results if r.get("score", 0) > 0]
            if not results:
                results = vector_results[:k]

        # 按分数排序
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        results = results[:k]

        logger.info(f"Retrieved {len(results)} results for query: {query[:50]}...")
        return results

    @property
    def doc_count(self) -> int:
        return self.store.size
