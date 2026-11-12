"""
Audit Logging and System Configuration Models (FR-AUTH-04, FR-MD-04, NFR-11)
Immutable logging of all child, measurement, and vaccination changes.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from ..database import Base, utcnow

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(100), nullable=False)
    role = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOCKOUT, EXPORT
    entity = Column(String(50), nullable=False)  # Child, Measurement, VaccineRecord, User, Visit
    entity_id = Column(String(50), nullable=True)
    before_val = Column(Text, nullable=True)     # JSON old values
    after_val = Column(Text, nullable=True)      # JSON new values
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=utcnow, index=True)


class SystemConfig(Base):
    """FR-MD-04: System thresholds and state machine parameters with change audit."""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    updated_by = Column(String(100), nullable=True)
