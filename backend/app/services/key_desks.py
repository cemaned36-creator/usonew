"""Resolve the current building's key desk before and after its rename."""
from app.models.access_point import AccessPoint
from app.services.room_scope import ACTIVE_ROOM_BUILDINGS

MAIN_DESK_NAMES = ("Охрана Главного корпуса", "Охрана корпуса Б")


def main_key_desk_id(db):
    desks = db.query(AccessPoint).filter(
        AccessPoint.name.in_(MAIN_DESK_NAMES),
        AccessPoint.point_type == "KEY_DESK",
    ).limit(2).all()
    return desks[0].id if len(desks) == 1 else None


def room_key_desk_id(db, room):
    if room is None or room.building not in ACTIVE_ROOM_BUILDINGS:
        return None
    return main_key_desk_id(db)
