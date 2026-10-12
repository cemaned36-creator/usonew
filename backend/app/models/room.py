from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(20), nullable=False)
    building = Column(String(50), nullable=False)
    floor = Column(Integer, nullable=False)

    capacity = Column(Integer, nullable=False)

    room_type = Column(String(50), nullable=False)

    has_projector = Column(Boolean, default=False)
    has_computers = Column(Boolean, default=False)

    board_type = Column(String(50), nullable=True)

    access_type = Column(String(20), nullable=False)
