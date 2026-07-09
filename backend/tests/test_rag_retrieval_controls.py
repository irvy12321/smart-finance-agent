import json
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from app.api import rag as rag_api
from app.rag.query_rewriter import multi_query_retrieve
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.tools.rag_tool import RAGTool


def test_vector_store_metadata_filter_searches_beyond_initial_top_k():
    store = VectorStore(dim=2)
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.95, 0.05],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )
    store.add(
        embeddings,
        ["apple result", "microsoft result", "tesla result"],
        [{"ticker": "AAPL"}, {"ticker": "MSFT"}, {"ticker": "TSLA"}],
    )

    results = store.search(
        np.array([1.0, 0.0], dtype=np.float32),
        top_k=1,
        metadata_filter={"ticker": "MSFT"},
    )

    assert len(results) == 1
    assert results[0]["metadata"]["ticker"] == "MSFT"


def test_vector_store_metadata_filter_matches_tag_intersection():
    store = VectorStore(dim=2)
    store.add(
        np.array([[1.0, 0.0]], dtype=np.float32),
        ["risk disclosure"],
        [{"tags": ["risk", "10-k"]}],
    )

    results = store.search(
        np.array([1.0, 0.0], dtype=np.float32),
        metadata_filter={"tags": ["risk"]},
    )

    assert len(results) == 1


def test_vector_store_min_score_filters_low_relevance():
    store = VectorStore(dim=2)
    store.add(
        np.array([[0.0, 1.0]], dtype=np.float32),
        ["unrelated"],
        [{"ticker": "TSLA"}],
    )

    results = store.search(
        np.array([1.0, 0.0], dtype=np.float32),
        top_k=1,
        min_score=0.2,
    )

    assert results == []


def test_vector_store_rejects_mismatched_add_payloads():
    store = VectorStore(dim=2)

    with pytest.raises(ValueError, match="embeddings/texts"):
        store.add(
            np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
            ["only one text"],
        )

    with pytest.raises(ValueError, match="metadata/texts"):
        store.add(
            np.array([[1.0, 0.0]], dtype=np.float32),
            ["one text"],
            [{"id": 1}, {"id": 2}],
        )


def test_vector_store_load_rejects_inconsistent_persistence(tmp_path):
    store = VectorStore(dim=2, persist_dir=str(tmp_path))
    store.add(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        ["first", "second"],
        [{"id": 1}, {"id": 2}],
    )
    store.save()
    (tmp_path / "metadata.json").write_text(json.dumps([{"id": 1}]), encoding="utf-8")

    reloaded = VectorStore(dim=2, persist_dir=str(tmp_path))

    assert reloaded.load() is False
    assert reloaded.size == 0


def test_vector_store_concurrent_add_and_search_keeps_invariants():
    store = VectorStore(dim=2)

    def add_and_search(i: int):
        vector = np.array([[1.0, (i % 10) / 100]], dtype=np.float32)
        store.add(vector, [f"doc-{i}"], [{"id": i}])
        return store.search(np.array([1.0, 0.0], dtype=np.float32), top_k=3)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(add_and_search, range(50)))

    texts, metadata = store.snapshot()
    assert store.size == 50
    assert len(texts) == 50
    assert len(metadata) == 50
    assert all(isinstance(result, list) for result in results)


def test_vector_store_rebuild_replaces_existing_contents():
    store = VectorStore(dim=2)
    store.add(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        ["old-a", "old-b"],
        [{"id": "old-a"}, {"id": "old-b"}],
    )

    store.rebuild(
        np.array([[1.0, 0.0]], dtype=np.float32),
        ["new-a"],
        [{"id": "new-a"}],
    )

    texts, metadata = store.snapshot()
    assert store.size == 1
    assert texts == ["new-a"]
    assert metadata == [{"id": "new-a"}]


def test_retriever_normalize_metadata_sets_source_doc_type_and_chunk_index():
    metadata = Retriever.normalize_metadata(
        {"ticker": "AAPL"},
        doc_id="doc-1",
        filename="apple-10k.pdf",
        file_type=".pdf",
    )

    assert metadata["source"] == "apple-10k.pdf"
    assert metadata["doc_type"] == "pdf"
    assert metadata["doc_id"] == "doc-1"
    assert metadata["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_rag_delete_document_rebuilds_from_vector_store_snapshot(monkeypatch):
    documents = [
        {
            "id": "keep",
            "filename": "keep.md",
            "file_type": ".md",
            "file_size": 10,
            "chunk_count": 1,
            "status": "completed",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "metadata": {},
        },
        {
            "id": "drop",
            "filename": "drop.md",
            "file_type": ".md",
            "file_size": 10,
            "chunk_count": 1,
            "status": "completed",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "metadata": {},
        },
    ]
    saved_documents = []

    class _Store:
        def __init__(self):
            self.rebuilt = None
            self.saved = False

        def snapshot(self):
            return ["keep text", "drop text"], [
                {"doc_id": "keep"},
                {"doc_id": "drop"},
            ]

        def rebuild(self, embeddings, texts, metadata):
            self.rebuilt = (embeddings, texts, metadata)

        def clear(self):
            self.rebuilt = "cleared"

        def save(self):
            self.saved = True

    class _Embedder:
        def embed_batch(self, texts):
            return np.ones((len(texts), 2), dtype=np.float32)

    store = _Store()
    monkeypatch.setattr(rag_api, "_load_documents", lambda: list(documents))
    monkeypatch.setattr(
        rag_api, "_save_documents", lambda docs: saved_documents.append(docs)
    )
    monkeypatch.setattr(rag_api, "_get_vector_store", lambda: store)
    monkeypatch.setattr(rag_api, "_get_embedder", lambda: _Embedder())

    response = await rag_api.delete_document("drop", current_user=object())

    assert response.document_id == "drop"
    assert store.saved is True
    assert store.rebuilt[1] == ["keep text"]
    assert store.rebuilt[2] == [{"doc_id": "keep"}]
    assert [doc["id"] for doc in saved_documents[-1]] == ["keep"]


class _FakeRetriever:
    doc_count = 3

    def retrieve(self, query, **kwargs):
        self.query = query
        self.kwargs = kwargs
        return []


@pytest.mark.asyncio
async def test_rag_tool_distinguishes_empty_kb_from_no_matches():
    retriever = _FakeRetriever()
    result = await RAGTool(retriever=retriever).execute(
        query="apple revenue",
        metadata_filter={"ticker": "MSFT"},
        min_score=0.7,
    )

    assert result.success is True
    assert result.data["results"] == []
    assert result.data["message"] == "No matching documents found in knowledge base"
    assert retriever.kwargs["metadata_filter"] == {"ticker": "MSFT"}
    assert retriever.kwargs["min_score"] == 0.7


class _FakeRewriter:
    async def rewrite(self, query):
        return [query, f"{query} variant"]

    async def hyde(self, query):
        return f"{query} hypothetical document"


class _RecordingRetriever:
    def __init__(self):
        self.calls = []

    def retrieve(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return [{"text": query, "score": 0.9, "metadata": {"ticker": "AAPL"}}]


@pytest.mark.asyncio
async def test_multi_query_retrieve_passes_filters_to_all_probe_queries():
    retriever = _RecordingRetriever()

    results = await multi_query_retrieve(
        "apple revenue",
        retriever=retriever,
        rewriter=_FakeRewriter(),
        top_k=2,
        use_hyde=True,
        metadata_filter={"ticker": "AAPL"},
        min_score=0.5,
    )

    assert results
    assert len(retriever.calls) == 3
    for _, kwargs in retriever.calls:
        assert kwargs["metadata_filter"] == {"ticker": "AAPL"}
        assert kwargs["min_score"] == 0.5
