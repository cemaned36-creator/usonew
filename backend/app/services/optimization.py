
from dataclasses import dataclass
from datetime import time

from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.models.lesson_requirement import LessonRequirement
from app.models.room import Room
from app.models.student_group import StudentGroup
from app.models.weekly_schedule_entry import WeeklyScheduleEntry
from app.services.access import calculate_transition_time


@dataclass
class ScheduleItem:
    """Копия записи расписания, не отслеживаемая SQLAlchemy."""

    id: int
    lesson_id: int
    weekday: int
    room_id: int
    start_time: time
    end_time: time


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _overlaps(first, second) -> bool:
    return (
        _minutes(first.start_time) < _minutes(second.end_time)
        and _minutes(second.start_time) < _minutes(first.end_time)
    )


def _room_fits(room, requirement, group) -> bool:
    """Проверяет вместимость и оборудование аудитории."""

    if group is None:
        return False

    if room.capacity < group.students_count:
        return False

    if requirement is None:
        return True

    if room.capacity < requirement.min_capacity:
        return False

    if requirement.room_type and room.room_type != requirement.room_type:
        return False

    if requirement.projector_required and not room.has_projector:
        return False

    if requirement.computers_required and not room.has_computers:
        return False

    if requirement.whiteboard_required and room.board_type != "whiteboard":
        return False

    return True


def _has_schedule_conflict(candidate, entry, entries, lessons) -> bool:
    """Проверяет конфликты аудитории, преподавателя и группы."""

    lesson = lessons.get(entry.lesson_id)
    if lesson is None:
        return True

    for other in entries:
        if other.id == entry.id or other.weekday != entry.weekday:
            continue

        if not _overlaps(entry, other):
            continue

        other_lesson = lessons.get(other.lesson_id)
        if other_lesson is None:
            return True

        if other.room_id == candidate.id:
            return True

        if other_lesson.teacher_id == lesson.teacher_id:
            return True

        if other_lesson.group_id == lesson.group_id:
            return True

    return False


def _transition_minutes(db, previous, current, lessons, rooms):
    """Возвращает время перехода или None, если переход невозможен."""

    previous_lesson = lessons.get(previous.lesson_id)
    current_lesson = lessons.get(current.lesson_id)

    if previous_lesson is None or current_lesson is None:
        return None

    if previous_lesson.teacher_id != current_lesson.teacher_id:
        return 0

    previous_room = rooms.get(previous.room_id)
    current_room = rooms.get(current.room_id)

    if previous_room is None or current_room is None:
        return None

    result = calculate_transition_time(
        db=db,
        previous_room_id=previous.room_id,
        previous_access_type=previous_room.access_type,
        target_room_id=current.room_id,
        target_access_type=current_room.access_type,
    )

    if result is None:
        return None

    available_minutes = (
        _minutes(current.start_time) - _minutes(previous.end_time)
    )

    if available_minutes < 0 or result["total_time"] > available_minutes:
        return None

    return result["total_time"]



def _teacher_transition_total(entries, lessons, rooms, db):
    """Суммирует время переходов между занятиями преподавателей.

    Возвращает None, если хотя бы один необходимый переход
    невозможно рассчитать.
    """
    by_teacher_day = {}

    for entry in entries:
        lesson = lessons.get(entry.lesson_id)
        if lesson is None:
            continue

        key = (lesson.teacher_id, entry.weekday)
        by_teacher_day.setdefault(key, []).append(entry)

    total = 0

    for teacher_entries in by_teacher_day.values():
        teacher_entries.sort(
            key=lambda item: _minutes(item.start_time)
        )

        for previous, current in zip(
            teacher_entries, teacher_entries[1:]
        ):
            value = _transition_minutes(
                db, previous, current, lessons, rooms
            )

            if value is None:
                return None

            total += value

    return total



def _check_teacher_transitions(
    db, entries, changed_entry, lessons, rooms
):
    """Проверяет переходы, затрагивающие изменённое занятие."""

    lesson = lessons.get(changed_entry.lesson_id)
    if lesson is None:
        return False

    teacher_entries = [
        item
        for item in entries
        if item.weekday == changed_entry.weekday
        and lessons.get(item.lesson_id) is not None
        and lessons[item.lesson_id].teacher_id == lesson.teacher_id
    ]

    teacher_entries.sort(key=lambda item: _minutes(item.start_time))

    for previous, current in zip(teacher_entries, teacher_entries[1:]):
        if previous.id != changed_entry.id and current.id != changed_entry.id:
            continue

        if _transition_minutes(
            db, previous, current, lessons, rooms
        ) is None:
            return False

    return True


def _optimize_entries(
    db, entries, rooms_list, rooms, lessons, requirements, groups
):
    """Подбирает аудитории для копий записей расписания."""

    current_total = _teacher_transition_total(
        entries, lessons, rooms, db
    )
    if current_total is None:
        return
    
    for entry in entries:
        lesson = lessons.get(entry.lesson_id)

        if lesson is None or entry.room_id not in rooms:
            continue

        requirement = requirements.get(entry.lesson_id)
        group = groups.get(lesson.group_id)

        candidates = [
            room
            for room in rooms_list
            if room.id != entry.room_id
            and _room_fits(room, requirement, group)
        ]

        for candidate in candidates:
            if _has_schedule_conflict(
                candidate, entry, entries, lessons
            ):
                continue

            old_room_id = entry.room_id
            entry.room_id = candidate.id

            if not _check_teacher_transitions(
                db, entries, entry, lessons, rooms
            ):
                entry.room_id = old_room_id
                continue

            new_total = _teacher_transition_total(
                entries, lessons, rooms, db
            )

            if new_total < current_total:
                current_total = new_total
                break

            entry.room_id = old_room_id


def preview_optimization(db: Session):
    """
    Формирует предварительный план назначений.
    Изменяет только копии расписания, не ORM-записи.
    """

    db_entries = (
        db.query(WeeklyScheduleEntry)
        .order_by(
            WeeklyScheduleEntry.weekday,
            WeeklyScheduleEntry.start_time,
        )
        .all()
    )

    entries = [
        ScheduleItem(
            id=item.id,
            lesson_id=item.lesson_id,
            weekday=item.weekday,
            room_id=item.room_id,
            start_time=item.start_time,
            end_time=item.end_time,
        )
        for item in db_entries
    ]

    original_room_ids = {
        item.id: item.room_id for item in entries
    }

    rooms_list = db.query(Room).all()
    rooms = {room.id: room for room in rooms_list}

    lessons = {
        lesson.id: lesson for lesson in db.query(Lesson).all()
    }

    requirements = {
        item.lesson_id: item
        for item in db.query(LessonRequirement).all()
    }

    groups = {
        group.id: group for group in db.query(StudentGroup).all()
    }

    unknown_routes = []
    by_teacher_day = {}

    for entry in entries:
        lesson = lessons.get(entry.lesson_id)
        if lesson is not None:
            by_teacher_day.setdefault(
                (lesson.teacher_id, entry.weekday), []
            ).append(entry)

    for teacher_entries in by_teacher_day.values():
        teacher_entries.sort(key=lambda item: _minutes(item.start_time))

        for previous, current in zip(teacher_entries, teacher_entries[1:]):
            if _transition_minutes(
                db, previous, current, lessons, rooms
            ) is None:
                unknown_routes.append({
                    "previous_entry_id": previous.id,
                    "current_entry_id": current.id,
                    "reason": (
                        "Маршрут отсутствует или времени "
                        "на переход недостаточно"
                    ),
                })

    original_entries = [
        ScheduleItem(
            id=item.id,
            lesson_id=item.lesson_id,
            weekday=item.weekday,
            room_id=item.room_id,
            start_time=item.start_time,
            end_time=item.end_time,
        )
        for item in entries
    ]

    before_total = _teacher_transition_total(
        original_entries, lessons, rooms, db
    )

    _optimize_entries(
        db=db,
        entries=entries,
        rooms_list=rooms_list,
        rooms=rooms,
        lessons=lessons,
        requirements=requirements,
        groups=groups,
    )

    changes = []

    for entry in entries:
        old_room_id = original_room_ids[entry.id]
        new_room_id = entry.room_id

        if old_room_id == new_room_id:
            continue

        changes.append({
            "entry_id": entry.id,
            "lesson_id": entry.lesson_id,
            "weekday": entry.weekday,
            "start_time": entry.start_time.strftime("%H:%M"),
            "end_time": entry.end_time.strftime("%H:%M"),
            "old_room_id": old_room_id,
            "old_room_name": rooms[old_room_id].name,
            "new_room_id": new_room_id,
            "new_room_name": rooms[new_room_id].name,
        })

    after_total = _teacher_transition_total(
        entries, lessons, rooms, db
    )

    return {
        "changes": changes,
        "changes_count": len(changes),
        "transition_time_before": before_total,
        "transition_time_after": after_total,
        "time_saved": max(0, before_total - after_total),
        "unknown_routes": unknown_routes,
        "saved_to_database": False,
    }

