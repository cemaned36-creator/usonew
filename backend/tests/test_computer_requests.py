from datetime import datetime, timedelta, timezone
import unittest
from fastapi import HTTPException
import test_teacher_conditions as fixtures
from app.routers import room_requests as r
from app.routers.weekly_schedule import get_weekly_schedule
from app.models import Room, WeeklyScheduleEntry, Lesson, LessonGroup
from app.services.dashboard import get_daily_schedule, get_academic_week

class RequestTest(unittest.TestCase):
    setUp = fixtures.ConditionsTest.setUp
    tearDown = fixtures.ConditionsTest.tearDown

    def test_fifo_one_occurrence_report_and_close(self):
        day = datetime.now(r.ZONE).date() + timedelta(days=7)
        day += timedelta(days=(-day.weekday())%7)
        week = get_academic_week(day)['week_type']
        entry = self.db.query(WeeklyScheduleEntry).filter_by(week_type=week).one()
        self.db.get(Room,1).has_computers = True
        self.db.add(Lesson(id=2,teacher_id=2,group_id=2,subject_id=1))
        self.db.flush()
        self.db.add_all([LessonGroup(lesson_id=2,group_id=2,subgroup_number=0),
                         WeeklyScheduleEntry(id=3,lesson_id=2,week_type=week,weekday=0,room_id=2,start_time=entry.start_time,end_time=entry.end_time)])
        self.db.commit()
        first = r.Submission(teacher_id=1,entry_id=entry.id,day=day)
        r.submit(first,self.db)
        with self.assertRaises(HTTPException):r.submit(first,self.db)
        r.submit(r.Submission(teacher_id=2,entry_id=3,day=day),self.db)
        self.assertEqual(r.due(self.db)['processed'],0)
        r.configure(r.Deadline(deadline=datetime.now(timezone.utc)+timedelta(days=1)),self.db)
        r.settings(self.db).deadline=datetime.now(timezone.utc)-timedelta(minutes=1)
        self.db.commit()
        result=r.due(self.db)
        self.assertEqual(result['processed'],2)
        self.assertEqual([row['status'] for row in r.queue(None,self.db)['rows']],['assigned','rejected'])
        self.assertTrue(r.queue(None,self.db)['closed'])
        self.assertEqual(r.manual(self.db)['processed'],0)
        self.assertEqual(get_daily_schedule(self.db,day,1)['schedule'][0]['room'],'1')
        self.assertEqual(get_daily_schedule(self.db,day+timedelta(days=14),1)['schedule'][0]['room'],'3')
        self.assertEqual(next(x for x in get_weekly_schedule(week,self.db,day) if x['id']==entry.id)['room_id'],1)
        self.assertEqual(entry.room_id,3)
        r.hide(self.db)
        self.assertFalse(r.queue(None,self.db)['rows'])
        self.assertTrue(r.pdf(result['report_id'],self.db).body.startswith(b'%PDF'))
