from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import (
    require_any_staff,
    require_me_manager,
    resolve_list_county,
)
from app.models.user import User
from app.services.stats_service import get_overview_stats, get_analytics, export_sessions_csv, export_participants_csv

router = APIRouter(prefix="/stats", tags=["Statistics"])


def _trainer_scope(user: User) -> tuple[str | None, str | None]:
    if user.role == "ROLE_TRAINER":
        return user.county, user.id
    return None, None


@router.get("/overview")
def overview(
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    trainer_county, created_by = _trainer_scope(current_user)
    if trainer_county:
        effective_county = trainer_county
    else:
        effective_county = resolve_list_county(current_user, county)
    return get_overview_stats(db, effective_county, created_by=created_by)


@router.get("/analytics")
def analytics(
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_me_manager),
):
    effective_county = resolve_list_county(current_user, county)
    overview = get_overview_stats(db, effective_county)
    detail = get_analytics(db, effective_county)
    return {**overview, **detail}


@router.get("/export/sessions.csv")
def export_sessions(
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_me_manager),
):
    effective_county = resolve_list_county(current_user, county)
    csv_data = export_sessions_csv(db, effective_county)
    filename = f"trainsmart-sessions-{date.today().isoformat()}.csv"
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/participants.csv")
def export_participants(
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_me_manager),
):
    effective_county = resolve_list_county(current_user, county)
    csv_data = export_participants_csv(db, effective_county)
    filename = f"trainsmart-participants-{date.today().isoformat()}.csv"
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
