from sqlalchemy import Column, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        # Prevent duplicate national certificates for the same registry person
        UniqueConstraint("session_id", "person_id", name="uq_participants_session_person"),
    )

    id                  = Column(String, primary_key=True, index=True)
    session_id          = Column(String, ForeignKey("training_sessions.id", ondelete="CASCADE"),
                                 nullable=False, index=True)
    person_id           = Column(String, ForeignKey("people.id", ondelete="SET NULL"),
                                 nullable=True, index=True)
    name                = Column(String, nullable=False)
    staff_number        = Column(String, nullable=True, index=True)
    cadre               = Column(String, nullable=False)
    facility            = Column(String, nullable=False)
    status              = Column(String, default="PRESENT")
    pre_test_score      = Column(Float, nullable=True)
    post_test_score     = Column(Float, nullable=True)
    certificate_serial  = Column(String, nullable=True, unique=True)

    session             = relationship("TrainingSession", back_populates="participants")
    person              = relationship("Person")
