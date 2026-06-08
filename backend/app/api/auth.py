"""
Authentication API routes
"""
from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends

from app.auth import get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.auth.models import UserCreate, UserLogin, UserResponse, Token
from app.auth.dependencies import (
    get_user_by_username,
    get_user_by_email,
    create_user,
    authenticate_user,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user"""
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


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """Authenticate user and return token"""
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
