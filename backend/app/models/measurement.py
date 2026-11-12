"""
Measurement and StateEvent Models (FR-GM-01 to FR-GM-08, FR-ZS-01 to FR-ZS-06, FR-SM-04)
"""
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base, utcnow

class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    measurement_id = Column(String(50), unique=True, index=True, nullable=False)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    
    # Exact age calculated by system (FR-GM-02)
    age_days = Column(Integer, nullable=False)
    age_months = Column(Integer, nullable=False)

    # Anthropometrics (FR-GM-01)
    weight_kg = Column(Float, nullable=False)
    length_height_cm = Column(Float, nullable=False)
    posture = Column(String(20), nullable=False, default="RECUMBENT")
    posture_corrected = Column(Boolean, default=False)
    corrected_dimension_cm = Column(Float, nullable=False)
    muac_cm = Column(Float, nullable=True)
    oedema = Column(Boolean, default=False)

    # Z-scores (FR-ZS-01, FR-ZS-02)
    waz = Column(Float, nullable=False)
    haz = Column(Float, nullable=False)
    whz = Column(Float, nullable=False)
    acute_class = Column(String(20), nullable=False)  # Normal, MAM, SAM
    
    # Growth flags (FR-ZS-04)
    is_underweight = Column(Boolean, default=False)
    is_severely_underweight = Column(Boolean, default=False)
    is_stunted = Column(Boolean, default=False)
    is_severely_stunted = Column(Boolean, default=False)
    is_implausible = Column(Boolean, default=False)
    ref_version = Column(String(50), default="WHO_2006_2007")

    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    child = relationship("Child", back_populates="measurements")
    state_events = relationship("StateEvent", back_populates="measurement")


class StateEvent(Base):
    """FR-SM-04: Persists every state transition as an immutable historical event."""
    __tablename__ = "state_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), unique=True, index=True, nullable=False)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    from_state = Column(String(20), nullable=True)
    to_state = Column(String(20), nullable=False)
    measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=True)
    event_date = Column(Date, default=date.today)
    transition_rule = Column(String(10), nullable=False)  # T1 - T15
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    child = relationship("Child", back_populates="state_events")
    measurement = relationship("Measurement", back_populates="state_events")
