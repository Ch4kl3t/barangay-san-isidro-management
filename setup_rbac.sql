-- ============================================================================
-- ROLE-BASED AUTHENTICATION SYSTEM DATABASE MIGRATION
-- ============================================================================
-- This script adds role-based access control to the barangay system
-- Roles: 'admin' (full access) and 'user' (view-only)
-- ============================================================================

-- 1. ADD ROLE COLUMN TO USERS TABLE
-- ============================================================================
-- ALTER IGNORE will not fail if column already exists
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' COMMENT 'admin or user';

-- 2. CREATE PASSWORD RESET TRACKING TABLE
-- ============================================================================
-- This table stores password reset tokens and tracks their usage
CREATE TABLE IF NOT EXISTS password_resets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL COMMENT 'Unique reset token (32 chars)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When reset was requested',
    expires_at TIMESTAMP NOT NULL COMMENT 'Token expiration (1 hour from creation)',
    used BOOLEAN DEFAULT FALSE COMMENT 'Whether token has been used',
    used_at TIMESTAMP NULL COMMENT 'When password was reset',
    ip_address VARCHAR(80) COMMENT 'IP address of reset request',
    attempt_count INT DEFAULT 1 COMMENT 'Number of attempts to use this token',
    KEY idx_token (token),
    KEY idx_username (username),
    KEY idx_used (used)
);

-- 3. UPDATE EXISTING USERS TO ADMIN ROLE
-- ============================================================================
-- Ensures existing users maintain full access when system is upgraded
UPDATE users SET role = 'admin' WHERE role IS NULL OR role = '';

-- 4. CREATE INDEX FOR ROLE LOOKUPS
-- ============================================================================
-- Improves performance of role-based queries
CREATE INDEX IF NOT EXISTS idx_role ON users(role);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- After running this migration, verify with these queries:
--
-- SELECT id, username, role FROM users;
-- DESCRIBE users;
-- DESCRIBE password_resets;
--
-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================
-- Next Steps:
-- 1. Copy .env.example to .env and add your Gmail credentials
-- 2. Restart the Flask application: python app.py
-- 3. Log in with existing admin account
-- 4. Test "Forgot Password" to verify email sends
-- 5. Visit /user-management (admin panel) to create regular user accounts
-- 6. Set user role to 'user' for residents (view-only access)
-- ============================================================================
