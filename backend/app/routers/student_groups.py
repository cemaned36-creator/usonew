from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student_group import StudentGroup

router = APIRouter(
    prefix="/student-groups",
    tags=["Student Groups"]
)


@router.get("/")
def get_student_groups(db: Session = Depends(get_db)):
    return db.query(StudentGroup).order_by(StudentGroup.id).all()