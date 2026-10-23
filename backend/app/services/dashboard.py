from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.models.room import Room
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.weekly_schedule_entry import WeeklyScheduleEntry
from app.services.lesson_participants import (
    load_lesson_participants,
    get_lesson_students_count,
)
from app.services.weekly_validation import validate_weekly_entries


def get_academic_week(target_date: date) -> dict:
    academic_year_start = (
        target_date.year
        if (target_date.month, target_date.day) >= (9, 1)
        else target_date.year - 1
    )
    september_first = date(academic_year_start, 9, 1)
    first_week_start = september_first - timedelta(
        days=september_first.weekday()
    )
    week_number = ((target_date - first_week_start).days // 7) + 1

    return {
        "academic_year": f"{academic_year_start}-{academic_year_start + 1}",
        "week_number": week_number,
        "week_type": "odd" if week_number % 2 else "even",
        "week_start": (
            target_date - timedelta(days=target_date.weekday())
        ).isoformat(),
    }


def get_daily_schedule(
    db: Session,
    target_date: date,
    teacher_id: int | None = None,
) -> dict:
    week = get_academic_week(target_date)

    entries = (
        db.query(WeeklyScheduleEntry)
        .filter(
            WeeklyScheduleEntry.weekday == target_date.weekday(),
            WeeklyScheduleEntry.week_type == week["week_type"],
        )
        .order_by(
            WeeklyScheduleEntry.start_time,
            WeeklyScheduleEntry.id,
        )
        .all()
    )

    lesson_ids = {entry.lesson_id for entry in entries}
    lessons = {
        lesson.id: lesson
        for lesson in db.query(Lesson)
        .filter(Lesson.id.in_(lesson_ids))
        .all()
    } if lesson_ids else {}

    room_ids = {entry.room_id for entry in entries}
    rooms = {
        room.id: room
        for room in db.query(Room).filter(Room.id.in_(room_ids)).all()
    } if room_ids else {}

    teacher_ids = {lesson.teacher_id for lesson in lessons.values()}
    teachers = {
        teacher.id: teacher
        for teacher in db.query(Teacher)
        .filter(Teacher.id.in_(teacher_ids))
        .all()
    } if teacher_ids else {}

    subject_ids = {lesson.subject_id for lesson in lessons.values()}
    subjects = {
        subject.id: subject
        for subject in db.query(Subject)
        .filter(Subject.id.in_(subject_ids))
        .all()
    } if subject_ids else {}

    participants = load_lesson_participants(db, list(lesson_ids))
    schedule = []

    for entry in entries:
        lesson = lessons.get(entry.lesson_id)
        room = rooms.get(entry.room_id)

        if lesson is None or room is None:
            raise ValueError(
                f"Запись {entry.id}: отсутствует занятие или аудитория."
            )

        teacher = teachers.get(lesson.teacher_id)
        subject = subjects.get(lesson.subject_id)

        if teacher is None or subject is None:
            raise ValueError(
                f"Занятие {lesson.id}: отсутствует преподаватель или предмет."
            )

        if teacher_id is not None and lesson.teacher_id != teacher_id:
            continue

        members = participants[lesson.id]
        labels = [
            member["group_name"]
            if member["subgroup_number"] == 0
            else (
                f'{member["group_name"]} '
                f'({member["subgroup_number"]}-я подгруппа)'
            )
            for member in members
        ]

        schedule.append({
            "id": entry.id,
            "lesson_id": lesson.id,
            "teacher_id": teacher.id,
            "time": entry.start_time.strftime("%H:%M"),
            "end": entry.end_time.strftime("%H:%M"),
            "subject": subject.name,
            "teacher": teacher.name,
            "group": ", ".join(labels),
            "groups": members,
            "group_ids": [member["group_id"] for member in members],
            "students_count": get_lesson_students_count(members),
            "lesson_type": lesson.lesson_type,
            "room": room.name,
            "room_type": room.room_type,
            "access_type": room.access_type,
        })

    return {
        "date": target_date.isoformat(),
        **week,
        "weekday": target_date.weekday(),
        "schedule": schedule,
    }


def get_dashboard_data(db: Session, target_date: date):
    result = get_daily_schedule(db, target_date)

    # Validate the complete day, including all teachers and groups.
    entries = (
        db.query(WeeklyScheduleEntry)
        .filter(
            WeeklyScheduleEntry.weekday == result["weekday"],
            WeeklyScheduleEntry.week_type == result["week_type"],
        )
        .all()
    )

    validation_error = None
    try:
        validate_weekly_entries(db, entries)
    except ValueError as exc:
        validation_error = str(exc)

    return {
        **result,
        "stats": {
            "lessons": db.query(Lesson).count(),
            "teachers": db.query(Teacher).count(),
            "rooms": db.query(Room).count(),
            # The validator stops at the first error.
            # None means the total number of problems is unknown.
            "problems": 0 if validation_error is None else None,
        },
        "validation": {
            "status": "valid" if validation_error is None else "invalid",
            "first_error": validation_error,
            "scope": "selected_day",
        },
        "optimization": None,
    }