"""
User models and schemas
"""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """User login request"""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response (without password)"""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseModel):
    """Token payload data"""
    user_id: int | None = None
    username: str | None = None
