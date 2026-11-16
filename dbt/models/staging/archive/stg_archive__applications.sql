-- Legacy CRM applications mapped onto the same shape as stg_salesforce__applications.
select
    legacy_application_id               as application_id,
    'archive'                           as source_system,
    legacy_application_id               as application_number,
    legacy_application_id               as synthetic_key,
    legacy_contact_id                   as contact_id,
    program,
    term,
    status,
    cast(submitted_date as date)        as submitted_date,
    cast(created_at as timestamp)       as created_at,
    cast(created_at as timestamp)       as modified_at
from {{ source('archive', 'applications') }}
