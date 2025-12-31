"""Database connection management using SQLModel with asyncpg."""

import ssl
from typing import AsyncGenerator, Optional
from urllib.parse import urlparse, urlunparse

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.config.settings import settings
from app.config.logger import app_logger

_engine: Optional[create_async_engine] = None
_session_maker: Optional[async_sessionmaker] = None


def get_db_url() -> str:
    """Get database URL for SQLAlchemy with asyncpg driver."""
    db_url = settings.effective_database_url
    if not db_url:
        raise ValueError("DATABASE_URL not configured")
    # SQLite or other non-Postgres URLs are returned as-is
    if db_url.startswith("sqlite"):
        return db_url

    # For Postgres URLs, normalize and strip sslmode (asyncpg handles SSL via connect_args)
    parsed = urlparse(db_url)
    query_parts = [p for p in parsed.query.split("&") if not p.startswith("sslmode=") and p]
    query = "&".join(query_parts)
    clean_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            query,
            parsed.fragment,
        )
    )

    # Convert to asyncpg driver
    if clean_url.startswith("postgresql://"):
        clean_url = clean_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif clean_url.startswith("postgres://"):
        clean_url = clean_url.replace("postgres://", "postgresql+asyncpg://", 1)

    return clean_url


async def init_db() -> None:
    """Initialize the database engine and create tables."""
    global _engine, _session_maker
    
    try:
        db_url = get_db_url()
        app_logger.info("Initializing database connection")

        connect_args = {}
        # SSL context for Supabase / Postgres (no certificate verification)
        if db_url.startswith("postgresql+asyncpg://"):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connect_args = {"ssl": ssl_context}

        # Async engine (Postgres with asyncpg or SQLite with aiosqlite)
        _engine = create_async_engine(
            db_url,
            echo=False,
            pool_size=20,
            max_overflow=0,
            connect_args=connect_args,
        )
        
        # Create session maker
        _session_maker = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Import all models to register them with SQLModel
        from app.models import (
            user,
            user_connector,
            audit_log,
            test_item,
            rjm_document,
            persona_generation,
            chat_session,
        )
        
        # Create all tables
        async with _engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        app_logger.info("Database initialized successfully")
        
    except ValueError:
        app_logger.warning("DATABASE_URL not set; database will not be initialized")
        app_logger.info("Set DATABASE_URL in .env or configure SUPABASE_DATABASE_* variables")
    except Exception as e:
        app_logger.error(f"Failed to initialize database: {e}")
        app_logger.error(f"Error type: {type(e).__name__}")
        app_logger.warning("=" * 60)
        app_logger.warning("DATABASE CONNECTION FAILED - Running in limited mode")
        app_logger.warning("SQLAlchemy features disabled. Supabase REST API still available.")
        app_logger.warning("To fix: Use Supabase Connection Pooler or deploy to IPv6-compatible host")
        app_logger.warning("=" * 60)
        # Don't raise - allow app to start without database


async def close_db() -> None:
    """Close the database engine."""
    global _engine, _session_maker
    
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_maker = None
        app_logger.info("Database connection closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session."""
    if not _session_maker:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. The server is running in limited mode. "
                   "Direct PostgreSQL connection failed (IPv6 not supported on this host). "
                   "Contact administrator to configure Supabase Connection Pooler."
        )
    
    async with _session_maker() as session:
        yield session


@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for internal background tasks."""
    if not _session_maker:
        raise RuntimeError(
            "Database not initialized. Direct PostgreSQL connection unavailable. "
            "Configure Supabase Connection Pooler or deploy to IPv6-compatible host."
        )
    
    async with _session_maker() as session:
        yield session


async def ping_database() -> tuple[bool, str]:
    """Run a lightweight health query against the database."""
    if not _engine or not _session_maker:
        return False, "Database not initialized"
    
    try:
        from sqlalchemy import text
        async with _session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            row = result.scalar()
            if row == 1:
                return True, "Database connection healthy"
            return False, f"Unexpected response: {row}"
    except Exception as e:
        return False, f"Database query failed: {str(e)}"
