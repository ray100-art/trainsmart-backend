from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class TrainingProgram(Base):
    __tablename__ = "training_programs"

    id              = Column(String, primary_key=True, index=True)
    code            = Column(String, unique=True, nullable=False, index=True)
    name            = Column(String, nullable=False)
    description     = Column(Text, nullable=True)
    category        = Column(String, nullable=False, index=True)
    target_cadres   = Column(String, nullable=True)
    duration_days   = Column(Integer, nullable=True)
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    sessions = relationship("TrainingSession", back_populates="program")
