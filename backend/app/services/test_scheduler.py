from datetime import date, time, timedelta, datetime

from app.database import SessionLocal

from app.models.lesson import Lesson
from app.models.schedule_entry import ScheduleEntry
from app.models.room import Room

from app.services.optimizer import recommend_room
from app.services.conflict_checker import check_conflicts
from app.services.schedule_utils import get_previous_entry


LESSON_DURATION = 90


def test_schedule():

    db = SessionLocal()

    try:

        # очищаем старое тестовое расписание
        db.query(ScheduleEntry).delete()
        db.commit()


        today = date.today()


        # Берем два занятия
        lessons = (
            db.query(Lesson)
            .filter(
                Lesson.id.in_([1, 2])
            )
            .order_by(Lesson.id)
            .all()
        )


        if len(lessons) < 2:
            print(
                "Недостаточно занятий"
            )
            return


        # -------------------------
        # Первое занятие
        # -------------------------

        first = ScheduleEntry(
            lesson_id=lessons[0].id,
            room_id=2,
            date=today,
            start_time=time(8,30),
            end_time=time(10,0)
        )

        db.add(first)
        db.commit()


        print(
            "Создано первое занятие:"
        )

        print(
            "08:30-10:00 "
            "аудитория 2 PASS"
        )


        # -------------------------
        # Второе занятие
        # -------------------------

        previous_room_id = 2

        previous_access_type = "PASS"


        available_time = 10

        print(
            "Доступное время перехода:",
            available_time
        )

        result = recommend_room(
            db=db,
            lesson_id=lessons[1].id,

            previous_room_id=
                previous_room_id,

            previous_access_type=
                previous_access_type,

            available_transition_minutes=
                available_time
        )


        print()
        print(
            "Результат подбора:"
        )

        print(result)


    finally:

        db.close()



if __name__ == "__main__":
    test_schedule()