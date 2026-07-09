"""
多用户数据隔离/越权访问集成测试（真实 SQLite + 真实 JWT）

覆盖：
- 会话（conversation）跨用户读取/删除被 403 拒绝
- 会话列表只返回本人数据
- 任务（task）状态/结果/执行跨用户访问被 403 拒绝
- 任务列表只返回本人数据
- 报告（report）跨用户访问被 403 拒绝
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

PASSWORD = "Str0ngPass-123"


async def _make_analyst(client: AsyncClient, storage, username: str) -> dict:
    resp = await client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
        },
    )
    assert resp.status_code == 201, resp.text
    conn = storage._get_connection()
    try:
        conn.execute(
            "UPDATE users SET role = 'analyst' WHERE username = ?", (username,)
        )
        conn.commit()
    finally:
        conn.close()
    return resp.json()


def _auth(data: dict) -> dict:
    return {"Authorization": f"Bearer {data['access_token']}"}


async def test_conversation_cross_user_access_denied(real_client, temp_db):
    a = await _make_analyst(real_client, temp_db, "own_conv_a")
    b = await _make_analyst(real_client, temp_db, "own_conv_b")

    resp = await real_client.post("/api/chat/conversations", headers=_auth(a))
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]
    temp_db.add_message(conv_id, "user", "hello from A")

    # B 读 A 的会话历史 → 403
    resp = await real_client.get(f"/api/chat/conversations/{conv_id}", headers=_auth(b))
    assert resp.status_code == 403

    # B 删 A 的会话 → 403，且数据未被删除
    resp = await real_client.delete(
        f"/api/chat/conversations/{conv_id}", headers=_auth(b)
    )
    assert resp.status_code == 403
    assert temp_db.get_conversation(conv_id) is not None

    # A 本人可读
    resp = await real_client.get(f"/api/chat/conversations/{conv_id}", headers=_auth(a))
    assert resp.status_code == 200
    assert resp.json()["total_messages"] == 1


async def test_ownerless_conversation_access_denied(real_client, temp_db):
    a = await _make_analyst(real_client, temp_db, "ownerless_conv_a")
    temp_db.create_conversation("legacy-ownerless")
    temp_db.add_message("legacy-ownerless", "user", "legacy private data")

    resp = await real_client.get(
        "/api/chat/conversations/legacy-ownerless", headers=_auth(a)
    )
    assert resp.status_code == 403


async def test_conversation_list_only_own(real_client, temp_db):
    a = await _make_analyst(real_client, temp_db, "own_list_a")
    b = await _make_analyst(real_client, temp_db, "own_list_b")

    resp = await real_client.post("/api/chat/conversations", headers=_auth(a))
    a_conv = resp.json()["conversation_id"]

    resp = await real_client.get("/api/chat/conversations", headers=_auth(b))
    assert resp.status_code == 200
    b_convs = [c["conversation_id"] for c in resp.json()["conversations"]]
    assert a_conv not in b_convs


async def test_task_cross_user_access_denied(real_client, temp_db):
    a = await _make_analyst(real_client, temp_db, "own_task_a")
    b = await _make_analyst(real_client, temp_db, "own_task_b")

    resp = await real_client.post(
        "/api/task/create", json={"query": "Analyze AAPL"}, headers=_auth(a)
    )
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    # B 查状态/结果/执行 → 403
    resp = await real_client.get(f"/api/task/{task_id}/status", headers=_auth(b))
    assert resp.status_code == 403
    resp = await real_client.get(f"/api/task/{task_id}/result", headers=_auth(b))
    assert resp.status_code == 403
    resp = await real_client.post(f"/api/task/{task_id}/run", headers=_auth(b))
    assert resp.status_code == 403

    # A 本人可查
    resp = await real_client.get(f"/api/task/{task_id}/status", headers=_auth(a))
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


async def test_task_list_only_own(real_client, temp_db):
    a = await _make_analyst(real_client, temp_db, "own_tlist_a")
    b = await _make_analyst(real_client, temp_db, "own_tlist_b")

    resp = await real_client.post(
        "/api/task/create", json={"query": "Analyze TSLA"}, headers=_auth(a)
    )
    a_task = resp.json()["task_id"]

    resp = await real_client.get("/api/task/list", headers=_auth(b))
    assert resp.status_code == 200
    b_tasks = [t["task_id"] for t in resp.json()["tasks"]]
    assert a_task not in b_tasks

    resp = await real_client.get("/api/task/list", headers=_auth(a))
    a_tasks = [t["task_id"] for t in resp.json()["tasks"]]
    assert a_task in a_tasks


async def test_report_cross_user_access_denied(real_client, temp_db):
    a = await _make_analyst(real_client, temp_db, "own_rep_a")
    b = await _make_analyst(real_client, temp_db, "own_rep_b")

    resp = await real_client.post(
        "/api/task/create", json={"query": "Analyze NVDA"}, headers=_auth(a)
    )
    task_id = resp.json()["task_id"]

    temp_db.update_task_result(
        task_id,
        {"answer": "done", "report_markdown": "# Report", "confidence": 0.9},
        [],
    )
    temp_db.update_task(task_id, status="completed")

    for suffix in [
        "",
        "/summary",
        "/markdown",
        "/charts",
        "/analysis",
        "/sources",
        "/process",
    ]:
        resp = await real_client.get(f"/api/report/{task_id}{suffix}", headers=_auth(b))
        assert resp.status_code == 403, f"suffix={suffix}: {resp.text}"

    resp = await real_client.get(f"/api/report/{task_id}", headers=_auth(a))
    assert resp.status_code == 200
