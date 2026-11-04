ALTER TABLE users ADD COLUMN IF NOT EXISTS session_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE household ADD COLUMN IF NOT EXISTS mental_health_status VARCHAR(500);
ALTER TABLE household ADD COLUMN IF NOT EXISTS current_health_status VARCHAR(500);
ALTER TABLE household ALTER COLUMN mental_health_status DROP NOT NULL;
ALTER TABLE household ALTER COLUMN current_health_status DROP NOT NULL;
-- Unknown history stays unknown. Never backfill these with migration time.
ALTER TABLE household ADD COLUMN IF NOT EXISTS registration_date DATE;
ALTER TABLE household ADD COLUMN IF NOT EXISTS death_date DATE;
ALTER TABLE household ADD COLUMN IF NOT EXISTS status_recorded_at TIMESTAMP;
ALTER TABLE password_resets ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE password_resets ADD COLUMN IF NOT EXISTS token_hash VARCHAR(64);
-- Legacy NOT NULL columns must be relaxed before discarding old plaintext tokens.
ALTER TABLE password_resets ALTER COLUMN token DROP NOT NULL;
ALTER TABLE password_resets ALTER COLUMN username DROP NOT NULL;
-- Legacy tokens are revoked; the plaintext token column is retained nullable for rollback compatibility.
UPDATE password_resets SET used=TRUE, token=NULL WHERE token_hash IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS password_resets_hash ON password_resets(token_hash);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_normalized ON users(LOWER(TRIM(email)))
 WHERE email IS NOT NULL AND TRIM(email) <> '';
CREATE UNIQUE INDEX IF NOT EXISTS households_identity ON households(LOWER(TRIM(surname)), LOWER(TRIM(house_number)));
ALTER TABLE household ADD CONSTRAINT household_membership FOREIGN KEY(household_id)
 REFERENCES households(id) ON DELETE RESTRICT;
ALTER TABLE household ADD CONSTRAINT mental_health_length CHECK (length(mental_health_status) <= 500);
ALTER TABLE household ADD CONSTRAINT current_health_length CHECK (length(current_health_status) <= 500);
CREATE INDEX IF NOT EXISTS household_household_id ON household(household_id);
CREATE INDEX IF NOT EXISTS audit_created ON audit_logs(created_at, id);
CREATE INDEX IF NOT EXISTS reset_user_created ON password_resets(user_id, created_at);
CREATE TABLE IF NOT EXISTS auth_attempts (
 key_hash VARCHAR(64) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS auth_attempts_lookup ON auth_attempts(key_hash, created_at);
