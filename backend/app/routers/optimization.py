from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lesson import Lesson
from app.models.lesson_requirement import LessonRequirement
from app.models.room import Room
from app.models.student_group import StudentGroup
from app.models.weekly_schedule_entry import WeeklyScheduleEntry
from app.services.optimization import (
    ScheduleItem,
    _has_schedule_conflict,
    _room_fits,
    _teacher_transition_total,
    preview_optimization,
)


router = APIRouter(
    prefix="/optimization",
    tags=["Optimization"],
)


class OptimizationChange(BaseModel):
    entry_id: int
    old_room_id: int
    new_room_id: int


class OptimizationApplyRequest(BaseModel):
    changes: list[OptimizationChange]
    week_type: str = "odd"


@router.get("/preview")
def optimization_preview(
    week_type: str = "odd",
    db: Session = Depends(get_db),
):
    try:
        if week_type not in {"odd", "even"}:
            raise HTTPException(status_code=422, detail="week_type должен быть odd или even")
        return preview_optimization(db, week_type=week_type)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка предварительной оптимизации: {str(e)}",
        ) from e


@router.post("/apply")
def apply_optimization(
    payload: OptimizationApplyRequest,
    db: Session = Depends(get_db),
):
    """Проверяет актуальность плана и сохраняет его атомарно."""

    try:
        if not payload.changes:
            raise HTTPException(
                status_code=400,
                detail="Нет изменений для сохранения.",
            )

        # Повторно строим план на актуальных данных. Это защищает от
        # сохранения устаревшего или вручную изменённого preview.
        if payload.week_type not in {"odd", "even"}:
            raise HTTPException(status_code=422, detail="week_type должен быть odd или even")
        current_preview = preview_optimization(db, week_type=payload.week_type)
        expected = {
            item["entry_id"]: item
            for item in current_preview["changes"]
        }
        submitted = {item.entry_id: item for item in payload.changes}

        if len(submitted) != len(payload.changes):
            raise HTTPException(
                status_code=400,
                detail="В запросе повторяется одна и та же запись расписания.",
            )

        if set(submitted) != set(expected):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Расписание изменилось после предварительного расчёта. "
                    "Запусти оптимизацию заново и проверь новый результат."
                ),
            )

        for entry_id, item in submitted.items():
            fresh = expected[entry_id]
            if (
                item.old_room_id != fresh["old_room_id"]
                or item.new_room_id != fresh["new_room_id"]
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "План оптимизации устарел или был изменён. "
                        "Запусти расчёт заново."
                    ),
                )

        db_entries = (
            db.query(WeeklyScheduleEntry)
            .filter(WeeklyScheduleEntry.week_type == payload.week_type)
            .order_by(
                WeeklyScheduleEntry.weekday,
                WeeklyScheduleEntry.start_time,
            )
            .with_for_update()
            .all()
        )
        orm_by_id = {item.id: item for item in db_entries}

        if not set(submitted).issubset(orm_by_id):
            raise HTTPException(
                status_code=409,
                detail="Некоторые записи расписания уже удалены.",
            )

        rooms_list = db.query(Room).all()
        rooms = {room.id: room for room in rooms_list}
        lessons = {item.id: item for item in db.query(Lesson).all()}
        requirements = {
            item.lesson_id: item
            for item in db.query(LessonRequirement).all()
        }
        groups = {item.id: item for item in db.query(StudentGroup).all()}

        # Проверяем копии, не изменяя ORM-записи до успешной проверки.
        entries = [
            ScheduleItem(
                id=item.id,
                lesson_id=item.lesson_id,
                weekday=item.weekday,
                room_id=item.room_id,
                start_time=item.start_time,
                end_time=item.end_time,
            )
            for item in db_entries
        ]
        entries_by_id = {item.id: item for item in entries}

        for entry_id, change in submitted.items():
            entry = entries_by_id[entry_id]
            if entry.room_id != change.old_room_id:
                raise HTTPException(
                    status_code=409,
                    detail="Исходная аудитория уже изменилась. Запусти расчёт заново.",
                )

            lesson = lessons.get(entry.lesson_id)
            target_room = rooms.get(change.new_room_id)
            if lesson is None or target_room is None:
                raise HTTPException(
                    status_code=409,
                    detail="Не найдено занятие или новая аудитория.",
                )

            requirement = requirements.get(entry.lesson_id)
            group = groups.get(lesson.group_id)
            if not _room_fits(target_room, requirement, group):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Аудитория {target_room.name} больше не подходит "
                        f"для занятия {entry.lesson_id}."
                    ),
                )

            entry.room_id = change.new_room_id

        # Проверяем занятость аудиторий, преподавателей и групп для
        # всего результирующего расписания.
        for entry in entries:
            lesson = lessons.get(entry.lesson_id)
            if lesson is None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Для записи {entry.id} не найдено занятие.",
                )
            room = rooms.get(entry.room_id)
            if room is None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Для записи {entry.id} не найдена аудитория.",
                )
            if _has_schedule_conflict(room, entry, entries, lessons):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "После изменения обнаружен конфликт расписания. "
                        "Изменения не сохранены; запусти оптимизацию заново."
                    ),
                )

        transition_total = _teacher_transition_total(
            entries, lessons, rooms, db
        )
        if transition_total is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "В итоговом расписании есть невозможный переход "
                    "или недостаточно времени. Изменения не сохранены."
                ),
            )

        for entry_id, change in submitted.items():
            orm_by_id[entry_id].room_id = change.new_room_id

        db.commit()

        return {
            "status": "success",
            "message": "Оптимизированное расписание сохранено.",
            "saved_count": len(submitted),
            "saved_to_database": True,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Не удалось сохранить оптимизацию. Изменения отменены.",
        ) from e
