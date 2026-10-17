-- USO: поддержка расписания по типу учебной недели.
-- Существующие записи сохраняются и отображаются в обе недели.

ALTER TABLE weekly_schedule_entries
    ADD COLUMN IF NOT EXISTS week_type VARCHAR(8) NOT NULL DEFAULT 'both';

-- Удаляем старое ограничение UNIQUE только на lesson_id (имя могло отличаться).
DO $$
DECLARE
    constraint_record RECORD;
BEGIN
    FOR constraint_record IN
        SELECT c.conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE t.relname = 'weekly_schedule_entries'
          AND n.nspname = current_schema()
          AND c.contype = 'u'
          AND (
              SELECT array_agg(a.attname ORDER BY a.attname)
              FROM unnest(c.conkey) AS key_column(attnum)
              JOIN pg_attribute a
                ON a.attrelid = t.oid AND a.attnum = key_column.attnum
          ) = ARRAY['lesson_id']::name[]
    LOOP
        EXECUTE format(
            'ALTER TABLE weekly_schedule_entries DROP CONSTRAINT %I',
            constraint_record.conname
        );
    END LOOP;
END $$;

-- Повторный запуск безопасен: перед созданием проверяем имя ограничения.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_weekly_schedule_lesson_day_week'
          AND conrelid = 'weekly_schedule_entries'::regclass
    ) THEN
        ALTER TABLE weekly_schedule_entries
            ADD CONSTRAINT uq_weekly_schedule_lesson_day_week
            UNIQUE (lesson_id, weekday, week_type);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'check_week_type'
          AND conrelid = 'weekly_schedule_entries'::regclass
    ) THEN
        ALTER TABLE weekly_schedule_entries
            ADD CONSTRAINT check_week_type
            CHECK (week_type IN ('odd', 'even', 'both'));
    END IF;
END $$;
