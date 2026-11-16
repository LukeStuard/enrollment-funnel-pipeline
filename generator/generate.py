"""
Synthetic enrollment funnel generator.

Writes CSVs for the Salesforce Bulk API (see load.py). Offline and deterministic:
the same --seed and --as-of always produce the same files.

Two entry paths, mirroring a real admissions pattern:
  lead-first  Inquiry Lead -> portal signup (Contact) -> Application.
              The org's Application trigger converts the Lead on load.
  direct      Signup and Application with no Lead ("stealth" applicants).

Nothing is dated after --as-of, so recent cohorts are left in flight.

Output is split by time, the way most institutions' data is:
  data/salesforce/  the current cycle (terms starting after --as-of), loaded
                    into the org by load.py. Small enough for Developer
                    Edition's 5 MB data storage.
  data/archive/     earlier terms, written as a legacy CRM export with its
                    own column names and LEG- keys. Lands in R2 directly.

Deliberate defects (for the dbt tests to find):
  - a share of lead-first applicants sign up with a different email, so their
    Lead never converts and they look like a separate direct applicant
  - a few Leads with no program of interest
  - a few Lead emails in upper case
  - a few submitted Applications missing Submitted_Date__c
"""

import argparse
import csv
import random
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from faker import Faker

# ---------------------------------------------------------------- settings

KEY_PREFIX = "FUN"

LEAD_FIRST_SHARE = 0.40          # share of applicants who start as a Lead
INQUIRY_TO_APPLICANT = 0.25      # share of Leads (for passed terms) who apply
EMAIL_MISMATCH_RATE = 0.05       # lead-first applicants who sign up with another email
MISSING_PROGRAM_RATE = 0.03      # Leads with no program of interest
UPPERCASE_EMAIL_RATE = 0.03      # Leads whose email was typed in capitals
MISSING_SUBMIT_DATE_RATE = 0.02  # submitted Applications missing Submitted_Date__c

# program: (share of applicants, admit rate, yield of admits)
PROGRAMS = {
    "MBA": (0.40, 0.70, 0.55),
    "MS Management": (0.25, 0.75, 0.60),
    "MS Data Analytics": (0.25, 0.60, 0.65),
    "Certificate in Leadership": (0.10, 0.90, 0.50),
}

# term: (share of applicants, term start date)
TERMS = {
    "Fall 2025": (0.22, date(2025, 8, 25)),
    "Spring 2026": (0.12, date(2026, 1, 12)),
    "Summer 2026": (0.07, date(2026, 5, 11)),
    "Fall 2026": (0.25, date(2026, 8, 24)),
    "Spring 2027": (0.14, date(2027, 1, 11)),
    "Summer 2027": (0.08, date(2027, 5, 10)),
    "Fall 2027": (0.12, date(2027, 8, 23)),
}

LEAD_SOURCES = {
    "Web": 40, "LinkedIn": 20, "Event": 15, "Email Campaign": 10,
    "Agent": 8, "Partner Referral": 5, "Phone Inquiry": 2,
}

SUBMIT_RATE = 0.85        # Drafts that get submitted
REVIEW_RATE = 0.97        # submitted that reach review
WITHDRAW_SHARE = 0.60     # admits who don't enroll and formally withdraw (rest stay Admitted)
CONTACTED_RATE_APPLICANT = 0.70
CONTACTED_RATE_NONAPPLICANT = 0.65
CLOSE_RATE_NONAPPLICANT = 0.70

LOCALES = ["en_US", "es_MX", "en_IN"]

# ---------------------------------------------------------------- helpers


def pick(rng, weights):
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def at(rng, d):
    """A business-hours UTC timestamp on date d."""
    return datetime.combine(d, time(rng.randint(15, 23), rng.randint(0, 59)), tzinfo=timezone.utc)


def ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def ascii_slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return "".join(ch for ch in s.lower() if ch.isalnum())


@dataclass
class Person:
    first: str
    last: str
    email: str
    phone: str


@dataclass
class Generated:
    leads: list = field(default_factory=list)
    contacts: list = field(default_factory=list)
    applications: list = field(default_factory=list)
    lead_events: list = field(default_factory=list)
    app_events: list = field(default_factory=list)


class Keys:
    def __init__(self):
        self.n = {}

    def next(self, kind):
        self.n[kind] = self.n.get(kind, 0) + 1
        return f"{KEY_PREFIX}-{kind}-{self.n[kind]:06d}"


# ---------------------------------------------------------------- generator


class Generator:
    def __init__(self, seed, as_of):
        self.rng = random.Random(seed)
        Faker.seed(seed)
        self.fake = Faker(LOCALES)
        self.as_of = as_of
        # Salesforce rejects a CreatedDate in the future, so never go past now.
        self.as_of_dt = min(datetime.combine(as_of, time(23, 59), tzinfo=timezone.utc),
                            datetime.now(timezone.utc) - timedelta(minutes=5))
        self.keys = Keys()
        self.out = Generated()
        self.emails = set()

    # people

    def person(self):
        first, last = self.fake.first_name(), self.fake.last_name()
        email = self.email_for(first, last)
        phone = f"555-{self.rng.randint(100, 999)}-{self.rng.randint(1000, 9999)}"
        return Person(first, last, email, phone)

    def email_for(self, first, last):
        base = f"{ascii_slug(first)}.{ascii_slug(last)}"
        while True:
            email = f"{base}{self.rng.randint(1, 999)}@example.com"
            if email not in self.emails:
                self.emails.add(email)
                return email

    # events

    def lead_event(self, lead_key, from_stage, to_stage, when, term):
        self.out.lead_events.append({
            "_term": term,
            "Synthetic_Key__c": self.keys.next("SEL"),
            "Lead__r.Synthetic_Key__c": lead_key,
            "From_Stage__c": from_stage or "",
            "To_Stage__c": to_stage,
            "Event_Date__c": ts(when),
            "Source__c": "Generator",
            "CreatedDate": ts(when),
        })

    def app_event(self, app_key, contact_key, from_stage, to_stage, when, term):
        self.out.app_events.append({
            "_term": term,
            "Synthetic_Key__c": self.keys.next("SEA"),
            "Application__r.Synthetic_Key__c": app_key,
            "Contact__r.Synthetic_Key__c": contact_key,
            "From_Stage__c": from_stage or "",
            "To_Stage__c": to_stage,
            "Event_Date__c": ts(when),
            "Source__c": "Generator",
            "CreatedDate": ts(when),
        })

    # leads

    def add_lead(self, p, program, term, created, path):
        """path: list of (stage, datetime) after the Inquiry, already cut at as_of."""
        key = self.keys.next("L")
        email = p.email.upper() if self.rng.random() < UPPERCASE_EMAIL_RATE else p.email
        program_value = "" if self.rng.random() < MISSING_PROGRAM_RATE else program
        status_by_stage = {
            "Inquiry": "Open - Not Contacted",
            "Contacted": "Working - Contacted",
            "Application Started": "Application Started",
            "Not Converted": "Closed - Not Converted",
        }
        stages = [("Inquiry", created)] + path
        self.out.leads.append({
            "_term": term,
            "_converted_contact": "",
            "Synthetic_Key__c": key,
            "FirstName": p.first,
            "LastName": p.last,
            "Company": "Prospective Student",
            "Email": email,
            "Phone": p.phone,
            "LeadSource": pick(self.rng, LEAD_SOURCES),
            "Program_of_Interest__c": program_value,
            "Term_of_Interest__c": term,
            "Status": status_by_stage[stages[-1][0]],
            "CreatedDate": ts(created),
        })
        prev = None
        for stage, when in stages:
            self.lead_event(key, prev, stage, when, term)
            prev = stage
        return key

    def nonapplicant_lead(self):
        term = pick(self.rng, {t: v[0] for t, v in TERMS.items()})
        start = TERMS[term][1]
        created = at(self.rng, start - timedelta(days=self.rng.randint(30, 240)))
        if created > self.as_of_dt:
            return
        path = []
        last = created
        if self.rng.random() < CONTACTED_RATE_NONAPPLICANT:
            last = last + timedelta(days=self.rng.randint(1, 14), hours=self.rng.randint(1, 6))
            if last <= self.as_of_dt:
                path.append(("Contacted", last))
        if self.rng.random() < CLOSE_RATE_NONAPPLICANT:
            closed = last + timedelta(days=self.rng.randint(45, 120))
            if closed <= self.as_of_dt:
                path.append(("Not Converted", closed))
        program = pick(self.rng, {k: v[0] for k, v in PROGRAMS.items()})
        self.add_lead(self.person(), program, term, created, path)

    # applicants

    def applicant(self, lead_first):
        program = pick(self.rng, {k: v[0] for k, v in PROGRAMS.items()})
        term = pick(self.rng, {t: v[0] for t, v in TERMS.items()})
        _, admit_rate, yield_rate = PROGRAMS[program]
        start = TERMS[term][1]

        app_created = at(self.rng, start - timedelta(days=self.rng.randint(20, 180)))
        if app_created > self.as_of_dt:
            return False  # this applicant hasn't applied yet
        signup = app_created - timedelta(hours=self.rng.randint(1, 72))
        p = self.person()

        contact_email = p.email
        if lead_first:
            lead_created = signup - timedelta(days=self.rng.randint(14, 120))
            path = []
            if self.rng.random() < CONTACTED_RATE_APPLICANT:
                contacted = lead_created + timedelta(days=self.rng.randint(1, 10), hours=self.rng.randint(1, 6))
                if contacted < signup:
                    path.append(("Contacted", contacted))
            path.append(("Application Started", signup))
            self.add_lead(p, program, term, lead_created, path)
            lead_row = self.out.leads[-1]
            if self.rng.random() < EMAIL_MISMATCH_RATE:
                contact_email = self.email_for(p.first, p.last)
                lead_row = None  # the Lead never converts

        contact_key = self.keys.next("C")
        if lead_first and lead_row is not None:
            lead_row["_converted_contact"] = contact_key
        self.out.contacts.append({
            "_term": term,
            "Synthetic_Key__c": contact_key,
            "FirstName": p.first,
            "LastName": p.last,
            "Email": contact_email,
            "Phone": p.phone,
            "CreatedDate": ts(signup),
        })

        # application timeline, cut at as_of
        stages = [("Applicant", app_created)]
        submitted = None
        t = app_created
        if self.rng.random() < SUBMIT_RATE:
            t = t + timedelta(days=self.rng.randint(1, 21), hours=self.rng.randint(1, 8))
            submitted = t
            stages.append(("Submitted", t))
            if self.rng.random() < REVIEW_RATE:
                t = t + timedelta(days=self.rng.randint(2, 10), hours=self.rng.randint(1, 8))
                stages.append(("In Review", t))
                t = t + timedelta(days=self.rng.randint(7, 35), hours=self.rng.randint(1, 8))
                if self.rng.random() < admit_rate:
                    stages.append(("Admitted", t))
                    if self.rng.random() < yield_rate:
                        enrolled = max(t + timedelta(days=1), at(self.rng, start - timedelta(days=self.rng.randint(0, 10))))
                        stages.append(("Enrolled", enrolled))
                    elif self.rng.random() < WITHDRAW_SHARE:
                        stages.append(("Withdrawn", t + timedelta(days=self.rng.randint(10, 60))))
                else:
                    stages.append(("Denied", t))
        stages = [(s, w) for s, w in stages if w <= self.as_of_dt]

        status = "Draft" if stages[-1][0] == "Applicant" else stages[-1][0]
        reached_submit = any(s == "Submitted" for s, _ in stages)
        submit_date = ""
        if reached_submit and self.rng.random() >= MISSING_SUBMIT_DATE_RATE:
            submit_date = submitted.date().isoformat()

        app_key = self.keys.next("A")
        self.out.applications.append({
            "_term": term,
            "Synthetic_Key__c": app_key,
            "Applicant__r.Synthetic_Key__c": contact_key,
            "Program__c": program,
            "Term__c": term,
            "Status__c": status,
            "Submitted_Date__c": submit_date,
            "CreatedDate": ts(app_created),
        })
        prev = None
        for stage, when in stages:
            self.app_event(app_key, contact_key, prev, stage, when, term)
            prev = stage
        return True

    def run(self, applicants):
        made = lead_first_made = 0
        for _ in range(applicants):
            lead_first = self.rng.random() < LEAD_FIRST_SHARE
            if self.applicant(lead_first):
                made += 1
                lead_first_made += lead_first
        # Inquiries that never apply: sized so lead-first applicants are about
        # INQUIRY_TO_APPLICANT of all Leads.
        nonapplicants = round(lead_first_made * (1 / INQUIRY_TO_APPLICANT - 1))
        for _ in range(nonapplicants):
            self.nonapplicant_lead()
        return made, lead_first_made


# ---------------------------------------------------------------- output

ARCHIVE_PREFIX = "LEG"
BYTES_PER_RECORD = 2048  # Salesforce counts most records as 2 KB of data storage


def public(row):
    return {k: v for k, v in row.items() if not k.startswith("_")}


def legacy(key):
    return key.replace(f"{KEY_PREFIX}-", f"{ARCHIVE_PREFIX}-", 1) if key else ""


def to_archive(out):
    """Rename to the legacy CRM's own export schema."""
    leads = [{
        "legacy_lead_id": legacy(r["Synthetic_Key__c"]),
        "first_name": r["FirstName"], "last_name": r["LastName"],
        "email": r["Email"], "phone": r["Phone"],
        "lead_source": r["LeadSource"],
        "program_interest": r["Program_of_Interest__c"],
        "term_interest": r["Term_of_Interest__c"],
        "status": "Closed - Converted" if r["_converted_contact"] else r["Status"],
        "converted_contact_id": legacy(r["_converted_contact"]),
        "created_at": r["CreatedDate"],
    } for r in out.leads]
    contacts = [{
        "legacy_contact_id": legacy(r["Synthetic_Key__c"]),
        "first_name": r["FirstName"], "last_name": r["LastName"],
        "email": r["Email"], "phone": r["Phone"],
        "created_at": r["CreatedDate"],
    } for r in out.contacts]
    applications = [{
        "legacy_application_id": legacy(r["Synthetic_Key__c"]),
        "legacy_contact_id": legacy(r["Applicant__r.Synthetic_Key__c"]),
        "program": r["Program__c"], "term": r["Term__c"], "status": r["Status__c"],
        "submitted_date": r["Submitted_Date__c"],
        "created_at": r["CreatedDate"],
    } for r in out.applications]
    events = [{
        "legacy_event_id": legacy(r["Synthetic_Key__c"]),
        "legacy_lead_id": legacy(r["Lead__r.Synthetic_Key__c"]),
        "legacy_application_id": "", "legacy_contact_id": "",
        "from_stage": r["From_Stage__c"], "to_stage": r["To_Stage__c"],
        "event_at": r["Event_Date__c"],
    } for r in out.lead_events] + [{
        "legacy_event_id": legacy(r["Synthetic_Key__c"]),
        "legacy_lead_id": "",
        "legacy_application_id": legacy(r["Application__r.Synthetic_Key__c"]),
        "legacy_contact_id": legacy(r["Contact__r.Synthetic_Key__c"]),
        "from_stage": r["From_Stage__c"], "to_stage": r["To_Stage__c"],
        "event_at": r["Event_Date__c"],
    } for r in out.app_events]
    return {"leads.csv": leads, "contacts.csv": contacts,
            "applications.csv": applications, "stage_events.csv": events}


def write_csv(path, rows):
    if not rows:
        path.unlink(missing_ok=True)
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic enrollment funnel CSVs.")
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today(),
                        help="Nothing is dated after this day (YYYY-MM-DD). Default: today.")
    parser.add_argument("--applicants", type=int, default=1150,
                        help="Applicants to plan before dropping those who haven't applied by --as-of.")
    parser.add_argument("--limit", type=int, help="Smoke test: plan only this many applicants.")
    parser.add_argument("--out", type=Path, default=Path("data"))
    args = parser.parse_args()

    planned = args.limit or args.applicants
    gen = Generator(args.seed, args.as_of)
    made, lead_first = gen.run(planned)

    current = {t for t, (_, start) in TERMS.items() if start > args.as_of}

    def split(rows):
        return ([r for r in rows if r["_term"] in current],
                [r for r in rows if r["_term"] not in current])

    sf_out, arch_out = Generated(), Generated()
    for name in ("leads", "contacts", "applications", "lead_events", "app_events"):
        cur, old = split(getattr(gen.out, name))
        setattr(sf_out, name, cur)
        setattr(arch_out, name, old)

    sf_dir, arch_dir = args.out / "salesforce", args.out / "archive"
    sf_dir.mkdir(parents=True, exist_ok=True)
    arch_dir.mkdir(parents=True, exist_ok=True)
    sf_files = {
        "leads.csv": sf_out.leads,
        "contacts.csv": sf_out.contacts,
        "applications.csv": sf_out.applications,
        "stage_events_lead.csv": sf_out.lead_events,
        "stage_events_application.csv": sf_out.app_events,
    }
    for name, rows in sf_files.items():
        write_csv(sf_dir / name, [public(r) for r in rows])
    arch_files = to_archive(arch_out)
    for name, rows in arch_files.items():
        write_csv(arch_dir / name, rows)

    sf_records = sum(len(r) for r in sf_files.values())
    print(f"as of {args.as_of}, seed {args.seed}")
    print(f"applicants: {made} of {planned} planned ({lead_first} lead-first, {made - lead_first} direct)")
    print(f"current cycle (Salesforce): {', '.join(sorted(current, key=lambda t: TERMS[t][1])) or 'none'}")
    for name, rows in sf_files.items():
        print(f"  salesforce/{name:30} {len(rows):6}")
    print(f"  ~{sf_records * BYTES_PER_RECORD / 1024 / 1024:.1f} MB of Salesforce data storage ({sf_records} records)")
    for name, rows in arch_files.items():
        print(f"  archive/{name:33} {len(rows):6}")


if __name__ == "__main__":
    main()
