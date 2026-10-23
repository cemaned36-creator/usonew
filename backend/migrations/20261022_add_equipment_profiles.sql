CREATE TABLE IF NOT EXISTS equipment_profiles (
    code VARCHAR(50) PRIMARY KEY,
    name VARCHAR(150) NOT NULL
);

CREATE TABLE IF NOT EXISTS room_equipment_profiles (
    room_id INTEGER NOT NULL
        REFERENCES rooms(id) ON DELETE CASCADE,

    profile_code VARCHAR(50) NOT NULL
        REFERENCES equipment_profiles(code),

    CONSTRAINT pk_room_equipment_profiles
        PRIMARY KEY (room_id, profile_code)
);

CREATE TABLE IF NOT EXISTS lesson_equipment_profiles (
    lesson_id INTEGER NOT NULL
        REFERENCES lessons(id) ON DELETE CASCADE,

    profile_code VARCHAR(50) NOT NULL
        REFERENCES equipment_profiles(code),

    CONSTRAINT pk_lesson_equipment_profiles
        PRIMARY KEY (lesson_id, profile_code)
);