from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, ForeignKey, Index, func
from sqlalchemy.orm import relationship

from app.database import Base


class TrainingSession(Base):
    __tablename__ = "training_sessions"
    __table_args__ = (
        Index("ix_training_sessions_created_by", "created_by"),
        Index("ix_training_sessions_created_at", "created_at"),
        Index("ix_training_sessions_approval_status", "approval_status"),
        Index("ix_training_sessions_county_created", "county", "created_at"),
        Index("ix_training_sessions_created_by_created", "created_by", "created_at"),
        Index("ix_training_sessions_status", "status"),
        Index("ix_training_sessions_end_date", "end_date"),
        Index(
            "ix_sessions_report_cert_pipeline",
            "report_approval_status",
            "certificates_issued",
            "certificates_signed",
            "end_date",
        ),
    )

    id                    = Column(String, primary_key=True, index=True)
    title                 = Column(String, nullable=False)
    county                = Column(String, nullable=False, index=True)
    facility              = Column(String, nullable=False)
    venue                 = Column(String, nullable=True)
    funding_source        = Column(String, nullable=True)
    sponsor_id            = Column(String, ForeignKey("sponsors.id", ondelete="SET NULL"), nullable=True, index=True)
    trainee_count         = Column(Integer, default=0)
    start_date            = Column(Date, nullable=False)
    end_date              = Column(Date, nullable=False)

    status                = Column(String, default="UPCOMING")
    approval_status       = Column(String, default="PENDING")
    approval_note         = Column(Text, nullable=True)
    approved_by           = Column(String, nullable=True)

    report_summary        = Column(Text, nullable=True)
    report_challenges     = Column(Text, nullable=True)
    report_recommendations= Column(Text, nullable=True)
    report_submitted_at   = Column(Date, nullable=True)
    report_approval_status= Column(String, default="PENDING")
    report_approval_note  = Column(Text, nullable=True)
    report_approved_by    = Column(String, nullable=True)

    certificates_issued   = Column(Boolean, default=False)
    certificates_signed   = Column(Boolean, default=False, nullable=False)

    program_id            = Column(String, ForeignKey("training_programs.id", ondelete="SET NULL"), nullable=True, index=True)

    created_by            = Column(String, ForeignKey("users.id"), nullable=True)
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), onupdate=func.now())

    created_by_user       = relationship("User", back_populates="sessions",
                                         foreign_keys=[created_by])
    participants          = relationship("Participant", back_populates="session",
                                         cascade="all, delete-orphan")
    trainers              = relationship("SessionTrainer", back_populates="session",
                                         cascade="all, delete-orphan")
    program               = relationship("TrainingProgram", back_populates="sessions")
    sponsor               = relationship("Sponsor", back_populates="sessions")
