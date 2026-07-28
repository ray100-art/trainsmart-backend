from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas.person import PersonCreate, PersonUpdate, PersonOut
from app.schemas.common import PaginatedResponse
from app.services import person_service
from app.services.person_import_service import bulk_import_people_csv, people_csv_template
from app.services.auth_service import COUNTY_SCOPED_ROLES
from app.lib.uploads import read_upload_text
from app.core.dependencies import require_any_staff, require_roles
from app.models.user import User
from app.lib.county import normalize_county

router = APIRouter(prefix="/people", tags=["People"])

_can_manage_people = require_roles(
    "ROLE_TRAINER", "ROLE_SITE_COORDINATOR", "ROLE_COUNTY_OFFICER",
    "ROLE_NATIONAL_ADMIN", "ROLE_SYSTEM_ADMIN",
)


@router.get("", response_model=PaginatedResponse[PersonOut])
def list_people(
    q: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    effective_county = county
    if current_user.role in COUNTY_SCOPED_ROLES:
        effective_county = current_user.county
    elif county:
        effective_county = normalize_county(county)
    items, total = person_service.list_people(
        db, q=q, county=effective_county, skip=skip, limit=limit
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=PersonOut, status_code=201)
def create_person(
    data: PersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_can_manage_people),
):
    if current_user.role in COUNTY_SCOPED_ROLES:
        data = data.model_copy(update={"county": current_user.county})
    return person_service.create_person(db, data, created_by=current_user.id)


@router.get("/import/template.csv")
def people_import_template(_current_user: User = Depends(_can_manage_people)):
    return PlainTextResponse(
        content=people_csv_template(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="people-import-template.csv"'},
    )


@router.post("/import")
def import_people(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(_can_manage_people),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file.")
    text = read_upload_text(file)
    force_county = current_user.county if current_user.role in COUNTY_SCOPED_ROLES else None
    return bulk_import_people_csv(
        db, text, created_by=current_user.id, force_county=force_county,
    )


@router.get("/{person_id}", response_model=PersonOut)
def get_person(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    person = person_service.get_person_or_404(db, person_id)
    if current_user.role in COUNTY_SCOPED_ROLES:
        if normalize_county(person.county) != normalize_county(current_user.county):
            raise HTTPException(status_code=403, detail="You can only view people in your county.")
    return person


@router.patch("/{person_id}", response_model=PersonOut)
def update_person(
    person_id: str,
    data: PersonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_can_manage_people),
):
    person = person_service.get_person_or_404(db, person_id)
    if current_user.role in COUNTY_SCOPED_ROLES:
        if normalize_county(person.county) != normalize_county(current_user.county):
            raise HTTPException(status_code=403, detail="You can only edit people in your county.")
        if data.county is not None:
            data = data.model_copy(update={"county": current_user.county})
    return person_service.update_person(db, person, data, updated_by=current_user.id)
