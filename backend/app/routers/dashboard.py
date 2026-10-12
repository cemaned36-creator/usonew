from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.dashboard import get_dashboard_data


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("")
def dashboard(
    db: Session = Depends(get_db),
):
    """
    Возвращает полную информацию
    для Dashboard.
    """

    return get_dashboard_data(
        db=db,
        target_date=date.today(),
    )