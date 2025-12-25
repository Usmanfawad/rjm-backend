"""Database seed helpers using Supabase REST API."""

from datetime import datetime, timezone

from app.config.logger import app_logger
from app.db.supabase_db import get_user_by_email, create_user
from app.utils.passwords import hash_password

SEED_EMAIL = "admin@test.com"
SEED_PASSWORD = "Password123!"


async def ensure_seed_admin_user() -> None:
    """Create the admin@test.com seed user if it doesn't exist.
    
    Uses Supabase REST API (HTTPS port 443) for database operations.
    """
    try:
        # Check if user already exists via Supabase REST API
        existing = await get_user_by_email(SEED_EMAIL)
        if existing:
            app_logger.info("Seed admin user already exists: %s", SEED_EMAIL)
            return

        # Create seed admin user via Supabase REST API
        await create_user(
            email=SEED_EMAIL,
            username="admin",
            full_name="Seed Admin",
            hashed_password=hash_password(SEED_PASSWORD),
            is_active=True,
            is_verified=True,
            role="admin",
        )
        app_logger.info("Seeded default admin user via Supabase REST API: %s", SEED_EMAIL)
        
    except Exception as e:
        app_logger.warning(f"Failed to seed admin user (this is OK on first run): {e}")
        app_logger.info("Make sure the 'users' table exists in Supabase. See supabase/schema.sql")
