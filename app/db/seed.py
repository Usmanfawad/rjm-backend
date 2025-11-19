"""Database seed helpers."""

from datetime import datetime, timezone
import hashlib

from sqlmodel import select  # type: ignore[import]

from app.config.logger import app_logger
from app.models.user import User
from app.db.db import db_session
from app.utils.passwords import hash_password

SEED_EMAIL = "admin@test.com"
SEED_PASSWORD = "Password123!"


async def ensure_seed_admin_user() -> None:
    """Create the admin@test.com seed user if it doesn't exist."""
    try:
        async with db_session() as session:
            result = await session.execute(select(User).where(User.email == SEED_EMAIL))
            existing = result.scalar_one_or_none()
            if existing:
                return

            user = User(
                email=SEED_EMAIL,
                username="admin",
                full_name="Seed Admin",
                hashed_password=hash_password(SEED_PASSWORD),
                is_active=True,
                is_verified=True,
                email_verified_at=datetime.now(timezone.utc),
            )
            session.add(user)
            await session.commit()
            app_logger.info("Seeded default admin user: %s", SEED_EMAIL)
    except Exception:  # pragma: no cover - best effort logging
        app_logger.exception("Failed to seed admin user")


