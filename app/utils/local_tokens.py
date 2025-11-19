"""Local JWT helpers for dev auth."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config.settings import settings


def create_local_token(user_id: str, email: str) -> str:
    """Create a short-lived JWT for local auth fallback."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=settings.LOCAL_AUTH_TOKEN_EXP_SECONDS)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "local",
        "exp": exp,
        "iat": now,
    }
    return jwt.encode(payload, settings.LOCAL_AUTH_SECRET, algorithm="HS256")


def decode_local_token(token: str) -> dict:
    """Decode a locally issued JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.LOCAL_AUTH_SECRET,
            algorithms=["HS256"],
        )
        if payload.get("type") != "local":
            raise JWTError("Invalid token type")
        return payload
    except JWTError as exc:
        raise ValueError(f"Invalid local token: {exc}") from exc


