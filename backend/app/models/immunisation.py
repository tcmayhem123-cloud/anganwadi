"""
Immunisation Models (FR-IM-01, FR-IM-02)
"""
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base, utcnow

class VaccineSchedule(Base):
    __tablename__ = "vaccine_schedules"

    id = Column(Integer, primary_key=True, index=True)
    vaccine_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    dose_no = Column(Integer, nullable=False)
    target_age_days = Column(Integer, nullable=False)
    window_start_days = Column(Integer, nullable=False)
    window_end_days = Column(Integer, nullable=False)
    category = Column(String(50), nullable=False)
    is_mandatory = Column(Boolean, default=True)
    version = Column(String(50), default="MoHFW_UIP_2024")


class VaccineRecord(Base):
    __tablename__ = "vaccine_records"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    vaccine_code = Column(String(50), nullable=False)
    dose_no = Column(Integer, default=1)
    given_date = Column(Date, nullable=False, default=date.today)
    place = Column(String(100), nullable=True)
    batch_no = Column(String(50), nullable=True)
    recorded_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    child = relationship("Child", back_populates="vaccine_records")
