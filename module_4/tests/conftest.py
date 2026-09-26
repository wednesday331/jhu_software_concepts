"""Shared pytest fixtures for the Module 4 test suite."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from app import create_app


@contextmanager
def fake_session_factory():
    """Provide a fake database session for Flask tests."""
    yield object()


def fake_analysis_results(_session):
    """Return predictable analysis data without querying PostgreSQL."""

    return SimpleNamespace(
        fall_2026_count=100,
        international_percentage=39.276,
        average_gpa=3.765,
        average_gre=165.876,
        average_gre_v=160.804,
        average_gre_aw=4.356,
        american_gpa=3.786,
        fall_2025_acceptance_percentage=47.956,
        accepted_gpa=3.781,
        jhu_count=8,
        original_count=28,
        llm_count=24,
        difference=-4,
        acceptance_by_group=[
            SimpleNamespace(
                group="American",
                accepted=60,
                total=100,
                percentage=60.0,
            ),
            SimpleNamespace(
                group="International",
                accepted=40,
                total=80,
                percentage=50.0,
            ),
        ],
        top_universities=[
            SimpleNamespace(university="University A", count=50),
            SimpleNamespace(university="University B", count=40),
            SimpleNamespace(university="University C", count=30),
            SimpleNamespace(university="University D", count=20),
            SimpleNamespace(university="University E", count=10),
        ],
    )


@pytest.fixture
def app():
    """Create a Flask application configured for testing."""

    test_app = create_app(
        config={
            "TESTING": True,
        },
        session_factory=fake_session_factory,
        analysis_query=fake_analysis_results,
        pull_runner=lambda: "Fake pull completed.",
    )

    return test_app


@pytest.fixture
def client(app):
    """Return Flask's test client."""

    return app.test_client()