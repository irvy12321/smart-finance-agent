"""
Chat API routes - 提供聊天接口
支持两种模式:
1. 直接 LLM 对话（简单问答）
2. Orchestrator 全流水线（金融研究查询：股价、新闻、分析等）
"""
import re
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from app.utils.logger import get_logger
from app import storage

logger = get_logger("api.chat")

router = APIRouter(prefix="/chat", tags=["chat"])

# 金融关键词，匹配时走 orchestrator 全流水线
FINANCIAL_KEYWORDS = re.compile(
    r"(?i)(stock|price|share|market|earnings|revenue|profit|financial|report|"
    r"analysis|trend|invest|trade|portfolio|bond|etf|index|nasdaq|s&p|dow|"
    r"股价|股票|市值|财报|营收|利润|分析|投资|交易|基金|行情|涨跌|"
    r"AAPL|TSLA|GOOGL|MSFT|AMZN|NVDA|META|BABA|JD|BIDU)",
    re.IGNORECASE,
)


# ============================================================
# Pydantic Models
# ============================================================

class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ChatRequest(BaseModel):
    """Request model for chat"""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for context")
    stream: bool = Field(default=False, description="Enable streaming response")


class ChatResponse(BaseModel):
    """Response model for chat"""
    conversation_id: str
    message: ChatMessage
    response: str
    sources: List[Dict[str, Any]] = []
    confidence: float = 0.0
    timestamp: str


class ConversationCreateResponse(BaseModel):
    """Response model for conversation creation"""
    conversation_id: str
    created_at: str
    message: str


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history"""
    conversation_id: str
    messages: List[ChatMessage]
    total_messages: int


# ============================================================
# Conversation Storage (SQLite via app.storage)
# ============================================================


# ============================================================
# Helper: Get orchestrator from app.state
# ============================================================

def _get_orchestrator(request: Request):
    """Get orchestrator from app.state, returns None if not available"""
    return getattr(request.app.state, "orchestrator", None)


# ============================================================
# API Routes
# ============================================================

@router.post("/conversations", response_model=ConversationCreateResponse)
async def create_conversation():
    """Create a new conversation"""
    try:
        conversation_id = str(uuid.uuid4())[:8]
        storage.create_conversation(conversation_id)

        logger.info(f"Created conversation {conversation_id}")

        return ConversationCreateResponse(
            conversation_id=conversation_id,
            created_at=datetime.now().isoformat(),
            message="Conversation created successfully",
        )
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(conversation_id: str, request: ChatRequest, req: Request, background_tasks: BackgroundTasks):
    """Send a message in a conversation - 自动路由到 LLM 直答或 Orchestrator 全流水线"""
    try:
        # Get or create conversation
        conversation = storage.get_conversation(conversation_id)
        if conversation is None:
            storage.create_conversation(conversation_id)

        # Add user message
        user_message = ChatMessage(
            role="user",
            content=request.message,
        )
        storage.add_message(conversation_id, "user", request.message)

        # 判断是否为金融研究查询 → 走 orchestrator
        is_financial = bool(FINANCIAL_KEYWORDS.search(request.message))
        sources: List[Dict[str, Any]] = []
        confidence = 0.85

        # Get orchestrator from app.state
        orchestrator = _get_orchestrator(req)

        if is_financial and orchestrator is not None:
            response_text, sources, confidence = await generate_orchestrator_response(request.message, orchestrator)
        else:
            response_text = await generate_chat_response(request.message, conversation_id)

        # Add assistant message
        assistant_message = ChatMessage(
            role="assistant",
            content=response_text,
        )
        storage.add_message(conversation_id, "assistant", response_text)

        return ChatResponse(
            conversation_id=conversation_id,
            message=assistant_message,
            response=response_text,
            sources=sources,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str):
    """Get conversation history"""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = [ChatMessage(**msg) for msg in conversation["messages"]]

    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        messages=messages,
        total_messages=len(messages),
    )


@router.get("/conversations")
async def list_conversations():
    """List all conversations"""
    conversations = storage.list_conversations()
    return {"conversations": conversations, "total": len(conversations)}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    deleted = storage.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": f"Conversation {conversation_id} deleted"}


# ============================================================
# Helper Functions
# ============================================================

async def generate_orchestrator_response(message: str, orchestrator) -> tuple[str, list, float]:
    """
    使用 Orchestrator 全流水线处理金融研究查询
    带 90 秒超时保护，超时自动降级到直接 LLM
    返回: (response_text, sources, confidence)
    """
    import asyncio
    try:
        logger.info(f"[orchestrator] Processing financial query: {message[:80]}...")
        result = await asyncio.wait_for(orchestrator.run(message), timeout=90)

        sources = []
        if result.exec_result:
            for tr in result.exec_result.task_results:
                if tr.success and tr.tool_name != "llm_synthesize":
                    sources.append({
                        "tool": tr.tool_name,
                        "task_id": tr.task_id,
                        "duration_ms": round(tr.duration_ms, 0),
                    })

        # 优先使用 answer（executor 合成的原始内容），其次 report.summary
        response_text = ""
        if result.report and result.report.summary and len(result.report.summary) > 30:
            response_text = result.report.summary
            if result.report.analysis.key_findings:
                response_text += "\n\n**Key Findings:**\n"
                for f in result.report.analysis.key_findings[:5]:
                    response_text += f"- {f}\n"
        elif result.answer and len(result.answer) > 30:
            response_text = _clean_json_response(result.answer)
        else:
            response_text = "Research completed but no summary was generated."

        confidence = 0.9 if result.reasoning_result else 0.75
        return response_text, sources, confidence

    except asyncio.TimeoutError:
        logger.warning("[orchestrator] Pipeline timed out (90s), falling back to direct LLM")
        fallback = await generate_chat_response(message, "")
        return fallback, [], 0.5
    except Exception as e:
        logger.error(f"[orchestrator] Error: {type(e).__name__}: {e}")
        fallback = await generate_chat_response(message, "")
        return fallback, [], 0.5


def _clean_json_response(text: str) -> str:
    """从 LLM 响应中提取纯文本摘要，清理 JSON 格式"""
    import json as _json
    # 尝试解析为 JSON 并提取 summary
    try:
        # 找到 JSON 对象
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = _json.loads(text[start:end])
            parts = []
            if "summary" in data:
                parts.append(data["summary"])
            if "key_findings" in data:
                parts.append("\n**Key Findings:**")
                for f in data["key_findings"][:5]:
                    parts.append(f"- {f}")
            if "recommendations" in data:
                parts.append("\n**Recommendations:**")
                for r in data["recommendations"][:3]:
                    parts.append(f"- {r}")
            if parts:
                return "\n".join(parts)
    except (_json.JSONDecodeError, KeyError):
        pass
    # 如果解析失败，返回原文（截断 JSON 部分）
    if text.startswith("{"):
        # 找到第一个非 JSON 行
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if not line.strip().startswith(('"', "'", "{", "}", "[", "]", ",")):
                return "\n".join(lines[i:])
    return text


async def generate_chat_response(message: str, conversation_id: str) -> str:
    """Generate a chat response using direct LLM call"""
    from app.infrastructure.llm_client import LLMClient

    llm = LLMClient.get_instance()

    # Build conversation context from history
    messages = []
    if conversation_id:
        history = storage.get_conversation(conversation_id)
        if history and history.get("messages"):
            for msg in history["messages"][-10:]:  # Last 10 messages for context
                messages.append({"role": msg["role"], "content": msg["content"]})

    # Add system prompt for financial assistant persona
    system_msg = {
        "role": "system",
        "content": (
            "You are a Smart Finance Agent, an AI financial research assistant. "
            "You can help with stock prices, financial reports, news analysis, and market research. "
            "Answer concisely and helpfully in a structured format. "
            "If the user asks about stocks or finance, provide useful information. "
            "Always reply in the same language as the user's message. "
            "Do NOT say 'I received your question' - instead provide a substantive answer."
        ),
    }

    llm_messages = [system_msg, *messages, {"role": "user", "content": message}]

    try:
        resp = await llm.chat(llm_messages, max_tokens=1024)
        return resp.content or "I apologize, but I couldn't generate a response. Please try rephrasing your question."
    except Exception as e:
        logger.error(f"LLM chat error: {e}")
        return f"I encountered an error: {type(e).__name__}. Please try again."