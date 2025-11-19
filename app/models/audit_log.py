"""Audit log model (WORM - Write Once Read Many)."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, JSON
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    """Immutable audit trail for compliance and security.
    
    WORM (Write Once Read Many) - This table is append-only.
    Updates and deletes are prevented at the database level via triggers.
    """
    
    __tablename__ = "audit_logs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL", index=True)
    action: str = Field(max_length=100, index=True)  # 'user.created', 'api.call', etc.
    resource_type: str | None = Field(default=None, max_length=50, index=True)
    resource_id: UUID | None = Field(default=None, index=True)
    ip_address: str | None = None
    user_agent: str | None = None
    request_method: str | None = Field(default=None, max_length=10)
    request_path: str | None = None
    status_code: int | None = None
    error_message: str | None = None
    # Use generic JSON so this model works on both Postgres and SQLite
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), index=True)
    )

