# One row per application with entry path, outcome flags and days between stages.
# No names or contact details: the dashboard doesn't need them.
from _warehouse import write_csv

write_csv("""
    SELECT application_id, origin, entry_path, lead_source, program, term, term_order,
           is_current_cycle, status, is_submitted, is_admitted, is_denied, is_enrolled,
           days_inquiry_to_apply, days_apply_to_submit, days_submit_to_decision
    FROM {marts}.fct_applications
    ORDER BY term_order, application_id
""")
