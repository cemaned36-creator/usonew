"""Read-only, per-entity comparison for optimization previews.

All numbers are computed on schedule copies. Unknown transitions stay null,
never silently turn into zero. One schedule entry is counted once even when
several student groups attend the same lesson.
"""
from collections import defaultdict

from app.services.optimization import _transition_minutes, _is_sports_entry
from app.services.room_scope import room_in_active_scope


def _time(value):
    return value.strftime("%H:%M")


def _transition_stats(entries, lessons, rooms, db):
    days = defaultdict(list)
    for entry in entries:
        lesson = lessons.get(entry.lesson_id)
        if lesson and room_in_active_scope(rooms.get(entry.room_id)):
            days[(lesson.teacher_id, entry.weekday)].append(entry)

    result = {}
    for (teacher_id, weekday), day in days.items():
        day.sort(key=lambda e: (e.start_time, e.id))
        minutes, missing = 0, 0
        for previous, current in zip(day, day[1:]):
            value = _transition_minutes(db, previous, current, lessons, rooms)
            if value is None:
                missing += 1
            else:
                minutes += value
        result[(teacher_id, weekday)] = {
            "minutes": None if missing else minutes,
            "unknown_transitions": missing,
            "transition_count": max(0, len(day) - 1),
        }
    return result


def _aggregate(stats, teacher_id):
    rows = [value for (tid, _), value in stats.items() if tid == teacher_id]
    unknown = sum(row["unknown_transitions"] for row in rows)
    return {
        "minutes": None if unknown else sum(row["minutes"] for row in rows),
        "unknown_transitions": unknown,
        "transition_count": sum(row["transition_count"] for row in rows),
    }


def _delta(before, after):
    if before is None or after is None:
        return None
    return after - before


def build_optimization_report(
    db, *, before_entries, after_entries, lessons, rooms, participants,
    teachers, subjects, requirements, week_type, selected_teacher_id=None,
):
    """Build additive preview analytics without changing the optimization plan."""
    original = {entry.id: entry for entry in before_entries}
    proposed = {entry.id: entry for entry in after_entries}

    # Report excludes sports entries consistently with the optimizer's metrics.
    eligible = {
        entry_id for entry_id, entry in original.items()
        if room_in_active_scope(rooms.get(entry.room_id))
        and not _is_sports_entry(entry, rooms, requirements)
    }
    before = [original[entry_id] for entry_id in sorted(eligible)]
    after = [proposed[entry_id] for entry_id in sorted(eligible)]
    before_stats = _transition_stats(before, lessons, rooms, db)
    after_stats = _transition_stats(after, lessons, rooms, db)

    changes = []
    teacher_change_ids = defaultdict(set)
    group_change_ids = defaultdict(set)
    changed_rooms = changed_times = 0
    for entry_id in sorted(original):
        old, new = original[entry_id], proposed[entry_id]
        if (old.room_id, old.start_time, old.end_time) == (
            new.room_id, new.start_time, new.end_time
        ):
            continue
        lesson = lessons[old.lesson_id]
        groups = participants.get(old.lesson_id, [])
        room_changed = old.room_id != new.room_id
        time_changed = (old.start_time, old.end_time) != (new.start_time, new.end_time)
        changed_rooms += int(room_changed)
        changed_times += int(time_changed)
        teacher_change_ids[lesson.teacher_id].add(entry_id)
        for group in groups:
            group_change_ids[group["group_id"]].add(entry_id)
        changes.append({
            "entry_id": entry_id,
            "lesson_id": old.lesson_id,
            "subject_name": getattr(subjects.get(lesson.subject_id), "name", None),
            "teacher_id": lesson.teacher_id,
            "teacher_name": getattr(teachers.get(lesson.teacher_id), "name", None),
            "groups": [
                {"id": group["group_id"], "name": group["group_name"],
                 "subgroup_number": group["subgroup_number"]}
                for group in groups
            ],
            "weekday": old.weekday,
            "change_types": (["room"] if room_changed else []) +
                            (["time"] if time_changed else []),
            "before": {
                "room_id": old.room_id,
                "room_name": rooms[old.room_id].name,
                "start_time": _time(old.start_time),
                "end_time": _time(old.end_time),
            },
            "after": {
                "room_id": new.room_id,
                "room_name": rooms[new.room_id].name,
                "start_time": _time(new.start_time),
                "end_time": _time(new.end_time),
            },
            # Explicitly distinguish inferred classification from exact optimizer reasons.
            "reason": "teacher_conditions_or_transition_optimization",
            "reason_verified": False,
        })

    teacher_ids = sorted(
        {lessons[entry.lesson_id].teacher_id for entry in before}
        | set(teacher_change_ids)
    )
    teacher_report = []
    for teacher_id in teacher_ids:
        b = _aggregate(before_stats, teacher_id)
        a = _aggregate(after_stats, teacher_id)
        teacher_report.append({
            "teacher_id": teacher_id,
            "teacher_name": getattr(teachers.get(teacher_id), "name", None),
            "changes_count": len(teacher_change_ids[teacher_id]),
            "before": b,
            "after": a,
            "delta_minutes": _delta(b["minutes"], a["minutes"]),
            "time_saved": _delta(a["minutes"], b["minutes"]),
        })

    groups_report = []
    group_names = {
        group["group_id"]: group["group_name"]
        for group_list in participants.values() for group in group_list
    }
    for group_id, ids in sorted(group_change_ids.items()):
        groups_report.append({
            "group_id": group_id,
            "group_name": group_names.get(group_id),
            "changes_count": len(ids),
            "entry_ids": sorted(ids),
        })

    total_before = sum(row["before"]["minutes"] for row in teacher_report
                       if row["before"]["minutes"] is not None)
    total_after = sum(row["after"]["minutes"] for row in teacher_report
                      if row["after"]["minutes"] is not None)
    complete = all(
        row["before"]["minutes"] is not None and row["after"]["minutes"] is not None
        for row in teacher_report
    )

    return {
        "version": 1,
        "week_type": week_type,
        "teacher_id": selected_teacher_id,
        "scope": "active_rooms_excluding_sports",
        "summary": {
            "changed_entries": len(changes),
            "room_changes": changed_rooms,
            "time_changes": changed_times,
            "affected_teachers": len(teacher_change_ids),
            "affected_groups": len(group_change_ids),
            "transition_time_before": total_before if complete else None,
            "transition_time_after": total_after if complete else None,
            "time_saved": total_before - total_after if complete else None,
            "transition_metrics_complete": complete,
        },
        "teachers": teacher_report,
        "groups": groups_report,
        "changes": changes,
    }
