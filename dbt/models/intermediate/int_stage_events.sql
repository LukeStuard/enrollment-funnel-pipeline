-- Stage events from both source systems in one shape: the legacy archive (earlier terms)
-- and Salesforce (current cycle).
select * from {{ ref('stg_salesforce__stage_events') }}
union all by name
select * from {{ ref('stg_archive__stage_events') }}
