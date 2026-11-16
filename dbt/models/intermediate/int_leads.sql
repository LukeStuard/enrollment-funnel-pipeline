-- Leads from both source systems in one shape: the legacy archive (earlier terms)
-- and Salesforce (current cycle).
select * from {{ ref('stg_salesforce__leads') }}
union all by name
select * from {{ ref('stg_archive__leads') }}
