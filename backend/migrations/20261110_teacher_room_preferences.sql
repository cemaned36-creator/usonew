ALTER TABLE teachers ADD COLUMN IF NOT EXISTS preferred_rooms_by_type JSON NOT NULL DEFAULT '{}'::json;
