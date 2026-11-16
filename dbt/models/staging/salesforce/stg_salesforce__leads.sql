-- One row per live Lead: latest extracted version of each Id, deleted rows removed.
with ranked as (
    select
        *,
        row_number() over (partition by Id order by SystemModstamp desc, _extracted_at desc) as version_rank
    from {{ source('salesforce', 'lead') }}
)

select
    Id                                  as lead_id,
    'salesforce'                        as source_system,
    Synthetic_Key__c                    as synthetic_key,
    FirstName                           as first_name,
    LastName                            as last_name,
    lower(trim(Email))                  as email,
    Phone                               as phone,
    LeadSource                          as lead_source,
    Status                              as status,
    Program_of_Interest__c              as program_interest,
    Term_of_Interest__c                 as term_interest,
    IsConverted = 'true'                as is_converted,
    ConvertedContactId                  as converted_contact_id,
    cast(CreatedDate as timestamp)      as created_at,
    cast(SystemModstamp as timestamp)   as modified_at
from ranked
where version_rank = 1
  and IsDeleted = 'false'
