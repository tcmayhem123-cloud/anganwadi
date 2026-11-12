"""
Alerts and Notification System Models (FR-AL-01, FR-AL-03, FR-SM-06)
Includes automated multi-tier escalation (AWW -> LS at 7 days -> CDPO at 14 days)
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from ..database import Base, utcnow

class AlertType(str, Enum):
    NEW_SAM = "NEW_SAM"
    NEW_MAM = "NEW_MAM"
    SAM_RELAPSE = "SAM_RELAPSE"
    MISSED_MEASUREMENT = "MISSED_MEASUREMENT"
    OVERDUE_VACCINE = "OVERDUE_VACCINE"
    CHILD_NOT_SEEN_60D = "CHILD_NOT_SEEN_60D"
    VISIT_DUE_30D = "VISIT_DUE_30D"

class AlertPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED_LS = "ESCALATED_LS"
    ESCALATED_CDPO = "ESCALATED_CDPO"
    CLOSED = "CLOSED"

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(50), unique=True, index=True, nullable=False)
    type = Column(SQLEnum(AlertType), nullable=False)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=True)
    awc_id = Column(Integer, ForeignKey("awcs.id"), nullable=False)
    priority = Column(SQLEnum(AlertPriority), default=AlertPriority.MEDIUM, nullable=False)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.OPEN, nullable=False)
    
    # 0 = AWW, 1 = LS (7 days unresolved), 2 = CDPO (14 days unresolved)
    escalation_level = Column(Integer, default=0)
    
    description = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    action_taken = Column(String(255), nullable=True)  # e.g. "Referred to NRC", "Counselling given"
    action_by = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=utcnow)
    last_escalated_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
