# Pre-defense refinement: review and release guide

November 5 toast/favicon follow-up: ordinary admin/auth flashes and registration
completion now share one toast surface; pre-action confirmations, corrective form
feedback, recovery warnings and report-preview messages remain. The original navy
house/three-people SVG has local PNG/ICO fallbacks. Only these three public icons
receive a one-day cache policy; authenticated pages remain no-store. No authentication,
record, schema, migration or production configuration change is included.

November 5 household-head UI follow-up: the owner reports migration 007 is already
installed and the feature is working in production. Do not reapply it. This release
refines the card, native review dialog, history presentation and single inline
feedback. Its only backend changes are read-only history name/date presentation
and scoped feedback categories. Existing migration-pending notes below describe
earlier releases. No production connection, SQL, push or deployment is part of this task.

November 4, 2026 (Asia/Manila). Local release preparation only; no production connection,
migration, seed import, credential change, deployment or push performed.
The owner's 30 households / 120 residents / 110 active / 10 deceased inventory
is owner-reported evidence. It was not independently queried here.

Follow-up after owner-reported deployment of `89c74ed`: compact directory search
toolbars, independent 10-row Analytics pages with full-set totals/charts, clearer
optional head controls, and early background/CSS loading are prepared. The exact
application candidate passed 94 focused tests (6.28 seconds), Python syntax and
JavaScript syntax checks. Live hosted visual acceptance remains to be performed;
no database connection, migration or deployment occurred. `RELEASE-FILES.txt` now
lists the 18 paths for this follow-up. Optional 007 remains unapplied and unverified.

## Immediate application release: no migration required

Release the interface, filters, age/pagination fixes, safe feedback and workflow changes
against the existing canonical 001–006 schema. **Do not run 007 for this release.**
Its eight unverified PostgreSQL cases block enabling the optional head schema only.
Without both optional tables, head/relationship controls stay hidden and the new head
POST returns 409. Existing household/resident creation, editing and detail views
remain available. No initializer, seed, credential operation or SQL is needed.

Essential release checks: **72 database-free tests passed** (2.38 seconds), including
production-mode `app:app` startup, health/login without a database connection,
six baseline form/detail pages, baseline household/resident saves and rejection of
forged head writes. These supplement the historical 1,259-case pass below; counts
overlap. No full-suite rerun or PostgreSQL pass is claimed for release preparation.
The exact parent-commit-plus-allowlist candidate was also exported into a temporary
directory and independently passed the same 72 tests (2.96 seconds), Python syntax
and all JavaScript syntax checks. No ignored or unrelated workspace file was needed.
The temporary candidate was removed after verification.

The original `89c74ed` release contained 49 approved paths. It included the refinement,
focused self-contained tests, inert optional SQL/tests for future validation, and prior
safety changes retiring nine obsolete connection/bootstrap helpers and three legacy
schema scripts. The existing administrator-only user-deletion regression is included.
It excludes all environment/private authentication files, local databases, archives,
generated output, legacy investigation/recovery tools, old audit reports and unrelated
local tooling/tests. Earlier excluded changes remain in the working tree.

Render's existing build (`python -m pip install -r requirements.txt`) and start
(`gunicorn --bind 0.0.0.0:$PORT app:app`) remain compatible and unchanged.
Requirements, authentication, database routing/pins and production settings are
unchanged from parent commit `6f5a95b`. No environment changes are required.
This is code/configuration compatibility evidence; the live service was not inspected.

Owner-controlled release sequence:

1. Review the local commit with `git show --stat HEAD` and `git show --name-only HEAD`.
   Preserve the currently deployed Render commit SHA. Confirm the existing service
   uses the intended repository/branch and has no migration/seed pre-deploy command.
2. Set Auto-Deploy to Off before pushing, then run `git push origin main` (no force).
   If Git reports a divergent remote, stop and reconcile; do not force-push.
3. On the same Render service, open Manual Deploy > Deploy a specific commit, select
   the prepared release SHA and click Deploy Commit. Keep the service URL and current
   database configuration. See [Render's manual deployment instructions](https://render.com/docs/deploys#manual-deploys).
4. Check health, existing admin login, household/resident counts, filters, details,
   reports and audit views. Head controls should be absent. Avoid live test mutations.
   On failure, redeploy the previous service commit; there is no database rollback
   for this application-only release. Do not reset/import/reinitialize the database.

## Existing application and changes

The existing Flask application already provides administrator-only CRUD,
CSRF/authentication, server-side searches, report filters, signed report scopes,
health opt-in, print/Word exports and audit history. These were retained.
The report preview already limits display to 100; exports already use all matches.
No resident portal, signup, general account dashboard or alternative login was added.

- Removed the shared notification bell/navigation and visible login illustration
  disclaimer. Operational/security/audit events and the existing inbox backend remain.
  The decorative image is not identified as an official hall photograph.
- Compact household tables retain actions; health and secondary demographics are
  available in the administrator resident detail view rather than directory payloads.
- Added combined directory status/gender/age/household/civil-status filters alongside
  existing search, active-state/reset controls and responsive household card layouts.
- Added explicit head designation/reassignment/clearing and assignment-specific
  relationships. Existing households start unassigned; surnames and ages infer nothing.
  Heads must be active members when newly selected. A deceased head remains in
  history until explicitly reassigned. Transfers/deletes of a current head are blocked
  until reassignment/clearing. Earlier relationship labels are retained, not copied.
- Unified scoped field/filter styling and native accessible feedback/confirmation
  dialogs, keeping existing application colors, modal workflows and security checks.

Corrected bugs: deceased ages now use the known death date (unknown dates stay
unknown); submitted ages are recalculated; NULL gender/civil values match the
existing Not recorded filter; out-of-range directory/member pages redirect safely;
late relationship validation rolls back the resident mutation; commit failures cannot
leave success flashes; rejected saves are recorded as FAILED, not SUCCESS.
An unavailable head can also be explicitly cleared without removing its history.
Rollback SQL locks its new tables before checking emptiness to prevent a race.
These changes do not mass-update existing resident values or infer health diagnoses.

## Exact files in this refinement

Runtime: `account_routes.py`, `dashboard_routes.py`, `directory_routes.py`,
`record_routes.py`, `reporting.py`, `validation.py`, `webapp.py`; new `household_roles.py`.

Existing templates: `templates/add_household.html`, `templates/add_member.html`,
`templates/base.html`, `templates/edit_member.html`, `templates/login.html`,
`templates/resident_detail.html`, `templates/view_household.html`,
`templates/view_households.html`, `templates/view_members.html`.
New includes: `templates/household_head_panel.html`, `templates/household_role_fields.html`,
`templates/resident_directory_filters.html`.

Assets: `static/js/ui_bridge.js`, `static/js/workflow-polish.js`;
new `static/js/defense-refinement.js`, `static/css/defense-refinement.css`.

Tests: `tests/test_admin_consistency.py`, `tests/test_homepage_visual.py`,
`tests/test_login_visual.py`, `tests/test_isolation_logs_templates.py`;
new `tests/test_defense_refinement.py`, `integration_tests/test_isolated_household_roles.py`.
New SQL: `migrations/optional/007_household_roles.up.sql` and
`migrations/optional/007_household_roles.down.sql`. This guide is also new.
Earlier dirty workspace changes are outside this refinement and must be retained/reviewed
when assembling a release. Git HEAD alone is not the complete candidate.

## Separate optional schema change

Canonical 001–006, authentication, connection isolation, fresh initialization and
legacy rehearsal/recovery tools were not edited for this refinement. The optional
007 is deliberately outside their migration glob and ledger. Neither startup,
`manage.py migrate` nor the fresh initializer installs it. Do not rerun the initializer
on the populated deployment, or use the old legacy rehearsal workflow for this change.

007 adds two empty metadata tables, supporting indexes and a composite uniqueness
constraint on resident ID/household ID. Composite foreign keys prevent head/relationship
membership mismatches; partial unique indexes prevent conflicting current heads.
Stable recorded IDs preserve designation history after deletion of a source record.
There is no data backfill, head inference, credential update or baseline record DML.
Its DDL takes locks and builds indexes; PostgreSQL execution remains to be validated.
The subset-column SET NULL syntax requires PostgreSQL 16+ (see the official
[PostgreSQL constraint documentation](https://www.postgresql.org/docs/16/ddl-constraints.html)).

Without 007 the application keeps existing workflows and hides the new head controls.
With 007 household/resident/head writes serialize on transaction advisory lock 762022, then validate
membership and the submitted assignment revision inside the existing transaction.

## Actual validation

Final database-free run: **1,259 passed, one deliberately deselected**, zero failures,
29.85 seconds. This includes 44 focused refinement cases. Syntax checks passed for
132 Python files and 20 JavaScript files; installed dependencies and whitespace
checks passed. Template/asset validation passed within the executed suite.
Use this command to reproduce the unit run without opening the machine-local private
recovery archive used by one historical style-freezing test:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider --tb=short --deselect=tests/test_restored_ui.py::test_every_original_inline_style_and_core_asset_unchanged
```

Tests cover head decisions/history/stale forms/membership, empty household creation,
resident saves and rollback, filters/pagination, age at death, privacy, auth/CSRF,
failed audits and equal preview/print/Word filters. A 125-record fixture proves the
100-row preview limit does not truncate print/Word exports.

Eight opt-in integration cases create only a NEW random-port temporary PostgreSQL
cluster with fictional records and temporary test authentication; they never select
an existing database or use owner credentials. Windows pg_ctl failed with
“could not create restricted token” (error 87), so all eight were skipped. No server
connection/SQL/migration was reached; generated cluster files were cleaned up.
For an owner-context isolated run before any production SQL approval:

```powershell
$env:RUN_ISOLATED_HEAD_TESTS='1'
try { .\.venv\Scripts\python.exe -B -m pytest integration_tests/test_isolated_household_roles.py -q -p no:cacheprovider --tb=short -rs }
finally { Remove-Item Env:RUN_ISOLATED_HEAD_TESTS -ErrorAction SilentlyContinue }
```

Native Chrome review used a loopback Flask fixture with mocked data/database access,
not production: compact dark-theme household details, head form, centered native
confirmation, Escape dismissal and focus restoration. The fixture server is stopped.
This is not evidence of live PostgreSQL behavior or hosted browser acceptance.

## Manual acceptance checklist

- Desktop and narrow mobile; light/dark; keyboard Tab/Shift+Tab, Escape and focus
  return; readable labels/tables, no bell, no hidden or broken actions.
- On isolated data: create an empty household, add/edit a resident, cancel, duplicate
  rejection, validation failure, failed save and confirmed delete. Success only after save.
- Explicit first head, reassignment, clearing, stale two-tab submissions, differing
  surnames, relationships, deceased head retained, transfer/delete guard and history.
- Combined name/ID/status/gender/civil/age/household filters, NULL/unknown values,
  reset, no matches, counts, pagination and age at death with known/unknown dates.
- Report preview/print/Word with >100 matches, all selected filters, long names and
  addresses, page breaks, empty results and explicit health inclusion/exclusion.
- Audit search/actor/action/entity/date/outcome; successful versus failed saves;
  session expiry, unauthorized routes and CSRF rejection; no audit editing.

## Later optional 007 procedure — not a prerequisite for the application release

1. Before enabling head storage, pass the isolated PostgreSQL tests and browser acceptance. Review the exact
   complete candidate, optional SQL and checksums; preserve the current release artifact.
2. Keep the same existing Render service/URL and configured new Neon database.
   Do not touch the original old Neon project, connection information or recovery databases.
   Preserve a current backup of the populated deployment before approving any DDL.
3. Schedule a brief write pause. A separately reviewed owner session must authenticate
   privately with verified TLS, verify exact endpoint/database/role, PostgreSQL 16+
   and applied canonical 001–006, and confirm the two new tables/constraint are absent.
   Capture aggregate counts/statuses and private preservation comparisons for existing
   records/accounts without displaying any credential values.
4. In one explicit transaction with bounded lock/statement timeouts, acquire existing
   migration lock 762019 then feature lock 762022, lock the baseline household tables,
   and apply only reviewed `007_household_roles.up.sql`. Recheck original counts and
   preservation comparisons, constraints/indexes and empty new tables before commit.
   Stop/roll back on a mismatch. Record this optional migration/checksum separately;
   do not forge a canonical ledger row. Do not run the supplied seed SQL again.
5. After a successful schema check, deploy only the reviewed release to the same
   Render service using the existing build/start configuration. No startup migration,
   new environment setting, service or password reset is needed for this feature.
   Verify existing administrator access and read-only screens/counts first. Keep
   fictional CRUD acceptance in the isolated environment, not the shared evaluation data.

No production SQL command is supplied for immediate execution: live SQL compatibility
and the exact release still need the checks above. This task did not deploy anything.

## Rollback

Before commit, a failed optional installation rolls back its transaction. After commit,
restore the previous application artifact on the same service; the additive tables
can remain and old code ignores them. Preserve any recorded head/relationship history.
Only if both new tables are empty may a separately approved explicit transaction run
the guarded down SQL. Its exclusive locks prevent concurrent insertion between the
emptiness check and removal. With recorded decisions, down refuses: roll back code
only. Never automatically restore/reseed/truncate or discard resident/admin records.
