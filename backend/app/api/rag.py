"""
RAG API 路由 - 文档上传、向量化、检索管理
"""

import contextlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from pydantic import BaseModel, Field

from app.auth.dependencies import require_role
from app.auth.models import UserResponse
from app.auth.roles import Role
from app.rag.chunker import chunk_text
from app.rag.embed import create_embedder
from app.rag.file_parser import FileParserError, get_supported_extensions, parse_file
from app.rag.vector_store import VectorStore
from app.utils.logger import get_logger

logger = get_logger("api.rag")

router = APIRouter(prefix="/rag", tags=["rag"])

# 数据目录
RAG_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "rag"
DOCUMENTS_FILE = RAG_DATA_DIR / "documents.json"
VECTOR_STORE_DIR = RAG_DATA_DIR / "vector_store"

# 全局实例
_vector_store: VectorStore | None = None
_embedder = None


def _ensure_dirs():
    """确保目录存在"""
    RAG_DATA_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


def _get_embedder():
    """获取嵌入模型实例"""
    global _embedder
    if _embedder is None:
        _embedder = create_embedder()
    return _embedder


def _get_vector_store() -> VectorStore:
    """获取向量存储实例"""
    global _vector_store
    if _vector_store is None:
        embedder = _get_embedder()
        _vector_store = VectorStore(
            dim=embedder.dim, persist_dir=str(VECTOR_STORE_DIR), embedder=embedder
        )
        _vector_store.load()
    return _vector_store


def _load_documents() -> list[dict[str, Any]]:
    """加载文档列表"""
    _ensure_dirs()
    if DOCUMENTS_FILE.exists():
        try:
            with open(DOCUMENTS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load documents: {e}")
    return []


def _save_documents(documents: list[dict[str, Any]]):
    """保存文档列表"""
    _ensure_dirs()
    try:
        with open(DOCUMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save documents: {e}")


# ============================================================
# Pydantic Models
# ============================================================


class DocumentInfo(BaseModel):
    """文档信息"""

    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str  # processing, completed, failed
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = {}


class DocumentListResponse(BaseModel):
    """文档列表响应"""

    documents: list[DocumentInfo]
    total: int


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""

    document_id: str
    filename: str
    status: str
    message: str


class DocumentDeleteResponse(BaseModel):
    """文档删除响应"""

    document_id: str
    message: str


class RAGSearchRequest(BaseModel):
    """RAG 搜索请求"""

    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class RAGSearchResult(BaseModel):
    """RAG 搜索结果"""

    text: str
    score: float
    metadata: dict[str, Any] = {}


class RAGSearchResponse(BaseModel):
    """RAG 搜索响应"""

    query: str
    results: list[RAGSearchResult]
    total: int


class RAGStatsResponse(BaseModel):
    """RAG 统计响应"""

    total_documents: int
    total_chunks: int
    vector_store_size: int
    embedding_mode: str


# ============================================================
# API Routes
# ============================================================


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """获取所有文档列表"""
    documents = _load_documents()
    return DocumentListResponse(
        documents=[DocumentInfo(**doc) for doc in documents], total=len(documents)
    )


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: str | None = Form(default=None),
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """上传文档并触发向量化"""
    _ensure_dirs()

    # 验证文件类型
    allowed_types = get_supported_extensions()
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_types)}",
        )

    # 读取文件内容
    content = await file.read()

    # 解析文件内容
    try:
        text_content = parse_file(content, file.filename)
        logger.info(
            f"File parsed successfully: {file.filename} ({len(text_content)} chars)"
        )
    except FileParserError as e:
        logger.error(f"File parsing failed: {file.filename} - {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e

    # 生成文档 ID
    doc_id = str(uuid.uuid4())[:8]

    # 保存原始文件
    upload_dir = RAG_DATA_DIR / "uploads"
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / f"{doc_id}{file_ext}"

    # 根据文件类型选择写入模式
    if file_ext in {".txt", ".md", ".csv", ".json"}:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
    else:
        # 二进制文件 (PDF, DOCX) 保存原始内容
        with open(file_path, "wb") as f:
            f.write(content)

    # 解析元数据
    doc_metadata = {}
    if metadata:
        with contextlib.suppress(json.JSONDecodeError):
            doc_metadata = json.loads(metadata)

    # 创建文档记录
    now = datetime.now().isoformat()
    document = {
        "id": doc_id,
        "filename": file.filename,
        "file_type": file_ext,
        "file_size": len(content),
        "chunk_count": 0,
        "status": "processing",
        "created_at": now,
        "updated_at": now,
        "metadata": doc_metadata,
        "file_path": str(file_path),
    }

    documents = _load_documents()
    documents.append(document)
    _save_documents(documents)

    # 后台处理向量化
    background_tasks.add_task(_process_document, doc_id, text_content, doc_metadata)

    logger.info(f"Document uploaded: {file.filename} -> {doc_id}")

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename,
        status="processing",
        message="Document uploaded. Vectorization in progress.",
    )


async def _process_document(doc_id: str, content: str, metadata: dict[str, Any]):
    """后台处理文档向量化"""
    try:
        # 分块
        chunks = chunk_text(content)
        if not chunks:
            _update_document_status(doc_id, "failed", 0)
            return

        # 向量化
        embedder = _get_embedder()
        embeddings = embedder.embed_batch(chunks)

        # 存储到向量数据库
        vector_store = _get_vector_store()
        chunk_metadata = [
            {**metadata, "doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))
        ]
        vector_store.add(embeddings, chunks, chunk_metadata)
        vector_store.save()

        # 更新文档状态
        _update_document_status(doc_id, "completed", len(chunks))

        logger.info(f"Document {doc_id} processed: {len(chunks)} chunks")

    except Exception as e:
        logger.error(f"Failed to process document {doc_id}: {e}")
        _update_document_status(doc_id, "failed", 0)


def _update_document_status(doc_id: str, status: str, chunk_count: int):
    """更新文档状态"""
    documents = _load_documents()
    for doc in documents:
        if doc["id"] == doc_id:
            doc["status"] = status
            doc["chunk_count"] = chunk_count
            doc["updated_at"] = datetime.now().isoformat()
            break
    _save_documents(documents)


@router.get("/documents/{doc_id}", response_model=DocumentInfo)
async def get_document(
    doc_id: str,
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """获取单个文档信息"""
    documents = _load_documents()
    for doc in documents:
        if doc["id"] == doc_id:
            return DocumentInfo(**doc)
    raise HTTPException(status_code=404, detail="Document not found")


@router.delete("/documents/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    doc_id: str, current_user: UserResponse = Depends(require_role(Role.ADMIN))
):
    """删除文档及其向量数据"""
    documents = _load_documents()
    doc_to_delete = None

    for doc in documents:
        if doc["id"] == doc_id:
            doc_to_delete = doc
            break

    if not doc_to_delete:
        raise HTTPException(status_code=404, detail="Document not found")

    # 从向量存储中删除相关块
    try:
        vector_store = _get_vector_store()
        # 过滤掉属于该文档的向量
        new_texts = []
        new_metadata = []

        for i, meta in enumerate(vector_store.metadata):
            if meta.get("doc_id") != doc_id:
                new_texts.append(vector_store.texts[i])
                new_metadata.append(meta)

        # 重建索引（如果文档数量较多，可能需要优化）
        if len(new_texts) < vector_store.size:
            embedder = _get_embedder()
            if new_texts:
                new_embeddings = embedder.embed_batch(new_texts)
                vector_store.clear()
                vector_store.add(new_embeddings, new_texts, new_metadata)
            else:
                vector_store.clear()
            vector_store.save()
    except Exception as e:
        logger.error(f"Failed to delete vectors for document {doc_id}: {e}")

    # 删除原始文件
    if "file_path" in doc_to_delete:
        try:
            file_path = Path(doc_to_delete["file_path"])
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")

    # 从文档列表中删除
    documents = [d for d in documents if d["id"] != doc_id]
    _save_documents(documents)

    logger.info(f"Document deleted: {doc_id}")

    return DocumentDeleteResponse(
        document_id=doc_id,
        message="Document and associated vectors deleted successfully",
    )


@router.post("/search", response_model=RAGSearchResponse)
async def search_documents(
    request: RAGSearchRequest,
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """搜索相关文档片段"""
    try:
        embedder = _get_embedder()
        vector_store = _get_vector_store()

        # 向量化查询
        query_embedding = embedder.embed_text(request.query)

        # 搜索
        results = vector_store.search(query_embedding, top_k=request.top_k)

        return RAGSearchResponse(
            query=request.query,
            results=[
                RAGSearchResult(
                    text=r["text"], score=r["score"], metadata=r["metadata"]
                )
                for r in results
            ],
            total=len(results),
        )
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}") from e


@router.get("/stats", response_model=RAGStatsResponse)
async def get_rag_stats(
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """获取 RAG 系统统计信息"""
    documents = _load_documents()
    vector_store = _get_vector_store()

    embed_config = get_embedding_config()

    return RAGStatsResponse(
        total_documents=len(documents),
        total_chunks=sum(d.get("chunk_count", 0) for d in documents),
        vector_store_size=vector_store.size,
        embedding_mode=embed_config.mode,
    )


@router.post("/reindex")
async def reindex_documents(
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """重新索引所有文档"""
    documents = _load_documents()
    if not documents:
        return {"message": "No documents to reindex"}

    # 清空向量存储
    vector_store = _get_vector_store()
    vector_store.clear()
    vector_store.save()

    # 重置所有文档状态
    for doc in documents:
        doc["status"] = "processing"
        doc["chunk_count"] = 0
    _save_documents(documents)

    # 后台重新处理所有文档
    for doc in documents:
        if "file_path" in doc:
            try:
                with open(doc["file_path"], encoding="utf-8") as f:
                    content = f.read()
                background_tasks.add_task(
                    _process_document, doc["id"], content, doc.get("metadata", {})
                )
            except Exception as e:
                logger.error(f"Failed to read document {doc['id']}: {e}")

    return {"message": f"Reindexing {len(documents)} documents in background"}


def get_embedding_config():
    """获取嵌入配置"""
    from app.infrastructure.config import get_embedding_config as _get_config

    return _get_config()
