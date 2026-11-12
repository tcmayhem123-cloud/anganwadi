"""
User Model with Role-Based Access Control and Account Lockout (FR-AUTH-01, FR-AUTH-02, FR-AUTH-03)
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from ..database import Base, utcnow

class UserRole(str, Enum):
    AWW = "AWW"
    LS = "LS"
    CDPO = "CDPO"
    DPO = "DPO"
    ADMIN = "ADMIN"

class JurisdictionType(str, Enum):
    AWC = "AWC"
    SECTOR = "SECTOR"
    BLOCK = "BLOCK"
    DISTRICT = "DISTRICT"
    GLOBAL = "GLOBAL"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    mobile = Column(String(15), nullable=True)
    jurisdiction_type = Column(SQLEnum(JurisdictionType), nullable=False, default=JurisdictionType.AWC)
    jurisdiction_id = Column(Integer, nullable=True)  # ID of AWC, Sector, Block, or District
    
    # FR-AUTH-03 Lockout
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
