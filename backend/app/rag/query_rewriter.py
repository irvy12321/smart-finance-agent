"""Query rewrite module — LLM 多路改写 + HyDE.

设计:
* ``QueryRewriter``: 调 LLM 生成 N 个查询变体（multi-query），用于克服
  原始 query 与文档间的词汇/句式鸿沟.
* ``multi_query_retrieve()``: 多路检索 + 合并去重 + (可选) reranker 精排.
* ``hyde()``: HyDE — 让 LLM 先生成一个"假设答案文档"，再用该文档的
  embedding 去检索，缓解 query/doc 表达差异.

侵入度低: 只暴露 ``multi_query_retrieve(query, retriever, ...)`` 一个函数，
调用方（retriever.retrieve_with_rewrite）按需启用；LLM 不可用时自动降级到
原始单路检索，绝不抛错.

遵循项目规则:
* LLM 只做语言生成（改写 query / 生成假设文档），不产生任何金融数值.
* 任何 LLM 失败都降级，不阻塞主流程.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("query_rewriter")


# ─── prompt ─────────────────────────────────────────────────────────────

_MULTI_QUERY_SYSTEM = """You are a query rewriting assistant for a financial RAG system.
Given a user query, generate 3 alternative phrasings that a user might use to
search for the SAME information. Use different vocabulary and sentence structure
but preserve the intent and any ticker symbols / numbers verbatim.

Output STRICT JSON only, no prose:
{"variants": ["variant 1", "variant 2", "variant 3"]}

Rules:
- Never invent numbers not present in the original query.
- Keep ticker symbols (e.g. AAPL, TSLA) unchanged.
- Each variant must be a self-contained search query.
- Output JSON only."""

_HYDE_SYSTEM = """You are a hypothetical document generator for a financial RAG system.
Given a user query, write a SHORT (3-5 sentences) hypothetical document that
WOULD answer this query. This document will be used only as a search probe — it
is NOT shown to the user and is NOT a real answer.

Rules:
- Do NOT invent specific numbers, dates, or facts. Use placeholders like
  <metric> or <date> if needed.
- Match the domain language of financial research.
- Output the document text only, no JSON, no preamble."""


def _strip_json_fence(text: str) -> str:
    """剥离 ```json ... ``` 围栏."""
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            return m.group(1)
    return text


def _extract_json_object(text: str) -> dict | None:
    """多层容错 JSON 提取: fence 剥离 → json.loads → 子串提取."""
    candidate = _strip_json_fence(text.strip())
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # 子串提取
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


# ─── QueryRewriter ──────────────────────────────────────────────────────


class QueryRewriter:
    """LLM 多路改写器.

    接受任意有 ``async complete(prompt, system=...) -> str`` 接口的客户端
    （LLMClient 或 LiteLLMRouter.complete 都满足后者需多一个 agent_name 参数，
    调用方自行包装）.
    """

    def __init__(self, llm_client: Any, num_variants: int = 3):
        self.llm = llm_client
        self.num_variants = max(1, num_variants)

    async def rewrite(self, query: str) -> list[str]:
        """返回包含原始 query + N 个变体的去重列表."""
        variants = [query]
        try:
            prompt = (
                f"Original query: {query}\n\n"
                f"Generate {self.num_variants} alternative search queries."
            )
            resp = await self.llm.complete(prompt, system=_MULTI_QUERY_SYSTEM)
            data = _extract_json_object(resp)
            if data and isinstance(data.get("variants"), list):
                for v in data["variants"][: self.num_variants]:
                    if isinstance(v, str) and v.strip():
                        v = v.strip()
                        if v not in variants:
                            variants.append(v)
            else:
                logger.warning(
                    "Query rewrite returned no parseable variants; using original only"
                )
        except Exception as e:
            logger.warning(
                f"Query rewrite failed ({type(e).__name__}: {e}); "
                f"using original query only"
            )
        return variants

    async def hyde(self, query: str) -> str | None:
        """生成假设文档. 失败返回 None（调用方降级到原 query）."""
        try:
            prompt = f"User query: {query}\n\nWrite the hypothetical document."
            resp = await self.llm.complete(prompt, system=_HYDE_SYSTEM)
            text = resp.strip()
            if text:
                return text
        except Exception as e:
            logger.warning(f"HyDE failed ({type(e).__name__}: {e}); skipping")
        return None


# ─── multi_query_retrieve ───────────────────────────────────────────────


def _dedupe_by_text(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 text 字段去重，保留首次出现（分数通常更高）."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in results:
        key = (r.get("text") or "").strip()
        if key and key not in seen:
            seen.add(key)
            out.append(r)
    return out


async def multi_query_retrieve(
    query: str,
    retriever: Any,
    rewriter: QueryRewriter | None = None,
    top_k: int = 5,
    use_hyde: bool = False,
    reranker: Any | None = None,
) -> list[dict[str, Any]]:
    """多路检索 + 合并去重 + (可选) reranker 精排.

    流程:
    1. 若 rewriter 提供: 生成 query 变体；否则只用原 query.
    2. (可选) HyDE: 生成假设文档，作为额外一路检索 probe.
    3. 对每路 query 调 retriever.retrieve()，合并所有结果.
    4. 按 text 去重.
    5. 若 reranker 可用: rerank 精排；否则按 score 排序截断 top_k.

    任何 LLM / reranker 失败都降级，最终至少返回原 query 的单路检索结果.
    """
    queries = [query]

    if rewriter is not None:
        try:
            variants = await rewriter.rewrite(query)
            # variants[0] 是原 query，其余是变体
            queries = variants
        except Exception as e:
            logger.warning(
                f"multi_query rewrite failed ({type(e).__name__}: {e}); "
                f"single-query fallback"
            )

    # HyDE: 额外一路
    hyde_doc = None
    if use_hyde and rewriter is not None:
        hyde_doc = await rewriter.hyde(query)

    # 多路检索
    all_results: list[dict[str, Any]] = []
    for q in queries:
        try:
            res = retriever.retrieve(q, top_k=top_k)
            all_results.extend(res)
        except Exception as e:
            logger.warning(
                f"retrieve sub-query failed ({type(e).__name__}: {e}); "
                f"skipping: {q[:50]}"
            )

    if hyde_doc:
        try:
            res = retriever.retrieve(hyde_doc, top_k=top_k)
            all_results.extend(res)
        except Exception as e:
            logger.warning(f"HyDE retrieve failed ({type(e).__name__}: {e}); skipping")

    if not all_results:
        logger.warning("multi_query_retrieve: all sub-retrievals empty")
        return []

    # 去重
    deduped = _dedupe_by_text(all_results)

    # reranker 精排 或 按 score 排序
    if reranker is not None and getattr(reranker, "is_available", False):
        try:
            return reranker.rerank(query, deduped, top_k=top_k)
        except Exception as e:
            logger.warning(
                f"rerank failed ({type(e).__name__}: {e}); score-sort fallback"
            )

    deduped.sort(key=lambda x: x.get("score", 0), reverse=True)
    return deduped[:top_k]
