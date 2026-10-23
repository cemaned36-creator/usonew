from sqlalchemy import (
    Column, Integer, ForeignKey, CheckConstraint,
    PrimaryKeyConstraint, Index,
)
from app.database import Base


class LessonGroup(Base):
    __tablename__ = "lesson_groups"

    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
    )

    group_id = Column(
        Integer,
        ForeignKey("student_groups.id"),
        nullable=False,
    )

    subgroup_number = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    __table_args__ = (
        PrimaryKeyConstraint(
            "lesson_id", "group_id",
            name="pk_lesson_groups",
        ),
        CheckConstraint(
            "subgroup_number IN (0, 1, 2)",
            name="ck_lesson_groups_subgroup",
        ),
        Index("ix_lesson_groups_group_id", "group_id"),
    )