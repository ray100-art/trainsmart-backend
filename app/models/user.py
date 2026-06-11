from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id               = Column(String, primary_key=True, index=True)
    username         = Column(String, unique=True, nullable=False, index=True)
    email            = Column(String, unique=True, nullable=False, index=True)
    hashed_password  = Column(String, nullable=False)
    full_name        = Column(String, nullable=False)
    role             = Column(String, nullable=False)          # e.g. ROLE_TRAINER
    county           = Column(String, nullable=False)          # e.g. Nairobi
    staff_number     = Column(String, nullable=True, index=True)  # MOH staff/national ID
    is_active        = Column(Boolean, default=True, nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sessions         = relationship("TrainingSession", back_populates="created_by_user",
                                    foreign_keys="TrainingSession.created_by")