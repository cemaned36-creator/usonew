ALTER TABLE lessons
    ADD COLUMN IF NOT EXISTS lesson_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS weeks_label VARCHAR(30),
    ADD COLUMN IF NOT EXISTS odd_pairs INTEGER
        CONSTRAINT ck_lessons_odd_pairs_nonnegative
        CHECK (odd_pairs >= 0),
    ADD COLUMN IF NOT EXISTS even_pairs INTEGER
        CONSTRAINT ck_lessons_even_pairs_nonnegative
        CHECK (even_pairs >= 0);

CREATE TABLE IF NOT EXISTS lesson_groups (
    lesson_id INTEGER NOT NULL
        REFERENCES lessons(id) ON DELETE CASCADE,

    group_id INTEGER NOT NULL
        REFERENCES student_groups(id),

    subgroup_number INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT pk_lesson_groups
        PRIMARY KEY (lesson_id, group_id),

    CONSTRAINT ck_lesson_groups_subgroup
        CHECK (subgroup_number IN (0, 1, 2))
);

CREATE INDEX IF NOT EXISTS ix_lesson_groups_group_id
    ON lesson_groups(group_id);

CREATE TABLE IF NOT EXISTS lesson_teaching_loads (
    lesson_id INTEGER NOT NULL
        REFERENCES lessons(id) ON DELETE CASCADE,

    teaching_load_id INTEGER NOT NULL
        REFERENCES teaching_load(id),

    CONSTRAINT pk_lesson_teaching_loads
        PRIMARY KEY (lesson_id, teaching_load_id),

    CONSTRAINT uq_lesson_teaching_loads_source
        UNIQUE (teaching_load_id)
);

-- Existing lessons retain their original group.
INSERT INTO lesson_groups (lesson_id, group_id, subgroup_number)
SELECT id, group_id, 0
FROM lessons
ON CONFLICT (lesson_id, group_id) DO NOTHING;