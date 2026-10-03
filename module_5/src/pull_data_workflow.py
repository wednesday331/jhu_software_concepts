"""Capture, clean, and import GradCafe applicant records."""

import json
from pathlib import Path

from capture_page import capture_pages
from clean import clean_data
from load_data import (
    connect_to_database,
    get_applicant_id,
    main as import_applicants,
)
from load_original_universities import main as import_original_universities

MODULE_DIR = Path(__file__).resolve().parent
RAW_FILE = MODULE_DIR / "applicant_data.json"
CLEANED_FILE = MODULE_DIR / "llm_extend_applicant_data.json"


def read_records(path):
    """Read applicant records from a JSON file."""
    with path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError(
            f"{path.name} must contain a list of applicant records."
        )

    return records


def verify_cleaned_prefix(raw_records, cleaned_records):
    """Check that the cleaned records match the raw record order."""

    if len(cleaned_records) > len(raw_records):
        raise RuntimeError(
            "The cleaned file contains more records than the raw file."
        )

    for index, cleaned_record in enumerate(cleaned_records):
        raw_record = raw_records[index]

        raw_id = get_applicant_id(raw_record, index + 1)
        cleaned_id = get_applicant_id(cleaned_record, index + 1)

        if raw_id != cleaned_id:
            raise RuntimeError(
                "The raw and cleaned JSON files have different "
                f"record ordering at position {index + 1}. "
                "No cleaning or database import was attempted."
            )


def database_count():
    """Count applicant records currently stored in PostgreSQL."""

    with connect_to_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM applicants
                LIMIT 1;
                """
            )
            return cursor.fetchone()[0]


def run_pull_data():
    """Capture new records, clean them, and import them into PostgreSQL."""

    if not RAW_FILE.exists() or not CLEANED_FILE.exists():
        raise FileNotFoundError(
            "The raw or cleaned applicant JSON file is missing."
        )

    raw_before = read_records(RAW_FILE)
    cleaned_before = read_records(CLEANED_FILE)

    # The cleaning script resumes by record position, so verify
    # the existing files before capturing additional records.
    verify_cleaned_prefix(raw_before, cleaned_before)

    # Uses MAX_PAGES = 2 from capture_page.py during testing.
    # Web mode must not wait for terminal input.
    capture_pages(web_mode=True)

    raw_after = read_records(RAW_FILE)
    newly_saved = len(raw_after) - len(raw_before)

    if newly_saved < 0:
        raise RuntimeError(
            "The raw applicant file unexpectedly became smaller."
        )

    verify_cleaned_prefix(raw_after, cleaned_before)

    if newly_saved == 0 and len(cleaned_before) == len(raw_after):
        # Keep the supplementary table synchronized even when
        # the scraper finds no new applicant records.
        import_original_universities()

        return (
            "Pull Data finished. No new applicant records were found. "
            "Original university records were synchronized. "
            "No new applicant records were imported."
        )

    # Clean newly captured records using the existing workflow.
    clean_data()

    cleaned_after = read_records(CLEANED_FILE)
    verify_cleaned_prefix(raw_after, cleaned_after)

    if len(cleaned_after) != len(raw_after):
        raise RuntimeError(
            "Cleaning did not finish all records. "
            "The database import was not started."
        )

    before_count = database_count()

    # Import cleaned applicant records into the main table.
    # Existing applicant IDs are skipped.
    import_applicants()

    # Import original university names into the supplementary table.
    # Existing rows are updated using the original university value.
    import_original_universities()

    after_count = database_count()
    inserted = after_count - before_count

    return (
        f"Pull Data finished. Found {newly_saved:,} new saved "
        f"records and inserted {inserted:,} new database records. "
        "Click Update Analysis to view the latest results."
    )
