from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from app.database import Base


class Sponsor(Base):
    """Funding / sponsor catalog (Settings → Sponsor on legacy TrainSMART)."""
    __tablename__ = "sponsors"

    id          = Column(String, primary_key=True)
    name        = Column(String, unique=True, nullable=False, index=True)
    code        = Column(String, nullable=True, unique=True)
    description = Column(String, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    sessions = relationship("TrainingSession", back_populates="sponsor")
