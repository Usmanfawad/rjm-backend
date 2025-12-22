"""Test item model."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4, UUID

from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


# SQLModel for database
class TestItem(SQLModel, table=True):
    """Test item database model."""
    
    __tablename__ = "test_items"
    
    id: int = Field(primary_key=True)
    name: str = Field(max_length=255)
    description: str | None = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )


# Pydantic models for API
class TestItemCreate(BaseModel):
    """Schema for creating a test item."""
    name: str = PydanticField(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: bool = PydanticField(True)


class TestItemUpdate(BaseModel):
    """Schema for updating a test item."""
    name: Optional[str] = PydanticField(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TestItemResponse(BaseModel):
    """Schema for test item response."""
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
