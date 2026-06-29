from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import require_me_manager
from app.models.user import User
from app.services.audit_query_service import list_audit_logs

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_me_manager),
):
    items, total = list_audit_logs(
        db, limit=limit, offset=offset, action=action, entity_type=entity_type,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}
