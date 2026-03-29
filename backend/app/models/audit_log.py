from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    user_email: Optional[str] = Field(default=None, index=True)
    user_role: Optional[str] = Field(default=None, index=True)
    action: str = Field(index=True)
    entity_type: str = Field(index=True)
    entity_id: Optional[str] = Field(default=None, index=True)
    ip_address: Optional[str] = Field(default=None)
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
