import re
from typing import Any

from app.infrastructure.config import get_rag_config
from app.utils.logger import get_logger

logger = get_logger("chunker")

_SENTENCE_ENDINGS = frozenset("。！？；!?;")


def _validate_sizes(chunk_size: int, overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")


def _preferred_split(text: str, start: int, hard_end: int, overlap: int) -> int:
    """Choose a natural boundary without creating a very small chunk."""
    minimum = start + max(overlap + 1, (hard_end - start) // 2)

    paragraph_end = text.rfind("\n\n", minimum, hard_end)
    if paragraph_end >= 0:
        return paragraph_end + 2

    for index in range(hard_end - 1, minimum - 1, -1):
        char = text[index]
        if char in _SENTENCE_ENDINGS:
            return index + 1
        if char == "." and (index + 1 == len(text) or text[index + 1].isspace()):
            return index + 1

    for index in range(hard_end - 1, minimum - 1, -1):
        if text[index].isspace():
            return index + 1

    return hard_end


def chunk_text(
    text: str, chunk_size: int | None = None, overlap: int | None = None
) -> list[str]:
    """Split text into bounded, overlapping chunks.

    Paragraph and Chinese/English sentence boundaries are preferred. If no
    suitable boundary exists, the input is hard-split by character length, so
    unspaced Chinese text can never produce an oversized chunk.
    """
    config = get_rag_config()
    resolved_size = config.chunk_size if chunk_size is None else chunk_size
    resolved_overlap = config.chunk_overlap if overlap is None else overlap
    _validate_sizes(resolved_size, resolved_overlap)

    normalized = text.strip() if text else ""
    if not normalized:
        return []
    if len(normalized) <= resolved_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        hard_end = min(start + resolved_size, len(normalized))
        end = (
            hard_end
            if hard_end == len(normalized)
            else _preferred_split(normalized, start, hard_end, resolved_overlap)
        )
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - resolved_overlap

    return chunks


def _semantic_regions(
    paragraphs: list[str], embedder: Any, threshold: float, min_chunk_size: int
) -> list[str]:
    import numpy as np

    vecs = np.asarray(embedder.embed_batch(paragraphs))
    if len(vecs) != len(paragraphs):
        raise ValueError("embedder returned an unexpected number of vectors")

    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = vecs / norms
    similarities = (unit[:-1] * unit[1:]).sum(axis=1)

    regions: list[str] = []
    current = paragraphs[0]
    for index in range(1, len(paragraphs)):
        if similarities[index - 1] < threshold and len(current) >= min_chunk_size:
            regions.append(current)
            current = paragraphs[index]
        else:
            current = f"{current}\n\n{paragraphs[index]}"
    regions.append(current)
    return regions


def semantic_chunk(
    text: str,
    embedder: Any = None,
    threshold: float = 0.5,
    min_chunk_size: int = 100,
    max_chunk_size: int = 1000,
    overlap: int = 50,
) -> list[str]:
    """Split at semantic paragraph changes, then enforce the size limit.

    This low-level function accepts an embedder for direct use and testing. The
    public ``chunk_document`` entry point only calls it for embedders that
    explicitly advertise real semantic similarity support.
    """
    if not text or not text.strip():
        return []
    _validate_sizes(max_chunk_size, overlap)

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return []

    if embedder is None:
        logger.info("semantic_chunk: no semantic embedder; using fixed chunking")
        return chunk_text(text, chunk_size=max_chunk_size, overlap=overlap)

    try:
        regions = _semantic_regions(paragraphs, embedder, threshold, min_chunk_size)
    except Exception as exc:
        logger.warning(
            "semantic_chunk embedding failed (%s: %s); using fixed chunking",
            type(exc).__name__,
            exc,
        )
        return chunk_text(text, chunk_size=max_chunk_size, overlap=overlap)

    chunks: list[str] = []
    for region in regions:
        chunks.extend(chunk_text(region, chunk_size=max_chunk_size, overlap=overlap))
    return chunks


def chunk_document(text: str, embedder: Any = None) -> list[str]:
    """Use the configured document chunking strategy for every ingest path."""
    config = get_rag_config()
    if not getattr(config, "semantic_chunking_enabled", False):
        return chunk_text(
            text, chunk_size=config.chunk_size, overlap=config.chunk_overlap
        )

    if not getattr(embedder, "supports_semantic_similarity", False):
        logger.info(
            "Semantic chunking requested without a real semantic embedder; "
            "using fixed chunking"
        )
        return chunk_text(
            text, chunk_size=config.chunk_size, overlap=config.chunk_overlap
        )

    return semantic_chunk(
        text,
        embedder=embedder,
        threshold=getattr(config, "semantic_chunking_threshold", 0.5),
        min_chunk_size=getattr(config, "semantic_chunking_min_chunk_size", 100),
        max_chunk_size=config.chunk_size,
        overlap=config.chunk_overlap,
    )
