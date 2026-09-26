"""Tests for the complete Pull Data orchestration workflow."""

import json

import pytest

import pull_data_workflow as workflow


def write_records(path, records):
    """Write test applicant records as JSON."""

    path.write_text(
        json.dumps(records),
        encoding="utf-8",
    )


def record(applicant_id):
    """Create a minimal applicant record with a stable result URL."""

    return {
        "url": (
            "https://www.thegradcafe.com/"
            f"result/{applicant_id}"
        ),
        "program": "Computer Science",
    }


class FakeCursor:
    """Fake cursor that returns a configured applicant count."""

    def __init__(self, count):
        self.count = count
        self.executed_sql = None

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False

    def execute(self, sql):
        self.executed_sql = sql

    def fetchone(self):
        return (self.count,)


class FakeConnection:
    """Fake PostgreSQL connection for database_count tests."""

    def __init__(self, count):
        self.fake_cursor = FakeCursor(count)

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False

    def cursor(self):
        return self.fake_cursor


@pytest.mark.integration
def test_read_records_returns_list(tmp_path):
    """A JSON list should be returned unchanged."""

    path = tmp_path / "records.json"

    records = [
        record(1),
        record(2),
    ]

    write_records(
        path,
        records,
    )

    assert (
        workflow.read_records(path)
        == records
    )


@pytest.mark.integration
def test_read_records_rejects_non_list(tmp_path):
    """The workflow requires a top-level JSON list."""

    path = tmp_path / "records.json"

    path.write_text(
        json.dumps(
            {
                "url":
                    "https://example.com/result/1"
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must contain a list",
    ):
        workflow.read_records(path)


@pytest.mark.integration
def test_verify_cleaned_prefix_rejects_too_many_cleaned():
    """The cleaned file cannot contain more rows than the raw file."""

    raw_records = [
        record(1),
    ]

    cleaned_records = [
        record(1),
        record(2),
    ]

    with pytest.raises(
        RuntimeError,
        match="contains more records",
    ):
        workflow.verify_cleaned_prefix(
            raw_records,
            cleaned_records,
        )


@pytest.mark.integration
def test_verify_cleaned_prefix_rejects_wrong_order():
    """Raw and cleaned records must remain in identical ID order."""

    raw_records = [
        record(1),
        record(2),
    ]

    cleaned_records = [
        record(2),
    ]

    with pytest.raises(
        RuntimeError,
        match="different record ordering",
    ):
        workflow.verify_cleaned_prefix(
            raw_records,
            cleaned_records,
        )


@pytest.mark.integration
def test_verify_cleaned_prefix_accepts_matching_records():
    """Matching raw and cleaned prefixes should be accepted."""

    raw_records = [
        record(1),
        record(2),
    ]

    cleaned_records = [
        record(1),
    ]

    result = workflow.verify_cleaned_prefix(
        raw_records,
        cleaned_records,
    )

    assert result is None


@pytest.mark.db
def test_database_count(monkeypatch):
    """database_count should query the applicants table."""

    fake_connection = FakeConnection(
        count=42
    )

    monkeypatch.setattr(
        workflow,
        "connect_to_database",
        lambda: fake_connection,
    )

    result = workflow.database_count()

    assert result == 42

    assert (
        fake_connection
        .fake_cursor
        .executed_sql
        == "SELECT COUNT(*) FROM applicants"
    )


@pytest.mark.integration
def test_run_pull_data_requires_both_files(
    tmp_path,
    monkeypatch,
):
    """The workflow should stop if either required JSON file is missing."""

    raw_file = tmp_path / "raw.json"
    cleaned_file = tmp_path / "cleaned.json"

    monkeypatch.setattr(
        workflow,
        "RAW_FILE",
        raw_file,
    )

    monkeypatch.setattr(
        workflow,
        "CLEANED_FILE",
        cleaned_file,
    )

    with pytest.raises(
        FileNotFoundError,
        match="raw or cleaned applicant JSON file is missing",
    ):
        workflow.run_pull_data()


@pytest.mark.integration
def test_run_pull_data_no_new_records(
    tmp_path,
    monkeypatch,
):
    """No-new-data runs should only synchronize universities."""

    raw_file = tmp_path / "raw.json"
    cleaned_file = tmp_path / "cleaned.json"

    existing = [
        record(100),
    ]

    write_records(
        raw_file,
        existing,
    )

    write_records(
        cleaned_file,
        existing,
    )

    monkeypatch.setattr(
        workflow,
        "RAW_FILE",
        raw_file,
    )

    monkeypatch.setattr(
        workflow,
        "CLEANED_FILE",
        cleaned_file,
    )

    capture_calls = []
    university_calls = []

    monkeypatch.setattr(
        workflow,
        "capture_pages",
        lambda web_mode=False:
            capture_calls.append(web_mode),
    )

    monkeypatch.setattr(
        workflow,
        "import_original_universities",
        lambda:
            university_calls.append(True),
    )

    def should_not_clean():
        raise AssertionError(
            "clean_data should not run "
            "when there is nothing new."
        )

    def should_not_import():
        raise AssertionError(
            "Applicant import should not run "
            "when there is nothing new."
        )

    monkeypatch.setattr(
        workflow,
        "clean_data",
        should_not_clean,
    )

    monkeypatch.setattr(
        workflow,
        "import_applicants",
        should_not_import,
    )

    result = workflow.run_pull_data()

    assert capture_calls == [True]

    assert university_calls == [True]

    assert (
        result
        == "Pull Data finished. No new applicant records were found. "
        "Original university records were synchronized. "
        "No new applicant records were imported."
    )


@pytest.mark.integration
def test_run_pull_data_detects_raw_file_shrinking(
    tmp_path,
    monkeypatch,
):
    """The raw file must never become smaller after capture."""

    raw_file = tmp_path / "raw.json"
    cleaned_file = tmp_path / "cleaned.json"

    original_raw = [
        record(1),
        record(2),
    ]

    cleaned = [
        record(1),
    ]

    write_records(
        raw_file,
        original_raw,
    )

    write_records(
        cleaned_file,
        cleaned,
    )

    monkeypatch.setattr(
        workflow,
        "RAW_FILE",
        raw_file,
    )

    monkeypatch.setattr(
        workflow,
        "CLEANED_FILE",
        cleaned_file,
    )

    def shrink_raw_file(web_mode=False):
        assert web_mode is True

        write_records(
            raw_file,
            [
                record(1),
            ],
        )

    monkeypatch.setattr(
        workflow,
        "capture_pages",
        shrink_raw_file,
    )

    with pytest.raises(
        RuntimeError,
        match="unexpectedly became smaller",
    ):
        workflow.run_pull_data()


@pytest.mark.integration
def test_run_pull_data_rejects_incomplete_cleaning(
    tmp_path,
    monkeypatch,
):
    """Database import should not start if cleaning leaves records unfinished."""

    raw_file = tmp_path / "raw.json"
    cleaned_file = tmp_path / "cleaned.json"

    existing = [
        record(10),
    ]

    write_records(
        raw_file,
        existing,
    )

    write_records(
        cleaned_file,
        existing,
    )

    monkeypatch.setattr(
        workflow,
        "RAW_FILE",
        raw_file,
    )

    monkeypatch.setattr(
        workflow,
        "CLEANED_FILE",
        cleaned_file,
    )

    def add_new_raw_record(web_mode=False):
        assert web_mode is True

        write_records(
            raw_file,
            [
                record(10),
                record(20),
            ],
        )

    monkeypatch.setattr(
        workflow,
        "capture_pages",
        add_new_raw_record,
    )

    # Deliberately leave cleaned_file unchanged.
    monkeypatch.setattr(
        workflow,
        "clean_data",
        lambda: None,
    )

    with pytest.raises(
        RuntimeError,
        match="Cleaning did not finish all records",
    ):
        workflow.run_pull_data()


@pytest.mark.integration
def test_run_pull_data_success(
    tmp_path,
    monkeypatch,
):
    """New records should be cleaned and imported successfully."""

    raw_file = tmp_path / "raw.json"
    cleaned_file = tmp_path / "cleaned.json"

    initial = [
        record(100),
    ]

    write_records(
        raw_file,
        initial,
    )

    write_records(
        cleaned_file,
        initial,
    )

    monkeypatch.setattr(
        workflow,
        "RAW_FILE",
        raw_file,
    )

    monkeypatch.setattr(
        workflow,
        "CLEANED_FILE",
        cleaned_file,
    )

    def capture_new_record(web_mode=False):
        assert web_mode is True

        write_records(
            raw_file,
            [
                record(100),
                record(200),
            ],
        )

    def clean_new_record():
        write_records(
            cleaned_file,
            [
                record(100),
                record(200),
            ],
        )

    calls = []

    monkeypatch.setattr(
        workflow,
        "capture_pages",
        capture_new_record,
    )

    monkeypatch.setattr(
        workflow,
        "clean_data",
        clean_new_record,
    )

    monkeypatch.setattr(
        workflow,
        "import_applicants",
        lambda:
            calls.append("applicants"),
    )

    monkeypatch.setattr(
        workflow,
        "import_original_universities",
        lambda:
            calls.append("universities"),
    )

    counts = iter(
        [
            50,
            51,
        ]
    )

    monkeypatch.setattr(
        workflow,
        "database_count",
        lambda: next(counts),
    )

    result = workflow.run_pull_data()

    assert calls == [
        "applicants",
        "universities",
    ]

    assert (
        result
        == "Pull Data finished. Found 1 new saved "
        "records and inserted 1 new database records. "
        "Click Update Analysis to view the latest results."
    )