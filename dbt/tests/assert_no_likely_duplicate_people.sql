-- Warns on unconverted Leads that look like the same person as an existing
-- Contact (same first name, last name and phone), but were never linked because
-- the emails differ. In this data set these are the deliberate email mismatches:
-- an inquiry that signed up with a different address. Real fix: merge them.
{{ config(severity = 'warn') }}

select
    l.lead_id,
    c.contact_id,
    l.source_system,
    l.first_name,
    l.last_name,
    l.email  as lead_email,
    c.email  as contact_email
from {{ ref('int_leads') }} l
join {{ ref('int_contacts') }} c
  on lower(l.first_name) = lower(c.first_name)
 and lower(l.last_name)  = lower(c.last_name)
 and l.phone             = c.phone
 and l.source_system     = c.source_system
where not l.is_converted
