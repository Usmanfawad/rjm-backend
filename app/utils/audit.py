"""Audit logging utility for WORM (Write Once Read Many) audit trail."""

from typing import Optional
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def create_audit_log(
    session: AsyncSession,
    action: str,
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID | str | int] = None,
    request: Optional[Request] = None,
    status_code: Optional[int] = None,
    error_message: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AuditLog:
    """Create an audit log entry (WORM - Write Once Read Many).
    
    Args:
        session: Database session
        action: Action name (e.g., 'user.created', 'api.call', 'rjm_document.created')
        user_id: User ID who performed the action (if authenticated)
        resource_type: Type of resource affected (e.g., 'user', 'rjm_document')
        resource_id: ID of the resource affected
        request: FastAPI Request object (for IP, user agent, etc.)
        status_code: HTTP status code
        error_message: Error message if action failed
        metadata: Additional metadata as dict (stored in JSONB)
    
    Returns:
        Created AuditLog instance
    """
    # Extract request information if provided
    ip_address = None
    user_agent = None
    request_method = None
    request_path = None
    
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        request_method = request.method
        request_path = str(request.url.path)
    
    # Convert resource_id to UUID if it's a string/int (for non-UUID resources, store in metadata)
    audit_resource_id = None
    if resource_id:
        if isinstance(resource_id, UUID):
            audit_resource_id = resource_id
        elif isinstance(resource_id, str):
            try:
                audit_resource_id = UUID(resource_id)
            except ValueError:
                # Not a valid UUID string, store in metadata instead
                if metadata is None:
                    metadata = {}
                metadata["resource_id"] = resource_id
        elif isinstance(resource_id, int):
            # Integer IDs can't be stored in UUID field, store in metadata
            if metadata is None:
                metadata = {}
            metadata["resource_id"] = resource_id
    
    # Create audit log entry
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=audit_resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_method=request_method,
        request_path=request_path,
        status_code=status_code,
        error_message=error_message,
        metadata_json=metadata or {},
    )
    
    session.add(audit_log)
    # Note: Don't commit here - let the caller commit
    # This allows audit logs to be part of the same transaction
    
    return audit_log

