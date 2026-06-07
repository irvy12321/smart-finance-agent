from app.infrastructure.config import get_rag_config


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
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
                if sub_chunk:
                    current = sub_chunk
                else:
                    current = ""
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
