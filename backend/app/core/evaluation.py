"""End-to-end evaluation harness for the Agent pipeline.

Quantifies Agent output quality along four axes:

* task_success_rate  — did the Executor's DAG complete successfully?
* tool_accuracy      — did the Planner pick the tools we expected?
* retrieval_recall@k — for RAG cases, were the expected docs retrieved?
* answer_groundedness — do the expected numbers appear in the answer, and
                       do the forbidden (hallucination-trap) numbers NOT appear?

Design:

* Zero-intrusion: calls ``orchestrator.run(query)`` exactly as production does.
* No LLM-as-judge — every metric is deterministic Python over the RunResult.
* Golden cases live in a JSON file so they can be versioned and extended
  without touching code.
* ``--dry-run`` loads the golden set and reports case count + categories,
  proving the module imports and the dataset parses without making any LLM /
  network calls. Safe for CI smoke tests.
* ``--min-*`` threshold flags turn the run into a regression gate: when any
  aggregate metric falls below its threshold the process exits non-zero, so
  CI can fail the build on prompt / planner / RAG regressions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.core.orchestrator import Orchestrator, RunResult

logger = get_logger("evaluation")


# ── Data structures ┇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class GoldenCase:
    """A single labeled test case for the Agent pipeline."""

    query: str
    expected_tools: list[str]
    expected_data_fields: list[str]
    expected_answer_numbers: list[float]
    forbidden_numbers: list[float]
    category: str  # "simple" / "standard" / "detailed"
    expected_rag_keywords: list[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GoldenCase:
        return cls(
            query=d["query"],
            expected_tools=list(d.get("expected_tools", [])),
            expected_data_fields=list(d.get("expected_data_fields", [])),
            expected_answer_numbers=[
                float(x) for x in d.get("expected_answer_numbers", [])
            ],
            forbidden_numbers=[float(x) for x in d.get("forbidden_numbers", [])],
            category=d.get("category", "standard"),
            expected_rag_keywords=list(d.get("expected_rag_keywords", [])),
            description=d.get("description", ""),
        )


@dataclass
class EvalResult:
    """Aggregate metrics over the golden set."""

    task_success_rate: float
    tool_accuracy: float
    retrieval_recall_at_k: float
    answer_groundedness: float
    avg_confidence: float
    avg_duration_ms: float
    per_case: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        return (
            "EvalResult:\n"
            f"  task_success_rate    = {self.task_success_rate:.1%}\n"
            f"  tool_accuracy        = {self.tool_accuracy:.1%}\n"
            f"  retrieval_recall@k   = {self.retrieval_recall_at_k:.1%}\n"
            f"  answer_groundedness  = {self.answer_groundedness:.1%}\n"
            f"  avg_confidence       = {self.avg_confidence:.3f}\n"
            f"  avg_duration_ms      = {self.avg_duration_ms:.0f}\n"
            f"  cases                = {len(self.per_case)}"
        )


# ── EvalRunner ┇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class EvalRunner:
    """Runs the orchestrator against a golden set and scores each case."""

    def __init__(self, orchestrator: Orchestrator, golden_set_path: str | Path):
        self.orchestrator = orchestrator
        self.golden_set_path = Path(golden_set_path)
        self.cases: list[GoldenCase] = self._load_cases()

    def _load_cases(self) -> list[GoldenCase]:
        raw = json.loads(self.golden_set_path.read_text(encoding="utf-8"))
        cases = [GoldenCase.from_dict(c) for c in raw.get("cases", [])]
        logger.info(f"Loaded {len(cases)} golden cases from {self.golden_set_path}")
        return cases

    async def run_all(self) -> EvalResult:
        if not self.cases:
            return EvalResult(
                task_success_rate=0.0,
                tool_accuracy=0.0,
                retrieval_recall_at_k=0.0,
                answer_groundedness=0.0,
                avg_confidence=0.0,
                avg_duration_ms=0.0,
                per_case=[],
            )

        per_case: list[dict] = []
        for i, case in enumerate(self.cases, 1):
            logger.info(f"[{i}/{len(self.cases)}] {case.category}: {case.query[:60]}")
            try:
                result = await self.run_single(case)
            except Exception as e:
                logger.error(f"Case failed with exception: {e}")
                result = {
                    "query": case.query,
                    "category": case.category,
                    "error": str(e),
                    "task_success": 0.0,
                    "tool_accuracy": 0.0,
                    "retrieval_recall": 0.0,
                    "groundedness": 0.0,
                    "confidence": 0.0,
                    "duration_ms": 0.0,
                }
            per_case.append(result)

        n = len(per_case)
        return EvalResult(
            task_success_rate=sum(c["task_success"] for c in per_case) / n,
            tool_accuracy=sum(c["tool_accuracy"] for c in per_case) / n,
            retrieval_recall_at_k=sum(c["retrieval_recall"] for c in per_case) / n,
            answer_groundedness=sum(c["groundedness"] for c in per_case) / n,
            avg_confidence=sum(c["confidence"] for c in per_case) / n,
            avg_duration_ms=sum(c["duration_ms"] for c in per_case) / n,
            per_case=per_case,
        )

    async def run_single(self, case: GoldenCase) -> dict:
        """Run one golden case through the orchestrator and score it."""
        run: RunResult = await self.orchestrator.run(case.query)

        # 1. Task success rate (per-case)
        total = run.subtask_count or 1
        task_success = run.successful_tasks / total

        # 2. Tool accuracy — Jaccard overlap between expected and actual tools
        tool_accuracy = self._check_tool_accuracy(run.exec_result, case.expected_tools)

        # 3. Retrieval recall — only scored for cases with rag expectations
        retrieval_recall = self._check_retrieval_recall(
            run.exec_result, case.expected_rag_keywords
        )

        # 4. Answer groundedness — expected numbers present, forbidden absent
        answer_text = self._compose_answer_text(run)
        groundedness = self._check_groundedness(
            answer_text,
            case.expected_answer_numbers,
            case.forbidden_numbers,
        )

        confidence = run.reasoning_result.confidence if run.reasoning_result else 0.0

        return {
            "query": case.query,
            "category": case.category,
            "task_success": round(task_success, 3),
            "tool_accuracy": round(tool_accuracy, 3),
            "retrieval_recall": round(retrieval_recall, 3),
            "groundedness": round(groundedness, 3),
            "confidence": round(confidence, 3),
            "duration_ms": round(run.total_duration_ms, 1),
            "trace_id": run.trace_id,
            "tools_used": self._extract_tools(run.exec_result),
        }

    # ── Metric implementations ┇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _check_tool_accuracy(
        self,
        exec_result: Any | None,
        expected_tools: list[str],
    ) -> float:
        """Jaccard overlap between expected tools and tools actually used."""
        actual = set(self._extract_tools(exec_result))
        expected = set(expected_tools)
        if not expected and not actual:
            return 1.0
        if not expected or not actual:
            return 0.0
        intersection = expected & actual
        union = expected | actual
        return len(intersection) / len(union) if union else 1.0

    def _check_retrieval_recall(
        self,
        exec_result: Any | None,
        expected_keywords: list[str],
    ) -> float:
        """For RAG cases: did the rag_retrieve tool return data containing
        the expected keywords?

        Returns 1.0 when the case has no RAG expectations (not applicable),
        so RAG-less cases do not drag the aggregate down.
        """
        if not expected_keywords:
            return 1.0
        if exec_result is None:
            return 0.0

        rag_data = ""
        for tr in getattr(exec_result, "task_results", []):
            if tr.tool_name == "rag_retrieve" and tr.success and tr.data:
                rag_data += str(tr.data) + " "

        if not rag_data:
            return 0.0

        rag_data_lower = rag_data.lower()
        hits = sum(1 for kw in expected_keywords if kw.lower() in rag_data_lower)
        return hits / len(expected_keywords)

    def _check_groundedness(
        self,
        answer: str,
        expected: list[float],
        forbidden: list[float],
    ) -> float:
        """Score how well the answer is grounded in expected numbers.

        * +1 for each expected number present (normalized to /len(expected))
        * -0.5 penalty for each forbidden number present (hallucination trap)
        * clamped to [0, 1]
        """
        if not expected and not forbidden:
            return 1.0

        text = answer or ""
        hit = 0.0
        if expected:
            for num in expected:
                if self._number_in_text(num, text):
                    hit += 1.0
            hit /= len(expected)

        penalty = 0.0
        if forbidden:
            for num in forbidden:
                if self._number_in_text(num, text):
                    penalty += 0.5
            penalty = min(penalty, 1.0)

        return max(0.0, hit - penalty)

    # ── Helpers ┇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _extract_tools(exec_result: Any | None) -> list[str]:
        if exec_result is None:
            return []
        return [tr.tool_name for tr in getattr(exec_result, "task_results", [])]

    @staticmethod
    def _compose_answer_text(run: RunResult) -> str:
        """Concatenate every textual output the user-facing answer derives from."""
        parts: list[str] = []
        if run.answer:
            parts.append(str(run.answer))
        if run.report is not None:
            parts.append(run.report.summary)
            kf = getattr(run.report.analysis, "key_findings", [])
            parts.extend(str(f) for f in kf)
        if run.reasoning_result is not None:
            parts.append(run.reasoning_result.reasoning)
            parts.extend(run.reasoning_result.key_insights)
        return "\n".join(parts)

    @staticmethod
    def _number_in_text(number: float, text: str) -> bool:
        """True if ``number`` appears in ``text`` as a standalone numeric token.

        Avoids substring false-positives (e.g. ``12`` matching ``123``) by
        requiring word boundaries around the number. Handles integers and
        decimals, and ignores thousands separators.
        """
        if not text:
            return False
        # Normalize: drop commas used as thousands separators
        cleaned = text.replace(",", "")
        # Build a regex that matches the number with optional sign and decimals.
        # \b ensures we don't match inside a longer digit run.
        pattern = r"(?<![0-9.])" + re.escape(str(number)) + r"(?![0-9])"
        return re.search(pattern, cleaned) is not None


# ── CLI ┇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _default_golden_path() -> Path:
    """Resolve the golden dataset path relative to the project root."""
    here = Path(__file__).resolve().parent
    return here.parent.parent / "data" / "golden_dataset.json"


async def _run_async(args: argparse.Namespace) -> int:
    golden_path = Path(args.golden_set) if args.golden_set else _default_golden_path()

    if args.dry_run:
        runner = EvalRunner.__new__(EvalRunner)
        runner.golden_set_path = golden_path
        runner.cases = runner._load_cases()
        cats: dict[str, int] = {}
        for c in runner.cases:
            cats[c.category] = cats.get(c.category, 0) + 1
        print(f"[dry-run] golden set: {golden_path}")
        print(f"[dry-run] cases: {len(runner.cases)}")
        print(f"[dry-run] categories: {cats}")
        return 0

    if not golden_path.exists():
        print(f"Golden set not found: {golden_path}", file=sys.stderr)
        return 2

    from app.core.orchestrator import Orchestrator

    orchestrator = Orchestrator(use_router=bool(args.use_router))
    runner = EvalRunner(orchestrator, golden_path)
    result = await runner.run_all()
    print(result.summary())
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nFull results written to {args.json_out}")
    return check_thresholds(result, args)


def check_thresholds(result: EvalResult, args: argparse.Namespace) -> int:
    """Compare aggregate metrics against --min-* thresholds.

    Returns 0 when every configured threshold is met, 1 otherwise. Thresholds
    left at None are not enforced.
    """
    checks = [
        ("task_success_rate", result.task_success_rate, args.min_task_success),
        ("tool_accuracy", result.tool_accuracy, args.min_tool_accuracy),
        (
            "retrieval_recall@k",
            result.retrieval_recall_at_k,
            args.min_retrieval_recall,
        ),
        ("answer_groundedness", result.answer_groundedness, args.min_groundedness),
    ]
    failed = False
    for name, value, minimum in checks:
        if minimum is None:
            continue
        if value < minimum:
            print(f"[FAIL] {name} = {value:.3f} < required {minimum:.3f}")
            failed = True
        else:
            print(f"[PASS] {name} = {value:.3f} >= {minimum:.3f}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="End-to-end evaluation harness for the Smart Finance Agent"
    )
    parser.add_argument(
        "--golden-set",
        default=None,
        help="Path to golden_dataset.json (default: backend/data/golden_dataset.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and validate the golden set without running the orchestrator",
    )
    parser.add_argument(
        "--use-router",
        action="store_true",
        default=False,
        help="Enable LiteLLMRouter for multi-model routing (default: off)",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Write full per-case results to this JSON file",
    )
    for flag, metric in (
        ("--min-task-success", "task_success_rate"),
        ("--min-tool-accuracy", "tool_accuracy"),
        ("--min-retrieval-recall", "retrieval_recall@k"),
        ("--min-groundedness", "answer_groundedness"),
    ):
        parser.add_argument(
            flag,
            type=float,
            default=None,
            help=f"Fail (exit 1) when {metric} is below this value (0..1)",
        )
    args = parser.parse_args(argv)
    return asyncio.run(_run_async(args))


if __name__ == "__main__":
    sys.exit(main())
