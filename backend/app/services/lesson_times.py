from datetime import time


LESSON_PAIRS = [
    (1, time(8, 30), time(10, 5)),
    (2, time(10, 15), time(11, 50)),
    (3, time(12, 0), time(13, 35)),
    (4, time(14, 30), time(16, 5)),
    (5, time(16, 15), time(17, 50)),
    (6, time(18, 0), time(19, 35)),
]


def get_lesson_pair(start_time: time, end_time: time):
    """Возвращает номер пары или None, если время недопустимо."""
    for number, pair_start, pair_end in LESSON_PAIRS:
        if start_time == pair_start and end_time == pair_end:
            return number

    return None


def spans_long_break(previous, current):
    """Exclude the 13:35–14:30 break from cost, never from feasibility checks."""
    return (previous.weekday == current.weekday
            and previous.end_time <= LESSON_PAIRS[2][2]
            and current.start_time >= LESSON_PAIRS[3][1])
