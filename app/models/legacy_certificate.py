from sqlalchemy import Column, String, Float, Date, DateTime, func

from app.database import Base


class LegacyCertificate(Base):
    """Certificates issued by legacy TrainSMART (pre-migration)."""

    __tablename__ = "legacy_certificates"

    id               = Column(String, primary_key=True, index=True)
    serial           = Column(String, unique=True, nullable=False, index=True)
    participant_name = Column(String, nullable=False)
    cadre            = Column(String, nullable=False)
    facility         = Column(String, nullable=False)
    course           = Column(String, nullable=False)
    county           = Column(String, nullable=False, index=True)
    start_date       = Column(Date, nullable=True)
    end_date         = Column(Date, nullable=True)
    post_test_score  = Column(Float, nullable=True)
    issued_date      = Column(Date, nullable=True)
    # pre_2018 | post_2018 — matches legacy TrainSMART verification eras
    era              = Column(String, nullable=False, index=True)
    imported_at      = Column(DateTime(timezone=True), server_default=func.now())
