# Role-Based Authentication System - Setup Guide

This guide walks you through setting up the role-based authentication system for the Barangay Information System.

## Overview

The system now supports two user roles:
- **Admin**: Full access to all features (add, edit, delete members/households, generate reports, manage users)
- **User**: View-only access (can only view residents, households, and analytics)

## Prerequisites

- Python 3.7+
- Flask application running
- MySQL database connection working
- Gmail account (for password recovery emails)

---

## Step 1: Database Migration

The system adds a `role` column to the users table and creates a `password_resets` table for tracking password reset attempts.

### Run the Migration

```bash
mysql -u root -p barangay_db < setup_rbac.sql
```

Or, if using MySQL GUI (phpMyAdmin, Workbench):
1. Open your MySQL management tool
2. Select the `barangay_db` database
3. Open and execute the `setup_rbac.sql` file

### Verify Migration

After running the migration, verify the changes:

```sql
-- Check users table has role column
SELECT id, username, role FROM users;

-- Should show all users with role = 'admin'
DESCRIBE users;

-- Should show the new password_resets table
DESCRIBE password_resets;
```

---

## Step 2: Gmail Configuration

The system uses Gmail SMTP to send password reset emails. Follow these steps to set up Gmail credentials.

### Get Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (choose your platform)
3. Google will generate a 16-character password like: `abcd efgh ijkl mnop`
4. Copy this password (spaces are fine)

### Create .env File

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your Gmail credentials:
   ```
   GMAIL_ADDRESS=your-email@gmail.com
   GMAIL_PASSWORD=abcd efgh ijkl mnop
   ```

3. Save the file

### Important Security Notes

- ⚠️ **DO NOT** commit `.env` to version control
- ⚠️ The `.env` file should be in `.gitignore`
- ⚠️ Never use your regular Gmail password; always use an App Password
- ⚠️ App Passwords are only available if you have 2-Factor Authentication enabled on Gmail

---

## Step 3: Restart Flask Application

After running the migration and setting up Gmail credentials, restart the Flask application:

```bash
python app.py
```

The application will now run with role-based authentication enabled.

---

## Step 4: Test the System

### Test Admin Login
1. Open the system login page
2. Log in with your existing admin account
3. You should see "ADMIN" badge in the top-right corner
4. Click the dashboard statistics - they should display normally
5. Try accessing Edit/Delete/Add buttons - they should work

### Test Password Recovery
1. On the login page, click "Forgot Password?"
2. Enter your admin username
3. Check your Gmail inbox (and spam folder)
4. Click the password reset link
5. Enter a new password (8+ characters)
6. Log in with the new password to verify it worked

### Test Admin Panel
1. After logging in as admin, click your username in the top-right
2. Select "User Management"
3. You should see a list of all users with their roles
4. You should see password reset activity in the "Password Reset Activity" tab

---

## Step 5: Create User Accounts

### Add Regular Users (View-Only Access)

As an admin:
1. Go to User Management (/user-management)
2. View the "Users" tab
3. Click "Make User" on any admin account to demote them
4. Or create new users directly in the MySQL database:

```sql
INSERT INTO users (username, password, role) VALUES ('resident1', 'defaultpassword', 'user');
INSERT INTO users (username, password, role) VALUES ('resident2', 'defaultpassword', 'user');
```

5. Users can then reset their password via "Forgot Password" link

### Promote Users to Admin

As an admin:
1. Go to User Management (/user-management)
2. In the "Users" tab, click "Make Admin" on any regular user
3. That user will now have full access

---

## Step 6: Restrict UI for View-Only Users

Regular users (role='user') will:
- ❌ NOT see edit/delete buttons for members and households
- ❌ NOT see "Add Member" or "Add Household" buttons
- ❌ NOT see the "Print Reports" page
- ❌ NOT see dashboard statistics on the home page
- ✅ Can view all members and households (read-only)
- ✅ Can access analytics dashboard
- ✅ Can change their own password via User Profile

### Current UI Hiding

The following has been implemented:
- Home page hides statistics for non-admin users
- /print_reports page restricted to admins
- All edit/delete routes are now admin-only

### Additional UI Customizations (Optional)

To further improve the view-only experience, consider:
1. Hiding "Edit" and "Delete" buttons in member/household lists for non-admins
2. Hiding "Add Member/Household" buttons from the sidebar for non-admins
3. Showing a "View-Only Mode" indicator at the top of the page

See base.html and script.js for implementing these UI changes.

---

## Troubleshooting

### Problem: "Unauthorized" error when trying to access admin pages

**Solution**: 
- Verify your user has role='admin' in the database
- Check you're logged in with the correct admin account
- Restart the Flask application

### Problem: Password reset email not sending

**Solution**:
1. Verify .env file has GMAIL_ADDRESS and GMAIL_PASSWORD set
2. Check Flask console for error messages
3. Verify Gmail account has:
   - 2-Factor Authentication enabled
   - App Password generated (not regular password)
   - "Less secure apps" is not blocking (2FA should replace this)
4. Try sending a test email from Flask shell:

```python
from auth_utils import send_password_reset_email
send_password_reset_email('recipient@gmail.com', 'testuser', 'https://example.com/reset/testtoken')
```

### Problem: Database migration failed

**Solution**:
- Check if role column already exists: `DESC users;`
- Check if password_resets table already exists: `DESC password_resets;`
- Try running just the needed ALTER TABLE commands manually

### Problem: Role column exists but doesn't work

**Solution**:
- Verify all users have a role set: `SELECT username, role FROM users WHERE role IS NULL;`
- Update any NULL roles: `UPDATE users SET role='admin' WHERE role IS NULL;`
- Restart Flask application

---

## Database Schema

### Users Table (Modified)
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user'  -- NEW: 'admin' or 'user'
);
```

### Password Resets Table (New)
```sql
CREATE TABLE password_resets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP NULL,
    ip_address VARCHAR(80),
    attempt_count INT DEFAULT 1
);
```

---

## Files Modified/Created

- **Modified**:
  - `app.py` - Added authentication routes and decorators
  - `.env.example` - Gmail configuration template

- **Created**:
  - `auth_utils.py` - Authentication utilities and decorators
  - `email_config.py` - Gmail SMTP configuration
  - `setup_rbac.sql` - Database migration script
  - `forgot_password.html` - Password reset request form
  - `reset_password.html` - Password reset form
  - `user_management.html` - Admin user management dashboard
  - `.env` - Local configuration (copy from .env.example)

---

## Security Considerations

1. **Passwords**: Currently stored as plain text. Consider using `werkzeug.security` for hashing:
   ```python
   from werkzeug.security import generate_password_hash, check_password_hash
   ```

2. **Session Management**: Add session timeout after inactivity
   ```python
   @app.before_request
   def session_timeout():
       session.permanent = True
       app.permanent_session_lifetime = timedelta(minutes=30)
   ```

3. **Rate Limiting**: Implement rate limiting on password reset to prevent brute force

4. **Logging**: All actions are logged to the audit_logs table for admin review

---

## Support

For issues or questions, check the audit logs for detailed activity tracking at `/audit-log` (admin only).

---

**Setup Complete!** 🎉

Your role-based authentication system is now ready to use. Admins have full control, and regular users have view-only access as intended.
