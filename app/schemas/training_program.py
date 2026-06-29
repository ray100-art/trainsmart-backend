from pydantic import BaseModel, Field
from typing import Optional


class TrainingProgramCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=3, max_length=300)
    description: str = Field(default="", max_length=5000)
    category: str = Field(..., min_length=2, max_length=100)
    target_cadres: str = Field(default="", max_length=500)
    duration_days: Optional[int] = Field(None, ge=1, le=365)


class TrainingProgramUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=300)
    description: Optional[str] = Field(None, max_length=5000)
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    target_cadres: Optional[str] = Field(None, max_length=500)
    duration_days: Optional[int] = Field(None, ge=1, le=365)
    is_active: Optional[bool] = None


class TrainingProgramOut(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    category: str
    target_cadres: Optional[str] = None
    duration_days: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True
