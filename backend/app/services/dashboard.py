from datetime import date, datetime
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.models.room import Room
from app.models.schedule_entry import ScheduleEntry

from app.services.access import calculate_transition_time
from app.services.conflict_checker import check_conflicts
from app.services.optimizer import recommend_room


KEY_OPERATION_MINUTES = 5


def calculate_current_metrics(
    db: Session,
    entries: list[ScheduleEntry],
):
    """
    Рассчитывает показатели текущего расписания.
    """

    transition_minutes = 0
    key_operations = 0

    # Группируем занятия по преподавателю
    teacher_entries = defaultdict(list)

    for entry in entries:

        lesson = (
            db.query(Lesson)
            .filter(Lesson.id == entry.lesson_id)
            .first()
        )

        if lesson:
            teacher_entries[
                lesson.teacher_id
            ].append(entry)

    # -----------------------------------------------------
    # Перемещения преподавателей
    # -----------------------------------------------------

    for teacher_id, teacher_schedule in teacher_entries.items():

        teacher_schedule.sort(
            key=lambda entry: entry.start_time
        )

        previous_entry = None

        for entry in teacher_schedule:

            if previous_entry is None:
                previous_entry = entry
                continue

            previous_room = (
                db.query(Room)
                .filter(
                    Room.id
                    == previous_entry.room_id
                )
                .first()
            )

            current_room = (
                db.query(Room)
                .filter(
                    Room.id
                    == entry.room_id
                )
                .first()
            )

            if not previous_room or not current_room:
                previous_entry = entry
                continue

            transition = calculate_transition_time(
                db=db,
                previous_room_id=previous_room.id,
                previous_access_type=previous_room.access_type,
                target_room_id=current_room.id,
                target_access_type=current_room.access_type,
            )

            if transition is not None:

                transition_minutes += (
                    transition["total_time"]
                )

                key_operations += (
                    transition["key_time"]
                    // KEY_OPERATION_MINUTES
                )

            previous_entry = entry

    # -----------------------------------------------------
    # Конфликты
    # -----------------------------------------------------

    conflicting_entries = set()

    conflict_details = []

    for entry in entries:

        lesson = (
            db.query(Lesson)
            .filter(Lesson.id == entry.lesson_id)
            .first()
        )

        if not lesson:
            continue

        conflicts = check_conflicts(
            db=db,
            lesson_id=entry.lesson_id,
            room_id=entry.room_id,
            schedule_date=entry.date,
            start_time=entry.start_time,
            end_time=entry.end_time,
        )

        if conflicts:

            conflicting_entries.add(
                entry.id
            )

            conflict_details.append(
                {
                    "entry_id": entry.id,
                    "conflicts": conflicts,
                }
            )

    return {
        "transition_minutes": transition_minutes,
        "key_operations": key_operations,
        "conflicts": len(conflicting_entries),
        "conflict_details": conflict_details,
    }


def calculate_optimized_metrics(
    db: Session,
    entries: list[ScheduleEntry],
):
    """
    Запускает optimizer в режиме dry-run.

    Существующие записи ScheduleEntry НЕ изменяются.
    """

    if not entries:
        return {
            "transition_minutes": 0,
            "key_operations": 0,
            "conflicts": 0,
            "assignments": {},
            "changes": [],
        }

    # -----------------------------------------------------
    # Сортируем по времени.
    #
    # Это важно:
    # сначала распределяются более ранние занятия,
    # чтобы у optimizer уже была информация о предыдущем
    # помещении преподавателя.
    # -----------------------------------------------------

    sorted_entries = sorted(
        entries,
        key=lambda entry: (
            entry.date,
            entry.start_time,
            entry.id,
        ),
    )

    # -----------------------------------------------------
    # Результаты симуляции
    # -----------------------------------------------------

    assignments = {}

    # предыдущая аудитория каждого преподавателя
    teacher_previous = {}

    # комнаты, занятые в конкретный момент
    simulated_entries = []

    # -----------------------------------------------------
    # Распределение аудиторий
    # -----------------------------------------------------

    for entry in sorted_entries:

        lesson = (
            db.query(Lesson)
            .filter(Lesson.id == entry.lesson_id)
            .first()
        )

        if not lesson:
            continue

        previous_data = teacher_previous.get(
            lesson.teacher_id
        )

        previous_room_id = None
        previous_access_type = None
        available_transition_minutes = None

        if previous_data:

            previous_entry = previous_data[
                "entry"
            ]

            previous_room_id = previous_data[
                "room_id"
            ]

            previous_access_type = previous_data[
                "access_type"
            ]

            previous_end = datetime.combine(
                entry.date,
                previous_entry.end_time,
            )

            current_start = datetime.combine(
                entry.date,
                entry.start_time,
            )

            available_transition_minutes = int(
                (
                    current_start
                    - previous_end
                ).total_seconds()
                / 60
            )

        # -------------------------------------------------
        # Определяем занятые аудитории
        # -------------------------------------------------

        occupied_room_ids = set()

        for simulated in simulated_entries:

            if simulated["date"] != entry.date:
                continue

            # Есть пересечение по времени
            if (
                simulated["start_time"]
                < entry.end_time
                and simulated["end_time"]
                > entry.start_time
            ):
                occupied_room_ids.add(
                    simulated["room_id"]
                )

        # -------------------------------------------------
        # Запускаем наш optimizer
        # -------------------------------------------------

        result = recommend_room(
            db=db,
            lesson_id=entry.lesson_id,
            previous_room_id=previous_room_id,
            previous_access_type=previous_access_type,
            available_transition_minutes=available_transition_minutes,
            excluded_room_ids=occupied_room_ids,
        )

        if not result or not result["room_id"]:

            # Если optimizer не смог подобрать
            # аудиторию — оставляем текущую.
            room_id = entry.room_id

            room = (
                db.query(Room)
                .filter(Room.id == room_id)
                .first()
            )

            access_type = (
                room.access_type
                if room
                else None
            )

        else:

            room_id = result["room_id"]
            access_type = result["access_type"]

        # -------------------------------------------------
        # Сохраняем симулированное назначение
        # -------------------------------------------------

        assignments[entry.id] = {
            "room_id": room_id,
            "access_type": access_type,
        }

        simulated_entries.append(
            {
                "entry_id": entry.id,
                "lesson_id": entry.lesson_id,
                "date": entry.date,
                "start_time": entry.start_time,
                "end_time": entry.end_time,
                "room_id": room_id,
            }
        )

        teacher_previous[
            lesson.teacher_id
        ] = {
            "entry": entry,
            "room_id": room_id,
            "access_type": access_type,
        }

    # -----------------------------------------------------
    # Метрики после оптимизации
    # -----------------------------------------------------

    transition_minutes = 0
    key_operations = 0

    teacher_entries = defaultdict(list)

    for entry in entries:

        lesson = (
            db.query(Lesson)
            .filter(Lesson.id == entry.lesson_id)
            .first()
        )

        if lesson:
            teacher_entries[
                lesson.teacher_id
            ].append(entry)

    for teacher_id, teacher_schedule in teacher_entries.items():

        teacher_schedule.sort(
            key=lambda entry: entry.start_time
        )

        previous_entry = None

        for entry in teacher_schedule:

            if previous_entry is None:
                previous_entry = entry
                continue

            previous_assignment = assignments.get(
                previous_entry.id
            )

            current_assignment = assignments.get(
                entry.id
            )

            if (
                not previous_assignment
                or not current_assignment
            ):
                previous_entry = entry
                continue

            transition = calculate_transition_time(
                db=db,
                previous_room_id=previous_assignment[
                    "room_id"
                ],
                previous_access_type=previous_assignment[
                    "access_type"
                ],
                target_room_id=current_assignment[
                    "room_id"
                ],
                target_access_type=current_assignment[
                    "access_type"
                ],
            )

            if transition is not None:

                transition_minutes += (
                    transition["total_time"]
                )

                key_operations += (
                    transition["key_time"]
                    // KEY_OPERATION_MINUTES
                )

            previous_entry = entry

    # -----------------------------------------------------
    # Конфликты после оптимизации
    # -----------------------------------------------------

    optimized_conflicts = set()

    for i, first in enumerate(
        simulated_entries
    ):

        for second in simulated_entries[
            i + 1 :
        ]:

            if first["date"] != second["date"]:
                continue

            overlap = (
                first["start_time"]
                < second["end_time"]
                and first["end_time"]
                > second["start_time"]
            )

            if not overlap:
                continue

            if (
                first["room_id"]
                == second["room_id"]
            ):

                optimized_conflicts.add(
                    first["entry_id"]
                )

                optimized_conflicts.add(
                    second["entry_id"]
                )

    
    # -----------------------------------------------------
    # Список изменённых аудиторий
    # -----------------------------------------------------

    changes = []

    from app.models.subject import Subject
    from app.models.teacher import Teacher
    from app.models.student_group import StudentGroup

    for entry in sorted_entries:
        assignment = assignments.get(entry.id)

        if not assignment:
            continue

        # Сравниваем с исходной аудиторией в БД
        if assignment["room_id"] == entry.room_id:
            continue

        old_room = (
            db.query(Room)
            .filter(Room.id == entry.room_id)
            .first()
        )

        new_room = (
            db.query(Room)
            .filter(Room.id == assignment["room_id"])
            .first()
        )

        lesson = (
            db.query(Lesson)
            .filter(Lesson.id == entry.lesson_id)
            .first()
        )

        if not old_room or not new_room or not lesson:
            continue

        subject = (
            db.query(Subject)
            .filter(Subject.id == lesson.subject_id)
            .first()
        )

        teacher = (
            db.query(Teacher)
            .filter(Teacher.id == lesson.teacher_id)
            .first()
        )

        group = (
            db.query(StudentGroup)
            .filter(StudentGroup.id == lesson.group_id)
            .first()
        )

        changes.append({
            "entry_id": entry.id,
            "lesson_id": lesson.id,
            "date": entry.date.isoformat(),
            "time": entry.start_time.strftime("%H:%M"),
            "end": entry.end_time.strftime("%H:%M"),
            "subject": subject.name if subject else "Неизвестный предмет",
            "teacher": teacher.name if teacher else "Неизвестный преподаватель",
            "group": group.name if group else "Неизвестная группа",
            "from_room": old_room.name,
            "from_room_id": old_room.id,
            "to_room": new_room.name,
            "to_room_id": new_room.id,
            "reason": "Аудитория изменена по результатам dry-run",
        })

    return {
        "transition_minutes": transition_minutes,
        "key_operations": key_operations,
        "conflicts": len(optimized_conflicts),
        "assignments": assignments,
        "changes": changes,
    }


def get_dashboard_data(
    db: Session,
    target_date: date,
):
    """
    Полностью формирует данные Dashboard.
    """

    # -----------------------------------------------------
    # Статистика
    # -----------------------------------------------------

    from app.models.teacher import Teacher

    lessons_count = (
        db.query(Lesson).count()
    )

    teachers_count = (
        db.query(Teacher).count()
    )

    rooms_count = (
        db.query(Room).count()
    )

    # -----------------------------------------------------
    # Расписание выбранного дня
    # -----------------------------------------------------

    entries = (
        db.query(ScheduleEntry)
        .filter(
            ScheduleEntry.date
            == target_date
        )
        .order_by(
            ScheduleEntry.start_time
        )
        .all()
    )

    # -----------------------------------------------------
    # Текущие метрики
    # -----------------------------------------------------

    before = calculate_current_metrics(
        db=db,
        entries=entries,
    )

    # -----------------------------------------------------
    # Оптимизированные метрики
    # -----------------------------------------------------

    after = calculate_optimized_metrics(
        db=db,
        entries=entries,
    )

    # -----------------------------------------------------
    # Расписание для frontend
    # -----------------------------------------------------

    schedule = []

    from app.models.subject import Subject
    from app.models.teacher import Teacher
    from app.models.student_group import StudentGroup

    for entry in entries:

        lesson = (
            db.query(Lesson)
            .filter(
                Lesson.id
                == entry.lesson_id
            )
            .first()
        )

        if not lesson:
            continue

        teacher = (
            db.query(Teacher)
            .filter(
                Teacher.id
                == lesson.teacher_id
            )
            .first()
        )

        subject = (
            db.query(Subject)
            .filter(
                Subject.id
                == lesson.subject_id
            )
            .first()
        )

        group = (
            db.query(StudentGroup)
            .filter(
                StudentGroup.id
                == lesson.group_id
            )
            .first()
        )

        room = (
            db.query(Room)
            .filter(
                Room.id
                == entry.room_id
            )
            .first()
        )

        if not room:
            continue

        schedule.append(
            {
                "id": entry.id,
                "time": entry.start_time.strftime(
                    "%H:%M"
                ),
                "end": entry.end_time.strftime(
                    "%H:%M"
                ),
                "subject": (
                    subject.name
                    if subject
                    else "Неизвестный предмет"
                ),
                "teacher": (
                    teacher.name
                    if teacher
                    else "Неизвестный преподаватель"
                ),
                "group": (
                    group.name
                    if group
                    else "Неизвестная группа"
                ),
                "room": room.name,
                "room_type": room.room_type,
                "access_type": room.access_type,
            }
        )

    # -----------------------------------------------------
    # Финальный результат
    # -----------------------------------------------------

    return {
        "date": target_date.isoformat(),

        "stats": {
            "lessons": lessons_count,
            "teachers": teachers_count,
            "rooms": rooms_count,
            "problems": before["conflicts"],
        },

        "schedule": schedule,

        "optimization": {
            "before": {
                "transition_minutes": before[
                    "transition_minutes"
                ],
                "key_operations": before[
                    "key_operations"
                ],
                "conflicts": before[
                    "conflicts"
                ],
            },

            "after": {
                "transition_minutes": after[
                    "transition_minutes"
                ],
                "key_operations": after[
                    "key_operations"
                ],
                "conflicts": after[
                    "conflicts"
                ],
            },
            "changes": after["changes"],
        },
    }