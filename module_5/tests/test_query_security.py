"""Security tests for parameterized applicant search queries."""

import pytest

from query_data import clamp_limit, search_applicants


class FakeCursor:
    """Capture query execution without contacting PostgreSQL."""

    def __init__(self):
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        """Record the query and bound parameters."""
        self.query = query
        self.params = params

    def fetchall(self):
        """Return an empty result set for the unit test."""
        return []


class FakeConnection:
    """Provide one reusable fake cursor."""

    def __init__(self):
        self.fake_cursor = FakeCursor()

    def cursor(self):
        """Return the fake cursor."""
        return self.fake_cursor


def test_clamp_limit_enforces_range_and_default():
    """Clamp result limits to 1-100 and default invalid input safely."""
    assert clamp_limit(0) == 1
    assert clamp_limit(50) == 50
    assert clamp_limit(1000) == 100
    assert clamp_limit("not-a-number") == 25


def test_search_applicants_binds_malicious_value_and_caps_limit():
    """Treat malicious-looking text as a value instead of executable SQL."""
    connection = FakeConnection()
    malicious_value = "'; DROP TABLE applicants; --"

    result = search_applicants(
        connection,
        "program",
        malicious_value,
        limit=1000,
    )

    assert result == []
    assert connection.fake_cursor.params == (malicious_value, 100)


def test_search_applicants_rejects_unapproved_identifier():
    """Reject an unapproved dynamic SQL identifier before execution."""
    connection = FakeConnection()

    with pytest.raises(ValueError, match="Unsupported search column"):
        search_applicants(
            connection,
            "program; DROP TABLE applicants; --",
            "Computer Science",
        )
