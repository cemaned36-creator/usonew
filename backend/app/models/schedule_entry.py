from sqlalchemy import Column, Integer, Date, Time, ForeignKey
from app.database import Base

class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id = Column(Integer, primary_key=True, index=True)

    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id"),
        nullable=False
    )

    room_id = Column(
        Integer,
        ForeignKey("rooms.id"),
        nullable=False
    )

    date = Column(Date, nullable=False)

    start_time = Column(Time, nullable=False)

    end_time = Column(Time, nullable=False)