from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.lesson import Lesson
from app.models.room import Room
from app.models.student_group import StudentGroup
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.weekly_schedule_entry import WeeklyScheduleEntry
from app.services.dashboard import get_dashboard_data


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_academic_week(target_date: date) -> dict:
    """
    Учебная неделя 1 начинается в понедельник той недели,
    на которую приходится 1 сентября. Неделя 1 нечётная,
    неделя 2 чётная и далее по порядку.
    """
    academic_year_start = (
        target_date.year
        if (target_date.month, target_date.day) >= (9, 1)
        else target_date.year - 1
    )
    september_first = date(academic_year_start, 9, 1)
    first_week_start = september_first - timedelta(days=september_first.weekday())
    week_number = ((target_date - first_week_start).days // 7) + 1

    return {
        "academic_year": f"{academic_year_start}-{academic_year_start + 1}",
        "week_number": week_number,
        "week_type": "odd" if week_number % 2 == 1 else "even",
        "week_start": (target_date - timedelta(days=target_date.weekday())).isoformat(),
    }


@router.get("")
def dashboard(
    db: Session = Depends(get_db),
):
    """Возвращает данные для главной страницы."""
    today = datetime.now(ZoneInfo("Europe/Paris")).date()
    return get_dashboard_data(db=db, target_date=today)


@router.get("/today")
def dashboard_today(
    teacher_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """Возвращает занятия на сегодня из расписания нужной чётности недели."""
    today = datetime.now(ZoneInfo("Europe/Paris")).date()
    week = get_academic_week(today)

    query = (
        db.query(WeeklyScheduleEntry, Lesson, Teacher, Subject, StudentGroup, Room)
        .join(Lesson, Lesson.id == WeeklyScheduleEntry.lesson_id)
        .join(Teacher, Teacher.id == Lesson.teacher_id)
        .join(Subject, Subject.id == Lesson.subject_id)
        .join(StudentGroup, StudentGroup.id == Lesson.group_id)
        .join(Room, Room.id == WeeklyScheduleEntry.room_id)
        .filter(
            WeeklyScheduleEntry.weekday == today.weekday(),
            WeeklyScheduleEntry.week_type == week["week_type"],
        )
    )

    if teacher_id is not None:
        if not db.get(Teacher, teacher_id):
            raise HTTPException(status_code=404, detail="Преподаватель не найден")
        query = query.filter(Lesson.teacher_id == teacher_id)

    rows = query.order_by(WeeklyScheduleEntry.start_time).all()

    schedule = [
        {
            "id": entry.id,
            "lesson_id": lesson.id,
            "teacher_id": teacher.id,
            "time": entry.start_time.strftime("%H:%M"),
            "end": entry.end_time.strftime("%H:%M"),
            "subject": subject.name,
            "teacher": teacher.name,
            "group": group.name,
            "room": room.name,
            "room_type": room.room_type,
            "access_type": room.access_type,
        }
        for entry, lesson, teacher, subject, group, room in rows
    ]

    return {
        "date": today.isoformat(),
        **week,
        "weekday": today.weekday(),
        "schedule": schedule,
    }
