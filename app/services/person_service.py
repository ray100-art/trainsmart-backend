import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.person import Person
from app.schemas.person import PersonCreate, PersonUpdate
from app.lib.county import normalize_county
from app.services.audit_service import log_action


def list_people(
    db: Session,
    *,
    q: str | None = None,
    county: str | None = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Person], int]:
    query = db.query(Person)
    if active_only:
        query = query.filter(Person.is_active.is_(True))
    if county:
        query = query.filter(Person.county == normalize_county(county))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Person.national_id.ilike(like))
            | (Person.first_name.ilike(like))
            | (Person.last_name.ilike(like))
            | (Person.facility.ilike(like))
            | (Person.qualification.ilike(like))
        )
    total = query.count()
    items = query.order_by(Person.last_name, Person.first_name).offset(skip).limit(limit).all()
    return items, total


def get_person_or_404(db: Session, person_id: str) -> Person:
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found.")
    return person


def create_person(db: Session, data: PersonCreate, created_by: str | None = None) -> Person:
    national_id = data.national_id.strip()
    existing = db.query(Person).filter(Person.national_id == national_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="A person with that National ID already exists.")

    person = Person(
        id=str(uuid.uuid4()),
        national_id=national_id,
        first_name=data.first_name.strip(),
        middle_name=(data.middle_name or "").strip() or None,
        last_name=data.last_name.strip(),
        gender=data.gender,
        qualification=data.qualification.strip(),
        facility=data.facility.strip(),
        county=normalize_county(data.county),
        phone=(data.phone or "").strip() or None,
        email=(data.email or "").strip() or None,
        created_by=created_by,
    )
    db.add(person)
    db.flush()
    log_action(db, user_id=created_by, action="CREATE_PERSON",
               entity_type="person", entity_id=person.id,
               detail=f"{person.national_id} {person.first_name} {person.last_name}")
    db.commit()
    db.refresh(person)
    return person


def update_person(
    db: Session, person: Person, data: PersonUpdate, updated_by: str | None = None
) -> Person:
    updates = data.model_dump(exclude_none=True)
    if "county" in updates:
        updates["county"] = normalize_county(updates["county"])
    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(person, field, value)
    log_action(db, user_id=updated_by, action="UPDATE_PERSON",
               entity_type="person", entity_id=person.id)
    db.commit()
    db.refresh(person)
    return person
