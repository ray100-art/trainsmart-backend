from typing import Optional
from pydantic import BaseModel, Field


class FacilityCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=300)
    county: str = Field(..., min_length=2, max_length=100)
    mfl_code: Optional[str] = Field(None, max_length=50)
    facility_type: Optional[str] = Field(None, max_length=100)


class FacilityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=300)
    county: Optional[str] = Field(None, min_length=2, max_length=100)
    mfl_code: Optional[str] = Field(None, max_length=50)
    facility_type: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class FacilityOut(BaseModel):
    id: str
    name: str
    county: str
    mfl_code: Optional[str] = None
    facility_type: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class SponsorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)


class SponsorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class SponsorOut(BaseModel):
    id: str
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
