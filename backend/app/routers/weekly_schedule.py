
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lesson import Lesson
from app.models.room import Room
from app.models.weekly_schedule_entry import WeeklyScheduleEntry
from app.schemas.weekly_schedule import WeeklyScheduleCreate
from app.services.access import calculate_transition_time

router = APIRouter(
    prefix="/weekly-schedule",
    tags=["Weekly Schedule"],
)


def overlaps(start1, end1, start2, end2):
    """Проверяет пересечение двух временных интервалов."""
    return start1 < end2 and start2 < end1


def minutes_between(start_time, end_time):
    """Количество минут между двумя значениями времени."""
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    return end_minutes - start_minutes


def check_transition(
    db: Session,
    previous_room: Room,
    target_room: Room,
    available_minutes: int,
):
    """Проверяет, успеет ли преподаватель перейти в другую аудиторию."""

    transition = calculate_transition_time(
        db=db,
        previous_room_id=previous_room.id,
        previous_access_type=previous_room.access_type,
        target_room_id=target_room.id,
        target_access_type=target_room.access_type,
    )

    if transition is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Не найден маршрут из аудитории "
                f"{previous_room.name} в аудиторию {target_room.name}. "
                "Невозможно проверить время перехода."
            ),
        )

    required_minutes = transition["total_time"]

    if required_minutes > available_minutes:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Недостаточно времени на переход из аудитории "
                f"{previous_room.name} в аудиторию {target_room.name}. "
                f"Необходимо {required_minutes} мин., "
                f"доступно {available_minutes} мин. "
                f"Время перемещения: {transition['travel_time']} мин.; "
                f"операции с ключами: {transition['key_time']} мин."
            ),
        )


@router.get("/")
def get_weekly_schedule(db: Session = Depends(get_db)):
    entries = (
        db.query(WeeklyScheduleEntry)
        .order_by(
            WeeklyScheduleEntry.weekday,
            WeeklyScheduleEntry.start_time,
        )
        .all()
    )

    result = []

    for entry in entries:
        lesson = db.get(Lesson, entry.lesson_id)
        room = db.get(Room, entry.room_id)

        result.append({
            "id": entry.id,
            "lesson_id": entry.lesson_id,
            "weekday": entry.weekday,
            "start_time": entry.start_time.strftime("%H:%M"),
            "end_time": entry.end_time.strftime("%H:%M"),
            "room_id": entry.room_id,
            "room_name": room.name if room else None,
            "teacher_id": lesson.teacher_id if lesson else None,
            "subject_id": lesson.subject_id if lesson else None,
            "group_id": lesson.group_id if lesson else None,
        })

    return result


@router.post("/")
def assign_lesson(
    data: WeeklyScheduleCreate,
    db: Session = Depends(get_db),
):
    lesson = db.get(Lesson, data.lesson_id)
    room = db.get(Room, data.room_id)

    if not lesson:
        raise HTTPException(404, "Занятие не найдено")

    if not room:
        raise HTTPException(404, "Аудитория не найдена")

    if data.start_time >= data.end_time:
        raise HTTPException(
            400,
            "Время окончания должно быть позже времени начала",
        )

    existing = (
        db.query(WeeklyScheduleEntry)
        .filter(
            WeeklyScheduleEntry.lesson_id == data.lesson_id,
            WeeklyScheduleEntry.weekday == data.weekday,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Это занятие уже добавлено в расписание на этот день."
        )


    entries = (
        db.query(WeeklyScheduleEntry)
        .filter(
            WeeklyScheduleEntry.weekday == data.weekday
        )
        .all()
    )

    # Сначала проверяем конфликты расписания.
    for entry in entries:
        other_lesson = db.get(Lesson, entry.lesson_id)

        if not other_lesson:
            continue

        if not overlaps(
            data.start_time,
            data.end_time,
            entry.start_time,
            entry.end_time,
        ):
            continue

        if entry.room_id == data.room_id:
            raise HTTPException(
                409,
                "Аудитория уже занята в это время",
            )

        if other_lesson.teacher_id == lesson.teacher_id:
            raise HTTPException(
                409,
                "У преподавателя уже есть занятие в это время",
            )

        if other_lesson.group_id == lesson.group_id:
            raise HTTPException(
                409,
                "У группы уже есть занятие в это время",
            )

    # Ищем ближайшее предыдущее и следующее занятие
    # этого же преподавателя в этот день.
    teacher_entries = []

    for entry in entries:
        other_lesson = db.get(Lesson, entry.lesson_id)

        if (
            other_lesson
            and other_lesson.teacher_id == lesson.teacher_id
        ):
            teacher_entries.append((entry, other_lesson))

    previous = [
        (entry, other_lesson)
        for entry, other_lesson in teacher_entries
        if entry.end_time <= data.start_time
    ]

    following = [
        (entry, other_lesson)
        for entry, other_lesson in teacher_entries
        if entry.start_time >= data.end_time
    ]

    # Проверяем переход от предыдущего занятия к новому.
    if previous:
        previous_entry, _ = max(
            previous,
            key=lambda item: item[0].end_time,
        )

        previous_room = db.get(Room, previous_entry.room_id)

        if not previous_room:
            raise HTTPException(
                409,
                "Не удалось найти аудиторию предыдущего занятия",
            )

        available_minutes = minutes_between(
            previous_entry.end_time,
            data.start_time,
        )

        check_transition(
            db=db,
            previous_room=previous_room,
            target_room=room,
            available_minutes=available_minutes,
        )

    # Проверяем переход от нового занятия к следующему.
    if following:
        next_entry, _ = min(
            following,
            key=lambda item: item[0].start_time,
        )

        next_room = db.get(Room, next_entry.room_id)

        if not next_room:
            raise HTTPException(
                409,
                "Не удалось найти аудиторию следующего занятия",
            )

        available_minutes = minutes_between(
            data.end_time,
            next_entry.start_time,
        )

        check_transition(
            db=db,
            previous_room=room,
            target_room=next_room,
            available_minutes=available_minutes,
        )

    # Сохраняем запись только после успешных проверок.
    entry = WeeklyScheduleEntry(
        lesson_id=data.lesson_id,
        weekday=data.weekday,
        room_id=data.room_id,
        start_time=data.start_time,
        end_time=data.end_time,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "status": "success",
        "message": "Занятие добавлено в недельное расписание",
        "id": entry.id,
    }


@router.delete("/{entry_id}")
def delete_weekly_entry(
    entry_id: int,
    db: Session = Depends(get_db),
):
    entry = db.get(WeeklyScheduleEntry, entry_id)

    if not entry:
        raise HTTPException(404, "Запись не найдена")

    db.delete(entry)
    db.commit()

    return {"status": "success"}
