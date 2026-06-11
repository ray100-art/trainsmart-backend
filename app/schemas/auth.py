from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str
    county: str
    username: str
    full_name: str
    staff_number: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: str
    county: str
    staff_number: Optional[str] = None


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