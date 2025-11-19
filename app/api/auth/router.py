"""Authentication API routes using Supabase Auth."""

from datetime import datetime, timezone
from typing import Optional, Union
from uuid import UUID

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
from app.utils.supabase_client import get_supabase_client
from app.utils.auth import require_auth
from app.utils.passwords import verify_password
from app.utils.local_tokens import create_local_token
from app.api.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    ConfirmEmailRequest,
    ResendConfirmationRequest,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def supabase_enabled() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)




@router.post("/register", response_model=SuccessResponse[Union[TokenResponse, UserResponse]], status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user account using Supabase Auth.
    
    Creates a new user in Supabase Auth and syncs with local database.
    Returns access token for immediate use.
    """
    try:
        if not supabase_enabled():
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Supabase auth is not configured; registration is disabled in local mode.",
            )

        supabase = get_supabase_client()
        
        # Register user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "username": request.username,
                    "full_name": request.full_name,
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account"
            )
        
        # Create or update user in local database
        user_uuid = UUID(auth_response.user.id)
        from sqlalchemy import select as sql_select
        result = await session.execute(
            sql_select(User).where(User.id == user_uuid)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Update existing user
            existing_user.email = auth_response.user.email
            existing_user.username = request.username
            existing_user.full_name = request.full_name
            existing_user.is_active = True
            existing_user.is_verified = auth_response.user.email_confirmed_at is not None
            existing_user.email_verified_at = auth_response.user.email_confirmed_at
            user = existing_user
        else:
            # Create new user record
            new_user = User(
                id=user_uuid,
                email=auth_response.user.email or request.email,
                username=request.username,
                full_name=request.full_name,
                hashed_password=None,  # Supabase handles password hashing
                is_active=True,
                is_verified=auth_response.user.email_confirmed_at is not None,
                email_verified_at=auth_response.user.email_confirmed_at,
            )
            session.add(new_user)
            user = new_user
        
        await session.commit()
        await session.refresh(user)
        
        # Get access token from Supabase session
        # Note: If email confirmation is required, session may be None initially
        # In that case, user needs to confirm email before getting a token
        access_token = None
        expires_in = 3600
        
        if auth_response.session:
            access_token = auth_response.session.access_token
            expires_in = auth_response.session.expires_in or 3600
        
        # If no session token (email confirmation required), return user info without token
        # User will need to confirm email and then login
        if not access_token:
            app_logger.info(f"User registered: {user.email} (ID: {user.id}) - Email confirmation required")
            
            # Return user info without token
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
                message="User registered successfully. Please check your email to confirm your account."
            )
        
        app_logger.info(f"User registered: {user.email} (ID: {user.id})")
        
        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user_id=str(user.id),
            email=user.email,
        )
        
        return success_response(
            data=token_response,
            message="User registered successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        if "already registered" in str(e).lower() or "user already" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
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
    """Authenticate user with Supabase Auth and return access token.
    
    Validates email and password with Supabase, then returns JWT access token.
    """
    try:
        if not supabase_enabled():
            result = await session.execute(select(User).where(User.email == request.email))
            user = result.scalar_one_or_none()
            if not user or not user.hashed_password or not verify_password(
                request.password, user.hashed_password
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive",
                )

            token_response = TokenResponse(
                access_token=create_local_token(str(user.id), user.email),
                token_type="bearer",
                expires_in=settings.LOCAL_AUTH_TOKEN_EXP_SECONDS,
                user_id=str(user.id),
                email=user.email,
            )

            return success_response(
                data=token_response,
                message="Login successful (local mode)",
            )

        supabase = get_supabase_client()
        
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })
        
        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Sync user data with local database
        user_uuid = UUID(auth_response.user.id)
        result = await session.execute(
            select(User).where(User.id == user_uuid)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update existing user
            user.email = auth_response.user.email or user.email
            user.is_verified = auth_response.user.email_confirmed_at is not None
            user.email_verified_at = auth_response.user.email_confirmed_at
            user.last_login_at = datetime.now(timezone.utc)
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive"
                )
        else:
            # Create user record if it doesn't exist (shouldn't happen, but handle gracefully)
            app_logger.warning(f"User {auth_response.user.id} authenticated but not found in local database")
            new_user = User(
                id=user_uuid,
                email=auth_response.user.email or request.email,
                is_active=True,
                is_verified=auth_response.user.email_confirmed_at is not None,
                email_verified_at=auth_response.user.email_confirmed_at,
                last_login_at=datetime.now(timezone.utc),
            )
            session.add(new_user)
            user = new_user
        
        await session.commit()
        await session.refresh(user)
        
        app_logger.info(f"User logged in: {user.email} (ID: {user.id})")
        
        token_response = TokenResponse(
            access_token=auth_response.session.access_token,
            token_type="bearer",
            expires_in=auth_response.session.expires_in,
            user_id=str(user.id),
            email=user.email,
        )
        
        return success_response(
            data=token_response,
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    except Exception as e:
        await session.rollback()
        error_msg = str(e).lower()
        
        # Check for email confirmation errors
        if "email not confirmed" in error_msg or "email_not_confirmed" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not confirmed. Please check your email and confirm your account before logging in."
            )
        
        # Check for invalid credentials
        if "invalid" in error_msg and ("email" in error_msg or "password" in error_msg or "credentials" in error_msg):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        app_logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/confirm-email", response_model=SuccessResponse[TokenResponse])
async def confirm_email(
    request: ConfirmEmailRequest,
    session: AsyncSession = Depends(get_session),
):
    """Confirm user email using Supabase token.
    
    This endpoint verifies the email confirmation token from Supabase
    and returns an access token if confirmation is successful.
    
    For email confirmation, you need to provide both the token and email address.
    """
    try:
        supabase = get_supabase_client()
        
        # Verify the token with Supabase
        # verify_otp requires email address along with the token
        auth_response = supabase.auth.verify_otp({
            "token": request.token,
            "type": request.type,
            "email": request.email,
        })
        
        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired confirmation token"
            )
        
        # Update user verification status in local database
        user_uuid = UUID(auth_response.user.id)
        from sqlalchemy import select as sql_select
        result = await session.execute(
            sql_select(User).where(User.id == user_uuid)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.is_verified = auth_response.user.email_confirmed_at is not None
            user.email_verified_at = auth_response.user.email_confirmed_at
        else:
            # Create user if doesn't exist
            new_user = User(
                id=user_uuid,
                email=auth_response.user.email or "",
                is_active=True,
                is_verified=auth_response.user.email_confirmed_at is not None,
                email_verified_at=auth_response.user.email_confirmed_at,
            )
            session.add(new_user)
            user = new_user
        
        await session.commit()
        await session.refresh(user)
        
        app_logger.info(f"Email confirmed: {user.email} (ID: {user.id})")
        
        token_response = TokenResponse(
            access_token=auth_response.session.access_token,
            token_type="bearer",
            expires_in=auth_response.session.expires_in or 3600,
            user_id=str(user.id),
            email=user.email,
        )
        
        return success_response(
            data=token_response,
            message="Email confirmed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        app_logger.error(f"Email confirmation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email confirmation failed: {str(e)}"
        )


@router.post("/resend-confirmation", response_model=SuccessResponse[dict])
async def resend_confirmation(
    request: ResendConfirmationRequest,
):
    """Resend email confirmation link.
    
    Sends a new confirmation email to the user.
    """
    try:
        supabase = get_supabase_client()
        
        # Resend confirmation email
        supabase.auth.resend({
            "type": "signup",
            "email": request.email,
        })
        
        app_logger.info(f"Confirmation email resent to: {request.email}")
        
        return success_response(
            data={"email": request.email},
            message="Confirmation email sent successfully. Please check your inbox."
        )
        
    except Exception as e:
        app_logger.error(f"Failed to resend confirmation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend confirmation email: {str(e)}"
        )


@router.get("/confirm")
async def confirm_email_callback(
    token: Optional[str] = None,
    type: str = "signup",
    redirect_to: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """Email confirmation callback endpoint.
    
    This endpoint handles the redirect from Supabase email confirmation links.
    Supabase redirects to this endpoint with token in query params.
    After confirming, redirects to frontend with access token.
    
    Args:
        token: Confirmation token from Supabase email link (query param)
        type: Confirmation type (signup, email_change, etc.)
        redirect_to: Optional redirect URL after confirmation (defaults to frontend)
        session: Database session dependency
    """
    from fastapi.responses import RedirectResponse
    
    try:
        if not token:
            # If no token in query params, redirect to frontend with error
            redirect_url = redirect_to or "http://localhost:3000"
            error_url = f"{redirect_url}#error=missing_token&error_description=Confirmation+token+not+found"
            return RedirectResponse(url=error_url)
        
        supabase = get_supabase_client()
        
        # Try to verify the token with Supabase
        # First try with just token (for OTP tokens)
        try:
            auth_response = supabase.auth.verify_otp({
                "token": token,
                "type": type,
            })
        except Exception as e:
            # If it fails, the token might need email or might be a JWT
            # For JWT tokens, we can try to set the session directly
            error_str = str(e).lower()
            if "email" in error_str or "phone" in error_str:
                # Token needs email - try to extract from token or redirect with error
                redirect_url = redirect_to or "http://localhost:3000"
                error_url = f"{redirect_url}#error=token_requires_email&error_description=Please+use+POST+/auth/confirm-email+with+email+parameter"
                return RedirectResponse(url=error_url)
            raise
        
        if not auth_response.user or not auth_response.session:
            # Token invalid or expired
            redirect_url = redirect_to or "http://localhost:3000"
            error_url = f"{redirect_url}#error=invalid_token&error_description=Confirmation+token+is+invalid+or+expired"
            return RedirectResponse(url=error_url)
        
        # Update user verification status in local database
        user_uuid = UUID(auth_response.user.id)
        from sqlalchemy import select as sql_select
        result = await session.execute(
            sql_select(User).where(User.id == user_uuid)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.is_verified = auth_response.user.email_confirmed_at is not None
            user.email_verified_at = auth_response.user.email_confirmed_at
        else:
            # Create user if doesn't exist
            new_user = User(
                id=user_uuid,
                email=auth_response.user.email or "",
                is_active=True,
                is_verified=auth_response.user.email_confirmed_at is not None,
                email_verified_at=auth_response.user.email_confirmed_at,
            )
            session.add(new_user)
            user = new_user
        
        await session.commit()
        await session.refresh(user)
        
        app_logger.info(f"Email confirmed via callback: {user.email} (ID: {user.id})")
        
        # Redirect to frontend with access token in URL fragment
        redirect_url = redirect_to or "http://localhost:3000"
        token_fragment = f"access_token={auth_response.session.access_token}&token_type=bearer&expires_in={auth_response.session.expires_in or 3600}"
        success_url = f"{redirect_url}#{token_fragment}"
        
        return RedirectResponse(url=success_url)
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        app_logger.error(f"Email confirmation callback failed: {e}")
        redirect_url = redirect_to or "http://localhost:3000"
        error_url = f"{redirect_url}#error=confirmation_failed&error_description={str(e).replace(' ', '+')}"
        return RedirectResponse(url=error_url)


@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_current_user(
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(require_auth),
):
    """Get current authenticated user information.
    
    Returns user profile information for the authenticated user from Supabase Auth.
    """
    try:
        authenticated_user_id = user_id
        
        # Find user by ID
        user_uuid = UUID(authenticated_user_id)
        from sqlalchemy import select as sql_select
        result = await session.execute(
            sql_select(User).where(User.id == user_uuid)
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

