"""One occurrence only. All writers take the same PostgreSQL transaction lock."""
from datetime import date, datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Lesson, LessonRequirement, Room, Teacher, WeeklyScheduleEntry
from app.models.room_request import AllocationReport, Collection, ComputerRequest, overrides
from app.services.dashboard import get_academic_week, get_daily_schedule
from app.services.equipment import load_equipment_profiles, room_has_required_profiles
from app.services.weekly_generator import build_transition_checker
from app.services.room_scope import room_in_active_scope
from app.services.teacher_conditions import room_allowed
from app.services.optimization_pdf import date_label
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

router = APIRouter(prefix="/room-requests", tags=["Computer room requests"])
ZONE = ZoneInfo("Asia/Yekaterinburg")


def lock(db):
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(79501332)"))


def settings(db):
    return db.get(Collection, 1)


def utc(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def describe(row):
    return dict(row.snapshot, id=row.id, entry_id=row.entry_id, status=row.status, reason=row.reason,
                assigned_room=row.assigned_room)


class Submission(BaseModel):
    teacher_id: int
    entry_id: int
    day: date


class Deadline(BaseModel):
    deadline: datetime


@router.get("/options")
def options(day: date, teacher_id: int, db: Session = Depends(get_db)):
    now = datetime.now(ZONE)
    return [e for e in get_daily_schedule(db, day, teacher_id)["schedule"]
            if (day.isoformat(), e["time"]) > (now.date().isoformat(), now.strftime("%H:%M"))]


@router.get("")
def queue(teacher_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(ComputerRequest)
    q = q.filter_by(teacher_id=teacher_id) if teacher_id is not None else q.filter_by(hidden=False)
    conf = settings(db)
    return {"rows": [describe(r) for r in q.order_by(ComputerRequest.id).all()],
            "closed": bool(conf and (conf.closed or (conf.deadline and utc(conf.deadline) <= datetime.now(timezone.utc)))),
            "deadline": conf.deadline if conf else None}


@router.post("")
def submit(payload: Submission, db: Session = Depends(get_db)):
    lock(db)
    conf = settings(db)
    if conf and (conf.closed or (conf.deadline and datetime.now(timezone.utc) >= utc(conf.deadline))):
        raise HTTPException(409, "Сбор завершён")
    row = next((e for e in options(payload.day, payload.teacher_id, db) if e["id"] == payload.entry_id), None)
    if not row:
        raise HTTPException(409, "Выберите предстоящее занятие этого преподавателя")
    if db.query(ComputerRequest).filter_by(day=payload.day, entry_id=payload.entry_id).first():
        raise HTTPException(409, "На это занятие уже подана заявка")
    db.add(ComputerRequest(entry_id=row["id"], lesson_id=row["lesson_id"], teacher_id=payload.teacher_id,
                           day=payload.day, snapshot={**row, "day": payload.day.isoformat()}))
    db.commit()
    return {"ok": True}


@router.put("/settings")
def configure(payload: Deadline, db: Session = Depends(get_db)):
    if not payload.deadline.tzinfo or payload.deadline <= datetime.now(timezone.utc):
        raise HTTPException(422, "Укажите будущие дату и время с часовым поясом")
    lock(db)
    conf = settings(db) or Collection(id=1)
    conf.closed = False
    conf.deadline = payload.deadline.astimezone(timezone.utc)
    db.add(conf)
    db.commit()
    return {"ok": True}


@router.post("/hide")
def hide(db: Session = Depends(get_db)):
    lock(db)
    db.query(ComputerRequest).filter(ComputerRequest.status != "pending").update({"hidden": True})
    db.commit()
    return {"ok": True}


def assign(db, req, rooms, route, profiles):
    day = req.day
    rows = db.query(WeeklyScheduleEntry).filter_by(weekday=day.weekday(), week_type=get_academic_week(day)["week_type"]).all()
    entry = next((e for e in rows if e.id == req.entry_id and e.lesson_id == req.lesson_id), None)
    if not entry or entry.start_time.strftime("%H:%M") != req.snapshot["time"] or entry.end_time.strftime("%H:%M") != req.snapshot["end"]:
        return "Исходное занятие изменилось"
    if datetime.combine(day, entry.start_time, ZONE) <= datetime.now(ZONE):
        return "Занятие уже началось"
    lesson = db.get(Lesson, entry.lesson_id)
    if lesson.teacher_id != req.teacher_id:
        return "Преподаватель изменился"
    overrides_by_id = overrides(db, day, day)
    def rid(e):
        return overrides_by_id.get((day, e.id, e.lesson_id), e.room_id)
    peers = sorted([e for e in rows if db.get(Lesson, e.lesson_id).teacher_id == req.teacher_id], key=lambda e:e.start_time)
    idx = peers.index(entry)
    required = db.query(LessonRequirement).filter_by(lesson_id=lesson.id).first()
    actual = next(e for e in get_daily_schedule(db, day, req.teacher_id)["schedule"] if e["id"] == entry.id)
    req.snapshot = {**actual, "day": day.isoformat()}
    busy = {rid(e) for e in rows if e.id != entry.id and e.start_time < entry.end_time and entry.start_time < e.end_time}
    def fits(a,b,source,target):
        gap = (datetime.combine(day,b.start_time)-datetime.combine(day,a.end_time)).total_seconds()/60
        cost = route(source,target)
        return cost is not None and cost <= gap
    for room in sorted(rooms.values(), key=lambda r:(r.id != rid(entry), r.id)):
        if not (room_in_active_scope(room) and room.has_computers and room.id not in busy
                and room_allowed(room, db.get(Teacher, req.teacher_id))
                and room.capacity >= max(actual["students_count"], required.min_capacity if required else 0)
                and room_has_required_profiles(room.id, lesson.id, *profiles)):
            continue
        if required and ((required.room_type and required.room_type != room.room_type)
                         or (required.projector_required and not room.has_projector)
                         or (required.whiteboard_required and room.board_type != "whiteboard")):
            continue
        if idx and not fits(peers[idx-1],entry,rid(peers[idx-1]),room.id):
            continue
        if idx+1<len(peers) and not fits(entry,peers[idx+1],room.id,rid(peers[idx+1])):
            continue
        req.assigned_room = room.id
        req.snapshot = {**req.snapshot, "new_room": room.name}
        return None
    return "Нет свободной компьютерной аудитории, подходящей по вместимости, оборудованию и времени перехода"


def process(db, automatic):
    lock(db)
    conf = settings(db)
    if automatic and (not conf or conf.closed or not conf.deadline or utc(conf.deadline)>datetime.now(timezone.utc)):
        return {"processed": 0}
    pending = db.query(ComputerRequest).filter_by(status="pending").order_by(ComputerRequest.id).all()
    if pending or automatic:
        conf = conf or Collection(id=1)
        conf.closed = True
        db.add(conf)
    if not pending:
        db.commit()
        return {"processed": 0}
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("LOCK TABLE weekly_schedule_entries IN SHARE MODE"))
    rooms = {r.id:r for r in db.query(Room).all()}
    route = build_transition_checker(db,rooms)
    profiles = load_equipment_profiles(db)
    for req in pending:
        req.reason = assign(db,req,rooms,route,profiles)
        req.status = "rejected" if req.reason else "assigned"
        db.flush()
    report = AllocationReport(created=datetime.now(timezone.utc), mode="auto" if automatic else "manual",
                              rows=[describe(r) for r in pending])
    db.add(report)
    db.commit()
    return {"processed":len(pending),"report_id":report.id}


@router.post("/process")
def manual(db: Session = Depends(get_db)):
    return process(db,False)


@router.post("/due")
def due(db: Session = Depends(get_db)):
    return process(db,True)


@router.get("/reports")
def reports(db: Session = Depends(get_db)):
    return [{"id":r.id,"date":date_label(r.created),"mode":r.mode,"rows":r.rows}
            for r in db.query(AllocationReport).order_by(AllocationReport.id.desc()).all()]


@router.get("/reports/{report_id}/pdf")
def pdf(report_id:int, db: Session = Depends(get_db)):
    r = db.get(AllocationReport,report_id)
    if not r: raise HTTPException(404,"Отчёт не найден")
    data = BytesIO()
    style = ParagraphStyle("report",fontName="USO",leading=15)
    lines = [f"Компьютерные аудитории · отчёт №{r.id}",date_label(r.created),
             "По сроку" if r.mode=="auto" else "Вручную"]
    for x in r.rows:
        lines.extend([f'{x["day"]} · {x["time"]}–{x["end"]} · {x["subject"]}',
                      f'{x["teacher"]} · {x["group"]} · {x["room"]}',
                      f'Назначена аудитория: {x["new_room"]}' if x["status"]=="assigned" else x["reason"]])
    story = []
    for line in lines: story.extend([Paragraph(escape(line),style),Spacer(1,5)])
    SimpleDocTemplate(data).build(story)
    return Response(data.getvalue(),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="room-report-{r.id}.pdf"'})
