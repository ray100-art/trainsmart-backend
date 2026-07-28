from fastapi import APIRouter, Depends, BackgroundTasks, Request, Query, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Literal

from app.database import get_db
from app.services.certificate_service import (
    issue_certificates, verify_certificate, sign_certificates, list_certificate_pipeline,
)
from app.services.legacy_certificate_service import import_legacy_csv, legacy_csv_template
from app.services.session_service import to_session_summary
from app.schemas.session import SessionOut, SessionSummary
from app.schemas.common import PaginatedResponse
from app.core.dependencies import require_national_admin, require_system_admin, require_any_staff, resolve_list_county
from app.core.rate_limit import check_verify_rate_limit
from app.lib.uploads import read_upload_text
from app.models.user import User

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get("/pipeline", response_model=PaginatedResponse[SessionSummary])
def certificate_pipeline(
    tab: Literal["all", "pending", "certified", "signed"] = Query("all"),
    county: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    effective_county = resolve_list_county(current_user, county)
    created_by = current_user.id if current_user.role == "ROLE_TRAINER" else None
    items, total = list_certificate_pipeline(
        db,
        tab=tab,
        county=effective_county,
        created_by=created_by,
        skip=skip,
        limit=limit,
    )
    reviewer_ids = {s.approved_by for s in items if s.approved_by} | {
        s.report_approved_by for s in items if s.report_approved_by
    }
    reviewer_map: dict[str, str] = {}
    if reviewer_ids:
        rows = db.query(User.id, User.full_name).filter(User.id.in_(reviewer_ids)).all()
        reviewer_map = {r.id: r.full_name for r in rows}
    summaries = [to_session_summary(db, s, reviewer_map) for s in items]
    return PaginatedResponse(items=summaries, total=total, skip=skip, limit=limit)


@router.patch("/sessions/{session_id}/issue", response_model=SessionOut)
def issue(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_national_admin),
):
    return issue_certificates(db, session_id, issued_by=current_user.id, background_tasks=background_tasks)


@router.patch("/sessions/{session_id}/sign", response_model=SessionOut)
def sign(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_national_admin),
):
    return sign_certificates(db, session_id, signed_by=current_user.id)


@router.get("/verify/{serial}")
def verify(
    serial: str,
    request: Request,
    era: Optional[Literal["pre_2018", "post_2018"]] = Query(None),
    db: Session = Depends(get_db),
):
    check_verify_rate_limit(request, db=db)
    payload = verify_certificate(db, serial, era=era)
    return JSONResponse(
        content=payload,
        headers={
            "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
        },
    )


@router.get("/legacy/import/template.csv")
def legacy_import_template(_current_user: User = Depends(require_system_admin)):
    return PlainTextResponse(
        content=legacy_csv_template(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="legacy-certificates-template.csv"'},
    )


@router.post("/legacy/import")
def import_legacy_certificates(
    file: UploadFile = File(...),
    skip_duplicates: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file.")

    text = read_upload_text(file)
    return import_legacy_csv(db, text, skip_duplicates=skip_duplicates)
