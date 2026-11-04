CREATE DATABASE IF NOT EXISTS barangay_db;

USE barangay_db;

CREATE TABLE IF NOT EXISTS household (
    id INT AUTO_INCREMENT PRIMARY KEY,
    surname VARCHAR(50) NOT NULL,
    firstname VARCHAR(50) NOT NULL,
    middlename VARCHAR(50),
    age INT,
    gender VARCHAR(10),
    civil_status VARCHAR(20)
);
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100),
    username VARCHAR(100) NOT NULL,
    action_type VARCHAR(50) NOT NULL,          -- e.g., 'ADD', 'UPDATE', 'DELETE'
    target_type VARCHAR(100) DEFAULT 'System', -- e.g., 'Resident', 'Household', 'User'
    target_id VARCHAR(100) DEFAULT 'N/A',      -- affected record id
    old_value TEXT,                            -- JSON/text snapshot before change
    new_value TEXT,                            -- JSON/text snapshot after change
    status VARCHAR(30) DEFAULT 'SUCCESS',
    ip_address VARCHAR(80),
    user_agent VARCHAR(255),
    details TEXT NOT NULL,                     -- e.g., 'Added Resident: Juan Dela Cruz'
    household_context VARCHAR(150) DEFAULT 'N/A', -- e.g., 'Household #104 (San Isidro)'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
