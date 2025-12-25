"""Authentication utilities and dependency injection."""

from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.logger import app_logger
from app.config.settings import settings
from app.utils.local_tokens import decode_local_token

# HTTP Bearer token security scheme
security_scheme = HTTPBearer(
    scheme_name="Bearer",
    description="Bearer token authentication",
    auto_error=False,  # We'll handle errors manually for better control
)


async def get_auth_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
) -> str:
    """Extract and validate Bearer token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials from Security dependency

    Returns:
        str: The authentication token

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


async def verify_token(token: str = Depends(get_auth_token)) -> dict:
    """Verify and decode JWT authentication token.

    Args:
        token: Authentication token from get_auth_token dependency

    Returns:
        dict: Decoded token payload with user information (user_id, email, etc.)

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = decode_local_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "user_id": user_id,
        "email": email,
        "token": token,
    }


async def get_current_user_id(
    token_payload: dict = Depends(verify_token),
) -> Optional[str]:
    """Get current user ID from authenticated token.

    Args:
        token_payload: Decoded token payload from verify_token

    Returns:
        str: Current user ID (UUID as string) or None if not found

    Raises:
        HTTPException: If user is not authenticated or user not found
    """
    user_id = token_payload.get("user_id") or token_payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user identifier",
        )

    return str(user_id) if user_id else None


async def require_auth(
    user_id: Optional[str] = Depends(get_current_user_id),
) -> str:
    """Dependency that requires authentication (user_id must be present).

    Use this for endpoints that require a logged-in user.

    Args:
        user_id: User ID from get_current_user_id

    Returns:
        str: Authenticated user ID

    Raises:
        HTTPException: If user is not authenticated
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


# Convenience aliases for cleaner imports
GetAuthToken = Depends(get_auth_token)
GetCurrentUserId = Depends(get_current_user_id)
RequireAuth = Depends(require_auth)
