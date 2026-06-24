"""RAG retrieval-quality evaluation.

Information-retrieval metrics (Recall@k, Precision@k, MRR, nDCG@k) plus a small
harness that scores any ranking function against a labeled query set. Used to
compare embedders (hash vs BM25 vs semantic) quantitatively instead of by
eyeballing results.

Relevance is binary: a retrieved document id is either in the gold set or not.
"""

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

# A ranking function maps a query string to document ids ordered best-first.
RankFn = Callable[[str], list[str]]


def recall_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Fraction of the gold documents found in the top-k results."""
    if not relevant:
        return 0.0
    top = set(retrieved[:k])
    hits = sum(1 for r in relevant if r in top)
    return hits / len(relevant)


def precision_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Fraction of the top-k results that are gold documents."""
    if k <= 0:
        return 0.0
    relevant_set = set(relevant)
    hits = sum(1 for d in retrieved[:k] if d in relevant_set)
    return hits / k


def reciprocal_rank(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
    """1 / rank of the first relevant result, or 0 if none is retrieved."""
    relevant_set = set(relevant)
    for i, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant_set:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """Normalized discounted cumulative gain with binary relevance."""
    if not relevant:
        return 0.0
    relevant_set = set(relevant)
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant_set:
            dcg += 1.0 / math.log2(i + 1)
    ideal_hits = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


@dataclass
class EvalQuery:
    query: str
    relevant: list[str]
    type: str = "unlabeled"


@dataclass
class EvalReport:
    """Aggregate metrics over a query set, plus per-query-type breakdown."""

    n_queries: int
    ks: list[int]
    recall: dict[int, float] = field(default_factory=dict)
    precision: dict[int, float] = field(default_factory=dict)
    ndcg: dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0
    by_type: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "n_queries": self.n_queries,
            "ks": self.ks,
            "recall": {str(k): round(v, 4) for k, v in self.recall.items()},
            "precision": {str(k): round(v, 4) for k, v in self.precision.items()},
            "ndcg": {str(k): round(v, 4) for k, v in self.ndcg.items()},
            "mrr": round(self.mrr, 4),
            "by_type": {
                t: {m: round(v, 4) for m, v in metrics.items()}
                for t, metrics in self.by_type.items()
            },
        }


def load_eval_set(data_dir: str | Path) -> tuple[dict[str, str], list[EvalQuery]]:
    """Load the corpus (id -> text) and labeled queries from a directory."""
    data_dir = Path(data_dir)
    corpus_raw = json.loads((data_dir / "corpus.json").read_text(encoding="utf-8"))
    queries_raw = json.loads((data_dir / "queries.json").read_text(encoding="utf-8"))
    corpus = {d["id"]: d["text"] for d in corpus_raw["documents"]}
    queries = [
        EvalQuery(
            query=q["query"],
            relevant=list(q["relevant"]),
            type=q.get("type", "unlabeled"),
        )
        for q in queries_raw["queries"]
    ]
    return corpus, queries


def evaluate(
    rank_fn: RankFn,
    queries: Sequence[EvalQuery],
    ks: Sequence[int] = (1, 3, 5),
) -> EvalReport:
    """Score a ranking function against labeled queries.

    ``rank_fn`` returns document ids ordered best-first for a query. Metrics are
    macro-averaged across queries (each query weighted equally).
    """
    ks = sorted(set(ks))
    report = EvalReport(n_queries=len(queries), ks=list(ks))
    if not queries:
        return report

    recall_sum = dict.fromkeys(ks, 0.0)
    precision_sum = dict.fromkeys(ks, 0.0)
    ndcg_sum = dict.fromkeys(ks, 0.0)
    rr_sum = 0.0

    # Per-type accumulators (uses the largest k for the breakdown summary).
    type_acc: dict[str, dict[str, float]] = {}
    k_max = ks[-1]

    for q in queries:
        retrieved = rank_fn(q.query)
        rr = reciprocal_rank(retrieved, q.relevant)
        rr_sum += rr
        for k in ks:
            recall_sum[k] += recall_at_k(retrieved, q.relevant, k)
            precision_sum[k] += precision_at_k(retrieved, q.relevant, k)
            ndcg_sum[k] += ndcg_at_k(retrieved, q.relevant, k)

        acc = type_acc.setdefault(q.type, {"n": 0.0, "recall": 0.0, "mrr": 0.0})
        acc["n"] += 1
        acc["recall"] += recall_at_k(retrieved, q.relevant, k_max)
        acc["mrr"] += rr

    n = len(queries)
    report.recall = {k: recall_sum[k] / n for k in ks}
    report.precision = {k: precision_sum[k] / n for k in ks}
    report.ndcg = {k: ndcg_sum[k] / n for k in ks}
    report.mrr = rr_sum / n
    report.by_type = {
        t: {
            f"recall@{k_max}": acc["recall"] / acc["n"],
            "mrr": acc["mrr"] / acc["n"],
        }
        for t, acc in type_acc.items()
        if acc["n"] > 0
    }
    return report
