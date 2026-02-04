"""
Seed script: pull all data from Airtable via MCP tool calls and insert into SQLite.

Usage (run from backend/):
    python -m app.seed

This script uses the Airtable REST API directly (since MCP is only available
inside Claude). It requires an AIRTABLE_PAT environment variable.

Alternatively, you can run the export_from_airtable_mcp() function inside
Claude to dump JSON files, then load them with import_from_json().
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, Base
from app.models import Product, Student, Enrollment

AIRTABLE_BASE_ID = "appwPkOLAwRZT7dp2"
PRODUCT_TABLE_ID = "tblRGXqGHYg1YGSyZ"
STUDENT_TABLE_ID = "tbl5qRwXQKI4lI7w1"
ENROLLMENT_TABLE_ID = "tblQXNh9348BIb2j2"

DATA_DIR = os.path.join(os.path.dirname(__file__), "seed_data")


def parse_bool_select(value: str | None) -> bool | None:
    """Convert Airtable single-select 'True'/'False' to Python bool."""
    if value is None:
        return None
    return value.strip().lower() == "true"


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Airtable returns ISO format like "2025-10-24T03:19:46.000Z"
        cleaned = value.replace("Z", "").replace("+00:00", "")
        # Handle milliseconds
        if "." in cleaned:
            return datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
        if "T" in cleaned:
            return datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        # CSV format: "2026-01-24 20:58:10"
        return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def import_from_json(db: Session):
    """Load from JSON files previously exported (seed_data/ directory)."""
    products_path = os.path.join(DATA_DIR, "products.json")
    students_path = os.path.join(DATA_DIR, "students.json")
    enrollments_path = os.path.join(DATA_DIR, "enrollments.json")

    for path in [products_path, students_path, enrollments_path]:
        if not os.path.exists(path):
            print(f"Missing {path}. Run export first.")
            sys.exit(1)

    # --- Products ---
    with open(products_path) as f:
        product_records = json.load(f)

    airtable_product_id_map: dict[str, int] = {}  # airtable record ID → local ID
    for rec in product_records:
        fields = rec["fields"]
        product = Product(
            product_id=fields.get("Product ID", ""),
            product_name=fields.get("Product Name", ""),
            kit_tag=fields.get("Kit tag"),
        )
        db.add(product)
        db.flush()
        airtable_product_id_map[rec["id"]] = product.id

    print(f"Imported {len(product_records)} products")

    # --- Students ---
    with open(students_path) as f:
        student_records = json.load(f)

    airtable_student_id_map: dict[str, int] = {}  # airtable record ID → local ID
    for rec in student_records:
        fields = rec["fields"]
        student = Student(
            student_number=fields.get("Student #", 0),
            first_name=fields.get("First name", ""),
            last_name=fields.get("Last Name", ""),
            preferred_name=fields.get("Preferred name") or None,
            email=fields.get("Email", ""),
            alternative_email=fields.get("Alternative Email") or None,
            country=fields.get("Country") or None,
            timezone=fields.get("Timezone") or None,
            closest_city=fields.get("Closest City") or None,
            dob=parse_date(fields.get("DOB")),
            gender=fields.get("Gender") or None,
            learn_about_course=fields.get("Learn about the course") or None,
            consent_images=parse_bool_select(fields.get("Consent to use images")),
            consent_photo_on_site=parse_bool_select(fields.get("Consent to use photo on site")),
            what_made_you_join=fields.get("What made you want to join?") or None,
            get_from=fields.get("Get from") or None,
            here_for=fields.get("Here for") or None,
            claude_confidence_level=fields.get("Claude Confidence level"),
            onboarding_date=parse_datetime(fields.get("Onboarding Date")),
        )
        db.add(student)
        db.flush()
        airtable_student_id_map[rec["id"]] = student.id

    print(f"Imported {len(student_records)} students")

    # --- Enrollments ---
    with open(enrollments_path) as f:
        enrollment_records = json.load(f)

    skipped = 0
    imported = 0
    for rec in enrollment_records:
        fields = rec["fields"]

        # Resolve FK references
        student_links = fields.get("Student Record", [])
        product_links = fields.get("Program (from Product Record)", [])

        if not student_links or not product_links:
            skipped += 1
            continue

        student_airtable_id = student_links[0]
        product_airtable_id = product_links[0]

        local_student_id = airtable_student_id_map.get(student_airtable_id)
        local_product_id = airtable_product_id_map.get(product_airtable_id)

        if local_student_id is None or local_product_id is None:
            skipped += 1
            continue

        enrollment = Enrollment(
            enrollment_id=fields.get("Enrollment ID", ""),
            status=fields.get("Status") or None,
            student_id=local_student_id,
            product_id=local_product_id,
        )
        db.add(enrollment)
        imported += 1

    print(f"Imported {imported} enrollments (skipped {skipped})")

    db.commit()
    print("Seed complete!")


def fetch_all_via_api():
    """Fetch all records from Airtable REST API and save as JSON."""
    try:
        import requests
    except ImportError:
        print("Install requests: pip install requests")
        sys.exit(1)

    pat = os.environ.get("AIRTABLE_PAT")
    if not pat:
        print("Set AIRTABLE_PAT environment variable with your Airtable personal access token")
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)

    headers = {"Authorization": f"Bearer {pat}"}
    base_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"

    for table_id, filename in [
        (PRODUCT_TABLE_ID, "products.json"),
        (STUDENT_TABLE_ID, "students.json"),
        (ENROLLMENT_TABLE_ID, "enrollments.json"),
    ]:
        all_records = []
        offset = None
        while True:
            params = {}
            if offset:
                params["offset"] = offset
            resp = requests.get(f"{base_url}/{table_id}", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            all_records.extend(data["records"])
            offset = data.get("offset")
            if not offset:
                break
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "w") as f:
            json.dump(all_records, f, indent=2)
        print(f"Exported {len(all_records)} records to {filepath}")


def import_survey_csv(db: Session):
    """Import survey responses from CSV, updating enrollment rows directly via email match."""
    csv_path = os.path.join(DATA_DIR, "survey_responses.csv")
    if not os.path.exists(csv_path):
        print(f"Missing {csv_path}. Skipping survey import.")
        return

    # Build email → enrollment lookup for "Claude Code for Beginners" (product_id=1)
    # Check both primary email and alternative_email
    email_to_enrollment: dict[str, Enrollment] = {}
    enrollments = (
        db.query(Enrollment)
        .join(Student, Enrollment.student_id == Student.id)
        .filter(Enrollment.product_id == 1)
        .all()
    )
    for enr in enrollments:
        student = enr.student
        if student.email:
            email_to_enrollment[student.email.strip().lower()] = enr
        if student.alternative_email:
            email_to_enrollment[student.alternative_email.strip().lower()] = enr

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)  # skip header row

        updated = 0
        unmatched = 0
        for row in reader:
            if len(row) < 20:
                continue  # skip malformed rows

            response_hash = row[0].strip()
            if not response_hash:
                continue

            email = row[1].strip().lower()
            enrollment = email_to_enrollment.get(email)

            if not enrollment:
                unmatched += 1
                continue

            # Parse integer fields safely
            def safe_int(val):
                try:
                    return int(val.strip()) if val and val.strip() else None
                except (ValueError, AttributeError):
                    return None

            enrollment.response_hash = response_hash
            enrollment.biggest_win = row[2].strip() or None
            enrollment.three_things_learned = row[3].strip() or None
            enrollment.confidence_after = safe_int(row[4])
            enrollment.satisfaction = row[5].strip() or None
            enrollment.recommend_score = safe_int(row[6])
            enrollment.testimonial = row[7].strip() or None
            enrollment.improvement_suggestion = row[8].strip() or None
            enrollment.interest_longer_program = row[9].strip() or None
            enrollment.followup_topics = row[10].strip() or None
            enrollment.beginner_friendly_rating = row[11].strip() or None
            enrollment.expected_learning_not_covered = row[12].strip() or None
            enrollment.anything_else = row[13].strip() or None
            enrollment.survey_response_type = row[14].strip() or None
            enrollment.survey_start_date = parse_datetime(row[15].strip() or None)
            enrollment.survey_stage_date = parse_datetime(row[16].strip() or None)
            enrollment.survey_submit_date = parse_datetime(row[17].strip() or None)
            enrollment.survey_network_id = row[18].strip() or None
            enrollment.survey_tags = row[19].strip() or None
            # Column 20 is "Ending" — static thank-you text, discarded
            updated += 1

    db.commit()
    print(f"Updated {updated} enrollments with survey data (skipped {unmatched} unmatched emails)")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        fetch_all_via_api()
        return

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Product).count() > 0:
            print("Database already has data. Drop student.db and re-run to reseed.")
            return
        import_from_json(db)

        # Import survey data into enrollments if not already present
        has_survey = db.query(Enrollment).filter(Enrollment.response_hash.isnot(None)).count() > 0
        if not has_survey:
            import_survey_csv(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
