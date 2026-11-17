-- One row per record flagged by a known data quality check, so the dashboard
-- can show them (the dbt tests only warn in the build log). Same rules as the
-- warn-level tests:
--   likely_duplicate_person   unconverted Lead matching a Contact on name and
--                             phone (an inquiry who signed up with another email)
--   missing_program_interest  inquiry that didn't name a program
--   missing_submitted_date    Application past Draft with no submitted date
with leads as (
    select * from {{ ref('int_leads') }}
),

contacts as (
    select * from {{ ref('int_contacts') }}
),

apps as (
    select * from {{ ref('int_applications') }}
)

select
    'likely_duplicate_person'        as check_name,
    l.lead_id                         as record_id,
    l.source_system,
    l.origin,
    l.term_interest                   as term,
    'Lead ' || l.email || ' matches Contact ' || c.email as detail
from leads l
join contacts c
  on lower(l.first_name) = lower(c.first_name)
 and lower(l.last_name)  = lower(c.last_name)
 and l.phone             = c.phone
 and l.source_system     = c.source_system
where not l.is_converted

union all

select
    'missing_program_interest',
    lead_id,
    source_system,
    origin,
    term_interest,
    'Inquiry with no program of interest'
from leads
where program_interest is null

union all

select
    'missing_submitted_date',
    application_id,
    source_system,
    origin,
    term,
    'Status ' || status || ' but no submitted date'
from apps
where status <> 'Draft'
  and submitted_date is null
