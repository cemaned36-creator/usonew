from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint
from app.database import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)

    teacher_id = Column(
        Integer,
        ForeignKey("teachers.id"),
        nullable=False,
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False,
    )

    # Compatibility field. Full membership is stored in lesson_groups.
    group_id = Column(
        Integer,
        ForeignKey("student_groups.id"),
        nullable=False,
    )

    lesson_type = Column(String(50), nullable=True)
    weeks_label = Column(String(30), nullable=True)
    odd_pairs = Column(Integer, nullable=True)
    even_pairs = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "odd_pairs >= 0",
            name="ck_lessons_odd_pairs_nonnegative",
        ),
        CheckConstraint(
            "even_pairs >= 0",
            name="ck_lessons_even_pairs_nonnegative",
        ),
    )