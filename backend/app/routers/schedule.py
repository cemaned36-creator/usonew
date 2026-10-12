
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.scheduler import generate_schedule

import app.services.scheduler as scheduler_module

print("[DEBUG] scheduler.py загружен из:", scheduler_module.__file__)

router = APIRouter(prefix="/schedule", tags=["Schedule"])

print("[DEBUG] Вызван endpoint генерации расписания")
@router.post("/generate")
def generate(
    start_date: date | None = None,
    days_ahead: int = Query(default=7, ge=1, le=31),
    weekdays_only: bool = True,
    db: Session = Depends(get_db),
):
    start = start_date or date.today()

    try:
        created = generate_schedule(
            db=db,
            start_date=start,
            days_ahead=days_ahead,
            weekdays_only=weekdays_only,
        )

        return {
            "status": "success",
            "start_date": start.isoformat(),
            "end_date": (
                start + timedelta(days=days_ahead - 1)
            ).isoformat(),
            "created_count": len(created),
            "created": [
                {
                    "entry_id": entry.id,
                    "lesson_id": entry.lesson_id,
                    "room_id": entry.room_id,
                    "date": entry.date.isoformat(),
                    "start_time": entry.start_time.strftime("%H:%M"),
                    "end_time": entry.end_time.strftime("%H:%M"),
                }
                for entry in created
            ],
        }

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось создать расписание: {exc}",
        ) from exc