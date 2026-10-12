from datetime import (
    date,
    time,
    timedelta,
    datetime,
)

from sqlalchemy.orm import Session


from app.models.lesson import Lesson
from app.models.room import Room
from app.models.schedule_entry import ScheduleEntry

from app.services.schedule_report import ScheduleReport
from app.services.optimizer import recommend_room
from app.services.conflict_checker import check_conflicts
from app.services.schedule_utils import (
    get_previous_entry,
)


LESSON_DURATION = 90


START_TIMES = [
    time(8, 30),
    time(10, 10),
    time(12, 10),
    time(13, 50),
]



def generate_schedule(
    db: Session,
    start_date: date | None = None,
    days_ahead: int = 7,
    weekdays_only: bool = True,
):
    if days_ahead < 1 or days_ahead > 31:
        raise ValueError("days_ahead должен быть от 1 до 31")

    current_date = start_date or date.today()
    end_date = current_date + timedelta(days=days_ahead)

    lessons = (
        db.query(Lesson)
        .order_by(Lesson.teacher_id, Lesson.id)
        .all()
    )

    # Занятия, уже назначенные в выбранном периоде.
    existing_entries = (
        db.query(ScheduleEntry)
        .filter(
            ScheduleEntry.date >= current_date,
            ScheduleEntry.date < end_date,
        )
        .all()
    )

    scheduled_lesson_ids = {
        entry.lesson_id for entry in existing_entries
    }

    # Не создаём повторные записи для тех же занятий.
    lessons = [
        lesson for lesson in lessons
        if lesson.id not in scheduled_lesson_ids
    ]

    created_entries = []
    report = ScheduleReport()
    report.total = len(lessons)

    for lesson in lessons:
        scheduled = False

        for day_offset in range(days_ahead):
            schedule_date = current_date + timedelta(
                days=day_offset
            )

            if weekdays_only and schedule_date.weekday() >= 5:
                continue

            # Далее оставь существующий код:
            # перебор START_TIMES, подбор аудитории,
            # проверку конфликтов и создание ScheduleEntry.

                # -------------------------------------
                # Предыдущее занятие преподавателя
                # -------------------------------------

                previous_entry = (
                    get_previous_entry(
                        db=db,
                        teacher_id=lesson.teacher_id,
                        schedule_date=schedule_date,
                        start_time=start,
                    )
                )

                previous_room_id = None
                previous_access_type = None

                available_transition_minutes = None

                # -------------------------------------
                # Если предыдущее занятие существует
                # -------------------------------------

                if previous_entry:

                    previous_room_id = (
                        previous_entry.room_id
                    )

                    previous_room = (
                        db.query(Room)
                        .filter(
                            Room.id
                            == previous_entry.room_id
                        )
                        .first()
                    )

                    if previous_room:

                        previous_access_type = (
                            previous_room.access_type
                        )

                    previous_end = (
                        datetime.combine(
                            schedule_date,
                            previous_entry.end_time,
                        )
                    )

                    current_start = (
                        datetime.combine(
                            schedule_date,
                            start,
                        )
                    )

                    available_transition_minutes = int(
                        (
                            current_start
                            - previous_end
                        ).total_seconds()
                        / 60
                    )

                # -------------------------------------
                # Подбор аудитории
                # -------------------------------------

                room = recommend_room(
                    db=db,
                    lesson_id=lesson.id,

                    previous_room_id=(
                        previous_room_id
                    ),

                    previous_access_type=(
                        previous_access_type
                    ),

                    available_transition_minutes=(
                        available_transition_minutes
                    ),
                )
                print(
                    f"[DEBUG] lesson_id={lesson.id}, "
                    f"date={schedule_date}, start={start}, "
                    f"room_result={room!r}"
                )

                if not room or not room.get("room_id"):
                    reason = (
                        room.get("reason", "Причина не указана")
                        if isinstance(room, dict)
                        else "recommend_room вернул None"
                    )

                    print(
                        f"[NO ROOM] lesson_id={lesson.id}: {reason}"
                    )

                    report.add_failure(lesson.id, reason)
                    continue
                      
                # -------------------------------------
                # Проверка конфликтов
                # -------------------------------------

                conflicts = check_conflicts(
                    db=db,
                    lesson_id=lesson.id,
                    room_id=room["room_id"],
                    schedule_date=schedule_date,
                    start_time=start,
                    end_time=end,
                )

                if conflicts:
                    print(
                        f"[CONFLICT] lesson_id={lesson.id}, "
                        f"date={schedule_date}, start={start}, "
                        f"room_id={room['room_id']}, "
                        f"details={conflicts!r}"
                    )
                    continue

                # -------------------------------------
                # Создание записи
                # -------------------------------------

                entry = ScheduleEntry(
                    lesson_id=lesson.id,
                    room_id=room["room_id"],
                    date=schedule_date,
                    start_time=start,
                    end_time=end,
                )

                db.add(entry)

                db.flush()

                created_entries.append(entry)

                report.add_success()

                scheduled = True

                print(
                    f"Занятие {lesson.id} назначено: "
                    f"{schedule_date} "
                    f"{start}-{end}, "
                    f"аудитория "
                    f"{room['room_id']}, "
                    f"доступ "
                    f"{room['access_type']}, "
                    f"предыдущая аудитория: "
                    f"{previous_room_id}, "
                    f"переход: "
                    f"{room['transition_time']} мин, "
                    f"перемещение: "
                    f"{room['travel_time']} мин, "
                    f"ключ: "
                    f"{room['key_time']} мин."
                )

                break

            if scheduled:
                break

        if not scheduled:

            print(
                f"Не удалось назначить "
                f"занятие {lesson.id}"
            )

    db.commit()

    report.print()

    return created_entries