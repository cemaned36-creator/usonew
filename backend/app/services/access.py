
from sqlalchemy.orm import Session
from app.models.room import Room
from app.services.key_desks import room_key_desk_id

from app.services.distance import (
    get_travel_time,
    get_room_to_access_point_time,
    get_access_point_to_room_time,
)

# Время получения и возврата ключей, минуты
KEY_PICKUP_TIME = 5
KEY_RETURN_TIME = 5

# Типы доступа без получения ключа
NO_KEY_ACCESS_TYPES = {"OPEN", "PASS"}


def _get_key_desk_id(db: Session, room_id: int) -> int | None:
    return room_key_desk_id(db, db.get(Room, room_id))



def calculate_transition_time(
    db: Session,
    previous_room_id: int | None,
    previous_access_type: str | None,
    target_room_id: int,
    target_access_type: str,
):
    """
    Рассчитывает полное время перехода между аудиториями.

    OPEN — свободный вход.
    PASS — вход по пропуску.
    KEY — требуется получение/возврат ключа.

    Возвращает словарь с total_time, travel_time и key_time.
    Если маршрут не найден, возвращает None.
    """

    # Проверяем тип доступа целевой аудитории
    if target_access_type not in {"OPEN", "PASS", "KEY"}:
        return None

    if (
        previous_access_type is not None
        and previous_access_type not in {"OPEN", "PASS", "KEY"}
    ):
        return None

    target_key_desk_id = None
    previous_key_desk_id = None

    if target_access_type == "KEY":
        target_key_desk_id = _get_key_desk_id(db, target_room_id)
        if target_key_desk_id is None:
            return None

    if previous_room_id is not None and previous_access_type == "KEY":
        previous_key_desk_id = _get_key_desk_id(db, previous_room_id)
        if previous_key_desk_id is None:
            return None


    # Первое занятие: перехода из предыдущей аудитории нет
    if previous_room_id is None:
        if target_access_type in NO_KEY_ACCESS_TYPES:
            return {
                "total_time": 0,
                "travel_time": 0,
                "key_time": 0,
            }

        travel_time = get_access_point_to_room_time(
            db=db,
            access_point_id=target_key_desk_id,
            room_id=target_room_id,
        )

        if travel_time is None:
            return None

        return {
            "total_time": travel_time + KEY_PICKUP_TIME,
            "travel_time": travel_time,
            "key_time": KEY_PICKUP_TIME,
        }

    # Если аудитория та же, перемещение не требуется
    if previous_room_id == target_room_id:
        return {
            "total_time": 0,
            "travel_time": 0,
            "key_time": 0,
        }

    # OPEN/PASS -> OPEN/PASS: идём напрямую
    if (
        previous_access_type in NO_KEY_ACCESS_TYPES
        and target_access_type in NO_KEY_ACCESS_TYPES
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

    # OPEN/PASS -> KEY: идём к охране, берём ключ, идём в аудиторию
    if (
        previous_access_type in NO_KEY_ACCESS_TYPES
        and target_access_type == "KEY"
    ):
        to_desk_time = get_room_to_access_point_time(
            db=db,
            room_id=previous_room_id,
            access_point_id=target_key_desk_id,
        )

        from_desk_time = get_access_point_to_room_time(
            db=db,
            access_point_id=target_key_desk_id,
            room_id=target_room_id,
        )

        if to_desk_time is None or from_desk_time is None:
            return None

        travel_time = to_desk_time + from_desk_time
        key_time = KEY_PICKUP_TIME

        return {
            "total_time": travel_time + key_time,
            "travel_time": travel_time,
            "key_time": key_time,
        }

    # KEY -> OPEN/PASS: возвращаем ключ и идём в аудиторию
    if (
        previous_access_type == "KEY"
        and target_access_type in NO_KEY_ACCESS_TYPES
    ):
        to_desk_time = get_room_to_access_point_time(
            db=db,
            room_id=previous_room_id,
            access_point_id=previous_key_desk_id,
        )

        from_desk_time = get_access_point_to_room_time(
            db=db,
            access_point_id=previous_key_desk_id,
            room_id=target_room_id,
        )

        if to_desk_time is None or from_desk_time is None:
            return None

        travel_time = to_desk_time + from_desk_time
        key_time = KEY_RETURN_TIME

        return {
            "total_time": travel_time + key_time,
            "travel_time": travel_time,
            "key_time": key_time,
        }

    # KEY -> KEY: возвращаем первый ключ и получаем второй
    if (
        previous_access_type == "KEY"
        and target_access_type == "KEY"
    ):
        if previous_key_desk_id != target_key_desk_id:
        # Переход между разными вахтами пока не поддерживается.
            return None

        to_desk_time = get_room_to_access_point_time(
            db=db,
            room_id=previous_room_id,
            access_point_id=previous_key_desk_id,
        )

        from_desk_time = get_access_point_to_room_time(
            db=db,
            access_point_id=target_key_desk_id,
            room_id=target_room_id,
        )

        if to_desk_time is None or from_desk_time is None:
            return None

        travel_time = to_desk_time + from_desk_time
        key_time = KEY_RETURN_TIME + KEY_PICKUP_TIME

        return {
            "total_time": travel_time + key_time,
            "travel_time": travel_time,
            "key_time": key_time,
        }

    return None
