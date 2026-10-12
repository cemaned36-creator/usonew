from datetime import date, time

from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.models.schedule_entry import ScheduleEntry


def check_conflicts(
    db: Session,
    lesson_id: int,
    room_id: int,
    schedule_date: date,
    start_time: time,
    end_time: time,
):
    """
    Проверяет, есть ли конфликты для занятия.

    Проверяются:
    - занята ли аудитория;
    - занят ли преподаватель;
    - занята ли учебная группа.

    Возвращает список найденных конфликтов.
    Если список пустой — конфликтов нет.
    """

    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .first()
    )

    if not lesson:
        return ["lesson_not_found"]

    existing_entries = (
        db.query(ScheduleEntry, Lesson)
        .join(
            Lesson,
            ScheduleEntry.lesson_id == Lesson.id
        )
        .filter(
            ScheduleEntry.date == schedule_date,
            ScheduleEntry.start_time < end_time,
            ScheduleEntry.end_time > start_time,
            ScheduleEntry.lesson_id != lesson_id,
        )
        .all()
    )

    conflicts = []

    for entry, existing_lesson in existing_entries:

        # Конфликт аудитории
        if entry.room_id == room_id:
            conflicts.append("room")

        # Конфликт преподавателя
        if existing_lesson.teacher_id == lesson.teacher_id:
            conflicts.append("teacher")

        # Конфликт учебной группы
        if existing_lesson.group_id == lesson.group_id:
            conflicts.append("group")

    # Убираем повторяющиеся значения
    return list(set(conflicts))