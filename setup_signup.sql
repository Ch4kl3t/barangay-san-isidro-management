-- ============================================================================
-- SELF-REGISTRATION WITH ADMIN APPROVAL SYSTEM
-- ============================================================================
-- This script adds account status tracking for self-registration workflow
-- Status: 'pending' (awaiting admin approval), 'approved' (can login), 'rejected'
-- ============================================================================

-- 1. ADD STATUS COLUMN TO USERS TABLE
-- ============================================================================
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'approved' COMMENT 'pending, approved, or rejected';

-- 2. ADD SIGNUP DATE TRACKING
-- ============================================================================
ALTER TABLE users ADD COLUMN signup_date TIMESTAMP NULL COMMENT 'When user self-registered';

-- 3. UPDATE EXISTING USERS TO APPROVED STATUS
-- ============================================================================
-- Existing users are already approved (they were manually created)
UPDATE users SET status = 'approved' WHERE status IS NULL OR status = '';

-- 4. CREATE INDEX FOR STATUS LOOKUPS
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_signup_date ON users(signup_date);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- After running this migration, verify with these queries:
--
-- SELECT id, username, role, status, signup_date FROM users;
-- DESCRIBE users;
--
-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================
-- Next Steps:
-- 1. Run this migration: mysql -u root barangay_db < setup_signup.sql
-- 2. Public signup page is now available at /signup
-- 3. Users self-register with pending status
-- 4. Admin approves/rejects in User Management dashboard
-- ============================================================================
