# Enrollment Funnel Pipeline: Brief

Status: Phase 0 in progress

## Goal

An automated ELT pipeline that turns Salesforce admissions data into a tested, version-controlled enrollment funnel: how many inquiries become applicants, admits, and enrolled students, by program, term, and source, and how long each step takes. It rebuilds the idea behind a real enrollment funnel workbook with a modern data stack, using only synthetic data.

## Skills it demonstrates

- Incremental extraction from Salesforce (Bulk API 2.0, SystemModstamp watermark, deletes)
- Data lake landing (raw Parquet in Cloudflare R2)
- dbt modeling: sources, staging, intermediate, marts, tests, docs
- Slowly changing dimensions (dbt snapshots, SCD Type 2)
- Hosted warehouse (MotherDuck) with a separate local dev target (DuckDB)
- BI as code (Evidence, deployed as a static site on Cloudflare)
- Orchestration and monitoring (GitHub Actions)

## Architecture

Salesforce (gatewayDev) -> Python Bulk API extract -> raw Parquet in R2 -> dbt (prod: MotherDuck, dev: local DuckDB) -> Evidence static site on Cloudflare. GitHub Actions runs the chain on a schedule.

Everything runs on free tiers: Salesforce Developer Edition, R2, MotherDuck Lite, GitHub Actions, Cloudflare static hosting.

## Source org

gatewayDev (orgfarm-5ea30c60fa, org ID 00DjV000006UtBhUAK), shared with Safe Agent Gateway and Safe Document Intake. Every CLI command names --target-org gatewayDev explicitly.

Existing objects used:
- Application__c: Applicant__c (Contact), Program__c, Term__c, Status__c (Draft, Submitted, In Review, Admitted, Denied, Enrolled, Withdrawn), Submitted_Date__c
- Lead: standard fields only for funnel purposes (Status, LeadSource, CreatedDate, conversion fields)

Gaps to close in Phase 1:
- Lead has no program or term of interest
- Term__c only goes back to Fall 2026, so a year of history needs earlier terms
- No external IDs, so generator reruns could duplicate records
- No stage history: Application__c field history is off, and history rows can't be backdated

## Funnel stages

Inquiry (Lead) -> Applicant (Application Draft) -> Submitted -> In Review -> Admitted -> Enrolled
Exits: Lead closed not converted, Denied, Withdrawn

## History strategy

Two independent sources, compared in the marts:
1. Stage_Event__c: one record per stage change (from stage, to stage, event date, lookups to Lead and Application). The generator backfills a realistic timeline; new changes are logged as they happen.
2. dbt snapshots: SCD Type 2 history captured by the warehouse on every run, regardless of what the source kept.

## Phase plan

- Phase 0: Scaffold, repo, accounts (MotherDuck Lite and service account token, R2 bucket and scoped token), pin and verify tool versions
- Phase 1: Salesforce data model in gatewayDev (Lead fields, Term values, Stage_Event__c, external IDs, live stage logging, permission set, layouts), plus a read-only extract integration user
- Phase 2: Seeded synthetic data generator (cohorts Fall 2025 through Fall 2027, realistic conversion rates and time lags, a few deliberate data quality defects for the tests to catch)
- Phase 3: Incremental extract to Parquet in R2
- Phase 4: dbt project: sources and freshness, staging, intermediate, marts, snapshots, tests, docs
- Phase 5: Evidence dashboard deployed to Cloudflare
- Phase 6: GitHub Actions orchestration, failure alerts, live change test (edit a record in the org, see it flow through)
- Phase 7: README, redacted evidence screenshots, LinkedIn post

## Decisions

1. Lead conversion is real, mirroring a production pattern: an after-insert trigger on Application__c matches a Lead by the applicant's email and converts it into the existing Contact (no Opportunity). The generator creates Lead, then Contact, then Application, and the trigger converts. ConvertedDate cannot be backdated, so Stage_Event__c is the source of truth for conversion timing. Code is a clean rewrite of the pattern, not a copy.
2. Existing gateway and intake Applications are included. Their Contacts have no Leads, so they enter the funnel at the Applicant stage; marts use left joins for missing inquiry history.
3. Term__c gains Fall 2025, Spring 2026, and Summer 2026.
4. "Set Audit Fields upon Record Creation" is enabled for the generator, so CreatedDate is backdated on insert. SystemModstamp stays real and is the extract watermark; CreatedDate and event dates are business time.
5. Two entry paths, mirroring a real admissions pattern: lead-first applicants (inquiry Lead, then signup, then Application, converted by the trigger) and direct "stealth" applicants (no Lead). The split is a generator setting, defaulting to 40% lead-first and 60% direct; real institutions vary widely (one sees about 80% direct). Most inquiries never apply, so the generator creates a larger Lead pool from a separate inquiry-to-applicant rate. A small share of lead-first applicants sign up with a different email, so the trigger misses them; a dbt duplicate test is expected to catch these.
6. dbt Core v1.12 (dbt-duckdb 1.11.1, duckdb 1.5.6), not dbt v2. v2's DuckDB adapter is in beta and its bundled driver can't load the extensions needed to read Parquet from R2 without a separate driver install. CI runs dbt parse --use-v2-parser to keep the project v2-compatible; migrating to v2 is an optional final phase.

## Conventions

- No CIAM data, names, or systems in this repo
- Zips and scripts named with the funnel- prefix
- New Salesforce metadata ships with page layout and permission set steps
- PROGRESS entry before every commit; pull at session start, push at session end
- Check docs for the installed version of each library before writing code against it