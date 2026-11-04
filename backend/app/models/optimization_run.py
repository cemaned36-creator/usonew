"""Immutable before/after assignments for each applied optimization."""
from sqlalchemy import Column, Integer, String, DateTime, JSON, CheckConstraint, func
from app.database import Base


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    week_type = Column(String(8), nullable=False, index=True)
    # Historical scope, deliberately not a cascading FK: preserve history after deletion.
    teacher_id = Column(Integer, nullable=True, index=True)
    teacher_name = Column(String(100), nullable=True)
    before_entries = Column(JSON, nullable=False)
    after_entries = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)
    restored_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("week_type IN ('odd', 'even')", name="ck_optimization_run_week"),
    )
