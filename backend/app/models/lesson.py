from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)

    teacher_id = Column(
        Integer,
        ForeignKey("teachers.id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    group_id = Column(
        Integer,
        ForeignKey("student_groups.id"),
        nullable=False
    )
