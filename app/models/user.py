from sqlalchemy import Column, String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id                   = Column(String, primary_key=True, index=True)
    username             = Column(String, unique=True, nullable=False, index=True)
    email                = Column(String, unique=True, nullable=False, index=True)
    hashed_password      = Column(String, nullable=False)
    full_name            = Column(String, nullable=False)
    role                 = Column(String, nullable=False)
    county               = Column(String, nullable=False)
    staff_number         = Column(String, nullable=True, index=True)
    is_active            = Column(Boolean, default=True, nullable=False)
    token_version        = Column(Integer, default=0, nullable=False)
    setup_token          = Column(String, nullable=True, index=True)
    setup_token_expires  = Column(DateTime(timezone=True), nullable=True)
    mfa_enabled          = Column(Boolean, default=False, nullable=False)
    mfa_secret           = Column(String, nullable=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())

    sessions = relationship(
        "TrainingSession",
        back_populates="created_by_user",
        foreign_keys="TrainingSession.created_by",
    )
