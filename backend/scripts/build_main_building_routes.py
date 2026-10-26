"""Rebuild the reviewed route migration; this script never connects to a DB."""
import heapq
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_routes(graph):
    adj = {n: [] for n in graph['nodes']}
    for edge in graph['edges']:
        for a,b in [(edge['a'],edge['b']),(edge['b'],edge['a'])]:
            adj[a].append((b,edge['time_s'],edge['distance_m'] or 0))
    ends = [(r['id'],r['node_id']) for r in graph['rooms']] + [(None,graph['entrance_node'])]
    result = []
    for room_id,source in ends:
        queue=[(0,0,source)];seen={}
        while queue:
            seconds,metres,n=heapq.heappop(queue)
            if n in seen:continue
            seen[n]=(seconds,metres)
            for nxt,t,d in adj[n]:
                if nxt not in seen:heapq.heappush(queue,(seconds+t,metres+d,nxt))
        for target_id,target in ends:
            if target==source:continue
            seconds,metres=seen[target]
            result.append(dict(from_room_id=room_id,to_room_id=target_id,
                from_access_point_id=2 if room_id is None else None,
                to_access_point_id=2 if target_id is None else None,
                distance=round(metres,2),travel_time=max(1,math.ceil(seconds/60-1e-9))))
    assert len(result)==4556
    return result


def migration(graph):
    routes=build_routes(graph)
    route_json=json.dumps([[r['from_room_id'],r['to_room_id'],r['distance'],r['travel_time']] for r in routes],separators=(',',':'))
    rooms_json=json.dumps([{k:r[k] for k in ('id','name','floor')} for r in graph['rooms']],ensure_ascii=False,separators=(',',':'))
    return '''-- Generated from data/main_building_graph.json. Code rollout must precede this migration.
BEGIN;
SET LOCAL lock_timeout = '10s';
LOCK TABLE rooms, access_points, room_connections IN SHARE ROW EXCLUSIVE MODE;
CREATE TABLE IF NOT EXISTS route_migration_backups (
    migration_key text PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT now(),
    before_data jsonb NOT NULL, after_data jsonb NOT NULL
);
CREATE TEMP TABLE desired_routes ON COMMIT DROP AS
SELECT (value->>0)::int AS from_room_id,(value->>1)::int AS to_room_id,
CASE WHEN (value->>0) IS NULL THEN 2 ELSE NULL END AS from_access_point_id,
CASE WHEN (value->>1) IS NULL THEN 2 ELSE NULL END AS to_access_point_id,
(value->>2)::numeric AS distance,(value->>3)::int AS travel_time
FROM jsonb_array_elements($routes$''' + route_json + '''$routes$::jsonb)
AS x(value);
CREATE TEMP TABLE desired_rooms ON COMMIT DROP AS
SELECT * FROM jsonb_to_recordset($rooms$''' + rooms_json + '''$rooms$::jsonb) AS x(id int,name text,floor int);
DO $migration$
DECLARE matched int; saved jsonb;
BEGIN
    IF EXISTS(SELECT 1 FROM route_migration_backups WHERE migration_key='20261026-main-building') THEN
        RAISE EXCEPTION 'Migration already applied; inspect backup before retrying';
    END IF;
    SELECT count(*) INTO matched FROM rooms r JOIN desired_rooms d ON r.id=d.id AND r.name=d.name AND r.floor=d.floor WHERE r.building='Б';
    IF matched<>67 OR (SELECT count(*) FROM rooms WHERE building='Б')<>67 THEN RAISE EXCEPTION 'Room inventory differs from reviewed graph'; END IF;
    IF NOT EXISTS(SELECT 1 FROM access_points WHERE id=2 AND name='Охрана корпуса Б' AND point_type='KEY_DESK') THEN RAISE EXCEPTION 'Unexpected key desk'; END IF;
    IF EXISTS(SELECT 1 FROM rooms WHERE building='Главный корпус') OR EXISTS(SELECT 1 FROM access_points WHERE name='Охрана Главного корпуса') THEN RAISE EXCEPTION 'Target name already exists'; END IF;
    SELECT count(*) INTO matched FROM room_connections c JOIN desired_routes d
    ON c.from_room_id IS NOT DISTINCT FROM d.from_room_id AND c.to_room_id IS NOT DISTINCT FROM d.to_room_id
    AND c.from_access_point_id IS NOT DISTINCT FROM d.from_access_point_id AND c.to_access_point_id IS NOT DISTINCT FROM d.to_access_point_id;
    IF matched<>4556 OR (SELECT count(*) FROM room_connections)<>4556 THEN RAISE EXCEPTION 'Unexpected route set'; END IF;
    IF (SELECT count(*) FROM (SELECT DISTINCT from_room_id,to_room_id,from_access_point_id,to_access_point_id FROM room_connections)x)<>4556 THEN RAISE EXCEPTION 'Duplicate route endpoints'; END IF;
    saved=jsonb_build_object('connections',(SELECT jsonb_agg(to_jsonb(c) ORDER BY id) FROM room_connections c),
      'rooms',(SELECT jsonb_agg(jsonb_build_object('id',r.id,'building',r.building) ORDER BY r.id) FROM rooms r JOIN desired_rooms d USING(id)),
      'desk',(SELECT to_jsonb(a) FROM access_points a WHERE id=2));
    UPDATE room_connections c SET distance=d.distance,travel_time=d.travel_time FROM desired_routes d
    WHERE c.from_room_id IS NOT DISTINCT FROM d.from_room_id AND c.to_room_id IS NOT DISTINCT FROM d.to_room_id
    AND c.from_access_point_id IS NOT DISTINCT FROM d.from_access_point_id AND c.to_access_point_id IS NOT DISTINCT FROM d.to_access_point_id;
    GET DIAGNOSTICS matched=ROW_COUNT;
    IF matched<>4556 THEN RAISE EXCEPTION 'Route update count mismatch'; END IF;
    UPDATE rooms SET building='Главный корпус' WHERE id IN (SELECT id FROM desired_rooms);
    UPDATE access_points SET name='Охрана Главного корпуса' WHERE id=2;
    INSERT INTO route_migration_backups(migration_key,before_data,after_data)
    VALUES('20261026-main-building',saved,jsonb_build_object(
      'connections',(SELECT jsonb_agg(to_jsonb(c) ORDER BY id) FROM room_connections c),
      'rooms',(SELECT jsonb_agg(jsonb_build_object('id',r.id,'building',r.building) ORDER BY r.id) FROM rooms r JOIN desired_rooms d USING(id)),
      'desk',(SELECT to_jsonb(a) FROM access_points a WHERE id=2)));
END $migration$;
COMMENT ON COLUMN room_connections.distance IS 'Approximate horizontal metres along the fastest route; staircase length is unknown and excluded. Use travel_time for entrance preference.';
COMMIT;
'''


if __name__=='__main__':
    graph=json.loads((ROOT/'data/main_building_graph.json').read_text())
    path=ROOT/'migrations/20261026_main_building_routes.sql'
    path.write_text(migration(graph))
    print(f'Prepared 4556 routes in {path.name}; no database connection.')
