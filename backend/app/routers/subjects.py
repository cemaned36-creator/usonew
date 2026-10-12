from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.subject import Subject

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get("/")
def get_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).order_by(Subject.id).all()