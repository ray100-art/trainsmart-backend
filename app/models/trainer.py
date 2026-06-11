from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class SessionTrainer(Base):
    __tablename__ = "session_trainers"

    id          = Column(String, primary_key=True, index=True)
    session_id  = Column(String, ForeignKey("training_sessions.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    name        = Column(String, nullable=False)
    cadre       = Column(String, nullable=False)
    phone       = Column(String, nullable=False)

    # Relationship
    session     = relationship("TrainingSession", back_populates="trainers")