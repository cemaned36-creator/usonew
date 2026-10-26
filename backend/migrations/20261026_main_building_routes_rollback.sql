-- Restore ONLY this migration's routes/building/desk; leave schedule untouched.
-- Refuse if routes have changed after deployment. Keep the backup for review.
BEGIN;
SET LOCAL lock_timeout='10s';
LOCK TABLE rooms, access_points, room_connections IN SHARE ROW EXCLUSIVE MODE;
DO $rollback$
DECLARE b jsonb; a jsonb;
BEGIN
    SELECT before_data,after_data INTO b,a FROM route_migration_backups WHERE migration_key='20261026-main-building';
    IF b IS NULL THEN RAISE EXCEPTION 'Migration backup missing'; END IF;
    IF a->'connections' IS DISTINCT FROM (SELECT jsonb_agg(to_jsonb(c) ORDER BY id) FROM room_connections c)
       OR a->'desk' IS DISTINCT FROM (SELECT to_jsonb(p) FROM access_points p WHERE id=2)
       OR a->'rooms' IS DISTINCT FROM (SELECT jsonb_agg(jsonb_build_object('id',r.id,'building',r.building) ORDER BY r.id) FROM rooms r WHERE r.id IN (SELECT (value->>'id')::int FROM jsonb_array_elements(b->'rooms')))
    THEN RAISE EXCEPTION 'Data changed since migration; review before rollback'; END IF;
    UPDATE room_connections c SET distance=x.distance,travel_time=x.travel_time
    FROM jsonb_to_recordset(b->'connections') AS x(id int,distance numeric,travel_time int) WHERE c.id=x.id;
    UPDATE rooms r SET building=x.building FROM jsonb_to_recordset(b->'rooms') AS x(id int,building text) WHERE r.id=x.id;
    UPDATE access_points SET name=b->'desk'->>'name' WHERE id=2;
END $rollback$;
COMMENT ON COLUMN room_connections.distance IS 'Restored demonstration distance; see route_migration_backups for migration history.';
COMMIT;
