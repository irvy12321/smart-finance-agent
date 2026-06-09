"""
User database operations and dependencies
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import storage
from app.auth import decode_access_token, verify_password
from app.auth.models import TokenData, UserResponse

# Security scheme
security = HTTPBearer()


def get_user_by_username(username: str) -> dict | None:
    """Get user by username from database"""
    conn = storage._get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    """Get user by email from database"""
    conn = storage._get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """Get user by ID from database"""
    conn = storage._get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_user(username: str, email: str, hashed_password: str) -> dict:
    """Create a new user in database"""
    from datetime import datetime
    now = datetime.now().isoformat()
    conn = storage._get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, email, hashed_password, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, hashed_password, True, now, now)
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
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """Dependency to get current authenticated user from JWT token"""
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")

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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        is_active=user["is_active"],
        created_at=user["created_at"],
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))
) -> UserResponse | None:
    """Optional dependency - returns None if no token provided"""
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
