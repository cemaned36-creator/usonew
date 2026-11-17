"""Incremental transition costs for a room-only optimization stage."""
from collections import defaultdict


class TransitionTotals:
    """Keep accepted edge costs; evaluate trials without changing that baseline.

    Entry times, weekdays, lessons and membership must remain fixed during this
    stage. Construct a new instance after time repair. Room references stay live.
    Unknown or infeasible transitions remain None, including across lunch.
    """

    def __init__(self, entries, lessons, transition):
        self._transition = transition
        self._pairs = {}
        self._values = {}
        self._entry_edges = defaultdict(set)
        self._day_totals = defaultdict(int)
        self._day_invalid = defaultdict(int)
        self._total = self._invalid = 0
        days = defaultdict(list)
        for entry in entries:
            lesson = lessons.get(entry.lesson_id)
            if lesson is not None:
                days[(lesson.teacher_id, entry.weekday)].append(entry)
        for day, items in days.items():
            items.sort(key=lambda item: item.start_time.hour * 60 + item.start_time.minute)
            for previous, current in zip(items, items[1:]):
                edge = (day, previous.id, current.id)
                self._pairs[edge] = (previous, current)
                self._entry_edges[previous.id].add(edge)
                self._entry_edges[current.id].add(edge)
                value = transition(previous, current)
                self._values[edge] = value
                self._adjust(edge, value, 1)

    def _adjust(self, edge, value, sign):
        day = edge[0]
        if value is None:
            self._invalid += sign
            self._day_invalid[day] += sign
        else:
            self._total += sign * value
            self._day_totals[day] += sign * value

    def trial(self, entry_ids):
        edges = set()
        for entry_id in entry_ids:
            edges.update(self._entry_edges.get(entry_id, ()))
        # One shared edge is evaluated only once, even if both ends move.
        return {edge: self._transition(*self._pairs[edge]) for edge in sorted(edges)}

    def total(self, updates=None, *, days=None):
        selected = None if days is None else set(days)
        if selected is None:
            total, invalid = self._total, self._invalid
        else:
            total = sum(self._day_totals[day] for day in selected)
            invalid = sum(self._day_invalid[day] for day in selected)
        for edge, new in (updates or {}).items():
            if selected is not None and edge[0] not in selected:
                continue
            old = self._values[edge]
            total += (0 if new is None else new) - (0 if old is None else old)
            invalid += int(new is None) - int(old is None)
        return None if invalid else total

    def accept(self, updates):
        for edge, new in updates.items():
            self._adjust(edge, self._values[edge], -1)
            self._values[edge] = new
            self._adjust(edge, new, 1)
