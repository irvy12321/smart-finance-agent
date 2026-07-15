from app.rag.retriever import Retriever
from app.tools.base_tool import BaseTool, ToolResult
from app.utils.logger import get_logger
from app.utils.redaction import redact_sensitive_text

logger = get_logger("rag_tool")

_global_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = Retriever()
    return _global_retriever


class RAGTool(BaseTool):
    name = "rag_retrieve"
    description = (
        "Retrieves relevant text chunks using the configured lexical or semantic index"
    )

    def __init__(self, retriever: Retriever | None = None):
        self.retriever = retriever or get_retriever()

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)
        metadata_filter = kwargs.get("metadata_filter") or kwargs.get("filters")
        min_score = float(kwargs.get("min_score") or 0.0)

        if not query:
            return ToolResult(
                success=False, error="No query provided", tool_name=self.name
            )

        try:
            embedder = getattr(self.retriever, "embedder", None)
            status_getter = getattr(embedder, "get_runtime_status", None)
            retrieval_status = (
                status_getter()
                if status_getter is not None
                else {"semantic_enabled": False, "status": "unavailable"}
            )
            results = self.retriever.retrieve(
                query,
                top_k=top_k,
                metadata_filter=metadata_filter,
                min_score=min_score,
            )
            if not results:
                message = (
                    "No documents in knowledge base yet"
                    if self.retriever.doc_count == 0
                    else "No matching documents found in knowledge base"
                )
                return ToolResult(
                    success=True,
                    data={
                        "results": [],
                        "message": message,
                        "retrieval_status": retrieval_status,
                    },
                    tool_name=self.name,
                )
            return ToolResult(
                success=True,
                data={"results": results, "retrieval_status": retrieval_status},
                tool_name=self.name,
            )
        except Exception as e:
            safe_error = redact_sensitive_text(e)
            logger.error(f"RAG retrieve failed: {safe_error}")
            return ToolResult(success=False, error=safe_error, tool_name=self.name)

    def add_document(self, text: str, metadata: dict | None = None):
        self.retriever.add_document(text, metadata)

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """RAG 降级: 返回空结果"""
        query = kwargs.get("query", "unknown")
        logger.warning(f"RAG fallback for: {query}")
        return ToolResult(
            success=True,
            data={
                "results": [],
                "message": f"[Fallback] No local knowledge available for: {query}",
            },
            tool_name=self.name,
        )
