from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship

from app.database import Base


class Person(Base):
    """National people registry (trainees / health workers), keyed by National ID."""
    __tablename__ = "people"
    __table_args__ = (
        Index("ix_people_name", "last_name", "first_name"),
        Index("ix_people_county_facility", "county", "facility"),
        Index("ix_people_is_active", "is_active"),
        Index("ix_people_county_active_name", "county", "is_active", "last_name", "first_name"),
    )

    id              = Column(String, primary_key=True)
    national_id     = Column(String, unique=True, nullable=False, index=True)
    first_name      = Column(String, nullable=False)
    middle_name     = Column(String, nullable=True)
    last_name       = Column(String, nullable=False)
    gender          = Column(String, nullable=False)  # Male | Female | Other
    qualification   = Column(String, nullable=False)  # cadre / qualification
    facility        = Column(String, nullable=False)
    county          = Column(String, nullable=False, index=True)
    phone           = Column(String, nullable=True)
    email           = Column(String, nullable=True)
    is_active       = Column(Boolean, default=True, nullable=False)
    created_by      = Column(String, ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
