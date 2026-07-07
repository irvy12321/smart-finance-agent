"""
真实鉴权/RBAC 集成测试（不 mock 任何 auth 组件）

覆盖：
- 真实注册/登录：bcrypt 校验 + 真实 JWT 签发
- 无 token / 伪造 token 拒绝
- viewer 角色被 403 拒绝 analyst/admin 端点
- 角色提升后（DB 中的角色为准）放行
- refresh token 轮换：旧 token 复用被拒绝
- logout 撤销 refresh token
- 停用账户被拒绝
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

PASSWORD = "Str0ngPass-123"


async def _register(client: AsyncClient, username: str) -> dict:
    resp = await client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _set_role(storage, username: str, role: str) -> None:
    conn = storage._get_connection()
    try:
        conn.execute("UPDATE users SET role = ? WHERE username = ?", (role, username))
        conn.commit()
    finally:
        conn.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_register_login_me_with_real_jwt(real_client, temp_db):
    """注册返回真实 token 对；/me 用真实 JWT 解码；登录走真实 bcrypt 校验"""
    data = await _register(real_client, "rbac_user1")
    assert data["user"]["role"] == "viewer"
    assert data["access_token"] and data["refresh_token"]

    me = await real_client.get("/api/auth/me", headers=_auth(data["access_token"]))
    assert me.status_code == 200
    assert me.json()["username"] == "rbac_user1"

    login = await real_client.post(
        "/api/auth/login", json={"username": "rbac_user1", "password": PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == data["user"]["id"]

    bad = await real_client.post(
        "/api/auth/login", json={"username": "rbac_user1", "password": "WrongPass-123"}
    )
    assert bad.status_code == 401


async def test_missing_token_rejected(real_client, temp_db):
    resp = await real_client.get("/api/auth/me")
    assert resp.status_code in (401, 403)

    resp = await real_client.post("/api/task/create", json={"query": "AAPL analysis"})
    assert resp.status_code in (401, 403)


async def test_tampered_token_rejected(real_client, temp_db):
    data = await _register(real_client, "rbac_user2")
    token = data["access_token"]
    # 篡改签名中间的一个字符（末位字符的低比特是 base64 填充位，改了可能不生效）
    sig_start = token.rindex(".") + 1
    mid = sig_start + (len(token) - sig_start) // 2
    tampered = token[:mid] + ("A" if token[mid] != "A" else "B") + token[mid + 1 :]
    resp = await real_client.get("/api/auth/me", headers=_auth(tampered))
    assert resp.status_code == 401

    resp = await real_client.get("/api/auth/me", headers=_auth("not.a.jwt"))
    assert resp.status_code == 401


async def test_viewer_forbidden_on_write_endpoints(real_client, temp_db):
    """默认注册为 viewer，必须被 analyst/admin 专属端点 403 拒绝"""
    data = await _register(real_client, "rbac_viewer")
    headers = _auth(data["access_token"])

    for method, url, payload in [
        ("POST", "/api/task/create", {"query": "Analyze AAPL"}),
        ("POST", "/api/chat/conversations", None),
        ("POST", "/api/tools/stock/price", {"symbol": "AAPL"}),
        ("GET", "/api/task/list", None),
    ]:
        if method == "POST":
            resp = await real_client.post(url, json=payload, headers=headers)
        else:
            resp = await real_client.get(url, headers=headers)
        assert resp.status_code == 403, f"{url} -> {resp.status_code}"

    # admin 专属端点对 viewer 也是 403
    resp = await real_client.get("/api/auth/admin/users", headers=headers)
    assert resp.status_code == 403


async def test_analyst_role_from_db_grants_access(real_client, temp_db):
    """角色以 DB 为准：提升为 analyst 后同一 token 即可创建任务；analyst 仍无 admin 权限"""
    data = await _register(real_client, "rbac_analyst")
    headers = _auth(data["access_token"])

    resp = await real_client.post(
        "/api/task/create", json={"query": "Analyze AAPL"}, headers=headers
    )
    assert resp.status_code == 403

    _set_role(temp_db, "rbac_analyst", "analyst")

    resp = await real_client.post(
        "/api/task/create", json={"query": "Analyze AAPL"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    resp = await real_client.get("/api/auth/admin/users", headers=headers)
    assert resp.status_code == 403


async def test_admin_role_allows_admin_endpoints(real_client, temp_db):
    data = await _register(real_client, "rbac_admin")
    _set_role(temp_db, "rbac_admin", "admin")
    headers = _auth(data["access_token"])

    resp = await real_client.get("/api/auth/admin/users", headers=headers)
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "rbac_admin" in usernames


async def test_refresh_rotation_rejects_old_token(real_client, temp_db):
    """refresh 轮换：换出新 token 对，旧 refresh token 复用必须 401"""
    data = await _register(real_client, "rbac_refresh")
    old_refresh = data["refresh_token"]

    resp = await real_client.post(
        "/api/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != old_refresh

    # 新 access token 可用
    me = await real_client.get(
        "/api/auth/me", headers=_auth(new_tokens["access_token"])
    )
    assert me.status_code == 200

    # 旧 refresh token 已被撤销
    reuse = await real_client.post(
        "/api/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert reuse.status_code == 401


async def test_logout_revokes_refresh_token(real_client, temp_db):
    data = await _register(real_client, "rbac_logout")
    refresh = data["refresh_token"]

    resp = await real_client.post("/api/auth/logout", json={"refresh_token": refresh})
    assert resp.status_code == 200

    resp = await real_client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401


async def test_inactive_user_rejected(real_client, temp_db):
    data = await _register(real_client, "rbac_inactive")
    headers = _auth(data["access_token"])

    conn = temp_db._get_connection()
    try:
        conn.execute(
            "UPDATE users SET is_active = 0 WHERE username = ?", ("rbac_inactive",)
        )
        conn.commit()
    finally:
        conn.close()

    resp = await real_client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 403

    login = await real_client.post(
        "/api/auth/login", json={"username": "rbac_inactive", "password": PASSWORD}
    )
    assert login.status_code == 403
