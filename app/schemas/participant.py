from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


class ParticipantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    cadre: str = Field(..., min_length=2, max_length=100)
    facility: str = Field(..., min_length=2, max_length=200)
    status: Literal["PRESENT", "ABSENT"] = "PRESENT"
    staff_number: Optional[str] = Field(None, max_length=50)


class ScoresUpdate(BaseModel):
    pre_test_score: Optional[float] = None
    post_test_score: Optional[float] = None

    @field_validator("pre_test_score", "post_test_score")
    @classmethod
    def score_in_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("Scores must be between 0 and 100.")
        return v


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
