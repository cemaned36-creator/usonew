from sqlalchemy import Column, Integer, String
from app.database import Base

class StudentGroup(Base):
    __tablename__ = "student_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    students_count = Column(Integer, nullable=False)
