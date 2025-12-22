"""Persona Generation model for storing generated persona programs."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


class PersonaGeneration(SQLModel, table=True):
    """Model to store persona program generations."""
    
    __tablename__ = "persona_generations"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True, description="User who generated this program")
    
    # Request details
    brand_name: str = Field(max_length=255, description="Brand name for the program")
    brief: str = Field(sa_column=Column(Text), description="Campaign brief")
    
    # Generated content
    program_text: str = Field(
        sa_column=Column(Text),
        description="Human-readable formatted program text"
    )
    program_json: str = Field(
        sa_column=Column(Text),
        description="JSON string of the structured program data"
    )
    
    # Metadata
    advertising_category: Optional[str] = Field(
        default=None, 
        max_length=100,
        description="Detected advertising category"
    )
    source: str = Field(
        default="generator",
        max_length=50,
        description="Source of generation: 'generator' or 'chat'"
    )
    session_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Chat session ID if generated via chat"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )

