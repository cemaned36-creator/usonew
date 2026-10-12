from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.room import Room
from app.services.optimizer import recommend_room
from app.services.access import calculate_transition_time
from app.services.distance import (
    get_travel_time,
    get_room_to_access_point_time,
    get_access_point_to_room_time,
)


router = APIRouter(
    prefix="/lessons",
    tags=["Recommendations"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{lesson_id}/recommend-room")
def get_recommendation(
    lesson_id: int,
    previous_room_id: int | None = None,
    available_transition_minutes: int | None = None,
    db: Session = Depends(get_db)
):

    previous_access_type = None

    # Если указана предыдущая аудитория,
    # определяем её тип доступа
    if previous_room_id is not None:

        previous_room = (
            db.query(Room)
            .filter(Room.id == previous_room_id)
            .first()
        )

        if not previous_room:
            raise HTTPException(
                status_code=404,
                detail=f"Аудитория {previous_room_id} не найдена"
            )

        previous_access_type = (
            previous_room.access_type
        )
    # ==========================================
    # ВРЕМЕННАЯ ПРОВЕРКА МАРШРУТОВ
    # ==========================================

    print(
        "4 -> охрана:",
        get_room_to_access_point_time(
            db=db,
            room_id=4,
            access_point_id=1,
        )
    )

    print(
        "охрана -> 6:",
        get_access_point_to_room_time(
            db=db,
            access_point_id=1,
            room_id=6,
        )
    )

    print(
        "4 -> 6:",
        get_travel_time(
            db=db,
            from_room_id=4,
            to_room_id=6,
        )
    )

    print(
        "PASS -> KEY (102 -> 104):",
        calculate_transition_time(
            db=db,
            previous_room_id=2,
            previous_access_type="PASS",
            target_room_id=4,
            target_access_type="KEY",
        )
)
    # ==========================================
    # РЕКОМЕНДАЦИЯ АУДИТОРИИ
    # ==========================================

    result = recommend_room(
        db=db,
        lesson_id=lesson_id,
        previous_room_id=previous_room_id,
        previous_access_type=previous_access_type,
        available_transition_minutes=available_transition_minutes,
    )

    return result   