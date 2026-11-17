"""
Incremental extract from Salesforce to Parquet in R2.

For each object:
  1. Watermark = max(SystemModstamp) already landed in R2, minus a lookback
     window (records committed late with an earlier SystemModstamp are not
     missed). No landed data means a full extract.
  2. Bulk API 2.0 queryAll job (includes deleted rows, via IsDeleted) with
     SystemModstamp > watermark.
  3. Result pages are written to one Parquet file under
     salesforce/<object>/extracted_at=<UTC timestamp>/ with two metadata
     columns: _extracted_at and _sobject.

Rows can repeat across runs because of the lookback; dbt staging keeps the
latest version of each Id. Raw columns are stored as text exactly as the API
returned them; types are applied in dbt.

Auth: OAuth client credentials as the read-only extract user
(SF_INSTANCE_URL, SF_CLIENT_ID, SF_CLIENT_SECRET).
"""

import argparse
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from r2 import connect, require, url

API = "v68.0"
LOOKBACK = timedelta(minutes=10)
POLL_SECONDS = 3
JOB_TIMEOUT_SECONDS = 20 * 60
PAGE_SIZE = 50000

# Only fields the Funnel_Extract permission set can read, plus system fields.
OBJECTS = {
    "Lead": [
        "Id", "IsDeleted", "FirstName", "LastName", "Email", "Phone", "LeadSource", "Status",
        "Program_of_Interest__c", "Term_of_Interest__c", "Synthetic_Key__c",
        "IsConverted", "ConvertedDate", "ConvertedContactId", "CreatedDate", "SystemModstamp",
    ],
    "Contact": [
        "Id", "IsDeleted", "FirstName", "LastName", "Email", "Phone", "Synthetic_Key__c",
        "CreatedDate", "SystemModstamp",
    ],
    "Application__c": [
        "Id", "IsDeleted", "Name", "Applicant__c", "Program__c", "Term__c", "Status__c",
        "Submitted_Date__c", "Synthetic_Key__c", "CreatedDate", "SystemModstamp",
    ],
    "Stage_Event__c": [
        "Id", "IsDeleted", "Name", "Lead__c", "Contact__c", "Application__c", "From_Stage__c",
        "To_Stage__c", "Event_Date__c", "Source__c", "Synthetic_Key__c", "CreatedDate", "SystemModstamp",
    ],
}


def folder(sobject):
    return sobject.lower().replace("__c", "")


# ---------------------------------------------------------------- Salesforce


def token():
    resp = requests.post(
        f"{require('SF_INSTANCE_URL')}/services/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": require("SF_CLIENT_ID"),
            "client_secret": require("SF_CLIENT_SECRET"),
        },
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"Token request failed: HTTP {resp.status_code} {resp.text[:300]}")
    body = resp.json()
    return body["instance_url"], {"Authorization": f"Bearer {body['access_token']}"}


def run_query(instance, headers, soql):
    base = f"{instance}/services/data/{API}/jobs/query"
    resp = requests.post(base, headers=headers, timeout=30, json={
        "operation": "queryAll",
        "query": soql,
        "contentType": "CSV",
        "lineEnding": "LF",
        "columnDelimiter": "COMMA",
    })
    if resp.status_code not in (200, 201):
        sys.exit(f"Query job failed to start: HTTP {resp.status_code} {resp.text[:500]}")
    job_id = resp.json()["id"]

    deadline = time.monotonic() + JOB_TIMEOUT_SECONDS
    while True:
        state = requests.get(f"{base}/{job_id}", headers=headers, timeout=30).json()
        if state["state"] == "JobComplete":
            break
        if state["state"] in ("Failed", "Aborted"):
            sys.exit(f"Query job {job_id} {state['state']}: {state.get('errorMessage')}")
        if time.monotonic() > deadline:
            sys.exit(f"Query job {job_id} still {state['state']} after {JOB_TIMEOUT_SECONDS}s")
        time.sleep(POLL_SECONDS)

    pages, locator = [], None
    while True:
        params = {"maxRecords": PAGE_SIZE}
        if locator:
            params["locator"] = locator
        page = requests.get(f"{base}/{job_id}/results", headers={**headers, "Accept": "text/csv"},
                            params=params, timeout=120)
        if page.status_code != 200:
            sys.exit(f"Results for job {job_id} failed: HTTP {page.status_code} {page.text[:300]}")
        count = int(page.headers.get("Sforce-NumberOfRecords", "0"))
        if count:
            pages.append(page.content)
        locator = page.headers.get("Sforce-Locator")
        if not locator or locator == "null":
            return job_id, pages


# ---------------------------------------------------------------- R2


def watermark(con, sobject):
    try:
        row = con.execute(
            f"SELECT max(SystemModstamp) FROM read_parquet('{url('salesforce', folder(sobject), '*', '*.parquet')}')"
        ).fetchone()
    except Exception as e:  # nothing landed yet
        if "No files found" in str(e):
            return None
        raise
    if not row or not row[0]:
        return None
    landed = datetime.strptime(row[0], "%Y-%m-%dT%H:%M:%S.%f%z")
    return landed - LOOKBACK


def soql_for(sobject, since):
    soql = f"SELECT {', '.join(OBJECTS[sobject])} FROM {sobject}"
    if since:
        soql += f" WHERE SystemModstamp > {since.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    return soql


def land(con, sobject, pages, extracted_at):
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for i, content in enumerate(pages):
            p = Path(tmp) / f"page{i:04d}.csv"
            p.write_bytes(content)
            files.append(p.as_posix())
        stamp = extracted_at.strftime("%Y%m%dT%H%M%SZ")
        target = url("salesforce", folder(sobject), f"extracted_at={stamp}", "data.parquet")
        file_list = "[" + ", ".join(f"'{f}'" for f in files) + "]"
        con.execute(f"""
            COPY (
                SELECT *,
                       '{extracted_at.strftime('%Y-%m-%dT%H:%M:%SZ')}' AS _extracted_at,
                       '{sobject}' AS _sobject
                FROM read_csv({file_list}, header = true, all_varchar = true)
            ) TO '{target}' (FORMAT parquet)
        """)
        rows = con.execute(f"SELECT count(*) FROM read_parquet('{target}')").fetchone()[0]
        return target, rows


# ---------------------------------------------------------------- main


def main():
    parser = argparse.ArgumentParser(description="Incremental Salesforce extract to R2.")
    parser.add_argument("--objects", nargs="*", choices=list(OBJECTS), default=list(OBJECTS))
    parser.add_argument("--full", action="store_true", help="Ignore the watermark and extract everything.")
    args = parser.parse_args()

    con = connect()
    instance, headers = token()
    extracted_at = datetime.now(timezone.utc)
    print(f"Extract run {extracted_at.strftime('%Y-%m-%dT%H:%M:%SZ')}")

    for sobject in args.objects:
        since = None if args.full else watermark(con, sobject)
        soql = soql_for(sobject, since)
        print(f"\n{sobject}: " + (f"changes since {since.strftime('%Y-%m-%dT%H:%M:%SZ')}" if since else "full extract"))
        job_id, pages = run_query(instance, headers, soql)
        if not pages:
            print(f"  job {job_id}: no rows")
            continue
        target, rows = land(con, sobject, pages, extracted_at)
        print(f"  job {job_id}: {rows} rows -> {target}")

    print("\nExtract complete.")


if __name__ == "__main__":
    main()
