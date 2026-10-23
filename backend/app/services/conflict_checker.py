from datetime import date, time

from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.models.schedule_entry import ScheduleEntry
from app.services.lesson_participants import (
    load_lesson_participants,
    participants_overlap,
)


def check_conflicts(
    db: Session,
    lesson_id: int,
    room_id: int,
    schedule_date: date,
    start_time: time,
    end_time: time,
    exclude_entry_id: int | None = None,
):
    """
    Check room, teacher and participant conflicts in dated schedules.

    When editing an existing entry, pass its ID as exclude_entry_id.
    Other occurrences of the same lesson still participate in checks.
    """
    if start_time >= end_time:
        return ["invalid_time"]

    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        return ["lesson_not_found"]

    query = (
        db.query(ScheduleEntry, Lesson)
        .join(Lesson, ScheduleEntry.lesson_id == Lesson.id)
        .filter(
            ScheduleEntry.date == schedule_date,
            ScheduleEntry.start_time < end_time,
            ScheduleEntry.end_time > start_time,
        )
    )

    if exclude_entry_id is not None:
        query = query.filter(
            ScheduleEntry.id != exclude_entry_id
        )

    existing_entries = query.all()

    lesson_ids = {lesson.id}
    lesson_ids.update(
        existing_lesson.id
        for _, existing_lesson in existing_entries
    )

    participants = load_lesson_participants(
        db, list(lesson_ids)
    )

    conflicts = set()

    for entry, existing_lesson in existing_entries:
        if entry.room_id == room_id:
            conflicts.add("room")

        if existing_lesson.teacher_id == lesson.teacher_id:
            conflicts.add("teacher")

        if participants_overlap(
            participants[lesson.id],
            participants[existing_lesson.id],
        ):
            conflicts.add("group")

    return sorted(conflicts)