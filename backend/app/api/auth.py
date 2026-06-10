"""
Authentication API routes
"""
import traceback
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_password_hash
from app.auth.dependencies import (
    authenticate_user,
    create_user,
    get_current_user,
    get_user_by_email,
    get_user_by_username,
)
from app.auth.models import Token, UserCreate, UserLogin, UserResponse
from app.utils.logger import get_logger

logger = get_logger("api.auth")

router = APIRouter(prefix="/auth", tags=["authentication"])

limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserCreate):
    """Register a new user"""
    try:
        logger.info(f"Register attempt: username={user_data.username}, email={user_data.email}")

        # Check if username already exists
        existing_user = get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )

        # Check if email already exists
        existing_email = get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Create user
        hashed_password = get_password_hash(user_data.password)
        user = create_user(user_data.username, user_data.email, hashed_password)

        logger.info(f"User created: id={user['id']}, username={user['username']}")

        # Generate token
        access_token = create_access_token(
            data={"user_id": user["id"], "username": user["username"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                is_active=user["is_active"],
                created_at=user["created_at"],
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {e!s}"
        ) from e


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, user_data: UserLogin):
    """Authenticate user and return token"""
    try:
        logger.info(f"Login attempt: username={user_data.username}")
        user = authenticate_user(user_data.username, user_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )

        # Generate token
        access_token = create_access_token(
            data={"user_id": user["id"], "username": user["username"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                is_active=user["is_active"],
                created_at=user["created_at"],
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {e!s}"
        ) from e


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current authenticated user info"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: UserResponse = Depends(get_current_user)):
    """Refresh access token"""
    access_token = create_access_token(
        data={"user_id": current_user.id, "username": current_user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=current_user
    )
