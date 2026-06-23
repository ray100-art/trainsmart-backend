import re
from pydantic import BaseModel, Field, field_validator

_PHONE_STRIP_RE = re.compile(r'[\s\-\(\)]')
_PHONE_VALID_RE = re.compile(r'^\+?[0-9]{7,15}$')


class TrainerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    cadre: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=7, max_length=25)

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: str) -> str:
        cleaned = _PHONE_STRIP_RE.sub("", v.strip())
        if not _PHONE_VALID_RE.match(cleaned):
            raise ValueError("Invalid phone number. Expected 7–15 digits, optional leading '+'.")
        return cleaned


class TrainerOut(BaseModel):
    id: str
    name: str
    cadre: str
    phone: str

    class Config:
        from_attributes = True
