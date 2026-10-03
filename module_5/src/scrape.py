"""GradCafe scraping and record-parsing utilities."""

import json
import re
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

BASE_URL = "https://www.thegradcafe.com"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
OUTPUT_FILE = "applicant_data.json"


def robots_allows(url):
    """Check whether robots.txt permits access to a URL."""

    parser = RobotFileParser()
    parser.set_url(ROBOTS_URL)
    parser.read()

    return parser.can_fetch("*", url)


def save_data(data, filename=OUTPUT_FILE):
    """Save applicant records to a JSON file."""

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def load_data(filename=OUTPUT_FILE):
    """Load previously saved applicant records."""

    path = Path(filename)

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _get_result_links(html):
    """Extract unique GradCafe result links from a survey page."""

    soup = BeautifulSoup(html, "html.parser")
    links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if href.startswith("/result/"):
            full_url = urljoin(BASE_URL, href)

            if full_url not in links:
                links.append(full_url)

    return links


def _normalize_missing(value):
    """
    Convert obvious missing-value labels to a consistent empty string.

    Original raw text is still preserved separately.
    """

    if value is None:
        return ""

    value = value.strip()

    missing_values = {
        "Not provided",
        "N/A",
        "None"
    }

    if value in missing_values:
        return ""

    return value


def _parse_survey_row(row):
    """Parse one applicant row from the GradCafe survey/results table."""

    result_link = row.find(
        "a",
        href=re.compile(r"^/result/\d+")
    )

    if result_link is None:
        return None

    url = urljoin(
        BASE_URL,
        result_link.get("href", "")
    )

    cells = row.find_all("td")

    if len(cells) < 4:
        return None

    school_text = cells[0].get_text(" ", strip=True)
    program_text = cells[1].get_text(" ", strip=True)
    date_added = cells[2].get_text(" ", strip=True)
    decision = cells[3].get_text(" ", strip=True)

    # Preserve the main row for traceability.
    raw_text = row.get_text(" ", strip=True)

    # GradCafe stores additional applicant information in the
    # immediately following table row.
    extra_row = row.find_next_sibling("tr")

    if extra_row is not None:
        extra_text = extra_row.get_text(" ", strip=True)
        raw_text = f"{raw_text} {extra_text}".strip()

    return {
        "program": program_text,
        "university": school_text,
        "comments": "",
        "date_added": date_added,
        "url": url,
        "status": decision,
        "decision_date": "",
        "acceptance_date": "",
        "rejection_date": "",
        "term": "",
        "student_type": "",
        "gre": "",
        "gre_v": "",
        "gre_aw": "",
        "gpa": "",
        "degree": "",
        "raw_text": raw_text
    }

# pylint: disable-next=too-many-branches
def _extract_extra_fields(record):
    text = record["raw_text"]

    # Separate the decision status from the displayed decision date.
    #
    # Examples:
    # "Accepted on Sep 11"
    # "Rejected on Apr 23"
    # "Wait listed on Sep 10"
    # "Interview on Jul 10"
    decision_match = re.match(
        r"^(Accepted|Rejected|Wait listed|Interview)"
        r"(?:\s+on\s+(.+))?$",
        record["status"],
        re.IGNORECASE
    )

    if decision_match:
        status = decision_match.group(1)
        decision_date = decision_match.group(2) or ""

        status_mapping = {
            "accepted": "Accepted",
            "rejected": "Rejected",
            "wait listed": "Wait listed",
            "interview": "Interview"
        }

        record["status"] = status_mapping.get(
            status.lower(),
            status
        )

        record["decision_date"] = decision_date.strip()

        # Keep the generic decision date, but also populate the
        # assignment-specific acceptance/rejection date fields.
        if record["status"] == "Accepted":
            record["acceptance_date"] = record["decision_date"]

        elif record["status"] == "Rejected":
            record["rejection_date"] = record["decision_date"]

    # Extract intended enrollment term.
    # Example: "Fall 2026"
    term_match = re.search(
        r"\b(Spring|Summer|Fall|Winter)\s+\d{4}\b",
        text,
        re.IGNORECASE
    )

    if term_match:
        record["term"] = term_match.group(0)

    # Extract applicant type.
    if re.search(
        r"\bInternational\b",
        text,
        re.IGNORECASE
    ):
        record["student_type"] = "International"

    elif re.search(
        r"\bAmerican\b",
        text,
        re.IGNORECASE
    ):
        record["student_type"] = "American"

    elif re.search(
        r"\bOther\b",
        text,
        re.IGNORECASE
    ):
        record["student_type"] = "Other"

    # Extract GPA.
    gpa_match = re.search(
        r"\bGPA\s+([0-9.]+)",
        text,
        re.IGNORECASE
    )

    if gpa_match:
        record["gpa"] = gpa_match.group(1)

    # Extract GRE General.
    gre_match = re.search(
        r"\bGRE\s+(\d+)",
        text
    )

    if gre_match:
        record["gre"] = gre_match.group(1)

    # Extract GRE Verbal.
    gre_v_match = re.search(
        r"\bGRE\s+V\s+(\d+)",
        text,
        re.IGNORECASE
    )

    if gre_v_match:
        record["gre_v"] = gre_v_match.group(1)

    # Extract GRE Analytical Writing.
    gre_aw_match = re.search(
        r"\bGRE\s+AW\s+([0-9.]+)",
        text,
        re.IGNORECASE
    )

    if gre_aw_match:
        record["gre_aw"] = gre_aw_match.group(1)

    # Determine degree category.
    if re.search(
        r"\bPhD\b",
        text,
        re.IGNORECASE
    ):
        record["degree"] = "PhD"

    elif re.search(
        r"\bMasters?\b",
        text,
        re.IGNORECASE
    ):
        record["degree"] = "Masters"

    # MFA is a master's-level degree.
    elif re.search(
        r"\bMFA\b",
        text,
        re.IGNORECASE
    ):
        record["degree"] = "Masters"

    return record


def parse_survey_page(html):
    """Parse all applicant records from one saved GradCafe survey page."""

    soup = BeautifulSoup(html, "html.parser")
    records = []

    for row in soup.find_all("tr"):
        record = _parse_survey_row(row)

        if record is None:
            continue

        record = _extract_extra_fields(record)
        records.append(record)

    return records


def _parse_entry(html, url):
    """
    Parse an individual GradCafe result page.

    We are keeping this function because it can be useful later
    for validating or enriching individual records.
    """

    soup = BeautifulSoup(html, "html.parser")
    fields = {}

    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")

        if dd is not None:
            field_name = dt.get_text(" ", strip=True)
            field_value = dd.get_text(" ", strip=True)
            fields[field_name] = field_value

    status = fields.get("Decision", "")
    notification = fields.get("Notification", "")

    record = {
        "program": fields.get("Program", ""),
        "university": fields.get("Institution", ""),
        "comments": fields.get("Notes", ""),
        "url": url,
        "status": status,
        "decision_date": notification,
        "acceptance_date": notification if status == "Accepted" else "",
        "rejection_date": notification if status == "Rejected" else "",
        "notification": notification,
        "degree": fields.get("Degree Type", ""),
        "student_type": fields.get(
            "Degree's Country of Origin",
            ""
        ),
        "gpa": _normalize_missing(
            fields.get("Undergrad GPA", "")
        ),
        "gre": _normalize_missing(
            fields.get("GRE General", "")
        ),
        "gre_v": _normalize_missing(
            fields.get("GRE Verbal", "")
        ),
        "gre_aw": _normalize_missing(
            fields.get("Analytical Writing", "")
        ),
        "raw_fields": fields
    }

    return record


def _page_sort_key(path):
    """Sort survey_page.html, survey_page_2.html, ... numerically."""

    if path.name == "survey_page.html":
        return 1

    match = re.fullmatch(r"survey_page_(\d+)\.html", path.name)

    if match:
        return int(match.group(1))

    return float("inf")


def scrape_data():
    """
    Parse all saved GradCafe survey pages and append new records
    to applicant_data.json.
    """

    survey_url = f"{BASE_URL}/survey/"

    if not robots_allows(survey_url):
        print(
            f"robots.txt does not permit scraping: "
            f"{survey_url}"
        )
        return

    print("robots.txt permits the survey URL.")

    html_files = sorted(
        Path(".").glob("survey_page*.html"),
        key=_page_sort_key
    )

    if not html_files:
        print("No survey_page*.html files were found.")
        return

    existing_data = load_data()

    existing_urls = {
        record.get("url")
        for record in existing_data
        if record.get("url")
    }

    total_new_records = 0

    for html_file in html_files:
        print(f"\nProcessing {html_file.name}...")

        html = html_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        page_records = parse_survey_page(html)

        print(
            f"Found {len(page_records)} applicant "
            f"records on this page."
        )

        page_new_records = 0

        for record in page_records:
            if record["url"] not in existing_urls:
                existing_data.append(record)
                existing_urls.add(record["url"])
                page_new_records += 1
                total_new_records += 1

        print(
            f"Added {page_new_records} new records "
            f"from {html_file.name}."
        )

        # Save after every page so progress is preserved.
        save_data(existing_data)

    print("\nFinished processing saved pages.")
    print(f"Added {total_new_records} new records.")
    print(f"Total saved records: {len(existing_data)}")


if __name__ == "__main__":
    scrape_data()
