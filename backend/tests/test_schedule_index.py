from datetime import time
from types import SimpleNamespace as NS
from app.services.schedule_index import ScheduleIndex
from app.services.optimization import _has_schedule_conflict, _check_teacher_transitions
from test_transition_metrics import setup_entries


def test_day_index_preserves_order_and_does_not_drop_invalid_lessons():
    entries, lessons, rooms = setup_entries()
    unknown = NS(id=3, lesson_id=99, weekday=0, room_id=3,
                 start_time=time(8, 30), end_time=time(10, 5))
    other_day = NS(id=4, lesson_id=1, weekday=1, room_id=1,
                   start_time=time(8, 30), end_time=time(10, 5))
    entries += [unknown, other_day]
    indexed = ScheduleIndex(entries, lessons)
    assert list(indexed) == entries
    assert indexed.for_day(0) == tuple(entries[:3])
    assert indexed.for_teacher_day(10, 0) == tuple(entries[:2])
    assert indexed.for_day(6) == ()
    members = {1: [{'group_id': 1, 'subgroup_number': 0}],
               2: [{'group_id': 2, 'subgroup_number': 0}]}
    assert _has_schedule_conflict(NS(id=2), entries[0], indexed, lessons, members)


def test_conflicts_match_scan_during_time_trials_and_atomic_room_swap():
    lessons = {i: NS(teacher_id=(i % 3)) for i in range(1, 13)}
    members = {i: [{'group_id': i % 4, 'subgroup_number': i % 3}] for i in lessons}
    entries = [NS(id=i, lesson_id=i, weekday=i % 2, room_id=i % 4,
                  start_time=time(8 + i % 3), end_time=time(10 + i % 3)) for i in lessons]
    indexed = ScheduleIndex(entries, lessons)
    for entry in entries:
        old = (entry.room_id, entry.start_time, entry.end_time)
        for hour in (8, 10, 12):
            entry.start_time, entry.end_time = time(hour), time(hour + 1)
            for rid in range(5):
                entry.room_id = rid
                assert _has_schedule_conflict(NS(id=rid), entry, indexed, lessons, members) == _has_schedule_conflict(NS(id=rid), entry, entries, lessons, members)
        entry.room_id, entry.start_time, entry.end_time = old
    first, second = entries[0], entries[2]
    first.room_id, second.room_id = second.room_id, first.room_id
    for entry in (first, second):
        assert _has_schedule_conflict(NS(id=entry.room_id), entry, indexed, lessons, members) == _has_schedule_conflict(NS(id=entry.room_id), entry, entries, lessons, members)


def test_teacher_index_resorts_live_times_and_checks_live_rooms():
    entries, lessons, rooms = setup_entries()
    indexed = ScheduleIndex(entries, lessons)
    db = NS(info={'_optimization_transition_checker': lambda a, b: 0 if a == b else 20})
    assert not _check_teacher_transitions(db, indexed, entries[0], lessons, rooms)
    entries[1].room_id = entries[0].room_id
    assert _check_teacher_transitions(db, indexed, entries[0], lessons, rooms)
    entries[0].start_time, entries[0].end_time = time(12), time(13, 35)
    assert _check_teacher_transitions(db, indexed, entries[0], lessons, rooms)
    entries[0].start_time = time(11)
    assert not _check_teacher_transitions(db, indexed, entries[0], lessons, rooms)
    assert indexed.for_teacher_day(10, 0) == tuple(entries)
