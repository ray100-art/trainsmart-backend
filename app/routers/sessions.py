from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas.session import (
    SessionCreate, SessionUpdate, SessionOut,
    ApproveSessionRequest, RejectSessionRequest,
    TrainingReportSchema, RejectReportRequest,
)
from app.services import session_service
from app.core.dependencies import (
    get_current_user, require_trainer,
    require_county_officer, require_national_admin, require_any_staff,
)
from app.models.user import User

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    return session_service.get_all_sessions(db, county)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    return session_service.get_session_or_404(db, session_id)


@router.post("", response_model=SessionOut, status_code=201)
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    return session_service.create_session(db, data, current_user.id)


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: str,
    data: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    if s.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session and cannot modify it.",
        )
    return session_service.update_session(db, session_id, data)


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    if s.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session and cannot delete it.",
        )
    session_service.delete_session(db, session_id)


@router.patch("/{session_id}/approve", response_model=SessionOut)
def approve_session(
    session_id: str,
    data: ApproveSessionRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_county_officer),
):
    return session_service.approve_session(db, session_id, data.approved_by)


@router.patch("/{session_id}/reject", response_model=SessionOut)
def reject_session(
    session_id: str,
    data: RejectSessionRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_county_officer),
):
    return session_service.reject_session(db, session_id, data.note, data.approved_by)


@router.patch("/{session_id}/report", response_model=SessionOut)
def submit_report(
    session_id: str,
    data: TrainingReportSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    if s.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session and cannot submit its report.",
        )
    return session_service.submit_report(db, session_id, data)


@router.patch("/{session_id}/report/approve", response_model=SessionOut)
def approve_report(
    session_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_county_officer),
):
    return session_service.approve_report(db, session_id)


@router.patch("/{session_id}/report/reject", response_model=SessionOut)
def reject_report(
    session_id: str,
    data: RejectReportRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_county_officer),
):
    return session_service.reject_report(db, session_id, data.note)