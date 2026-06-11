from pydantic import BaseModel
from typing import Optional


class ParticipantCreate(BaseModel):
    name: str
    cadre: str
    facility: str
    status: str = "PRESENT"
    staff_number: Optional[str] = None


class ScoresUpdate(BaseModel):
    pre_test_score: float
    post_test_score: float


class ParticipantOut(BaseModel):
    id: str
    name: str
    staff_number: Optional[str] = None
    cadre: str
    facility: str
    status: str
    pre_test_score: Optional[float] = None
    post_test_score: Optional[float] = None
    certificate_serial: Optional[str] = None

    class Config:
        from_attributes = True