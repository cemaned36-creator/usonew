-- Audited legacy demo cleanup. Tested on a Neon branch before production.
-- Fails atomically if counts differ or any protected row changes.
BEGIN;
SET LOCAL lock_timeout = '10s';

SET LOCAL statement_timeout = '60s';

LOCK TABLE public.lessons, public.weekly_schedule_entries, public.schedule_entries, public.lesson_groups, public.lesson_requirements, public.lesson_equipment_profiles, public.lesson_teaching_loads, public.teaching_load, public.equipment_profiles, public.rooms, public.room_equipment_profiles, public.room_connections, public.access_points, public.teachers, public.student_groups, public.subjects IN SHARE ROW EXCLUSIVE MODE;

DO $$ BEGIN
IF (SELECT count(*) FROM teaching_load) <> 217 OR (SELECT count(*) FROM lesson_teaching_loads) <> 217 OR (SELECT count(*) FROM lessons) <> 181 OR (SELECT count(*) FROM weekly_schedule_entries) <> 239 THEN RAISE EXCEPTION 'Unexpected dataset; abort cleanup'; END IF;
IF EXISTS (SELECT 1 FROM lesson_teaching_loads WHERE lesson_id BETWEEN 1 AND 11) THEN RAISE EXCEPTION 'Legacy lessons linked to new workload'; END IF;
END $$;

CREATE TEMP TABLE preserved_before ON COMMIT DROP AS SELECT 'lessons' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lessons t WHERE id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'weekly_schedule_entries' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.weekly_schedule_entries t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'schedule_entries' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.schedule_entries t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'lesson_groups' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lesson_groups t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'lesson_requirements' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lesson_requirements t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'lesson_equipment_profiles' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lesson_equipment_profiles t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'lesson_teaching_loads' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lesson_teaching_loads t WHERE TRUE
UNION ALL
SELECT 'teaching_load' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.teaching_load t WHERE TRUE
UNION ALL
SELECT 'equipment_profiles' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.equipment_profiles t WHERE TRUE
UNION ALL
SELECT 'rooms' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.rooms t WHERE id NOT BETWEEN 1 AND 12
UNION ALL
SELECT 'room_equipment_profiles' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.room_equipment_profiles t WHERE room_id NOT BETWEEN 1 AND 12
UNION ALL
SELECT 'room_connections' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.room_connections t WHERE NOT (coalesce(from_room_id BETWEEN 1 AND 12,false) OR coalesce(to_room_id BETWEEN 1 AND 12,false) OR coalesce(from_access_point_id=1,false) OR coalesce(to_access_point_id=1,false))
UNION ALL
SELECT 'access_points' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.access_points t WHERE id<>1
UNION ALL
SELECT 'teachers' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.teachers t WHERE id NOT BETWEEN 2 AND 6
UNION ALL
SELECT 'student_groups' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.student_groups t WHERE id NOT BETWEEN 5 AND 8
UNION ALL
SELECT 'subjects' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.subjects t WHERE id NOT IN (6,7,9,10);

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.weekly_schedule_entries WHERE lesson_id BETWEEN 1 AND 11; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 22 THEN RAISE EXCEPTION 'weekly_schedule_entries: expected 22 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.schedule_entries WHERE lesson_id BETWEEN 1 AND 11; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 1 THEN RAISE EXCEPTION 'schedule_entries: expected 1 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.lesson_requirements WHERE lesson_id BETWEEN 1 AND 11; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 10 THEN RAISE EXCEPTION 'lesson_requirements: expected 10 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.lesson_groups WHERE lesson_id BETWEEN 1 AND 11; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 11 THEN RAISE EXCEPTION 'lesson_groups: expected 11 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.lesson_equipment_profiles WHERE lesson_id BETWEEN 1 AND 11; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 0 THEN RAISE EXCEPTION 'lesson_equipment_profiles: expected 0 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.lessons WHERE id BETWEEN 1 AND 11; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 11 THEN RAISE EXCEPTION 'lessons: expected 11 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.room_connections WHERE NOT (NOT (coalesce(from_room_id BETWEEN 1 AND 12,false) OR coalesce(to_room_id BETWEEN 1 AND 12,false) OR coalesce(from_access_point_id=1,false) OR coalesce(to_access_point_id=1,false))); GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 26 THEN RAISE EXCEPTION 'room_connections: expected 26 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.room_equipment_profiles WHERE room_id BETWEEN 1 AND 12; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 0 THEN RAISE EXCEPTION 'room_equipment_profiles: expected 0 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.rooms WHERE id BETWEEN 1 AND 12 AND building='Главный корпус'; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 12 THEN RAISE EXCEPTION 'rooms: expected 12 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.access_points WHERE id=1 AND name='Охрана' AND point_type='KEY_DESK'; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 1 THEN RAISE EXCEPTION 'access_points: expected 1 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.teachers WHERE id BETWEEN 2 AND 6; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 5 THEN RAISE EXCEPTION 'teachers: expected 5 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.student_groups WHERE id BETWEEN 5 AND 8; GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 4 THEN RAISE EXCEPTION 'student_groups: expected 4 deleted, got %',affected; END IF; END $$;

DO $$ DECLARE affected integer; BEGIN DELETE FROM public.subjects WHERE id IN (6,7,9,10); GET DIAGNOSTICS affected = ROW_COUNT; IF affected <> 4 THEN RAISE EXCEPTION 'subjects: expected 4 deleted, got %',affected; END IF; END $$;

CREATE TEMP TABLE preserved_after ON COMMIT DROP AS SELECT 'lessons' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lessons t WHERE id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'weekly_schedule_entries' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.weekly_schedule_entries t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'schedule_entries' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.schedule_entries t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'lesson_groups' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lesson_groups t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'lesson_requirements' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lesson_requirements t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'lesson_equipment_profiles' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lesson_equipment_profiles t WHERE lesson_id NOT BETWEEN 1 AND 11
UNION ALL
SELECT 'lesson_teaching_loads' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.lesson_teaching_loads t WHERE TRUE
UNION ALL
SELECT 'teaching_load' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.teaching_load t WHERE TRUE
UNION ALL
SELECT 'equipment_profiles' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.equipment_profiles t WHERE TRUE
UNION ALL
SELECT 'rooms' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.rooms t WHERE id NOT BETWEEN 1 AND 12
UNION ALL
SELECT 'room_equipment_profiles' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.room_equipment_profiles t WHERE room_id NOT BETWEEN 1 AND 12
UNION ALL
SELECT 'room_connections' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.room_connections t WHERE NOT (coalesce(from_room_id BETWEEN 1 AND 12,false) OR coalesce(to_room_id BETWEEN 1 AND 12,false) OR coalesce(from_access_point_id=1,false) OR coalesce(to_access_point_id=1,false))
UNION ALL
SELECT 'access_points' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.access_points t WHERE id<>1
UNION ALL
SELECT 'teachers' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.teachers t WHERE id NOT BETWEEN 2 AND 6
UNION ALL
SELECT 'student_groups' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.student_groups t WHERE id NOT BETWEEN 5 AND 8
UNION ALL
SELECT 'subjects' AS table_name, coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) AS rows FROM public.subjects t WHERE id NOT IN (6,7,9,10);

DO $$ BEGIN IF EXISTS(SELECT * FROM preserved_before EXCEPT SELECT * FROM preserved_after) OR EXISTS(SELECT * FROM preserved_after EXCEPT SELECT * FROM preserved_before) THEN RAISE EXCEPTION 'Protected data changed'; END IF; END $$;

SELECT (SELECT count(*) FROM lessons) lessons,(SELECT count(*) FROM teaching_load) teaching_load,(SELECT count(*) FROM weekly_schedule_entries) weekly_entries,(SELECT count(*) FROM teachers) teachers,(SELECT count(*) FROM student_groups) groups,(SELECT count(*) FROM subjects) subjects,(SELECT count(*) FROM rooms) rooms,(SELECT count(*) FROM room_connections) connections;
COMMIT;
