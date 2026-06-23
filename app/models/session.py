from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id                    = Column(String, primary_key=True, index=True)
    title                 = Column(String, nullable=False)
    county                = Column(String, nullable=False, index=True)
    facility              = Column(String, nullable=False)
    trainee_count         = Column(Integer, default=0)
    start_date            = Column(Date, nullable=False)
    end_date              = Column(Date, nullable=False)

    # Workflow status
    status                = Column(String, default="UPCOMING")        # UPCOMING | IN_PROGRESS | COMPLETED
    approval_status       = Column(String, default="PENDING")         # PENDING | APPROVED | REJECTED
    approval_note         = Column(Text, nullable=True)
    approved_by           = Column(String, nullable=True)             # user ID of last reviewer

    # Report fields
    report_summary        = Column(Text, nullable=True)
    report_challenges     = Column(Text, nullable=True)
    report_recommendations= Column(Text, nullable=True)
    report_submitted_at   = Column(Date, nullable=True)
    report_approval_status= Column(String, default="PENDING")         # PENDING | APPROVED | REJECTED
    report_approval_note  = Column(Text, nullable=True)

    # Certificates
    certificates_issued   = Column(Boolean, default=False)

    # Audit
    created_by            = Column(String, ForeignKey("users.id"), nullable=True)
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    created_by_user       = relationship("User", back_populates="sessions",
                                         foreign_keys=[created_by])
    participants          = relationship("Participant", back_populates="session",
                                         cascade="all, delete-orphan")
    trainers              = relationship("SessionTrainer", back_populates="session",
                                         cascade="all, delete-orphan")
