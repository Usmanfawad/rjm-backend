"""Simple password hashing helpers for local/dev auth."""

import hashlib
import hmac


def hash_password(password: str) -> str:
    """Return a SHA256 hash for the given password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time comparison for password hashes."""
    return hmac.compare_digest(hash_password(password), hashed)


