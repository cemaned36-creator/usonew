import heapq
import random
from collections import Counter, defaultdict
from functools import lru_cache
from time import monotonic
from types import SimpleNamespace

from app.models.lesson import Lesson
from app.models.lesson_requirement import LessonRequirement
from app.models.lesson_teaching_load import LessonTeachingLoad
from app.models.room import Room
from app.models.room_connection import RoomConnection
from app.models.weekly_schedule_entry import WeeklyScheduleEntry
from app.services.access import (
    _get_key_desk_id,
    KEY_PICKUP_TIME,
    KEY_RETURN_TIME,
)
from app.services.equipment import (
    load_equipment_profiles,
    room_has_required_profiles,
)
from app.services.lesson_participants import (
    load_lesson_participants,
    get_lesson_students_count,
    participants_overlap,
)
from app.services.lesson_times import LESSON_PAIRS
from app.services.weekly_validation import validate_weekly_entries
from app.services.teacher_conditions import load_teacher_conditions, room_allowed, time_allowed, entrance_distances, entrance_cost


def minutes(value):
    return value.hour * 60 + value.minute


def build_transition_checker(db, rooms):
    """Load routes once. Search must not repeatedly query the database."""
    graph = defaultdict(list)

    for edge in db.query(RoomConnection).all():
        source = (
            ("R", edge.from_room_id)
            if edge.from_room_id is not None
            else ("A", edge.from_access_point_id)
        )
        target = (
            ("R", edge.to_room_id)
            if edge.to_room_id is not None
            else ("A", edge.to_access_point_id)
        )
        if source[1] is None or target[1] is None:
            raise ValueError("Connection has a missing endpoint")
        if edge.travel_time is None or edge.travel_time < 0:
            raise ValueError("Connection has invalid travel time")
        graph[source].append((target, edge.travel_time))

    desks = {
        room.id: _get_key_desk_id(db, room.id)
        for room in rooms.values()
        if room.access_type == "KEY"
    }

    @lru_cache(maxsize=None)
    def distances(source):
        result = {source: 0}
        queue = [(0, source)]
        while queue:
            elapsed, node = heapq.heappop(queue)
            if elapsed != result[node]:
                continue
            for target, weight in graph[node]:
                candidate = elapsed + weight
                if candidate < result.get(target, float("inf")):
                    result[target] = candidate
                    heapq.heappush(queue, (candidate, target))
        return result

    @lru_cache(maxsize=None)
    def transition(previous_id, target_id):
        previous = rooms[previous_id]
        target = rooms[target_id]
        allowed = {"OPEN", "PASS", "KEY"}

        if (
            previous.access_type not in allowed
            or target.access_type not in allowed
        ):
            return None

        previous_key = previous.access_type == "KEY"
        target_key = target.access_type == "KEY"
        previous_desk = desks.get(previous_id)
        target_desk = desks.get(target_id)

        if previous_key and previous_desk is None:
            return None
        if target_key and target_desk is None:
            return None
        if previous_id == target_id:
            return 0
        if previous_key and target_key and previous_desk != target_desk:
            return None

        route = [("R", previous_id)]
        key_time = 0

        if previous_key:
            route.append(("A", previous_desk))
            key_time += KEY_RETURN_TIME
        if target_key:
            desk_node = ("A", target_desk)
            if route[-1] != desk_node:
                route.append(desk_node)
            key_time += KEY_PICKUP_TIME

        route.append(("R", target_id))
        total = key_time

        for source, destination in zip(route, route[1:]):
            value = distances(source).get(destination)
            if value is None:
                return None
            total += value

        return total

    return transition


def generate_weekly_preview(
    db,
    week_type,
    *,
    seed=42,
    max_attempts=200,
    time_limit_seconds=60,
):
    """
    Generate a complete preview for source-linked lessons.

    Existing entries belonging to other lessons remain fixed.
    Existing entries of generated lessons are replaced in the preview.
    No ORM objects are added, updated or deleted.
    """
    if week_type not in {"odd", "even"}:
        raise ValueError("week_type must be odd or even")
    if max_attempts <= 0 or time_limit_seconds <= 0:
        raise ValueError("Search limits must be positive")

    new_lessons = (
        db.query(Lesson)
        .join(
            LessonTeachingLoad,
            LessonTeachingLoad.lesson_id == Lesson.id,
        )
        .distinct()
        .order_by(Lesson.id)
        .all()
    )
    if not new_lessons:
        raise ValueError("No lessons linked to teaching load")

    new_ids = {lesson.id for lesson in new_lessons}
    demand = {}

    for lesson in new_lessons:
        count = getattr(lesson, f"{week_type}_pairs")
        if count is None or count < 0 or count > 6:
            raise ValueError(
                f"Lesson {lesson.id}: invalid weekly demand {count}"
            )
        demand[lesson.id] = count

    existing = (
        db.query(WeeklyScheduleEntry)
        .filter(WeeklyScheduleEntry.week_type == week_type)
        .all()
    )
    fixed = [entry for entry in existing if entry.lesson_id not in new_ids]

    all_ids = new_ids | {entry.lesson_id for entry in fixed}
    lessons = {
        lesson.id: lesson
        for lesson in db.query(Lesson).filter(Lesson.id.in_(all_ids)).all()
    }
    requirements = {
        item.lesson_id: item
        for item in db.query(LessonRequirement)
        .filter(LessonRequirement.lesson_id.in_(all_ids))
        .all()
    }
    if all_ids - requirements.keys():
        raise ValueError("Some lessons have no requirements")

    members = load_lesson_participants(db, list(all_ids))
    groups = {
        lesson_id: {member["group_id"] for member in participants}
        for lesson_id, participants in members.items()
    }
    rooms = {room.id: room for room in db.query(Room).all()}
    room_profiles, lesson_profiles = load_equipment_profiles(db)
    sports = {
        lesson_id
        for lesson_id in all_ids
        if requirements[lesson_id].room_type == "gym"
    }

    teachers = load_teacher_conditions(db)
    distances_from_entrance = entrance_distances(db)
    candidates = {}
    for lesson in new_lessons:
        requirement = requirements[lesson.id]
        capacity = max(
            requirement.min_capacity,
            get_lesson_students_count(members[lesson.id]),
        )
        suitable = []

        for room in rooms.values():
            if not room_allowed(room, teachers.get(lesson.teacher_id)):
                continue
            if lesson.id in sports:
                if room.room_type != "gym":
                    continue
            elif room.building != "Б" or room.room_type == "gym":
                continue

            if room.capacity < capacity:
                continue
            if requirement.room_type and room.room_type != requirement.room_type:
                continue
            if requirement.projector_required and not room.has_projector:
                continue
            if requirement.computers_required and not room.has_computers:
                continue
            if requirement.whiteboard_required and room.board_type != "whiteboard":
                continue
            if not room_has_required_profiles(
                room.id, lesson.id, room_profiles, lesson_profiles
            ):
                continue
            suitable.append(room.id)

        candidates[lesson.id] = sorted(suitable)
        if demand[lesson.id] and not suitable:
            raise ValueError(f"Lesson {lesson.id}: no suitable rooms")

    # Validate the fixed part before starting the search.
    validate_weekly_entries(db, fixed)
    transition = build_transition_checker(db, rooms)

    @lru_cache(maxsize=None)
    def students_overlap(first_id, second_id):
        return participants_overlap(members[first_id], members[second_id])

    def can_place(entry, day_entries):
        lesson = lessons[entry.lesson_id]

        for other in day_entries:
            if other.lesson_id == entry.lesson_id:
                return False
            overlaps = (
                entry.start_time < other.end_time
                and other.start_time < entry.end_time
            )
            if overlaps and (
                entry.room_id == other.room_id
                or lesson.teacher_id == lessons[other.lesson_id].teacher_id
                or students_overlap(entry.lesson_id, other.lesson_id)
            ):
                return False

        teacher_entries = [
            other for other in day_entries
            if lessons[other.lesson_id].teacher_id == lesson.teacher_id
        ]
        teacher_entries.append(entry)
        teacher_entries.sort(key=lambda item: item.start_time)

        # Inserting an entry changes only its adjacent transitions.
        index = teacher_entries.index(entry)
        neighbours = []
        if index:
            neighbours.append((teacher_entries[index - 1], entry))
        if index + 1 < len(teacher_entries):
            neighbours.append((entry, teacher_entries[index + 1]))

        for previous, current in neighbours:
            required = transition(previous.room_id, current.room_id)
            available = minutes(current.start_time) - minutes(previous.end_time)
            if required is None or required > available:
                return False

        # Check sports for every group affected by this insertion.
        for group_id in groups[entry.lesson_id]:
            group_entries = [
                other for other in day_entries
                if group_id in groups[other.lesson_id]
            ]
            group_entries.append(entry)
            for sport in group_entries:
                if sport.lesson_id not in sports:
                    continue
                before = any(
                    other is not sport and other.end_time <= sport.start_time
                    for other in group_entries
                )
                after = any(
                    other is not sport and other.start_time >= sport.end_time
                    for other in group_entries
                )
                if before and after:
                    return False

        return True

    tasks = [
        (lesson_id, occurrence)
        for lesson_id, count in demand.items()
        for occurrence in range(count)
    ]
    teacher_load = Counter()
    for lesson_id, count in demand.items():
        teacher_load[lessons[lesson_id].teacher_id] += count

    expected = sum(demand.values())
    rng = random.Random(seed)
    deadline = monotonic() + time_limit_seconds
    best_count = -1
    best_missing = {}
    attempts = 0

    for attempt in range(1, max_attempts + 1):
        if monotonic() >= deadline:
            break
        attempts = attempt
        by_day = defaultdict(list)
        for entry in fixed:
            by_day[entry.weekday].append(entry)

        # Place sports, scarce rooms and shared lessons early.
        order = sorted(
            tasks,
            key=lambda task: (
                task[0] not in sports,
                len(candidates[task[0]]),
                -len(groups[task[0]]),
                -teacher_load[lessons[task[0]].teacher_id],
                rng.random(),
            ),
        )
        generated = []

        for lesson_id, occurrence in order:
            if monotonic() >= deadline:
                break

            slots = [
                (day, number, start, end)
                for day in range(6)
                for number, start, end in LESSON_PAIRS
                if time_allowed(start, teachers.get(lessons[lesson_id].teacher_id))
            ]
            rng.shuffle(slots)

            # Prefer days with fewer lessons for these groups.
            slots.sort(key=lambda slot: sum(
                bool(groups[lesson_id] & groups[item.lesson_id])
                for item in by_day[slot[0]]
            ))

            chosen = None
            for day, number, start, end in slots:
                room_ids = candidates[lesson_id].copy()
                rng.shuffle(room_ids)
                room_ids.sort(key=lambda room_id: entrance_cost(room_id, teachers.get(lessons[lesson_id].teacher_id), distances_from_entrance))
                for room_id in room_ids:
                    entry = SimpleNamespace(
                        id=-(len(generated) + 1),
                        lesson_id=lesson_id,
                        week_type=week_type,
                        weekday=day,
                        room_id=room_id,
                        start_time=start,
                        end_time=end,
                    )
                    if can_place(entry, by_day[day]):
                        chosen = entry
                        break
                if chosen is not None:
                    break

            if chosen is None:
                break

            generated.append(chosen)
            by_day[chosen.weekday].append(chosen)

        counts = Counter(entry.lesson_id for entry in generated)
        if len(generated) > best_count:
            best_count = len(generated)
            best_missing = {
                lesson_id: count - counts[lesson_id]
                for lesson_id, count in demand.items()
                if count != counts[lesson_id]
            }

        if len(generated) != expected:
            continue

        if any(counts[lesson_id] != count for lesson_id, count in demand.items()):
            raise RuntimeError("Generated workload differs from required workload")

        # Independent final validation using the application's existing service.
        validate_weekly_entries(db, [*fixed, *generated])

        return {
            "week_type": week_type,
            "status": "complete",
            "attempts": attempt,
            "expected_pairs": expected,
            "generated_pairs": len(generated),
            "fixed_entries": len(fixed),
            "entries": sorted(
                generated,
                key=lambda entry: (
                    entry.weekday, entry.start_time, entry.lesson_id
                ),
            ),
            "saved_to_database": False,
        }

    return {
        "week_type": week_type,
        "status": "search_limit",
        "attempts": attempts,
        "expected_pairs": expected,
        "best_generated_pairs": max(best_count, 0),
        "missing_pairs_by_lesson": best_missing,
        "entries": [],
        "saved_to_database": False,
    }