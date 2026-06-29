import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.training_program import TrainingProgram
from app.schemas.training_program import TrainingProgramCreate, TrainingProgramUpdate
from app.services.audit_service import log_action

# NASCOP / NHITC-aligned national HIV training catalog
DEFAULT_PROGRAMS = [
    ("NHITC-01", "HIV Fundamentals & National Guidelines", "Foundational HIV care and treatment concepts", "Foundation", "All cadres", 5),
    ("NHITC-02", "HIV Testing Services (HTS)", "Provider-initiated and community HTS", "Clinical", "Nurse, Clinical Officer, Lab Technologist", 3),
    ("NHITC-03", "Antiretroviral Therapy (ART)", "ART initiation, monitoring and adherence", "Clinical", "Doctor, Clinical Officer, Nurse, Pharmacist", 5),
    ("NHITC-04", "PMTCT & EID", "Prevention of mother-to-child transmission", "Clinical", "Nurse, Clinical Officer, Counsellor", 3),
    ("NHITC-05", "Pediatric & Adolescent HIV", "HIV care for children and adolescents", "Clinical", "Doctor, Clinical Officer, Nurse", 4),
    ("NHITC-06", "Laboratory HIV Diagnostics", "VL, CD4, EID and quality assurance", "Laboratory", "Lab Technologist", 3),
    ("NHITC-07", "Pharmacy & ARV Supply", "ARV dispensing, pharmacovigilance, supply chain", "Pharmacy", "Pharmacist", 3),
    ("NHITC-08", "Nutrition & HIV", "Nutritional assessment and support for PLHIV", "Nutrition", "Nutritionist, Nurse", 2),
    ("NHITC-09", "Community Health & HIV", "Community linkage, adherence support", "Community", "Community Health Worker, Counsellor", 3),
    ("NHITC-10", "VMMC", "Voluntary medical male circumcision", "Clinical", "Clinical Officer, Nurse", 2),
    ("NHITC-11", "TB-HIV Co-infection", "Integrated TB-HIV management", "Clinical", "Doctor, Clinical Officer, Nurse", 3),
    ("NHITC-12", "Key & Vulnerable Populations", "Targeted HIV services for KP/VP", "Clinical", "Counsellor, Nurse, Clinical Officer", 3),
    ("NHITC-13", "HIV Case-Based Surveillance", "CBS implementation and data quality", "Surveillance", "All cadres", 2),
    ("NHITC-14", "Mental Health & HIV", "Psychosocial support and mental health integration", "Psychosocial", "Counsellor, Nurse", 2),
    ("NHITC-15", "PrEP & PEP", "HIV pre- and post-exposure prophylaxis", "Clinical", "Clinical Officer, Nurse, Doctor", 2),
]


def seed_default_programs(db: Session) -> int:
    created = 0
    for code, name, desc, category, cadres, days in DEFAULT_PROGRAMS:
        if db.query(TrainingProgram).filter(TrainingProgram.code == code).first():
            continue
        db.add(TrainingProgram(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            description=desc,
            category=category,
            target_cadres=cadres,
            duration_days=days,
            is_active=True,
        ))
        created += 1
    if created:
        db.commit()
    return created


def list_programs(db: Session, *, active_only: bool = True) -> list[TrainingProgram]:
    q = db.query(TrainingProgram).order_by(TrainingProgram.category, TrainingProgram.code)
    if active_only:
        q = q.filter(TrainingProgram.is_active.is_(True))
    return q.all()


def get_program_or_404(db: Session, program_id: str) -> TrainingProgram:
    p = db.query(TrainingProgram).filter(TrainingProgram.id == program_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Training program not found.")
    return p


def create_program(db: Session, data: TrainingProgramCreate, *, created_by: str | None) -> TrainingProgram:
    if db.query(TrainingProgram).filter(TrainingProgram.code == data.code.upper()).first():
        raise HTTPException(status_code=409, detail=f"Program code '{data.code}' already exists.")
    p = TrainingProgram(
        id=str(uuid.uuid4()),
        code=data.code.upper().strip(),
        name=data.name.strip(),
        description=data.description.strip() or None,
        category=data.category.strip(),
        target_cadres=data.target_cadres.strip() or None,
        duration_days=data.duration_days,
        is_active=True,
    )
    db.add(p)
    log_action(db, user_id=created_by, action="CREATE_PROGRAM",
               entity_type="program", entity_id=p.id, detail=p.code)
    db.commit()
    db.refresh(p)
    return p


def update_program(
    db: Session, program: TrainingProgram, data: TrainingProgramUpdate, *, updated_by: str | None,
) -> TrainingProgram:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(program, field, value)
    log_action(db, user_id=updated_by, action="UPDATE_PROGRAM",
               entity_type="program", entity_id=program.id, detail=program.code)
    db.commit()
    db.refresh(program)
    return program
