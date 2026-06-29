from sqlalchemy import Column, String, DateTime, func

from app.database import Base


class RateLimitEvent(Base):
    __tablename__ = "rate_limit_events"

    id         = Column(String, primary_key=True)
    scope      = Column(String, nullable=False, index=True)
    identifier = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
