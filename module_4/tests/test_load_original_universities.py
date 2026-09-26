"""Tests for loading original university names."""

import io
import json
import runpy
from pathlib import Path

import pytest

import load_data
import load_original_universities as original_loader


class FakeCursor:
    """Fake PostgreSQL cursor for loader tests."""

    def __init__(self, count=2):
        self.count = count
        self.rows = None
        self.executemany_sql = None
        self.executed_sql = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def executemany(self, sql, rows):
        self.executemany_sql = sql
        self.rows = list(rows)

    def execute(self, sql):
        self.executed_sql = sql

    def fetchone(self):
        return (self.count,)


class FakeConnection:
    """Fake PostgreSQL connection for loader tests."""

    def __init__(self, count=2):
        self.fake_cursor = FakeCursor(count)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return self.fake_cursor


@pytest.mark.db
def test_get_applicant_id():
    """The numeric GradCafe result ID should be extracted."""

    result = original_loader.get_applicant_id(
        {
            "url":
                "https://www.thegradcafe.com/result/12345"
        }
    )

    assert result == 12345


@pytest.mark.db
def test_get_applicant_id_with_suffix():
    """Result IDs should work with a URL suffix."""

    result = original_loader.get_applicant_id(
        {
            "url":
                "https://www.thegradcafe.com/result/9876/?test=yes"
        }
    )

    assert result == 9876


@pytest.mark.db
def test_get_applicant_id_rejects_missing_url():
    """A missing URL should raise ValueError."""

    with pytest.raises(
        ValueError,
        match="Applicant record is missing its URL",
    ):
        original_loader.get_applicant_id(
            {"url": ""}
        )


@pytest.mark.db
def test_get_applicant_id_rejects_invalid_url():
    """A non-result URL should raise ValueError."""

    with pytest.raises(
        ValueError,
        match="Cannot extract applicant ID",
    ):
        original_loader.get_applicant_id(
            {
                "url":
                    "https://www.thegradcafe.com/survey/"
            }
        )


@pytest.mark.db
def test_main_loads_original_universities(
    tmp_path,
    monkeypatch,
    capsys,
):
    """Original university names should be inserted into the table."""

    data_file = (
        tmp_path
        / "llm_extend_applicant_data.json"
    )

    records = [
        {
            "url":
                "https://www.thegradcafe.com/result/101",
            "university":
                "  Johns Hopkins University  ",
        },
        {
            "url":
                "https://www.thegradcafe.com/result/202",
            "university": "",
        },
    ]

    data_file.write_text(
        json.dumps(records),
        encoding="utf-8",
    )

    fake_connection = FakeConnection(
        count=2
    )

    monkeypatch.setattr(
        original_loader,
        "DATA_FILE",
        data_file,
    )

    monkeypatch.setattr(
        original_loader,
        "connect_to_database",
        lambda: fake_connection,
    )

    original_loader.main()

    cursor = fake_connection.fake_cursor

    assert cursor.rows == [
        (
            101,
            "Johns Hopkins University",
        ),
        (
            202,
            None,
        ),
    ]

    assert (
        "INSERT INTO "
        "applicant_original_universities"
        in cursor.executemany_sql
    )

    assert (
        "ON CONFLICT (p_id)"
        in cursor.executemany_sql
    )

    assert (
        "SELECT COUNT(*) FROM "
        "applicant_original_universities"
        in cursor.executed_sql
    )

    output = capsys.readouterr().out

    assert (
        "Original university records loaded: 2"
        in output
    )


@pytest.mark.integration
def test_main_entrypoint(
    monkeypatch,
    capsys,
):
    """Running the script directly should execute main()."""

    test_json = json.dumps(
        [
            {
                "url":
                    "https://www.thegradcafe.com/result/303",
                "university":
                    "Example University",
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

    fake_connection = FakeConnection(
        count=1
    )

    # When runpy executes the module again, it imports this
    # function from load_data, so patch it there.
    monkeypatch.setattr(
        load_data,
        "connect_to_database",
        lambda: fake_connection,
    )

    runpy.run_path(
        original_loader.__file__,
        run_name="__main__",
    )

    assert (
        fake_connection
        .fake_cursor
        .rows
        == [
            (
                303,
                "Example University",
            )
        ]
    )

    output = capsys.readouterr().out

    assert (
        "Original university records loaded: 1"
        in output
    )