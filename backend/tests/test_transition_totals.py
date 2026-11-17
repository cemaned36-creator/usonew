from datetime import time
from types import SimpleNamespace as NS
from app.services.transition_totals import TransitionTotals
from app.services.optimization import _transition_minutes, _teacher_transition_total
from test_transition_metrics import setup_entries


def test_trial_and_accept_match_full_recalculation_including_unknown_routes():
    lessons = {i: NS(teacher_id=(i - 1) // 4) for i in range(1, 9)}
    rooms = {i: NS(access_type='OPEN', room_type='classroom', building='Главный корпус') for i in range(1, 5)}
    entries = [NS(id=i, lesson_id=i, weekday=0, room_id=(i % 3) + 1,
                  start_time=time(8 + 2 * ((i - 1) % 4)), end_time=time(9 + 2 * ((i - 1) % 4), 35)) for i in lessons]
    db = NS(info={'_optimization_transition_checker': lambda a,b: None if a == 4 and b == 3 else abs(a-b) * 3})
    costs = TransitionTotals(entries, lessons, lambda a,b: _transition_minutes(db,a,b,lessons,rooms))
    assert costs.total() == _teacher_transition_total(entries,lessons,rooms,db)
    for iteration in range(32):
        changed = [entries[iteration % 8], entries[(iteration + 3) % 8]]
        original = [e.room_id for e in changed]
        baseline = costs.total()
        for entry in changed:
            entry.room_id = iteration % 4 + 1
        updates = costs.trial([e.id for e in changed])
        expected = _teacher_transition_total(entries,lessons,rooms,db)
        assert costs.total(updates) == expected
        assert costs.total() == baseline  # A rejected trial cannot poison the cache.
        for tid in (0, 1):
            subset = [e for e in entries if lessons[e.lesson_id].teacher_id == tid]
            assert costs.total(updates, days=[(tid,0)]) == _teacher_transition_total(subset,lessons,rooms,db)
        if iteration % 2:
            costs.accept(updates)
            assert costs.total() == expected
        else:
            for entry, room_id in zip(changed,original):
                entry.room_id = room_id
        assert costs.total() == _teacher_transition_total(entries,lessons,rooms,db)


def test_only_adjacent_edges_recomputed_and_shared_edge_not_counted_twice():
    entries = [NS(id=i,lesson_id=i,weekday=0,start_time=time(i+8)) for i in range(5)]
    lessons = {i:NS(teacher_id=1) for i in range(5)}
    calls = []
    def transition(a,b):
        calls.append((a.id,b.id))
        return 2
    costs = TransitionTotals(entries,lessons,transition)
    assert costs.total() == 8
    calls.clear()
    costs.trial([2])
    assert calls == [(1,2),(2,3)]
    calls.clear()
    updates = costs.trial([2,3])
    assert calls == [(1,2),(2,3),(3,4)]
    assert costs.total(updates) == 8


def test_unrelated_invalid_teacher_does_not_block_affected_days_score():
    entries = [NS(id=i,lesson_id=i,weekday=0,start_time=time(i+8)) for i in range(4)]
    lessons = {i:NS(teacher_id=i//2) for i in range(4)}
    costs = TransitionTotals(entries,lessons,lambda a,b: None if a.id==2 else 3)
    assert costs.total() is None
    assert costs.total(days=[(0,0)]) == 3
    assert costs.total(days=[(1,0)]) is None
    assert costs.total(days=[(9,0)]) == 0


def test_long_break_remains_in_search_cost_and_invalid_transition_stays_invalid():
    entries, lessons, rooms = setup_entries()
    entries[0].start_time, entries[0].end_time = time(12), time(13,35)
    entries[1].start_time, entries[1].end_time = time(14,30), time(16,5)
    db = NS(info={'_optimization_transition_checker': lambda a,b: 13})
    costs = TransitionTotals(entries,lessons,lambda a,b: _transition_minutes(db,a,b,lessons,rooms))
    assert costs.total() == 13
    assert _teacher_transition_total(entries,lessons,rooms,db,exclude_long_break=True) == 0
    for value in (None,56):
        db.info['_optimization_transition_checker'] = lambda a,b: value
        assert costs.total(costs.trial([1])) is None
        assert costs.total() == 13
