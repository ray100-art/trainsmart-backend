import uuid
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    *,
    user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> None:
    entry = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
