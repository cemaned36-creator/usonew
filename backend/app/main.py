from fastapi import FastAPI

from app.database import engine, Base

from app.models.teacher import Teacher
from app.models.subject import Subject
from app.models.student_group import StudentGroup
from app.models.room import Room
from app.models.lesson import Lesson
from app.models.lesson_requirement import LessonRequirement
from app.models.schedule_entry import ScheduleEntry
from app.models.room_connection import RoomConnection

from app.routers.schedule import router as schedule_router
from app.routers.recommendation import router as recommendation_router
from app.routers.dashboard import router as dashboard_router
from app.routers.rooms import router as rooms_router
from app.routers.teachers import router as teachers_router
from app.routers.subjects import router as subjects_router
from app.routers.student_groups import router as student_groups_router
from app.routers.lessons import router as lessons_router

from fastapi.middleware.cors import CORSMiddleware

from app.routers.weekly_schedule import router as weekly_schedule_router
from app.models.weekly_schedule_entry import WeeklyScheduleEntry


app = FastAPI(
    title="University Schedule Optimizer",
    description="API для оптимизации расписания",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://usonew-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    recommendation_router
)
app.include_router(dashboard_router)

app.include_router(schedule_router)

app.include_router(weekly_schedule_router)

app.include_router(rooms_router)

app.include_router(teachers_router)

app.include_router(subjects_router)

app.include_router(student_groups_router)

app.include_router(lessons_router)

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {
        "message": "USO API",
        "status": "running",
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }

@app.get("/db-test")
def db_test():
    try:
        with engine.connect():
            return {
                "status": "connected",
                "database": "university_schedule",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }
