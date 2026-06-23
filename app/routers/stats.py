from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.dependencies import get_current_user, require_any_staff, resolve_list_county
from app.models.user import User
from app.services.stats_service import get_overview_stats

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/overview")
def overview(
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    effective_county = resolve_list_county(current_user, county)
    return get_overview_stats(db, effective_county)
