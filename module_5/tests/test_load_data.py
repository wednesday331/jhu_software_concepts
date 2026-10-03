"""Tests for loading cleaned GradCafe data into PostgreSQL."""

import io
import json
import runpy
from datetime import date
from pathlib import Path

import pytest

import load_data


class FakeCursor:
    """Minimal PostgreSQL cursor used by the loader tests."""

    def __init__(self):
        self.last_sql = ""
        self.count_reads = 0
        self.inserted_records = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql):
        self.last_sql = sql

    def executemany(self, sql, records):
        self.last_sql = sql
        self.inserted_records = list(records)

    def fetchone(self):
        if "current_database" in self.last_sql:
            return ("test_gradcafe",)

        if "COUNT(*)" in self.last_sql:
            self.count_reads += 1

            if self.count_reads == 1:
                return (10,)

            return (12,)

        raise AssertionError(
            f"Unexpected fetchone for SQL: {self.last_sql}"
        )

    def fetchall(self):
        return [
            (column,)
            for column in load_data.EXPECTED_COLUMNS
        ]


class FakeConnection:
    """Minimal PostgreSQL connection used by loader tests."""

    def __init__(self):
        self.fake_cursor = FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return self.fake_cursor


@pytest.mark.db
def test_connect_to_database_uses_environment(monkeypatch):
    """PostgreSQL environment settings should be passed to psycopg."""

    monkeypatch.setenv("PGHOST", "localhost")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGDATABASE", "gradcafe")
    monkeypatch.setenv("PGUSER", "test_user")
    monkeypatch.setenv("PGPASSWORD", "test_password")

    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return "connection"

    monkeypatch.setattr(
        load_data.psycopg,
        "connect",
        fake_connect,
    )

    result = load_data.connect_to_database()

    assert result == "connection"

    assert captured == {
        "host": "localhost",
        "port": "5432",
        "dbname": "gradcafe",
        "user": "test_user",
        "password": "test_password",
    }


@pytest.mark.db
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        (" Computer Science ", "Computer Science"),
        (123, "123"),
    ],
)
def test_optional_text(value, expected):
    """Optional text should convert blank values to None."""

    assert load_data.optional_text(value) == expected


@pytest.mark.db
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("3.90", 3.9),
        ("1,234.5", 1234.5),
        (168, 168.0),
        ("NaN", None),
        ("inf", None),
        ("-inf", None),
    ],
)
def test_optional_number(value, expected):
    """Optional numeric values should be converted safely."""

    assert load_data.optional_number(value) == expected


@pytest.mark.db
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("Sep 12, 2026", date(2026, 9, 12)),
        ("September 12, 2026", date(2026, 9, 12)),
        ("2026-09-12", date(2026, 9, 12)),
    ],
)
def test_optional_date(value, expected):
    """Supported date formats should become Python date objects."""

    assert load_data.optional_date(value) == expected


@pytest.mark.db
def test_optional_date_rejects_unknown_format():
    """An unsupported date format should raise ValueError."""

    with pytest.raises(
        ValueError,
        match="Unrecognized date format",
    ):
        load_data.optional_date("09/12/2026")


@pytest.mark.db
def test_clean_url_handles_missing_plain_and_markdown():
    """URLs may be missing, plain text, or Markdown links."""

    assert load_data.clean_url(None) is None

    assert (
        load_data.clean_url(
            " https://example.com/result/123 "
        )
        == "https://example.com/result/123"
    )

    assert (
        load_data.clean_url(
            "[GradCafe]"
            "(https://example.com/result/456)"
        )
        == "https://example.com/result/456"
    )


@pytest.mark.db
def test_get_applicant_id_extracts_result_number():
    """The GradCafe result number should become p_id."""

    record = {
        "url": "https://example.com/result/12345"
    }

    assert (
        load_data.get_applicant_id(record, 1)
        == 12345
    )


@pytest.mark.db
def test_get_applicant_id_supports_url_suffix():
    """Result IDs should work before query and path suffixes."""

    record = {
        "url":
            "https://example.com/result/9876/?test=yes"
    }

    assert (
        load_data.get_applicant_id(record, 2)
        == 9876
    )


@pytest.mark.db
def test_get_applicant_id_rejects_missing_url():
    """A record without a URL cannot receive a stable ID."""

    with pytest.raises(
        ValueError,
        match="missing applicant URL",
    ):
        load_data.get_applicant_id(
            {"url": ""},
            3,
        )


@pytest.mark.db
def test_get_applicant_id_rejects_invalid_url():
    """A URL without /result/<number> should fail clearly."""

    with pytest.raises(
        ValueError,
        match="cannot extract applicant ID",
    ):
        load_data.get_applicant_id(
            {
                "url":
                    "https://example.com/survey/"
            },
            4,
        )


@pytest.mark.db
def test_get_applicant_id_rejects_integer_overflow():
    """IDs larger than PostgreSQL INTEGER should be rejected."""

    with pytest.raises(
        ValueError,
        match="applicant ID is too large",
    ):
        load_data.get_applicant_id(
            {
                "url":
                    "https://example.com/result/2147483648"
            },
            5,
        )


@pytest.mark.db
def test_prepare_record_rejects_non_dictionary():
    """Each source record must be a JSON object."""

    with pytest.raises(
        ValueError,
        match="expected a JSON object",
    ):
        load_data.prepare_record(
            "not a dictionary",
            1,
        )


@pytest.mark.db
def test_prepare_record_maps_all_columns():
    """A cleaned JSON record should map to all required DB columns."""

    source = {
        "program": " Computer Science ",
        "comments": " Test comment ",
        "url":
            "[Result]"
            "(https://example.com/result/123)",
        "status": " Accepted ",
        "date_added": "Sep 12, 2026",
        "term": " Fall 2026 ",
        "student_type": " International ",
        "gpa": "3.90",
        "gre": "168",
        "gre_v": "162",
        "gre_aw": "4.5",
        "degree": " PhD ",
        "llm-generated-program":
            " Computer Science ",
        "llm-generated-university":
            " Johns Hopkins University ",
    }

    result = load_data.prepare_record(
        source,
        1,
    )

    assert result == {
        "p_id": 123,
        "program": "Computer Science",
        "comments": "Test comment",
        "url":
            "https://example.com/result/123",
        "status": "Accepted",
        "date_added": date(2026, 9, 12),
        "term": "Fall 2026",
        "us_or_international":
            "International",
        "gpa": 3.9,
        "gre": 168.0,
        "gre_v": 162.0,
        "gre_aw": 4.5,
        "degree": "PhD",
        "llm_generated_program":
            "Computer Science",
        "llm_generated_university":
            "Johns Hopkins University",
    }


@pytest.mark.db
def test_verify_table_columns_accepts_expected_schema():
    """The exact required 15-column schema should be accepted."""

    cursor = FakeCursor()

    load_data.verify_table_columns(cursor)

    assert "information_schema.columns" in cursor.last_sql


@pytest.mark.db
def test_verify_table_columns_rejects_wrong_schema():
    """An unexpected applicants schema should stop the import."""

    class WrongSchemaCursor(FakeCursor):
        def fetchall(self):
            return [
                ("p_id",),
                ("wrong_column",),
            ]

    cursor = WrongSchemaCursor()

    with pytest.raises(
        RuntimeError,
        match="does not match the required",
    ):
        load_data.verify_table_columns(cursor)


@pytest.mark.db
def test_main_rejects_non_list_json(
    tmp_path,
    monkeypatch,
):
    """The loader should reject a top-level JSON object."""

    data_file = tmp_path / "input.json"

    data_file.write_text(
        json.dumps(
            {
                "program":
                    "Computer Science"
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        load_data,
        "DATA_FILE",
        data_file,
    )

    with pytest.raises(
        ValueError,
        match="Expected the JSON file to contain a list",
    ):
        load_data.main()


@pytest.mark.db
def test_main_imports_unique_records(
    tmp_path,
    monkeypatch,
    capsys,
):
    """main should validate, deduplicate, and insert applicant records."""

    data_file = tmp_path / "input.json"

    records = [
        {
            "program": "Computer Science",
            "url":
                "https://example.com/result/100",
            "status": "Accepted",
        },
        {
            # Same ID: this duplicate should not be inserted twice.
            "program": "Duplicate CS",
            "url":
                "https://example.com/result/100",
            "status": "Accepted",
        },
        {
            "program": "Mathematics",
            "url":
                "https://example.com/result/200",
            "status": "Rejected",
        },
    ]

    data_file.write_text(
        json.dumps(records),
        encoding="utf-8",
    )

    fake_connection = FakeConnection()

    monkeypatch.setattr(
        load_data,
        "DATA_FILE",
        data_file,
    )

    monkeypatch.setattr(
        load_data,
        "connect_to_database",
        lambda: fake_connection,
    )

    load_data.main()

    inserted = (
        fake_connection
        .fake_cursor
        .inserted_records
    )

    assert len(inserted) == 2

    assert {
        record["p_id"]
        for record in inserted
    } == {100, 200}

    # setdefault keeps the first duplicate.
    first_record = next(
        record
        for record in inserted
        if record["p_id"] == 100
    )

    assert (
        first_record["program"]
        == "Computer Science"
    )

    output = capsys.readouterr().out

    assert "JSON records found: 3" in output
    assert "Unique applicant IDs in JSON: 2" in output
    assert "Repeated applicant IDs in JSON: 1" in output
    assert "Connected to database: test_gradcafe" in output
    assert "New rows inserted: 2" in output
    assert "Import completed successfully!" in output


@pytest.mark.integration
def test_load_data_main_entrypoint(
    tmp_path,
    monkeypatch,
):
    """Executing load_data.py directly should run main()."""

    test_json = json.dumps(
        [
            {
                "program":
                    "Computer Science",
                "url":
                    "https://example.com/result/500",
                "status":
                    "Accepted",
            }
        ]
    )

    original_path_open = Path.open

    def fake_path_open(
        self,
        mode="r",
        *args,
        **kwargs,
    ):
        if (
            self.name
            == "llm_extend_applicant_data.json"
            and "r" in mode
        ):
            return io.StringIO(
                test_json
            )

        return original_path_open(
            self,
            mode,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        Path,
        "open",
        fake_path_open,
    )

    fake_connection = FakeConnection()

    monkeypatch.setattr(
        load_data.psycopg,
        "connect",
        lambda **_kwargs:
            fake_connection,
    )

    monkeypatch.setenv(
        "PGHOST",
        "localhost",
    )
    monkeypatch.setenv(
        "PGPORT",
        "5432",
    )
    monkeypatch.setenv(
        "PGDATABASE",
        "gradcafe",
    )
    monkeypatch.setenv(
        "PGUSER",
        "test_user",
    )
    monkeypatch.setenv(
        "PGPASSWORD",
        "test_password",
    )

    runpy.run_path(
        load_data.__file__,
        run_name="__main__",
    )

    assert len(
        fake_connection
        .fake_cursor
        .inserted_records
    ) == 1