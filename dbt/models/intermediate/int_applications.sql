-- Applications from both source systems in one shape: the legacy archive (earlier terms)
-- and Salesforce (current cycle).
select * from {{ ref('stg_salesforce__applications') }}
union all by name
select * from {{ ref('stg_archive__applications') }}
