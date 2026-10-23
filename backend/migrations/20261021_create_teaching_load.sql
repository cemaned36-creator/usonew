-- USO: создание таблицы teaching_load для импортированной учебной нагрузки.
-- Только подготовка локальной миграции. Не выполнять в Neon без согласования.

BEGIN;

CREATE TABLE teaching_load (
    id SERIAL PRIMARY KEY,
    source_row_number INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    group_id INTEGER NOT NULL REFERENCES student_groups(id),
    teacher_position VARCHAR(100),
    faculty VARCHAR(50),
    lesson_type VARCHAR(50) NOT NULL,
    subgroup VARCHAR(30),
    weeks_label VARCHAR(30) NOT NULL,
    odd_pairs INTEGER NOT NULL DEFAULT 0,
    even_pairs INTEGER NOT NULL DEFAULT 0,
    source_room VARCHAR(50),
    joint_groups TEXT
);

CREATE UNIQUE INDEX ix_teaching_load_source_row_number
    ON teaching_load(source_row_number);


CREATE INDEX ix_teaching_load_teacher_id
    ON teaching_load(teacher_id);

CREATE INDEX ix_teaching_load_subject_id
    ON teaching_load(subject_id);

CREATE INDEX ix_teaching_load_group_id
    ON teaching_load(group_id);

COMMIT;
