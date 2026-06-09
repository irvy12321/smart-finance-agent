from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger("loader")


async def load_text_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(p, encoding="utf-8") as f:
        return f.read()


async def load_from_string(content: str) -> str:
    return content
