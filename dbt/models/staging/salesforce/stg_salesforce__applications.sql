-- One row per live Application: latest extracted version of each Id, deleted rows removed.
with ranked as (
    select
        *,
        row_number() over (partition by Id order by SystemModstamp desc, _extracted_at desc) as version_rank
    from {{ source('salesforce', 'application') }}
)

select
    Id                                      as application_id,
    'salesforce'                            as source_system,
    Name                                    as application_number,
    Synthetic_Key__c                        as synthetic_key,
    Applicant__c                            as contact_id,
    Program__c                              as program,
    Term__c                                 as term,
    Status__c                               as status,
    cast(Submitted_Date__c as date)         as submitted_date,
    cast(CreatedDate as timestamp)          as created_at,
    cast(SystemModstamp as timestamp)       as modified_at
from ranked
where version_rank = 1
  and IsDeleted = 'false'
