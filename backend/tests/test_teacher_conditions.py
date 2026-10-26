"""Run with: DATABASE_URL=sqlite:// python -m unittest discover -s tests."""
import os
os.environ.setdefault('DATABASE_URL', 'sqlite://')
import unittest
from datetime import time
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException
from pydantic import ValidationError
from app.database import Base
from app.models import (Teacher, Room, Lesson, Subject, StudentGroup,
    LessonGroup, LessonRequirement, WeeklyScheduleEntry, AccessPoint,
    RoomConnection, TeachingLoad, LessonTeachingLoad)
from app.services.optimization import preview_optimization
from app.services.weekly_validation import validate_weekly_entries
from app.services.weekly_generator import generate_weekly_preview
from app.services.teacher_conditions import entrance_distances
from app.routers.teachers import update_conditions, TeacherConditions
from app.routers.optimization import apply_optimization, OptimizationApplyRequest


class TestSession(Session):
    def execute(self, statement, *args, **kwargs):
        # SQLite has no PostgreSQL table-lock statements. All application queries
        # and persistence still execute; locks are verified separately on Neon.
        if str(statement).lstrip().startswith(('SET LOCAL', 'LOCK TABLE')):
            return None
        return super().execute(statement, *args, **kwargs)


class ConditionsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.db = TestSession(self.engine, autoflush=False)
        self.db.add_all([Teacher(id=1, name='Teacher'), Teacher(id=2, name='Other'),
                         Subject(id=1, name='Subject'), StudentGroup(id=1, name='Group', students_count=20),
                         StudentGroup(id=2, name='Other group', students_count=20),
                         AccessPoint(id=2, name='Охрана корпуса Б', point_type='KEY_DESK')])
        for i in range(1,4):
            self.db.add(Room(id=i, name=str(i), building='Б', floor=i,
                capacity=30, room_type='classroom', access_type='OPEN'))
            self.db.add(RoomConnection(from_access_point_id=2, to_room_id=i,
                distance={1:100,2:10,3:5}[i], travel_time={1:3,2:2,3:1}[i]))
            for j in range(1,4):
                if i!=j:self.db.add(RoomConnection(from_room_id=i,to_room_id=j,distance=100,travel_time=2))
        self.db.flush()
        self.db.add(Lesson(id=1, teacher_id=1, subject_id=1, group_id=1,
                           odd_pairs=1, even_pairs=1, lesson_type='Лекция'))
        self.db.flush()
        self.db.add_all([LessonGroup(lesson_id=1,group_id=1,subgroup_number=0),
            LessonRequirement(lesson_id=1,min_capacity=20),
            TeachingLoad(id=1,source_row_number=1,teacher_id=1,subject_id=1,group_id=1,
                         lesson_type='Лекция',weeks_label='both',odd_pairs=1,even_pairs=1)])
        self.db.flush()
        self.db.add(LessonTeachingLoad(lesson_id=1,teaching_load_id=1))
        for i,week in enumerate(['odd','even'],1):
            self.db.add(WeeklyScheduleEntry(id=i,lesson_id=1,weekday=0,week_type=week,
                                           room_id=3,start_time=time(8,30),end_time=time(10,5)))
        self.db.commit()

    def tearDown(self):
        self.db.close();self.engine.dispose()

    def conditions(self, **values):
        return update_conditions(1,TeacherConditions(earliest_start_pair=values.get('earliest_start_pair',3),
            max_floor=values.get('max_floor',2),prefer_near_entrance=values.get('prefer_near_entrance',True)),self.db)

    def payload(self, preview):
        keys=['entry_id','old_room_id','new_room_id','old_start_time','old_end_time','new_start_time','new_end_time']
        return OptimizationApplyRequest(week_type='odd',teacher_id=1,
            changes=[{k:c[k] for k in keys} for c in preview['changes']])

    def test_save_preview_apply_and_other_week_preserved(self):
        saved=self.conditions();self.assertEqual(saved['affected_entries'],2)
        self.assertEqual(self.db.get(WeeklyScheduleEntry,1).start_time,time(8,30))
        preview=preview_optimization(self.db,'odd',1)
        self.assertTrue(preview['can_apply']);change=preview['changes'][0]
        self.assertEqual(change['new_start_time'],'12:00');self.assertEqual(change['new_room_id'],2)
        apply_optimization(self.payload(preview),self.db)
        self.assertEqual(self.db.get(WeeklyScheduleEntry,1).start_time,time(12))
        self.assertEqual(self.db.get(WeeklyScheduleEntry,1).room_id,2)
        self.assertEqual(self.db.get(WeeklyScheduleEntry,2).room_id,3)

    def test_stale_and_tampered_plan_rejected(self):
        self.conditions();preview=preview_optimization(self.db,'odd',1)
        payload=self.payload(preview);payload.changes[0].new_start_time='14:30'
        with self.assertRaises(HTTPException):apply_optimization(payload,self.db)
        self.assertEqual(self.db.get(WeeklyScheduleEntry,1).start_time,time(8,30))
        self.conditions(max_floor=1)
        with self.assertRaises(HTTPException):apply_optimization(self.payload(preview),self.db)

    def test_no_suitable_room_blocks_apply(self):
        self.conditions(max_floor=1)
        self.db.get(Room,1).capacity=5;self.db.commit()
        preview=preview_optimization(self.db,'odd',1)
        self.assertFalse(preview['can_apply']);self.assertTrue(preview['constraint_issues'])
        with self.assertRaises(ValueError):generate_weekly_preview(self.db,'odd')

    def test_nearest_room_even_without_transition_saving(self):
        self.conditions(earliest_start_pair=1,max_floor=2)
        self.db.get(WeeklyScheduleEntry,1).room_id=1;self.db.commit()
        preview=preview_optimization(self.db,'odd',1)
        self.assertEqual(preview['time_saved'],0)
        self.assertEqual(preview['changes'][0]['new_room_id'],2)

    def test_generation_both_weeks_and_manual_validation(self):
        self.conditions()
        with self.assertRaises(ValueError):
            validate_weekly_entries(self.db,[self.db.get(WeeklyScheduleEntry,1)])
        for week in ['odd','even']:
            preview=generate_weekly_preview(self.db,week)
            self.assertEqual(preview['status'],'complete')
            self.assertGreaterEqual(preview['entries'][0].start_time,time(12))
            self.assertEqual(preview['entries'][0].room_id,2)

    def test_shared_group_blocks_occupied_time(self):
        self.conditions()
        self.db.add(Lesson(id=2, teacher_id=2, subject_id=1, group_id=2))
        self.db.flush()
        self.db.add_all([LessonGroup(lesson_id=2, group_id=2, subgroup_number=0),
            LessonGroup(lesson_id=2, group_id=1, subgroup_number=0),
            LessonRequirement(lesson_id=2, min_capacity=40),
            WeeklyScheduleEntry(id=3, lesson_id=2, weekday=0, week_type='odd', room_id=1,
                                start_time=time(12), end_time=time(13,35))])
        self.db.get(Room,1).capacity=50
        self.db.commit()
        preview=preview_optimization(self.db,'odd',1)
        self.assertTrue(preview['can_apply'])
        self.assertEqual(preview['changes'][0]['new_start_time'], '14:30')

    def test_reset_restores_unrestricted_defaults(self):
        self.conditions()
        saved=self.conditions(earliest_start_pair=1, max_floor=None, prefer_near_entrance=False)
        self.assertEqual(saved['affected_entries'], 0)
        self.assertIsNone(self.db.get(Teacher,1).max_floor)
        self.assertEqual(self.db.get(WeeklyScheduleEntry,1).start_time,time(8,30))

    def test_strict_request_values(self):
        for values in [{'earliest_start_pair':0},{'earliest_start_pair':4},
                       {'earliest_start_pair':True},{'earliest_start_pair':1,'max_floor':0},
                       {'earliest_start_pair':1,'prefer_near_entrance':'false'}]:
            with self.assertRaises(ValidationError):TeacherConditions(**values)

    def test_conflicting_other_teacher_not_moved(self):
        self.conditions()
        self.db.add(Lesson(id=2,teacher_id=2,subject_id=1,group_id=2))
        self.db.flush()
        self.db.add_all([LessonGroup(lesson_id=2,group_id=2,subgroup_number=0),
            LessonRequirement(lesson_id=2,min_capacity=20),
            WeeklyScheduleEntry(id=3,lesson_id=2,weekday=0,week_type='odd',room_id=2,
                                start_time=time(12),end_time=time(13,35))])
        self.db.commit()
        preview=preview_optimization(self.db,'odd',1)
        self.assertTrue(preview['can_apply'])
        self.assertEqual([c['entry_id'] for c in preview['changes']],[1])
        self.assertNotEqual(preview['changes'][0]['new_room_id'],2)
        self.assertEqual(self.db.get(WeeklyScheduleEntry,3).room_id,2)

if __name__=='__main__':unittest.main()
