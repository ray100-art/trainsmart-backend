from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal


class ParticipantCreate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    cadre: Optional[str] = Field(None, min_length=2, max_length=100)
    facility: Optional[str] = Field(None, min_length=2, max_length=200)
    status: Literal["PRESENT", "ABSENT"] = "PRESENT"
    staff_number: Optional[str] = Field(None, max_length=50)
    person_id: Optional[str] = Field(None, max_length=100)

    @model_validator(mode="after")
    def require_fields_or_person(self) -> "ParticipantCreate":
        if self.person_id:
            return self
        missing = [f for f in ("name", "cadre", "facility") if not getattr(self, f)]
        if missing:
            raise ValueError(
                f"Provide person_id from the people registry, or fill: {', '.join(missing)}."
            )
        return self


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
    person_id: Optional[str] = None
    cadre: str
    facility: str
    status: str
    pre_test_score: Optional[float] = None
    post_test_score: Optional[float] = None
    certificate_serial: Optional[str] = None

    class Config:
        from_attributes = True
