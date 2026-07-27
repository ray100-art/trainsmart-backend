from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class PersonCreate(BaseModel):
    national_id: str = Field(..., min_length=5, max_length=30)
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    gender: Literal["Male", "Female", "Other"]
    qualification: str = Field(..., min_length=1, max_length=150)
    facility: str = Field(..., min_length=1, max_length=300)
    county: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=200)

    @field_validator("national_id", "first_name", "last_name", "qualification", "facility")
    @classmethod
    def strip_required(cls, v: str) -> str:
        return v.strip()


class PersonUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[Literal["Male", "Female", "Other"]] = None
    qualification: Optional[str] = Field(None, min_length=1, max_length=150)
    facility: Optional[str] = Field(None, min_length=1, max_length=300)
    county: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class PersonOut(BaseModel):
    id: str
    national_id: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    gender: str
    qualification: str
    facility: str
    county: str
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
