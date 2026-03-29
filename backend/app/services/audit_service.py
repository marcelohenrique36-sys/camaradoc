import json
import logging
from typing import Any

from fastapi import Request
from sqlmodel import Session

from app.api.deps import resolve_user_role
from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


def get_request_ip(request: Request | None) -> str | None:
    if request is None:
        return None

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host
    return None


def _safe_details(details: dict[str, Any] | None) -> str | None:
    if not details:
        return None
    try:
        return json.dumps(details, ensure_ascii=False)[:4000]
    except Exception:
        return None


def log_audit_event(
    session: Session,
    *,
    action: str,
    entity_type: str,
    user: User | None,
    entity_id: str | None = None,
    request: Request | None = None,
    details: dict[str, Any] | None = None,
):
    try:
        entry = AuditLog(
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            user_role=resolve_user_role(user) if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=get_request_ip(request),
            details=_safe_details(details),
        )
        session.add(entry)
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.warning("Nao foi possivel gravar audit_log: %s", exc)
