from app.tools.base_tool import BaseTool, ToolResult
from app.rag.retriever import Retriever
from app.utils.logger import get_logger

logger = get_logger("rag_tool")

_global_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = Retriever()
    return _global_retriever


class RAGTool(BaseTool):
    name = "rag_retrieve"
    description = "Retrieves relevant text chunks from the knowledge base using semantic search"

    def __init__(self, retriever: Retriever | None = None):
        self.retriever = retriever or get_retriever()

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)

        if not query:
            return ToolResult(success=False, error="No query provided", tool_name=self.name)

        try:
            results = self.retriever.retrieve(query, top_k=top_k)
            if not results:
                return ToolResult(
                    success=True,
                    data={"results": [], "message": "No documents in knowledge base yet"},
                    tool_name=self.name,
                )
            return ToolResult(success=True, data={"results": results}, tool_name=self.name)
        except Exception as e:
            logger.error(f"RAG retrieve failed: {e}")
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def add_document(self, text: str, metadata: dict | None = None):
        self.retriever.add_document(text, metadata)

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """RAG 降级: 返回空结果"""
        query = kwargs.get("query", "unknown")
        logger.warning(f"RAG fallback for: {query}")
        return ToolResult(
            success=True,
            data={"results": [], "message": f"[Fallback] No local knowledge available for: {query}"},
            tool_name=self.name,
        )
