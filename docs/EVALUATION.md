# Evaluation and Reliability Evidence

This document records the reproducible evaluations behind the claims in the
project README. The harnesses use deterministic Python metrics rather than an
LLM-as-judge.

## RAG retrieval evaluation

The retrieval benchmark contains 62 financial documents and 44 gold queries,
including 12 Chinese paraphrase and colloquial-query cases. The following
results were re-measured on CPU on 2026-08-03.

| Embedder | R@1 | R@3 | R@5 | P@5 | MRR | nDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hash (development pseudo-vector) | 0.1818 | 0.3409 | 0.3864 | 0.0773 | 0.2808 | 0.2938 |
| BM25 (lexical) | 0.5682 | 0.6591 | 0.6818 | 0.1364 | 0.6188 | 0.6294 |
| BGE small zh v1.5 (semantic) | **0.8182** | **0.9318** | **0.9545** | **0.1909** | **0.8795** | **0.8987** |

On the Chinese paraphrase subset, BM25 scored `0/0` for Recall@5/MRR, while
BGE scored `1.0000/0.9583`. This distinction is important: the local BM25 mode
is lexical retrieval and is not presented as semantic retrieval.

Run the benchmark with a locally cached semantic model:

```powershell
cd backend
python -m pip install -r requirements-semantic.txt
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
python scripts/rag_eval.py --local-files-only
```

The production image pins `BAAI/bge-small-zh-v1.5` to revision
`7999e1d3359715c523056ef9478215996d62a620`. Index metadata includes the model,
revision, dimension, normalization and query-instruction fingerprint. An
incompatible index is rebuilt from persisted chunks or rejected, depending on
`index_mismatch_policy`.

## Orchestration reliability

`backend/app/core/reliability.py` provides a seeded fault-injection harness. It
does not call external APIs or LLMs, so it is repeatable in CI.

```powershell
cd backend
python scripts/reliability_eval.py
```

The command writes raw results to `backend/data/reliability_eval/results.json`.
The reference run used `seed=42`.

### Single-point tool failure

The primary tool fails with probability `p`; the fallback tool remains healthy.
Each row contains 400 trials.

| p(fail) | served | hard failure | real-tool recovery | static fallback |
| ---: | ---: | ---: | ---: | ---: |
| 0.00 | 1.000 | 0.000 | 0.000 | 0.000 |
| 0.25 | 1.000 | 0.000 | 0.260 | 0.000 |
| 0.50 | 1.000 | 0.000 | 0.492 | 0.000 |
| 0.75 | 1.000 | 0.000 | 0.750 | 0.000 |
| 1.00 | 1.000 | 0.000 | 1.000 | 0.000 |

### Correlated tool failure

The primary and alternative tools fail together with probability `p`. Static
fallbacks remain explicitly labelled and cap final confidence.

| p(fail) | served | hard failure | real-tool recovery | static fallback |
| ---: | ---: | ---: | ---: | ---: |
| 0.00 | 1.000 | 0.000 | 0.000 | 0.000 |
| 0.25 | 1.000 | 0.000 | 0.242 | 0.020 |
| 0.50 | 1.000 | 0.000 | 0.352 | 0.133 |
| 0.75 | 1.000 | 0.000 | 0.270 | 0.430 |
| 1.00 | 1.000 | 0.000 | 0.000 | 1.000 |

### Circuit breaker and deadlock recovery

With a fully unavailable tool, a threshold of five and 100 calls, the breaker
invoked the tool five times and short-circuited the remaining 95 calls. In 50
seeded dependency-failure scenarios, deadlock recovery released all 50 stalled
DAGs so downstream work could continue.

These results show availability under the tested fault model. A statically
served response is degraded output, not equivalent to a successful real-data
response. The application preserves that distinction in status, warnings and
confidence.

## Agent output evaluation

`backend/app/core/evaluation.py` and `backend/data/golden_dataset.json` define ten
end-to-end cases. Metrics include task success, tool accuracy, retrieval recall
and answer groundedness. Groundedness checks required numbers and rejects
forbidden numbers without asking an LLM to grade another LLM.

Validate the dataset and imports without external calls:

```powershell
cd backend
python -m app.core.evaluation --dry-run
```

The full evaluation supports independent threshold gates:
`--min-task-success`, `--min-tool-accuracy`, `--min-retrieval-recall` and
`--min-groundedness`. CI always runs the dry check; the model-backed suite is
enabled with `AGENT_EVAL_ENABLED=true` and the required provider credentials.
