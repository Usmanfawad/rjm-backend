"""Chat persistence service for storing and retrieving MIRA conversations.

This module handles database operations for chat sessions and messages,
enabling users to view past conversations and resume them.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import uuid4

from app.config.logger import app_logger
from app.db.supabase_db import insert_record, get_records, update_record
from app.services.mira_session import update_session


async def create_chat_session(
    user_id: str,
    session_id: str,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new chat session in the database.
    
    Args:
        user_id: The user ID
        session_id: The in-memory session ID to associate
        title: Optional title for the session
        
    Returns:
        The created session record
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        session_data = {
            "id": session_id,  # Use the same ID as in-memory session
            "user_id": user_id,
            "title": title,
            "current_state": "STATE_GREETING",
            "message_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        
        result = await insert_record("chat_sessions", session_data)
        app_logger.debug(f"Created chat session {session_id} for user {user_id}")
        return result
    except Exception as e:
        app_logger.error(f"Failed to create chat session: {e}")
        raise


async def get_or_create_chat_session(
    user_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """Get existing chat session or create a new one.
    
    Args:
        user_id: The user ID
        session_id: The session ID
        
    Returns:
        The session record
    """
    try:
        # Try to get existing session
        sessions = await get_records(
            "chat_sessions",
            filters={"id": session_id, "user_id": user_id},
            limit=1,
        )
        
        if sessions:
            return sessions[0]
        
        # Create new session
        return await create_chat_session(user_id, session_id)
    except Exception as e:
        app_logger.error(f"Failed to get or create chat session: {e}")
        raise


async def save_chat_message(
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    state_before: Optional[str] = None,
    state_after: Optional[str] = None,
) -> Dict[str, Any]:
    """Save a chat message to the database.
    
    Args:
        session_id: The chat session ID
        user_id: The user ID
        role: Message role ('user' or 'assistant')
        content: Message content
        state_before: Behavioral state before this message
        state_after: Behavioral state after this message
        
    Returns:
        The created message record
    """
    try:
        message_data = {
            "id": str(uuid4()),
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "state_before": state_before,
            "state_after": state_after,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        result = await insert_record("chat_messages", message_data)
        app_logger.debug(f"Saved chat message for session {session_id}")
        return result
    except Exception as e:
        app_logger.error(f"Failed to save chat message: {e}")
        raise


async def update_chat_session(
    session_id: str,
    updates: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Update a chat session with new data.
    
    Args:
        session_id: The session ID
        updates: Dictionary of fields to update
        
    Returns:
        The updated session record or None
    """
    try:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await update_record("chat_sessions", session_id, updates)
        return result
    except Exception as e:
        app_logger.error(f"Failed to update chat session: {e}")
        raise


async def persist_chat_turn(
    session_id: str,
    user_id: str,
    user_message: str,
    assistant_reply: str,
    state_before: str,
    state_after: str,
    brand_name: Optional[str] = None,
    brief: Optional[str] = None,
    category: Optional[str] = None,
) -> None:
    """Persist a complete chat turn (user message + assistant reply).
    
    This is the main function called after each chat turn to save messages
    and update session state.
    
    Args:
        session_id: The chat session ID
        user_id: The user ID
        user_message: The user's message
        assistant_reply: MIRA's reply
        state_before: Behavioral state before this turn
        state_after: Behavioral state after this turn
        brand_name: Brand name if captured
        brief: Campaign brief if captured
        category: Detected category if captured
    """
    try:
        # Ensure session exists
        await get_or_create_chat_session(user_id, session_id)
        
        # Save user message
        await save_chat_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=user_message,
            state_before=state_before,
            state_after=state_before,  # User message doesn't change state
        )
        
        # Save assistant reply
        await save_chat_message(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=assistant_reply,
            state_before=state_before,
            state_after=state_after,
        )
        
        # Update session metadata
        session_updates: Dict[str, Any] = {
            "current_state": state_after,
        }
        
        # Update title from first user message if not set
        if user_message:
            # Generate title from first ~50 chars of first message or brand name
            title = brand_name if brand_name else user_message[:50].strip()
            if len(user_message) > 50 and not brand_name:
                title += "..."
            session_updates["title"] = title
        
        if brand_name:
            session_updates["brand_name"] = brand_name
        if brief:
            session_updates["brief"] = brief
        if category:
            session_updates["category"] = category
        
        # Increment message count by 2 (user + assistant)
        # We'll handle this with a raw update since Supabase doesn't support increment
        sessions = await get_records(
            "chat_sessions",
            filters={"id": session_id},
            limit=1,
        )
        if sessions:
            current_count = sessions[0].get("message_count", 0)
            session_updates["message_count"] = current_count + 2
        
        await update_chat_session(session_id, session_updates)
        
        app_logger.debug(f"Persisted chat turn for session {session_id}")
        
    except Exception as e:
        app_logger.warning(f"Failed to persist chat turn: {e}")
        # Don't raise - persistence failure shouldn't break the chat


async def get_user_chat_sessions(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Get all chat sessions for a user.
    
    Args:
        user_id: The user ID
        limit: Maximum number of sessions to return
        offset: Number of sessions to skip
        
    Returns:
        List of chat session records, newest first
    """
    try:
        sessions = await get_records(
            "chat_sessions",
            filters={"user_id": user_id},
            limit=limit,
            order_by="updated_at",
            ascending=False,
        )
        return sessions
    except Exception as e:
        app_logger.error(f"Failed to get user chat sessions: {e}")
        raise


async def get_chat_session_detail(
    session_id: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """Get a chat session with all its messages.
    
    Args:
        session_id: The session ID
        user_id: The user ID (for authorization)
        
    Returns:
        Session record with messages, or None if not found
    """
    try:
        # Get session
        sessions = await get_records(
            "chat_sessions",
            filters={"id": session_id, "user_id": user_id},
            limit=1,
        )
        
        if not sessions:
            return None
        
        session = sessions[0]
        
        # Get all messages for this session
        messages = await get_records(
            "chat_messages",
            filters={"session_id": session_id},
            order_by="created_at",
            ascending=True,
        )
        
        session["messages"] = messages
        return session
        
    except Exception as e:
        app_logger.error(f"Failed to get chat session detail: {e}")
        raise


async def restore_session_from_db(
    session_id: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """Restore in-memory session state from database.
    
    This is used when resuming a past conversation to restore
    the session state so the behavioral engine can continue properly.
    
    Args:
        session_id: The session ID to restore
        user_id: The user ID (for authorization)
        
    Returns:
        Session data including messages if found, None otherwise
    """
    try:
        session_data = await get_chat_session_detail(session_id, user_id)
        
        if not session_data:
            return None
        
        # Update in-memory session with restored state
        update_session(
            session_id,
            brand_name=session_data.get("brand_name"),
            brief=session_data.get("brief"),
            category=session_data.get("category"),
            current_state=session_data.get("current_state", "STATE_GREETING"),
        )
        
        # Restore conversation history to in-memory session
        messages = session_data.get("messages", [])
        from app.services.mira_session import add_message_to_history
        
        for msg in messages:
            add_message_to_history(
                session_id,
                role=msg["role"],
                content=msg["content"],
            )
        
        app_logger.info(f"Restored session {session_id} from database with {len(messages)} messages")
        return session_data
        
    except Exception as e:
        app_logger.error(f"Failed to restore session from database: {e}")
        raise


async def delete_chat_session(
    session_id: str,
    user_id: str,
) -> bool:
    """Delete a chat session and all its messages.
    
    Args:
        session_id: The session ID to delete
        user_id: The user ID (for authorization)
        
    Returns:
        True if deleted, False if not found
    """
    try:
        from app.db.supabase_db import delete_record
        
        # Verify ownership
        sessions = await get_records(
            "chat_sessions",
            filters={"id": session_id, "user_id": user_id},
            limit=1,
        )
        
        if not sessions:
            return False
        
        # Delete session (messages will cascade delete due to FK constraint)
        await delete_record("chat_sessions", session_id)
        app_logger.info(f"Deleted chat session {session_id}")
        return True
        
    except Exception as e:
        app_logger.error(f"Failed to delete chat session: {e}")
        raise

