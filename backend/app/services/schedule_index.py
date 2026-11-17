"""Day/teacher lookup for one fixed set of optimization preview entries."""
from collections import defaultdict
from collections.abc import Sequence


class ScheduleIndex(Sequence):
    """Keep original iteration order and live references to copied entries.

    The optimizer changes rooms and start/end times, not weekdays or teachers.
    Do not cache occupancy or time ordering: trials and room swaps change them.
    Rebuild the index if lesson membership, weekday or teacher ever changes.
    """

    def __init__(self, entries, lessons):
        self._entries = tuple(entries)
        days = defaultdict(list)
        teacher_days = defaultdict(list)
        for entry in self._entries:
            days[entry.weekday].append(entry)
            lesson = lessons.get(entry.lesson_id)
            if lesson is not None:
                teacher_days[(lesson.teacher_id, entry.weekday)].append(entry)
        self._days = {key: tuple(items) for key, items in days.items()}
        self._teacher_days = {key: tuple(items) for key, items in teacher_days.items()}

    def __len__(self):
        return len(self._entries)

    def __getitem__(self, index):
        return self._entries[index]

    def __iter__(self):
        return iter(self._entries)

    def for_day(self, weekday):
        return self._days.get(weekday, ())

    def for_teacher_day(self, teacher_id, weekday):
        return self._teacher_days.get((teacher_id, weekday), ())
