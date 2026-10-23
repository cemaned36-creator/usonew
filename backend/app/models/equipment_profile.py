from sqlalchemy import (
    Column, Integer, String, ForeignKey, PrimaryKeyConstraint,
)
from app.database import Base


class EquipmentProfile(Base):
    __tablename__ = "equipment_profiles"

    code = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)


class RoomEquipmentProfile(Base):
    __tablename__ = "room_equipment_profiles"

    room_id = Column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_code = Column(
        String(50),
        ForeignKey("equipment_profiles.code"),
        nullable=False,
    )

    __table_args__ = (
        PrimaryKeyConstraint(
            "room_id", "profile_code",
            name="pk_room_equipment_profiles",
        ),
    )


class LessonEquipmentProfile(Base):
    __tablename__ = "lesson_equipment_profiles"

    lesson_id = Column(
        Integer,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_code = Column(
        String(50),
        ForeignKey("equipment_profiles.code"),
        nullable=False,
    )

    __table_args__ = (
        PrimaryKeyConstraint(
            "lesson_id", "profile_code",
            name="pk_lesson_equipment_profiles",
        ),
    )