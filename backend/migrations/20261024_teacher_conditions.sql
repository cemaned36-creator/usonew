BEGIN;
ALTER TABLE teachers ADD COLUMN earliest_start_pair INTEGER NOT NULL DEFAULT 1;
ALTER TABLE teachers ADD COLUMN max_floor INTEGER;
ALTER TABLE teachers ADD COLUMN prefer_near_entrance BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE teachers ADD CONSTRAINT ck_teacher_start_pair CHECK (earliest_start_pair BETWEEN 1 AND 3);
ALTER TABLE teachers ADD CONSTRAINT ck_teacher_max_floor CHECK (max_floor IS NULL OR max_floor BETWEEN 1 AND 4);
COMMIT;
