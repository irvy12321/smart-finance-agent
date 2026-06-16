"""
Authentication API routes

Supports:
- Register: Create user + return access_token + refresh_token
- Login: Authenticate + return access_token + refresh_token
- Refresh: Rotate refresh_token + return new access_token + refresh_token
- Logout: Revoke refresh_token
- Me: Get current user info
"""

import traceback

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_token_pair, get_password_hash
from app.auth.dependencies import (
    authenticate_user,
    create_refresh_token_record,
    create_user,
    get_current_user,
    get_user_by_email,
    get_user_by_username,
    require_role,
    revoke_refresh_token,
    verify_and_rotate_refresh_token,
)
from app.auth.login_security import (
    get_remaining_attempts,
    is_account_locked,
    record_login_failure,
    record_login_success,
)
from app.auth.models import (
    AdminUserCreate,
    AdminUserUpdate,
    LogoutRequest,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.auth.roles import Role, get_default_role, is_valid_role
from app.utils.logger import get_logger

logger = get_logger("api.auth")

router = APIRouter(prefix="/auth", tags=["authentication"])

limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserCreate):
    """Register a new user and return token pair"""
    try:
        logger.info(
            f"Register attempt: username={user_data.username}, email={user_data.email}"
        )

        # Check if username already exists
        existing_user = get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )

        # Check if email already exists
        existing_email = get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

        # Create user with default role
        hashed_password = get_password_hash(user_data.password)
        user = create_user(user_data.username, user_data.email, hashed_password)

        # Set default role
        user_role = get_default_role()

        # Update user role in database
        from app import storage

        conn = storage._get_connection()
        try:
            conn.execute(
                "UPDATE users SET role = ? WHERE id = ?", (user_role, user["id"])
            )
            conn.commit()
        finally:
            conn.close()

        user["role"] = user_role

        logger.info(
            f"User created: id={user['id']}, username={user['username']}, role={user_role}"
        )

        # Generate token pair with role
        tokens = create_token_pair(user["id"], user["username"], user_role)

        # Store refresh token
        create_refresh_token_record(user["id"], tokens["refresh_token"])

        return Token(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=tokens["expires_in"],
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                role=user_role,
                is_active=user["is_active"],
                created_at=user["created_at"],
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {e!s}",
        ) from e


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, user_data: UserLogin):
    """Authenticate user and return token pair"""
    try:
        logger.info(f"Login attempt: username={user_data.username}")

        # 检查账户是否被锁定
        is_locked, seconds_remaining = is_account_locked(user_data.username)
        if is_locked:
            minutes_remaining = (seconds_remaining // 60) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account temporarily locked due to too many failed attempts. Please try again in {minutes_remaining} minutes.",
            )

        user = authenticate_user(user_data.username, user_data.password)
        if not user:
            # 记录登录失败
            record_login_failure(user_data.username)
            remaining = get_remaining_attempts(user_data.username)

            if remaining <= 0:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Account temporarily locked due to too many failed attempts. Please try again in 15 minutes.",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Incorrect username or password. {remaining} attempts remaining.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
            )

        # Get user role (default to viewer if not set)
        user_role = user.get("role", "viewer")

        # 登录成功，清零失败次数
        record_login_success(user_data.username)

        # Generate token pair with role
        tokens = create_token_pair(user["id"], user["username"], user_role)

        # Store refresh token
        create_refresh_token_record(user["id"], tokens["refresh_token"])

        logger.info(f"Login successful: user_id={user['id']}, role={user_role}")

        return Token(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=tokens["expires_in"],
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                role=user_role,
                is_active=user["is_active"],
                created_at=user["created_at"],
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {e!s}",
        ) from e


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current authenticated user info"""
    return current_user


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh_token(request: Request, body: RefreshTokenRequest):
    """
    Refresh access token using refresh token

    Implements token rotation:
    - Verifies the refresh token
    - Creates new access token + refresh token
    - Revokes the old refresh token
    """
    try:
        logger.info("Token refresh attempt")

        result = verify_and_rotate_refresh_token(body.refresh_token)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user, new_access_token, new_refresh_token = result

        # Get user role
        user_role = user.get("role", "viewer")

        logger.info(
            f"Token refreshed successfully: user_id={user['id']}, role={user_role}"
        )

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                role=user_role,
                is_active=user["is_active"],
                created_at=user["created_at"],
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {e!s}",
        ) from e


@router.post("/logout")
async def logout(body: LogoutRequest):
    """
    Logout by revoking refresh token

    Note: Access token remains valid until expiry (short-lived)
    """
    try:
        logger.info("Logout attempt")

        revoked = revoke_refresh_token(body.refresh_token)

        if revoked:
            logger.info("Logout successful: refresh token revoked")
        else:
            logger.warning("Logout: refresh token not found (may already be revoked)")

        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {e!s}",
        ) from e


# ============================================================
# Admin API - 仅管理员可访问
# ============================================================


@router.post(
    "/admin/create-user",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_user(
    user_data: AdminUserCreate,
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """
    管理员创建指定角色的用户

    仅 admin 角色可访问
    """
    try:
        logger.info(
            f"Admin create user attempt: username={user_data.username}, role={user_data.role} by {current_user.username}"
        )

        # 检查用户名是否已存在
        existing_user = get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )

        # 检查邮箱是否已存在
        existing_email = get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

        # 验证角色
        if not is_valid_role(user_data.role):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {user_data.role}. Must be one of: admin, analyst, viewer",
            )

        # 创建用户
        hashed_password = get_password_hash(user_data.password)
        user = create_user(user_data.username, user_data.email, hashed_password)

        # 设置角色
        from app import storage

        conn = storage._get_connection()
        try:
            conn.execute(
                "UPDATE users SET role = ? WHERE id = ?", (user_data.role, user["id"])
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(
            f"Admin created user: {user_data.username} (role={user_data.role}) by {current_user.username}"
        )

        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user_data.role,
            is_active=user["is_active"],
            created_at=user["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin create user failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {e!s}",
        ) from e


@router.get("/admin/users", response_model=list[UserResponse])
async def admin_list_users(
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """
    管理员获取用户列表

    仅 admin 角色可访问
    """
    try:
        from app import storage

        conn = storage._get_connection()
        try:
            cursor = conn.execute(
                "SELECT id, username, email, role, is_active, created_at FROM users ORDER BY id"
            )
            users = []
            for row in cursor.fetchall():
                users.append(
                    UserResponse(
                        id=row[0],
                        username=row[1],
                        email=row[2],
                        role=row[3],
                        is_active=bool(row[4]),
                        created_at=row[5],
                    )
                )
            return users
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Admin list users failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {e!s}",
        ) from e


@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """
    管理员更新用户信息

    仅 admin 角色可访问
    """
    try:
        from app import storage

        conn = storage._get_connection()
        try:
            # 检查用户是否存在
            cursor = conn.execute(
                "SELECT id, username, email, role, is_active, created_at FROM users WHERE id = ?",
                (user_id,),
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            # 更新字段
            updates = []
            params = []
            if user_data.role is not None:
                if not is_valid_role(user_data.role):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid role: {user_data.role}",
                    )
                updates.append("role = ?")
                params.append(user_data.role)
            if user_data.is_active is not None:
                updates.append("is_active = ?")
                params.append(user_data.is_active)

            if updates:
                params.append(user_id)
                conn.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params
                )
                conn.commit()

            # 返回更新后的用户
            cursor = conn.execute(
                "SELECT id, username, email, role, is_active, created_at FROM users WHERE id = ?",
                (user_id,),
            )
            user = cursor.fetchone()

            logger.info(
                f"Admin updated user {user_id}: {user_data.dict(exclude_none=True)} by {current_user.username}"
            )

            return UserResponse(
                id=user[0],
                username=user[1],
                email=user[2],
                role=user[3],
                is_active=bool(user[4]),
                created_at=user[5],
            )
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin update user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {e!s}",
        ) from e


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """
    管理员删除用户

    仅 admin 角色可访问
    """
    try:
        # 不能删除自己
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself"
            )

        from app import storage

        conn = storage._get_connection()
        try:
            # 检查用户是否存在
            cursor = conn.execute(
                "SELECT id, username FROM users WHERE id = ?", (user_id,)
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            # 删除用户
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

            logger.info(
                f"Admin deleted user: {user[1]} (id={user_id}) by {current_user.username}"
            )

            return {"message": f"User {user[1]} deleted successfully"}
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin delete user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {e!s}",
        ) from e
