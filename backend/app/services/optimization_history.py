"""History is committed with assignments; restores validate a complete week."""
from datetime import datetime, timezone, time
from types import SimpleNamespace
from fastapi import HTTPException
from sqlalchemy import text
from app.models.optimization_run import OptimizationRun
from app.models.weekly_schedule_entry import WeeklyScheduleEntry
from app.models.lesson import Lesson
from app.services.weekly_validation import validate_weekly_entries


def snapshot(entry, lessons):
    return dict(id=entry.id, lesson_id=entry.lesson_id,
                teacher_id=lessons[entry.lesson_id].teacher_id,
                week_type=entry.week_type, weekday=entry.weekday, room_id=entry.room_id,
                start_time=entry.start_time.isoformat(), end_time=entry.end_time.isoformat())


def record_run(db, *, week_type, teacher_id, teacher_name, before, after, preview):
    run = OptimizationRun(week_type=week_type, teacher_id=teacher_id,
                          teacher_name=teacher_name, before_entries=before,
                          after_entries=after, metrics={key: preview.get(key) for key in
                          ('transition_time_before', 'transition_time_after', 'time_saved', 'detailed_report', 'warnings', 'constraint_issues', 'can_apply')})
    db.add(run)
    db.flush()  # The caller owns the transaction, including any failure.
    return run


def iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def serialize_run(run):
    return dict(id=run.id, created_at=iso(run.created_at), week_type=run.week_type,
                teacher_id=run.teacher_id, teacher_name=run.teacher_name,
                restored_at=iso(run.restored_at), changes_count=len(run.before_entries),
                metrics=run.metrics, changes=[dict(before=a, after=b) for a, b in
                zip(run.before_entries, run.after_entries)])


def prepare_restore(db, run_id, week_type, teacher_id=None):
    run = db.get(OptimizationRun, run_id)
    if run is None:
        raise HTTPException(404, 'Запись истории не найдена.')
    if run.week_type != week_type or (teacher_id is not None and run.teacher_id != teacher_id):
        raise HTTPException(409, 'Запись истории относится к другой неделе или области оптимизации.')
    if run.restored_at is not None:
        raise HTTPException(409, 'Эта оптимизация уже отменена.')
    current = db.query(WeeklyScheduleEntry).filter(WeeklyScheduleEntry.week_type == run.week_type).all()
    by_id = {entry.id: entry for entry in current}
    lessons = {lesson.id: lesson for lesson in db.query(Lesson).all()}
    before = {entry['id']: entry for entry in run.before_entries}
    after = {entry['id']: entry for entry in run.after_entries}
    if not before or before.keys() != after.keys():
        raise HTTPException(409, 'Снимок истории неполон. Восстановление отменено.')
    for entry_id, saved in after.items():
        entry = by_id.get(entry_id)
        if entry is None or entry.lesson_id not in lessons or snapshot(entry, lessons) != saved:
            raise HTTPException(409, f'Запись #{entry_id} удалена или изменена после оптимизации. Восстановление отменено.')
    proposed = []
    for entry in current:
        values = before.get(entry.id) or snapshot(entry, lessons)
        proposed.append(SimpleNamespace(**{**values,
            'start_time': time.fromisoformat(values['start_time']),
            'end_time': time.fromisoformat(values['end_time'])}))
    try:
        validate_weekly_entries(db, proposed)
    except ValueError as exc:
        raise HTTPException(409, f'Прежний вариант не соответствует текущим условиям: {exc}. Расписание не изменено.') from exc
    return run, by_id, before


def restore_run(db, run_id, week_type, teacher_id=None):
    try:
        # Same lock order as apply: serializes restores with optimizations and manual edits.
        db.execute(text("SET LOCAL lock_timeout = '5s'"))
        db.execute(text('LOCK TABLE weekly_schedule_entries, teachers IN SHARE ROW EXCLUSIVE MODE'))
        db.expire_all()
        run, entries, before = prepare_restore(db, run_id, week_type, teacher_id)
        for entry_id, values in before.items():
            entries[entry_id].room_id = values['room_id']
            entries[entry_id].start_time = time.fromisoformat(values['start_time'])
            entries[entry_id].end_time = time.fromisoformat(values['end_time'])
        run.restored_at = datetime.now(timezone.utc)
        db.commit()
        return dict(status='success', restored_count=len(before), history_id=run_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, 'Не удалось восстановить расписание. Изменения отменены.') from exc
