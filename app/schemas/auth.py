import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional

_USERNAME_RE = re.compile(r'^[a-z0-9][a-z0-9_.\-]*[a-z0-9]$')


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    token: str
    role: str
    county: str
    username: str
    full_name: str
    staff_number: Optional[str] = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=150)
    role: str = Field(..., min_length=1, max_length=50)
    county: str = Field(..., min_length=2, max_length=100)
    staff_number: Optional[str] = Field(None, max_length=50)

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) < 3 or not _USERNAME_RE.match(v):
            raise ValueError(
                "Username must be 3–50 characters and contain only letters, digits, "
                "dots, hyphens, or underscores (cannot start or end with a special character)."
            )
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("full_name cannot be blank.")
        return v


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    county: str
    staff_number: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
