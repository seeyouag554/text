from __future__ import annotations

from datetime import datetime
from typing import Generator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Caffeine Intake Tracker API")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users", response_model=schemas.UserRead, status_code=201)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db, user)


@app.get("/users/{user_id}", response_model=schemas.UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.patch("/users/{user_id}", response_model=schemas.UserRead)
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.update_user(db, db_user, payload)


@app.post("/caffeine-items", response_model=schemas.CaffeineItemRead, status_code=201)
def create_item(item: schemas.CaffeineItemCreate, db: Session = Depends(get_db)):
    return crud.create_caffeine_item(db, item)


@app.get("/caffeine-items", response_model=list[schemas.CaffeineItemRead])
def list_items(db: Session = Depends(get_db)):
    return crud.list_caffeine_items(db)


@app.post("/intake-records", response_model=schemas.IntakeRecordResponse, status_code=201)
def create_intake_record(payload: schemas.IntakeRecordCreate, db: Session = Depends(get_db)):
    user = crud.get_user(db, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.create_intake_record(db, user=user, payload=payload)


@app.get("/intake-records", response_model=list[schemas.IntakeRecordRead])
def list_records(
    user_id: int,
    date: Optional[datetime] = Query(None, description="Filter by specific day"),
    db: Session = Depends(get_db),
):
    return crud.list_intake_records(db, user_id=user_id, date=date)


@app.get("/summaries/daily", response_model=dict)
def get_daily_summary(
    user_id: int,
    date: datetime = Query(..., description="Date to summarize"),
    db: Session = Depends(get_db),
):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    summary = crud.get_daily_summary(db, user=user, date=date)
    summary["records"] = [schemas.IntakeRecordRead.from_orm(r) for r in summary["records"]]
    summary["status"] = summary["status"].dict()
    return summary
