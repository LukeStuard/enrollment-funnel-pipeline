"""
DuckDB connection with an R2 secret, shared by the extract and the archive upload.

Credentials come from environment variables, never from the code:
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and optionally R2_BUCKET.
Locally, scripts/Use-FunnelEnv.ps1 sets them from Windows Credential Manager;
in GitHub Actions they come from repository secrets.

DuckDB's R2 secret only applies to r2:// URLs.
"""

import os
import sys

import duckdb

BUCKET = os.environ.get("R2_BUCKET", "enrollment-funnel-raw")


def require(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing environment variable {name}. Locally, dot-source scripts/Use-FunnelEnv.ps1 first.")
    return value


def sql_str(value):
    return "'" + value.replace("'", "''") + "'"


def connect():
    con = duckdb.connect()
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    con.execute(f"""
        CREATE SECRET r2_funnel (
            TYPE r2,
            KEY_ID {sql_str(require("R2_ACCESS_KEY_ID"))},
            SECRET {sql_str(require("R2_SECRET_ACCESS_KEY"))},
            ACCOUNT_ID {sql_str(require("R2_ACCOUNT_ID"))}
        )
    """)
    return con


def url(*parts):
    return f"r2://{BUCKET}/" + "/".join(parts)
