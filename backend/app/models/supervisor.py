"""
Supervisor Visit and Action Item Models (FR-SV-01 to FR-SV-06)
"""
from datetime import date, datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Date, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base, utcnow

class SupervisorVisit(Base):
    __tablename__ = "supervisor_visits"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(String(50), unique=True, index=True, nullable=False)
    awc_id = Column(Integer, ForeignKey("awcs.id"), nullable=False)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    visit_date = Column(Date, default=date.today, nullable=False)
    
    # Checklist items (FR-SV-02)
    attendance_count = Column(Integer, default=0)
    gps_lat = Column(Float, nullable=True)
    gps_lng = Column(Float, nullable=True)
    register_upkeep_score = Column(Integer, default=5)  # 1 to 5
    equipment_functional = Column(Boolean, default=True)
    cleanliness_score = Column(Integer, default=5)      # 1 to 5
    sn_delivered = Column(Boolean, default=True)        # Supplementary nutrition delivered

    # Auto-populated AWC snapshot statistics (FR-SV-03)
    enrolled_children = Column(Integer, default=0)
    measured_this_month = Column(Integer, default=0)
    sam_count = Column(Integer, default=0)
    mam_count = Column(Integer, default=0)
    overdue_vaccine_count = Column(Integer, default=0)

    observations = Column(Text, nullable=True)
    status = Column(String(20), default="SUBMITTED")
    created_at = Column(DateTime, default=utcnow)

    awc = relationship("AWC", back_populates="visits")
    action_items = relationship("ActionItem", back_populates="visit", cascade="all, delete-orphan")


class ActionItem(Base):
    """FR-SV-04: Action items generated during supervisor visits with owner and tracking."""
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("supervisor_visits.id"), nullable=False)
    description = Column(String(255), nullable=False)
    owner_role = Column(String(50), nullable=False)  # AWW, LS, CDPO
    owner_name = Column(String(100), nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(20), default="PENDING")   # PENDING, RESOLVED
    resolution_notes = Column(Text, nullable=True)
    resolved_date = Column(Date, nullable=True)

    visit = relationship("SupervisorVisit", back_populates="action_items")
