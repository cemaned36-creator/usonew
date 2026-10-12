from datetime import date, time

from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.models.schedule_entry import ScheduleEntry


def get_previous_entry(
    db: Session,
    teacher_id: int,
    schedule_date: date,
    start_time: time,
):
    """
    Возвращает предыдущее занятие преподавателя
    в этот день.

    Если предыдущего занятия нет, возвращает None.
    """

    previous_entry = (
        db.query(ScheduleEntry)
        .join(
            Lesson,
            ScheduleEntry.lesson_id == Lesson.id
        )
        .filter(
            Lesson.teacher_id == teacher_id,
            ScheduleEntry.date == schedule_date,
            ScheduleEntry.end_time <= start_time,
        )
        .order_by(
            ScheduleEntry.end_time.desc()
        )
        .first()
    )

    return previous_entry


def get_previous_room(
    db: Session,
    teacher_id: int,
    schedule_date: date,
    start_time: time,
):
    """
    Возвращает ID аудитории предыдущего занятия.

    Если предыдущего занятия нет, возвращает None.
    """

    previous_entry = get_previous_entry(
        db=db,
        teacher_id=teacher_id,
        schedule_date=schedule_date,
        start_time=start_time,
    )

    if not previous_entry:
        return None

    return previous_entry.room_id