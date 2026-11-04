"""History persistence and guarded restores; no live database access."""
import unittest
from datetime import time
from unittest.mock import patch
from fastapi import HTTPException
import test_teacher_conditions as fixture
from app.models import Teacher, WeeklyScheduleEntry, OptimizationRun, Lesson, LessonGroup, LessonRequirement
from app.routers.optimization import (apply_optimization, OptimizationApplyRequest,
    optimization_history, restore_preview, restore_optimization)
from app.services.optimization import preview_optimization
from app.services.optimization_history import prepare_restore


class HistoryTest(unittest.TestCase):
    setUp = fixture.ConditionsTest.setUp
    tearDown = fixture.ConditionsTest.tearDown

    def payload(self):
        self.db.get(Teacher, 1).prefer_near_entrance = True
        self.db.get(WeeklyScheduleEntry, 1).room_id = 1
        self.db.commit()
        preview = preview_optimization(self.db, 'odd', 1)
        self.assertTrue(preview['can_apply'])
        self.assertEqual(len(preview['changes']), 1)
        return OptimizationApplyRequest(week_type='odd', teacher_id=1, changes=preview['changes'])

    def apply(self):
        return apply_optimization(self.payload(), self.db)['history_id']

    def test_history_created_with_assignments_and_scoped_list(self):
        run_id = self.apply()
        run = self.db.get(OptimizationRun, run_id)
        self.assertEqual(run.before_entries[0]['room_id'], 1)
        self.assertEqual(run.after_entries[0]['room_id'], 3)
        self.assertEqual(run.before_entries[0]['start_time'], '08:30:00')
        self.assertEqual(optimization_history('odd', 1, 0, 10, self.db)['items'][0]['id'], run_id)
        self.assertEqual(optimization_history('odd', 2, 0, 10, self.db)['items'], [])
        self.assertEqual(optimization_history('even', 1, 0, 10, self.db)['items'], [])

    def test_preview_read_only_restore_preserves_other_week_and_marks_history(self):
        run_id = self.apply()
        self.assertTrue(restore_preview(run_id, 'odd', 1, self.db)['can_restore'])
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 3)
        result = restore_optimization(run_id, 'odd', 1, self.db)
        self.assertEqual(result['restored_count'], 1)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 1)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 2).room_id, 3)
        self.assertIsNotNone(self.db.get(OptimizationRun, run_id).restored_at)
        with self.assertRaises(HTTPException) as error:
            restore_optimization(run_id, 'odd', 1, self.db)
        self.assertEqual(error.exception.status_code, 409)

    def test_later_edit_is_not_overwritten(self):
        run_id = self.apply()
        self.db.get(WeeklyScheduleEntry, 1).room_id = 2
        self.db.commit()
        with self.assertRaises(HTTPException):
            restore_optimization(run_id, 'odd', 1, self.db)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 2)
        self.assertIsNone(self.db.get(OptimizationRun, run_id).restored_at)

    def test_deleted_entry_is_not_recreated(self):
        run_id = self.apply()
        self.db.delete(self.db.get(WeeklyScheduleEntry, 1)); self.db.commit()
        with self.assertRaises(HTTPException):
            restore_optimization(run_id, 'odd', 1, self.db)
        self.assertIsNone(self.db.get(WeeklyScheduleEntry, 1))

    def test_wrong_teacher_and_week_rejected(self):
        run_id = self.apply()
        for week, teacher in [('even', 1), ('odd', 2)]:
            with self.assertRaises(HTTPException):
                restore_optimization(run_id, week, teacher, self.db)
        self.assertIsNone(self.db.get(OptimizationRun, run_id).restored_at)

    def test_old_invalid_condition_is_not_restored(self):
        self.db.get(Teacher, 1).max_floor = 1
        self.db.commit()
        preview = preview_optimization(self.db, 'odd', 1)
        run_id = apply_optimization(OptimizationApplyRequest(week_type='odd', teacher_id=1,
            changes=preview['changes']), self.db)['history_id']
        with self.assertRaises(HTTPException) as error:
            restore_optimization(run_id, 'odd', 1, self.db)
        self.assertIn('текущим условиям', error.exception.detail)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 1)

    def test_validation_failure_leaves_history_and_schedule_unchanged(self):
        run_id = self.apply()
        with patch('app.services.optimization_history.validate_weekly_entries', side_effect=ValueError('конфликт')):
            with self.assertRaises(HTTPException):
                restore_optimization(run_id, 'odd', 1, self.db)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 3)
        self.assertIsNone(self.db.get(OptimizationRun, run_id).restored_at)

    def test_history_failure_rolls_back_apply(self):
        payload = self.payload()
        with patch('app.routers.optimization.record_run', side_effect=RuntimeError('history write failed')):
            with self.assertRaises(HTTPException):
                apply_optimization(payload, self.db)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 1)
        self.assertEqual(self.db.query(OptimizationRun).count(), 0)

    def test_new_room_conflict_blocks_restore(self):
        run_id = self.apply()
        self.db.add(Lesson(id=2, teacher_id=2, subject_id=1, group_id=2))
        self.db.flush()
        self.db.add_all([LessonGroup(lesson_id=2, group_id=2, subgroup_number=0),
            LessonRequirement(lesson_id=2, min_capacity=20),
            WeeklyScheduleEntry(id=3, lesson_id=2, weekday=0, week_type='odd',
                room_id=1, start_time=time(8,30), end_time=time(10,5))])
        self.db.commit()
        with self.assertRaises(HTTPException) as error:
            restore_optimization(run_id, 'odd', 1, self.db)
        self.assertIn('Прежний вариант', error.exception.detail)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 3)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 3).room_id, 1)

    def test_restore_original_time_after_condition_is_relaxed(self):
        self.db.get(Teacher, 1).earliest_start_pair = 3
        self.db.commit()
        preview = preview_optimization(self.db, 'odd', 1)
        run_id = apply_optimization(OptimizationApplyRequest(week_type='odd', teacher_id=1,
            changes=preview['changes']), self.db)['history_id']
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).start_time, time(12))
        self.db.get(Teacher, 1).earliest_start_pair = 1
        self.db.commit()
        restore_optimization(run_id, 'odd', 1, self.db)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).start_time, time(8,30))
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 3)

    def test_restore_commit_failure_rolls_back_both(self):
        run_id = self.apply()
        with patch.object(self.db, 'commit', side_effect=RuntimeError('write failed')):
            with self.assertRaises(HTTPException):
                restore_optimization(run_id, 'odd', 1, self.db)
        self.assertEqual(self.db.get(WeeklyScheduleEntry, 1).room_id, 3)
        self.assertIsNone(self.db.get(OptimizationRun, run_id).restored_at)


if __name__ == '__main__':
    unittest.main()
