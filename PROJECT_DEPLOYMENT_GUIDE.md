# PROJECT DEPLOYMENT GUIDE
## Barangay Information System - Complete Reference

**Last Updated**: July 2026  
**Status**: Production Ready  
**Python Version**: 3.9+  
**Database**: PostgreSQL (Render.com) / MySQL (Local Development)

---

## TABLE OF CONTENTS
1. [Project Overview](#1-project-overview)
2. [Folder Structure](#2-folder-structure)
3. [Python Version](#3-python-version)
4. [Required Packages](#4-required-packages)
5. [Environment Variables](#5-environment-variables)
6. [Database Schema](#6-database-schema)
7. [Tables](#7-tables)
8. [Relationships](#8-relationships)
9. [Startup Process](#9-startup-process)
10. [Flask Routes](#10-flask-routes)
11. [Authentication Flow](#11-authentication-flow)
12. [Analytics Flow](#12-analytics-flow)
13. [Print System](#13-print-system)
14. [Deployment Instructions](#14-deployment-instructions)
15. [Common Errors](#15-common-errors)
16. [Recovery Instructions](#16-recovery-instructions)
17. [Database Migration Guide](#17-database-migration-guide)
18. [Backup Procedure](#18-backup-procedure)

---

## 1. PROJECT OVERVIEW

### What is the Barangay Information System?

A comprehensive web-based management system for barangay (village) administration that enables:

- **Resident Management**: Add, edit, and delete household members with comprehensive data tracking
- **Household Management**: Organize residents into households with address and contact information
- **User Management**: Role-based access control (Admin/User roles)
- **Analytics Dashboard**: View statistics on resident demographics, status, and household distributions
- **Print & Reports**: Generate printable documents and audit reports
- **Authentication**: Secure login with password reset functionality
- **Audit Logging**: Track all administrative actions for compliance and accountability

### Key Features

- ✅ **Role-Based Access Control (RBAC)**: Admin (full access) vs User (read-only)
- ✅ **Email-Based Password Reset**: Secure token-based password recovery
- ✅ **100% Offline Capable**: All icons, fonts, and charts are local (no CDN dependencies)
- ✅ **Comprehensive Audit Trail**: Every action logged with user, timestamp, and details
- ✅ **Responsive Design**: Works on desktop and mobile devices
- ✅ **Real-Time Analytics**: Gender distribution, resident status, registration trends
- ✅ **Advanced Filtering**: Filter residents by gender, status, and registration month

### Technology Stack

- **Backend**: Python 3.9+ with Flask web framework
- **Database**: PostgreSQL (production) / MySQL (development)
- **Frontend**: HTML5, CSS3, JavaScript (vanilla, no frameworks)
- **Document Generation**: python-docx for Word document reports
- **Authentication**: Session-based with JWT-compatible token system
- **Deployment**: Render.com (production) / Local/Docker (development)

---

## 2. FOLDER STRUCTURE

```
barangay_system/
├── app.py                              # Main Flask application (2800+ lines)
├── auth_utils.py                       # Authentication & authorization utilities
├── email_config.py                     # Gmail SMTP configuration
├── database.sql                        # SQL schema definition (MySQL)
├── setup_rbac.sql                      # Role-based access control setup
├── setup_signup.sql                    # User signup table schema
├── setup_db.py                         # Database initialization script
├── init_db_render.py                   # PostgreSQL initialization for Render.com
├── requirements.txt                    # Python package dependencies
├── Procfile                            # Heroku/Render.com deployment config
├── .env.example                        # Environment variables template
│
├── static/                             # Static assets (served to browser)
│   ├── css/
│   │   └── style.css                   # Main stylesheet (offline-friendly)
│   ├── fonts/
│   │   └── inter-fonts.css             # Inter font definitions (no CDN)
│   ├── icons/
│   │   └── lucide-icons.js             # SVG icon library (no CDN)
│   ├── images/                         # Project images
│   └── js/
│       ├── script.js                   # Main frontend logic
│       └── simple-chart.js             # Chart rendering library
│
└── templates/                          # HTML templates (Jinja2)
    ├── base.html                       # Base template (navigation, layout)
    ├── user_base.html                  # User dashboard base
    ├── login.html                      # Login page
    ├── signup.html                     # New user registration
    ├── forgot_password.html            # Password reset request
    ├── reset_password.html             # Password reset form
    ├── index.html                      # Admin home/dashboard
    ├── user_home.html                  # User home page
    ├── user_profile.html               # User profile page
    ├── add_household.html              # Add household form
    ├── edit_member.html                # Edit resident form
    ├── view_members.html               # List all residents
    ├── view_households.html            # List all households
    ├── household_members.html          # View members in household
    ├── information.html                # System information page
    ├── print_member.html               # Print resident details
    ├── print_reports.html              # Print system reports
    ├── audit_log.html                  # Audit trail viewer
    ├── user_management.html            # Admin user management panel
    ├── analytics.html                  # Analytics dashboard
    └── search.html                     # Search page
```

### File Descriptions

| File | Purpose | Lines |
|------|---------|-------|
| **app.py** | Core Flask application with all routes | 2800+ |
| **auth_utils.py** | Authentication decorators, email sending | 100+ |
| **email_config.py** | Gmail SMTP configuration | 15 |
| **requirements.txt** | Python dependencies | 15+ |
| **static/js/script.js** | Frontend logic, API calls, interactivity | 500+ |
| **static/js/simple-chart.js** | Pure JS charting library | 200+ |
| **static/css/style.css** | Responsive design, offline fonts | 1000+ |
| **templates/*.html** | Jinja2 templates for pages | 50-150 each |

---

## 3. PYTHON VERSION

### Minimum Requirements

- **Python**: 3.9 or higher
- **Recommended**: Python 3.11 or latest stable

### Check Your Python Version

```bash
# On Windows PowerShell
python --version

# On macOS/Linux
python3 --version
```

### Expected Output

```
Python 3.9.x or higher
```

### If You Need to Install Python

1. **Windows**: Download from [python.org](https://www.python.org/downloads/)
   - Enable "Add Python to PATH" during installation
   - Verify: Open new PowerShell and run `python --version`

2. **macOS**: Use Homebrew
   ```bash
   brew install python@3.11
   ```

3. **Linux**: Use apt/yum
   ```bash
   sudo apt install python3.11 python3-pip
   ```

### Virtual Environment (Highly Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows PowerShell
.\venv\Scripts\Activate.ps1

# Activate on macOS/Linux
source venv/bin/activate

# Should see (venv) prefix in terminal
(venv) C:\path\to\barangay_system>
```

---

## 4. REQUIRED PACKAGES

### Dependencies List

All required Python packages are specified in [requirements.txt](requirements.txt):

```
Flask==2.3.0
psycopg2-binary==2.9.6
python-docx==0.8.11
PyMySQL==1.0.2
gunicorn==20.1.0
blinker==1.6.2
click==8.1.3
Werkzeug==2.3.0
Jinja2==3.1.2
```

### Installation

```bash
# With virtual environment activated
pip install -r requirements.txt

# Verify installation
pip list
```

### Package Descriptions

| Package | Purpose | Used For |
|---------|---------|----------|
| **Flask** | Web framework | Route handling, templates, sessions |
| **psycopg2-binary** | PostgreSQL adapter | Database connections (production) |
| **PyMySQL** | MySQL adapter | Database connections (development) |
| **python-docx** | Document generation | Creating Word (.docx) reports |
| **gunicorn** | WSGI server | Production deployment |
| **blinker** | Signal support | Flask signals |
| **Werkzeug** | Utilities | Request/response handling |

### Troubleshooting Package Installation

```bash
# If pip is slow, use faster mirror
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

# Force reinstall
pip install --force-reinstall -r requirements.txt

# Install specific version
pip install Flask==2.3.0
```

---

## 5. ENVIRONMENT VARIABLES

### Purpose

Environment variables store sensitive configuration outside of code, making the system secure for deployment.

### Required Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL/MySQL connection string | `postgresql://user:pass@localhost/db` |
| `FLASK_ENV` | Development or production | `production` or `development` |
| `SECRET_KEY` | Flask session encryption key | Generate with `secrets.token_urlsafe(32)` |
| `GMAIL_ADDRESS` | Gmail account for sending emails | `your.email@gmail.com` |
| `GMAIL_PASSWORD` | Gmail App Password (NOT regular password) | 16-char code from Google Account |

### Setting Up Environment Variables

#### Option 1: Using .env File (Local Development)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values:
   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/barangay_db
   FLASK_ENV=development
   SECRET_KEY=your_secret_key_here
   GMAIL_ADDRESS=your.email@gmail.com
   GMAIL_PASSWORD=abcd efgh ijkl mnop
   ```

3. Install python-dotenv:
   ```bash
   pip install python-dotenv
   ```

4. Load in app.py (already done):
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

#### Option 2: System Environment Variables (Windows)

```powershell
# Set permanent environment variables
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/barangay_db"
$env:FLASK_ENV = "production"
$env:SECRET_KEY = "your_secret_key_here"
$env:GMAIL_ADDRESS = "your.email@gmail.com"
$env:GMAIL_PASSWORD = "abcd efgh ijkl mnop"

# Verify
echo $env:DATABASE_URL
```

#### Option 3: Render.com Dashboard (Production)

1. Go to Render.com > Your Service
2. Click "Environment"
3. Add each variable:
   - Key: `DATABASE_URL`
   - Value: Your PostgreSQL URL
4. Save and redeploy

### Gmail App Password Setup

1. Enable 2-Factor Authentication on Google Account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Select "Mail" and "Windows PC" (or your device)
4. Click "Generate"
5. Copy 16-character password (ignore spaces)
6. Set `GMAIL_PASSWORD` to this value

### Secret Key Generation

```python
# In Python REPL
import secrets
secrets.token_urlsafe(32)
# Output: 'a1b2c3d4e5f6...'
```

---

## 6. DATABASE SCHEMA

### Database Systems Supported

- **Production**: PostgreSQL (via Render.com)
- **Development**: MySQL 5.7+ or PostgreSQL local

### Schema Initialization

The database schema is created automatically when:

1. Application starts (Flask initializes tables)
2. Admin account is created (if not exists)
3. Migrations run (for schema updates)

### Core Schema Components

```sql
-- Authentication & Authorization
users              -- Login credentials, roles, status
password_resets    -- Password reset tokens
audit_logs         -- Activity tracking

-- Data Management
household          -- Household information
residents          -- Resident/member details (with status tracking)
email_logs         -- Email delivery tracking (optional)
```

### Schema Initialization Methods

#### Method 1: Automatic (Recommended)

```bash
# Start Flask app - schema auto-creates
python app.py

# Navigate to http://localhost:5000/init-db
# Click "Initialize Database"
```

#### Method 2: Manual SQL

```bash
# For PostgreSQL
psql -U username -d barangay_db -f database.sql

# For MySQL
mysql -u root -p barangay_db < database.sql
```

#### Method 3: Python Script

```bash
# Run setup script
python setup_db.py

# For Render.com PostgreSQL
python init_db_render.py
```

---

## 7. TABLES

### Core Tables Overview

#### 1. **users**
Stores user accounts and authentication data.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',           -- 'admin' or 'user'
    status VARCHAR(20) DEFAULT 'approved',     -- 'approved', 'pending', 'rejected'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

| Column | Type | Purpose |
|--------|------|---------|
| `id` | SERIAL | Unique user identifier |
| `username` | VARCHAR(100) | Login name (unique) |
| `email` | VARCHAR(100) | Email address (unique) |
| `password` | VARCHAR(255) | Hashed password |
| `role` | VARCHAR(20) | 'admin' = full access, 'user' = read-only |
| `status` | VARCHAR(20) | 'approved' = active, 'pending' = awaiting review |
| `created_at` | TIMESTAMP | Account creation date |
| `updated_at` | TIMESTAMP | Last update date |

#### 2. **household**
Stores household/family unit information.

```sql
CREATE TABLE household (
    id INT PRIMARY KEY AUTO_INCREMENT,
    surname VARCHAR(50) NOT NULL,
    firstname VARCHAR(50) NOT NULL,
    middlename VARCHAR(50),
    house_number VARCHAR(20),
    address VARCHAR(255),
    contact_number VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT | Unique household identifier |
| `surname` | VARCHAR(50) | Head of household surname |
| `firstname` | VARCHAR(50) | Head of household first name |
| `middlename` | VARCHAR(50) | Head of household middle name |
| `house_number` | VARCHAR(20) | House/Unit number |
| `address` | VARCHAR(255) | Full street address |
| `contact_number` | VARCHAR(20) | Phone number |
| `created_at` | TIMESTAMP | Record creation date |
| `updated_at` | TIMESTAMP | Record update date |

#### 3. **residents** (Also referred to as "members")
Stores individual resident/household member information.

```sql
CREATE TABLE residents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    household_id INT NOT NULL,
    surname VARCHAR(50) NOT NULL,
    firstname VARCHAR(50) NOT NULL,
    middlename VARCHAR(50),
    age INT,
    gender VARCHAR(10),                         -- 'Male', 'Female', 'Other'
    civil_status VARCHAR(20),                   -- 'Single', 'Married', 'Widowed', etc.
    occupation VARCHAR(100),
    contact_number VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',        -- 'active', 'deceased', 'transferred'
    deceased_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (household_id) REFERENCES household(id) ON DELETE CASCADE
);
```

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT | Unique resident identifier |
| `household_id` | INT | Links to household |
| `surname` | VARCHAR(50) | Last name |
| `firstname` | VARCHAR(50) | First name |
| `middlename` | VARCHAR(50) | Middle name |
| `age` | INT | Age in years |
| `gender` | VARCHAR(10) | 'Male', 'Female', 'Other' |
| `civil_status` | VARCHAR(20) | Marital status |
| `occupation` | VARCHAR(100) | Job/profession |
| `contact_number` | VARCHAR(20) | Phone number |
| `status` | VARCHAR(20) | 'active', 'deceased', 'transferred' |
| `deceased_date` | DATE | Date of death (if deceased) |
| `notes` | TEXT | Additional information |
| `created_at` | TIMESTAMP | Record creation date |
| `updated_at` | TIMESTAMP | Record update date |

#### 4. **password_resets**
Stores password reset tokens for secure password recovery.

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
    attempt_count INT DEFAULT 1,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);
```

#### 5. **audit_logs**
Tracks all administrative actions for compliance and accountability.

```sql
CREATE TABLE audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100),
    username VARCHAR(100) NOT NULL,
    action_type VARCHAR(50) NOT NULL,           -- 'ADD', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT'
    target_type VARCHAR(100) DEFAULT 'System',  -- 'Resident', 'Household', 'User'
    target_id VARCHAR(100) DEFAULT 'N/A',       -- ID of affected record
    old_value TEXT,                             -- JSON snapshot before change
    new_value TEXT,                             -- JSON snapshot after change
    status VARCHAR(30) DEFAULT 'SUCCESS',       -- 'SUCCESS', 'FAILED'
    ip_address VARCHAR(80),                     -- Request IP address
    user_agent VARCHAR(255),                    -- Browser user agent
    details TEXT NOT NULL,                      -- Human-readable description
    household_context VARCHAR(150) DEFAULT 'N/A', -- Household info for context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. RELATIONSHIPS

### Entity Relationship Diagram

```
┌─────────────┐
│    users    │
│ (id, role)  │
└─────────────┘
        │
        │ ONE-TO-MANY (user performs)
        │
┌─────────────────────┐
│    audit_logs       │
│ (username, action)  │
└─────────────────────┘


┌─────────────────┐
│   household     │
│  (id, address)  │
└─────────────────┘
        │
        │ ONE-TO-MANY
        │
┌─────────────────────────┐
│     residents           │
│ (household_id, status)  │
└─────────────────────────┘


┌──────────────┐
│    users     │
│ (username)   │
└──────────────┘
       │
       │ ONE-TO-MANY
       │
┌─────────────────────┐
│  password_resets    │
│ (username, token)   │
└─────────────────────┘
```

### Relationship Descriptions

#### users ↔ audit_logs (ONE-TO-MANY)
- One user can perform many actions
- Each audit log entry records who performed an action
- CASCADE DELETE: User deletion cascades (historical)

#### household ↔ residents (ONE-TO-MANY)
- One household contains many residents
- Each resident belongs to exactly one household
- CASCADE DELETE: Household deletion removes all residents

#### users ↔ password_resets (ONE-TO-MANY)
- One user can have multiple password reset requests
- Each token is unique and expires after 1 hour
- CASCADE DELETE: User deletion removes reset tokens

### Data Integrity Constraints

1. **UNIQUE Constraints**: username, email (no duplicates)
2. **NOT NULL Constraints**: username, password, role, status
3. **FOREIGN KEY Constraints**: household_id must exist
4. **DEFAULT VALUES**: role='user', status='approved'
5. **CHECK Constraints**: role IN ('admin', 'user')

---

## 9. STARTUP PROCESS

### Pre-Startup Checklist

- [ ] Python 3.9+ installed (`python --version`)
- [ ] Virtual environment created and activated (`venv` folder exists)
- [ ] Dependencies installed (`pip list` shows Flask, psycopg2, etc.)
- [ ] Database connection configured (DATABASE_URL set)
- [ ] Environment variables loaded (.env file exists)
- [ ] Gmail configured (GMAIL_ADDRESS and GMAIL_PASSWORD set)

### Step-by-Step Startup

#### Step 1: Activate Virtual Environment

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Should see (venv) prefix
(venv) C:\path\to\barangay_system>
```

#### Step 2: Verify Environment Variables

```powershell
# Check if variables are set
echo $env:DATABASE_URL
echo $env:GMAIL_ADDRESS

# Should display values, not blank
```

#### Step 3: Start Flask Development Server

```bash
python app.py
```

#### Step 4: Check Startup Output

```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
 * Restarting with reloader
 * Debugger is active!
```

#### Step 5: Access Application

Open browser to: **http://localhost:5000**

Should see login page.

### First-Time Setup After Startup

1. Navigate to **http://localhost:5000/init-db**
2. Click "Initialize Database" button
3. Wait for "DB + ADMIN CREATED" message
4. Go to **http://localhost:5000/login**
5. Log in with credentials:
   - **Username**: `Ch4kl3t`
   - **Password**: `l0r41n322`

### Startup Troubleshooting

| Issue | Solution |
|-------|----------|
| "ModuleNotFoundError: No module named 'flask'" | Run `pip install -r requirements.txt` |
| "DATABASE_URL not found" | Set environment variable or use .env file |
| "Address already in use" | Change port: `python app.py --port 5001` |
| "Permission denied" on .env | Delete `.env` and create new one |
| "SMTP authentication failed" | Verify Gmail App Password (not regular password) |

### Shutdown

```bash
# Press Ctrl+C in terminal
^C
 * Shutting down...
 * Exiting
```

---

## 10. FLASK ROUTES

### Route Categories

#### Public Routes (No Login Required)

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Redirect to login |
| `/login` | GET | Display login page |
| `/login` | POST | Process login credentials |
| `/signup` | GET | Display registration page |
| `/signup` | POST | Create new user account |
| `/forgot_password` | GET | Password reset request page |
| `/forgot_password` | POST | Send reset email |
| `/reset_password/<token>` | GET | Display reset form |
| `/reset_password/<token>` | POST | Process password reset |

#### Admin Routes (role='admin' Required)

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Admin dashboard |
| `/add_member` | GET | Display add resident form |
| `/add_member` | POST | Create new resident |
| `/edit_member/<id>` | GET | Display edit resident form |
| `/edit_member/<id>` | POST | Update resident |
| `/delete_member/<id>` | GET | Delete resident |
| `/add_household` | GET | Display add household form |
| `/add_household` | POST | Create new household |
| `/delete_household/<id>` | GET | Delete household |
| `/audit-log` | GET | View audit trail |
| `/user-management` | GET | User management page |
| `/print_member/<id>` | GET | Print resident details |
| `/print_reports` | GET | Print system reports |

#### User Routes (Authenticated)

| Route | Method | Purpose |
|-------|--------|---------|
| `/user-home` | GET | User dashboard (read-only) |
| `/user-profile` | GET | View own profile |
| `/user-profile` | POST | Update own profile |
| `/view_members` | GET | List all residents |
| `/view_households` | GET | List all households |
| `/household_members/<id>` | GET | View household members |
| `/search` | GET | Search residents/households |
| `/information` | GET | System information |
| `/analytics` | GET | Analytics dashboard |
| `/logout` | GET | End session and redirect to login |
| `/change_password` | GET | Change password page |
| `/change_password` | POST | Process password change |

#### API Routes (JSON Responses)

| Route | Method | Purpose | Auth |
|-------|--------|---------|------|
| `/api/dashboard` | GET | Analytics data (charts, stats) | User |
| `/api/search_residents` | GET | Search residents by keyword | User |
| `/search_households` | GET | Search households by address | User |
| `/search_members` | GET | Search household members | User |
| `/api/user/role` | GET | Get current user role | User |
| `/api/user/role` | POST | Update user role (admin only) | Admin |
| `/api/user/status/<user_id>/<action>` | GET | Approve/reject signup | Admin |
| `/api/preview/residents` | GET | Preview resident list | Admin |
| `/api/preview/households` | GET | Preview household list | Admin |
| `/api/preview/audit` | GET | Preview audit log | Admin |
| `/api/pending-signups-count` | GET | Count pending registrations | Admin |
| `/init-db` | GET | Initialize database | None |

### Route Protection

```python
# Public - no login required
@app.route('/login', methods=['GET', 'POST'])
def login():
    # No decorator needed
    pass

# Protected - login required
@app.route('/user-home')
@require_role('admin', 'user')  # Either role OK
def user_home():
    pass

# Admin only
@app.route('/add_member', methods=['GET', 'POST'])
@require_role('admin')  # Admin only
def add_member():
    pass
```

---

## 11. AUTHENTICATION FLOW

### User Login Flow

```
┌─────────────────────────────────────────┐
│  User navigates to /login               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Display login form                     │
│  - Username field                       │
│  - Password field                       │
│  - "Forgot Password?" link              │
│  - Submit button                        │
└──────────────┬──────────────────────────┘
               │ User enters credentials
               ▼
┌─────────────────────────────────────────┐
│  Form POST to /login                    │
│  - Validate CSRF token                  │
│  - Query users table for username       │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
   User found    User not found
   AND password  OR password
   matches       doesn't match
        │             │
        ▼             ▼
   ✓ Success     ✗ Failed
        │             │
        ▼             ▼
   Create session  Flash error
   Set cookies     Redirect to /login
   Store role
        │
        ▼
   ┌──────────────────┐
   │ Redirect based   │
   │ on role:         │
   │                  │
   │ role='admin' →   │
   │   /index (home)  │
   │                  │
   │ role='user' →    │
   │   /user-home     │
   └──────────────────┘
```

### Session Management

```python
# When user logs in successfully:
session['username'] = 'Ch4kl3t'
session['user_id'] = 1
session['role'] = 'admin'
session.permanent = True
app.permanent_session_lifetime = timedelta(days=7)

# Check if user is logged in:
if 'username' in session:
    current_user = session['username']
    current_role = session['role']

# On logout:
session.clear()
```

### Password Reset Flow

```
┌──────────────────────────────────┐
│ User clicks "Forgot Password?"   │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────────────┐
│ Display form requesting username         │
└────────────┬─────────────────────────────┘
             │ User enters username
             ▼
┌──────────────────────────────────────────┐
│ POST /forgot_password                    │
│ - Query users for username               │
│ - Generate secure token (32 chars)       │
│ - Store in password_resets table         │
│ - Set expires_at = now + 1 hour          │
└────────────┬─────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────┐
│ Send email via Gmail SMTP                │
│ Link: /reset_password/<token>            │
│ Message: Click link within 1 hour        │
└────────────┬─────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────┐
│ User clicks link in email                │
│ Browser navigates to:                    │
│ /reset_password/<token>                  │
└────────────┬─────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────┐
│ Validate token:                          │
│ - Check token exists                     │
│ - Check not expired                      │
│ - Check not already used                 │
└────────────┬─────────────────────────────┘
             │
        ┌────┴─────┐
        ▼          ▼
    Valid       Invalid/Expired
        │          │
        ▼          ▼
  Display      Redirect to
  new password /forgot_password
  form         with error message
        │
        ▼
   User submits
   new password
        │
        ▼
  POST /reset_password/<token>
   - Validate password (8+ chars)
   - Hash new password
   - Update users table
   - Mark token as used
   - Redirect to /login
```

### Role-Based Access Control

```python
# Three roles:

# ADMIN - Full Access
- Add/edit/delete residents
- Add/edit/delete households
- View audit logs
- Manage users
- Generate reports
- View analytics

# USER - Read-Only Access
- View residents list
- View households list
- Search residents
- View analytics (read-only)
- Change own password

# UNAUTHENTICATED - No Access
- Login required for all except:
  - /login
  - /signup
  - /forgot_password
  - /reset_password/<token>
```

---

## 12. ANALYTICS FLOW

### Analytics Dashboard (/analytics)

```
┌──────────────────────────────────┐
│  User navigates to /analytics    │
│  or clicks Analytics in sidebar  │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│  Load analytics.html template                │
│  - Display filter controls                   │
│  - Initialize chart containers               │
│  - Load simple-chart.js library              │
└────────────┬─────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│  JavaScript: Call loadDashboard()            │
│  - GET /api/dashboard (no filters)           │
│  - Parse JSON response                       │
│  - Render 4 charts:                          │
│    1. Gender distribution (doughnut)         │
│    2. Resident status (doughnut)             │
│    3. Registration trends (bar)              │
│    4. Top households (bar)                   │
│  - Display resident details table            │
└────────────┬─────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│  Backend: GET /api/dashboard                 │
│  1. Connect to database                      │
│  2. Execute queries:                         │
│     - Count residents by gender              │
│     - Count residents by status              │
│     - Count monthly registrations            │
│     - Count members per household             │
│     - Get resident details                   │
│  3. Return JSON:                             │
│     {                                        │
│       stats: {...},                          │
│       genderData: [...],                     │
│       statusData: [...],                     │
│       monthlyData: [...],                    │
│       householdData: [...],                  │
│       residents: [...]                       │
│     }                                        │
└────────────┬─────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│  Frontend: User selects filters              │
│  - Gender: Male/Female/All                   │
│  - Status: Active/Deceased/All               │
│  - Month: January/February/.../All           │
│  - Click "Apply Filters"                     │
└────────────┬─────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│  JavaScript: Call loadDashboard(gender,      │
│  status, month)                              │
│  - GET /api/dashboard?gender=Male&...        │
│  - Parse filtered response                   │
│  - Re-render all charts with new data        │
│  - Update resident table                     │
└────────────┬─────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│  Backend: GET /api/dashboard with params     │
│  1. Build WHERE clause from filters:         │
│     - WHERE gender = ? (if gender filter)    │
│     - AND status = ? (if status filter)      │
│     - AND MONTH(created_at) = ? (if month)   │
│  2. Execute filtered queries                 │
│  3. Return filtered JSON                     │
└────────────┬─────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│  Charts updated with filtered data           │
│  Residents table filtered and re-rendered    │
└──────────────────────────────────────────────┘
```

### Supported Filters

| Filter | Values | Purpose |
|--------|--------|---------|
| **Gender** | All, Male, Female, Other | Filter residents by gender |
| **Status** | All, Active, Deceased | Filter by active/deceased status |
| **Month** | Jan-Dec | Filter by registration month |

### Chart Types

1. **Gender Distribution** (Doughnut Chart)
   - Shows count of residents per gender
   - Colors: Blue (Male), Pink (Female), Gray (Other)

2. **Resident Status** (Doughnut Chart)
   - Shows count of active vs deceased residents
   - Colors: Green (Active), Red (Deceased)

3. **Monthly Registration Trends** (Bar Chart)
   - Shows registrations per month
   - Helps identify seasonal patterns

4. **Top Households by Members** (Bar Chart)
   - Shows households with most residents
   - Top 10 displayed

### Data Flow for Charts

```
GET /api/dashboard?gender=Male&status=Active
                ↓
SQL Query: SELECT gender, COUNT(*) 
           FROM residents 
           WHERE gender='Male' AND status='Active'
           GROUP BY gender
                ↓
Results: { male: 150, female: 0, other: 0 }
                ↓
JSON Response:
{
  "stats": { "total_residents": 150, ... },
  "genderData": [
    { label: "Male", value: 150 },
    { label: "Female", value: 0 },
    { label: "Other", value: 0 }
  ],
  ...
}
                ↓
Frontend renders chart
```

---

## 13. PRINT SYSTEM

### Available Print Functions

#### 1. Print Individual Resident (/print_member/<id>)

**Purpose**: Generate printable document for single resident

```
Input:
- Resident ID (from URL)

Output:
- Word document (.docx)
- Filename: Resident_[name].docx

Contents:
┌─────────────────────────────────┐
│   BARANGAY INFORMATION SYSTEM    │
│    Resident Information Form     │
│                                  │
│ Name: [First Middle Last]        │
│ Age: [age]                       │
│ Gender: [gender]                 │
│ Civil Status: [status]           │
│ Occupation: [occupation]         │
│ Contact: [number]                │
│ Status: [active/deceased]        │
│ Household: [household address]   │
│ Date Printed: [date/time]        │
└─────────────────────────────────┘
```

#### 2. Print System Reports (/print_reports)

**Purpose**: Generate comprehensive system reports

```
Available Reports:

1. Resident Summary Report
   - Total residents count
   - Gender distribution
   - Status breakdown
   - Top households
   - Registration timeline

2. Household Summary Report
   - Total households count
   - Average members per household
   - Household listing with details

3. Admin Activity Report
   - All users
   - User roles
   - Last login dates
   - Account status

4. Audit Trail Report
   - Recent actions (50 entries)
   - User, action type, timestamp
   - Changes made
```

### Print System API

#### Generate Print Preview

```bash
GET /api/preview/residents
GET /api/preview/households
GET /api/preview/audit
```

Response: JSON data for preview tables

#### Download Actual Document

```bash
GET /print_member/<id>
GET /print_reports
```

Response: .docx file (Word document)

### Print Settings

- **Paper Size**: A4 (8.27" × 11.69")
- **Orientation**: Portrait (default) / Landscape (for tables)
- **Margins**: 1" on all sides
- **Font**: Calibri 11pt (body), 14pt (headers)
- **Page Numbers**: Enabled
- **Header/Footer**: Barangay name and date

### Customizing Print Templates

Edit `app.py` routes: `/print_member/<id>` and `/print_reports`

```python
@app.route('/print_member/<int:member_id>')
@require_role('admin')
def print_member(member_id):
    # ... fetch resident data ...
    doc = Document()
    
    # Add title
    title = doc.add_heading('Resident Information', 0)
    
    # Add details
    doc.add_paragraph(f"Name: {resident['firstname']} {resident['lastname']}")
    
    # ... add more content ...
    
    # Return as attachment
    output = BytesIO()
    doc.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=f"Resident_{resident['firstname']}.docx"
    )
```

---

## 14. DEPLOYMENT INSTRUCTIONS

### Deployment Targets

1. **Local Development**: Python + Flask development server
2. **Production**: Render.com + PostgreSQL
3. **Docker**: Containerized deployment
4. **Traditional Server**: Ubuntu/CentOS with Gunicorn

### Option 1: Render.com Deployment (Recommended)

#### Prerequisites

- Render.com account (free tier available)
- GitHub repository (fork or push project)
- PostgreSQL database (Render provides free tier)
- Gmail App Password

#### Step 1: Create PostgreSQL Database

1. Log in to Render.com
2. Click "New +"
3. Select "PostgreSQL"
4. Name: `barangay-db`
5. Region: Choose closest to you
6. Create database
7. Copy connection string (looks like: `postgresql://user:pass@host:port/db`)

#### Step 2: Create Web Service

1. Click "New +"
2. Select "Web Service"
3. Connect GitHub repository
4. Name: `barangay-system`
5. Region: Same as database
6. Runtime: Python 3.11
7. Build command: `pip install -r requirements.txt`
8. Start command: `gunicorn app:app`

#### Step 3: Set Environment Variables

In Render dashboard:
1. Go to Web Service settings
2. Click "Environment"
3. Add variables:
   ```
   DATABASE_URL = postgresql://user:pass@host:port/db
   FLASK_ENV = production
   SECRET_KEY = [generate with secrets.token_urlsafe(32)]
   GMAIL_ADDRESS = your.email@gmail.com
   GMAIL_PASSWORD = your-app-password-16-chars
   ```

#### Step 4: Deploy

1. Click "Deploy"
2. Wait for build to complete (~2-3 minutes)
3. View logs for errors
4. Access at: `https://barangay-system.onrender.com`
5. Initialize database: Visit `/init-db`

#### Render.com Monitoring

```bash
# View logs
Click "Logs" in Render dashboard

# Monitor disk usage
Render provides usage dashboard

# Health checks
Render auto-restarts failed services
```

### Option 2: Local Server Deployment (Windows/Mac/Linux)

#### Prerequisites

- Python 3.9+
- PostgreSQL 12+ (or MySQL 5.7+)
- Git

#### Setup Steps

```bash
# 1. Clone repository
git clone <your-repo-url>
cd barangay_system

# 2. Create virtual environment
python -m venv venv

# 3. Activate venv
# On Windows:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file
cp .env.example .env
# Edit .env with your database URL and Gmail credentials

# 6. Initialize database
python setup_db.py

# 7. Run application
python app.py
```

#### Running as Background Service

**Windows - Task Scheduler**

```powershell
# Create batch file: run_app.bat
@echo off
cd C:\path\to\barangay_system
.\venv\Scripts\python.exe app.py

# Schedule via Task Scheduler
# - New Task
# - Action: Run run_app.bat
# - Trigger: On system startup
```

**Linux/Mac - Systemd**

```bash
# Create service file: /etc/systemd/system/barangay.service
[Unit]
Description=Barangay System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/barangay_system
ExecStart=/var/www/barangay_system/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable barangay
sudo systemctl start barangay
sudo systemctl status barangay
```

### Option 3: Docker Deployment

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

#### Docker Compose

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/barangay_db
      FLASK_ENV: production
      SECRET_KEY: ${SECRET_KEY}
      GMAIL_ADDRESS: ${GMAIL_ADDRESS}
      GMAIL_PASSWORD: ${GMAIL_PASSWORD}
    depends_on:
      - db

  db:
    image: postgres:13
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: barangay_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### Deploy with Docker

```bash
docker-compose up -d
```

### Option 4: Traditional VPS/Cloud Server

#### Ubuntu 20.04+ Setup

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python and PostgreSQL
sudo apt install -y python3.11 python3-pip postgresql postgresql-contrib nginx

# 3. Create application user
sudo useradd -m barangay
sudo su - barangay

# 4. Clone repository
git clone <your-repo-url>
cd barangay_system

# 5. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Configure PostgreSQL
sudo -u postgres createdb barangay_db
sudo -u postgres psql -d barangay_db -f database.sql

# 7. Create systemd service (see above)
sudo nano /etc/systemd/system/barangay.service

# 8. Configure Nginx as reverse proxy
sudo nano /etc/nginx/sites-available/barangay

# 9. Enable and start services
sudo systemctl restart nginx
sudo systemctl start barangay
```

#### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/barangay/barangay_system/static;
    }
}
```

#### SSL Certificate (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
# Auto-renewal enabled by default
```

---

## 15. COMMON ERRORS

### Error 1: ModuleNotFoundError: No module named 'flask'

**Cause**: Flask not installed or wrong Python environment

**Solution**:
```bash
# Activate virtual environment first
.\venv\Scripts\Activate.ps1

# Then install
pip install flask
pip install -r requirements.txt
```

### Error 2: DATABASE_URL not found

**Cause**: Environment variable not set

**Solution**:
```bash
# Option 1: Set environment variable
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/barangay_db"

# Option 2: Create .env file
echo 'DATABASE_URL=postgresql://user:password@localhost:5432/barangay_db' > .env

# Option 3: Check if set
echo $env:DATABASE_URL
```

### Error 3: Address already in use (port 5000)

**Cause**: Another service using port 5000

**Solution**:
```bash
# Option 1: Change Flask port
python app.py -p 5001

# Option 2: Find and kill process using port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Option 3: Use different port in app.py
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
```

### Error 4: SMTP Authentication Failed (Gmail)

**Cause**: Wrong Gmail password or 2FA not enabled

**Solution**:
1. Enable 2-Factor Authentication on Google Account
2. Get App Password: https://myaccount.google.com/apppasswords
3. Use 16-character app password (NOT regular Gmail password)
4. Update .env:
   ```
   GMAIL_PASSWORD=abcd efgh ijkl mnop
   ```
5. Restart Flask app

### Error 5: psycopg2.OperationalError: could not connect to server

**Cause**: Database server not running or incorrect connection string

**Solution**:
```bash
# Check if PostgreSQL is running
sudo service postgresql status

# Or for Windows
pg_isready -h localhost -p 5432

# Test connection string
psql "postgresql://user:password@localhost:5432/barangay_db"

# If connection string wrong:
# Format: postgresql://username:password@host:port/database
```

### Error 6: No such file or directory: '.env'

**Cause**: .env file not in project root

**Solution**:
```bash
# Create .env file
cp .env.example .env

# Or manually create
New-Item -Path .\.env -ItemType File
# Then edit with your values
```

### Error 7: 403 Forbidden - You do not have permission

**Cause**: User role is 'user' but trying to access admin route

**Solution**:
```bash
# Log in as admin user (role='admin')
# Or ask administrator to grant admin role

# Check current role:
SELECT username, role FROM users WHERE username='your_username';

# Update role if needed:
UPDATE users SET role='admin' WHERE username='your_username';
```

### Error 8: Could not establish a new connection - Connection pool is exhausted

**Cause**: Database connections not being closed properly

**Solution**:
```bash
# This is a known bug fixed in latest version
# Update app.py from GitHub repository

# Or manually:
# Ensure all database operations are wrapped in try-finally
try:
    conn, cur = get_db()
    # ... your code ...
finally:
    if conn:
        conn.close()
```

### Error 9: Password reset email not received

**Cause**: Gmail credentials wrong or email service down

**Solution**:
1. Verify GMAIL_ADDRESS and GMAIL_PASSWORD in .env
2. Check Gmail App Passwords: https://myaccount.google.com/apppasswords
3. Verify Gmail account allows less secure apps (if using regular password)
4. Check spam folder
5. Try logging in to Gmail - if can't, use app password instead

### Error 10: Cannot find template file

**Cause**: Template file missing or path incorrect

**Solution**:
```bash
# Verify templates folder exists
ls -la templates/

# Check template filename in app.py
# Make sure it matches exactly (case-sensitive on Linux)

# Verify route exists
grep "def add_member" app.py
```

---

## 16. RECOVERY INSTRUCTIONS

### Recovery Scenario 1: User Lockout (Forgot Password)

**Symptoms**: User cannot log in

**Recovery Steps**:

1. User goes to login page
2. Clicks "Forgot Password?"
3. Enters username
4. System sends email with reset link
5. User clicks link in email
6. User sets new password
7. User can now log in

**If email not received**:
- Check spam folder
- Verify email address in system
- Admin can manually reset: (See Scenario 2)

### Recovery Scenario 2: Admin Password Reset (Manual)

**Symptoms**: Admin account locked, email not working

**Recovery Steps** (for system administrator):

```bash
# 1. Connect to database
psql -U postgres -d barangay_db

# 2. Update password directly
UPDATE users 
SET password='newhashedpassword' 
WHERE username='Ch4kl3t';

# Or generate new password hash
python3 -c "import hashlib; print(hashlib.sha256('newpassword'.encode()).hexdigest())"

# 3. Test login
# Go to http://localhost:5000/login
# Username: Ch4kl3t
# Password: newpassword
```

### Recovery Scenario 3: Database Corruption

**Symptoms**: Unusual data, missing records, query errors

**Recovery Steps**:

```bash
# 1. Create backup of current database
pg_dump barangay_db > backup_corrupted.sql

# 2. Drop corrupted tables (CAREFUL!)
psql -d barangay_db -c "DROP TABLE IF EXISTS residents CASCADE;"
psql -d barangay_db -c "DROP TABLE IF EXISTS household CASCADE;"

# 3. Recreate schema
psql -d barangay_db -f database.sql

# 4. Restore from backup (if available)
psql -d barangay_db -f backup_clean.sql
```

### Recovery Scenario 4: Lost Data (Accidental Deletion)

**Symptoms**: Resident/household records accidentally deleted

**Recovery Steps**:

1. **Use Audit Log to verify deletion**:
   ```sql
   SELECT * FROM audit_logs 
   WHERE action_type='DELETE' 
   ORDER BY created_at DESC 
   LIMIT 10;
   ```

2. **Restore from backup**:
   ```bash
   # Last backup
   psql -d barangay_db -f backup_latest.sql
   ```

3. **Manual re-entry**:
   - Log in as admin
   - Go to "Add Resident" / "Add Household"
   - Re-enter data

### Recovery Scenario 5: Connection Pool Exhaustion

**Symptoms**: 
- "Connection pool is exhausted" errors
- 500 errors on random endpoints
- Gradually increasing response times

**Recovery Steps**:

```bash
# 1. Restart Flask application
# Ctrl+C in terminal
# python app.py

# 2. If problem persists, check active connections
psql -d barangay_db -c "SELECT * FROM pg_stat_activity;"

# 3. Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' AND query_start < now() - interval '10 minutes';
```

### Recovery Scenario 6: Audit Log Too Large

**Symptoms**: 
- Audit log page slow to load
- Database disk space getting full
- Slow backup times

**Recovery Steps**:

```bash
# 1. Archive old logs
CREATE TABLE audit_logs_archive AS 
SELECT * FROM audit_logs 
WHERE created_at < now() - interval '1 year';

# 2. Delete old logs
DELETE FROM audit_logs 
WHERE created_at < now() - interval '1 year';

# 3. Optimize table
VACUUM ANALYZE audit_logs;
```

### Recovery Scenario 7: Running Out of Disk Space

**Symptoms**:
- Database won't start
- Cannot upload new data
- Error: "disk full"

**Recovery Steps** (Production):

```bash
# 1. Check disk usage
df -h

# 2. Clean up old backups
rm -f /backups/*_2024*.sql

# 3. Archive old audit logs (see above)

# 4. Optimize PostgreSQL
VACUUM FULL;
REINDEX DATABASE barangay_db;

# 5. Resize Render.com disk
# Go to Render.com > Database > Settings > Resize
```

### Recovery Scenario 8: SSL Certificate Expired (Production)

**Symptoms**:
- Browser shows "Connection not secure"
- HTTPS fails
- Render.com warning

**Recovery Steps**:

```bash
# If using Certbot (Let's Encrypt)
sudo certbot renew

# If using Render.com
# Automatic renewal enabled by default
# No action needed - Render handles it

# Manual renewal
sudo certbot certonly --standalone -d yourdomain.com
```

### Recovery Scenario 9: Forgotten Admin Username

**Symptoms**: Forgot admin account username

**Recovery Steps**:

```sql
-- Find all admin users
SELECT username, email, role FROM users WHERE role='admin';

-- Change any user to admin
UPDATE users SET role='admin' WHERE username='known_username';
```

### Recovery Scenario 10: Complete Data Loss

**Worst Case Scenario**: Database completely deleted

```bash
# 1. If no backup exists - DATA IS LOST
# This is why regular backups are critical

# 2. Re-initialize from scratch
python init_db_render.py

# 3. Manually re-enter data
# Go to /add_household, /add_member

# PREVENTION for future:
# - Automated daily backups (see Backup Procedure)
# - Off-site backup storage
# - Database replication
```

---

## 17. DATABASE MIGRATION GUIDE

### Migration Scenario 1: MySQL to PostgreSQL

**Why Migrate**: PostgreSQL is more reliable for production

**Before Starting**:
- Backup MySQL database
- Backup PostgreSQL database
- Test on non-production system first

**Migration Steps**:

```bash
# 1. Export MySQL data
mysqldump -u root -p barangay_db > mysql_dump.sql

# 2. Convert schema (manual)
# Edit mysql_dump.sql:
# - Change AUTO_INCREMENT to SERIAL
# - Change INT to BIGINT where needed
# - Change datetime to timestamp

# 3. Create PostgreSQL database
createdb barangay_db

# 4. Import converted schema
psql -d barangay_db -f mysql_dump.sql

# 5. Verify data
psql -d barangay_db -c "SELECT COUNT(*) FROM residents;"
psql -d barangay_db -c "SELECT COUNT(*) FROM household;"

# 6. Test application
# Update DATABASE_URL to PostgreSQL
# Restart Flask app
# Test all features
```

### Migration Scenario 2: Local to Production (Render.com)

**Setup**:
1. Database already on Render.com (PostgreSQL)
2. Data currently on local machine (MySQL or PostgreSQL)
3. Ready to go live

**Migration Steps**:

```bash
# 1. Export local database
mysqldump -u root -p barangay_db > local_data.sql

# 2. If PostgreSQL:
pg_dump barangay_db > local_data.sql

# 3. Convert format if needed (MySQL → PostgreSQL)
# Edit local_data.sql file

# 4. Import to Render.com database
psql "postgresql://user:pass@render-db.onrender.com:5432/barangay_db" < local_data.sql

# 5. Test production
# Visit https://barangay-system.onrender.com
# Test all features
# Check audit logs

# 6. Update DNS (if using custom domain)
# Point to Render.com service
```

### Migration Scenario 3: Database Schema Update

**Example**: Add new column for SMS notifications

**Steps**:

```bash
# 1. Create migration file
echo "-- Migration 001: Add SMS column
ALTER TABLE users ADD COLUMN sms_number VARCHAR(20);
ALTER TABLE users ADD COLUMN notify_via_sms BOOLEAN DEFAULT FALSE;" > migrations/001_add_sms.sql

# 2. Test locally
psql -d barangay_db -f migrations/001_add_sms.sql

# 3. Verify column exists
psql -d barangay_db -c "\d users;"

# 4. Deploy to production
psql "postgresql://user:pass@render-db.onrender.com:5432/barangay_db" < migrations/001_add_sms.sql

# 5. Update app.py to use new column
# Add SMS notification logic
```

### Migration Scenario 4: Large Dataset Import

**Importing 50,000+ residents at once**

```bash
# 1. Prepare CSV file format
# resident_id, household_id, firstname, lastname, age, gender, status

# 2. Create import script
python import_residents.py --file residents.csv

# Or use COPY command (PostgreSQL)
COPY residents(household_id, firstname, surname, age, gender, status) 
FROM '/path/to/file.csv' 
WITH (FORMAT csv, HEADER true);

# 3. Verify import
SELECT COUNT(*) FROM residents;

# 4. Update analytics
# Refresh dashboard cache

# 5. Backup after import
pg_dump barangay_db > backup_after_import.sql
```

### Migration Scenario 5: Database Version Upgrade

**Example**: PostgreSQL 12 → PostgreSQL 13

**On Render.com**:
1. Click database > Settings
2. Select new version
3. Render handles migration automatically

**On Local Machine**:
```bash
# 1. Backup current database
pg_dump barangay_db > pre_upgrade_backup.sql

# 2. Upgrade PostgreSQL
brew upgrade postgresql  # macOS
sudo apt upgrade postgresql  # Linux

# 3. Recreate database with new version
dropdb barangay_db
createdb barangay_db
psql -d barangay_db -f pre_upgrade_backup.sql

# 4. Test application
python app.py
```

---

## 18. BACKUP PROCEDURE

### Why Backups Matter

- **Data Loss Protection**: Accidental deletion, corruption, hardware failure
- **Disaster Recovery**: Ransomware, hacking, natural disasters
- **Compliance**: Regulatory requirements (government, healthcare)
- **Peace of Mind**: Know your data is safe

### Backup Strategy

```
┌──────────────────────────────────┐
│   BACKUP SCHEDULE RECOMMENDED    │
├──────────────────────────────────┤
│ Daily: Automated backup daily    │
│ Weekly: Full backup to off-site  │
│ Monthly: Archive backup offline  │
└──────────────────────────────────┘

Recovery Time Objective (RTO): 1 hour
Recovery Point Objective (RPO): 1 day
```

### Backup Method 1: Manual PostgreSQL Backup

```bash
# Full database backup
pg_dump barangay_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup (smaller file)
pg_dump barangay_db | gzip > backup_$(date +%Y%m%d).sql.gz

# With statistics
pg_dump --verbose --format=custom barangay_db > backup.dump

# Specific table only
pg_dump -t residents barangay_db > residents_backup.sql
```

### Backup Method 2: Automated Daily Backup (Linux/macOS)

**Cron Job Setup**:

```bash
# Edit crontab
crontab -e

# Add this line (backup daily at 2 AM)
0 2 * * * pg_dump barangay_db | gzip > /backups/barangay_db_$(date +\%Y\%m\%d).sql.gz

# Verify
crontab -l
```

**Cleanup Old Backups**:

```bash
# Delete backups older than 30 days
find /backups -name "barangay_db_*.sql.gz" -mtime +30 -delete
```

### Backup Method 3: Render.com Automatic Backups

Render.com automatically backs up PostgreSQL databases:
- Daily automated backups (7-day retention)
- Manual backup option in database settings
- Point-in-time recovery available

**Accessing Render Backups**:
1. Go to Render.com > Your Database
2. Click "Backups" tab
3. See list of available backups
4. Click restore button

### Backup Method 4: Full Application Backup

```bash
# Backup everything (code + database)
tar -czf barangay_system_backup_$(date +%Y%m%d).tar.gz \
  /home/barangay/barangay_system \
  < <(pg_dump barangay_db | gzip)

# Or separately
pg_dump barangay_db | gzip > app_backup_db_$(date +%Y%m%d).sql.gz
tar -czf app_backup_code_$(date +%Y%m%d).tar.gz /home/barangay/barangay_system/
```

### Backup Storage Locations

**Local Development**:
```
C:\Backups\barangay_db_20260706.sql
~/backups/barangay_db_20260706.sql.gz
```

**Production - Recommended**:
1. **Primary**: Render.com automated backups
2. **Secondary**: Off-site cloud (AWS S3, Google Cloud Storage)
3. **Tertiary**: External hard drive (monthly)

**Cloud Backup Setup** (AWS S3):

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure

# Upload backup to S3
aws s3 cp backup_20260706.sql.gz s3://barangay-backups/

# Schedule automatic uploads
0 3 * * * pg_dump barangay_db | gzip | aws s3 cp - s3://barangay-backups/backup_$(date +\%Y\%m\%d).sql.gz
```

### Backup Verification

Always verify backups are working:

```bash
# 1. Check backup file exists and has size
ls -lh backup_*.sql.gz

# 2. List contents (without extracting)
tar -tzf backup_*.tar.gz | head -20

# 3. Test restore to temporary database
createdb barangay_db_test
psql -d barangay_db_test < backup_20260706.sql

# 4. Verify data
psql -d barangay_db_test -c "SELECT COUNT(*) FROM residents;"

# 5. Clean up test database
dropdb barangay_db_test
```

### Disaster Recovery Test

**Monthly Recovery Drill** (test restoration process):

```bash
# 1. Take current backup
pg_dump barangay_db | gzip > backup_test_$(date +%Y%m%d).sql.gz

# 2. Create test database
createdb barangay_db_test

# 3. Restore from backup
gunzip -c backup_test_$(date +%Y%m%d).sql.gz | psql -d barangay_db_test

# 4. Verify restoration
psql -d barangay_db_test -c "SELECT COUNT(*) FROM households;"
psql -d barangay_db_test -c "SELECT COUNT(*) FROM residents;"
psql -d barangay_db_test -c "SELECT COUNT(*) FROM audit_logs;"

# 5. Time the recovery
# Goal: Complete recovery within RTO (1 hour)

# 6. Document results
echo "Recovery test completed: $(date)" >> recovery_tests.log

# 7. Clean up
dropdb barangay_db_test
```

### Backup Checklist

- [ ] Automated backups running daily
- [ ] Backups stored in 2+ locations
- [ ] Backups tested monthly
- [ ] Off-site backups (cloud storage)
- [ ] Backup encryption enabled
- [ ] Backup retention policy defined
- [ ] Disaster recovery plan documented
- [ ] Staff trained on recovery procedure
- [ ] RTO/RPO defined and monitored
- [ ] Backup logs monitored for failures

### Backup Troubleshooting

| Issue | Solution |
|-------|----------|
| Backup fails silently | Check cron logs: `grep CRON /var/log/syslog` |
| Backup file corrupted | Verify with `pg_dump --validate` |
| Backup too large | Use compression: `pg_dump \| gzip` |
| Restore takes too long | Use `--jobs` parameter: `pg_restore --jobs=4` |
| Out of disk space | Clean old backups: `find /backups -mtime +30 -delete` |

---

## APPENDIX

### Quick Reference: Important Files

| File | Purpose |
|------|---------|
| [app.py](app.py) | Main application - 2800+ lines |
| [requirements.txt](requirements.txt) | Python dependencies |
| [database.sql](database.sql) | Database schema |
| [setup_db.py](setup_db.py) | Database initialization |
| [auth_utils.py](auth_utils.py) | Authentication utilities |
| [email_config.py](email_config.py) | Gmail configuration |

### Quick Reference: Important Routes

| Route | Purpose | Role |
|-------|---------|------|
| `/login` | User login | Public |
| `/signup` | New registration | Public |
| `/forgot_password` | Password reset | Public |
| `/add_member` | Add resident | Admin |
| `/add_household` | Add household | Admin |
| `/analytics` | Dashboard | User |
| `/user-management` | Admin panel | Admin |
| `/logout` | End session | User |

### Support Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Render.com Docs**: https://render.com/docs
- **python-docx**: https://python-docx.readthedocs.io/

### Project Maintenance

**Monthly Tasks**:
- Review audit logs
- Test backups
- Monitor disk usage
- Check for dependency updates

**Quarterly Tasks**:
- Update Python packages
- Review security settings
- Performance optimization

**Yearly Tasks**:
- Major version upgrades
- Security audit
- Capacity planning
- Disaster recovery drill

---

**Document Version**: 1.0  
**Last Updated**: July 2026  
**Status**: COMPLETE - Ready for Production
