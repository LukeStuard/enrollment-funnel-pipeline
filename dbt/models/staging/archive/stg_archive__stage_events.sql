-- Legacy CRM stage history mapped onto the same shape as stg_salesforce__stage_events.
select
    legacy_event_id                     as stage_event_id,
    'archive'                           as source_system,
    'Legacy'                            as event_source,
    legacy_lead_id                      as lead_id,
    legacy_contact_id                   as contact_id,
    legacy_application_id               as application_id,
    from_stage,
    to_stage,
    cast(event_at as timestamp)         as event_at
from {{ source('archive', 'stage_events') }}
