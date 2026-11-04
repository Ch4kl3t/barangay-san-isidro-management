-- Approval and resident verification are independent. Existing accounts stay unlinked.
-- Nullable live references preserve decisions when an account/record is deleted.
CREATE TABLE resident_account_links (
 id BIGSERIAL PRIMARY KEY,
 account_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
 resident_id INTEGER REFERENCES household(id) ON DELETE SET NULL,
 account_id_record INTEGER NOT NULL,
 resident_id_record INTEGER NOT NULL,
 verified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
 verified_by_record INTEGER NOT NULL,
 verified_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 verification_reason VARCHAR(300) NOT NULL,
 revoked_at TIMESTAMP,
 revoked_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
 revocation_reason VARCHAR(300),
 CHECK(length(trim(verification_reason)) BETWEEN 3 AND 300),
 CHECK(revoked_at IS NULL OR revocation_reason IS NOT NULL)
);
CREATE UNIQUE INDEX resident_link_active_account ON resident_account_links(account_id) WHERE revoked_at IS NULL;
CREATE UNIQUE INDEX resident_link_active_resident ON resident_account_links(resident_id) WHERE revoked_at IS NULL;
CREATE INDEX resident_link_account_history ON resident_account_links(account_id_record,id);
