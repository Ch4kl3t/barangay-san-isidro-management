-- Explicit baseline. Existing tables are preserved; no administrator is seeded.
CREATE TABLE IF NOT EXISTS users (
 id SERIAL PRIMARY KEY, username VARCHAR(255) UNIQUE NOT NULL,
 password VARCHAR(255) NOT NULL, email VARCHAR(255), role VARCHAR(20) DEFAULT 'user',
 status VARCHAR(20) DEFAULT 'approved', signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS households (
 id SERIAL PRIMARY KEY, surname VARCHAR(255), house_number VARCHAR(100),
 address TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS household (
 id SERIAL PRIMARY KEY, firstname VARCHAR(255), middlename VARCHAR(255), surname VARCHAR(255),
 house_number VARCHAR(100), address TEXT, age VARCHAR(20), birthdate VARCHAR(50),
 gender VARCHAR(50), civil_status VARCHAR(100), occupation VARCHAR(255), household_id INTEGER,
 status VARCHAR(50) DEFAULT 'Active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_logs (
 id SERIAL PRIMARY KEY, user_id VARCHAR(100), username VARCHAR(255), action_type VARCHAR(100),
 target_type VARCHAR(100) DEFAULT 'System', target_id VARCHAR(100) DEFAULT 'N/A',
 old_value TEXT, new_value TEXT, details TEXT, household_context TEXT DEFAULT 'N/A',
 status VARCHAR(30) DEFAULT 'SUCCESS', ip_address VARCHAR(80), user_agent VARCHAR(255),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS password_resets (
 id SERIAL PRIMARY KEY, username VARCHAR(255), token VARCHAR(255),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL,
 used BOOLEAN DEFAULT FALSE, used_at TIMESTAMP, ip_address VARCHAR(80), attempt_count INTEGER DEFAULT 1
);
