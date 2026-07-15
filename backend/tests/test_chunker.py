import threading
from itertools import pairwise
from types import SimpleNamespace

import numpy as np
import pytest

from app.api import rag as rag_api
from app.core import memory as memory_module
from app.rag import chunker
from app.rag import retriever as retriever_module
from app.rag.embed import BM25Embedder


class _FakeEmbedder:
    supports_semantic_similarity = False

    def embed_batch(self, texts):
        return np.ones((len(texts), 2), dtype=np.float32)


class _RecordingStore:
    def __init__(self):
        self.added = None
        self.saved = False

    def add(self, embeddings, texts, metadata):
        self.added = (embeddings, texts, metadata)

    def save(self):
        self.saved = True


def _config(**overrides):
    values = {
        "chunk_size": 100,
        "chunk_overlap": 20,
        "semantic_chunking_enabled": False,
        "semantic_chunking_threshold": 0.5,
        "semantic_chunking_min_chunk_size": 20,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_long_unspaced_chinese_is_hard_split_with_bounded_overlap():
    text = "中" * 401

    chunks = chunker.chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    assert all(0 < len(part) <= 100 for part in chunks)
    assert all(
        current.startswith(previous[-20:]) for previous, current in pairwise(chunks)
    )


def test_chinese_sentence_boundaries_are_preferred():
    text = ("甲" * 70 + "。") + ("乙" * 70 + "。") + ("丙" * 70 + "。")

    chunks = chunker.chunk_text(text, chunk_size=100, overlap=10)

    assert chunks[0].endswith("。")
    assert chunks[1].endswith("。")
    assert all(len(part) <= 100 for part in chunks)
    assert all(
        current.startswith(previous[-10:]) for previous, current in pairwise(chunks)
    )


def test_default_fifty_character_overlap_stays_inside_chunk_limit():
    chunks = chunker.chunk_text("长" * 300, chunk_size=120, overlap=50)

    assert all(len(part) <= 120 for part in chunks)
    assert all(
        current.startswith(previous[-50:]) for previous, current in pairwise(chunks)
    )


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_empty_text_returns_no_chunks(text):
    assert chunker.chunk_text(text) == []
    assert chunker.chunk_document(text) == []


def test_semantic_config_falls_back_for_lexical_embedder(monkeypatch):
    config = _config(semantic_chunking_enabled=True)
    monkeypatch.setattr(chunker, "get_rag_config", lambda: config)

    def unexpected_semantic_chunk(*args, **kwargs):
        pytest.fail("lexical embedders must not trigger semantic chunking")

    monkeypatch.setattr(chunker, "semantic_chunk", unexpected_semantic_chunk)
    text = "中文内容" * 80

    lexical_embedder = BM25Embedder()
    assert lexical_embedder.supports_semantic_similarity is False
    assert chunker.chunk_document(text, lexical_embedder) == chunker.chunk_text(text)


def test_semantic_config_uses_capable_embedder_without_loading_a_model(monkeypatch):
    config = _config(semantic_chunking_enabled=True)
    monkeypatch.setattr(chunker, "get_rag_config", lambda: config)

    class SemanticFake(_FakeEmbedder):
        supports_semantic_similarity = True

        def embed_batch(self, texts):
            return np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

    text = "甲" * 30 + "\n\n" + "乙" * 30

    assert chunker.chunk_document(text, SemanticFake()) == ["甲" * 30, "乙" * 30]


def test_semantic_chunk_fallback_also_bounds_unspaced_text():
    chunks = chunker.semantic_chunk(
        "中" * 260, embedder=None, max_chunk_size=100, overlap=20
    )

    assert all(len(part) <= 100 for part in chunks)
    assert all(
        current.startswith(previous[-20:]) for previous, current in pairwise(chunks)
    )


def test_retriever_add_document_uses_unified_chunk_entry(monkeypatch):
    instance = retriever_module.Retriever.__new__(retriever_module.Retriever)
    instance.embedder = _FakeEmbedder()
    instance.store = _RecordingStore()
    seen = {}

    def fake_chunk_document(text, embedder):
        seen.update(text=text, embedder=embedder)
        return ["first", "second"]

    monkeypatch.setattr(retriever_module, "chunk_document", fake_chunk_document)

    instance.add_document("source text", {"source": "unit-test"})

    assert seen == {"text": "source text", "embedder": instance.embedder}
    assert instance.store.added[1] == ["first", "second"]
    assert [item["chunk_index"] for item in instance.store.added[2]] == [0, 1]


@pytest.mark.asyncio
async def test_upload_processing_uses_unified_chunk_entry(monkeypatch):
    embedder = _FakeEmbedder()
    store = _RecordingStore()
    statuses = []
    seen = {}

    def fake_chunk_document(text, actual_embedder):
        seen.update(text=text, embedder=actual_embedder)
        return ["upload chunk"]

    monkeypatch.setattr(rag_api, "chunk_document", fake_chunk_document)
    monkeypatch.setattr(rag_api, "_get_embedder", lambda: embedder)
    monkeypatch.setattr(rag_api, "_get_vector_store", lambda: store)
    monkeypatch.setattr(
        rag_api,
        "_update_document_status",
        lambda doc_id, status, count: statuses.append((doc_id, status, count)),
    )

    await rag_api._process_document(
        "doc-1",
        "uploaded text",
        {"source": "upload"},
        filename="a.txt",
        file_type=".txt",
    )

    assert seen == {"text": "uploaded text", "embedder": embedder}
    assert store.added[1] == ["upload chunk"]
    assert store.saved is True
    assert statuses == [("doc-1", "completed", 1)]


def test_long_term_memory_uses_unified_chunk_entry(monkeypatch):
    instance = memory_module.LongTermMemory.__new__(memory_module.LongTermMemory)
    instance.enabled = True
    instance.embedder = _FakeEmbedder()
    instance.store = _RecordingStore()
    instance._write_lock = threading.Lock()
    seen = {}

    def fake_chunk_document(text, embedder):
        seen.update(text=text, embedder=embedder)
        return ["memory chunk"]

    monkeypatch.setattr(memory_module, "chunk_document", fake_chunk_document)

    instance.store_memory("remember this", {"kind": "test"})

    assert seen == {"text": "remember this", "embedder": instance.embedder}
    assert instance.store.added[1] == ["memory chunk"]
    assert instance.store.saved is True
