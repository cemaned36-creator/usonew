from sqlalchemy import (
    Column, Integer, Time, String, ForeignKey,
    UniqueConstraint, CheckConstraint,
)
from app.database import Base


class WeeklyScheduleEntry(Base):
    __tablename__ = "weekly_schedule_entries"

    id = Column(Integer, primary_key=True, index=True)

    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id"),
        nullable=False,
    )

    weekday = Column(Integer, nullable=False)

    # odd — нечётная неделя, even — чётная неделя.
    week_type = Column(String(8), nullable=False, default="odd", server_default="odd")

    room_id = Column(
        Integer,
        ForeignKey("rooms.id"),
        nullable=False,
    )

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "lesson_id", "weekday", "week_type",
            name="uq_weekly_schedule_lesson_day_week",
        ),
        CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="check_weekday_range",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="check_lesson_time",
        ),
        CheckConstraint(
            "week_type IN ('odd', 'even')",
            name="check_week_type",
        ),
    )
