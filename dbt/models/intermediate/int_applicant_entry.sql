-- How each applicant (a Contact with at least one Application) entered the funnel.
--   lead-first: a Lead was converted into this Contact, so there is inquiry history.
--   direct:     no Lead converted into this Contact ("stealth" applicant).
-- An applicant who inquired under a different email shows up as direct here,
-- because the system never linked the two; see the likely-duplicate test.
with applicants as (
    select distinct contact_id
    from {{ ref('int_applications') }}
),

converted_leads as (
    select
        converted_contact_id as contact_id,
        lead_id,
        created_at as inquiry_at,
        lead_source,
        row_number() over (partition by converted_contact_id order by created_at) as lead_rank
    from {{ ref('int_leads') }}
    where is_converted
)

select
    a.contact_id,
    l.lead_id,
    l.inquiry_at,
    l.lead_source,
    case when l.lead_id is not null then 'lead-first' else 'direct' end as entry_path
from applicants a
left join converted_leads l
    on l.contact_id = a.contact_id
   and l.lead_rank = 1
