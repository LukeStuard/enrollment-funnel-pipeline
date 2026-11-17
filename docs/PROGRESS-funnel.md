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
## 2026-11-16: Phase 4 part 1, dbt staging

- dbt project in dbt/ (dbt-core 1.12.7, dbt-duckdb 1.11.1). profiles.yml is committed: the dev target is a local DuckDB file and the R2 secret is built only from environment variables.
- Sources read Parquet straight from R2 (external_location with read_parquet over every extract folder). Salesforce sources have freshness checks (warn 36h, error 72h); the archive has none, since it's a one-time load.
- Eight staging models, four per source, with one shared shape: Salesforce keeps the latest version of each Id (removes lookback duplicates) and drops deleted rows; the archive's legacy column names are mapped onto the same columns; timestamps typed (UTC), emails lowercased and trimmed, source_system added.
- 32 tests (unique and not-null keys, accepted values for every status and stage): 40/40 passing against real R2; source freshness passing.
- Verified offline first against a local fake lake built from generator output (raw_root var override).
## 2026-11-16: Phase 4 part 2, intermediate and marts

- terms seed (term calendar: start date, order, academic year); schema macro so schemas are named staging, intermediate, marts, reference.
- Intermediate: unions of both sources (leads, contacts, applications, stage events); int_applicant_entry tags each applicant lead-first or direct via the conversion link; int_application_milestones gives the first time each application reached each stage.
- Marts: fct_applications (entry path, milestones, outcome flags, days between stages; falls back to CreatedDate and Submitted_Date__c for demo records with no stage history), fct_stage_events, fct_funnel_by_term_program (inquiries, applicants by entry path, submitted, admitted, denied, enrolled, inquiry-to-applicant, admit and yield rates).
- Data quality tests set to warn (known issues, not pipeline bugs): likely duplicate people, missing program of interest, missing submitted date. Hard-fail tests: relationships (applications to contacts, events to applications and leads, terms to the seed) and one row per term and program in the funnel mart (custom generic test, no packages).
- Real data: 77 pass, 3 warn, 0 error. The duplicate test found exactly the injected email mismatches: 4 in Salesforce (the Leads the trigger couldn't convert) and 23 in the archive.
## 2026-11-16: Phase 4 part 3, origin, snapshots, MotherDuck prod

- origin column (generator or demo) on the intermediate models and marts, and part of the funnel mart's grain (term, program, origin). Demo = records the gateway and intake projects created in the shared org; confirmed they explained Spring 2027's 7 enrollments (51 demo vs 124 generator applications, 0 generator enrolled).
- Snapshots (SCD Type 2, timestamp strategy on modified_at, hard deletes invalidate) on Salesforce Applications and Leads. Tested locally: a Draft to Submitted change produced two versions with correct valid-from and valid-to.
- MotherDuck: service account funnel_pipeline with a Read/Write token (Credential Manager: EnrollmentFunnel-MotherDuck; Use-FunnelEnv.ps1 sets MOTHERDUCK_TOKEN). Database enrollment_funnel created as the service account, so it belongs to the service account.
- prod target (md:enrollment_funnel). R2 reads run in MotherDuck's cloud engine using the temporary R2 secret; first prod build failed because the cloud engine sent its own AWS region (us-west-2), which R2 rejects. Fixed with region: auto on the R2 secret in both targets.
- Prod and dev: 81 pass, 3 warn (the deliberate defects), 0 error.
## Phase 5: Dashboard (2026-11-16)

**Tool change.** The planned Evidence template has become Evidence Studio, a hosted product with its own CLI and a required account. Switched to Observable Framework 1.13.4: a static site generator whose Python data loaders query the warehouse at build time, so the published site holds only pre-aggregated CSVs and never connects to the database from the browser.

**Pages.** Overview (KPI cards, funnel by term, conversion rates by term), Programs, Entry paths (lead-first vs. direct), Time between stages (box plots by program), Data quality. Every page has an origin toggle: synthetic data set only, or including the hand-made demo records.

**Read-only access.** MotherDuck Lite has no read scaling tokens and no filtered shares (INCLUDE_PATTERN is not enabled on Lite). The dashboard uses a second service account, funnel_dashboard, that reads a restricted, hidden share of enrollment_funnel instead of the database itself. Verified: the share returns rows (45 from the funnel mart) and CREATE is refused. Tradeoff: on this plan the share covers the whole database rather than only the marts schema; the loaders query marts only.

**New mart.** dq_issues: one row per flagged record for likely_duplicate_person, missing_program_interest and missing_submitted_date, built from the same rules as the warn-level dbt tests, so the page counts and the build warnings always agree (27, 32, 12).

**Privacy.** The applications loader excludes names and contact details. The data quality detail shows the synthetic example.com emails only, so the person-matching defect can be seen.

**Fixes during build.**
- A FileAttachment resolves to its data only in other code blocks; loading and using it in the same block gave a pending promise (issues.map is not a function). Load and use are now separate blocks.
- Inline expressions get their own wrapper, so cards placed inline stacked instead of filling the grid. Card rows are now built with display(html`...`) in a code block.
- Facet labels on the timing plot were clipped; added marginRight.

**Next.** Deploy the static build to Cloudflare (Workers static assets).

