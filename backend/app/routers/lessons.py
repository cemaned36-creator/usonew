from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lesson import Lesson
from app.models.lesson_group import LessonGroup
from app.models.teacher import Teacher
from app.models.subject import Subject
from app.models.student_group import StudentGroup
from app.services.lesson_participants import (
    load_lesson_participants,
    get_lesson_students_count,
)


router = APIRouter(prefix="/lessons", tags=["Lessons"])


class LessonCreate(BaseModel):
    teacher_id: int
    subject_id: int
    group_id: int


def serialize_lesson(lesson, members):
    return {
        "id": lesson.id,
        "teacher_id": lesson.teacher_id,
        "subject_id": lesson.subject_id,
        "group_id": lesson.group_id,
        "group_ids": [member["group_id"] for member in members],
        "groups": members,
        "students_count": get_lesson_students_count(members),
        "lesson_type": lesson.lesson_type,
        "weeks_label": lesson.weeks_label,
        "odd_pairs": lesson.odd_pairs,
        "even_pairs": lesson.even_pairs,
    }


@router.get("/")
def get_lessons(db: Session = Depends(get_db)):
    lessons = db.query(Lesson).order_by(Lesson.id).all()

    participants = load_lesson_participants(
        db, [lesson.id for lesson in lessons]
    )

    return [
        serialize_lesson(lesson, participants[lesson.id])
        for lesson in lessons
    ]


@router.post("/")
def create_lesson(
    data: LessonCreate,
    db: Session = Depends(get_db),
):
    if db.get(Teacher, data.teacher_id) is None:
        raise HTTPException(404, "Teacher not found")

    if db.get(Subject, data.subject_id) is None:
        raise HTTPException(404, "Subject not found")

    group = db.get(StudentGroup, data.group_id)
    if group is None:
        raise HTTPException(404, "Student group not found")

    if group.students_count <= 0:
        raise HTTPException(409, "Group size must be positive")

    try:
        lesson = Lesson(
            teacher_id=data.teacher_id,
            subject_id=data.subject_id,
            group_id=data.group_id,
        )
        db.add(lesson)
        db.flush()

        db.add(LessonGroup(
            lesson_id=lesson.id,
            group_id=data.group_id,
            subgroup_number=0,
        ))
        db.flush()

        participants = load_lesson_participants(db, [lesson.id])
        result = serialize_lesson(lesson, participants[lesson.id])

        db.commit()
        return result

    except Exception:
        db.rollback()
        raise