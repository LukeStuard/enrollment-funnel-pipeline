"""
Builds a local fake data lake for CI checks: no Salesforce, no R2, no secrets.

Runs the seeded generator, then writes its output in the same layout and shape
the real pipeline lands in R2:
  salesforce/<object>/extracted_at=<UTC>/data.parquet  what the Bulk API extract
      returns: text columns, Ids (here the synthetic keys), IsDeleted, Name,
      SystemModstamp, _extracted_at and _sobject. Lead conversion is applied the
      way the org's Application trigger does it: a Lead in Application Started
      whose email matches (ignoring case) an applicant Contact's email.
  archive/<table>/data.parquet  the legacy export, as extract/upload_archive.py
      writes it.

Usage (from the repo root):
  python ci/build_test_lake.py --out ci-lake
then point dbt at it with --vars '{raw_root: <absolute path to ci-lake>}'.
"""

import argparse
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parent.parent
AS_OF = "2026-11-16"  # fixed, so every CI run checks the same data
SEED = "20261116"
ARCHIVE_TABLES = ["leads", "contacts", "applications", "stage_events"]

# Bulk API shape for each object, built from the generator's Salesforce CSVs.
# {now} is the extract timestamp; generator keys stand in for Salesforce Ids.
SALESFORCE = {
    "lead": ("Lead", """
        SELECT l.Synthetic_Key__c AS Id, 'false' AS IsDeleted,
               l.FirstName, l.LastName, l.Email, l.Phone, l.LeadSource,
               CASE WHEN c.contact_id IS NOT NULL THEN 'Closed - Converted' ELSE l.Status END AS Status,
               l.Program_of_Interest__c, l.Term_of_Interest__c, l.Synthetic_Key__c,
               CASE WHEN c.contact_id IS NOT NULL THEN 'true' ELSE 'false' END AS IsConverted,
               CASE WHEN c.contact_id IS NOT NULL THEN substr(c.applied_at, 1, 10) END AS ConvertedDate,
               c.contact_id AS ConvertedContactId,
               l.CreatedDate, '{now}' AS SystemModstamp
        FROM read_csv('{src}/leads.csv', all_varchar = true) l
        LEFT JOIN (
            SELECT lower(ct.Email) AS email, ct.Synthetic_Key__c AS contact_id,
                   min(a.CreatedDate) AS applied_at
            FROM read_csv('{src}/contacts.csv', all_varchar = true) ct
            JOIN read_csv('{src}/applications.csv', all_varchar = true) a
              ON a."Applicant__r.Synthetic_Key__c" = ct.Synthetic_Key__c
            GROUP BY ALL
        ) c ON l.Status = 'Application Started' AND lower(l.Email) = c.email
    """),
    "contact": ("Contact", """
        SELECT Synthetic_Key__c AS Id, 'false' AS IsDeleted, FirstName, LastName, Email, Phone,
               Synthetic_Key__c, CreatedDate, '{now}' AS SystemModstamp
        FROM read_csv('{src}/contacts.csv', all_varchar = true)
    """),
    "application": ("Application__c", """
        SELECT Synthetic_Key__c AS Id, 'false' AS IsDeleted, Synthetic_Key__c AS "Name",
               "Applicant__r.Synthetic_Key__c" AS Applicant__c, Program__c, Term__c, Status__c,
               Submitted_Date__c, Synthetic_Key__c, CreatedDate, '{now}' AS SystemModstamp
        FROM read_csv('{src}/applications.csv', all_varchar = true)
    """),
    "stage_event": ("Stage_Event__c", """
        SELECT Synthetic_Key__c AS Id, 'false' AS IsDeleted, Synthetic_Key__c AS "Name",
               "Lead__r.Synthetic_Key__c" AS Lead__c, NULL AS Contact__c, NULL AS Application__c,
               From_Stage__c, To_Stage__c, Event_Date__c, Source__c, Synthetic_Key__c,
               CreatedDate, '{now}' AS SystemModstamp
        FROM read_csv('{src}/stage_events_lead.csv', all_varchar = true)
        UNION ALL BY NAME
        SELECT Synthetic_Key__c AS Id, 'false' AS IsDeleted, Synthetic_Key__c AS "Name",
               NULL AS Lead__c, "Contact__r.Synthetic_Key__c" AS Contact__c,
               "Application__r.Synthetic_Key__c" AS Application__c,
               From_Stage__c, To_Stage__c, Event_Date__c, Source__c, Synthetic_Key__c,
               CreatedDate, '{now}' AS SystemModstamp
        FROM read_csv('{src}/stage_events_application.csv', all_varchar = true)
    """),
}


def main():
    parser = argparse.ArgumentParser(description="Build a local fake data lake for CI.")
    parser.add_argument("--out", type=Path, default=Path("ci-lake"))
    args = parser.parse_args()
    out = args.out.resolve()

    now = datetime.now(timezone.utc)
    now_api = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [sys.executable, str(REPO / "generator" / "generate.py"),
             "--seed", SEED, "--as-of", AS_OF, "--out", tmp],
            check=True, cwd=REPO / "generator",
        )
        src_sf = Path(tmp, "salesforce").as_posix()
        src_arch = Path(tmp, "archive").as_posix()
        con = duckdb.connect()

        for folder, (sobject, sql) in SALESFORCE.items():
            target = out / "salesforce" / folder / f"extracted_at={stamp}" / "data.parquet"
            target.parent.mkdir(parents=True, exist_ok=True)
            con.execute(f"""
                COPY (
                    SELECT *, '{now.strftime('%Y-%m-%dT%H:%M:%SZ')}' AS _extracted_at, '{sobject}' AS _sobject
                    FROM ({sql.format(src=src_sf, now=now_api)})
                ) TO '{target.as_posix()}' (FORMAT parquet)
            """)
            rows = con.execute(f"SELECT count(*) FROM read_parquet('{target.as_posix()}')").fetchone()[0]
            print(f"salesforce/{folder:12} {rows:6} rows")

        for table in ARCHIVE_TABLES:
            target = out / "archive" / table / "data.parquet"
            target.parent.mkdir(parents=True, exist_ok=True)
            con.execute(f"""
                COPY (SELECT * FROM read_csv('{src_arch}/{table}.csv', header = true, all_varchar = true))
                TO '{target.as_posix()}' (FORMAT parquet)
            """)
            rows = con.execute(f"SELECT count(*) FROM read_parquet('{target.as_posix()}')").fetchone()[0]
            print(f"archive/{table:14} {rows:6} rows")

    print(f"Fake lake ready at {out}")


if __name__ == "__main__":
    main()
