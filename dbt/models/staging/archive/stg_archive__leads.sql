-- Legacy CRM leads mapped onto the same shape as stg_salesforce__leads.
select
    legacy_lead_id                      as lead_id,
    'archive'                           as source_system,
    legacy_lead_id                      as synthetic_key,
    first_name,
    last_name,
    lower(trim(email))                  as email,
    phone,
    lead_source,
    status,
    program_interest,
    term_interest,
    converted_contact_id is not null    as is_converted,
    converted_contact_id,
    cast(created_at as timestamp)       as created_at,
    cast(created_at as timestamp)       as modified_at
from {{ source('archive', 'leads') }}
