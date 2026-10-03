
"""
Load original downloaded university names into a supplementary table.

The required 15-column applicants table remains unchanged.
"""

import json
import re
from pathlib import Path

from load_data import clean_url, connect_to_database


DATA_FILE = Path(__file__).resolve().parent / "llm_extend_applicant_data.json"


def get_applicant_id(record):
    """Extract the Grad Cafe result ID from its URL."""
    url = clean_url(record.get("url"))

    if not url:
        raise ValueError("Applicant record is missing its URL")

    match = re.search(r"/result/(\d+)(?:[/?#]|$)", url)

    if not match:
        raise ValueError(f"Cannot extract applicant ID from {url!r}")

    return int(match.group(1))


def main():
    """Load original university values into the PostgreSQL database."""
    with DATA_FILE.open("r", encoding="utf-8") as file:
        records = json.load(file)

    rows = [
        (
            get_applicant_id(record),
            str(record.get("university") or "").strip() or None,
        )
        for record in records
    ]

    sql = """
        INSERT INTO applicant_original_universities (p_id, university)
        VALUES (%s, %s)
        ON CONFLICT (p_id)
        DO UPDATE SET university = EXCLUDED.university;
    """

    with connect_to_database() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(sql, rows)

            cursor.execute(
                "SELECT COUNT(*) FROM applicant_original_universities;"
            )
            count = cursor.fetchone()[0]

    print(f"Original university records loaded: {count:,}")


if __name__ == "__main__":
    main()
