from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def list_audit_logs(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    entity_type: str | None = None,
) -> tuple[list[dict], int]:
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)

    total = q.count()
    rows = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    user_ids = {r.user_id for r in rows if r.user_id}
    user_map: dict[str, str] = {}
    if user_ids:
        for uid, name in db.query(User.id, User.full_name).filter(User.id.in_(user_ids)).all():
            user_map[uid] = name

    return [
        {
            "id": r.id,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "detail": r.detail,
            "user_id": r.user_id,
            "user_name": user_map.get(r.user_id) if r.user_id else None,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ], total
