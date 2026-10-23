from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.teacher import Teacher
from app.services.dashboard import (
    get_dashboard_data,
    get_daily_schedule,
)


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("")
def dashboard(db: Session = Depends(get_db)):
    today = datetime.now(ZoneInfo("Asia/Yekaterinburg")).date()

    try:
        return get_dashboard_data(db=db, target_date=today)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/today")
def dashboard_today(
    teacher_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    if teacher_id is not None and db.get(Teacher, teacher_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Преподаватель не найден",
        )

    today = datetime.now(ZoneInfo("Asia/Yekaterinburg")).date()

    try:
        return get_daily_schedule(
            db=db,
            target_date=today,
            teacher_id=teacher_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc