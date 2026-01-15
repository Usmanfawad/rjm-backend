"""Models module - imports all models for SQLModel registration."""

# Import all models so SQLModel can register them
from app.models.test_item import TestItem
from app.models.user import User
from app.models.user_connector import UserConnector
from app.models.audit_log import AuditLog
from app.models.rjm_document import RJMDocument
from app.models.persona_generation import PersonaGeneration
from app.models.chat_session import ChatSession, ChatMessage

__all__ = [
    "TestItem",
    "User",
    "UserConnector",
    "AuditLog",
    "RJMDocument",
    "PersonaGeneration",
    "ChatSession",
    "ChatMessage",
]
