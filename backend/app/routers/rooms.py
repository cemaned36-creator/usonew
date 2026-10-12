from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.room import Room

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("/")
def get_rooms(db: Session = Depends(get_db)):
    rooms = db.query(Room).order_by(Room.name).all()

    return [
        {
            "id": room.id,
            "name": room.name,
            "room_type": room.room_type,
            "access_type": room.access_type,
            "capacity": room.capacity,
        }
        for room in rooms
    ]
