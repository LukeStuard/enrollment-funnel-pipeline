-- Leads from both source systems in one shape: the legacy archive (earlier terms)
-- and Salesforce (current cycle).
--
-- origin: 'generator' for the synthetic data set (archive rows and Salesforce rows
-- with a Synthetic_Key__c), 'demo' for records the gateway and intake projects
-- created in the shared org.
with unioned as (
    select * from {{ ref('stg_salesforce__leads') }}
    union all by name
    select * from {{ ref('stg_archive__leads') }}
)

select
    *,
    case
        when source_system = 'archive' or synthetic_key is not null then 'generator'
        else 'demo'
    end as origin
from unioned
