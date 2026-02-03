from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Iterable, Optional, Tuple

from sqlalchemy.orm import Session

from . import models, schemas

MAX_DAILY_MG = 400.0
MAX_SINGLE_MG = 200.0
DAILY_MG_PER_KG = 5.7
SINGLE_MG_PER_KG = 3.0
ALERT_THRESHOLD_RATIO = 0.8
SLEEP_WINDOW_HOURS = 6


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        name=user.name,
        weight_kg=user.weight_kg,
        sleep_time=user.sleep_time,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, db_user: models.User, user_update: schemas.UserUpdate) -> models.User:
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(db_user, field, value)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_caffeine_item(db: Session, item: schemas.CaffeineItemCreate) -> models.CaffeineItem:
    db_item = models.CaffeineItem(
        name=item.name,
        default_caffeine_mg=item.default_caffeine_mg,
        description=item.description,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def list_caffeine_items(db: Session) -> Iterable[models.CaffeineItem]:
    return db.query(models.CaffeineItem).order_by(models.CaffeineItem.name).all()


def _calculate_single_limit(weight_kg: Optional[float]) -> float:
    limit_by_weight = weight_kg * SINGLE_MG_PER_KG if weight_kg else MAX_SINGLE_MG
    if weight_kg:
        return float(min(MAX_SINGLE_MG, limit_by_weight))
    return MAX_SINGLE_MG


def _calculate_daily_limit(weight_kg: Optional[float]) -> float:
    limit_by_weight = weight_kg * DAILY_MG_PER_KG if weight_kg else MAX_DAILY_MG
    if weight_kg:
        return float(min(MAX_DAILY_MG, limit_by_weight))
    return MAX_DAILY_MG


def _resolve_weight(user: models.User, weight_snapshot: Optional[float]) -> Optional[float]:
    if weight_snapshot is not None:
        return weight_snapshot
    if user.weight_kg is not None:
        return float(user.weight_kg)
    return None


def _day_bounds(moment: datetime) -> Tuple[datetime, datetime]:
    start = datetime.combine(moment.date(), time.min, tzinfo=moment.tzinfo)
    end = start + timedelta(days=1)
    return start, end


def _next_sleep_window(user: models.User, moment: datetime) -> Optional[Tuple[datetime, datetime]]:
    if user.sleep_time is None:
        return None
    sleep_time = datetime.combine(moment.date(), user.sleep_time, tzinfo=moment.tzinfo)
    if moment.time() > user.sleep_time:
        sleep_time += timedelta(days=1)
    window_start = sleep_time - timedelta(hours=SLEEP_WINDOW_HOURS)
    window_end = sleep_time
    return window_start, window_end


def _sleep_window_ok(user: models.User, consumed_at: datetime) -> bool:
    sleep_window = _next_sleep_window(user, consumed_at)
    if sleep_window is None:
        return True
    window_start, _ = sleep_window
    return consumed_at < window_start


def _build_status(
    *,
    single_ok: bool,
    single_limit: float,
    daily_ok: bool,
    daily_limit: float,
    sleep_ok: bool,
    daily_total: float,
    caffeine_mg: float,
) -> schemas.ThresholdStatus:
    message_parts = []
    if not single_ok:
        message_parts.append(
            f"单次摄入 {caffeine_mg:.1f}mg 超过上限 {single_limit:.1f}mg"
        )
    if not daily_ok:
        message_parts.append(
            f"当日累计 {daily_total:.1f}mg 超过上限 {daily_limit:.1f}mg"
        )
    if not sleep_ok:
        message_parts.append("距离预设睡眠时间不足 6 小时")
    message = "；".join(message_parts) if message_parts else None
    return schemas.ThresholdStatus(
        single_intake_ok=single_ok,
        single_intake_limit_mg=single_limit,
        daily_total_ok=daily_ok,
        daily_total_limit_mg=daily_limit,
        sleep_window_ok=sleep_ok,
        message=message,
    )


def create_intake_record(
    db: Session, *, user: models.User, payload: schemas.IntakeRecordCreate
) -> schemas.IntakeRecordResponse:
    weight = _resolve_weight(user, payload.weight_snapshot_kg)
    single_limit = _calculate_single_limit(weight)
    daily_limit = _calculate_daily_limit(weight)

    caffeine_mg = float(payload.caffeine_mg)
    single_ok = caffeine_mg <= single_limit

    day_start, day_end = _day_bounds(payload.consumed_at)
    existing_total = (
        db.query(models.IntakeRecord)
        .filter(
            models.IntakeRecord.user_id == user.id,
            models.IntakeRecord.consumed_at >= day_start,
            models.IntakeRecord.consumed_at < day_end,
        )
        .with_entities(models.IntakeRecord.caffeine_mg)
        .all()
    )
    total_before = sum(float(row.caffeine_mg) for row in existing_total)
    total_after = total_before + caffeine_mg
    daily_ok = total_after <= daily_limit

    sleep_ok = _sleep_window_ok(user, payload.consumed_at)

    record = models.IntakeRecord(
        user_id=user.id,
        caffeine_item_id=payload.caffeine_item_id,
        consumed_at=payload.consumed_at,
        caffeine_mg=payload.caffeine_mg,
        weight_snapshot_kg=payload.weight_snapshot_kg,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    status = _build_status(
        single_ok=single_ok,
        single_limit=single_limit,
        daily_ok=daily_ok,
        daily_limit=daily_limit,
        sleep_ok=sleep_ok,
        daily_total=total_after,
        caffeine_mg=caffeine_mg,
    )
    return schemas.IntakeRecordResponse(record=record, status=status)


def list_intake_records(db: Session, user_id: int, date: Optional[datetime] = None):
    query = db.query(models.IntakeRecord).filter(models.IntakeRecord.user_id == user_id)
    if date:
        day_start, day_end = _day_bounds(date)
        query = query.filter(
            models.IntakeRecord.consumed_at >= day_start,
            models.IntakeRecord.consumed_at < day_end,
        )
    return query.order_by(models.IntakeRecord.consumed_at.desc()).all()


def get_daily_summary(db: Session, user: models.User, date: datetime) -> dict:
    day_start, day_end = _day_bounds(date)
    records = (
        db.query(models.IntakeRecord)
        .filter(
            models.IntakeRecord.user_id == user.id,
            models.IntakeRecord.consumed_at >= day_start,
            models.IntakeRecord.consumed_at < day_end,
        )
        .all()
    )
    total = sum(float(r.caffeine_mg) for r in records)
    weight = _resolve_weight(user, None)
    daily_limit = _calculate_daily_limit(weight)
    status = _build_status(
        single_ok=True,
        single_limit=_calculate_single_limit(weight),
        daily_ok=total <= daily_limit,
        daily_limit=daily_limit,
        sleep_ok=True,
        daily_total=total,
        caffeine_mg=0.0,
    )
    return {
        "date": day_start.date().isoformat(),
        "total_caffeine_mg": total,
        "records": records,
        "status": status,
    }
