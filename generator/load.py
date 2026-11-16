"""
Load the generator's CSVs into Salesforce with the Bulk API (Salesforce CLI).

The CLI holds the org credentials, so this script never sees a token.
Load order matters, and follows real life:
  1. Leads
  2. Lead stage events (must load before conversion: a converted Lead can't be
     the target of an external ID lookup)
  3. Contacts
  4. Applications (the org's trigger converts lead-first applicants' Leads)
  5. Application stage events

Safety:
  - preflight: refuses to start unless the whole load fits in the org's
    remaining data storage with 20% of the limit left over
  - every command names --target-org explicitly (the CLI's default org is
    a different org on this machine)
  - refuses to load if generator Leads already exist, unless --from is used
    to resume after a failure
  - stops at the first file with failed rows and downloads the failure CSVs
"""

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ACCOUNT_NAME = "Funnel Applicants"
BYTES_PER_RECORD = 2048   # Salesforce counts most records as 2 KB of data storage
HEADROOM = 0.20           # share of the storage limit to leave free
KEY_LIKE = "FUN-%"

STEPS = [
    ("leads", "leads.csv", "Lead"),
    ("lead-events", "stage_events_lead.csv", "Stage_Event__c"),
    ("contacts", "contacts.csv", "Contact"),
    ("applications", "applications.csv", "Application__c"),
    ("application-events", "stage_events_application.csv", "Stage_Event__c"),
]


def sf(org, *args, cwd=None):
    exe = shutil.which("sf")
    if not exe:
        sys.exit("Salesforce CLI (sf) not found on PATH.")
    proc = subprocess.run(
        [exe, *args, "--target-org", org, "--json"],
        capture_output=True, text=True, encoding="utf-8", cwd=cwd,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout)
        print(proc.stderr)
        sys.exit(f"Could not read CLI output for: sf {' '.join(args)}")


def soql_count(org, soql):
    out = sf(org, "data", "query", "--query", soql)
    if out.get("status") != 0:
        sys.exit(f"Query failed: {out.get('message')}")
    return out["result"]["totalSize"]


def count_rows(path):
    with path.open(encoding="utf-8", newline="") as f:
        return max(sum(1 for _ in f) - 1, 0)


def storage_preflight(org, paths):
    out = sf(org, "org", "list", "limits")
    if out.get("status") != 0:
        sys.exit(f"Could not read org limits: {out.get('message')}")
    limit = next((x for x in out["result"] if x.get("name") == "DataStorageMB"), None)
    if not limit:
        sys.exit("DataStorageMB not found in org limits; not loading blind.")
    records = sum(count_rows(p) for p in paths) + 1  # +1 for the Account
    needed = records * BYTES_PER_RECORD / 1024 / 1024
    remaining, maximum = limit["remaining"], limit["max"]
    left_after = remaining - needed
    print(f"Storage: {remaining} of {maximum} MB free; this load needs ~{needed:.1f} MB "
          f"({records} records); {left_after:.1f} MB would be left.")
    if left_after < maximum * HEADROOM:
        sys.exit(f"Not loading: keep at least {maximum * HEADROOM:.1f} MB free. "
                 f"Generate a smaller set (lower --applicants) and try again.")


def account_id(org):
    out = sf(org, "data", "query", "--query", f"SELECT Id FROM Account WHERE Name = '{ACCOUNT_NAME}' LIMIT 1")
    if out.get("status") != 0:
        sys.exit(f"Account lookup failed: {out.get('message')}")
    records = out["result"]["records"]
    if records:
        return records[0]["Id"]
    out = sf(org, "data", "create", "record", "--sobject", "Account", "--values", f"Name='{ACCOUNT_NAME}'")
    if out.get("status") != 0:
        sys.exit(f"Account create failed: {out.get('message')}")
    print(f"Created Account '{ACCOUNT_NAME}'")
    return out["result"]["id"]


def contacts_with_account(src, dst, acct_id):
    with src.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["AccountId"] = acct_id
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def find(d, *keys):
    """First matching key in the CLI's result (or error data) block."""
    for block in (d.get("result") or {}, d.get("data") or {}):
        for k in keys:
            if isinstance(block, dict) and block.get(k) is not None:
                return block[k]
    return None


def import_file(org, path, sobject, results_dir):
    print(f"\n{path.name} -> {sobject}")
    out = sf(org, "data", "import", "bulk", "--file", str(path), "--sobject", sobject,
             "--line-ending", "LF", "--wait", "30")
    job_id = find(out, "jobId", "id")
    processed = find(out, "processedRecords", "numberRecordsProcessed")
    failed = find(out, "failedRecords", "numberRecordsFailed")
    print(f"  job {job_id}  processed {processed}  failed {failed}  status {out.get('status')}")

    if out.get("status") == 0 and not failed:
        return True

    if out.get("message"):
        print(f"  message: {out['message']}")
    if job_id:
        results_dir.mkdir(parents=True, exist_ok=True)
        res = sf(org, "data", "bulk", "results", "--job-id", job_id, cwd=str(results_dir))
        print(f"  failure details saved in {results_dir}:")
        print("  " + json.dumps(res.get("result", res), indent=2).replace("\n", "\n  "))
    else:
        print(json.dumps(out, indent=2))
    return False


def main():
    parser = argparse.ArgumentParser(description="Load generator CSVs into Salesforce.")
    parser.add_argument("--target-org", default="gatewayDev")
    parser.add_argument("--data", type=Path, default=Path("data/salesforce"))
    parser.add_argument("--from", dest="start", choices=[s[0] for s in STEPS],
                        help="Resume from this step after a failure.")
    args = parser.parse_args()
    org = args.target_org

    missing = [f for _, f, _ in STEPS if not (args.data / f).exists()]
    if missing:
        sys.exit(f"Missing in {args.data}: {', '.join(missing)}. Run generate.py first.")

    existing = soql_count(org, f"SELECT COUNT() FROM Lead WHERE Synthetic_Key__c LIKE '{KEY_LIKE}'")
    if existing and not args.start:
        sys.exit(f"{existing} generator Leads already exist in {org}. Use --from to resume, or clear them first.")

    names = [s[0] for s in STEPS]
    first = names.index(args.start) if args.start else 0
    if not args.start:
        storage_preflight(org, [args.data / f for _, f, _ in STEPS])

    acct = account_id(org)
    staged = args.data / "contacts_with_account.csv"
    contacts_with_account(args.data / "contacts.csv", staged, acct)

    for name, filename, sobject in STEPS[first:]:
        path = staged if name == "contacts" else args.data / filename
        if not import_file(org, path, sobject, args.data / "results"):
            sys.exit(f"Stopped at '{name}'. Fix the cause, then rerun with --from {name}.")
        if name == "applications":
            converted = soql_count(org, f"SELECT COUNT() FROM Lead WHERE Synthetic_Key__c LIKE '{KEY_LIKE}' AND IsConverted = true")
            waiting = soql_count(org, f"SELECT COUNT() FROM Lead WHERE Synthetic_Key__c LIKE '{KEY_LIKE}' AND IsConverted = false AND Status = 'Application Started'")
            print(f"  Leads converted by the trigger: {converted}; Application Started but unconverted: {waiting}")

    print("\nLoad complete.")


if __name__ == "__main__":
    main()
