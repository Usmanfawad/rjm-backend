"""Authentication API routes using simple JWT authentication."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.db import get_session
from app.config.logger import app_logger
from app.config.settings import settings
from app.models.user import User
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
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user account.

    Creates a new user in the database with hashed password.
    Returns access token for immediate use.
    """
    try:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.email == request.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Create new user
        new_user = User(
            id=uuid4(),
            email=request.email,
            username=request.username,
            full_name=request.full_name,
            hashed_password=hash_password(request.password),
            is_active=True,
            is_verified=True,  # Auto-verify for simple auth
            email_verified_at=datetime.now(timezone.utc),
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        # Create access token
        access_token = create_local_token(str(new_user.id), new_user.email)

        app_logger.info(f"User registered: {new_user.email} (ID: {new_user.id})")

        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.LOCAL_AUTH_TOKEN_EXP_SECONDS,
            user_id=str(new_user.id),
            email=new_user.email,
        )

        return success_response(
            data=token_response,
            message="User registered successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        app_logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Authenticate user and return access token.

    Validates email and password, then returns JWT access token.
    """
    try:
        # Find user by email
        result = await session.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()

        if not user or not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(user)

        # Create access token
        access_token = create_local_token(str(user.id), user.email)

        app_logger.info(f"User logged in: {user.email} (ID: {user.id})")

        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.LOCAL_AUTH_TOKEN_EXP_SECONDS,
            user_id=str(user.id),
            email=user.email,
        )

        return success_response(
            data=token_response,
            message="Login successful"
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        app_logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_current_user(
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(require_auth),
):
    """Get current authenticated user information.

    Returns user profile information for the authenticated user.
    """
    try:
        # Find user by ID
        user_uuid = UUID(user_id)
        result = await session.execute(
            select(User).where(User.id == user_uuid)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user_response = UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
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
