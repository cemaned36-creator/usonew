from sqlalchemy import (
    Column, Integer, ForeignKey,
    PrimaryKeyConstraint, UniqueConstraint,
)
from app.database import Base


class LessonTeachingLoad(Base):
    __tablename__ = "lesson_teaching_loads"

    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
    )

    teaching_load_id = Column(
        Integer,
        ForeignKey("teaching_load.id"),
        nullable=False,
    )

    __table_args__ = (
        PrimaryKeyConstraint(
            "lesson_id", "teaching_load_id",
            name="pk_lesson_teaching_loads",
        ),
        UniqueConstraint(
            "teaching_load_id",
            name="uq_lesson_teaching_loads_source",
        ),
    )