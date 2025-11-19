"""User connector model for external API connections."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class UserConnector(SQLModel, table=True):
    """External service connection (OpenAI, Anthropic, etc.) per user."""
    
    __tablename__ = "user_connectors"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    connector_type: str = Field(max_length=50, index=True)  # 'openai', 'anthropic', etc.
    connector_name: str = Field(max_length=100)
    api_key_encrypted: str | None = None
    is_active: bool = Field(default=True, index=True)
    # Use generic JSON so the model works on both Postgres and SQLite
    config: dict = Field(default_factory=dict, sa_column=Column(JSON))
    last_used_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

