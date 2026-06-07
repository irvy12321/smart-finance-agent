"""
Component Tests - RAG Pipeline
Verifies: chunker, embedder, vector store, retriever
All tests run offline (uses HashEmbedder dev mode)
"""
import pytest
import numpy as np

from rag.chunker import chunk_text
from rag.embed import HashEmbedder
from rag.vector_store import VectorStore


# ============================================================
# Chunker Tests
# ============================================================

class TestChunker:
    def test_chunk_basic(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text, chunk_size=100, overlap=0)
        assert len(chunks) >= 1

    def test_chunk_empty_string(self):
        chunks = chunk_text("", chunk_size=100, overlap=0)
        assert chunks == []

    def test_chunk_respects_size_limit(self):
        # Use text with word boundaries so chunker can split properly
        long_text = "word " * 300  # ~1500 chars with spaces
        chunks = chunk_text(long_text, chunk_size=200, overlap=0)
        for chunk in chunks:
            assert len(chunk) <= 300  # Allow tolerance for word boundaries

    def test_chunk_preserves_content(self):
        text = "Hello world.\n\nGoodbye world."
        chunks = chunk_text(text, chunk_size=200, overlap=0)
        combined = " ".join(chunks)
        assert "Hello" in combined
        assert "Goodbye" in combined

    def test_chunk_with_overlap(self):
        text = "A" * 200 + "\n\n" + "B" * 200
        chunks_no_overlap = chunk_text(text, chunk_size=100, overlap=0)
        chunks_with_overlap = chunk_text(text, chunk_size=100, overlap=30)
        # Overlap should produce same or more chunks
        assert len(chunks_with_overlap) >= len(chunks_no_overlap)


# ============================================================
# Embedder Tests (HashEmbedder - dev mode)
# ============================================================

class TestEmbedder:
    def test_hash_embedder_dim(self):
        embedder = HashEmbedder(dimension=128)
        assert embedder.dim == 128

    def test_hash_embedder_produces_normalized_vectors(self):
        embedder = HashEmbedder(dimension=64)
        vec = embedder.embed_text("Tesla stock analysis")

        assert vec.shape == (64,)
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 0.01  # Should be normalized

    def test_hash_embedder_batch(self):
        embedder = HashEmbedder(dimension=32)
        texts = ["hello", "world", "finance"]
        vecs = embedder.embed_batch(texts)

        assert vecs.shape == (3, 32)

    def test_hash_embedder_deterministic(self):
        embedder = HashEmbedder(dimension=64)
        v1 = embedder.embed_text("same text")
        v2 = embedder.embed_text("same text")
        np.testing.assert_array_equal(v1, v2)

    def test_hash_embedder_different_texts_differ(self):
        embedder = HashEmbedder(dimension=64)
        v1 = embedder.embed_text("Apple Inc")
        v2 = embedder.embed_text("Microsoft Corp")
        assert not np.array_equal(v1, v2)


# ============================================================
# VectorStore Tests
# ============================================================

class TestVectorStore:
    def test_vectorstore_add_and_search(self):
        store = VectorStore(dim=64)
        embedder = HashEmbedder(dimension=64)

        texts = ["Tesla revenue growth", "Apple quarterly earnings", "Market volatility"]
        embeddings = embedder.embed_batch(texts)
        store.add(embeddings, texts)

        assert store.size == 3

        query = embedder.embed_text("Tesla financial performance")
        results = store.search(query, top_k=2)

        assert len(results) == 2
        assert all("score" in r for r in results)
        assert all("text" in r for r in results)
        assert results[0]["score"] >= results[1]["score"]

    def test_vectorstore_empty_search(self):
        store = VectorStore(dim=32)
        embedder = HashEmbedder(dimension=32)

        query = embedder.embed_text("test")
        results = store.search(query, top_k=5)

        assert results == []

    def test_vectorstore_top_k_limit(self):
        store = VectorStore(dim=32)
        embedder = HashEmbedder(dimension=32)

        texts = [f"Document {i}" for i in range(10)]
        embeddings = embedder.embed_batch(texts)
        store.add(embeddings, texts)

        query = embedder.embed_text("test query")
        results = store.search(query, top_k=3)

        assert len(results) == 3

    def test_vectorstore_metadata(self):
        store = VectorStore(dim=32)
        embedder = HashEmbedder(dimension=32)

        texts = ["doc A", "doc B"]
        embeddings = embedder.embed_batch(texts)
        metadata = [{"source": "file_a"}, {"source": "file_b"}]
        store.add(embeddings, texts, metadata)

        query = embedder.embed_text("doc A")
        results = store.search(query, top_k=1)

        assert results[0]["metadata"]["source"] == "file_a"

    def test_vectorstore_clear(self):
        store = VectorStore(dim=32)
        embedder = HashEmbedder(dimension=32)

        embeddings = embedder.embed_batch(["a", "b"])
        store.add(embeddings, ["a", "b"])
        assert store.size == 2

        store.clear()
        assert store.size == 0


# ============================================================
# Retriever Tests (integration)
# ============================================================

class TestRetriever:
    def test_retriever_add_and_retrieve(self):
        from rag.retriever import Retriever

        retriever = Retriever(embedder=HashEmbedder(dimension=384))
        retriever.add_document("Tesla reported record revenue in Q4 2024.")
        retriever.add_document("Apple announced new product line.")
        retriever.add_document("S&P 500 reached all-time high.")

        results = retriever.retrieve("Tesla earnings", top_k=2)

        assert len(results) > 0
        assert retriever.doc_count == 3

    def test_retriever_returns_scores(self):
        from rag.retriever import Retriever

        retriever = Retriever(embedder=HashEmbedder(dimension=384))
        retriever.add_document("Financial analysis of tech stocks")
        retriever.add_document("Cooking recipes for dinner")

        results = retriever.retrieve("stock market analysis", top_k=2)

        assert len(results) > 0
        assert all("score" in r for r in results)
        assert all(isinstance(r["score"], float) for r in results)
