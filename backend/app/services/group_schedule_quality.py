"""Student-group schedule quality, calculated from full weekly timetable copies.

A shared lesson is counted once per group. Parallel subgroup classes in the
same pair occupy one group-level slot. Quality metrics are descriptive; they
are not part of the optimizer's objective or hard constraints.
"""
from collections import defaultdict

from app.services.lesson_times import get_lesson_pair, LESSON_PAIRS

PAIR_COUNT = len(LESSON_PAIRS)


def _minute(value):
    return value.hour * 60 + value.minute


def _days(entries, participants):
    schedule = defaultdict(lambda: defaultdict(list))
    for entry in entries:
        for member in participants.get(entry.lesson_id, []):
            schedule[member["group_id"]][entry.weekday].append(entry)
    return schedule


def _day_stats(entries):
    if not entries:
        return {
            "lessons": 0, "occupied_pairs": 0, "windows": 0,
            "span_minutes": 0, "first_pair": None, "last_pair": None,
            "unknown_pair_entries": 0,
        }
    unique = {item.id: item for item in entries}
    lessons = list(unique.values())
    pair_numbers = {
        pair for item in lessons
        if (pair := get_lesson_pair(item.start_time, item.end_time)) is not None
    }
    unknown = sum(
        get_lesson_pair(item.start_time, item.end_time) is None for item in lessons
    )
    first = min(pair_numbers) if pair_numbers else None
    last = max(pair_numbers) if pair_numbers else None
    # A window is a full unoccupied teaching pair between occupied pairs,
    # not a normal inter-pair break (including the long lunch break).
    windows = sum(pair not in pair_numbers for pair in range(first, last + 1)) if first is not None else None
    return {
        "lessons": len(lessons),
        "occupied_pairs": len(pair_numbers),
        "windows": windows if not unknown else None,
        "span_minutes": max(_minute(e.end_time) for e in lessons) - min(_minute(e.start_time) for e in lessons),
        "first_pair": first,
        "last_pair": last,
        "unknown_pair_entries": unknown,
    }


def _week_stats(day_map):
    days = [
        {"weekday": weekday, **_day_stats(day_map.get(weekday, []))}
        for weekday in range(7)
    ]
    known = all(day["unknown_pair_entries"] == 0 for day in days)
    return {
        "days_with_lessons": sum(day["lessons"] > 0 for day in days),
        "lesson_entries": sum(day["lessons"] for day in days),
        "occupied_pairs": sum(day["occupied_pairs"] for day in days),
        "windows": sum(day["windows"] for day in days) if known else None,
        "span_minutes": sum(day["span_minutes"] for day in days),
        "latest_pair": max((day["last_pair"] or 0 for day in days), default=0) or None,
        "unknown_pair_entries": sum(day["unknown_pair_entries"] for day in days),
        "days": days,
    }


def build_group_quality(before_entries, after_entries, participants, group_change_ids):
    before_days = _days(before_entries, participants)
    after_days = _days(after_entries, participants)
    group_names = {
        member["group_id"]: member["group_name"]
        for members in participants.values()
        for member in members
    }
    groups = []
    for group_id in sorted(group_change_ids):
        before = _week_stats(before_days.get(group_id, {}))
        after = _week_stats(after_days.get(group_id, {}))
        # More windows or longer day means worse student logistics;
        # we expose both, rather than compressing them into an arbitrary score.
        window_delta = (
            after["windows"] - before["windows"]
            if before["windows"] is not None and after["windows"] is not None
            else None
        )
        span_delta = after["span_minutes"] - before["span_minutes"]
        if window_delta is None:
            impact = "unknown"
        elif window_delta <= 0 and span_delta <= 0 and (window_delta < 0 or span_delta < 0):
            impact = "improved"
        elif window_delta >= 0 and span_delta >= 0 and (window_delta > 0 or span_delta > 0):
            impact = "worsened"
        elif window_delta == 0 and span_delta == 0:
            impact = "unchanged"
        else:
            impact = "mixed"
        groups.append({
            "group_id": group_id,
            "group_name": group_names.get(group_id),
            "changes_count": len(group_change_ids[group_id]),
            "entry_ids": sorted(group_change_ids[group_id]),
            "before": before,
            "after": after,
            "window_delta": window_delta,
            "span_delta_minutes": span_delta,
            "impact": impact,
        })
    return groups
