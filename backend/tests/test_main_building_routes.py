import json
import unittest
from pathlib import Path
import test_teacher_conditions as fixture
from app.models import Room, AccessPoint, RoomConnection
from app.services.access import _get_key_desk_id, calculate_transition_time
from app.services.room_scope import room_in_active_scope
from app.services.teacher_conditions import entrance_distances
from app.services.weekly_generator import generate_weekly_preview
from scripts.build_main_building_routes import build_routes


class MainBuildingTest(unittest.TestCase):
    def setUp(self):fixture.ConditionsTest.setUp(self)
    def tearDown(self):fixture.ConditionsTest.tearDown(self)

    def test_rename_keeps_current_key_desk_and_generation(self):
        self.assertEqual(_get_key_desk_id(self.db,1),2)
        for room in self.db.query(Room):room.building='Главный корпус'
        self.db.get(AccessPoint,2).name='Охрана Главного корпуса'
        self.db.get(Room,1).access_type='KEY';self.db.commit()
        self.assertEqual(_get_key_desk_id(self.db,1),2)
        self.assertTrue(room_in_active_scope(self.db.get(Room,1)))
        self.assertEqual(calculate_transition_time(self.db,None,None,1,'KEY')['key_time'],5)
        for week in ('odd','even'):
            self.assertEqual(generate_weekly_preview(self.db,week)['status'],'complete')

    def test_ambiguous_desk_fails_closed(self):
        self.db.add(AccessPoint(id=3,name='Охрана Главного корпуса',point_type='KEY_DESK'));self.db.commit()
        self.assertIsNone(_get_key_desk_id(self.db,1))
        self.assertEqual(entrance_distances(self.db),{})

    def test_entrance_cost_accounts_for_stair_time_not_horizontal_metres(self):
        self.db.query(RoomConnection).delete()
        self.db.add_all([RoomConnection(from_access_point_id=2,to_room_id=1,distance=1,travel_time=5),
                         RoomConnection(from_access_point_id=2,to_room_id=2,distance=100,travel_time=2)])
        self.db.commit()
        d=entrance_distances(self.db)
        self.assertLess(d[2],d[1])

    def test_graph_has_all_routes_and_required_detour(self):
        g=json.loads((Path(__file__).resolve().parents[1]/'data/main_building_graph.json').read_text())
        rows=build_routes(g)
        self.assertEqual(len(rows),4556)
        by={(r['from_room_id'],r['to_room_id']):r for r in rows}
        self.assertEqual(by[13,15]['travel_time'],6)
        self.assertEqual(by[13,14]['travel_time'],1)
        self.assertEqual(len([e for e in g['edges'] if e['kind']=='stairs']),27)
        for r in rows:
            self.assertEqual(r['travel_time'],by[r['to_room_id'],r['from_room_id']]['travel_time'])
            self.assertGreaterEqual(r['travel_time'],1)


if __name__=='__main__':unittest.main()
