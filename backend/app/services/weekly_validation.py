from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.models.lesson_requirement import LessonRequirement
from app.models.room import Room
from app.services.access import calculate_transition_time
from app.services.equipment import (
    load_equipment_profiles,
    room_has_required_profiles,
)
from app.services.lesson_participants import (
    load_lesson_participants,
    get_lesson_students_count,
    participants_overlap,
)
from app.services.lesson_times import get_lesson_pair


def validate_weekly_entries(db: Session, entries) -> None:
    """
    Validate supplied weekly entries without writing to the database.

    Pass the complete resulting schedule for the affected week.
    Weekly workload completeness is checked separately.
    """
    entries = list(entries)
    if not entries:
        return

    lesson_ids = {entry.lesson_id for entry in entries}
    room_ids = {entry.room_id for entry in entries}

    lessons = {
        item.id: item
        for item in db.query(Lesson)
        .filter(Lesson.id.in_(lesson_ids))
        .all()
    }
    rooms = {
        item.id: item
        for item in db.query(Room)
        .filter(Room.id.in_(room_ids))
        .all()
    }
    requirements = {
        item.lesson_id: item
        for item in db.query(LessonRequirement)
        .filter(LessonRequirement.lesson_id.in_(lesson_ids))
        .all()
    }

    participants = load_lesson_participants(db, list(lesson_ids))
    room_profiles, lesson_profiles = load_equipment_profiles(db)

    by_day = defaultdict(list)
    by_teacher_day = defaultdict(list)
    by_group_day = defaultdict(list)
    seen = set()

    for entry in entries:
        lesson = lessons.get(entry.lesson_id)
        room = rooms.get(entry.room_id)
        requirement = requirements.get(entry.lesson_id)

        if lesson is None or room is None or requirement is None:
            raise ValueError(
                f"Занятие {entry.lesson_id}: отсутствует занятие, "
                "аудитория или требования."
            )

        if entry.week_type not in {"odd", "even"}:
            raise ValueError("Недопустимый тип недели.")

        if entry.weekday not in range(7):
            raise ValueError("Недопустимый день недели.")

        if get_lesson_pair(entry.start_time, entry.end_time) is None:
            raise ValueError(
                f"Занятие {entry.lesson_id}: время не соответствует паре."
            )

        key = (entry.week_type, entry.weekday, entry.lesson_id)
        if key in seen:
            raise ValueError(
                f"Занятие {entry.lesson_id} повторяется в один день недели."
            )
        seen.add(key)

        students = get_lesson_students_count(
            participants[entry.lesson_id]
        )
        if room.capacity < max(students, requirement.min_capacity):
            raise ValueError(
                f"Занятие {entry.lesson_id}: аудитория {room.name} "
                "не вмещает участников."
            )

        sports_lesson = requirement.room_type == "gym"
        sports_room = room.room_type == "gym"

        if sports_lesson != sports_room:
            raise ValueError(
                "Спортзал допускается только для спортивных занятий; "
                "спортивные занятия должны проходить в спортзале."
            )

        if requirement.room_type and room.room_type != requirement.room_type:
            raise ValueError(
                f"Занятие {entry.lesson_id}: неверный тип аудитории."
            )

        if requirement.projector_required and not room.has_projector:
            raise ValueError(f"Аудитория {room.name}: нет проектора.")

        if requirement.computers_required and not room.has_computers:
            raise ValueError(f"Аудитория {room.name}: нет компьютеров.")

        if requirement.whiteboard_required and room.board_type != "whiteboard":
            raise ValueError(f"Аудитория {room.name}: нет требуемой доски.")

        if not room_has_required_profiles(
            room.id, lesson.id, room_profiles, lesson_profiles
        ):
            raise ValueError(
                f"Аудитория {room.name}: отсутствует специальное оборудование."
            )

        day = (entry.week_type, entry.weekday)
        by_day[day].append(entry)
        by_teacher_day[(*day, lesson.teacher_id)].append(entry)

        for member in participants[lesson.id]:
            by_group_day[(*day, member["group_id"])].append(entry)

    # Check room, teacher and student overlaps.
    for day_entries in by_day.values():
        for index, first in enumerate(day_entries):
            for second in day_entries[index + 1:]:
                if not (
                    first.start_time < second.end_time
                    and second.start_time < first.end_time
                ):
                    continue

                if first.room_id == second.room_id:
                    raise ValueError("Обнаружено пересечение занятости аудитории.")

                if (
                    lessons[first.lesson_id].teacher_id
                    == lessons[second.lesson_id].teacher_id
                ):
                    raise ValueError("Обнаружено пересечение занятий преподавателя.")

                if participants_overlap(
                    participants[first.lesson_id],
                    participants[second.lesson_id],
                ):
                    raise ValueError("Обнаружено пересечение занятий студентов.")

    # Check transitions between consecutive teacher lessons.
    for teacher_entries in by_teacher_day.values():
        ordered = sorted(teacher_entries, key=lambda item: item.start_time)

        for previous, current in zip(ordered, ordered[1:]):
            previous_room = rooms[previous.room_id]
            current_room = rooms[current.room_id]

            transition = calculate_transition_time(
                db=db,
                previous_room_id=previous.room_id,
                previous_access_type=previous_room.access_type,
                target_room_id=current.room_id,
                target_access_type=current_room.access_type,
            )

            available = (
                current.start_time.hour * 60 + current.start_time.minute
                - previous.end_time.hour * 60 - previous.end_time.minute
            )

            if transition is None or transition["total_time"] > available:
                raise ValueError(
                    f"Невозможен переход между занятиями "
                    f"{previous.lesson_id} и {current.lesson_id}."
                )

    # Sports must be first or last in every participating group's day.
    for group_entries in by_group_day.values():
        for sports in group_entries:
            if requirements[sports.lesson_id].room_type != "gym":
                continue

            others = [item for item in group_entries if item is not sports]
            has_before = any(
                item.end_time <= sports.start_time for item in others
            )
            has_after = any(
                item.start_time >= sports.end_time for item in others
            )

            if has_before and has_after:
                raise ValueError(
                    f"Физкультура {sports.lesson_id} находится "
                    "в середине учебного дня одной из групп."
                )