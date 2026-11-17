-- One row per funnel stage change across both systems, with the program and
-- term it belongs to (from the Application, or the Lead's interest before
-- an Application exists).
with events as (
    select * from {{ ref('int_stage_events') }}
),

apps as (
    select application_id, program, term, origin from {{ ref('int_applications') }}
),

leads as (
    select lead_id, program_interest, term_interest, origin from {{ ref('int_leads') }}
)

select
    e.stage_event_id,
    e.source_system,
    coalesce(a.origin, l.origin, 'demo') as origin,
    e.event_source,
    e.lead_id,
    e.contact_id,
    e.application_id,
    case when e.application_id is not null then 'application' else 'lead' end as event_scope,
    e.from_stage,
    e.to_stage,
    e.event_at,
    coalesce(a.program, l.program_interest, 'Unknown')  as program,
    coalesce(a.term, l.term_interest)                    as term
from events e
left join apps a  on a.application_id = e.application_id
left join leads l on l.lead_id = e.lead_id
