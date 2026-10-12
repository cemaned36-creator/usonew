from sqlalchemy.orm import Session

from app.models.room import Room
from app.services.distance import (
    get_travel_time,
    get_room_to_access_point_time,
    get_access_point_to_room_time,
)


# ID точки выдачи/возврата ключей
KEY_DESK_ID = 1

# Время получения ключа
KEY_PICKUP_TIME = 5

# Время возврата ключа
KEY_RETURN_TIME = 5


def calculate_transition_time(
    db: Session,
    previous_room_id: int | None,
    previous_access_type: str | None,
    target_room_id: int,
    target_access_type: str,
):
    """
    Рассчитывает полное время перехода преподавателя
    из предыдущей аудитории в целевую.

    Учитываются:
    - перемещение между аудиториями;
    - путь до точки выдачи ключей;
    - получение ключа;
    - возврат ключа.
    """

    # ---------------------------------------------------------
    # 1. Первое занятие
    # ---------------------------------------------------------

    if previous_room_id is None:
        if target_access_type == "PASS":
            return {
                "total_time": 0,
                "travel_time": 0,
                "key_time": 0,
            }

        if target_access_type == "KEY":
            travel_time = get_access_point_to_room_time(
                db=db,
                access_point_id=KEY_DESK_ID,
                room_id=target_room_id,
            )

            if travel_time is None:
                return None

            key_time = KEY_PICKUP_TIME

            return {
                "total_time": travel_time + key_time,
                "travel_time": travel_time,
                "key_time": key_time,
            }

    # ---------------------------------------------------------
    # 2. Предыдущая аудитория и текущая аудитория одинаковые
    # ---------------------------------------------------------

    if previous_room_id == target_room_id:
        if previous_access_type == target_access_type:
            return {
                "total_time": 0,
                "travel_time": 0,
                "key_time": 0,
            }

    # ---------------------------------------------------------
    # 3. PASS -> PASS
    # ---------------------------------------------------------

    if (
        previous_access_type == "PASS"
        and target_access_type == "PASS"
    ):
        travel_time = get_travel_time(
            db=db,
            from_room_id=previous_room_id,
            to_room_id=target_room_id,
        )

        if travel_time is None:
            return None

        return {
            "total_time": travel_time,
            "travel_time": travel_time,
            "key_time": 0,
        }

    # ---------------------------------------------------------
    # 4. PASS -> KEY
    #
    # Аудитория 1
    #     ↓
    # Охрана
    #     ↓
    # получение ключа
    #     ↓
    # Аудитория 2
    # ---------------------------------------------------------

    if (
        previous_access_type == "PASS"
        and target_access_type == "KEY"
    ):
        to_desk_time = get_room_to_access_point_time(
            db=db,
            room_id=previous_room_id,
            access_point_id=KEY_DESK_ID,
        )

        from_desk_time = get_access_point_to_room_time(
            db=db,
            access_point_id=KEY_DESK_ID,
            room_id=target_room_id,
        )

        if to_desk_time is None or from_desk_time is None:
            return None

        key_time = KEY_PICKUP_TIME

        total_time = (
            to_desk_time
            + key_time
            + from_desk_time
        )

        return {
            "total_time": total_time,
            "travel_time": to_desk_time + from_desk_time,
            "key_time": key_time,
        }

    # ---------------------------------------------------------
    # 5. KEY -> PASS
    #
    # Аудитория 1
    #     ↓
    # Охрана
    #     ↓
    # возврат ключа
    #     ↓
    # Аудитория 2
    # ---------------------------------------------------------

    if (
        previous_access_type == "KEY"
        and target_access_type == "PASS"
    ):
        to_desk_time = get_room_to_access_point_time(
            db=db,
            room_id=previous_room_id,
            access_point_id=KEY_DESK_ID,
        )

        from_desk_time = get_access_point_to_room_time(
            db=db,
            access_point_id=KEY_DESK_ID,
            room_id=target_room_id,
        )

        if to_desk_time is None or from_desk_time is None:
            return None

        key_time = KEY_RETURN_TIME

        total_time = (
            to_desk_time
            + key_time
            + from_desk_time
        )

        return {
            "total_time": total_time,
            "travel_time": to_desk_time + from_desk_time,
            "key_time": key_time,
        }

    # ---------------------------------------------------------
    # 6. KEY -> KEY
    #
    # Аудитория 1
    #     ↓
    # Охрана
    #     ↓
    # возврат первого ключа
    #     ↓
    # получение второго ключа
    #     ↓
    # Аудитория 2
    # ---------------------------------------------------------

    if (
        previous_access_type == "KEY"
        and target_access_type == "KEY"
    ):
        to_desk_time = get_room_to_access_point_time(
            db=db,
            room_id=previous_room_id,
            access_point_id=KEY_DESK_ID,
        )

        from_desk_time = get_access_point_to_room_time(
            db=db,
            access_point_id=KEY_DESK_ID,
            room_id=target_room_id,
        )

        if to_desk_time is None or from_desk_time is None:
            return None

        key_time = (
            KEY_RETURN_TIME
            + KEY_PICKUP_TIME
        )

        total_time = (
            to_desk_time
            + key_time
            + from_desk_time
        )

        return {
            "total_time": total_time,
            "travel_time": to_desk_time + from_desk_time,
            "key_time": key_time,
        }

    return None