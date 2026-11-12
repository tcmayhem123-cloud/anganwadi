"""
Child Entity and Child Transfer Models (FR-REG-01 to FR-REG-06)
"""
from datetime import date, datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Date, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from ..database import Base, utcnow

class ChildStatus(str, Enum):
    ACTIVE = "ACTIVE"
    MIGRATED = "MIGRATED"
    DECEASED = "DECEASED"
    INACTIVE = "INACTIVE"
    GRADUATED = "GRADUATED"

class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(String(50), unique=True, index=True, nullable=False)  # System generated
    name = Column(String(100), nullable=False)
    sex = Column(String(1), nullable=False)  # M or F
    dob = Column(Date, nullable=False)
    guardian_name = Column(String(100), nullable=False)
    guardian_relationship = Column(String(50), nullable=False, default="Mother")
    mobile = Column(String(15), nullable=True)
    guardian_consent_sms = Column(Boolean, default=True)  # DPDP Act 2023 compliance
    address_village = Column(String(200), nullable=False)
    awc_id = Column(Integer, ForeignKey("awcs.id"), nullable=False)
    registration_date = Column(Date, default=date.today)
    
    # FR-REG-06: Birth weight and low birth weight flag
    birth_weight_kg = Column(Float, nullable=True)
    is_low_birth_weight = Column(Boolean, default=False)

    # Status lifecycle: ACTIVE, MIGRATED, DECEASED, INACTIVE, GRADUATED (FR-REG-02, FR-REG-05)
    status = Column(SQLEnum(ChildStatus), default=ChildStatus.ACTIVE, nullable=False)
    status_reason = Column(String(255), nullable=True)
    status_date = Column(Date, nullable=True)

    # Nutritional State Machine current values (FR-SM-01)
    current_state = Column(String(20), default="Normal", nullable=False)
    consecutive_normal_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=utcnow)

    # Relationships
    awc = relationship("AWC", back_populates="children")
    measurements = relationship("Measurement", back_populates="child", cascade="all, delete-orphan", order_by="Measurement.date")
    vaccine_records = relationship("VaccineRecord", back_populates="child", cascade="all, delete-orphan")
    state_events = relationship("StateEvent", back_populates="child", cascade="all, delete-orphan", order_by="StateEvent.event_date")
    transfer_history = relationship("ChildTransferHistory", back_populates="child", cascade="all, delete-orphan")


class ChildTransferHistory(Base):
    """FR-REG-04: Child transfer between AWCs with history of previous centres."""
    __tablename__ = "child_transfers"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    from_awc_id = Column(Integer, ForeignKey("awcs.id"), nullable=False)
    to_awc_id = Column(Integer, ForeignKey("awcs.id"), nullable=False)
    transfer_date = Column(Date, default=date.today)
    reason = Column(String(255), nullable=True)
    transferred_by = Column(String(100), nullable=False)

    child = relationship("Child", back_populates="transfer_history")
