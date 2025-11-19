"""Generic response models for consistent API responses."""

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

from app.config.settings import settings

T = TypeVar("T")


class ResponseMetadata(BaseModel):
    """Metadata included in all API responses."""
    
    app_name: str = Field(default=settings.APP_NAME)
    app_version: str = Field(default=settings.APP_VERSION)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "app_name": "RJM Backend Core",
                "app_version": "1.0.0",
                "timestamp": "2025-11-03T15:58:36Z",
            }
        }
    }


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response with data and metadata."""
    
    success: bool = Field(default=True)
    message: str = Field(default="Operation completed successfully")
    data: T
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {},
                "metadata": {
                    "app_name": "RJM Backend Core",
                    "app_version": "1.0.0",
                    "timestamp": "2025-11-03T15:58:36Z",
                },
            }
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response structure."""
    
    success: bool = Field(default=False)
    error: str
    detail: Optional[str] = None
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "error": "Resource not found",
                "detail": "The requested resource with id 123 was not found",
                "metadata": {
                    "app_name": "RJM Backend Core",
                    "app_version": "1.0.0",
                    "timestamp": "2025-11-03T15:58:36Z",
                },
            }
        }
    }


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    
    page: int = Field(ge=1, description="Current page number")
    limit: int = Field(ge=1, le=1000, description="Items per page")
    total: int = Field(ge=0, description="Total number of items")
    pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response with data and pagination metadata."""
    
    success: bool = Field(default=True)
    message: str = Field(default="Items retrieved successfully")
    data: List[T]
    pagination: PaginationMeta
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Items retrieved successfully",
                "data": [],
                "pagination": {
                    "page": 1,
                    "limit": 10,
                    "total": 100,
                    "pages": 10,
                    "has_next": True,
                    "has_prev": False,
                },
                "metadata": {
                    "app_name": "RJM Backend Core",
                    "app_version": "1.0.0",
                    "timestamp": "2025-11-03T15:58:36Z",
                },
            }
        }
    }


# Helper functions to create responses
def success_response(
    data: T,
    message: str = "Operation completed successfully",
    **kwargs: Any
) -> SuccessResponse[T]:
    """Create a success response."""
    return SuccessResponse(
        success=True,
        message=message,
        data=data,
        metadata=ResponseMetadata(**kwargs) if kwargs else ResponseMetadata()
    )


def error_response(
    error: str,
    detail: Optional[str] = None,
    **kwargs: Any
) -> ErrorResponse:
    """Create an error response."""
    return ErrorResponse(
        success=False,
        error=error,
        detail=detail,
        metadata=ResponseMetadata(**kwargs) if kwargs else ResponseMetadata()
    )


def paginated_response(
    data: List[T],
    page: int,
    limit: int,
    total: int,
    message: str = "Items retrieved successfully",
    **kwargs: Any
) -> PaginatedResponse[T]:
    """Create a paginated response."""
    pages = (total + limit - 1) // limit if total > 0 else 0
    
    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        ),
        metadata=ResponseMetadata(**kwargs) if kwargs else ResponseMetadata()
    )

