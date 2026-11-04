"""Read-only, per-entity comparison for optimization previews.

All numbers are computed on schedule copies. Unknown transitions stay null,
never silently turn into zero. One schedule entry is counted once even when
several student groups attend the same lesson.
"""
from collections import defaultdict

from app.services.optimization import _transition_minutes, _is_sports_entry
from app.services.room_scope import room_in_active_scope
from app.services.teacher_conditions import room_allowed, time_allowed
from app.services.group_schedule_quality import build_group_quality


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


def _adjacent_transition_effect(db, entries, entry_id, lessons, rooms):
    """Measure only transitions touching this entry, in one teacher-day snapshot.

    Before/after differences are descriptive, not independently additive:
    moving two adjacent lessons can affect their shared transition twice.
    """
    by_id = {entry.id: entry for entry in entries}
    focus = by_id[entry_id]
    teacher_id = lessons[focus.lesson_id].teacher_id
    day = [
        entry for entry in entries
        if entry.weekday == focus.weekday
        and lessons[entry.lesson_id].teacher_id == teacher_id
        and room_in_active_scope(rooms.get(entry.room_id))
    ]
    day.sort(key=lambda entry: (entry.start_time, entry.id))
    index = next(i for i, entry in enumerate(day) if entry.id == entry_id)
    links = []
    if index > 0:
        links.append((day[index - 1], day[index]))
    if index + 1 < len(day):
        links.append((day[index], day[index + 1]))
    values = [_transition_minutes(db, left, right, lessons, rooms) for left, right in links]
    return {
        "minutes": sum(values) if all(value is not None for value in values) else None,
        "unknown_transitions": sum(value is None for value in values),
        "transition_count": len(links),
    }


def _change_explanation(old, new, teacher, old_room, new_room, before_touch, after_touch):
    """Explain verified facts, without claiming why a search step chose a candidate."""
    reasons = []
    if teacher is not None and not time_allowed(old.start_time, teacher) and time_allowed(new.start_time, teacher):
        pair = getattr(teacher, "earliest_start_pair", None)
        reasons.append({
            "code": "earliest_pair_fixed",
            "verified": True,
            "text": f"Исправлено начало занятия раньше разрешённой пары №{pair}.",
        })
    if teacher is not None and not room_allowed(old_room, teacher) and room_allowed(new_room, teacher):
        floor = getattr(teacher, "max_floor", None)
        reasons.append({
            "code": "max_floor_fixed",
            "verified": True,
            "text": f"Исправлено превышение разрешённого этажа {floor}.",
        })
    before_min = before_touch["minutes"]
    after_min = after_touch["minutes"]
    if before_min is not None and after_min is not None and before_min != after_min:
        difference = before_min - after_min
        reasons.append({
            "code": "adjacent_transitions_changed",
            "verified": True,
            "text": (
                f"Сумма соседних переходов {'сократилась' if difference > 0 else 'увеличилась'} "
                f"на {abs(difference)} мин. Это наблюдаемый эффект, не доказательство причины выбора."
            ),
        })
    if not reasons:
        reasons.append({
            "code": "assignment_changed",
            "verified": True,
            "text": "Назначение изменено. Точная причина выбора кандидата алгоритмом не записана.",
        })
    return reasons


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
        before_touch = _adjacent_transition_effect(db, before_entries, entry_id, lessons, rooms)
        after_touch = _adjacent_transition_effect(db, after_entries, entry_id, lessons, rooms)
        explanation = _change_explanation(
            old, new, teachers.get(lesson.teacher_id),
            rooms[old.room_id], rooms[new.room_id], before_touch, after_touch,
        )
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
            # Verified observable effects, not optimizer decision provenance.
            "reasons": explanation,
            "adjacent_transitions": {
                "before": before_touch,
                "after": after_touch,
                "saved_minutes": _delta(after_touch["minutes"], before_touch["minutes"]),
                "additive": False,
            },
            "reason": explanation[0]["code"],
            "reason_verified": all(item["verified"] for item in explanation),
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

    # Group quality uses the full timetable (including gym), not the
    # teacher walking-time scope. All shared/subgroup pairs are deduplicated
    # at group-slot level in the new metric module.
    groups_report = build_group_quality(
        before_entries, after_entries, participants, group_change_ids
    )

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
