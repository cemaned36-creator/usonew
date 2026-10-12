from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.database import Base

class LessonRequirement(Base):
    __tablename__ = "lesson_requirements"

    id = Column(Integer, primary_key=True, index=True)

    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id"),
        nullable=False,
        unique=True
    )

    min_capacity = Column(Integer, nullable=False)

    room_type = Column(String(50), nullable=True)

    projector_required = Column(Boolean, default=False)
    computers_required = Column(Boolean, default=False)
    whiteboard_required = Column(Boolean, default=False)