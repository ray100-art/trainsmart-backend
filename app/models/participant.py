from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Participant(Base):
    __tablename__ = "participants"

    id                  = Column(String, primary_key=True, index=True)
    session_id          = Column(String, ForeignKey("training_sessions.id", ondelete="CASCADE"),
                                 nullable=False, index=True)
    name                = Column(String, nullable=False)
    staff_number        = Column(String, nullable=True, index=True)   # MOH staff/national ID for trainee matching
    cadre               = Column(String, nullable=False)
    facility            = Column(String, nullable=False)
    status              = Column(String, default="PRESENT")           # PRESENT | ABSENT
    pre_test_score      = Column(Float, nullable=True)
    post_test_score     = Column(Float, nullable=True)
    certificate_serial  = Column(String, nullable=True, unique=True)

    # Relationship
    session             = relationship("TrainingSession", back_populates="participants")