-- Additive notification state; audit rows remain immutable and are never backfilled.
CREATE TABLE notification_events (
 id BIGSERIAL PRIMARY KEY,
 audit_id INTEGER NOT NULL UNIQUE REFERENCES audit_logs(id) ON DELETE RESTRICT,
 category TEXT NOT NULL CHECK(category IN ('accounts','residents','households')),
 summary TEXT NOT NULL,
 destination TEXT NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE notification_recipients (
 event_id BIGINT NOT NULL REFERENCES notification_events(id) ON DELETE CASCADE,
 recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 read_at TIMESTAMP,
 PRIMARY KEY(event_id,recipient_id)
);
CREATE INDEX notification_recipient_unread ON notification_recipients(recipient_id,read_at,event_id DESC);
