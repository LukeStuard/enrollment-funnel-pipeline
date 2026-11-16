-- Funnel counts and rates by term and program, ready for the dashboard.
--   inquiries:                Leads interested in that term and program
--   applicants:               Applications, split by entry path
--   inquiry_to_applicant_rate: lead-first applicants / inquiries
--   admit_rate:               admitted / decided (admitted + denied)
--   yield_rate:               enrolled / admitted
-- Current-cycle terms are still in flight, so their rates will move.
with inquiries as (
    select
        term_interest                         as term,
        coalesce(program_interest, 'Unknown') as program,
        count(*)                              as inquiries
    from {{ ref('int_leads') }}
    where term_interest is not null
    group by 1, 2
),

apps as (
    select
        term,
        program,
        count(*)                                          as applicants,
        count(*) filter (where entry_path = 'lead-first') as lead_first_applicants,
        count(*) filter (where entry_path = 'direct')     as direct_applicants,
        count(*) filter (where is_submitted)              as submitted,
        count(*) filter (where is_admitted)               as admitted,
        count(*) filter (where is_denied)                 as denied,
        count(*) filter (where is_enrolled)               as enrolled
    from {{ ref('fct_applications') }}
    group by 1, 2
),

joined as (
    select
        coalesce(a.term, i.term)          as term,
        coalesce(a.program, i.program)    as program,
        coalesce(i.inquiries, 0)          as inquiries,
        coalesce(a.applicants, 0)         as applicants,
        coalesce(a.lead_first_applicants, 0) as lead_first_applicants,
        coalesce(a.direct_applicants, 0)  as direct_applicants,
        coalesce(a.submitted, 0)          as submitted,
        coalesce(a.admitted, 0)           as admitted,
        coalesce(a.denied, 0)             as denied,
        coalesce(a.enrolled, 0)           as enrolled
    from apps a
    full outer join inquiries i
        on i.term = a.term and i.program = a.program
)

select
    j.term,
    t.term_order,
    t.term_start_date,
    t.term_start_date > current_date as is_current_cycle,
    j.program,
    j.inquiries,
    j.applicants,
    j.lead_first_applicants,
    j.direct_applicants,
    j.submitted,
    j.admitted,
    j.denied,
    j.enrolled,
    round(j.lead_first_applicants / nullif(j.inquiries, 0), 3)   as inquiry_to_applicant_rate,
    round(j.admitted / nullif(j.admitted + j.denied, 0), 3)      as admit_rate,
    round(j.enrolled / nullif(j.admitted, 0), 3)                 as yield_rate
from joined j
left join {{ ref('terms') }} t on t.term = j.term
