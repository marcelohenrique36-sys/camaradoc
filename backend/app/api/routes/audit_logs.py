from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.api.deps import require_admin
from app.core.database import get_session
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["Auditoria"])


@router.get("/", response_model=list[AuditLogOut])
def list_audit_logs(
    session: Session = Depends(get_session),
    user=Depends(require_admin),
    action: str | None = None,
    entity_type: str | None = None,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    statement = select(AuditLog)

    if action:
        statement = statement.where(AuditLog.action == action)
    if entity_type:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if user_id is not None:
        statement = statement.where(AuditLog.user_id == user_id)
    if date_from:
        statement = statement.where(AuditLog.created_at >= date_from)
    if date_to:
        statement = statement.where(AuditLog.created_at <= date_to)

    statement = statement.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    return session.exec(statement).all()
