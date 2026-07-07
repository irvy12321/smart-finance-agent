"""
黄金路径端到端测试（仅在 LLM/Orchestrator 边界打桩，其余全部真实）

完整用户旅程：
注册 → 登录 → 鉴权(/me) → 创建会话 → 发消息（真实持久化）→ 读历史
→ 创建任务 → 执行任务（事件流→进度→结果真实写入 SQLite）
→ 查询结果 → 获取报告 → 登出（refresh token 失效）

全程走真实 JWT、真实 RBAC、真实 SQLite 存储。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio

PASSWORD = "Str0ngPass-123"


class FakeOrchestrator:
    """在 orchestrator 边界打桩：产出真实事件流供 task 管线消费"""

    async def run_with_streaming(self, query: str, language: str = "en"):
        yield {"stage": "planning"}
        yield {
            "stage": "plan_ready",
            "subtasks": [{"id": "t1", "tool": "stock_price"}],
            "reasoning": "Plan for AAPL",
        }
        yield {
            "stage": "task_done",
            "task_id": "t1",
            "tool": "stock_price",
            "success": True,
            "duration_ms": 10,
        }
        yield {"stage": "reasoning"}
        yield {"stage": "reasoning_done", "confidence": 0.9, "insights": ["insight"]}
        yield {"stage": "reporting"}
        yield {
            "stage": "complete",
            "answer": "AAPL is trending upward",
            "report_markdown": "# AAPL Report\n## 摘要\nGolden path summary",
        }


async def test_golden_path_full_user_journey(
    real_client, temp_db, test_app, monkeypatch
):
    # ── 1. 注册（真实 bcrypt + JWT）───────────────────────────
    resp = await real_client.post(
        "/api/auth/register",
        json={
            "username": "golden_user",
            "email": "golden_user@example.com",
            "password": PASSWORD,
        },
    )
    assert resp.status_code == 201

    # 提升为 analyst（角色以 DB 为准）
    conn = temp_db._get_connection()
    try:
        conn.execute("UPDATE users SET role = 'analyst' WHERE username = 'golden_user'")
        conn.commit()
    finally:
        conn.close()

    # ── 2. 登录 ───────────────────────────────────────────────
    resp = await real_client.post(
        "/api/auth/login", json={"username": "golden_user", "password": PASSWORD}
    )
    assert resp.status_code == 200
    tokens = resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = await real_client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "analyst"

    # ── 3. 会话：创建 → 发消息 → 读历史（真实 SQLite 持久化）──
    from app.api import chat as chat_module

    monkeypatch.setattr(
        chat_module,
        "generate_chat_response",
        AsyncMock(return_value="I can help with financial research."),
    )
    ltm = MagicMock()
    ltm.store_memory = AsyncMock()
    monkeypatch.setattr(
        chat_module.LongTermMemory, "get_instance", classmethod(lambda cls: ltm)
    )

    resp = await real_client.post("/api/chat/conversations", headers=headers)
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]

    resp = await real_client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"message": "Hello, what can you do?"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["response"] == "I can help with financial research."

    resp = await real_client.get(f"/api/chat/conversations/{conv_id}", headers=headers)
    assert resp.status_code == 200
    history = resp.json()
    assert history["total_messages"] == 2
    assert history["messages"][0]["role"] == "user"
    assert history["messages"][1]["role"] == "assistant"

    # ── 4. 任务：创建 → 执行 → 轮询状态 → 取结果 ─────────────
    old_orch = getattr(test_app.state, "orchestrator", None)
    test_app.state.orchestrator = FakeOrchestrator()
    try:
        resp = await real_client.post(
            "/api/task/create", json={"query": "Analyze AAPL"}, headers=headers
        )
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]

        resp = await real_client.get(f"/api/task/{task_id}/status", headers=headers)
        assert resp.json()["status"] == "pending"

        resp = await real_client.post(f"/api/task/{task_id}/run", headers=headers)
        assert resp.status_code == 200

        status = ""
        for _ in range(100):
            resp = await real_client.get(f"/api/task/{task_id}/status", headers=headers)
            status = resp.json()["status"]
            if status in ("completed", "failed"):
                break
            await asyncio.sleep(0.05)
        assert status == "completed"

        resp = await real_client.get(f"/api/task/{task_id}/result", headers=headers)
        assert resp.status_code == 200
        result = resp.json()
        assert result["answer"] == "AAPL is trending upward"
        assert result["confidence"] == 0.9
        assert result["total_tasks"] == 1
        assert result["success_tasks"] == 1
        assert result["failed_tasks"] == 0

        # ── 5. 报告 ───────────────────────────────────────────
        resp = await real_client.get(f"/api/report/{task_id}", headers=headers)
        assert resp.status_code == 200
        assert "AAPL Report" in resp.json()["report_markdown"]
    finally:
        test_app.state.orchestrator = old_orch

    # ── 6. 登出：refresh token 立即失效 ──────────────────────
    resp = await real_client.post(
        "/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200

    resp = await real_client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 401
