"""Tests for the BM25 lexical embedder + its persistence across reloads.

These cover two previously-broken behaviours:
1. BM25 document-length normalization was a no-op (``b * avg_dl / avg_dl``),
   so longer documents were not penalized.
2. The fitted vocab/IDF was never persisted, so after a restart reloaded FAISS
   vectors and freshly embedded queries lived in different lexical spaces and
   the vector path silently degraded to keyword fallback.
"""

import numpy as np

from app.rag.embed import BM25Embedder
from app.rag.vector_store import VectorStore


def _fit(corpus: list[str]) -> BM25Embedder:
    emb = BM25Embedder()
    emb.embed_batch(corpus)  # fits vocab/IDF/avgdl from the corpus
    return emb


def test_bm25_length_normalization_penalizes_longer_docs():
    """A shared term should weigh more in a short doc than in a long one."""
    short_doc = "alpha"
    long_doc = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    emb = _fit([short_doc, long_doc])

    assert emb._avgdl > 1.0  # corpus avg doc length actually computed

    idx = emb._vocab["alpha"]
    w_short = emb._text_to_vector(short_doc)[idx]
    w_long = emb._text_to_vector(long_doc)[idx]

    # With real BM25 length normalization the shorter document wins.
    assert w_short > w_long


def test_embedder_state_roundtrip_preserves_query_space():
    corpus = [
        "apple reports record quarterly revenue and earnings",
        "the federal reserve raised interest rates again",
        "tesla unveils a new electric vehicle model",
    ]
    original = _fit(corpus)
    query = "apple quarterly earnings"
    expected = original.embed_text(query)

    state = original.get_state()
    assert state and "idf" in state and state["vocab"]

    restored = BM25Embedder()
    restored.load_state(state)
    got = restored.embed_text(query)

    assert restored._avgdl == original._avgdl
    np.testing.assert_allclose(got, expected, rtol=1e-6, atol=1e-6)


def test_vector_store_persists_and_restores_embedder_state(tmp_path):
    corpus = [
        "apple reports record quarterly revenue",
        "tesla unveils a new electric vehicle",
        "the federal reserve raised interest rates",
    ]
    emb = _fit(corpus)
    store = VectorStore(dim=emb.dim, persist_dir=str(tmp_path), embedder=emb)
    store.add(emb.embed_batch(corpus), corpus)
    store.save()

    assert (tmp_path / "embedder_state.json").exists()

    # Fresh embedder + store, simulating a process restart.
    reloaded_emb = BM25Embedder()
    reloaded_store = VectorStore(
        dim=reloaded_emb.dim, persist_dir=str(tmp_path), embedder=reloaded_emb
    )
    assert reloaded_store.load() is True

    # Embedder space restored: query embeds identically and vector search hits.
    assert reloaded_emb.get_state()  # fitted, not empty
    query = "apple quarterly revenue"
    np.testing.assert_allclose(
        reloaded_emb.embed_text(query), emb.embed_text(query), rtol=1e-6, atol=1e-6
    )

    results = reloaded_store.search(reloaded_emb.embed_text(query), top_k=1)
    assert results and results[0]["text"] == corpus[0]
