"""Chat Session and Message models for persisting MIRA conversations."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


class ChatSession(SQLModel, table=True):
    """Model to store MIRA chat sessions."""
    
    __tablename__ = "chat_sessions"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True, description="User who owns this session")
    
    # Session metadata
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Auto-generated title from first message or brand name"
    )
    brand_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Brand name if captured during conversation"
    )
    brief: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Campaign brief if captured during conversation"
    )
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Detected advertising category"
    )
    
    # Session state for resumption
    current_state: str = Field(
        default="STATE_GREETING",
        max_length=100,
        description="Current behavioral state for resumption"
    )
    session_data: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="JSON serialized session state data for full resumption"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    
    # Message count for quick display
    message_count: int = Field(default=0, description="Number of messages in this session")


class ChatMessage(SQLModel, table=True):
    """Model to store individual chat messages."""
    
    __tablename__ = "chat_messages"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(index=True, description="Parent chat session")
    user_id: UUID = Field(index=True, description="User who owns this message")
    
    # Message content
    role: str = Field(
        max_length=20,
        description="Message role: 'user' or 'assistant'"
    )
    content: str = Field(
        sa_column=Column(Text),
        description="Message content"
    )
    
    # Optional metadata
    state_before: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Behavioral state before this message"
    )
    state_after: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Behavioral state after this message"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

