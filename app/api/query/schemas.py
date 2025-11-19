"""Request and response schemas for query API endpoints."""

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Query endpoints
class QueryRequest(BaseModel):
    """Request schema for POST /v1/query."""
    
    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    include_metadata: bool = Field(default=True, description="Include metadata in results")
    filters: Optional[dict] = Field(default=None, description="Optional filters for search")
    
    model_config = {"json_schema_extra": {"example": {
        "query": "Find emails about project deadlines",
        "top_k": 5,
        "include_metadata": True,
        "filters": {"source": "gmail", "date_range": "last_month"}
    }}}


class QueryResult(BaseModel):
    """Single query result item."""
    
    id: str = Field(description="Result ID")
    content: str = Field(description="Result content/text")
    source: str = Field(description="Source (e.g., 'gmail', 'drive', 'onedrive')")
    score: float = Field(description="Similarity score (0-1)")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")
    
    model_config = {"json_schema_extra": {"example": {
        "id": "chunk_123",
        "content": "Email content about project deadlines...",
        "source": "gmail",
        "score": 0.89,
        "metadata": {"email_id": "msg_456", "date": "2025-10-15"}
    }}}


class QueryResponse(BaseModel):
    """Response schema for query endpoints."""
    
    results: List[QueryResult] = Field(default_factory=list, description="Search results")
    query: str = Field(description="Original query")
    total_results: int = Field(default=0, description="Total number of matching results")
    processing_time_ms: float = Field(description="Query processing time in milliseconds")
    
    model_config = {"json_schema_extra": {"example": {
        "results": [],
        "query": "Find emails about project deadlines",
        "total_results": 12,
        "processing_time_ms": 234.5
    }}}


class DeepSearchRequest(BaseModel):
    """Request schema for POST /v1/deep_search."""
    
    query: str = Field(..., min_length=1, description="Search query text")
    sources: Optional[List[str]] = Field(default=None, description="Specific sources to search (e.g., ['gmail', 'drive'])")
    top_k_per_source: int = Field(default=3, ge=1, le=10, description="Results per source")
    include_metadata: bool = Field(default=True, description="Include metadata in results")
    filters: Optional[dict] = Field(default=None, description="Optional filters for search")
    
    model_config = {"json_schema_extra": {"example": {
        "query": "Documents about financial planning",
        "sources": ["gmail", "drive", "onedrive"],
        "top_k_per_source": 3,
        "include_metadata": True
    }}}


class DeepSearchResponse(BaseModel):
    """Response schema for deep search."""
    
    results_by_source: Dict[str, List[QueryResult]] = Field(description="Results grouped by source")
    query: str = Field(description="Original query")
    total_results: int = Field(default=0, description="Total number of matching results")
    sources_searched: List[str] = Field(default_factory=list, description="Sources that were searched")
    processing_time_ms: float = Field(description="Query processing time in milliseconds")
    
    model_config = {"json_schema_extra": {"example": {
        "results_by_source": {
            "gmail": [],
            "drive": []
        },
        "query": "Documents about financial planning",
        "total_results": 15,
        "sources_searched": ["gmail", "drive", "onedrive"],
        "processing_time_ms": 456.7
    }}}


# Data deletion endpoint
class DeleteDataResponse(BaseModel):
    """Response schema for DELETE /v1/delete_my_data."""
    
    status: str = Field(default="deleted", description="Deletion status")
    deleted_resources: List[str] = Field(description="List of resource types deleted")
    audit_id: str = Field(description="Audit log ID for deletion receipt")
    timestamp: str = Field(description="ISO timestamp of deletion")
    
    model_config = {"json_schema_extra": {"example": {
        "status": "deleted",
        "deleted_resources": ["embeddings", "metadata", "tokens"],
        "audit_id": "del_01J9Z3R4A2",
        "timestamp": "2025-10-14T15:32:10Z"
    }}}


# Data export endpoint
class ExportDataResponse(BaseModel):
    """Response schema for GET /v1/export_my_data."""
    
    export_id: str = Field(description="Unique export job ID")
    status: str = Field(description="Export status (pending, processing, completed)")
    download_url: Optional[str] = Field(default=None, description="Download URL for ZIP file (when completed)")
    format: str = Field(default="zip", description="Export format (zip or jsonl)")
    expires_at: Optional[str] = Field(default=None, description="URL expiration timestamp")
    estimated_size_mb: Optional[float] = Field(default=None, description="Estimated export size")
    
    model_config = {"json_schema_extra": {"example": {
        "export_id": "exp_01J9Z3R4B3",
        "status": "completed",
        "download_url": "https://api.corpusiq.io/v1/exports/exp_01J9Z3R4B3/download",
        "format": "zip",
        "expires_at": "2025-11-10T15:32:10Z",
        "estimated_size_mb": 2.5
    }}}

