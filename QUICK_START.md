# Quick Reference - Role-Based Auth Setup

## 📋 Quick Checklist (Do This Now)

```
Step 1: Database Migration (5 min)
  [ ] Open MySQL client or phpMyAdmin
  [ ] Run setup_rbac.sql against barangay_db
  [ ] Verify: SELECT COUNT(*) FROM password_resets;

Step 2: Gmail Setup (5 min)
  [ ] Go to myaccount.google.com/apppasswords
  [ ] Get Gmail App Password (16 chars, spaces ok)
  [ ] Copy .env.example to .env
  [ ] Edit .env - add GMAIL_ADDRESS and GMAIL_PASSWORD
  [ ] Save .env (do not commit to git!)

Step 3: Restart App (2 min)
  [ ] Stop Flask: Ctrl+C
  [ ] Start Flask: python app.py
  [ ] Check console for errors

Step 4: Test Login (5 min)
  [ ] Go to http://localhost:5000/login
  [ ] Log in with admin account
  [ ] Check top-right - should see ADMIN badge
  [ ] Home page - should see statistics

Step 5: Test Password Reset (10 min)
  [ ] Click "Forgot Password?"
  [ ] Enter admin username
  [ ] Check Gmail inbox
  [ ] Click email link
  [ ] Enter new password (8+ chars)
  [ ] Log in with new password

Step 6: Test User Account (10 min)
  [ ] Go to /user-management
  [ ] Demote a user to role='user'
  [ ] Log out
  [ ] Log in as that user
  [ ] Check home page - NO statistics shown
  [ ] Try accessing /add_member - should be blocked

Total Time: ~40 minutes
```

---

## 🔑 Key Files

| File | Purpose |
|------|---------|
| `.env.example` | Copy to `.env`, add Gmail credentials |
| `setup_rbac.sql` | Run this against MySQL database |
| `RBAC_SETUP_GUIDE.md` | Detailed instructions |
| `IMPLEMENTATION_SUMMARY.md` | Technical reference |

---

## 🚀 Login Page Behavior

**Admin User:**
```
Home: Shows dashboard statistics ✓
Edit/Delete: Buttons visible ✓
Add Member: Button visible ✓
Print Reports: Accessible ✓
Audit Log: Accessible ✓
User Management: Accessible ✓
```

**Regular User:**
```
Home: No statistics shown ✗
Edit/Delete: Buttons hidden ✗
Add Member: Button hidden ✗
Print Reports: Blocked (403) ✗
Audit Log: Blocked (403) ✗
User Management: Blocked (403) ✗
View Members: ✓ (read-only)
View Households: ✓ (read-only)
Analytics: ✓ (read-only)
```

---

## 🔒 Protected Routes

These routes require `role='admin'`:
- `/add_member` - Add resident
- `/edit_member/<id>` - Edit resident
- `/delete_member/<id>` - Delete resident
- `/add_household` - Add household
- `/delete_household/<id>` - Delete household
- `/print_*` - All print/report routes
- `/audit-log` - View audit logs
- `/user-management` - Manage users
- `/api/user/role` - Update user roles
- `/api/preview/*` - Report previews

---

## 🐛 Troubleshooting

**Problem**: Import error for auth_utils  
**Fix**: Verify auth_utils.py is in app root directory

**Problem**: Email not sending  
**Fix**: 
1. Check .env has GMAIL_ADDRESS and GMAIL_PASSWORD
2. Enable 2FA on Gmail account
3. Generate App Password (not regular password)
4. Check Flask console for errors

**Problem**: Getting 403 Unauthorized  
**Fix**: 
1. Check database: `SELECT username, role FROM users;`
2. Verify user has role='admin'
3. Restart Flask app

**Problem**: Can't find /reset-password/<token> page  
**Fix**: Click the email link in reset email (not browser back button)

---

## 📱 URLs Reference

| Route | Purpose | Auth |
|-------|---------|------|
| `/login` | Login page | Public |
| `/logout` | Logout | Any |
| `/forgot-password` | Request reset | Public |
| `/reset-password/<token>` | Reset password | Public |
| `/user-management` | Manage users | Admin only |
| `/profile` | User profile | Any |
| `/audit-log` | View audit logs | Admin only |
| `/home` or `/` | Dashboard | Any |
| `/view_members` | View residents | Any |
| `/add_member` | Add resident | Admin only |
| `/print_reports` | Generate reports | Admin only |

---

## 📊 Database Check Commands

```sql
-- Check users and roles
SELECT id, username, role FROM users;

-- Check password resets
SELECT username, token, used, created_at FROM password_resets;

-- Check specific user
SELECT * FROM users WHERE username='admin';

-- Update user role manually
UPDATE users SET role='admin' WHERE username='admin';
```

---

## 🎯 Success Indicators

✅ System is ready when you see:
1. Admin user has role='admin' in database
2. Login page has "Forgot Password?" link
3. Password reset email arrives within 2 minutes
4. Admin can access /user-management
5. Regular user cannot access /add_member (404 or 403)
6. Home page shows/hides statistics based on role
7. All edits logged in `/audit-log`

---

## 📞 Still Having Issues?

Check these files in order:
1. `RBAC_SETUP_GUIDE.md` - Detailed setup
2. `IMPLEMENTATION_SUMMARY.md` - Technical details
3. Flask console output - Error messages
4. Audit log at `/audit-log` - Activity tracking

---

## ⏱️ Time Breakdown

- Database Setup: 5 min
- Gmail Config: 5 min
- App Restart: 2 min
- Login Test: 5 min
- Password Reset Test: 10 min
- User Account Test: 10 min
- **Total: ~40 minutes**

---

**Next Action**: Run `setup_rbac.sql` now, then follow the Quick Checklist above.
