from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.certificate_service import issue_certificates, verify_certificate
from app.schemas.session import SessionOut
from app.core.dependencies import require_national_admin

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.patch("/sessions/{session_id}/issue", response_model=SessionOut)
def issue(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _ = Depends(require_national_admin),
):
    return issue_certificates(db, session_id, background_tasks)


@router.get("/verify/{serial}")
def verify(serial: str, db: Session = Depends(get_db)):
    return verify_certificate(db, serial)