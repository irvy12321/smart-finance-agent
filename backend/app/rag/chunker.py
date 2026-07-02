from app.infrastructure.config import get_rag_config
from app.utils.logger import get_logger

logger = get_logger("chunker")


def chunk_text(
    text: str, chunk_size: int | None = None, overlap: int | None = None
) -> list[str]:
    config = get_rag_config()
    chunk_size = chunk_size or config.chunk_size
    overlap = overlap or config.chunk_overlap

    if not text or not text.strip():
        return []

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 1 <= chunk_size:
            current = f"{current}\n{para}" if current else para
        else:
            if current:
                chunks.append(current.strip())
            if len(para) > chunk_size:
                words = para.split()
                sub_chunk = ""
                for word in words:
                    if len(sub_chunk) + len(word) + 1 <= chunk_size:
                        sub_chunk = f"{sub_chunk} {word}" if sub_chunk else word
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk.strip())
                        sub_chunk = word
                current = sub_chunk or ""
            else:
                current = para

    if current.strip():
        chunks.append(current.strip())

    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(f"{prev_tail} {chunks[i]}")
        chunks = overlapped

    return chunks


def semantic_chunk(
    text: str,
    embedder=None,
    threshold: float = 0.5,
    min_chunk_size: int = 100,
    max_chunk_size: int = 1000,
) -> list[str]:
    """基于语义相似度的分块.

    按 paragraph 切分后，计算相邻段落的 embedding 相似度，在相似度低于
    threshold 的位置断开，形成语义连贯的 chunk.

    Args:
        text: 待分块文本.
        embedder: 实现 embed_text(str) -> np.ndarray 的 embedder. 若为 None
            则降级为按 paragraph 简单合并（不计算相似度）.
        threshold: 相似度低于此值则断开 (0~1, 默认 0.5).
        min_chunk_size: chunk 最小字符数，避免过碎.
        max_chunk_size: chunk 最大字符数，超过则强制断开.

    Returns:
        chunk 列表. 空/纯空白输入返回 [].
    """
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    # 无 embedder: 降级为按 min/max size 合并 paragraph
    if embedder is None:
        logger.info("semantic_chunk: no embedder, falling back to size-based merge")
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) + 1 <= max_chunk_size and (
                current or len(chunks) == 0
            ):
                current = f"{current}\n{para}" if current else para
            else:
                if current:
                    chunks.append(current)
                current = para
        if current:
            chunks.append(current)
        return chunks

    # 有 embedder: 计算相邻段落相似度，在语义跳变处断开
    import numpy as np

    try:
        vecs = np.asarray(embedder.embed_batch(paragraphs))
    except Exception as e:
        logger.warning(
            f"semantic_chunk embed failed ({type(e).__name__}: {e}); "
            f"size-based fallback"
        )
        return semantic_chunk(
            text,
            embedder=None,
            threshold=threshold,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
        )

    # 归一化后计算相邻 cosine 相似度
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = vecs / norms
    # sim[i] = cosine(paragraphs[i], paragraphs[i+1])
    sim = (unit[:-1] * unit[1:]).sum(axis=1)

    chunks: list[str] = []
    current = paragraphs[0]
    for i in range(1, len(paragraphs)):
        should_break = False
        # 语义跳变
        if i - 1 < len(sim) and sim[i - 1] < threshold:
            should_break = True
        # 超过 max size
        if len(current) + len(paragraphs[i]) + 1 > max_chunk_size:
            should_break = True

        if should_break and len(current) >= min_chunk_size:
            chunks.append(current)
            current = paragraphs[i]
        else:
            current = f"{current}\n{paragraphs[i]}" if current else paragraphs[i]

    if current:
        chunks.append(current)
    return chunks
