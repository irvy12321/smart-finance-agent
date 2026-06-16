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
    role: str = "viewer"
    is_active: bool
    created_at: str


class Token(BaseModel):
    """JWT token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseModel):
    """Token payload data"""

    user_id: int | None = None
    username: str | None = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request"""

    refresh_token: str


class AdminUserCreate(BaseModel):
    """Admin user creation request"""

    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default="viewer", pattern="^(admin|analyst|viewer)$")


class AdminUserUpdate(BaseModel):
    """Admin user update request"""

    role: str | None = Field(default=None, pattern="^(admin|analyst|viewer)$")
    is_active: bool | None = None
