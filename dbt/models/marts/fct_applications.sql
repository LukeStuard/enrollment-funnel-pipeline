-- One row per Application, with entry path, term attributes, milestone
-- timestamps and time between stages.
--
-- Milestones come from stage events. Applications with no events (demo records
-- created before the stage log existed) fall back to CreatedDate for the
-- application date and Submitted_Date__c for the submission date.
with apps as (
    select * from {{ ref('int_applications') }}
),

m as (
    select * from {{ ref('int_application_milestones') }}
),

entry as (
    select * from {{ ref('int_applicant_entry') }}
),

terms as (
    select * from {{ ref('terms') }}
)

select
    a.application_id,
    a.application_number,
    a.source_system,
    a.origin,
    a.contact_id,
    e.lead_id,
    e.entry_path,
    e.lead_source,
    a.program,
    a.term,
    t.term_start_date,
    t.term_order,
    t.academic_year,
    t.term_start_date > current_date                                    as is_current_cycle,
    a.status,

    e.inquiry_at,
    coalesce(m.applicant_event_at, a.created_at)                        as applied_at,
    coalesce(m.submitted_event_at, cast(a.submitted_date as timestamp)) as submitted_at,
    m.in_review_at,
    m.admitted_at,
    m.denied_at,
    m.enrolled_at,
    m.withdrawn_at,

    coalesce(m.submitted_event_at, a.submitted_date) is not null
        or a.status <> 'Draft'                                          as is_submitted,
    m.admitted_at is not null or a.status in ('Admitted', 'Enrolled')   as is_admitted,
    m.denied_at is not null or a.status = 'Denied'                      as is_denied,
    a.status = 'Enrolled'                                               as is_enrolled,

    date_diff('day', e.inquiry_at, coalesce(m.applicant_event_at, a.created_at))       as days_inquiry_to_apply,
    date_diff('day', coalesce(m.applicant_event_at, a.created_at), m.submitted_event_at) as days_apply_to_submit,
    date_diff('day', m.submitted_event_at, coalesce(m.admitted_at, m.denied_at))         as days_submit_to_decision,
    coalesce(m.stage_event_count, 0)                                                     as stage_event_count
from apps a
left join m     on m.application_id = a.application_id
left join entry e on e.contact_id = a.contact_id
left join terms t on t.term = a.term
