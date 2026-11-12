"""
Master Data Hierarchy Models: District -> Block -> Sector -> AWC (FR-MD-01)
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=False)

    blocks = relationship("Block", back_populates="district", cascade="all, delete-orphan")


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)

    district = relationship("District", back_populates="blocks")
    sectors = relationship("Sector", back_populates="block", cascade="all, delete-orphan")


class Sector(Base):
    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, index=True)
    block_id = Column(Integer, ForeignKey("blocks.id"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    supervisor_id = Column(Integer, nullable=True)  # References User with role LS

    block = relationship("Block", back_populates="sectors")
    awcs = relationship("AWC", back_populates="sector", cascade="all, delete-orphan")


class AWC(Base):
    __tablename__ = "awcs"

    id = Column(Integer, primary_key=True, index=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    village = Column(String(100), nullable=False)
    latitude = Column(String(50), nullable=True)
    longitude = Column(String(50), nullable=True)

    sector = relationship("Sector", back_populates="awcs")
    children = relationship("Child", back_populates="awc")
    visits = relationship("SupervisorVisit", back_populates="awc")
