"""Supabase client initialization and utilities."""

from typing import Optional

from supabase import create_client, Client

from app.config.settings import settings
from app.config.logger import app_logger

_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client with anon key.
    
    Returns:
        Client: Supabase client instance for user operations
        
    Raises:
        ValueError: If Supabase URL or anon key is not configured
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError(
            "Supabase URL and ANON_KEY must be configured. "
            "Set SUPABASE_URL and SUPABASE_ANON_KEY in .env"
        )
    
    try:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        app_logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        app_logger.error(f"Failed to initialize Supabase client: {e}")
        raise


def get_supabase_admin_client() -> Client:
    """Get or create Supabase admin client with service role key.
    
    Use this for admin operations that require elevated privileges.
    
    Returns:
        Client: Supabase admin client instance
        
    Raises:
        ValueError: If Supabase URL or service role key is not configured
    """
    global _supabase_admin_client
    
    if _supabase_admin_client is not None:
        return _supabase_admin_client
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError(
            "Supabase URL and SERVICE_ROLE_KEY must be configured for admin operations. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
        )
    
    try:
        _supabase_admin_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        app_logger.info("Supabase admin client initialized successfully")
        return _supabase_admin_client
    except Exception as e:
        app_logger.error(f"Failed to initialize Supabase admin client: {e}")
        raise

