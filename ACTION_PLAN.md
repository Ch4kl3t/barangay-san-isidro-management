# 🎯 ACTION PLAN - Role-Based Authentication Setup

**Status**: ✅ Code Complete | 🔧 Ready for Configuration  
**Time to Complete**: 40-60 minutes  
**Difficulty**: Easy (mostly copy-paste configuration)

---

## TODAY'S TASK: 5 Simple Steps

### STEP 1️⃣: Database Migration (5 minutes)

**What**: Apply database schema changes  
**How**:
```bash
# Option A: Using MySQL command line
mysql -u root -p barangay_db < setup_rbac.sql

# Option B: Using MySQL GUI (phpMyAdmin)
1. Go to phpMyAdmin
2. Select barangay_db database
3. Click "Import" tab
4. Upload setup_rbac.sql
5. Click "Go"
```

**Verify**:
```sql
SELECT COUNT(*) as tables FROM information_schema.tables WHERE table_schema='barangay_db' AND table_name='password_resets';
-- Should return: 1
```

✅ **Done**: Column added to users, password_resets table created

---

### STEP 2️⃣: Gmail Configuration (5 minutes)

**What**: Get Gmail credentials for password reset emails  
**How**:

1. Go to: https://myaccount.google.com/apppasswords
2. Select: **Mail** and **Windows Computer** (or your device)
3. Click "Generate"
4. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)
5. In your project folder, create `.env` file:
   ```
   GMAIL_ADDRESS=your-actual-email@gmail.com
   GMAIL_PASSWORD=xxxx xxxx xxxx xxxx
   ```
6. Save file (do NOT commit to git - it's in .gitignore)

✅ **Done**: Gmail credentials ready

---

### STEP 3️⃣: Start Flask Application (2 minutes)

**What**: Restart app to load configuration  
**How**:
```bash
# In PowerShell/Terminal, in project directory:
python app.py
```

**Expected Output**:
```
WARNING in app.run()
Running on http://127.0.0.1:5000
```

✅ **Done**: App running with authentication active

---

### STEP 4️⃣: Quick Login Test (5 minutes)

**What**: Verify admin access  
**How**:
1. Open: http://localhost:5000/login
2. Enter your admin username and password
3. You should see dashboard with statistics
4. Look top-right - should show **ADMIN** badge

✅ **Done**: Admin role verified

---

### STEP 5️⃣: Test Password Recovery (10 minutes)

**What**: Verify email system works  
**How**:
1. On login page, click **"Forgot Password?"**
2. Enter your admin username
3. Click **"Send Reset Link"**
4. Check your Gmail inbox (wait 2-3 seconds)
5. Look for email from: `your-gmail@gmail.com`
6. Click the blue **"Reset Your Password"** button in email
7. Enter new password: (must be 8+ characters)
8. Confirm password
9. Click **"Reset Password"**
10. Log in with new password

**Expected Email Content**:
- Subject: "Barangay Information System - Password Reset Request"
- Contains clickable "Reset Your Password" button
- States "Link expires in 1 hour"

✅ **Done**: Email system working

---

## VERIFICATION CHECKLIST

After completing above steps, verify:

```
[ ] Database migration executed (no errors)
[ ] .env file created with Gmail credentials
[ ] Flask app restarts without errors
[ ] Can log in with admin account
[ ] ADMIN badge shows in top-right corner
[ ] Dashboard statistics visible
[ ] "Forgot Password" link works
[ ] Password reset email arrives in 2-3 seconds
[ ] Can reset password via email link
[ ] Can log in with new password
```

---

## OPTIONAL: Test User Restrictions

**After** completing the 5 steps above, optionally test user restrictions:

```sql
-- Create a test user
INSERT INTO users (username, password, role) 
VALUES ('testuser', 'password123', 'user');
```

Then:
1. Log out
2. Log in as `testuser` with password `password123`
3. Verify:
   - ❌ NO statistics on home page
   - ❌ NO "Add Member" button
   - ❌ NO "Edit/Delete" buttons
   - ✅ CAN view members list (read-only)

---

## 📚 DOCUMENTATION

Read these for more details:

1. **QUICK_START.md** - Quick reference tables
2. **RBAC_SETUP_GUIDE.md** - Detailed step-by-step (recommended)
3. **IMPLEMENTATION_SUMMARY.md** - Technical overview

---

## 🆘 COMMON ISSUES & FIXES

### Issue: `ModuleNotFoundError: No module named 'auth_utils'`
**Fix**: Verify `auth_utils.py` is in the same folder as `app.py`

### Issue: Email not sending
**Fix**:
1. Check .env file exists with correct credentials
2. Verify you used **Gmail App Password**, not regular password
3. Enable 2-Factor Authentication on Gmail (required for app passwords)
4. Try generating a new App Password from https://myaccount.google.com/apppasswords

### Issue: "Unauthorized" when accessing /user-management
**Fix**:
1. Make sure you're logged in as admin
2. Database should have your user with role='admin'
3. Check: `SELECT username, role FROM users WHERE username='admin';`

### Issue: "Email service not configured"
**Fix**:
1. Create .env file (copy from .env.example)
2. Add `GMAIL_ADDRESS=your@gmail.com`
3. Add `GMAIL_PASSWORD=your-app-password`
4. Restart Flask: Ctrl+C then `python app.py`

---

## ⏰ TIME TRACKING

```
Setup Checklist:
✓ Step 1 (Database):        5 min
✓ Step 2 (Gmail):           5 min
✓ Step 3 (Restart):         2 min
✓ Step 4 (Login Test):      5 min
✓ Step 5 (Email Test):     10 min
─────────────────────────────
  TOTAL:                    27 minutes

Optional Verification:
  User Restrictions Test:    5 min
  Read Documentation:       15 min
```

---

## 🎓 WHAT YOU'VE ACCOMPLISHED

After these 5 steps, your system will have:

✅ **Admin Role**: Full access to everything
✅ **User Role**: View-only access (no add/edit/delete)
✅ **Password Recovery**: Secure email-based password reset
✅ **Admin Dashboard**: /user-management for user management
✅ **Audit Logs**: All user actions tracked
✅ **Security**: Role-based route protection

---

## 🚀 NEXT STEPS (After Today)

After successfully completing the 5 steps:

**This Week** (Optional Enhancements):
- [ ] Hide edit/delete buttons from view-only users in UI
- [ ] Add password hashing for additional security
- [ ] Create more user accounts for residents

**Security Improvements** (When Ready):
- [ ] Implement password hashing (werkzeug.security)
- [ ] Add session timeout after 30 min inactivity
- [ ] Add login attempt rate limiting

---

## 📞 NEED HELP?

1. **Error Message in Flask**: Check the terminal running Flask
2. **Email Not Sending**: Check email_config.py for setup instructions
3. **Database Error**: Run `DESCRIBE users;` to check structure
4. **Lost Password**: Use "Forgot Password" link on login page

---

## ✨ SUCCESS SIGNALS

You'll know it's working when:

1. ✅ Can log in and see ADMIN badge
2. ✅ Password reset email arrives in inbox
3. ✅ Can reset password via email link
4. ✅ Create new user with role='user'
5. ✅ That user cannot access add/edit/delete features
6. ✅ Regular users see empty home (no statistics)

---

## 📋 COMMAND REFERENCE

**Quick Commands:**

```bash
# Start app
python app.py

# Test login
curl http://localhost:5000/login

# Check user roles
mysql -u root -p barangay_db -e "SELECT username, role FROM users;"

# Clear user roles (if needed)
mysql -u root -p barangay_db -e "UPDATE users SET role='admin';"
```

---

**YOU'RE ALL SET!** 🎉

Start with **STEP 1** (Database Migration) and follow the 5 steps above.

Estimated completion: **40 minutes**

Good luck! Let me know if you hit any snags.
