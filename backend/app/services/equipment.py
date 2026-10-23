from sqlalchemy.orm import Session

from app.models.equipment_profile import (
    RoomEquipmentProfile,
    LessonEquipmentProfile,
)


def load_equipment_profiles(db: Session):
    """Load room capabilities and lesson requirements in two queries."""
    room_profiles = {}
    lesson_profiles = {}

    for link in db.query(RoomEquipmentProfile).all():
        room_profiles.setdefault(link.room_id, set()).add(
            link.profile_code
        )

    for link in db.query(LessonEquipmentProfile).all():
        lesson_profiles.setdefault(link.lesson_id, set()).add(
            link.profile_code
        )

    return room_profiles, lesson_profiles


def room_has_required_profiles(
    room_id: int,
    lesson_id: int,
    room_profiles: dict,
    lesson_profiles: dict,
) -> bool:
    required = lesson_profiles.get(lesson_id, set())
    available = room_profiles.get(room_id, set())
    return required.issubset(available)