from sqlalchemy import Column, String, DateTime, Text, func

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(String, primary_key=True, index=True)
    user_id     = Column(String, nullable=True, index=True)
    action      = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id   = Column(String, nullable=True)
    detail      = Column(Text, nullable=True)
    ip_address  = Column(String, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
