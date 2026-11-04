-- Health drafts stay server-side, scoped to the encoding administrator, for one hour.
CREATE TABLE resident_drafts (
 id VARCHAR(64) PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 payload JSONB NOT NULL, expires_at TIMESTAMP NOT NULL
);
CREATE INDEX resident_drafts_expiry ON resident_drafts(expires_at);
