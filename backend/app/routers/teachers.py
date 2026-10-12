from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.teacher import Teacher

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.get("/")
def get_teachers(db: Session = Depends(get_db)):
    return db.query(Teacher).order_by(Teacher.id).all()