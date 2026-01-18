from pydantic import BaseModel, EmailStr
from typing import Optional
from app.schemas.user import UserResponse

class Token(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Schema for decoded token payload."""
    user_id: Optional[int] = None
    email: Optional[str] = None
    token_type: Optional[str] = None  # "access" or "refresh"


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str
