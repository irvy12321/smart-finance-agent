"""Standalone RAG retrieval A/B harness: hash vs BM25 vs semantic.

Builds an in-memory FAISS index over the eval corpus with each embedder, runs
the labeled query set through it, and prints + persists Recall@k / MRR / nDCG.

NOT part of the CI test suite (the semantic backend is an optional dependency
and downloads a model). Run manually to regenerate the README numbers:

    python -m scripts.rag_eval                # from the backend/ directory

Use --no-semantic to skip the neural backend if it is not installed.
"""

import argparse
import json
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.rag.embed import BM25Embedder, HashEmbedder, SemanticEmbedder  # noqa: E402
from app.rag.eval import evaluate, load_eval_set  # noqa: E402
from app.rag.vector_store import VectorStore  # noqa: E402

DATA_DIR = _BACKEND_DIR / "app" / "rag" / "eval_data"
KS = (1, 3, 5)
SEARCH_DEPTH = 10


def _make_rank_fn(embedder, corpus: dict[str, str]):
    """Index the corpus with ``embedder`` and return a query -> ranked-ids fn."""
    ids = list(corpus.keys())
    texts = [corpus[i] for i in ids]
    # embed_batch fits BM25 vocab/IDF; queries then share that lexical space.
    doc_vecs = embedder.embed_batch(texts)
    store = VectorStore(dim=embedder.dim, embedder=embedder)
    store.add(doc_vecs, texts, [{"id": i} for i in ids])

    def rank_fn(query: str) -> list[str]:
        qv = embedder.embed_query(query)
        hits = store.search(qv, top_k=SEARCH_DEPTH)
        return [h["metadata"]["id"] for h in hits]

    return rank_fn


def _build_embedders(
    use_semantic: bool,
    semantic_model: str,
    semantic_revision: str,
    local_files_only: bool,
) -> dict:
    embedders: dict[str, object] = {
        "hash (dev, lexical)": HashEmbedder(),
        "bm25 (prod, lexical)": BM25Embedder(),
    }
    if use_semantic:
        try:
            start = time.perf_counter()
            emb = SemanticEmbedder(
                model_name=semantic_model,
                backend="sentence_transformers",
                model_revision=semantic_revision,
                query_instruction="为这个句子生成表示以用于检索相关文章：",
                local_files_only=local_files_only,
            )
            emb.load_seconds = time.perf_counter() - start
            embedders[f"semantic ({semantic_model})"] = emb
        except ImportError as e:
            print(f"[skip] semantic backend unavailable: {e}\n")
    return embedders


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG retrieval A/B evaluation")
    parser.add_argument(
        "--no-semantic", action="store_true", help="skip the neural semantic backend"
    )
    parser.add_argument(
        "--semantic-model",
        default="BAAI/bge-small-zh-v1.5",
        help="sentence-transformers model used for the semantic comparison",
    )
    parser.add_argument(
        "--semantic-revision",
        default="7999e1d3359715c523056ef9478215996d62a620",
        help="pinned Hugging Face model revision",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="fail instead of downloading a missing semantic model",
    )
    parser.add_argument(
        "--out",
        default=str(_BACKEND_DIR / "data" / "rag_eval" / "results.json"),
        help="where to write the JSON results (gitignored by default)",
    )
    args = parser.parse_args()

    corpus, queries = load_eval_set(DATA_DIR)
    print(f"corpus={len(corpus)} docs  queries={len(queries)}  ks={list(KS)}\n")

    embedders = _build_embedders(
        use_semantic=not args.no_semantic,
        semantic_model=args.semantic_model,
        semantic_revision=args.semantic_revision,
        local_files_only=args.local_files_only,
    )
    results: dict[str, dict] = {}

    header = f"{'embedder':<26} {'R@1':>6} {'R@3':>6} {'R@5':>6} {'P@5':>6} {'MRR':>6} {'nDCG@5':>7}"
    print(header)
    print("-" * len(header))
    for name, embedder in embedders.items():
        rank_fn = _make_rank_fn(embedder, corpus)
        report = evaluate(rank_fn, queries, ks=KS)
        results[name] = report.to_dict()
        if hasattr(embedder, "load_seconds"):
            results[name]["load_seconds"] = round(embedder.load_seconds, 3)
        print(
            f"{name:<26} "
            f"{report.recall[1]:>6.3f} {report.recall[3]:>6.3f} {report.recall[5]:>6.3f} "
            f"{report.precision[5]:>6.3f} {report.mrr:>6.3f} {report.ndcg[5]:>7.3f}"
        )

    # Per-type (lexical vs semantic queries) breakdown for the strongest setup.
    print("\nBy query type (recall@5 / mrr):")
    for name, report in results.items():
        bt = report.get("by_type", {})
        parts = [
            f"{t}: R@5={m.get('recall@5', 0):.3f} MRR={m.get('mrr', 0):.3f}"
            for t, m in sorted(bt.items())
        ]
        print(f"  {name:<26} " + "  ".join(parts))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
