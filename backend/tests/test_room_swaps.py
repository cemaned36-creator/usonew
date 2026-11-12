"""Tests for full-week exchanges of already occupied rooms.

Run with: DATABASE_URL=sqlite:// python -m unittest discover -s tests
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite://")

import unittest
from datetime import time

from fastapi import HTTPException

from test_teacher_conditions import ConditionsTest
from app.models import (
    Lesson, LessonGroup, LessonRequirement, Room, RoomConnection,
    Teacher, WeeklyScheduleEntry,
)
from app.services.optimization import preview_optimization
from app.routers.optimization import OptimizationApplyRequest, apply_optimization
from app.services.weekly_validation import validate_weekly_entries


class OccupiedRoomSwapTest(unittest.TestCase):
    def setUp(self):
        ConditionsTest.setUp(self)
        self.db.get(WeeklyScheduleEntry, 1).room_id = 1
        self.db.get(WeeklyScheduleEntry, 2).room_id = 1
        self.db.get(Room, 3).capacity = 5
        self.db.get(Teacher, 1).preferred_rooms_by_type = {"Лекция": [2]}
        self.db.get(Teacher, 2).preferred_rooms_by_type = {"Лекция": [1]}
        self.db.add(Lesson(
            id=2, teacher_id=2, subject_id=1, group_id=2,
            odd_pairs=1, even_pairs=0, lesson_type="Лекция",
        ))
        self.db.flush()
        self.db.add_all([
            LessonGroup(lesson_id=2, group_id=2, subgroup_number=0),
            LessonRequirement(lesson_id=2, min_capacity=20),
            WeeklyScheduleEntry(
                id=3, lesson_id=2, weekday=0, week_type="odd",
                room_id=2, start_time=time(8, 30), end_time=time(10, 5),
            ),
        ])
        self.db.commit()

    def tearDown(self):
        ConditionsTest.tearDown(self)

    def payload(self, preview, *, teacher_id=None):
        keys = (
            "entry_id", "old_room_id", "new_room_id",
            "old_start_time", "old_end_time", "new_start_time", "new_end_time",
        )
        return OptimizationApplyRequest(
            week_type="odd", teacher_id=teacher_id,
            changes=[{key: change[key] for key in keys} for change in preview["changes"]],
        )

    def test_full_week_can_swap_two_occupied_rooms_and_apply_atomically(self):
        initial = [(e.id, e.room_id) for e in self.db.query(WeeklyScheduleEntry)]
        preview = preview_optimization(self.db, "odd")
        self.assertTrue(preview["can_apply"])
        self.assertEqual(preview["room_swaps_count"], 1)
        self.assertEqual(
            {(c["entry_id"], c["new_room_id"]) for c in preview["changes"]},
            {(1, 2), (3, 1)},
        )
        self.assertEqual(initial, [(e.id, e.room_id) for e in self.db.query(WeeklyScheduleEntry)])
        result = apply_optimization(self.payload(preview), self.db)
        self.assertTrue(result["saved_to_database"])
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 2)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 3).room_id, 1)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 2).room_id, 1)
        validate_weekly_entries(
            self.db, self.db.query(WeeklyScheduleEntry).filter_by(week_type="odd").all(),
        )

    def test_individual_teacher_does_not_change_occupied_other_room(self):
        preview = preview_optimization(self.db, "odd", teacher_id=1)
        self.assertTrue(preview["can_apply"])
        self.assertEqual(preview["changes"], [])
        self.assertEqual(preview["room_swaps_count"], 0)

    def test_swaps_reject_capacity_mismatch(self):
        self.db.get(Room, 2).capacity = 50
        self.db.get(LessonRequirement, 2).min_capacity = 40
        self.db.commit()
        preview = preview_optimization(self.db, "odd")
        self.assertTrue(preview["can_apply"])
        self.assertEqual(preview["room_swaps_count"], 0)
        self.assertEqual(preview["changes"], [])

    def test_swaps_reject_missing_required_equipment(self):
        self.db.get(Room, 2).has_projector = True
        self.db.get(LessonRequirement, 2).projector_required = True
        self.db.commit()
        preview = preview_optimization(self.db, "odd")
        self.assertTrue(preview["can_apply"])
        self.assertEqual(preview["room_swaps_count"], 0)
        self.assertEqual(preview["changes"], [])

    def test_swaps_reject_insufficient_transition_for_either_teacher(self):
        # Teacher 1's next class must remain in lab 1; a switch to room 2
        # makes their intervening transition take 20 minutes (only 10 available).
        self.db.get(Room, 1).room_type = "laboratory"
        edge = self.db.query(RoomConnection).filter_by(
            from_room_id=2, to_room_id=1,
        ).one()
        edge.travel_time = 20
        self.db.add(Lesson(
            id=3, teacher_id=1, subject_id=1, group_id=1,
            odd_pairs=1, even_pairs=0, lesson_type="Лабораторная",
        ))
        self.db.flush()
        self.db.add_all([
            LessonGroup(lesson_id=3, group_id=1, subgroup_number=0),
            LessonRequirement(lesson_id=3, min_capacity=20, room_type="laboratory"),
            WeeklyScheduleEntry(
                id=4, lesson_id=3, weekday=0, week_type="odd",
                room_id=1, start_time=time(10, 15), end_time=time(11, 50),
            ),
        ])
        self.db.commit()
        preview = preview_optimization(self.db, "odd")
        self.assertTrue(preview["can_apply"])
        self.assertEqual(preview["room_swaps_count"], 0)
        self.assertEqual(preview["changes"], [])

    def test_cannot_apply_only_one_side_of_swap(self):
        preview = preview_optimization(self.db, "odd")
        payload = self.payload(preview)
        payload.changes = payload.changes[:1]
        with self.assertRaises(HTTPException):
            apply_optimization(payload, self.db)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 1)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 3).room_id, 2)


if __name__ == "__main__":
    unittest.main()
