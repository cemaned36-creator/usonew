from datetime import time
from types import SimpleNamespace as NS
from app.services.optimization import (_required_transition_minutes, _transition_minutes, _teacher_transition_total, ScheduleItem)
from app.services.optimization_report import build_optimization_report, _link_stats


def setup_entries():
    entries = [ScheduleItem(id=1, lesson_id=1, weekday=0, room_id=1, start_time=time(8,30), end_time=time(10,5)),
               ScheduleItem(id=2, lesson_id=2, weekday=0, room_id=2, start_time=time(10,15), end_time=time(11,50))]
    lessons = {i: NS(teacher_id=10, subject_id=1) for i in (1,2)}
    rooms = {i: NS(name=str(i), room_type='classroom', building='Главный корпус', access_type='OPEN') for i in (1,2)}
    return entries, lessons, rooms


def report(db, before, after, lessons, rooms, selected=None):
    return build_optimization_report(db, before_entries=before, after_entries=after, lessons=lessons,
        rooms=rooms, participants={}, teachers={}, subjects={}, requirements={}, week_type='odd', selected_teacher_id=selected)


def test_known_time_over_break_is_measured_but_still_infeasible():
    entries, lessons, rooms = setup_entries()
    db = NS(info={'_optimization_transition_checker': lambda a,b: 13})
    assert _required_transition_minutes(db, *entries, lessons, rooms) == 13
    assert _transition_minutes(db, *entries, lessons, rooms) is None
    assert _teacher_transition_total(entries, lessons, rooms, db) is None
    assert _teacher_transition_total(entries, lessons, rooms, db, require_feasible=False) == 13
    stats = _link_stats(db, [tuple(entries)], lessons, rooms)
    assert stats['minutes'] == 13 and stats['unknown_transitions'] == 0
    assert stats['insufficient_breaks'] == 1
    assert stats['issues'][0]['available_minutes'] == 10


def test_unknown_before_does_not_hide_known_after():
    entries, lessons, rooms = setup_entries()
    after = [NS(**vars(e)) for e in entries]
    after[1].room_id = 1
    db = NS(info={'_optimization_transition_checker': lambda a,b: 0 if a==b else None})
    result = report(db, entries, after, lessons, rooms)
    assert result['summary']['transition_time_before'] is None
    assert result['summary']['transition_time_after'] == 0
    assert result['summary']['time_saved'] is None
    assert result['teachers'][0]['before']['unknown_transitions'] == 1
    assert result['summary']['transition_metrics_complete'] is False


def test_individual_report_does_not_include_other_teacher():
    entries, lessons, rooms = setup_entries()
    other = [NS(**{**vars(e), 'id':e.id+10,'lesson_id':e.lesson_id+10}) for e in entries]
    lessons.update({11:NS(teacher_id=20,subject_id=1),12:NS(teacher_id=20,subject_id=1)})
    db = NS(info={'_optimization_transition_checker': lambda a,b: 13})
    result = report(db, entries+other, entries+other, lessons, rooms, selected=10)
    assert result['summary']['transition_time_before'] == 13
    assert result['summary']['insufficient_breaks_before'] == 1
    assert [t['teacher_id'] for t in result['teachers']] == [10]
    assert result['summary']['affected_teachers'] == 0


def test_unknown_partial_sum_and_overlapping_entries_remain_distinct():
    entries, lessons, rooms = setup_entries()
    third=NS(**{**vars(entries[1]),'id':3,'lesson_id':3,'room_id':1,'start_time':time(12),'end_time':time(13,35)})
    lessons[3]=NS(teacher_id=10,subject_id=1)
    db=NS(info={'_optimization_transition_checker': lambda a,b: 4 if a==1 else None})
    stats=_link_stats(db,[(entries[0],entries[1]),(entries[1],third)],lessons,rooms)
    assert stats['minutes'] is None and stats['known_minutes']==4 and stats['unknown_transitions']==1
    entries[1].start_time=time(10)
    db.info['_optimization_transition_checker']=lambda a,b:0
    assert _transition_minutes(db,*entries,lessons,rooms) is None
    assert _link_stats(db,[tuple(entries)],lessons,rooms)['insufficient_breaks']==1


def test_unknown_after_preserves_known_before_and_exact_break_is_valid():
    entries, lessons, rooms = setup_entries()
    db = NS(info={'_optimization_transition_checker': lambda a,b: 10})
    assert _transition_minutes(db, *entries, lessons, rooms) == 10
    before = [NS(**vars(e)) for e in entries]
    before[1].room_id = 1
    db.info['_optimization_transition_checker'] = lambda a,b: 0 if a==b else None
    result = report(db, before, entries, lessons, rooms)
    assert result['summary']['transition_time_before'] == 0
    assert result['summary']['transition_time_after'] is None
    assert result['summary']['time_saved'] is None



def test_long_break_cost_excluded_without_disabling_feasibility():
    entries, lessons, rooms = setup_entries()
    entries[0].start_time, entries[0].end_time = time(12), time(13,35)
    entries[1].start_time, entries[1].end_time = time(14,30), time(16,5)
    db = NS(info={'_optimization_transition_checker': lambda a,b: 13})
    assert _required_transition_minutes(db, *entries, lessons, rooms) == 13
    assert _transition_minutes(db, *entries, lessons, rooms) == 13
    assert _teacher_transition_total(entries, lessons, rooms, db) == 13
    assert _teacher_transition_total(entries, lessons, rooms, db, require_feasible=False, exclude_long_break=True) == 0
    stats = _link_stats(db, [tuple(entries)], lessons, rooms)
    assert stats['minutes'] == 0 and stats['transition_count'] == 0
    assert report(db, entries, entries, lessons, rooms)['summary']['long_break_excluded']
    for value in [None, 56]:
        db.info['_optimization_transition_checker'] = lambda a,b: value
        assert _transition_minutes(db, *entries, lessons, rooms) is None
        assert _teacher_transition_total(entries, lessons, rooms, db) is None
        assert _teacher_transition_total(entries, lessons, rooms, db, require_feasible=False, exclude_long_break=True) == 0


def test_only_full_long_break_is_excluded():
    from app.services.lesson_times import spans_long_break
    entries, lessons, rooms = setup_entries()
    assert not spans_long_break(*entries)
    entries[0].end_time = time(13,36)
    entries[1].start_time = time(14,30)
    assert not spans_long_break(*entries)
    entries[0].end_time = time(13,35)
    entries[1].start_time = time(14,29)
    assert not spans_long_break(*entries)
    entries[0].end_time = time(11,50)
    entries[1].start_time = time(16,15)
    assert spans_long_break(*entries)
    entries[1].weekday = 1
    assert not spans_long_break(*entries)
