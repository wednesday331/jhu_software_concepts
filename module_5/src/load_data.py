
"""
Module 3: Load cleaned Grad Cafe applicant data into PostgreSQL.

Run from the module_3 folder:
    python load_data.py

PostgreSQL connection settings come from environment variables.
No database password is stored in this file.
"""
# pylint: disable=duplicate-code


import json
import os
import re
from datetime import datetime
from pathlib import Path

import psycopg


DATA_FILE = Path(__file__).resolve().parent / "llm_extend_applicant_data.json"

# These are the 15 columns required by the assignment.
EXPECTED_COLUMNS = [
    "p_id",
    "program",
    "comments",
    "url",
    "status",
    "date_added",
    "term",
    "us_or_international",
    "gpa",
    "gre",
    "gre_v",
    "gre_aw",
    "degree",
    "llm_generated_program",
    "llm_generated_university",
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS applicants (
    p_id INTEGER PRIMARY KEY,
    program TEXT,
    comments TEXT,
    url TEXT,
    status TEXT,
    date_added DATE,
    term TEXT,
    us_or_international TEXT,
    gpa DOUBLE PRECISION,
    gre DOUBLE PRECISION,
    gre_v DOUBLE PRECISION,
    gre_aw DOUBLE PRECISION,
    degree TEXT,
    llm_generated_program TEXT,
    llm_generated_university TEXT
);
"""

INSERT_SQL = """
INSERT INTO applicants (
    p_id,
    program,
    comments,
    url,
    status,
    date_added,
    term,
    us_or_international,
    gpa,
    gre,
    gre_v,
    gre_aw,
    degree,
    llm_generated_program,
    llm_generated_university
)
VALUES (
    %(p_id)s,
    %(program)s,
    %(comments)s,
    %(url)s,
    %(status)s,
    %(date_added)s,
    %(term)s,
    %(us_or_international)s,
    %(gpa)s,
    %(gre)s,
    %(gre_v)s,
    %(gre_aw)s,
    %(degree)s,
    %(llm_generated_program)s,
    %(llm_generated_university)s
)
ON CONFLICT (p_id) DO NOTHING;
"""


def connect_to_database():
    """Connect using the environment variables set in PowerShell."""
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )


def optional_text(value):
    """Convert blank or missing text to a database NULL."""
    if value is None:
        return None

    text = str(value).strip()
    return text if text else None


def optional_number(value):
    """Convert a score to a float, or return NULL if it is missing."""
    if value is None or str(value).strip() == "":
        return None

    number = float(str(value).strip().replace(",", ""))

    # PostgreSQL supports NaN, but it should not represent a missing score.
    if not -float("inf") < number < float("inf"):
        return None

    return number


def optional_date(value):
    """Convert dates such as 'Sep 12, 2026' to Python date objects."""
    if value is None or str(value).strip() == "":
        return None

    text = str(value).strip()

    for date_format in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue

    raise ValueError(f"Unrecognized date format: {text!r}")


def clean_url(value):
    """Extract the URL from either plain text or a Markdown link."""
    text = optional_text(value)

    if text is None:
        return None

    # Example: [https://example.com/result/123](https://example.com/result/123)
    markdown_match = re.fullmatch(r"\[[^\]]+\]\((https?://[^)]+)\)", text)

    if markdown_match:
        return markdown_match.group(1)

    return text


def get_applicant_id(record, position):
    """
    Use the numeric Grad Cafe result ID from the applicant's URL.

    This gives each applicant a stable p_id rather than assigning an ID
    based on their position in the JSON file.
    """
    url = clean_url(record.get("url"))

    if not url:
        raise ValueError(f"Record {position}: missing applicant URL")

    match = re.search(r"/result/(\d+)(?:[/?#]|$)", url)

    if not match:
        raise ValueError(
            f"Record {position}: cannot extract applicant ID from {url!r}"
        )

    applicant_id = int(match.group(1))

    # PostgreSQL INTEGER is a signed 32-bit type.
    if applicant_id > 2_147_483_647:
        raise ValueError(f"Record {position}: applicant ID is too large")

    return applicant_id


def prepare_record(record, position):
    """Map one JSON record to the required PostgreSQL columns."""
    if not isinstance(record, dict):
        raise ValueError(f"Record {position}: expected a JSON object")

    return {
        "p_id": get_applicant_id(record, position),
        "program": optional_text(record.get("program")),
        "comments": optional_text(record.get("comments")),
        "url": clean_url(record.get("url")),
        "status": optional_text(record.get("status")),
        "date_added": optional_date(record.get("date_added")),
        "term": optional_text(record.get("term")),
        "us_or_international": optional_text(record.get("student_type")),
        "gpa": optional_number(record.get("gpa")),
        "gre": optional_number(record.get("gre")),
        "gre_v": optional_number(record.get("gre_v")),
        "gre_aw": optional_number(record.get("gre_aw")),
        "degree": optional_text(record.get("degree")),
        "llm_generated_program": optional_text(
            record.get("llm-generated-program")
        ),
        "llm_generated_university": optional_text(
            record.get("llm-generated-university")
        ),
    }


def verify_table_columns(cursor):
    """Stop if an existing applicants table has a different schema."""
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'applicants'
        ORDER BY ordinal_position;
        """
    )

    actual_columns = [row[0] for row in cursor.fetchall()]

    if actual_columns != EXPECTED_COLUMNS:
        raise RuntimeError(
            "The existing applicants table does not match the required "
            f"15-column schema.\nFound: {actual_columns}\n"
            f"Expected: {EXPECTED_COLUMNS}\n"
            "No data was imported. Inspect the existing table before "
            "making changes."
        )


def main():
    """Load cleaned applicant records into the PostgreSQL database."""
    print(f"Reading: {DATA_FILE.name}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Expected the JSON file to contain a list of records")

    print(f"JSON records found: {len(records):,}")

    # Prepare and validate every record before changing the database.
    prepared_records = [
        prepare_record(record, position)
        for position, record in enumerate(records, start=1)
    ]

    # Check whether the JSON contains repeated Grad Cafe result IDs.
    unique_ids = {record["p_id"] for record in prepared_records}
    duplicate_count = len(prepared_records) - len(unique_ids)

    print(f"Unique applicant IDs in JSON: {len(unique_ids):,}")
    print(f"Repeated applicant IDs in JSON: {duplicate_count:,}")

    # Keep the first occurrence of each applicant ID.
    unique_records = {}
    for record in prepared_records:
        unique_records.setdefault(record["p_id"], record)

    with connect_to_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database();")
            print(f"Connected to database: {cursor.fetchone()[0]}")

            cursor.execute(CREATE_TABLE_SQL)
            verify_table_columns(cursor)

            cursor.execute("SELECT COUNT(*) FROM applicants;")
            before_count = cursor.fetchone()[0]

            print(f"Rows in applicants before import: {before_count:,}")
            print("Importing applicant records...")

            cursor.executemany(
                INSERT_SQL,
                list(unique_records.values()),
            )

            cursor.execute("SELECT COUNT(*) FROM applicants;")
            after_count = cursor.fetchone()[0]

            print(f"New rows inserted: {after_count - before_count:,}")
            print(f"Total rows in applicants: {after_count:,}")

        # The connection context commits only if the import succeeds.

    print("Import completed successfully!")


if __name__ == "__main__":
    main()
