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