-- USO: удаление типа both и перевод всех записей на odd/even.
-- Существующие записи both копируются в обе недели, чтобы не потерять расписание.

BEGIN;

-- Удаляем старое UNIQUE (lesson_id, weekday), которое блокирует
-- одинаковое занятие в один день разных типов недель.
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
          ) = ARRAY['lesson_id', 'weekday']::name[]
    LOOP
        EXECUTE format(
            'ALTER TABLE weekly_schedule_entries DROP CONSTRAINT %I',
            constraint_record.conname
        );
    END LOOP;
END $$;

-- Временно убираем CHECK, разрешающий both.
ALTER TABLE weekly_schedule_entries
    DROP CONSTRAINT IF EXISTS check_week_type;

-- Переносим каждую запись both в обе недели.
-- Если запись нужного типа уже есть, сохраняем существующую.
INSERT INTO weekly_schedule_entries
    (lesson_id, weekday, week_type, room_id, start_time, end_time)
SELECT lesson_id, weekday, 'odd', room_id, start_time, end_time
FROM weekly_schedule_entries
WHERE week_type = 'both'
ON CONFLICT (lesson_id, weekday, week_type) DO NOTHING;

INSERT INTO weekly_schedule_entries
    (lesson_id, weekday, week_type, room_id, start_time, end_time)
SELECT lesson_id, weekday, 'even', room_id, start_time, end_time
FROM weekly_schedule_entries
WHERE week_type = 'both'
ON CONFLICT (lesson_id, weekday, week_type) DO NOTHING;

DELETE FROM weekly_schedule_entries
WHERE week_type = 'both';

ALTER TABLE weekly_schedule_entries
    ALTER COLUMN week_type SET DEFAULT 'odd';

ALTER TABLE weekly_schedule_entries
    ADD CONSTRAINT check_week_type
    CHECK (week_type IN ('odd', 'even'));

COMMIT;
