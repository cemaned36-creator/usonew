from sqlalchemy import (
    Column, Integer, Time, ForeignKey,
    UniqueConstraint, CheckConstraint
)
from app.database import Base


class WeeklyScheduleEntry(Base):
    __tablename__ = "weekly_schedule_entries"

    id = Column(Integer, primary_key=True, index=True)

    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id"),
        nullable=False,
        unique=True,
    )

    weekday = Column(Integer, nullable=False)

    room_id = Column(
        Integer,
        ForeignKey("rooms.id"),
        nullable=False,
    )

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="check_weekday_range",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="check_lesson_time",
        ),
    )