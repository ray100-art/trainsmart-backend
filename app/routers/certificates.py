from fastapi import APIRouter, Depends, BackgroundTasks, Request, Query, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional, Literal

from app.database import get_db
from app.services.certificate_service import issue_certificates, verify_certificate
from app.services.legacy_certificate_service import import_legacy_csv, legacy_csv_template
from app.schemas.session import SessionOut
from app.core.dependencies import require_national_admin, require_system_admin
from app.core.rate_limit import check_verify_rate_limit
from app.models.user import User

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.patch("/sessions/{session_id}/issue", response_model=SessionOut)
def issue(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_national_admin),
):
    return issue_certificates(db, session_id, issued_by=current_user.id, background_tasks=background_tasks)


@router.get("/verify/{serial}")
def verify(
    serial: str,
    request: Request,
    era: Optional[Literal["pre_2018", "post_2018"]] = Query(None),
    db: Session = Depends(get_db),
):
    check_verify_rate_limit(request, db=db)
    return verify_certificate(db, serial, era=era)


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

    raw = file.file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    return import_legacy_csv(db, text, skip_duplicates=skip_duplicates)
