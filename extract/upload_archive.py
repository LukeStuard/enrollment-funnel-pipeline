"""
One-time upload of the legacy CRM export (generator/data/archive CSVs) to R2 as Parquet.

Writes archive/<table>/data.parquet, overwriting any earlier upload, so it's safe
to rerun after regenerating. Columns stay as text, as a legacy export would
deliver them; dbt applies types.
"""

import argparse
from pathlib import Path

from r2 import connect, url

TABLES = ["leads", "contacts", "applications", "stage_events"]


def main():
    parser = argparse.ArgumentParser(description="Upload the legacy archive CSVs to R2 as Parquet.")
    parser.add_argument("--data", type=Path, default=Path("data/archive"))
    args = parser.parse_args()

    con = connect()
    for table in TABLES:
        src = args.data / f"{table}.csv"
        if not src.exists():
            raise SystemExit(f"Missing {src}. Run generator/generate.py first.")
        target = url("archive", table, "data.parquet")
        con.execute(f"""
            COPY (SELECT * FROM read_csv('{src.as_posix()}', header = true, all_varchar = true))
            TO '{target}' (FORMAT parquet)
        """)
        rows = con.execute(f"SELECT count(*) FROM read_parquet('{target}')").fetchone()[0]
        print(f"{table:14} {rows:6} rows -> {target}")


if __name__ == "__main__":
    main()
