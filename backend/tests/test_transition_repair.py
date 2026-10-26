"""Repair initially infeasible transitions using one or two room assignments."""
import os
os.environ.setdefault('DATABASE_URL', 'sqlite://')
import unittest
from datetime import time
import test_teacher_conditions as fixture
from app.models import Teacher, Lesson, LessonGroup, LessonRequirement, WeeklyScheduleEntry, Room, RoomConnection
from app.services.optimization import preview_optimization
from app.services.weekly_validation import validate_weekly_entries
from app.routers.optimization import apply_optimization, OptimizationApplyRequest
from fastapi import HTTPException


class TransitionRepairTest(unittest.TestCase):
    def setUp(self):
        fixture.ConditionsTest.setUp(self)
        self.db.get(WeeklyScheduleEntry, 1).room_id = 1
        self.db.add(Teacher(id=3, name='Blocker'))
        self.db.flush()
        # A/B cannot exchange rooms: one is occupied during the first slot,
        # the other during the second. Both must move to the free third room.
        for lid, tid, gid in [(2,1,1),(3,3,2),(4,2,2)]:
            self.db.add(Lesson(id=lid,teacher_id=tid,subject_id=1,group_id=gid,
                               odd_pairs=1,even_pairs=0,lesson_type='Лекция'))
            self.db.flush()
            self.db.add_all([LessonGroup(lesson_id=lid,group_id=gid,subgroup_number=0),
                             LessonRequirement(lesson_id=lid,min_capacity=20)])
        self.db.add_all([
            WeeklyScheduleEntry(id=3,lesson_id=2,weekday=0,week_type='odd',room_id=2,start_time=time(10,15),end_time=time(11,50)),
            WeeklyScheduleEntry(id=4,lesson_id=3,weekday=0,week_type='odd',room_id=2,start_time=time(8,30),end_time=time(10,5)),
            WeeklyScheduleEntry(id=5,lesson_id=4,weekday=0,week_type='odd',room_id=1,start_time=time(10,15),end_time=time(11,50)),
        ])
        for edge in self.db.query(RoomConnection):
            edge.travel_time=20
        self.db.commit()

    def tearDown(self):
        fixture.ConditionsTest.tearDown(self)

    def payload(self,preview):
        keys=['entry_id','old_room_id','new_room_id','old_start_time','old_end_time','new_start_time','new_end_time']
        return OptimizationApplyRequest(week_type='odd',teacher_id=1,
            changes=[{k:c[k] for k in keys} for c in preview['changes']])

    def test_joint_repair_preview_apply_and_other_entries_preserved(self):
        original=[(e.id,e.room_id,e.start_time,e.end_time) for e in self.db.query(WeeklyScheduleEntry).order_by(WeeklyScheduleEntry.id)]
        preview=preview_optimization(self.db,'odd',1)
        self.assertTrue(preview['can_apply'])
        self.assertEqual([(c['entry_id'],c['new_room_id']) for c in preview['changes']],[(1,3),(3,3)])
        self.assertEqual(original,[(e.id,e.room_id,e.start_time,e.end_time) for e in self.db.query(WeeklyScheduleEntry).order_by(WeeklyScheduleEntry.id)])
        tampered=self.payload(preview);tampered.changes[0].new_room_id=2
        with self.assertRaises(HTTPException):apply_optimization(tampered,self.db)
        apply_optimization(self.payload(preview),self.db)
        validate_weekly_entries(self.db,self.db.query(WeeklyScheduleEntry).filter_by(week_type='odd').all())
        for eid,rid,start,end in original:
            row=self.db.get(WeeklyScheduleEntry,eid)
            self.assertEqual((row.start_time,row.end_time),(start,end))
            if eid not in (1,3):self.assertEqual(row.room_id,rid)

    def test_single_replacement_preferred(self):
        self.db.delete(self.db.get(WeeklyScheduleEntry,4));self.db.commit()
        preview=preview_optimization(self.db,'odd',1)
        self.assertTrue(preview['can_apply'])
        self.assertEqual(len(preview['changes']),1)
        self.assertEqual(preview['changes'][0]['new_room_id'],2)

    def test_impossible_repair_remains_blocked(self):
        self.db.get(Room,3).capacity=1;self.db.commit()
        preview=preview_optimization(self.db,'odd',1)
        self.assertFalse(preview['can_apply'])
        self.assertEqual(preview['changes'],[])
        with self.assertRaises(HTTPException):apply_optimization(self.payload(preview),self.db)

    def test_teacher_filter_does_not_repair_someone_else(self):
        preview=preview_optimization(self.db,'odd',3)
        self.assertEqual(preview['changes'],[])
        self.assertFalse(preview['can_apply'])  # Full schedule remains invalid.

    def test_disconnected_rooms_can_be_repaired_without_inventing_a_route(self):
        self.db.query(RoomConnection).delete();self.db.commit()
        preview=preview_optimization(self.db,'odd',1)
        self.assertTrue(preview['can_apply'])
        self.assertEqual({c['new_room_id'] for c in preview['changes']},{3})


if __name__=='__main__':unittest.main()
