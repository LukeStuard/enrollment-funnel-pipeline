# Records flagged by the known data quality checks (dq_issues mart).
from _warehouse import write_csv

write_csv("""
    SELECT check_name, record_id, source_system, origin, term, detail
    FROM {marts}.dq_issues
    ORDER BY check_name, source_system, record_id
""")
