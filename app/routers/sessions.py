from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas.session import (
    SessionCreate, SessionUpdate, SessionOut,
    RejectSessionRequest,
    TrainingReportSchema, RejectReportRequest,
)
from app.services import session_service
from app.core.dependencies import (
    get_current_user, require_trainer,
    require_county_officer, require_any_staff,
    assert_owns_session, assert_county_access, resolve_list_county,
    assert_can_view_session, assert_trainer_county,
)
from app.models.user import User

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(
    county: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    effective_county = resolve_list_county(current_user, county)
    return session_service.get_all_sessions(db, effective_county, skip, limit)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_can_view_session(s, current_user)
    return session_service.to_session_out(db, s)


@router.post("", response_model=SessionOut, status_code=201)
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    assert_trainer_county(data.county, current_user)
    return session_service.create_session(db, data, current_user.id)


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: str,
    data: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    if data.county is not None:
        assert_trainer_county(data.county, current_user)
    return session_service.update_session(db, s, data)


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    session_service.delete_session(db, s)


@router.patch("/{session_id}/approve", response_model=SessionOut)
def approve_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_county_officer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_county_access(s, current_user)
    return session_service.approve_session(db, s, current_user.id)


@router.patch("/{session_id}/reject", response_model=SessionOut)
def reject_session(
    session_id: str,
    data: RejectSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_county_officer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_county_access(s, current_user)
    return session_service.reject_session(db, s, data.note, current_user.id)


@router.patch("/{session_id}/report", response_model=SessionOut)
def submit_report(
    session_id: str,
    data: TrainingReportSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    return session_service.submit_report(db, s, data)


@router.patch("/{session_id}/report/approve", response_model=SessionOut)
def approve_report(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_county_officer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_county_access(s, current_user)
    return session_service.approve_report(db, s)


@router.patch("/{session_id}/report/reject", response_model=SessionOut)
def reject_report(
    session_id: str,
    data: RejectReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_county_officer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_county_access(s, current_user)
    return session_service.reject_report(db, s, data.note)
