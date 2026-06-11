from pydantic import BaseModel


class TrainerCreate(BaseModel):
    name: str
    cadre: str
    phone: str


class TrainerOut(BaseModel):
    id: str
    name: str
    cadre: str
    phone: str

    class Config:
        from_attributes = True