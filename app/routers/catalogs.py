from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas.catalog import (
    FacilityCreate, FacilityUpdate, FacilityOut,
    SponsorCreate, SponsorUpdate, SponsorOut,
)
from app.schemas.common import PaginatedResponse
from app.services import catalog_service
from app.core.dependencies import require_any_staff, require_system_admin
from app.models.user import User

facilities_router = APIRouter(prefix="/facilities", tags=["Facilities"])
sponsors_router = APIRouter(prefix="/sponsors", tags=["Sponsors"])


@facilities_router.get("", response_model=PaginatedResponse[FacilityOut])
def list_facilities(
    county: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    items, total = catalog_service.list_facilities(
        db, county=county, q=q, active_only=active_only, skip=skip, limit=limit
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@facilities_router.post("", response_model=FacilityOut, status_code=201)
def create_facility(
    data: FacilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    return catalog_service.create_facility(db, data, user_id=current_user.id)


@facilities_router.patch("/{facility_id}", response_model=FacilityOut)
def update_facility(
    facility_id: str,
    data: FacilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    facility = catalog_service.get_facility_or_404(db, facility_id)
    return catalog_service.update_facility(db, facility, data, user_id=current_user.id)


@sponsors_router.get("", response_model=PaginatedResponse[SponsorOut])
def list_sponsors(
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    items, total = catalog_service.list_sponsors(
        db, active_only=active_only, skip=skip, limit=limit
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@sponsors_router.post("", response_model=SponsorOut, status_code=201)
def create_sponsor(
    data: SponsorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    return catalog_service.create_sponsor(db, data, user_id=current_user.id)


@sponsors_router.patch("/{sponsor_id}", response_model=SponsorOut)
def update_sponsor(
    sponsor_id: str,
    data: SponsorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    sponsor = catalog_service.get_sponsor_or_404(db, sponsor_id)
    return catalog_service.update_sponsor(db, sponsor, data, user_id=current_user.id)
