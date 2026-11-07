"""Regression tests for the additive optimization report."""
from datetime import time
from types import SimpleNamespace

from app.services.optimization import ScheduleItem
from app.services import optimization_report


def item(id, lesson_id, room_id, start, end):
    return ScheduleItem(
        id=id, lesson_id=lesson_id, weekday=0, room_id=room_id,
        start_time=time.fromisoformat(start), end_time=time.fromisoformat(end),
    )


def test_report_counts_shared_lesson_once_and_uses_all_impacted_groups(monkeypatch):
    monkeypatch.setattr(optimization_report, "room_in_active_scope", lambda room: True)
    monkeypatch.setattr(
        optimization_report, "_required_transition_minutes",
        lambda db, left, right, lessons, rooms:
            3 if left.room_id == right.room_id else 8,
    )
    lessons = {
        1: SimpleNamespace(teacher_id=10, subject_id=1, lesson_type="Лекция"),
        2: SimpleNamespace(teacher_id=10, subject_id=1),
    }
    rooms = {
        1: SimpleNamespace(name="B1", room_type="classroom"),
        2: SimpleNamespace(name="B2", room_type="classroom"),
    }
    participants = {
        1: [{"group_id": 11, "group_name": "G1", "subgroup_number": 0},
            {"group_id": 12, "group_name": "G2", "subgroup_number": 0}],
        2: [{"group_id": 11, "group_name": "G1", "subgroup_number": 0}],
    }
    before = [item(1, 1, 1, "08:00", "09:30"),
              item(2, 2, 2, "09:40", "11:10")]
    after = [item(1, 1, 2, "08:00", "09:30"),
             item(2, 2, 2, "09:40", "11:10")]
    report = optimization_report.build_optimization_report(
        None, before_entries=before, after_entries=after, lessons=lessons,
        rooms=rooms, participants=participants,
        teachers={10: SimpleNamespace(name="Teacher")}, requirements={},
        subjects={1: SimpleNamespace(name="Subject")},
        week_type="odd", selected_teacher_id=10,
    )
    assert report["changes"][0]["lesson_type"] == "Лекция"
    assert report["groups"][0]["timetable"]["before"][0]["lessons"][0]["lesson_type"] == "Лекция"
    assert report["groups"][0]["timetable"]["after"][0]["lessons"][0]["lesson_type"] == "Лекция"
    assert report["summary"]["changed_entries"] == 1
    assert report["summary"]["room_changes"] == 1
    assert report["summary"]["affected_groups"] == 2
    assert {group["group_id"] for group in report["groups"]} == {11, 12}
    assert report["summary"]["time_saved"] == 5
    assert report["teachers"][0]["time_saved"] == 5


def test_unknown_transition_is_not_counted_as_zero(monkeypatch):
    monkeypatch.setattr(optimization_report, "room_in_active_scope", lambda room: True)
    monkeypatch.setattr(optimization_report, "_required_transition_minutes",
                        lambda *args: None)
    lessons = {1: SimpleNamespace(teacher_id=10, subject_id=1),
               2: SimpleNamespace(teacher_id=10, subject_id=1)}
    rooms = {1: SimpleNamespace(name="B1", room_type="classroom")}
    entries = [item(1, 1, 1, "08:00", "09:30"),
               item(2, 2, 1, "09:40", "11:10")]
    report = optimization_report.build_optimization_report(
        None, before_entries=entries, after_entries=entries, lessons=lessons,
        rooms=rooms,
        participants={1: [{"group_id": 11, "group_name": "G1", "subgroup_number": 0}],
                      2: [{"group_id": 11, "group_name": "G1", "subgroup_number": 0}]},
        teachers={}, subjects={}, requirements={}, week_type="even",
    )
    assert report["summary"]["transition_metrics_complete"] is False
    assert report["summary"]["time_saved"] is None
    assert report["teachers"][0]["before"]["unknown_transitions"] == 1


def test_history_keeps_detailed_report_without_changing_old_metrics():
    from app.services.optimization_history import record_run, serialize_run

    class FakeSession:
        def __init__(self):
            self.saved = None

        def add(self, row):
            self.saved = row

        def flush(self):
            self.saved.id = 42

    db = FakeSession()
    report = {
        "version": 1,
        "summary": {"changed_entries": 1},
        "teachers": [], "groups": [], "changes": [],
    }
    run = record_run(
        db, week_type="odd", teacher_id=10, teacher_name="Teacher",
        before=[{"id": 1}], after=[{"id": 1}],
        preview={
            "transition_time_before": 9,
            "transition_time_after": 4,
            "time_saved": 5,
            "detailed_report": report,
        },
    )
    assert run.metrics["time_saved"] == 5
    assert run.metrics["detailed_report"] == report
    serialized = serialize_run(run)
    assert serialized["metrics"]["detailed_report"]["version"] == 1


def test_verified_earliest_pair_and_neighbor_transition_effect(monkeypatch):
    from app.services.optimization_report import _change_explanation, _adjacent_transition_effect

    teacher = SimpleNamespace(earliest_start_pair=2, max_floor=3)
    before = item(1, 1, 1, "08:00", "09:30")
    after = item(1, 1, 2, "10:15", "11:50")
    old_room = SimpleNamespace(name="B4", floor=4)
    new_room = SimpleNamespace(name="B2", floor=2)
    reasons = _change_explanation(
        before, after, teacher, old_room, new_room,
        {"minutes": 8}, {"minutes": 3},
    )
    assert {reason["code"] for reason in reasons} == {
        "earliest_pair_fixed", "max_floor_fixed", "adjacent_transitions_changed",
    }
    assert all(reason["verified"] for reason in reasons)


def test_no_invented_improvement_when_transition_is_unknown():
    from app.services.optimization_report import _change_explanation

    old = item(1, 1, 1, "08:00", "09:30")
    new = item(1, 1, 2, "08:00", "09:30")
    room = SimpleNamespace(floor=2)
    reasons = _change_explanation(
        old, new, None, room, room,
        {"minutes": None}, {"minutes": 4},
    )
    assert [reason["code"] for reason in reasons] == ["assignment_changed"]


def test_adjacent_effect_counts_only_touches_and_is_not_global(monkeypatch):
    monkeypatch.setattr(optimization_report, "room_in_active_scope", lambda room: True)
    monkeypatch.setattr(optimization_report, "_required_transition_minutes", lambda *args: 4)
    lessons = {
        x: SimpleNamespace(teacher_id=10, subject_id=1) for x in range(1, 5)
    }
    entries = [
        item(1, 1, 1, "08:00", "09:00"),
        item(2, 2, 1, "09:10", "10:10"),
        item(3, 3, 1, "10:20", "11:20"),
        item(4, 4, 1, "11:30", "12:30"),
    ]
    stats = optimization_report._adjacent_transition_effect(
        None, entries, 2, lessons, {1: SimpleNamespace(room_type="classroom")}
    )
    assert stats["transition_count"] == 2
    assert stats["minutes"] == 8


def test_group_quality_windows_and_span_improve_when_gap_removed():
    from app.services.group_schedule_quality import build_group_quality

    participants = {
        1: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
        2: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
    }
    before = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 1, "12:00", "13:35"),
    ]
    after = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 1, "10:15", "11:50"),
    ]
    group = build_group_quality(before, after, participants, {11: {2}})[0]
    assert group["before"]["windows"] == 1
    assert group["after"]["windows"] == 0
    assert group["before"]["days"][0]["span_minutes"] == 305
    assert group["after"]["days"][0]["span_minutes"] == 200
    assert group["window_delta"] == -1
    assert group["span_delta_minutes"] == -105
    assert group["impact"] == "improved"


def test_group_quality_subgroups_share_slot_without_fake_windows():
    from app.services.group_schedule_quality import build_group_quality

    participants = {
        1: [{"group_id": 11, "group_name": "G11", "subgroup_number": 1}],
        2: [{"group_id": 11, "group_name": "G11", "subgroup_number": 2}],
        3: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
    }
    entries = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 1, "08:30", "10:05"),
        item(3, 3, 1, "10:15", "11:50"),
    ]
    group = build_group_quality(entries, entries, participants, {11: {1}})[0]
    assert group["before"]["lesson_entries"] == 3
    assert group["before"]["occupied_pairs"] == 2
    assert group["before"]["windows"] == 0
    assert group["impact"] == "unchanged"


def test_group_quality_includes_shared_and_sports_entries():
    from app.services.group_schedule_quality import build_group_quality

    participants = {
        1: [
            {"group_id": 11, "group_name": "G11", "subgroup_number": 0},
            {"group_id": 12, "group_name": "G12", "subgroup_number": 0},
        ],
        2: [{"group_id": 12, "group_name": "G12", "subgroup_number": 0}],
    }
    before = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 9, "12:00", "13:35"),
    ]
    after = [
        item(1, 1, 1, "10:15", "11:50"),
        item(2, 2, 9, "12:00", "13:35"),
    ]
    groups = build_group_quality(before, after, participants, {11: {1}, 12: {1}})
    one, two = groups
    assert one["before"]["windows"] == 0
    assert two["before"]["windows"] == 1
    assert two["after"]["windows"] == 0


def test_group_quality_unrecognized_pair_is_not_fake_zero():
    from app.services.group_schedule_quality import build_group_quality

    participants = {
        1: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
        2: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
    }
    entries = [
        item(1, 1, 1, "08:00", "09:30"),
        item(2, 2, 1, "12:00", "13:35"),
    ]
    group = build_group_quality(entries, entries, participants, {11: {1}})[0]
    assert group["before"]["windows"] is None
    assert group["impact"] == "unknown"


def test_group_timetable_includes_unchanged_lessons_and_highlights_changed():
    from app.services.group_schedule_quality import build_group_quality

    participants = {
        1: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
        2: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
    }
    old = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 1, "12:00", "13:35"),
    ]
    new = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 2, "10:15", "11:50"),
    ]
    meta = {
        1: SimpleNamespace(teacher_id=5, subject_id=9),
        2: SimpleNamespace(teacher_id=5, subject_id=9),
    }
    groups = build_group_quality(
        old, new, participants, {11: {2}},
        lessons=meta, rooms={1: SimpleNamespace(name="Б1-11"), 2: SimpleNamespace(name="Б2-24")},
        teachers={5: SimpleNamespace(name="Преподаватель")},
        subjects={9: SimpleNamespace(name="Математика")},
    )
    timetable = groups[0]["timetable"]
    before_rows = timetable["before"][0]["lessons"]
    after_rows = timetable["after"][0]["lessons"]
    assert len(before_rows) == len(after_rows) == 2
    assert [entry["changed"] for entry in before_rows] == [False, True]
    assert [entry["changed"] for entry in after_rows] == [False, True]
    assert before_rows[1]["room_name"] == "Б1-11"
    assert after_rows[1]["room_name"] == "Б2-24"
    assert after_rows[1]["subject_name"] == "Математика"
    assert after_rows[1]["pair_number"] == 2
    assert len(timetable["before"]) == len(timetable["after"]) == 7


def test_student_impact_warns_on_window_increase(monkeypatch):
    monkeypatch.setattr(optimization_report, "room_in_active_scope", lambda room: True)
    monkeypatch.setattr(optimization_report, "_required_transition_minutes", lambda *args: 0)
    lessons = {
        1: SimpleNamespace(teacher_id=10, subject_id=1),
        2: SimpleNamespace(teacher_id=20, subject_id=1),
    }
    before = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 1, "10:15", "11:50"),
    ]
    after = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 1, "12:00", "13:35"),
    ]
    report = optimization_report.build_optimization_report(
        None, before_entries=before, after_entries=after,
        lessons=lessons,
        rooms={1: SimpleNamespace(name="B1", room_type="classroom")},
        participants={
            1: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
            2: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
        },
        teachers={}, subjects={}, requirements={}, week_type="odd",
    )
    assert report["student_impact"]["worsened"] == 1
    assert len(report["student_warnings"]) == 1
    assert report["student_warnings"][0]["window_delta"] == 1
    assert report["student_warnings"][0]["span_delta_minutes"] == 105


def test_group_week_duration_average_max_and_actual_teaching_time():
    from app.services.group_schedule_quality import build_group_quality
    participants = {
        1: [{"group_id": 11, "group_name": "G11", "subgroup_number": 1}],
        2: [{"group_id": 11, "group_name": "G11", "subgroup_number": 2}],
        3: [{"group_id": 11, "group_name": "G11", "subgroup_number": 0}],
    }
    monday = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 2, "08:30", "10:05"),
    ]
    tuesday = item(3, 3, 1, "10:15", "11:50")
    tuesday.weekday = 1
    entries = monday + [tuesday]
    group = build_group_quality(entries, entries, participants, {11: {1}})[0]
    week = group["before"]
    assert week["days_with_lessons"] == 2
    assert week["weekly_span_minutes"] == 190
    assert week["span_minutes"] == 190  # legacy contract
    assert week["average_day_span_minutes"] == 95
    assert week["longest_day_span_minutes"] == 95
    assert week["teaching_minutes"] == 190
    assert week["days"][0]["teaching_minutes"] == 95


def test_group_teaching_time_excludes_windows_and_short_breaks():
    from app.services.group_schedule_quality import _day_stats
    entries = [
        item(1, 1, 1, "08:30", "10:05"),
        item(2, 2, 1, "12:00", "13:35"),
    ]
    stats = _day_stats(entries)
    assert stats["span_minutes"] == 305
    assert stats["teaching_minutes"] == 190
    assert stats["windows"] == 1


def test_group_week_empty_schedule_has_zero_durations():
    from app.services.group_schedule_quality import _week_stats
    week = _week_stats({})
    assert week["days_with_lessons"] == 0
    assert week["weekly_span_minutes"] == 0
    assert week["average_day_span_minutes"] == 0
    assert week["longest_day_span_minutes"] == 0
    assert week["teaching_minutes"] == 0
