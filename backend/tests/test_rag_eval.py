"""Tests for the RAG evaluation metrics and harness.

Deterministic and torch-free: the semantic backend is NOT exercised here (it is
an optional dependency). The baseline test only asserts BM25 > hash, which holds
purely on lexical grounds.
"""

from pathlib import Path

from app.rag.embed import BM25Embedder, HashEmbedder
from app.rag.eval import (
    evaluate,
    load_eval_set,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.rag.vector_store import VectorStore

DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "rag" / "eval_data"


def test_recall_at_k_basic():
    retrieved = ["a", "b", "c", "d"]
    relevant = ["b", "d", "z"]  # z is never retrieved
    assert recall_at_k(retrieved, relevant, k=2) == 1 / 3  # only b in top-2
    assert recall_at_k(retrieved, relevant, k=4) == 2 / 3  # b and d found
    assert recall_at_k(retrieved, [], k=4) == 0.0


def test_precision_at_k_basic():
    retrieved = ["a", "b", "c", "d"]
    relevant = ["b", "d"]
    assert precision_at_k(retrieved, relevant, k=2) == 0.5  # 1 of top-2
    assert precision_at_k(retrieved, relevant, k=4) == 0.5  # 2 of top-4
    assert precision_at_k(retrieved, relevant, k=0) == 0.0


def test_mrr_basic():
    assert reciprocal_rank(["a", "b", "c"], ["b"]) == 0.5  # first hit at rank 2
    assert reciprocal_rank(["a", "b", "c"], ["a"]) == 1.0  # rank 1
    assert reciprocal_rank(["a", "b", "c"], ["z"]) == 0.0  # no hit


def test_ndcg_at_k_basic():
    # Single relevant doc at rank 1 => perfect nDCG.
    assert ndcg_at_k(["a", "b", "c"], ["a"], k=3) == 1.0
    # Relevant doc at rank 2: dcg = 1/log2(3), idcg = 1/log2(2) = 1.
    import math

    expected = (1.0 / math.log2(3)) / 1.0
    assert abs(ndcg_at_k(["a", "b", "c"], ["b"], k=3) - expected) < 1e-9
    # No relevant docs retrieved => 0.
    assert ndcg_at_k(["a", "b", "c"], ["z"], k=3) == 0.0


def test_ndcg_rewards_higher_ranking():
    relevant = ["x"]
    high = ndcg_at_k(["x", "a", "b"], relevant, k=3)
    low = ndcg_at_k(["a", "b", "x"], relevant, k=3)
    assert high > low


def _rank_fn_for(embedder, corpus: dict[str, str]):
    ids = list(corpus.keys())
    texts = [corpus[i] for i in ids]
    doc_vecs = embedder.embed_batch(texts)
    store = VectorStore(dim=embedder.dim, embedder=embedder)
    store.add(doc_vecs, texts, [{"id": i} for i in ids])

    def rank_fn(query: str) -> list[str]:
        qv = embedder.embed_text(query)
        return [h["metadata"]["id"] for h in store.search(qv, top_k=10)]

    return rank_fn


def test_eval_set_loads_and_is_consistent():
    corpus, queries = load_eval_set(DATA_DIR)
    assert len(corpus) >= 40
    assert len(queries) >= 20
    # Every gold id must exist in the corpus.
    for q in queries:
        assert q.relevant, f"query has no gold labels: {q.query}"
        for doc_id in q.relevant:
            assert doc_id in corpus, f"unknown gold id {doc_id!r} for {q.query!r}"


def test_bm25_outperforms_hash_on_eval_corpus():
    corpus, queries = load_eval_set(DATA_DIR)
    hash_report = evaluate(_rank_fn_for(HashEmbedder(), corpus), queries, ks=(1, 3, 5))
    bm25_report = evaluate(_rank_fn_for(BM25Embedder(), corpus), queries, ks=(1, 3, 5))
    assert bm25_report.recall[5] > hash_report.recall[5]
    assert bm25_report.mrr > hash_report.mrr
