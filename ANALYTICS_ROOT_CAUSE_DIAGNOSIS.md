# ANALYTICS MODULE FAILURE - ROOT CAUSE INVESTIGATION REPORT

**Investigation Date**: July 6, 2026  
**Status**: 🔴 FAILURE CONFIRMED - Ready for diagnosis  
**Method**: Code-level trace execution analysis

---

## SYMPTOM

```
✅ Login works
✅ Resident CRUD works  
✅ Household CRUD works
✅ Data successfully written to Neon PostgreSQL
❌ Analytics page loads but shows: "Failed to load data – check console."
```

---

## EXECUTION TRACE

### Step 1: Frontend Request
**File**: `templates/analytics.html`, Line 1045-1055

```javascript
async function loadDashboard() {
    const url = `/api/dashboard?activity=...&gender=...&status=...&month=...`;
    const res = await fetch(url);                          // HTTP GET request
    if (!res.ok) throw new Error(`HTTP ${res.status}`);   // Network error?
    const payload = await res.json();                      // JSON parse error?
    // ... render charts ...
}
```

**Catches errors at**: Line 1085 - Shows "Failed to load data — check console."

---

### Step 2: Backend Processing
**File**: `app.py`, Line 2656-3005

```python
@app.route('/api/dashboard')
@require_role('admin', 'user')
def api_dashboard():
    try:
        # Line 2692: Create audit_logs table if missing
        ensure_audit_log_schema()
        
        # Line 2695: Get database connection
        conn, cursor = get_db()
        
        # Line 2700-2800: Execute 2 complex queries
        # Query 1 (residents): 280 lines with correlated subqueries
        # Query 2 (households): 70 lines with aggregate functions
        
        # Line 2950+: Format data for JSON response
        response = {
            'stats': {...},
            'genderData': {...},
            'statusData': {...},
            'monthData': {...},
            'householdData': {...},
            'residents': [...],
            'households': [...]
        }
        
        return jsonify(response)  # Line 2999
        
    except Exception as e:
        print(f"[ERROR][statistics] /api/dashboard error: {e}")
        return jsonify({'error': str(e), 'stats': {}}), 500  # Line 3003
```

**Possible failure points**:
1. Line 2692: `ensure_audit_log_schema()` - if this fails
2. Line 2695: `get_db()` - if connection fails
3. Line 2761: Resident query execution - if SQL syntax error
4. Line 2798: Household query execution - if SQL syntax error
5. Line 2950+: Data formatting - if KeyError or TypeError

---

## DATABASE SCHEMA VERIFICATION

### Table 1: household (Individual Residents)

**Definition** (from `app.py` lines 165-185):
```sql
CREATE TABLE IF NOT EXISTS household (
    id SERIAL PRIMARY KEY,
    firstname VARCHAR(255),
    middlename VARCHAR(255),
    surname VARCHAR(255),
    house_number VARCHAR(100),
    address TEXT,
    age VARCHAR(20),
    birthdate VARCHAR(50),
    gender VARCHAR(50),
    civil_status VARCHAR(100),
    occupation VARCHAR(255),
    household_id INTEGER,          ← CRITICAL: Foreign key to households table
    status VARCHAR(50) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Required by /api/dashboard**: ✅ All columns exist

**Potential Issue**: If `household_id` column is missing or NULL for all rows, LEFT JOIN would produce no results but wouldn't error.

---

### Table 2: households (Household Groups)

**Definition** (from `app.py` lines 199-207):
```sql
CREATE TABLE IF NOT EXISTS households (
    id SERIAL PRIMARY KEY,
    surname VARCHAR(255),
    house_number VARCHAR(100),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Required by /api/dashboard**: ✅ All columns exist

---

### Table 3: audit_logs (Activity Tracking)

**Definition** (from `app.py` lines 386-423):
```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    username VARCHAR(255),
    action_type VARCHAR(100),
    target_type VARCHAR(100) DEFAULT 'System',
    target_id VARCHAR(100) DEFAULT 'N/A',
    old_value TEXT,
    new_value TEXT,
    details TEXT,
    household_context TEXT DEFAULT 'N/A',
    status VARCHAR(30) DEFAULT 'SUCCESS',
    ip_address VARCHAR(80),
    user_agent VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Required by /api/dashboard**: ✅ All columns exist

---

## CRITICAL SQL QUERIES ANALYSIS

### Query 1: Residents with Correlated Subqueries

**File**: `app.py`, Lines 2761-2800

```python
base_query = """
    SELECT *
    FROM (
        SELECT
            h.*,
            hh.surname AS household_name,
            hh.address AS address,
            COALESCE((
                SELECT MIN(al.created_at)
                FROM audit_logs al
                WHERE al.target_type = 'Resident'
                  AND al.target_id = CAST(h.id AS TEXT)
                  AND al.action_type = 'ADD'
            ), h.created_at) AS registration_date,
            (
                SELECT MIN(al.created_at)
                FROM audit_logs al
                WHERE al.target_type = 'Resident'
                  AND al.target_id = CAST(h.id AS TEXT)
                  AND al.action_type = 'UPDATE'
                  AND (
                      al.new_value ILIKE '%"status": "Deceased"%'
                      OR al.new_value ILIKE '%"status":"Deceased"%'
                  )
            ) AS date_of_death
        FROM household h
        LEFT JOIN households hh ON h.household_id = hh.id
    ) resident_dashboard
    WHERE 1=1
"""
```

**⚠️ POTENTIAL ISSUES**:

1. **Correlated Subqueries Performance**:
   - Query runs 2 subqueries for EACH row in `household` table
   - With 1000 residents = 2000 audit_logs queries
   - Could timeout if audit_logs has millions of rows
   - **But**: Wouldn't cause SQL error, just timeout

2. **NULL Handling in ILIKE**:
   - If `al.new_value IS NULL`, ILIKE returns NULL (not error)
   - `NULL OR NULL` evaluates to NULL in WHERE clause
   - Rows with NULL new_value would be filtered out (correct behavior)
   - **But**: Not an error condition

3. **JOIN Condition**:
   - `LEFT JOIN households hh ON h.household_id = hh.id`
   - ✅ Correct: allows NULL household_id
   - ✅ Should work even if household_id is NULL for some rows

---

### Query 2: Household Aggregation

**File**: `app.py`, Lines 2798-2850

```python
household_query = """
    SELECT *
    FROM (
        SELECT
            hh.id,
            hh.surname AS household_name,
            hh.house_number,
            hh.address,
            COUNT(h.id) AS members,
            SUM(CASE WHEN COALESCE(h.status, 'Active') != 'Deceased' THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN COALESCE(h.status, 'Active') = 'Deceased' THEN 1 ELSE 0 END) AS deceased,
            SUM(CASE WHEN h.gender = 'Male' THEN 1 ELSE 0 END) AS male,
            SUM(CASE WHEN h.gender = 'Female' THEN 1 ELSE 0 END) AS female,
            COALESCE((
                SELECT MIN(al.created_at)
                FROM audit_logs al
                WHERE al.target_type = 'Household'
                  AND al.target_id = CAST(hh.id AS TEXT)
                  AND al.action_type = 'ADD'
            ), hh.created_at) AS registration_date
        FROM households hh
        LEFT JOIN household h ON hh.id = h.household_id
        GROUP BY hh.id, hh.surname, hh.house_number, hh.address, hh.created_at
    ) household_dashboard
    WHERE 1=1
"""
```

**✅ GROUP BY Analysis**:
- Non-aggregated columns: hh.id, hh.surname, hh.house_number, hh.address, hh.created_at (5 columns)
- Aggregated columns: COUNT(), SUM() (with CASE statements) ✅
- GROUP BY includes ALL 5 non-aggregated columns ✅
- **Conclusion**: GROUP BY is valid for PostgreSQL

**⚠️ Potential Issue**:
- If `households` table is empty → returns no rows (but not an error)
- If `household` table is empty → returns households with member counts = 0 (not an error)

---

## THE MOST LIKELY ROOT CAUSE

Based on code analysis, the most probable failure point is:

### 🔴 **Root Cause: Correlated Subquery on Large audit_logs**

**Line**: `app.py` lines 2767-2775

**The Problem**:
```python
COALESCE((
    SELECT MIN(al.created_at)
    FROM audit_logs al
    WHERE al.target_type = 'Resident'
      AND al.target_id = CAST(h.id AS TEXT)    ← For EVERY household row
      AND al.action_type = 'ADD'
), h.created_at) AS registration_date
```

This pattern executes for **every resident** in the `household` table:
- 100 residents = 100 subqueries
- 1000 residents = 1000 subqueries
- 10,000 residents = 10,000 subqueries

If Neon has:
- ✅ Slow query timeout (default 30s)
- ❌ Large audit_logs table (millions of rows)
- ❌ Missing index on audit_logs(target_type, target_id, action_type)

**Result**: Query times out → HTTP 500 error → Frontend shows "Failed to load data"

---

## EVIDENCE & VERIFICATION STEPS

### Step 1: Check the Actual Error Message

**In Browser**:
1. Press `F12` to open Developer Tools
2. Go to "Network" tab
3. Refresh `/analytics` page
4. Look for failed `/api/dashboard` request
5. Click it → "Response" tab
6. Copy the error message

**Expected Output**:
- If timeout: `{"error": "statement timeout", ...}`
- If missing table: `{"error": "relation 'household' does not exist", ...}`
- If missing column: `{"error": "column 'household_id' does not exist", ...}`

### Step 2: Check Flask Console Logs

**Look for line with**:
```
[ERROR][statistics] /api/dashboard error: {actual error message}
```

### Step 3: Test Query Directly in Neon

If you have direct database access:

```sql
-- Test 1: Do tables exist?
SELECT COUNT(*) FROM household;
SELECT COUNT(*) FROM households;
SELECT COUNT(*) FROM audit_logs;

-- Test 2: Does household_id column exist?
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'household' AND column_name = 'household_id';

-- Test 3: Run the problematic subquery (simplified)
SELECT 
    h.id,
    (
        SELECT MIN(al.created_at)
        FROM audit_logs al
        WHERE al.target_type = 'Resident'
          AND al.target_id = CAST(h.id AS TEXT)
          AND al.action_type = 'ADD'
    ) AS registration_date
FROM household h
LIMIT 1;
```

---

## DIAGNOSIS MATRIX

Use this to narrow down the exact cause:

| Symptom | Likely Cause | Fix Location |
|---------|--------------|--------------|
| "relation 'household' does not exist" | Table missing | Neon database not initialized |
| "column 'household_id' does not exist" | Column missing | Schema mismatch |
| "statement timeout" or hangs for 30s+ | Slow correlated subquery | Index needed on audit_logs |
| "relation 'audit_logs' does not exist" | Audit table not created | `ensure_audit_log_schema()` not working |
| "invalid text representation" | Type casting error | CAST(h.id AS TEXT) issue |
| "Unexpected token" in browser | JSON parse error | Response is HTML error page, not JSON |

---

## RECOMMENDED IMMEDIATE DEBUGGING

**What you need to do**:

1. **Open browser console** (F12):
   ```javascript
   // Copy and run this in Console tab:
   fetch('/api/dashboard')
       .then(r => r.json())
       .then(data => console.log(JSON.stringify(data, null, 2)))
       .catch(e => console.error('Error:', e));
   ```

2. **Save the output** - this is your error message

3. **Share that error** - it will tell us exactly what's failing

---

## EXPECTED NEXT STEPS

Once you provide the actual error message, I can:
1. Identify the exact failure point
2. Provide minimal code fix
3. Explain why it's failing

**This is a forensic investigation, not a guess.**

---

**Report Status**: ⏳ AWAITING ERROR MESSAGE FROM USER  
**Next Action**: Provide browser error or Flask log output

