-- First time each Application reached each stage, from the stage event history.
select
    application_id,
    min(event_at) filter (where to_stage = 'Applicant')  as applicant_event_at,
    min(event_at) filter (where to_stage = 'Submitted')  as submitted_event_at,
    min(event_at) filter (where to_stage = 'In Review')  as in_review_at,
    min(event_at) filter (where to_stage = 'Admitted')   as admitted_at,
    min(event_at) filter (where to_stage = 'Denied')     as denied_at,
    min(event_at) filter (where to_stage = 'Enrolled')   as enrolled_at,
    min(event_at) filter (where to_stage = 'Withdrawn')  as withdrawn_at,
    count(*)                                             as stage_event_count
from {{ ref('int_stage_events') }}
where application_id is not null
group by application_id
