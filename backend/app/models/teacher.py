from sqlalchemy import Column, Integer, String, Boolean, CheckConstraint
from app.database import Base


class Teacher(Base):

    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=True)

    earliest_start_pair = Column(Integer, nullable=False, default=1, server_default="1")
    max_floor = Column(Integer, nullable=True)
    prefer_near_entrance = Column(Boolean, nullable=False, default=False, server_default="false")

    __table_args__ = (
        CheckConstraint("earliest_start_pair BETWEEN 1 AND 3", name="ck_teacher_start_pair"),
        CheckConstraint("max_floor IS NULL OR max_floor BETWEEN 1 AND 4", name="ck_teacher_max_floor"),
    )
