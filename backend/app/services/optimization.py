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
from app.services.teacher_conditions import (
    load_teacher_conditions, room_allowed, time_allowed, condition_issues,
    entrance_distances, entrance_cost, preferred_room_cost,
)
from app.services.lesson_times import LESSON_PAIRS, spans_long_break
from app.services.weekly_validation import validate_weekly_entries
from types import SimpleNamespace


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

def _required_transition_minutes(db, previous, current, lessons, rooms):
    """Known walking + key time, independent of whether the break is sufficient."""
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

    return required


def _transition_minutes(db, previous, current, lessons, rooms):
    """Feasible transition only. Keep this strict for search and validation."""
    required = _required_transition_minutes(db, previous, current, lessons, rooms)
    available = _minutes(current.start_time) - _minutes(previous.end_time)

    if required is None or available < 0 or required > available:
        return None

    return required

def _teacher_transition_total(entries, lessons, rooms, db, *, require_feasible=True):
    """Суммирует время переходов между занятиями преподавателей.

    По умолчанию требует допустимости всех переходов. Для аналитики
    require_feasible=False сохраняет известное время при коротком перерыве.
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
            if spans_long_break(previous, current):
                if require_feasible and _transition_minutes(db, previous, current, lessons, rooms) is None:
                    return None
                continue
            calculate = _transition_minutes if require_feasible else _required_transition_minutes
            value = calculate(db, previous, current, lessons, rooms)

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



def _sports_position_valid(entries, lessons, requirements, participants):
    for sport in entries:
        requirement = requirements.get(sport.lesson_id)
        if requirement is None or requirement.room_type != "gym":
            continue
        for member in participants[sport.lesson_id]:
            others = [entry for entry in entries if entry.id != sport.id
                      and entry.weekday == sport.weekday
                      and any(x["group_id"] == member["group_id"] for x in participants[entry.lesson_id])]
            if any(x.end_time <= sport.start_time for x in others) and any(x.start_time >= sport.end_time for x in others):
                return False
    return True


def _repair_teacher_conditions(db, entries, rooms_list, rooms, lessons, requirements,
                               participants, teachers, distances, teacher_id):
    room_profiles, lesson_profiles = load_equipment_profiles(db)
    for entry in entries:
        lesson = lessons[entry.lesson_id]
        teacher = teachers.get(lesson.teacher_id)
        if teacher_id is not None and teacher_id != lesson.teacher_id:
            continue
        if room_allowed(rooms[entry.room_id], teacher) and time_allowed(entry.start_time, teacher):
            continue
        requirement = requirements.get(lesson.id)
        students = get_lesson_students_count(participants[lesson.id])
        if requirement and requirement.room_type == "gym":
            candidates = [rooms[entry.room_id]]
        else:
            candidates = [room for room in rooms_list
                          if _room_fits(room, requirement, students)
                          and room_has_required_profiles(room.id, lesson.id, room_profiles, lesson_profiles)]
        candidates = [room for room in candidates if room_allowed(room, teacher)]
        candidates.sort(key=lambda room: (preferred_room_cost(room.id, teacher, lesson), entrance_cost(room.id, teacher, distances), room.id != entry.room_id, room.id))
        old = (entry.room_id, entry.start_time, entry.end_time)
        slots = [(start, end) for _, start, end in LESSON_PAIRS if time_allowed(start, teacher)]
        slots.sort(key=lambda slot: (slot != old[1:], slot[0]))
        found = False
        for start, end in slots:
            entry.start_time, entry.end_time = start, end
            for room in candidates:
                entry.room_id = room.id
                if _has_schedule_conflict(room, entry, entries, lessons, participants):
                    continue
                if not _check_teacher_transitions(db, entries, entry, lessons, rooms):
                    continue
                if not _sports_position_valid(entries, lessons, requirements, participants):
                    continue
                found = True
                break
            if found:
                break
        if not found:
            entry.room_id, entry.start_time, entry.end_time = old


def _repair_infeasible_transitions(
    db, entries, rooms_list, rooms, lessons, requirements, participants,
    teacher_id=None,
):
    """Repair walking violations on preview copies, without changing time slots.

    Try one room first, then both rooms of an adjacent pair. A proposal must
    remove that violation without introducing another one in the teacher's
    day. This is a bounded local search, not a guarantee of a global solution.
    """
    teachers = load_teacher_conditions(db)
    distances = entrance_distances(db)
    room_profiles, lesson_profiles = load_equipment_profiles(db)
    days = {}
    for entry in entries:
        lesson = lessons.get(entry.lesson_id)
        if lesson is not None and (teacher_id is None or lesson.teacher_id == teacher_id):
            days.setdefault((lesson.teacher_id, entry.weekday), []).append(entry)

    for (tid, _), day in sorted(days.items()):
        day.sort(key=lambda entry: (entry.start_time, entry.id))
        pairs = list(zip(day, day[1:]))
        teacher = teachers.get(tid)

        def state():
            bad, total = set(), 0
            for previous, current in pairs:
                value = _transition_minutes(db, previous, current, lessons, rooms)
                if value is None:
                    bad.add((previous.id, current.id))
                elif not spans_long_break(previous, current):
                    total += value
            return bad, total

        def candidates(entry):
            lesson = lessons[entry.lesson_id]
            if (_is_sports_entry(entry, rooms, requirements)
                    or not room_in_active_scope(rooms.get(entry.room_id))
                    or not time_allowed(entry.start_time, teacher)):
                return []
            students = get_lesson_students_count(participants[lesson.id])
            return [room for room in rooms_list
                    if room.id != entry.room_id
                    and _room_fits(room, requirements.get(lesson.id), students)
                    and room_allowed(room, teacher)
                    and room_has_required_profiles(room.id, lesson.id, room_profiles, lesson_profiles)
                    and not _has_schedule_conflict(room, entry, entries, lessons, participants)]

        while True:
            old_bad, _ = state()
            if not old_bad:
                break
            improved = False
            for first, second in pairs:
                target = (first.id, second.id)
                if target not in old_bad:
                    continue
                # With overlapping slots, changing rooms cannot fix the cause.
                if first.end_time > second.start_time:
                    continue
                pools = (candidates(first), candidates(second))
                best = None

                def consider(changes):
                    nonlocal best
                    original = [(entry, entry.room_id) for entry, _ in changes]
                    try:
                        for entry, room in changes:
                            entry.room_id = room.id
                        if any(_has_schedule_conflict(room, entry, entries, lessons, participants)
                               for entry, room in changes):
                            return
                        bad, total = state()
                        if target in bad or not bad.issubset(old_bad):
                            return
                        preference = sum(entrance_cost(entry.room_id, teacher, distances) for entry in day)
                        score = (len(bad), sum(preferred_room_cost(e.room_id, teacher, lessons[e.lesson_id]) for e in day), preference, total,
                                 tuple((entry.id, room.id) for entry, room in changes))
                        if best is None or score < best[0]:
                            best = (score, list(changes))
                    finally:
                        for entry, room_id in original:
                            entry.room_id = room_id

                for entry, pool in zip((first, second), pools):
                    for room in pool:
                        consider([(entry, room)])
                if best is None:
                    for first_room in pools[0]:
                        for second_room in pools[1]:
                            consider([(first, first_room), (second, second_room)])
                if best is not None:
                    for entry, room in best[1]:
                        entry.room_id = room.id
                    improved = True
                    break  # Recompute violations after every accepted repair.
            if not improved:
                break


def _optimize_occupied_room_swaps(
    db, entries, rooms, lessons, requirements, participants, teacher_id=None,
):
    """Swap occupied rooms atomically between simultaneous lessons of two teachers.

    Only full-week optimization may touch both teachers. Each trial changes
    both copies at once; the preview and apply validators remain authoritative.
    """
    if teacher_id is not None:
        return []

    teachers = load_teacher_conditions(db)
    distances = entrance_distances(db)
    room_profiles, lesson_profiles = load_equipment_profiles(db)
    by_slot = {}
    by_teacher_day = {}
    for entry in entries:
        lesson = lessons.get(entry.lesson_id)
        room = rooms.get(entry.room_id)
        if lesson is None or room is None:
            continue
        by_teacher_day.setdefault((lesson.teacher_id, entry.weekday), []).append(entry)
        if room_in_active_scope(room) and not _is_sports_entry(entry, rooms, requirements):
            key = (entry.weekday, entry.start_time, entry.end_time)
            by_slot.setdefault(key, []).append(entry)

    swaps = []
    # A strict improvement is required on every exchange, so reversals cannot
    # cycle; cap the number of accepted moves for predictable preview time.
    max_swaps = len(entries)
    while len(swaps) < max_swaps:
        accepted = False
        for slot in sorted(by_slot):
            candidates = sorted(by_slot[slot], key=lambda item: item.id)
            for index, first in enumerate(candidates):
                first_lesson = lessons[first.lesson_id]
                first_teacher = teachers.get(first_lesson.teacher_id)
                for second in candidates[index + 1:]:
                    second_lesson = lessons[second.lesson_id]
                    if first_lesson.teacher_id == second_lesson.teacher_id:
                        continue
                    if first.room_id == second.room_id:
                        continue
                    if participants_overlap(
                        participants[first.lesson_id], participants[second.lesson_id]
                    ):
                        continue

                    second_teacher = teachers.get(second_lesson.teacher_id)
                    first_room = rooms[first.room_id]
                    second_room = rooms[second.room_id]
                    first_req = requirements.get(first.lesson_id)
                    second_req = requirements.get(second.lesson_id)

                    if not (
                        time_allowed(first.start_time, first_teacher)
                        and time_allowed(second.start_time, second_teacher)
                        and _room_fits(
                            second_room, first_req,
                            get_lesson_students_count(participants[first.lesson_id]),
                        )
                        and _room_fits(
                            first_room, second_req,
                            get_lesson_students_count(participants[second.lesson_id]),
                        )
                        and room_allowed(second_room, first_teacher)
                        and room_allowed(first_room, second_teacher)
                        and room_has_required_profiles(
                            second_room.id, first.lesson_id, room_profiles, lesson_profiles
                        )
                        and room_has_required_profiles(
                            first_room.id, second.lesson_id, room_profiles, lesson_profiles
                        )
                    ):
                        continue

                    affected = (
                        by_teacher_day[(first_lesson.teacher_id, first.weekday)]
                        + by_teacher_day[(second_lesson.teacher_id, second.weekday)]
                    )

                    def score():
                        transitions = _teacher_transition_total(
                            affected, lessons, rooms, db
                        )
                        if transitions is None:
                            return None
                        return (
                            preferred_room_cost(
                                first.room_id, first_teacher, first_lesson
                            ) + preferred_room_cost(
                                second.room_id, second_teacher, second_lesson
                            ),
                            entrance_cost(first.room_id, first_teacher, distances)
                            + entrance_cost(second.room_id, second_teacher, distances),
                            transitions,
                        )

                    before = score()
                    if before is None:
                        continue

                    first.room_id, second.room_id = second.room_id, first.room_id
                    valid = (
                        not _has_schedule_conflict(
                            rooms[first.room_id], first, entries, lessons, participants
                        )
                        and not _has_schedule_conflict(
                            rooms[second.room_id], second, entries, lessons, participants
                        )
                        and _check_teacher_transitions(
                            db, entries, first, lessons, rooms
                        )
                        and _check_teacher_transitions(
                            db, entries, second, lessons, rooms
                        )
                    )
                    after = score() if valid else None
                    if after is not None and after < before:
                        swaps.append({
                            "first_entry_id": first.id,
                            "second_entry_id": second.id,
                            "first_lesson_id": first.lesson_id,
                            "second_lesson_id": second.lesson_id,
                            "first_teacher_id": first_lesson.teacher_id,
                            "second_teacher_id": second_lesson.teacher_id,
                            "weekday": first.weekday,
                            "start_time": first.start_time.strftime("%H:%M"),
                            "end_time": first.end_time.strftime("%H:%M"),
                            "first_old_room_id": first_room.id,
                            "second_old_room_id": second_room.id,
                        })
                        accepted = True
                        break

                    # Reject the trial: no ORM rows were changed.
                    first.room_id, second.room_id = second.room_id, first.room_id
                if accepted:
                    break
            if accepted:
                break
        if not accepted:
            break
    return swaps


def _optimize_entries(
    db, entries, rooms_list, rooms, lessons, requirements, participants,
    teacher_id: int | None = None,
):
    """Optimize eligible entries while retaining all conflict checks."""
    all_entries = entries
    teachers = load_teacher_conditions(db)
    distances = entrance_distances(db)

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

    def preference_total():
        return (
            sum(preferred_room_cost(e.room_id, teachers.get(lessons[e.lesson_id].teacher_id), lessons[e.lesson_id]) for e in active_entries),
            sum(entrance_cost(e.room_id, teachers.get(lessons[e.lesson_id].teacher_id), distances) for e in active_entries),
        )

    current_preference = preference_total()


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
            and room_allowed(room, teachers.get(lesson.teacher_id))
            and room_has_required_profiles(
                room.id,
                entry.lesson_id,
                room_profiles,
                lesson_profiles,
            )
        ]

        candidates.sort(key=lambda room: (preferred_room_cost(room.id, teachers.get(lesson.teacher_id), lesson), entrance_cost(room.id, teachers.get(lesson.teacher_id), distances), room.id))
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

            new_preference = preference_total()
            if new_total is not None and (new_preference, new_total) < (current_preference, current_total):
                current_preference = new_preference
                current_total = new_total
                break

            entry.room_id = old_room_id


def unchanged_baseline_transition_exemptions(db, before, after, lessons, rooms, teacher_id):
    """Only grandfather pre-existing impossible transitions of untouched OTHER teachers.

    Never exempt a transition involving a changed assignment, the selected
    teacher, or a newly adjacent pair.
    """
    if teacher_id is None:
        return set()
    originals = {e.id: e for e in before}
    results = {e.id: e for e in after}
    by_day = {}
    for e in before:
        lesson = lessons.get(e.lesson_id)
        if lesson is not None and lesson.teacher_id != teacher_id:
            by_day.setdefault((lesson.teacher_id, e.weekday), []).append(e)
    exempt = set()
    for key, items in by_day.items():
        items.sort(key=lambda e: (e.start_time, e.id))
        final_items = sorted(
            (e for e in after if lessons.get(e.lesson_id) is not None
             and lessons[e.lesson_id].teacher_id == key[0] and e.weekday == key[1]),
            key=lambda e: (e.start_time, e.id),
        )
        final_pairs = {(a.id, b.id) for a, b in zip(final_items, final_items[1:])}
        for a, b in zip(items, items[1:]):
            pair = (a.id, b.id)
            if pair not in final_pairs:
                continue
            if any(
                (originals[e.id].room_id, originals[e.id].start_time, originals[e.id].end_time)
                != (results[e.id].room_id, results[e.id].start_time, results[e.id].end_time)
                for e in (a, b)
            ):
                continue
            if _transition_minutes(db, a, b, lessons, rooms) is None:
                exempt.add(pair)
    return exempt


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

    originals = {item.id: (item.room_id, item.start_time, item.end_time) for item in entries}

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

    # A complete baseline copy for reporting (including non-target teachers).
    report_before_entries = [
        ScheduleItem(
            id=item.id, lesson_id=item.lesson_id, weekday=item.weekday,
            room_id=item.room_id, start_time=item.start_time, end_time=item.end_time,
        )
        for item in all_entries
    ]

    # 1. Рассчитываем время переходов до оптимизации.
    before_total = _teacher_transition_total(
        original_entries, lessons, rooms, db, require_feasible=False
    )

    teachers = load_teacher_conditions(db)
    distances = entrance_distances(db)
    _repair_teacher_conditions(db, all_entries, rooms_list, rooms, lessons, requirements,
                               participants, teachers, distances, teacher_id)

    _repair_infeasible_transitions(
        db, all_entries, rooms_list, rooms, lessons, requirements,
        participants, teacher_id,
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

    # Cross-teacher occupied-room exchanges are allowed only for full-week runs.
    room_swaps = _optimize_occupied_room_swaps(
        db=db,
        entries=all_entries,
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
            required = _required_transition_minutes(db, previous, current, lessons, rooms)
            available = _minutes(current.start_time) - _minutes(previous.end_time)
            if required is None or available < 0 or required > available:
                unknown_routes.append({
                    "previous_entry_id": previous.id,
                    "current_entry_id": current.id,
                    "required_minutes": required,
                    "available_minutes": available,
                    "reason": ("Маршрут или время доступа не определены" if required is None else
                               f"На переход нужно {required} мин, доступно {available} мин"),
                })

    # 4. Формируем список изменений аудиторий.
    changes = []

    for entry in all_entries:
        old_room_id, old_start, old_end = originals[entry.id]
        new_room_id = entry.room_id

        if (old_room_id, old_start, old_end) == (new_room_id, entry.start_time, entry.end_time):
            continue

        changes.append({
            "entry_id": entry.id,
            "lesson_id": entry.lesson_id,
            "weekday": entry.weekday,
            "start_time": entry.start_time.strftime("%H:%M"),
            "end_time": entry.end_time.strftime("%H:%M"),
            "old_start_time": old_start.strftime("%H:%M"),
            "old_end_time": old_end.strftime("%H:%M"),
            "new_start_time": entry.start_time.strftime("%H:%M"),
            "new_end_time": entry.end_time.strftime("%H:%M"),
            "old_room_id": old_room_id,
            "old_room_name": rooms[old_room_id].name,
            "new_room_id": new_room_id,
            "new_room_name": rooms[new_room_id].name,
        })

    # 5. Рассчитываем время переходов после оптимизации.
    after_total = _teacher_transition_total(
        entries, lessons, rooms, db, require_feasible=False
    )

    time_saved = (
        before_total - after_total
        if before_total is not None and after_total is not None
        else None
    )

    issues = condition_issues(all_entries, lessons, rooms, teachers)
    if not issues:
        try:
            validate_weekly_entries(db, [SimpleNamespace(**vars(entry), week_type=week_type) for entry in all_entries],
                exempt_transition_pairs=unchanged_baseline_transition_exemptions(
                    db, report_before_entries, all_entries, lessons, rooms, teacher_id))
        except ValueError as exc:
            issues.append({"entry_id": None, "teacher_id": None, "reason": str(exc)})
    warnings = []
    inherited = unchanged_baseline_transition_exemptions(db, report_before_entries, all_entries, lessons, rooms, teacher_id)
    if inherited:
        warnings.append(f"В расписании других преподавателей остаётся {len(inherited)} ранее существовавших невозможных переходов. Они не изменялись; их необходимо исправить отдельно.")
    if any(teacher.prefer_near_entrance for teacher in teachers.values()) and not distances:
        warnings.append("Нет маршрутов от входа: предпочтение близости сейчас не учитывается.")

    unfulfilled = sum(
        preferred_room_cost(e.room_id, teachers.get(lessons[e.lesson_id].teacher_id), lessons[e.lesson_id])
        for e in all_entries
        if teacher_id is None or lessons[e.lesson_id].teacher_id == teacher_id
    )
    if unfulfilled:
        warnings.append(f"Предпочтительная аудитория не назначена для {unfulfilled} занятий. "
                        "Предпочтения не обязательны: проверьте доступность аудиторий и остальные ограничения.")

    # Additive analytics; legacy response fields and apply payload are unchanged.
    from app.models.subject import Subject
    from app.services.optimization_report import build_optimization_report

    subject_ids = {lesson.subject_id for lesson in lessons.values()}
    subjects = {
        subject.id: subject
        for subject in db.query(Subject).filter(Subject.id.in_(subject_ids)).all()
    }
    detailed_report = build_optimization_report(
        db,
        before_entries=report_before_entries,
        after_entries=all_entries,
        lessons=lessons,
        rooms=rooms,
        participants=participants,
        teachers={teacher.id: teacher for teacher in db.query(Teacher).all()},
        subjects=subjects,
        requirements=requirements,
        week_type=week_type,
        selected_teacher_id=teacher_id,
    )

    insufficient_before = detailed_report["summary"]["insufficient_breaks_before"]
    if insufficient_before:
        warnings.append(f"До оптимизации: {insufficient_before} переходов не укладываются в перерыв. "
                        "Их известное время включено в сумму; это не означает допустимость расписания.")

    return {
        "constraint_issues": issues,
        "warnings": warnings,
        "can_apply": not issues and not unknown_routes,
        "changes": changes,
        "changes_count": len(changes),
        "room_swaps_count": len(room_swaps),
        "room_swaps": room_swaps,
        "transition_time_before": before_total,
        "transition_time_after": after_total,
        "time_saved": time_saved,
        "unknown_routes": unknown_routes,
        "saved_to_database": False,
        "week_type": week_type,
        "teacher_id": teacher_id,
        "eligible_entries_count": len(entries),
        "detailed_report": detailed_report,
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
