from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, JSON, UniqueConstraint
from app.database import Base


class ComputerRequest(Base):
    __tablename__ = "computer_requests"
    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, nullable=False)
    lesson_id = Column(Integer, nullable=False)
    teacher_id = Column(Integer, nullable=False, index=True)
    day = Column(Date, nullable=False, index=True)
    snapshot = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending")
    reason = Column(String)
    assigned_room = Column(Integer)
    hidden = Column(Boolean, nullable=False, default=False)
    __table_args__ = (UniqueConstraint("entry_id", "day"),)


class Collection(Base):
    __tablename__ = "computer_request_settings"
    id = Column(Integer, primary_key=True)
    closed = Column(Boolean, nullable=False, default=False)
    deadline = Column(DateTime(timezone=True))


class AllocationReport(Base):
    __tablename__ = "computer_request_reports"
    id = Column(Integer, primary_key=True)
    created = Column(DateTime(timezone=True), nullable=False)
    mode = Column(String, nullable=False)
    rows = Column(JSON, nullable=False)


class AllocationUndo(Base):
    __tablename__ = "computer_request_undos"
    report_id = Column(Integer, ForeignKey("computer_request_reports.id"), primary_key=True)
    created = Column(DateTime(timezone=True), nullable=False)


def overrides(db, start, end):
    rows = db.query(ComputerRequest).filter(ComputerRequest.day.between(start, end),
                                            ComputerRequest.status == "assigned").all()
    return {(r.day, r.entry_id, r.lesson_id): r.assigned_room for r in rows}
