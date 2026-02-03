from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, validator


class UserCreate(BaseModel):
    name: str
    weight_kg: Optional[float] = None
    sleep_time: Optional[time] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    weight_kg: Optional[float] = None
    sleep_time: Optional[time] = None


class UserRead(BaseModel):
    id: int
    name: str
    weight_kg: Optional[float]
    sleep_time: Optional[time]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class CaffeineItemCreate(BaseModel):
    name: str
    default_caffeine_mg: float
    description: Optional[str] = None


class CaffeineItemRead(BaseModel):
    id: int
    name: str
    default_caffeine_mg: float
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class IntakeRecordBase(BaseModel):
    caffeine_item_id: Optional[int] = None
    consumed_at: datetime
    caffeine_mg: float
    weight_snapshot_kg: Optional[float] = None
    notes: Optional[str] = None

    @validator("caffeine_mg")
    def validate_caffeine_mg(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Caffeine amount must be positive")
        return value


class IntakeRecordCreate(IntakeRecordBase):
    user_id: int


class IntakeRecordRead(IntakeRecordBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ThresholdStatus(BaseModel):
    single_intake_ok: bool
    single_intake_limit_mg: float
    daily_total_ok: bool
    daily_total_limit_mg: float
    sleep_window_ok: bool
    message: Optional[str] = None


class IntakeRecordResponse(BaseModel):
    record: IntakeRecordRead
    status: ThresholdStatus
