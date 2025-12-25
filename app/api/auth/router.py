"""Authentication API routes using Supabase REST API.

Uses supabase-py for database operations (HTTPS port 443),
which works on all hosting platforms including Render free tier.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.config.logger import app_logger
from app.config.settings import settings
from app.db.supabase_db import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    update_user_last_login,
)
from app.utils.responses import (
    SuccessResponse,
    success_response,
)
from app.utils.auth import require_auth
from app.utils.passwords import hash_password, verify_password
from app.utils.local_tokens import create_local_token
from app.api.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", response_model=SuccessResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Register a new user account.

    Creates a new user in Supabase via REST API.
    Returns access token for immediate use.
    """
    try:
        # Check if user already exists
        existing_user = await get_user_by_email(request.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Create new user via Supabase REST API
        new_user = await create_user(
            email=request.email,
            username=request.username,
            full_name=request.full_name,
            hashed_password=hash_password(request.password),
            is_active=True,
            is_verified=True,
        )

        # Create access token
        access_token = create_local_token(new_user["id"], new_user["email"])

        app_logger.info(f"User registered via Supabase REST API: {new_user['email']} (ID: {new_user['id']})")

        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.LOCAL_AUTH_TOKEN_EXP_SECONDS,
            user_id=new_user["id"],
            email=new_user["email"],
        )

        return success_response(
            data=token_response,
            message="User registered successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(request: LoginRequest):
    """Authenticate user and return access token.

    Validates email and password via Supabase REST API,
    then returns JWT access token.
    """
    try:
        # Find user by email via Supabase REST API
        user = await get_user_by_email(request.email)

        if not user or not user.get("hashed_password"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        if not verify_password(request.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if user is active
        if not user.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Update last login (non-blocking, don't wait)
        await update_user_last_login(user["id"])

        # Create access token
        access_token = create_local_token(user["id"], user["email"])

        app_logger.info(f"User logged in via Supabase REST API: {user['email']} (ID: {user['id']})")

        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.LOCAL_AUTH_TOKEN_EXP_SECONDS,
            user_id=user["id"],
            email=user["email"],
        )

        return success_response(
            data=token_response,
            message="Login successful"
        )

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_current_user(user_id: str = Depends(require_auth)):
    """Get current authenticated user information.

    Returns user profile information for the authenticated user.
    """
    try:
        # Find user by ID via Supabase REST API
        user = await get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user_response = UserResponse(
            id=UUID(user["id"]),
            email=user["email"],
            username=user.get("username"),
            full_name=user.get("full_name"),
            is_active=user.get("is_active", False),
            is_verified=user.get("is_verified", False),
        )

        return success_response(
            data=user_response,
            message="User information retrieved successfully"
        )

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    except Exception as e:
        app_logger.error(f"Get user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user: {str(e)}"
        )
