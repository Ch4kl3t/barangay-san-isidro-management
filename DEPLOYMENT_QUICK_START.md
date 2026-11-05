# Quick Start: PostgreSQL Deployment

## ⚡ 5-Minute Setup

### 1. Environment Setup
```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="postgresql://user:password@host:5432/dbname"

# Verify psycopg2 is installed
pip install -r requirements.txt
```

### 2. Test Connection
```bash
# Run any verification script
python verify_migration.py
```

If you see "✅ STEP 1 VERIFICATION: SUCCESS!" → Ready to go!

### 3. Run Application
```bash
# Development
python app.py

# Production (Render/Cloud)
gunicorn -w 4 -b 0.0.0.0:$PORT app:app
```

---

## 🚀 Deploy on Render

### Option A: Web Service + Database
1. Create PostgreSQL database on Render
2. Create Web Service from GitHub
3. Connect to PostgreSQL
4. Set `DATABASE_URL` environment variable
5. Deploy

### Option B: Database Only (Existing Host)
1. Create PostgreSQL database on your host
2. Set `DATABASE_URL` environment variable on Render
3. Deploy web service

---

## ✅ Verification Commands

```bash
# Check database structure
python verify_migration.py

# Check email setup
python verify_email.py

# List users
python query_users.py

# View audit logs
python check_logs.py
```

---

## 🔑 Environment Variables Required

```
DATABASE_URL=postgresql://user:password@host:5432/database
```

That's it! All other configuration is automatic.

---

## 🆘 Troubleshooting

| Error | Fix |
|-------|-----|
| `DATABASE_URL not found` | Set environment variable |
| `psycopg2 not found` | `pip install psycopg2-binary` |
| `connection refused` | Check DATABASE_URL is correct |
| `ssl required` | Verify `sslmode=require` in URL |
| `relation does not exist` | Create database schema from database.sql |

---

## 📋 Checklist

- [ ] DATABASE_URL environment variable set
- [ ] psycopg2-binary installed
- [ ] PostgreSQL database created
- [ ] Verification script passes
- [ ] App starts without errors
- [ ] Can login to application
- [ ] Audit logs visible

✅ Ready to deploy!
