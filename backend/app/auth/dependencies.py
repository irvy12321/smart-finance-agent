"""
User database operations and dependencies
"""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import storage
from app.auth import (
    decode_access_token,
    get_refresh_token_expiry,
    hash_refresh_token,
    is_refresh_token_expired,
    verify_password,
)
from app.auth.models import TokenData, UserResponse
from app.auth.roles import Role, has_permission

# Security scheme
security = HTTPBearer()


def get_user_by_username(username: str) -> dict | None:
    """Get user by username from database"""
    conn = storage._get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    """Get user by email from database"""
    conn = storage._get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """Get user by ID from database"""
    conn = storage._get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_user(username: str, email: str, hashed_password: str) -> dict:
    """Create a new user in database"""
    now = datetime.now(timezone.utc).isoformat()
    conn = storage._get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, email, hashed_password, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, hashed_password, True, now, now),
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {
            "id": user_id,
            "username": username,
            "email": email,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate user with username and password"""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserResponse:
    """Dependency to get current authenticated user from JWT token"""
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        role: str = payload.get("role", "viewer")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_data = TokenData(user_id=user_id, username=username)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user = get_user_by_id(token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    # Use role from database (more up-to-date than JWT)
    user_role = user.get("role", role)

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user_role,
        is_active=user["is_active"],
        created_at=user["created_at"],
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> UserResponse | None:
    """Optional dependency - returns None if no token provided"""
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ── Refresh Token Operations ──────────────────────────────────────────────


def create_refresh_token_record(user_id: int, token: str) -> dict:
    """
    Store a refresh token in the database

    Args:
        user_id: User ID
        token: Plain refresh token (will be hashed before storage)

    Returns:
        Created record dict
    """
    token_hash = hash_refresh_token(token)
    expires_at = get_refresh_token_expiry()
    now = datetime.now(timezone.utc).isoformat()

    conn = storage._get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, token_hash, expires_at, now),
        )
        conn.commit()
        return {
            "id": cursor.lastrowid,
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "created_at": now,
        }
    finally:
        conn.close()


def get_refresh_token_record(token: str) -> dict | None:
    """
    Get refresh token record by plain token

    Args:
        token: Plain refresh token

    Returns:
        Record dict or None if not found
    """
    token_hash = hash_refresh_token(token)

    conn = storage._get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM refresh_tokens WHERE token_hash = ? AND revoked = 0",
            (token_hash,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def revoke_refresh_token(token: str) -> bool:
    """
    Revoke a specific refresh token

    Args:
        token: Plain refresh token to revoke

    Returns:
        True if token was revoked, False if not found
    """
    token_hash = hash_refresh_token(token)

    conn = storage._get_connection()
    try:
        cursor = conn.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def revoke_all_user_tokens(user_id: int) -> int:
    """
    Revoke all refresh tokens for a user

    Args:
        user_id: User ID

    Returns:
        Number of tokens revoked
    """
    conn = storage._get_connection()
    try:
        cursor = conn.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ? AND revoked = 0",
            (user_id,),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def cleanup_expired_tokens() -> int:
    """
    Remove expired refresh tokens from database

    Returns:
        Number of tokens removed
    """
    now = datetime.now(timezone.utc).isoformat()

    conn = storage._get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM refresh_tokens WHERE expires_at < ? OR revoked = 1", (now,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def get_user_active_tokens_count(user_id: int) -> int:
    """
    Get count of active refresh tokens for a user

    Args:
        user_id: User ID

    Returns:
        Count of active tokens
    """
    conn = storage._get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as count FROM refresh_tokens WHERE user_id = ? AND revoked = 0 AND expires_at > ?",
            (user_id, datetime.now(timezone.utc).isoformat()),
        ).fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()


def verify_and_rotate_refresh_token(old_token: str) -> tuple[dict, str, str] | None:
    """
    Verify a refresh token and rotate it (revoke old, create new)

    Args:
        old_token: Plain refresh token to verify

    Returns:
        Tuple of (user_dict, new_access_token, new_refresh_token) or None if invalid
    """
    from app.auth import create_token_pair

    # Get the old token record
    record = get_refresh_token_record(old_token)
    if not record:
        return None

    # Check if expired
    if is_refresh_token_expired(record["expires_at"]):
        revoke_refresh_token(old_token)
        return None

    # Get user
    user = get_user_by_id(record["user_id"])
    if not user or not user.get("is_active", True):
        revoke_refresh_token(old_token)
        return None

    # Get user role
    user_role = user.get("role", "viewer")

    # Generate new token pair with role
    tokens = create_token_pair(user["id"], user["username"], user_role)

    # Store new refresh token
    create_refresh_token_record(user["id"], tokens["refresh_token"])

    # Revoke old refresh token
    revoke_refresh_token(old_token)

    return user, tokens["access_token"], tokens["refresh_token"]


# ── Role-Based Access Control Dependencies ──────────────────────────────


def require_role(*roles: Role):
    """
    FastAPI dependency to require specific roles

    Usage:
        @router.post("/task/create")
        async def create_task(
            ...,
            current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST))
        ):
            ...
    """

    def role_checker(
        current_user: UserResponse = Depends(get_current_user),
    ) -> UserResponse:
        if current_user.role not in [r.value for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in roles]}",
            )
        return current_user

    return role_checker


def require_permission(permission: str):
    """
    FastAPI dependency to require a specific permission

    Usage:
        @router.post("/task/create")
        async def create_task(
            ...,
            current_user: UserResponse = Depends(require_permission("task:create"))
        ):
            ...
    """

    def permission_checker(
        current_user: UserResponse = Depends(get_current_user),
    ) -> UserResponse:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user

    return permission_checker
