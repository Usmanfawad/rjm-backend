"""
Server-side session store for MIRA chat.

This module manages conversation state persistence so clients don't have to
track all state themselves. Sessions are keyed by a UUID that the server
returns on first interaction.

Features:
- In-memory session storage with TTL expiration
- Stores brand, brief, conversation state, category, and reasoning context
- Thread-safe session access
- Automatic cleanup of expired sessions
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from app.config.logger import app_logger


# Session TTL in minutes (default 60 minutes)
SESSION_TTL_MINUTES = 60

# Maximum sessions to keep in memory
MAX_SESSIONS = 10000


@dataclass
class SessionState:
    """
    Complete session state for a MIRA conversation.

    Tracks:
    - Brand and brief information
    - Current conversation state
    - Detected user mode
    - Category (inferred or explicit)
    - Reasoning context from the Reasoning Engine
    - Conversation history for context
    - Generated program summary
    - Conversational phase (EXPERIENCE → REASONING → PACKAGING → ACTIVATION)
    """
    # Core conversation memory
    brand_name: Optional[str] = None
    brief: Optional[str] = None
    category: Optional[str] = None

    # Behavioral state
    current_state: str = "STATE_GREETING"
    mode_hint: Optional[str] = None

    # Conversational phase tracking (per Ingredient Canon flow)
    # EXPERIENCE: Learning about brand, brief, objectives
    # REASONING: Understanding category, funnel, strategy
    # PACKAGING: Generating persona program
    # ACTIVATION: Creating activation plan
    conversational_phase: str = "EXPERIENCE"
    experience_complete: bool = False
    reasoning_complete: bool = False
    packaging_complete: bool = False
    activation_complete: bool = False

    # Reasoning context (from Reasoning Engine)
    funnel_stage: Optional[str] = None
    platform_path: Optional[str] = None
    budget_window: Optional[str] = None
    performance_path: Optional[str] = None
    media_mix: Optional[Dict[str, str]] = None

    # Activation state
    activation_plan_generated: bool = False
    program_generated: bool = False
    activation_shown: bool = False

    # Generated program summary (for context in later turns)
    program_summary: Optional[str] = None

    # Conversation history (last N messages for context)
    # Each entry: {"role": "user"|"assistant", "content": str}
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    # Session metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turn_count: int = 0

    # UI state
    last_closing_idx: int = 0

    # Conversation summary (for context retention)
    conversation_summary: Optional[str] = None
    key_points: List[str] = field(default_factory=list)

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
        self.turn_count += 1

    def is_expired(self, ttl_minutes: int = SESSION_TTL_MINUTES) -> bool:
        """Check if session has expired."""
        expiry = self.last_activity + timedelta(minutes=ttl_minutes)
        return datetime.now(timezone.utc) > expiry


class SessionStore:
    """
    Thread-safe session store with automatic expiration cleanup.
    """

    def __init__(self, ttl_minutes: int = SESSION_TTL_MINUTES, max_sessions: int = MAX_SESSIONS):
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.RLock()
        self._ttl_minutes = ttl_minutes
        self._max_sessions = max_sessions

    def create_session(self) -> str:
        """Create a new session and return its ID."""
        with self._lock:
            # Cleanup expired sessions first if we're at capacity
            if len(self._sessions) >= self._max_sessions:
                self._cleanup_expired()

            # If still at capacity, remove oldest sessions
            if len(self._sessions) >= self._max_sessions:
                self._remove_oldest(count=100)

            sid = str(uuid.uuid4())
            self._sessions[sid] = SessionState()
            app_logger.debug(f"Created new session: {sid}")
            return sid

    def get_session(self, session_id: Optional[str]) -> tuple[str, SessionState]:
        """
        Get or create a session.

        Returns tuple of (session_id, SessionState).
        If session_id is None or not found, creates a new session.
        """
        with self._lock:
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if not session.is_expired(self._ttl_minutes):
                    session.touch()
                    return session_id, session
                else:
                    # Session expired, remove it
                    del self._sessions[session_id]
                    app_logger.debug(f"Session expired and removed: {session_id}")

            # Create new session
            sid = self.create_session()
            return sid, self._sessions[sid]

    def update_session(self, session_id: str, **kwargs) -> None:
        """
        Update session state with provided values.

        Only updates fields that exist on SessionState and have non-None values.
        """
        with self._lock:
            state = self._sessions.get(session_id)
            if not state:
                state = SessionState()
                self._sessions[session_id] = state

            for key, value in kwargs.items():
                if hasattr(state, key) and value is not None:
                    setattr(state, key, value)

            state.touch()

    def add_key_point(self, session_id: str, point: str) -> None:
        """Add a key point to the conversation summary."""
        with self._lock:
            state = self._sessions.get(session_id)
            if state and point:
                state.key_points.append(point)
                # Keep only last 10 key points
                if len(state.key_points) > 10:
                    state.key_points = state.key_points[-10:]

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of session state for debugging/logging."""
        with self._lock:
            state = self._sessions.get(session_id)
            if not state:
                return {"error": "Session not found"}

            return {
                "session_id": session_id,
                "brand_name": state.brand_name,
                "brief": state.brief[:50] + "..." if state.brief and len(state.brief) > 50 else state.brief,
                "category": state.category,
                "current_state": state.current_state,
                "mode_hint": state.mode_hint,
                "funnel_stage": state.funnel_stage,
                "platform_path": state.platform_path,
                "program_generated": state.program_generated,
                "activation_plan_generated": state.activation_plan_generated,
                "turn_count": state.turn_count,
                "created_at": state.created_at.isoformat(),
                "last_activity": state.last_activity.isoformat(),
            }

    def _cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        removed = 0
        expired_ids = [
            sid for sid, state in self._sessions.items()
            if state.is_expired(self._ttl_minutes)
        ]
        for sid in expired_ids:
            del self._sessions[sid]
            removed += 1

        if removed:
            app_logger.debug(f"Cleaned up {removed} expired sessions")
        return removed

    def _remove_oldest(self, count: int = 100) -> None:
        """Remove the oldest sessions by last_activity."""
        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda x: x[1].last_activity
        )
        for sid, _ in sorted_sessions[:count]:
            del self._sessions[sid]
        app_logger.debug(f"Removed {count} oldest sessions")

    @property
    def session_count(self) -> int:
        """Get current number of active sessions."""
        with self._lock:
            return len(self._sessions)


# Global session store instance
_store = SessionStore()


def create_session() -> str:
    """Create a new session and return its ID."""
    return _store.create_session()


def get_session(session_id: Optional[str]) -> tuple[str, SessionState]:
    """Get or create a session. Returns (session_id, SessionState)."""
    return _store.get_session(session_id)


def update_session(session_id: str, **kwargs) -> None:
    """Update session state with provided values."""
    _store.update_session(session_id, **kwargs)


def add_key_point(session_id: str, point: str) -> None:
    """Add a key point to the conversation summary."""
    _store.add_key_point(session_id, point)


def add_message_to_history(session_id: str, role: str, content: str, max_messages: int = 20) -> None:
    """
    Add a message to the conversation history.

    Args:
        session_id: The session ID
        role: "user" or "assistant"
        content: The message content
        max_messages: Maximum messages to keep (default 20 = 10 turns)
    """
    with _store._lock:
        state = _store._sessions.get(session_id)
        if state:
            state.conversation_history.append({"role": role, "content": content})
            # Keep only last N messages
            if len(state.conversation_history) > max_messages:
                state.conversation_history = state.conversation_history[-max_messages:]


def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """Get the conversation history for a session."""
    with _store._lock:
        state = _store._sessions.get(session_id)
        if state:
            return state.conversation_history.copy()
        return []


def set_program_summary(session_id: str, summary: str) -> None:
    """Store the generated program summary for context in later turns."""
    _store.update_session(session_id, program_summary=summary, program_generated=True)


def get_program_summary(session_id: str) -> Optional[str]:
    """Get the stored program summary."""
    with _store._lock:
        state = _store._sessions.get(session_id)
        if state:
            return state.program_summary
        return None


def get_session_summary(session_id: str) -> Dict[str, Any]:
    """Get a summary of session state for debugging/logging."""
    return _store.get_session_summary(session_id)


def get_session_count() -> int:
    """Get current number of active sessions."""
    return _store.session_count
