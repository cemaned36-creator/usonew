
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lesson import Lesson
from app.models.teacher import Teacher
from app.models.subject import Subject
from app.models.student_group import StudentGroup

router = APIRouter(prefix="/lessons", tags=["Lessons"])


class LessonCreate(BaseModel):
    teacher_id: int
    subject_id: int
    group_id: int


@router.get("/")
def get_lessons(db: Session = Depends(get_db)):
    lessons = db.query(Lesson).order_by(Lesson.id).all()

    return [
        {
            "id": lesson.id,
            "teacher_id": lesson.teacher_id,
            "subject_id": lesson.subject_id,
            "group_id": lesson.group_id,
        }
        for lesson in lessons
    ]


@router.post("/")
def create_lesson(
    data: LessonCreate,
    db: Session = Depends(get_db),
):
    if not db.get(Teacher, data.teacher_id):
        raise HTTPException(404, "Teacher not found")

    if not db.get(Subject, data.subject_id):
        raise HTTPException(404, "Subject not found")

    if not db.get(StudentGroup, data.group_id):
        raise HTTPException(404, "Student group not found")

    lesson = Lesson(
        teacher_id=data.teacher_id,
        subject_id=data.subject_id,
        group_id=data.group_id,
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    return {
        "id": lesson.id,
        "teacher_id": lesson.teacher_id,
        "subject_id": lesson.subject_id,
        "group_id": lesson.group_id,
    }
