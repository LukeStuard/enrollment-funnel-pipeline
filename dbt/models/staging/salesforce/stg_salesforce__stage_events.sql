-- One row per live stage event: latest extracted version of each Id, deleted rows removed.
with ranked as (
    select
        *,
        row_number() over (partition by Id order by SystemModstamp desc, _extracted_at desc) as version_rank
    from {{ source('salesforce', 'stage_event') }}
)

select
    Id                                  as stage_event_id,
    'salesforce'                        as source_system,
    Source__c                           as event_source,
    Lead__c                             as lead_id,
    Contact__c                          as contact_id,
    Application__c                      as application_id,
    From_Stage__c                       as from_stage,
    To_Stage__c                         as to_stage,
    cast(Event_Date__c as timestamp)    as event_at
from ranked
where version_rank = 1
  and IsDeleted = 'false'
