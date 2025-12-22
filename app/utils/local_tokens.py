"""JWT token helpers for authentication."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config.settings import settings


def create_local_token(user_id: str, email: str) -> str:
    """Create a JWT access token.

    Args:
        user_id: User ID to encode in the token
        email: User email to encode in the token

    Returns:
        str: Encoded JWT token
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=settings.LOCAL_AUTH_TOKEN_EXP_SECONDS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": exp,
        "iat": now,
    }
    return jwt.encode(payload, settings.LOCAL_AUTH_SECRET, algorithm="HS256")


def decode_local_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded token payload

    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.LOCAL_AUTH_SECRET,
            algorithms=["HS256"],
        )
        return payload
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
