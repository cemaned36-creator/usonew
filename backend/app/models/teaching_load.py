from sqlalchemy import Column, ForeignKey, Integer, String, Text
from app.database import Base


class TeachingLoad(Base):
    """Imported teaching workload; this is not a timetable with day/time slots."""

    __tablename__ = "teaching_load"

    id = Column(Integer, primary_key=True, index=True)
    source_row_number = Column(Integer, nullable=False, unique=True, index=True)

    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("student_groups.id"), nullable=False, index=True)

    teacher_position = Column(String(100), nullable=True)
    faculty = Column(String(50), nullable=True)
    lesson_type = Column(String(50), nullable=False)
    subgroup = Column(String(30), nullable=True)
    weeks_label = Column(String(30), nullable=False)
    odd_pairs = Column(Integer, nullable=False, default=0)
    even_pairs = Column(Integer, nullable=False, default=0)
    source_room = Column(String(50), nullable=True)
    joint_groups = Column(Text, nullable=True)
