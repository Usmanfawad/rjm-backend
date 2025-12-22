"""Script to seed admin user into the database."""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import select

from app.db.db import init_db, close_db, db_session
from app.models.user import User
from app.utils.passwords import hash_password


async def seed_admin_user():
    """Create the admin user if it doesn't exist."""

    # Admin user credentials
    ADMIN_EMAIL = "admin@admin.com"
    ADMIN_PASSWORD = "Password123!"
    ADMIN_FULL_NAME = "Admin User"
    ADMIN_USERNAME = "admin"

    # Initialize database
    await init_db()

    async with db_session() as session:
        try:
            # Check if admin user already exists
            result = await session.execute(
                select(User).where(User.email == ADMIN_EMAIL)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"Admin user already exists: {ADMIN_EMAIL}")
                print(f"User ID: {existing_user.id}")
                return existing_user

            # Create admin user
            admin_user = User(
                id=uuid4(),
                email=ADMIN_EMAIL,
                username=ADMIN_USERNAME,
                full_name=ADMIN_FULL_NAME,
                hashed_password=hash_password(ADMIN_PASSWORD),
                is_active=True,
                is_verified=True,
                email_verified_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)

            print("=" * 50)
            print("Admin user created successfully!")
            print("=" * 50)
            print(f"Email: {ADMIN_EMAIL}")
            print(f"Password: {ADMIN_PASSWORD}")
            print(f"User ID: {admin_user.id}")
            print("=" * 50)

            return admin_user

        except Exception as e:
            await session.rollback()
            print(f"Error creating admin user: {e}")
            raise

    # Close database connection
    await close_db()


async def main():
    """Main entry point."""
    print("Seeding admin user...")
    await seed_admin_user()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
