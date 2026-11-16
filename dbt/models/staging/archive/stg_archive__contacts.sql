-- Legacy CRM contacts mapped onto the same shape as stg_salesforce__contacts.
select
    legacy_contact_id                   as contact_id,
    'archive'                           as source_system,
    legacy_contact_id                   as synthetic_key,
    first_name,
    last_name,
    lower(trim(email))                  as email,
    phone,
    cast(created_at as timestamp)       as created_at,
    cast(created_at as timestamp)       as modified_at
from {{ source('archive', 'contacts') }}
