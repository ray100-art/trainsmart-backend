from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.training_program import TrainingProgramCreate, TrainingProgramUpdate, TrainingProgramOut
from app.services import program_service
from app.core.dependencies import require_any_staff, require_system_admin
from app.models.user import User

router = APIRouter(prefix="/programs", tags=["Training Programs"])


@router.get("", response_model=list[TrainingProgramOut])
def list_programs(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_any_staff),
):
    return program_service.list_programs(db, active_only=active_only)


@router.post("", response_model=TrainingProgramOut, status_code=201)
def create_program(
    data: TrainingProgramCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    return program_service.create_program(db, data, created_by=current_user.id)


@router.patch("/{program_id}", response_model=TrainingProgramOut)
def update_program(
    program_id: str,
    data: TrainingProgramUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    program = program_service.get_program_or_404(db, program_id)
    return program_service.update_program(db, program, data, updated_by=current_user.id)


@router.post("/seed", status_code=201)
def seed_programs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    count = program_service.seed_default_programs(db)
    return {"seeded": count, "message": f"{count} program(s) added to the national catalog."}
