from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    weight_kg = Column(Numeric(5, 2), nullable=True)
    sleep_time = Column(Time, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    intake_records = relationship("IntakeRecord", back_populates="user", cascade="all, delete-orphan")


class CaffeineItem(Base):
    __tablename__ = "caffeine_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    default_caffeine_mg = Column(Numeric(6, 1), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    intake_records = relationship("IntakeRecord", back_populates="caffeine_item")


class IntakeRecord(Base):
    __tablename__ = "intake_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    caffeine_item_id = Column(Integer, ForeignKey("caffeine_items.id"), nullable=True)
    consumed_at = Column(DateTime, nullable=False, index=True)
    caffeine_mg = Column(Numeric(6, 1), nullable=False)
    weight_snapshot_kg = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="intake_records")
    caffeine_item = relationship("CaffeineItem", back_populates="intake_records")
