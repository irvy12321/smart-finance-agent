"""
JWT Authentication utilities

Supports:
- Access Token (short-lived, 15 minutes)
- Refresh Token (long-lived, 7 days, stored in DB)
- Token rotation on refresh
"""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status

# Configuration — JWT_SECRET_KEY is mandatory; no insecure fallback
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable is not set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))  # 15 minutes
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # 7 days
REFRESH_TOKEN_LENGTH = int(os.getenv("REFRESH_TOKEN_LENGTH", "64"))  # 64 bytes = 128 hex chars


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Verify it's an access token
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token"""
    return secrets.token_hex(REFRESH_TOKEN_LENGTH)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage (SHA256)"""
    return hashlib.sha256(token.encode()).hexdigest()


def get_refresh_token_expiry() -> str:
    """Get refresh token expiry as ISO 8601 string"""
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return expires_at.isoformat()


def is_refresh_token_expired(expires_at: str) -> bool:
    """Check if a refresh token is expired"""
    try:
        expiry = datetime.fromisoformat(expires_at)
        # Handle both timezone-aware and naive datetimes
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expiry
    except (ValueError, TypeError):
        return True


def create_token_pair(user_id: int, username: str, role: str = "viewer") -> dict:
    """
    Create both access and refresh tokens
    
    Args:
        user_id: User ID
        username: Username
        role: User role (admin, analyst, viewer)
    
    Returns:
        dict with access_token, refresh_token, expires_in
    """
    # Create access token with role
    access_token = create_access_token(
        data={"user_id": user_id, "username": username, "role": role}
    )
    
    # Create refresh token
    refresh_token = generate_refresh_token()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
    }
