from sqlalchemy.orm import Session

from app.models.lesson_group import LessonGroup
from app.models.student_group import StudentGroup


def calculate_participant_count(
    students_count: int,
    subgroup_number: int,
) -> int:
    """Demo rule: split a group into two nearly equal subgroups."""
    if students_count <= 0:
        raise ValueError("Group size must be positive")

    if subgroup_number == 0:
        return students_count

    if subgroup_number == 1:
        return (students_count + 1) // 2

    if subgroup_number == 2:
        count = students_count // 2
        if count == 0:
            raise ValueError("Second subgroup would be empty")
        return count

    raise ValueError(f"Unsupported subgroup number: {subgroup_number}")


def load_lesson_participants(
    db: Session,
    lesson_ids: list[int],
) -> dict[int, list[dict]]:
    """Load participants for multiple lessons in one query."""
    ids = set(lesson_ids)
    if not ids:
        return {}

    result = {lesson_id: [] for lesson_id in ids}

    rows = (
        db.query(LessonGroup, StudentGroup)
        .join(StudentGroup, StudentGroup.id == LessonGroup.group_id)
        .filter(LessonGroup.lesson_id.in_(ids))
        .all()
    )

    for link, group in rows:
        result[link.lesson_id].append({
            "group_id": group.id,
            "group_name": group.name,
            "subgroup_number": link.subgroup_number,
            "students_count": calculate_participant_count(
                group.students_count,
                link.subgroup_number,
            ),
        })

    missing = sorted(
        lesson_id
        for lesson_id, participants in result.items()
        if not participants
    )
    if missing:
        raise ValueError(f"Lessons without participants: {missing}")

    for participants in result.values():
        participants.sort(key=lambda item: item["group_id"])

    return result


def get_lesson_students_count(participants: list[dict]) -> int:
    if not participants:
        raise ValueError("Lesson has no participants")

    return sum(item["students_count"] for item in participants)


def participants_overlap(
    first: list[dict],
    second: list[dict],
) -> bool:
    """Whether two lessons share students, regardless of their times."""
    if not first or not second:
        raise ValueError("Cannot check overlap without participants")

    for left in first:
        for right in second:
            if left["group_id"] != right["group_id"]:
                continue

            if (
                left["subgroup_number"] == 0
                or right["subgroup_number"] == 0
                or left["subgroup_number"] == right["subgroup_number"]
            ):
                return True

    return False