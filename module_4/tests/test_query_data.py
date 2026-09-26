"""Tests for the raw SQL analysis functions in query_data.py."""

import runpy

import pytest

import query_data


class FakeCursor:
    """Fake cursor that returns results based on the SQL executed."""

    def __init__(self):
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql):
        self.sql = sql

    def fetchone(self):
        sql = self.sql.lower()

        # Question 7
        if (
            "johns" in sql
            and "applicant_original_universities" in sql
        ):
            return (8,)

        # Question 8
        if (
            "georgetown" in sql
            and "applicant_original_universities" in sql
        ):
            return (28,)

        # Question 9
        if (
            "llm_generated_program" in sql
            and "llm_generated_university" in sql
        ):
            return (24,)

        # Question 3
        if "avg(gpa) filter" in sql:
            return (
                3.77,
                165.88,
                160.80,
                4.36,
            )

        # Question 4
        if (
            "avg(gpa)" in sql
            and "american" in sql
        ):
            return (3.79,)

        # Question 5
        if "fall 2025" in sql:
            return (47.96,)

        # Question 6
        if (
            "avg(gpa)" in sql
            and "accept%" in sql
            and "fall 2026" in sql
        ):
            return (3.78,)

        # Question 2
        if (
            "us_or_international" in sql
            and "100.0" in sql
        ):
            return (46.57,)

        # Question 1
        if (
            "count(*)" in sql
            and "fall 2026" in sql
        ):
            return (29901,)

        raise AssertionError(
            f"Unexpected SQL passed to fetchone:\n{self.sql}"
        )

    def fetchall(self):
        sql = self.sql.lower()

        # Original Question 1
        if (
            "group by trim(us_or_international)"
            in sql
        ):
            return [
                (
                    "American",
                    100,
                    60,
                    60.0,
                ),
                (
                    "International",
                    80,
                    40,
                    50.0,
                ),
            ]

        # Original Question 2
        if "limit 5" in sql:
            return [
                ("University A", 50),
                ("University B", 40),
                ("University C", 30),
                ("University D", 20),
                ("University E", 10),
            ]

        raise AssertionError(
            f"Unexpected SQL passed to fetchall:\n{self.sql}"
        )


class FakeConnection:
    """Fake PostgreSQL connection for SQL-analysis tests."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return FakeCursor()


@pytest.mark.db
def test_connect_to_database_uses_environment(
    monkeypatch,
):
    """Database environment variables should be passed to psycopg."""

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

    captured = {}

    fake_connection = FakeConnection()

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return fake_connection

    monkeypatch.setattr(
        query_data.psycopg,
        "connect",
        fake_connect,
    )

    result = query_data.connect_to_database()

    assert result is fake_connection

    assert captured == {
        "host": "localhost",
        "port": "5432",
        "dbname": "gradcafe",
        "user": "test_user",
        "password": "test_password",
    }


@pytest.mark.db
def test_fetch_one_executes_sql():
    """fetch_one should execute SQL and return the first row."""

    connection = FakeConnection()

    result = query_data.fetch_one(
        connection,
        """
        SELECT COUNT(*)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026';
        """,
    )

    assert result == (29901,)


@pytest.mark.analysis
def test_format_average():
    """Averages should use two decimals or N/A."""

    assert (
        query_data.format_average(3.776)
        == "3.78"
    )

    assert (
        query_data.format_average(None)
        == "N/A"
    )


@pytest.mark.analysis
def test_format_percentage():
    """Percentages should use two decimals and a percent sign."""

    assert (
        query_data.format_percentage(46.567)
        == "46.57%"
    )

    assert (
        query_data.format_percentage(None)
        == "N/A"
    )


@pytest.mark.analysis
def test_all_analysis_questions(
    capsys,
):
    """All eleven analysis functions should execute and format results."""

    connection = FakeConnection()

    query_data.question_1(connection)
    query_data.question_2(connection)
    query_data.question_3(connection)
    query_data.question_4(connection)
    query_data.question_5(connection)
    query_data.question_6(connection)
    query_data.question_7(connection)

    original_count = (
        query_data.question_8(
            connection
        )
    )

    query_data.question_9(
        connection,
        original_count,
    )

    query_data.original_question_1(
        connection
    )

    query_data.original_question_2(
        connection
    )

    assert original_count == 28

    output = capsys.readouterr().out

    assert (
        "Fall 2026 applicant count: 29,901"
        in output
    )

    assert (
        "Percent international: 46.57%"
        in output
    )

    assert "Average GPA: 3.77" in output

    assert (
        "Average GRE Quantitative: 165.88"
        in output
    )

    assert (
        "Average GRE Verbal: 160.80"
        in output
    )

    assert (
        "Average GRE Analytical Writing: 4.36"
        in output
    )

    assert (
        "Average GPA of American "
        "Fall 2026 applicants: 3.79"
        in output
    )

    assert (
        "Fall 2025 acceptance percentage: "
        "47.96%"
        in output
    )

    assert (
        "Average GPA of accepted "
        "Fall 2026 applicants: 3.78"
        in output
    )

    assert (
        "JHU Computer Science master's "
        "applicant count: 8"
        in output
    )

    assert (
        "Original-field count "
        "(Question 8): 28"
        in output
    )

    assert (
        "LLM-field count "
        "(Question 9): 24"
        in output
    )

    assert (
        "Difference "
        "(Question 9 minus Question 8): -4"
        in output
    )

    assert (
        "American: 60 accepted out of "
        "100 applicants (60.00%)"
        in output
    )

    assert (
        "International: 40 accepted out of "
        "80 applicants (50.00%)"
        in output
    )

    assert (
        "1. University A: 50"
        in output
    )

    assert (
        "5. University E: 10"
        in output
    )


@pytest.mark.integration
def test_main_runs_all_questions(
    monkeypatch,
    capsys,
):
    """main() should execute the complete analysis workflow."""

    monkeypatch.setattr(
        query_data,
        "connect_to_database",
        lambda: FakeConnection(),
    )

    query_data.main()

    output = capsys.readouterr().out

    assert "QUESTION 1" in output
    assert "QUESTION 9" in output
    assert "ORIGINAL QUESTION 1" in output
    assert "ORIGINAL QUESTION 2" in output

    assert (
        "Original-field count "
        "(Question 8): 28"
        in output
    )

    assert (
        "LLM-field count "
        "(Question 9): 24"
        in output
    )


@pytest.mark.integration
def test_query_data_main_entrypoint(
    monkeypatch,
    capsys,
):
    """Executing query_data.py directly should call main()."""

    fake_connection = FakeConnection()

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

    # runpy re-executes query_data.py, but psycopg is the
    # same imported Python module, so this patch remains active.
    monkeypatch.setattr(
        query_data.psycopg,
        "connect",
        lambda **_kwargs:
            fake_connection,
    )

    runpy.run_path(
        query_data.__file__,
        run_name="__main__",
    )

    output = capsys.readouterr().out

    assert "QUESTION 1" in output
    assert "QUESTION 9" in output

    assert (
        "Fall 2026 applicant count: 29,901"
        in output
    )

    assert (
        "Difference "
        "(Question 9 minus Question 8): -4"
        in output
    )