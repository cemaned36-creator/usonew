-- Additive migration. Does not modify timetable entries.
BEGIN;
CREATE TABLE IF NOT EXISTS optimization_runs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    week_type VARCHAR(8) NOT NULL,
    teacher_id INTEGER,
    teacher_name VARCHAR(100),
    before_entries JSON NOT NULL,
    after_entries JSON NOT NULL,
    metrics JSON NOT NULL,
    restored_at TIMESTAMPTZ,
    CONSTRAINT ck_optimization_run_week CHECK (week_type IN ('odd', 'even'))
);
CREATE INDEX IF NOT EXISTS ix_optimization_runs_week_type ON optimization_runs (week_type);
CREATE INDEX IF NOT EXISTS ix_optimization_runs_teacher_id ON optimization_runs (teacher_id);
COMMIT;
