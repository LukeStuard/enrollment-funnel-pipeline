# Enrollment Funnel Pipeline: Progress

## 2026-11-16: Phase 0 started

- Chose the project: enrollment funnel ELT pipeline with dbt, to close the modern data stack gap.
- Chose MotherDuck Lite as the prod warehouse from day one (snapshots need persistent state between CI runs) with a local DuckDB dev target.
- Source org: gatewayDev. Pulled describes for Application__c and Lead; gaps recorded in the brief.
- Scaffold committed: folder layout and .gitignore. Private repo created with gh.
- Installed and authenticated the GitHub CLI on the work PC.
- Settled the four open questions (see Decisions in the brief): real conversion via an Application trigger, include existing Applications, add past terms, enable audit fields.
- Added two entry paths to the design: 40% lead-first, 60% direct (stealth) applicants, with a larger inquiry pool and deliberate email-mismatch misses for a duplicate test.
- Created the MotherDuck Lite workspace and the R2 bucket enrollment-funnel-raw (public access disabled). No tokens yet.
- Python 3.13.5 venv; pinned duckdb 1.5.6 (inside MotherDuck's 1.4.1 to 1.5.6 client range), dbt-core 1.12.7, dbt-duckdb 1.11.1. Chose dbt v1.12 over v2 (see Decisions).
- API 67.0+ defaults Apex to user mode: handlers run explicitly in system mode (as system DML, WITH SYSTEM_MODE queries); tests use a FunnelTestData helper with system-mode DML and the duplicate rule header set to allow save. The generator must send the same duplicate rule header.
- Full org test run: 46/46 passing (11 funnel, 35 gateway and intake), so the new triggers don't break the shared org.
- Full load attempt hit STORAGE_LIMIT_EXCEEDED (Developer Edition data storage is 5 MB; the load needed about 32 MB). Should have checked storage before loading; cleared it and added a preflight to load.py.
- Generator now splits output: data/salesforce (current cycle) and data/archive (legacy export, snake_case columns, LEG- keys). Default --applicants set to 1150 to fit.
- Current-cycle load: 1,204 records (about 2.4 MB, 1.6 MB left), 5/5 steps clean, 41 Leads converted by the trigger, 4 deliberately unconverted (email mismatch).
- Archive: 770 applicants, 1,051 Leads, 5,635 stage events, Fall 2025 through Fall 2026.
## 2026-11-16: Extract integration user and client credentials

- Funnel_Extract permission set: read and View All on Lead, Contact, Application__c, Stage_Event__c; Account read (required by Contact); read on 20 fields only; API Enabled; no create, edit or delete. Verified by querying ObjectPermissions in the org.
- User funnel.extract@enrollment-funnel-pipeline.dev: last Salesforce license in gatewayDev (4 of 4 now used), Minimum Access - Salesforce profile, Salesforce CRM Content turned off (no Content feature licenses left, and not needed).
- External Client App "Enrollment Funnel Extract", separate from the gateway and intake apps (one app per trust boundary): client credentials only, scope api only, Run As the extract user. Consumer key and secret in Credential Manager (EnrollmentFunnel-SF); scripts/GatewayCredential.ps1 copied from the gateway repo to read it.
- Live checks as the extract user through a real client-credentials token:
  - Token scope api only: PASS
  - Reads all 191 generator Leads, including converted ones: PASS
  - Reads all 761 generator stage events: PASS
  - Applicant_Name__c (not granted) returns INVALID_FIELD: PASS
  - Creating a Lead is refused ("entity type cannot be inserted"): PASS
- Tightened Permitted Users to admin-approved with only Funnel_Extract approved; token still issues: PASS
- Admin user's email moved from the employer address to a personal one, so org access doesn't depend on an employer inbox.
## 2026-11-16: Phase 3 extract

- R2 API token scoped to the enrollment-funnel-raw bucket only (object read, write, list), stored in Credential Manager (EnrollmentFunnel-R2). scripts/Use-FunnelEnv.ps1 sets the session's environment variables from Credential Manager; nothing on disk.
- DuckDB (httpfs, R2 secret, r2:// URLs) handles all R2 reads and writes, so no boto3: one credential path shared by the extract and dbt.
- extract/upload_archive.py: legacy CSVs to archive/<table>/data.parquet (1,051 leads, 770 contacts, 770 applications, 5,635 stage events).
- extract/salesforce_extract.py: Bulk API 2.0 queryAll per object as the read-only extract user (client credentials), only the 20 fields Funnel_Extract can read. Writes salesforce/<object>/extracted_at=<UTC>/data.parquet with _extracted_at and _sobject. Raw columns kept as text; dbt applies types.
- Incremental: watermark = max(SystemModstamp) already in R2, minus a 10-minute lookback. Overlap rows are expected and deduplicated in dbt (latest version per Id).
- First full extract: Lead 2,373 rows = 191 live + 2,182 deleted (verified by query). queryAll returns deleted rows until Salesforce purges them, even after the Recycle Bin is emptied; staging filters on IsDeleted.
- Second run picked up the watermark and re-pulled only the final 10 minutes of activity, as designed.
- requests pinned (Salesforce HTTP calls); boto3 installed then removed as unneeded.

