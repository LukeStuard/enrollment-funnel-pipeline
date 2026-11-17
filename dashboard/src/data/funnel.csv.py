# Funnel counts and rates by term, program and origin (fct_funnel_by_term_program).
from _warehouse import write_csv

write_csv("""
    SELECT term, term_order, term_start_date, is_current_cycle, program, origin,
           inquiries, applicants, lead_first_applicants, direct_applicants,
           submitted, admitted, denied, enrolled
    FROM {marts}.fct_funnel_by_term_program
    ORDER BY term_order, program, origin
""")
