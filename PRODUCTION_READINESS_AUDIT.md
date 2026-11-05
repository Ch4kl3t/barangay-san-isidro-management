# Production Readiness Audit

Date: June 7, 2026

## Bugs Found And Fixed

### 1. Analytics monthly chart could ignore valid backend chart data
- File: `templates/analytics.html`
- Lines: 673, 798
- Why it occurred: `analytics.html` rebuilt monthly chart data from `residents` first. If browser date parsing failed or shifted a returned PostgreSQL timestamp, the rebuilt series could be empty even when `/api/dashboard` returned valid `monthData`.
- Change made: Added `parseDashboardDate()` and changed `getSeriesForStat()` to use `/api/dashboard.monthData` as the primary monthly source. Daily drilldown still uses resident rows.

### 2. Dashboard debug logging was too noisy for production
- File: `app.py`
- Lines: 69, 2656-3022
- Why it occurred: dashboard/search/preview debug statements printed on every request, increasing log volume during normal navigation.
- Change made: Added `debug_log()` gated by `APP_DEBUG_LOGS=1`. Error logs remain visible.

### 3. PostgreSQL grouping could fail on migrated schemas
- File: `app.py`
- Lines: 1174, 1353, 1397, 1494, 1927, 2521, 2835
- Why it occurred: several queries grouped only by `hh.id` while selecting other household columns. Fresh PostgreSQL schemas with a primary key often allow this, but migrated schemas or stricter query contexts can reject it.
- Change made: Expanded all affected `GROUP BY` clauses to include selected non-aggregated household columns.

### 4. Print Preview household API could return HTTP 500
- File: `app.py`
- Line: 2521
- Why it occurred: `/api/preview/households` used incomplete grouping in an aggregate query. When it fails, `print_reports.html` shows the generic "Could not load preview" message.
- Change made: Fixed the household preview `GROUP BY` clause. `/api/preview/residents`, `/api/preview/households`, and `/api/preview/audit` all return JSON on success and JSON error payloads on failure.

### 5. Search suggestions could disappear because stale responses won the race
- Files: `templates/view_members.html`, `templates/view_households.html`, `templates/user_view_members.html`, `templates/user_view_households.html`
- Lines: `view_members.html:338`, `view_households.html:183`, `user_view_members.html:507`, `user_view_households.html:466`
- Why it occurred: rapid typing started multiple fetches. Sequence checks existed, but old requests were still in flight and could still cause UI churn.
- Change made: Added `AbortController` cancellation for resident and household suggestion fetches.

### 6. Remaining `NOW()` calls
- File: `app.py`
- Lines: 607, 804
- Why it occurred: `NOW()` is PostgreSQL-safe, but the audit requested replacing remaining date/time function variants.
- Change made: Replaced `NOW()` with `CURRENT_TIMESTAMP`.

## PostgreSQL Compatibility

- No remaining `MONTH()`, `YEAR()`, `IFNULL()`, `CURDATE()`, `DATE_FORMAT()`, or `NOW()` calls were found in `app.py`, `templates`, or `init_db_render.py`.
- Month and year filters use `EXTRACT(...)`.
- Case-insensitive searches use `ILIKE`.
- Deceased audit-log matching uses `ILIKE`.

## Statistics Verification

- Total residents: `/api/dashboard` returns `len(residents)` after filters.
- Male/female residents: counted from returned resident rows by `gender`.
- Deceased residents: counted from returned resident rows where `status == 'Deceased'`.
- Household counts: aggregated in SQL from `households` left-joined to `household`.
- Monthly registrations: generated in backend `monthData`; frontend now consumes that backend series for monthly charts.
- Monthly deceased chart: uses `date_of_death` when available.

## Performance Findings

- Slow page loads are most likely from repeated full-page queries and repeated new PostgreSQL connections per request.
- Search endpoints use `%term%` `ILIKE`, which cannot use normal btree indexes efficiently.
- Dashboard resident queries contain correlated subqueries into `audit_logs` per resident. Indexes are required for this to stay fast.
- Pages rendering all residents/households can become slow as table size grows.

## Optimizations Applied

- Added audit indexes:
  - `idx_audit_logs_target_action_created`
  - `idx_audit_logs_action_created`
- Added optional trigram search indexes when `pg_trgm` is available:
  - `idx_household_name_trgm`
  - `idx_households_search_trgm`
- If `pg_trgm` is unavailable, startup logs a warning and continues.

## Recommended Next Optimizations

- Add pagination to resident, household, and audit pages.
- Replace dashboard correlated audit subqueries with pre-aggregated CTEs when data grows.
- Use a PostgreSQL connection pool instead of opening a new connection per request.
- Add `EXPLAIN ANALYZE` checks on `/api/dashboard`, `/search_members`, `/search_households`, and print preview queries using production-sized data.
- Consider normalizing `audit_logs.new_value` into `JSONB` for status-change queries.

## Render Deployment Checklist

- Set `DATABASE_URL` in Render environment variables.
- Set `APP_DEBUG_LOGS=0` or omit it for production; set `APP_DEBUG_LOGS=1` only while diagnosing.
- Run the app once and confirm startup creates indexes without fatal errors.
- If `pg_trgm` extension is denied, search still works but may be slower.
- Confirm `/api/dashboard` returns HTTP 200 while logged in.
- Confirm `/api/preview/residents`, `/api/preview/households`, and `/api/preview/audit` return JSON while logged in as admin.
- Open `/analytics?debug=1` only during testing to view frontend dashboard traces.
- Verify Render logs contain no PostgreSQL `GROUP BY` errors.
- Keep `debug=False` for Flask in production.
