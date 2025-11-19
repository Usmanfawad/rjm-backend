"""Model representing RJM document sync metadata."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class RJMDocument(SQLModel, table=True):
    """Tracks RJM document sync state between filesystem, DB, and vector store."""

    __tablename__ = "rjm_documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    file_name: str = Field(max_length=255)
    relative_path: str = Field(max_length=512, unique=True, index=True)
    content_hash: str = Field(max_length=128, index=True)
    chunk_size: int = Field(default=800, ge=1)
    chunk_overlap: int = Field(default=100, ge=0)
    chunk_count: int = Field(default=0, ge=0)
    last_synced_at: datetime | None = None
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )


