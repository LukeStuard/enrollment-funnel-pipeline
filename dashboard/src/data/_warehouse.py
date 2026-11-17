"""
Shared connection for the dashboard's data loaders.

Production: connects to MotherDuck as the funnel_dashboard service account
(DASHBOARD_MOTHERDUCK_TOKEN) and reads the marts through a read-only share.
That account owns no data, so it can't write anything.

Local testing: set FUNNEL_WAREHOUSE to a DuckDB file built by dbt (dev target)
to read its marts instead.

Files starting with an underscore are not routes, so Framework never serves this.
"""

import csv
import io
import os
import sys
from datetime import date, datetime

import duckdb

SHARE_URL = "md:_share/enrollment_funnel_share/68b01a3f-2b63-48e6-8039-14510269fd9f"
SHARE_ALIAS = "enrollment_funnel_share"


def connect():
    local = os.environ.get("FUNNEL_WAREHOUSE")
    if local:
        return duckdb.connect(local, read_only=True), "marts"
    token = os.environ.get("DASHBOARD_MOTHERDUCK_TOKEN")
    if not token:
        sys.exit("Set DASHBOARD_MOTHERDUCK_TOKEN (or FUNNEL_WAREHOUSE for a local file).")
    con = duckdb.connect("md:", config={"motherduck_token": token})
    con.execute(f"ATTACH IF NOT EXISTS '{SHARE_URL}' AS {SHARE_ALIAS}")
    return con, f"{SHARE_ALIAS}.marts"


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return value.isoformat()
    return value


def write_csv(sql):
    """Run a query and write the result to stdout as CSV, which Framework caches."""
    con, schema = connect()
    cur = con.execute(sql.format(marts=schema))
    columns = [d[0] for d in cur.description]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(columns)
    for row in cur.fetchall():
        writer.writerow([_cell(v) for v in row])
    sys.stdout.write(out.getvalue())
