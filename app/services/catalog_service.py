import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.facility import Facility
from app.models.sponsor import Sponsor
from app.schemas.catalog import FacilityCreate, FacilityUpdate, SponsorCreate, SponsorUpdate
from app.lib.county import normalize_county
from app.services.audit_service import log_action


def list_facilities(
    db: Session, *, county: str | None = None, q: str | None = None,
    active_only: bool = True, skip: int = 0, limit: int = 100,
) -> tuple[list[Facility], int]:
    query = db.query(Facility)
    if active_only:
        query = query.filter(Facility.is_active.is_(True))
    if county:
        query = query.filter(Facility.county == normalize_county(county))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Facility.name.ilike(like) | Facility.mfl_code.ilike(like))
    total = query.count()
    items = query.order_by(Facility.county, Facility.name).offset(skip).limit(limit).all()
    return items, total


def create_facility(db: Session, data: FacilityCreate, user_id: str | None = None) -> Facility:
    if data.mfl_code:
        exists = db.query(Facility).filter(Facility.mfl_code == data.mfl_code.strip()).first()
        if exists:
            raise HTTPException(status_code=409, detail="MFL code already exists.")
    facility = Facility(
        id=str(uuid.uuid4()),
        name=data.name.strip(),
        county=normalize_county(data.county),
        mfl_code=(data.mfl_code or "").strip() or None,
        facility_type=(data.facility_type or "").strip() or None,
    )
    db.add(facility)
    db.flush()
    log_action(db, user_id=user_id, action="CREATE_FACILITY",
               entity_type="facility", entity_id=facility.id, detail=facility.name)
    db.commit()
    db.refresh(facility)
    return facility


def get_facility_or_404(db: Session, facility_id: str) -> Facility:
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found.")
    return facility


def update_facility(
    db: Session, facility: Facility, data: FacilityUpdate, user_id: str | None = None
) -> Facility:
    updates = data.model_dump(exclude_none=True)
    if "county" in updates:
        updates["county"] = normalize_county(updates["county"])
    if "mfl_code" in updates and updates["mfl_code"]:
        mfl = updates["mfl_code"].strip() if isinstance(updates["mfl_code"], str) else updates["mfl_code"]
        exists = (
            db.query(Facility)
            .filter(Facility.mfl_code == mfl, Facility.id != facility.id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="MFL code already exists.")
    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(facility, field, value)
    log_action(db, user_id=user_id, action="UPDATE_FACILITY",
               entity_type="facility", entity_id=facility.id)
    db.commit()
    db.refresh(facility)
    return facility


def list_sponsors(
    db: Session, *, active_only: bool = True, skip: int = 0, limit: int = 100
) -> tuple[list[Sponsor], int]:
    query = db.query(Sponsor)
    if active_only:
        query = query.filter(Sponsor.is_active.is_(True))
    total = query.count()
    items = query.order_by(Sponsor.name).offset(skip).limit(limit).all()
    return items, total


def create_sponsor(db: Session, data: SponsorCreate, user_id: str | None = None) -> Sponsor:
    name = data.name.strip()
    if db.query(Sponsor).filter(Sponsor.name == name).first():
        raise HTTPException(status_code=409, detail="Sponsor name already exists.")
    sponsor = Sponsor(
        id=str(uuid.uuid4()),
        name=name,
        code=(data.code or "").strip() or None,
        description=(data.description or "").strip() or None,
    )
    db.add(sponsor)
    db.flush()
    log_action(db, user_id=user_id, action="CREATE_SPONSOR",
               entity_type="sponsor", entity_id=sponsor.id, detail=sponsor.name)
    db.commit()
    db.refresh(sponsor)
    return sponsor


def get_sponsor_or_404(db: Session, sponsor_id: str) -> Sponsor:
    sponsor = db.query(Sponsor).filter(Sponsor.id == sponsor_id).first()
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor not found.")
    return sponsor


def update_sponsor(
    db: Session, sponsor: Sponsor, data: SponsorUpdate, user_id: str | None = None
) -> Sponsor:
    updates = data.model_dump(exclude_none=True)
    if "name" in updates and updates["name"]:
        name = updates["name"].strip() if isinstance(updates["name"], str) else updates["name"]
        exists = (
            db.query(Sponsor)
            .filter(Sponsor.name == name, Sponsor.id != sponsor.id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="Sponsor name already exists.")
    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(sponsor, field, value)
    log_action(db, user_id=user_id, action="UPDATE_SPONSOR",
               entity_type="sponsor", entity_id=sponsor.id)
    db.commit()
    db.refresh(sponsor)
    return sponsor
