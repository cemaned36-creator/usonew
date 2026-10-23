# Активный корпус для подбора аудиторий и оптимизации.
ACTIVE_ROOM_BUILDINGS = frozenset({"Б"})


def room_in_active_scope(room) -> bool:
    return (
        room is not None
        and room.building in ACTIVE_ROOM_BUILDINGS
        and room.room_type != "gym"
    )