"""Tests for SQLAlchemy database configuration and ORM inserts."""

from datetime import date

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

from models import (
    Applicant,
    ApplicantOriginalUniversity,
    Base,
    get_engine,
    get_session,
)


def make_database_url(tmp_path):
    """Create a temporary SQLite database URL."""

    database_file = tmp_path / "test_gradcafe.db"

    return f"sqlite+pysqlite:///{database_file.as_posix()}"


@pytest.mark.db
def test_get_engine_requires_database_url(monkeypatch):
    """get_engine should fail clearly when no database URL is supplied."""

    monkeypatch.delenv(
        "DATABASE_URL",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="DATABASE_URL is not set",
    ):
        get_engine()


@pytest.mark.db
def test_get_engine_uses_environment_database_url(
    tmp_path,
    monkeypatch,
):
    """get_engine should read DATABASE_URL from the environment."""

    database_url = make_database_url(tmp_path)

    monkeypatch.setenv(
        "DATABASE_URL",
        database_url,
    )

    engine = get_engine()

    assert str(engine.url) == database_url


@pytest.mark.db
def test_database_schema_can_be_created(tmp_path):
    """The ORM should create both required tables."""

    database_url = make_database_url(tmp_path)

    engine = get_engine(database_url)

    Base.metadata.create_all(engine)

    inspector = inspect(engine)

    table_names = inspector.get_table_names()

    assert "applicants" in table_names

    assert (
        "applicant_original_universities"
        in table_names
    )


@pytest.mark.db
def test_insert_and_select_applicant(tmp_path):
    """An applicant and university record should insert and query correctly."""

    database_url = make_database_url(tmp_path)

    engine = get_engine(database_url)

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    with Session() as session:
        applicant = Applicant(
            p_id=1,
            program="Computer Science",
            comments="Test applicant",
            url="https://example.com/1",
            status="Accepted",
            date_added=date(2026, 1, 15),
            term="Fall 2026",
            us_or_international="American",
            gpa=3.9,
            gre=168.0,
            gre_v=162.0,
            gre_aw=4.5,
            degree="PhD",
            llm_generated_program="Computer Science",
            llm_generated_university="Johns Hopkins University",
        )

        university = ApplicantOriginalUniversity(
            p_id=1,
            university="Johns Hopkins University",
        )

        applicant.original_university = university

        session.add(applicant)

        session.commit()

    with Session() as session:
        stored_applicant = (
            session.query(Applicant)
            .filter_by(p_id=1)
            .one()
        )

        assert stored_applicant.program == "Computer Science"
        assert stored_applicant.status == "Accepted"
        assert stored_applicant.term == "Fall 2026"
        assert stored_applicant.gpa == 3.9

        assert (
            stored_applicant.original_university.university
            == "Johns Hopkins University"
        )


@pytest.mark.db
def test_get_session_accepts_test_database_url(tmp_path):
    """get_session should allow tests to inject another database."""

    database_url = make_database_url(tmp_path)

    engine = get_engine(database_url)

    Base.metadata.create_all(engine)

    session = get_session(database_url)

    try:
        applicant = Applicant(
            p_id=2,
            program="Data Science",
            status="Accepted",
            term="Fall 2026",
        )

        session.add(applicant)

        session.commit()

        stored_applicant = (
            session.query(Applicant)
            .filter_by(p_id=2)
            .one()
        )

        assert stored_applicant.program == "Data Science"

    finally:
        session.close()