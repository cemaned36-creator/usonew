from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal, Annotated
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.teacher import Teacher
from app.models.lesson import Lesson
from app.models.room import Room
from app.models.weekly_schedule_entry import WeeklyScheduleEntry
from app.services.teacher_conditions import condition_issues

router = APIRouter(prefix="/teachers", tags=["Teachers"])

class TeacherConditions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    earliest_start_pair: int = Field(ge=1, le=3)
    max_floor: int | None = Field(default=None, ge=1, le=4)
    prefer_near_entrance: bool = False
    preferred_rooms_by_type: dict[
        Literal["Лекция", "Практика", "Лабораторная"],
        list[Annotated[int, Field(gt=0)]],
    ] = Field(default_factory=dict)

    @field_validator("preferred_rooms_by_type")
    @classmethod
    def unique_rooms(cls, value):
        if any(len(ids) > 100 or len(ids) != len(set(ids)) for ids in value.values()):
            raise ValueError("Выберите до 100 различных аудиторий для каждого типа занятия.")
        return value


@router.get("/")
def get_teachers(db: Session = Depends(get_db)):
    return db.query(Teacher).order_by(Teacher.id).all()

@router.put("/{teacher_id}/conditions")
def update_conditions(teacher_id: int, data: TeacherConditions, db: Session = Depends(get_db)):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).with_for_update().first()
    if teacher is None:
        raise HTTPException(404, "Преподаватель не найден")
    try:
        values = data.model_dump()
        if "preferred_rooms_by_type" not in data.model_fields_set:
            values.pop("preferred_rooms_by_type")
        else:
            requested = {rid for ids in data.preferred_rooms_by_type.values() for rid in ids}
            existing = {room.id for room in db.query(Room).filter(Room.id.in_(requested)).all()}
            if requested != existing:
                raise HTTPException(422, "Выбранная аудитория не найдена. Обновите список аудиторий.")
        for key, value in values.items():
            setattr(teacher, key, value)
        lessons = {x.id: x for x in db.query(Lesson).filter(Lesson.teacher_id == teacher_id).all()}
        entries = db.query(WeeklyScheduleEntry).filter(WeeklyScheduleEntry.lesson_id.in_(lessons)).all()
        rooms = {x.id: x for x in db.query(Room).all()}
        issues = condition_issues(entries, lessons, rooms, {teacher.id: teacher})
        db.commit()
        return {"teacher_id": teacher.id, **values, "preferred_rooms_by_type": teacher.preferred_rooms_by_type,
                "affected_entries": len({x["entry_id"] for x in issues}),
                "issues": issues, "schedule_changed": False}
    except Exception:
        db.rollback()
        raise
