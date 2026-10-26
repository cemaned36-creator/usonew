# Активный корпус для подбора аудиторий и оптимизации.
MAIN_BUILDING = "Главный корпус"
# Keep the old value during the code-first rollout and for old test fixtures.
ACTIVE_ROOM_BUILDINGS = frozenset({"Б", MAIN_BUILDING})


def room_in_active_scope(room) -> bool:
    return (
        room is not None
        and room.building in ACTIVE_ROOM_BUILDINGS
        and room.room_type != "gym"
    )
