from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.models.lesson_requirement import LessonRequirement
from app.models.room import Room
from app.models.student_group import StudentGroup
from app.services.access import calculate_transition_time


def recommend_room(
    db: Session,
    lesson_id: int,
    previous_room_id: int | None = None,
    previous_access_type: str | None = None,
    available_transition_minutes: int | None = None,
    excluded_room_ids: set[int] | None = None,
):
    lesson = (
        db.query(Lesson)
        .filter(Lesson.id == lesson_id)
        .first()
    )

    if not lesson:
        return None

    requirement = (
        db.query(LessonRequirement)
        .filter(
            LessonRequirement.lesson_id == lesson_id
        )
        .first()
    )

    if not requirement:
        return None

    group = (
        db.query(StudentGroup)
        .filter(
            StudentGroup.id == lesson.group_id
        )
        .first()
    )

    if not group:
        return None

    excluded_room_ids = excluded_room_ids or set()

    rooms = (
        db.query(Room)
        .filter(
            Room.capacity >= group.students_count,
            Room.capacity >= requirement.min_capacity,
            Room.room_type == requirement.room_type,
        )
        .all()
    )

    best_room = None
    best_score = -999999
    best_transition = None

    failure_reasons = []

    for room in rooms:

        # -------------------------------------------------
        # Не используем аудитории, которые уже заняты
        # в симулируемом расписании
        # -------------------------------------------------

        if room.id in excluded_room_ids:
            failure_reasons.append(
                {
                    "type": "ROOM_OCCUPIED",
                    "room_id": room.id,
                    "room_name": room.name,
                }
            )

            continue

        # -------------------------------------------------
        # Требования к оборудованию
        # -------------------------------------------------

        if (
            requirement.projector_required
            and not room.has_projector
        ):
            failure_reasons.append(
                {
                    "type": "NO_PROJECTOR",
                    "room_id": room.id,
                    "room_name": room.name,
                }
            )

            continue

        if (
            requirement.computers_required
            and not room.has_computers
        ):
            failure_reasons.append(
                {
                    "type": "NO_COMPUTERS",
                    "room_id": room.id,
                    "room_name": room.name,
                }
            )

            continue

        if (
            requirement.whiteboard_required
            and not room.board_type
        ):
            failure_reasons.append(
                {
                    "type": "NO_WHITEBOARD",
                    "room_id": room.id,
                    "room_name": room.name,
                }
            )

            continue

        # -------------------------------------------------
        # Расчёт перехода
        # -------------------------------------------------

        transition = calculate_transition_time(
            db=db,
            previous_room_id=previous_room_id,
            previous_access_type=previous_access_type,
            target_room_id=room.id,
            target_access_type=room.access_type,
        )

        if transition is None:
            failure_reasons.append(
                {
                    "type": "NO_PATH",
                    "room_id": room.id,
                    "room_name": room.name,
                }
            )

            continue

        total_transition_time = transition[
            "total_time"
        ]

        # -------------------------------------------------
        # Проверяем доступное время между занятиями
        # -------------------------------------------------

        if (
            available_transition_minutes is not None
            and total_transition_time
            > available_transition_minutes
        ):
            failure_reasons.append(
                {
                    "type": "TRANSITION_TOO_LONG",
                    "room_id": room.id,
                    "room_name": room.name,
                    "required_minutes": total_transition_time,
                    "available_minutes": available_transition_minutes,
                    "travel_time": transition[
                        "travel_time"
                    ],
                    "key_time": transition[
                        "key_time"
                    ],
                }
            )

            continue

        # -------------------------------------------------
        # Оценка аудитории
        # -------------------------------------------------

        score = 0

        # Чем меньше переход — тем лучше
        score -= total_transition_time * 2

        # Предпочитаем PASS
        if room.access_type == "PASS":
            score += 5

        # Небольшой запас по вместимости
        if room.capacity - group.students_count >= 5:
            score += 10

        # Предпочитаем нижние этажи
        score -= room.floor

        # -------------------------------------------------
        # Лучший вариант
        # -------------------------------------------------

        if score > best_score:
            best_score = score
            best_room = room
            best_transition = transition

    # -----------------------------------------------------
    # Причина результата
    # -----------------------------------------------------

    if best_room:
        reason = "Аудитория выбрана"
    else:
        reason = "Нет подходящей аудитории"

    return {
        "room": (
            best_room.name
            if best_room
            else None
        ),

        "room_id": (
            best_room.id
            if best_room
            else None
        ),

        "score": best_score,

        "reasons": failure_reasons,

        "access_type": (
            best_room.access_type
            if best_room
            else None
        ),

        "transition_time": (
            best_transition["total_time"]
            if best_transition
            else None
        ),

        "travel_time": (
            best_transition["travel_time"]
            if best_transition
            else None
        ),

        "key_time": (
            best_transition["key_time"]
            if best_transition
            else None
        ),

        "reason": reason,
    }