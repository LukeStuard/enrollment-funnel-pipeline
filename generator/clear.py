"""
Delete every generator record (Synthetic_Key__c starting with FUN-) from the org,
so the generator can be reloaded from scratch. Records created any other way
(gateway and intake demo data, live test records) are never touched.

Deletes children before parents: stage events, Applications, Leads, Contacts.
Requires --yes, and names --target-org explicitly.
"""

import argparse
import csv
import sys
from pathlib import Path

from load import KEY_LIKE, sf

ORDER = ["Stage_Event__c", "Application__c", "Lead", "Contact"]


def main():
    parser = argparse.ArgumentParser(description="Delete generator records from the org.")
    parser.add_argument("--target-org", default="gatewayDev")
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--yes", action="store_true", help="Actually delete.")
    args = parser.parse_args()
    org = args.target_org

    work = args.data / "clear"
    work.mkdir(parents=True, exist_ok=True)
    for sobject in ORDER:
        out = sf(org, "data", "query", "--query", f"SELECT Id FROM {sobject} WHERE Synthetic_Key__c LIKE '{KEY_LIKE}'")
        if out.get("status") != 0:
            sys.exit(f"Query failed for {sobject}: {out.get('message')}")
        ids = [r["Id"] for r in out["result"]["records"]]
        total = out["result"]["totalSize"]
        if len(ids) != total:
            sys.exit(f"{sobject}: query returned {len(ids)} of {total} rows; not deleting a partial set.")
        print(f"{sobject}: {len(ids)} generator records")
        if not ids or not args.yes:
            continue
        path = work / f"{sobject}.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["Id"])
            w.writerows([i] for i in ids)
        res = sf(org, "data", "delete", "bulk", "--sobject", sobject, "--file", str(path),
                 "--line-ending", "LF", "--wait", "30")
        if res.get("status") != 0:
            sys.exit(f"Delete failed for {sobject}: {res.get('message')}")
        print(f"  deleted")

    if not args.yes:
        print("\nDry run. Rerun with --yes to delete these records.")


if __name__ == "__main__":
    main()
