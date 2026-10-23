from dataclasses import dataclass
from datetime import time

from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.models.lesson_requirement import LessonRequirement
from app.models.room import Room
from app.services.lesson_participants import (
    load_lesson_participants,
    get_lesson_students_count,
    participants_overlap,
)
from app.models.weekly_schedule_entry import WeeklyScheduleEntry
from app.services.access import calculate_transition_time
from app.services.room_scope import room_in_active_scope
from app.services.equipment import (
    load_equipment_profiles,
    room_has_required_profiles,
)
from app.models.teacher import Teacher

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


def _room_fits(room, requirement, students_count: int) -> bool:
    """Check room capacity, type and equipment."""
    if room is None or requirement is None:
        return False

    if students_count <= 0:
        return False

    if not room_in_active_scope(room):
        return False

    if room.room_type == "gym" or requirement.room_type == "gym":
        return False

    if room.capacity < max(students_count, requirement.min_capacity):
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

def _has_schedule_conflict(
    candidate, entry, entries, lessons, participants
) -> bool:
    """Check conflicts against all entries of the selected week."""
    lesson = lessons.get(entry.lesson_id)
    members = participants.get(entry.lesson_id)

    if lesson is None or not members:
        return True

    for other in entries:
        if other.id == entry.id or other.weekday != entry.weekday:
            continue

        if not _overlaps(entry, other):
            continue

        other_lesson = lessons.get(other.lesson_id)
        other_members = participants.get(other.lesson_id)

        if other_lesson is None or not other_members:
            return True

        if other.room_id == candidate.id:
            return True

        if other_lesson.teacher_id == lesson.teacher_id:
            return True

        if participants_overlap(members, other_members):
            return True

    return False

def _transition_minutes(db, previous, current, lessons, rooms):
    """Время перехода с учётом доступного перерыва."""
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

    checker = db.info.get("_optimization_transition_checker")

    if checker is not None:
        required = checker(previous.room_id, current.room_id)
    else:
        result = calculate_transition_time(
            db=db,
            previous_room_id=previous.room_id,
            previous_access_type=previous_room.access_type,
            target_room_id=current.room_id,
            target_access_type=current_room.access_type,
        )
        required = None if result is None else result["total_time"]

    available = _minutes(current.start_time) - _minutes(previous.end_time)

    if required is None or available < 0 or required > available:
        return None

    return required

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

    for previous, current in zip(
        teacher_entries, teacher_entries[1:]
    ):
        if previous.id != changed_entry.id and current.id != changed_entry.id:
            continue

        if _transition_minutes(
            db, previous, current, lessons, rooms
        ) is None:
            return False

    return True


def _is_sports_entry(entry, rooms, requirements) -> bool:
    """Определяет занятие спорткомплекса по помещению или требованиям."""
    room = rooms.get(entry.room_id)
    requirement = requirements.get(entry.lesson_id)

    return (
        (room is not None and room.room_type == "gym")
        or (
            requirement is not None
            and requirement.room_type == "gym"
        )
    )



def _optimize_entries(
    db, entries, rooms_list, rooms, lessons, requirements, participants,
    teacher_id: int | None = None,
):
    """Optimize eligible entries while retaining all conflict checks."""
    all_entries = entries

    active_entries = [
        entry
        for entry in all_entries
        if room_in_active_scope(rooms.get(entry.room_id))
        and not _is_sports_entry(entry, rooms, requirements)
        and (
            teacher_id is None
            or lessons[entry.lesson_id].teacher_id == teacher_id
        )
    ]

    current_total = _teacher_transition_total(
        active_entries, lessons, rooms, db
    )

    if current_total is None:
        return


    room_profiles, lesson_profiles = load_equipment_profiles(db)


    for entry in active_entries:
        lesson = lessons.get(entry.lesson_id)
        if lesson is None or entry.room_id not in rooms:
            continue

        requirement = requirements.get(entry.lesson_id)
        students_count = get_lesson_students_count(
            participants[entry.lesson_id]
        )

        candidates = [
            room
            for room in rooms_list
            if room.id != entry.room_id
            and _room_fits(room, requirement, students_count)
            and room_has_required_profiles(
                room.id,
                entry.lesson_id,
                room_profiles,
                lesson_profiles,
            )
        ]

        for candidate in candidates:
            if _has_schedule_conflict(
                candidate, entry, all_entries, lessons, participants
            ):
                continue

            old_room_id = entry.room_id
            entry.room_id = candidate.id

            # Include neighbouring teacher lessons outside the active scope.
            if not _check_teacher_transitions(
                db, all_entries, entry, lessons, rooms
            ):
                entry.room_id = old_room_id
                continue

            new_total = _teacher_transition_total(
                active_entries, lessons, rooms, db
            )

            if new_total is not None and new_total < current_total:
                current_total = new_total
                break

            entry.room_id = old_room_id


def _preview_optimization(
    db: Session,
    week_type: str = "odd",
    teacher_id: int | None = None,
):
    """
    Формирует предварительный план назначений.
    Изменяет только копии расписания, не ORM-записи.
    """

    if week_type not in {"odd", "even"}:
        raise ValueError("week_type должен быть odd или even")

    db_entries = (
        db.query(WeeklyScheduleEntry)
        .filter(WeeklyScheduleEntry.week_type == week_type)
        .order_by(
            WeeklyScheduleEntry.weekday,
            WeeklyScheduleEntry.start_time,
            WeeklyScheduleEntry.id,
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

    rooms_list = db.query(Room).order_by(Room.id).all()
    rooms = {room.id: room for room in rooms_list}

    lessons = {
        lesson.id: lesson for lesson in db.query(Lesson).all()
    }

    requirements = {
        item.lesson_id: item
        for item in db.query(LessonRequirement).all()
    }

    all_entries = entries

    participants = load_lesson_participants(
        db,
        list({entry.lesson_id for entry in all_entries}),
    )

    # Исключаем спорткомплекс из показателей до/после
    # и из списка маршрутов, требующих проверки.
    entries = [
        entry
        for entry in all_entries
        if room_in_active_scope(rooms.get(entry.room_id))
        and not _is_sports_entry(entry, rooms, requirements)
        and (
            teacher_id is None
            or lessons[entry.lesson_id].teacher_id == teacher_id
        )
    ]


    # Сохраняем исходное расписание для расчёта показателей до оптимизации.
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

    # 1. Рассчитываем время переходов до оптимизации.
    before_total = _teacher_transition_total(
        original_entries, lessons, rooms, db
    )

    # 2. Оптимизируем копии расписания.
    _optimize_entries(
        db=db,
        entries=all_entries,
        rooms_list=rooms_list,
        rooms=rooms,
        lessons=lessons,
        requirements=requirements,
        participants=participants,
        teacher_id=teacher_id,
    )

    # 3. Пересчитываем unknown_routes по итоговому расписанию.
    unknown_routes = []
    by_teacher_day = {}

    for entry in entries:
        lesson = lessons.get(entry.lesson_id)
        if lesson is not None:
            by_teacher_day.setdefault(
                (lesson.teacher_id, entry.weekday), []
            ).append(entry)

    for teacher_entries in by_teacher_day.values():
        teacher_entries.sort(
            key=lambda item: _minutes(item.start_time)
        )

        for previous, current in zip(
            teacher_entries, teacher_entries[1:]
        ):
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

    # 4. Формируем список изменений аудиторий.
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

    # 5. Рассчитываем время переходов после оптимизации.
    after_total = _teacher_transition_total(
        entries, lessons, rooms, db
    )

    time_saved = (
        max(0, before_total - after_total)
        if before_total is not None and after_total is not None
        else None
    )

    return {
        "changes": changes,
        "changes_count": len(changes),
        "transition_time_before": before_total,
        "transition_time_after": after_total,
        "time_saved": time_saved,
        "unknown_routes": unknown_routes,
        "saved_to_database": False,
        "week_type": week_type,
        "teacher_id": teacher_id,
        "eligible_entries_count": len(entries),
    }

def preview_optimization(
    db: Session,
    week_type: str = "odd",
    teacher_id: int | None = None,
):
    """Use a fresh route cache for this preview only."""
    from app.services.weekly_generator import build_transition_checker

    if week_type not in {"odd", "even"}:
        raise ValueError("week_type должен быть odd или even")

    if teacher_id is not None:
        if teacher_id <= 0 or db.get(Teacher, teacher_id) is None:
            raise ValueError("Преподаватель не найден")

    rooms = {room.id: room for room in db.query(Room).all()}
    checker = build_transition_checker(db, rooms)

    key = "_optimization_transition_checker"
    previous_checker = db.info.get(key)
    db.info[key] = checker

    try:
        return _preview_optimization(
            db,
            week_type=week_type,
            teacher_id=teacher_id,
        )
    finally:
        if previous_checker is None:
            db.info.pop(key, None)
        else:
            db.info[key] = previous_checker
