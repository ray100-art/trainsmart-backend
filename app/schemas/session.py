from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime
from app.schemas.participant import ParticipantOut
from app.schemas.trainer import TrainerOut


class TrainingReportSchema(BaseModel):
    summary: str
    challenges: str = ""
    recommendations: str = ""


class SessionCreate(BaseModel):
    title: str
    county: str
    facility: str
    start_date: str
    end_date: str
    status: str = "UPCOMING"

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format.")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "SessionCreate":
        try:
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.end_date, "%Y-%m-%d")
            if start > end:
                raise ValueError("start_date must be before or equal to end_date.")
        except ValueError as e:
            # Let the field validator errors raise first, or raise value error directly
            if "YYYY-MM-DD" not in str(e):
                raise ValueError("start_date must be before or equal to end_date.")
        return self


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    county: Optional[str] = None
    facility: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format.")
        return v


class ApproveSessionRequest(BaseModel):
    approved_by: str


class RejectSessionRequest(BaseModel):
    note: str
    approved_by: str


class RejectReportRequest(BaseModel):
    note: str


class SessionOut(BaseModel):
    id: str
    title: str
    county: str
    facility: str
    trainee_count: int
    start_date: str
    end_date: str
    status: str
    approval_status: str
    approval_note: Optional[str] = None
    approved_by: Optional[str] = None
    report_summary: Optional[str] = None
    report_challenges: Optional[str] = None
    report_recommendations: Optional[str] = None
    report_submitted_at: Optional[str] = None
    report_approval_status: str
    report_approval_note: Optional[str] = None
    certificates_issued: bool
    participants: list[ParticipantOut] = []
    trainers: list[TrainerOut] = []

    class Config:
        from_attributes = True