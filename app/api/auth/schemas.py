"""Authentication request and response schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (minimum 8 characters)")
    username: Optional[str] = Field(default=None, max_length=100, description="Optional username")
    full_name: Optional[str] = Field(default=None, max_length=255, description="Optional full name")

    model_config = {"json_schema_extra": {"example": {
        "email": "user@example.com",
        "password": "securepassword123",
        "username": "johndoe",
        "full_name": "John Doe"
    }}}


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = {"json_schema_extra": {"example": {
        "email": "user@example.com",
        "password": "securepassword123"
    }}}


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: str = Field(..., description="Authenticated user ID")
    email: str = Field(..., description="User email address")

    model_config = {"json_schema_extra": {"example": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 3600,
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "user@example.com"
    }}}


class UserResponse(BaseModel):
    """Response schema for user information."""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: Optional[str] = Field(default=None, description="Username")
    full_name: Optional[str] = Field(default=None, description="Full name")
    is_active: bool = Field(..., description="Whether user account is active")
    is_verified: bool = Field(..., description="Whether user email is verified")

    model_config = {"json_schema_extra": {"example": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "user@example.com",
        "username": "johndoe",
        "full_name": "John Doe",
        "is_active": True,
        "is_verified": True
    }}}
