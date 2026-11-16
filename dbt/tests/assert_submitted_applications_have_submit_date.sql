-- Warns on Applications past Draft with no Submitted_Date__c recorded
-- (a known data entry gap). fct_applications falls back to the stage event.
{{ config(severity = 'warn') }}

select application_id, source_system, status
from {{ ref('int_applications') }}
where status <> 'Draft'
  and submitted_date is null
