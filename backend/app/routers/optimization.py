from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.optimization import preview_optimization


router = APIRouter(
    prefix="/optimization",
    tags=["Optimization"],
)


@router.get("/preview")
def optimization_preview(
    db: Session = Depends(get_db),
):
    try:
        return preview_optimization(db)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка предварительной оптимизации: {str(e)}",
        ) from e