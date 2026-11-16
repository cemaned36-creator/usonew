"""Calculation caches must never survive a preview or cache occupancy."""
import unittest
from contextlib import nullcontext
from unittest.mock import patch
from sqlalchemy import event
import test_teacher_conditions as fixture
from app.models import Teacher, RoomConnection
from app.services.optimization import preview_optimization
from app.services.teacher_conditions import entrance_distances
from app.services.calculation_cache import calculation_cache


class CalculationCacheTest(unittest.TestCase):
    def setUp(self):
        fixture.ConditionsTest.setUp(self)

    def tearDown(self):
        fixture.ConditionsTest.tearDown(self)

    def test_identical_preview_with_fewer_queries_and_one_route_load(self):
        statements = []
        def count(conn, cursor, statement, parameters, context, many):
            statements.append(statement)
        event.listen(self.engine, 'before_cursor_execute', count)
        try:
            with patch('app.services.optimization.calculation_cache', lambda db: nullcontext()):
                baseline = preview_optimization(self.db, 'odd')
            baseline_count = len(statements)
            statements.clear()
            cached = preview_optimization(self.db, 'odd')
            self.assertEqual(cached, baseline)
            self.assertLess(len(statements), baseline_count)
            self.assertEqual(sum('FROM room_connections' in s for s in statements), 1)
            self.assertNotIn('_optimization_calculation_cache', self.db.info)
        finally:
            event.remove(self.engine, 'before_cursor_execute', count)

    def test_next_preview_reads_updated_teacher_conditions(self):
        self.assertEqual(preview_optimization(self.db, 'odd')['changes'], [])
        self.db.get(Teacher, 1).max_floor = 1
        self.db.commit()
        changed = preview_optimization(self.db, 'odd')
        self.assertTrue(changed['can_apply'])
        self.assertEqual(changed['changes'][0]['new_room_id'], 1)
        self.assertEqual(preview_optimization(self.db, 'even')['changes'][0]['new_room_id'], 1)

    def test_distances_refreshed_after_exception_and_nested_calculation(self):
        with self.assertRaisesRegex(ValueError, 'failed'):
            with calculation_cache(self.db):
                self.assertEqual(entrance_distances(self.db)[1], 3)
                with calculation_cache(self.db):
                    self.assertEqual(entrance_distances(self.db)[1], 3)
                raise ValueError('failed')
        self.assertNotIn('_optimization_calculation_cache', self.db.info)
        edge = self.db.query(RoomConnection).filter_by(from_access_point_id=2, to_room_id=1).one()
        edge.travel_time = 0
        self.db.commit()
        with calculation_cache(self.db):
            self.assertEqual(entrance_distances(self.db)[1], 0)
