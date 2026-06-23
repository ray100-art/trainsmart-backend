from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from datetime import date

from app.schemas.participant import ParticipantOut
from app.schemas.trainer import TrainerOut


class TrainingReportSchema(BaseModel):
    summary: str = Field(..., min_length=1, max_length=10000)
    challenges: str = Field(default="", max_length=10000)
    recommendations: str = Field(default="", max_length=10000)


class SessionCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    county: str = Field(..., min_length=2, max_length=100)
    facility: str = Field(..., min_length=2, max_length=300)
    start_date: date
    end_date: date
    status: Literal["UPCOMING", "IN_PROGRESS"] = "UPCOMING"

    @model_validator(mode="after")
    def validate_date_range(self) -> "SessionCreate":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date.")
        return self


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=300)
    county: Optional[str] = Field(None, min_length=2, max_length=100)
    facility: Optional[str] = Field(None, min_length=2, max_length=300)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[Literal["UPCOMING", "IN_PROGRESS"]] = None


class RejectSessionRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)


class RejectReportRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)


class SessionOut(BaseModel):
    id: str
    title: str
    county: str
    facility: str
    trainee_count: int
    start_date: date
    end_date: date
    status: str
    approval_status: str
    approval_note: Optional[str] = None
    approved_by: Optional[str] = None
    approved_by_name: Optional[str] = None
    report_summary: Optional[str] = None
    report_challenges: Optional[str] = None
    report_recommendations: Optional[str] = None
    report_submitted_at: Optional[date] = None
    report_approval_status: str
    report_approval_note: Optional[str] = None
    certificates_issued: bool
    participants: list[ParticipantOut] = []
    trainers: list[TrainerOut] = []

    class Config:
        from_attributes = True
