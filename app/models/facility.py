from sqlalchemy import Column, String, Boolean, DateTime, func

from app.database import Base


class Facility(Base):
    """Master facility catalog (Settings → Facility on legacy TrainSMART)."""
    __tablename__ = "facilities"

    id          = Column(String, primary_key=True)
    name        = Column(String, nullable=False, index=True)
    county      = Column(String, nullable=False, index=True)
    mfl_code    = Column(String, nullable=True, unique=True, index=True)
    facility_type = Column(String, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
