"""Supabase REST API database operations.

This module provides database operations using Supabase's REST API (HTTPS port 443),
which works on all hosting platforms including those without IPv6 support.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from app.utils.supabase_client import get_supabase_admin_client
from app.config.logger import app_logger


# ============================================
# User Operations
# ============================================

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email address."""
    try:
        client = get_supabase_admin_client()
        response = client.table('users').select('*').eq('email', email).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        app_logger.error(f"Failed to get user by email: {e}")
        raise


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    try:
        client = get_supabase_admin_client()
        response = client.table('users').select('*').eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        app_logger.error(f"Failed to get user by ID: {e}")
        raise


async def create_user(
    email: str,
    username: Optional[str],
    full_name: Optional[str],
    hashed_password: str,
    is_active: bool = True,
    is_verified: bool = True,
    role: str = "user",
) -> Dict[str, Any]:
    """Create a new user."""
    try:
        client = get_supabase_admin_client()
        
        user_data = {
            "id": str(uuid4()),
            "email": email,
            "username": username,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "is_active": is_active,
            "is_verified": is_verified,
            "role": role,
            "email_verified_at": datetime.now(timezone.utc).isoformat() if is_verified else None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        response = client.table('users').insert(user_data).execute()
        
        if response.data and len(response.data) > 0:
            app_logger.info(f"User created via Supabase REST API: {email}")
            return response.data[0]
        
        raise Exception("Failed to create user - no data returned")
    except Exception as e:
        app_logger.error(f"Failed to create user: {e}")
        raise


async def update_user(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update user by ID."""
    try:
        client = get_supabase_admin_client()
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        response = client.table('users').update(updates).eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        app_logger.error(f"Failed to update user: {e}")
        raise


async def update_user_last_login(user_id: str) -> None:
    """Update user's last login timestamp."""
    try:
        await update_user(user_id, {
            "last_login_at": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        app_logger.error(f"Failed to update last login: {e}")
        # Don't raise - this is not critical


# ============================================
# Generic Table Operations
# ============================================

async def insert_record(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a record into any table."""
    try:
        client = get_supabase_admin_client()
        response = client.table(table).insert(data).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        raise Exception(f"Failed to insert into {table} - no data returned")
    except Exception as e:
        app_logger.error(f"Failed to insert into {table}: {e}")
        raise


async def get_records(
    table: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    order_by: Optional[str] = None,
    ascending: bool = True,
) -> List[Dict[str, Any]]:
    """Get records from any table with optional filters."""
    try:
        client = get_supabase_admin_client()
        query = client.table(table).select('*')
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        if order_by:
            query = query.order(order_by, desc=not ascending)
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        return response.data or []
    except Exception as e:
        app_logger.error(f"Failed to get records from {table}: {e}")
        raise


async def update_record(
    table: str,
    record_id: str,
    updates: Dict[str, Any],
    id_column: str = "id",
) -> Optional[Dict[str, Any]]:
    """Update a record in any table."""
    try:
        client = get_supabase_admin_client()
        response = client.table(table).update(updates).eq(id_column, record_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        app_logger.error(f"Failed to update record in {table}: {e}")
        raise


async def delete_record(table: str, record_id: str, id_column: str = "id") -> bool:
    """Delete a record from any table."""
    try:
        client = get_supabase_admin_client()
        response = client.table(table).delete().eq(id_column, record_id).execute()
        return True
    except Exception as e:
        app_logger.error(f"Failed to delete record from {table}: {e}")
        raise


# ============================================
# Health Check
# ============================================

async def ping_supabase() -> tuple[bool, str]:
    """Check if Supabase connection is healthy."""
    try:
        client = get_supabase_admin_client()
        # Try to query the users table (or any table)
        response = client.table('users').select('id').limit(1).execute()
        return True, "Supabase REST API connection healthy"
    except Exception as e:
        return False, f"Supabase connection failed: {str(e)}"

