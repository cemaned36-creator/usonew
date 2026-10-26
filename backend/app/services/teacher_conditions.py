"""Shared hard constraints and entrance preference for scheduling services."""
import heapq
from collections import defaultdict
from app.models.teacher import Teacher
from app.models.room_connection import RoomConnection
from app.services.lesson_times import LESSON_PAIRS
from app.services.key_desks import main_key_desk_id


def load_teacher_conditions(db):
    return {teacher.id: teacher for teacher in db.query(Teacher).all()}


def room_allowed(room, teacher):
    maximum = getattr(teacher, "max_floor", None)
    return maximum is None or room.floor <= maximum


def time_allowed(start_time, teacher):
    earliest = getattr(teacher, "earliest_start_pair", 1) or 1
    return start_time >= LESSON_PAIRS[earliest - 1][1]


def condition_issues(entries, lessons, rooms, teachers):
    issues = []
    for entry in entries:
        teacher = teachers.get(lessons[entry.lesson_id].teacher_id)
        if not time_allowed(entry.start_time, teacher):
            issues.append({"entry_id": entry.id, "teacher_id": teacher.id,
                           "reason": f"{teacher.name}: занятие начинается раньше разрешённой пары №{teacher.earliest_start_pair}."})
        if not room_allowed(rooms[entry.room_id], teacher):
            issues.append({"entry_id": entry.id, "teacher_id": teacher.id,
                           "reason": f"{teacher.name}: аудитория выше разрешённого этажа {teacher.max_floor}."})
    return issues


def entrance_distances(db):
    """Walking minutes from the entrance, including the cost of stair detours.

    The historical name is retained for callers. Corridor-only metres would
    make stairs appear free; route time is the accessibility cost instead.
    """
    desk_id = main_key_desk_id(db)
    if desk_id is None:
        return {}
    graph = defaultdict(list)
    for edge in db.query(RoomConnection).all():
        source = ("R", edge.from_room_id) if edge.from_room_id is not None else ("A", edge.from_access_point_id)
        target = ("R", edge.to_room_id) if edge.to_room_id is not None else ("A", edge.to_access_point_id)
        if source[1] is not None and target[1] is not None and edge.travel_time is not None and edge.travel_time >= 0:
            graph[source].append((target, float(edge.travel_time)))
    source = ("A", desk_id)
    distances = {source: 0.0}
    queue = [(0.0, source)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue
        for target, weight in graph[node]:
            candidate = distance + weight
            if candidate < distances.get(target, float("inf")):
                distances[target] = candidate
                heapq.heappush(queue, (candidate, target))
    return {node[1]: value for node, value in distances.items() if node[0] == "R"}


def entrance_cost(room_id, teacher, distances):
    if not getattr(teacher, "prefer_near_entrance", False):
        return 0.0
    return distances.get(room_id, float("inf"))
