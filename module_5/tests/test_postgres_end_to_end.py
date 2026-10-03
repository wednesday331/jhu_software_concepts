"""PostgreSQL end-to-end integration test for Module 4.

This test uses the dedicated gradcafe_test PostgreSQL database configured
by GitHub Actions. It never runs against the normal gradcafe database.
"""

import json
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app as app_module
import load_data
import load_original_universities
from app import create_app
from models import (
    Applicant,
    ApplicantOriginalUniversity,
    Base,
)
from orm_queries import get_analysis_results


class SynchronousThread:
    """Run Flask background work immediately during the test."""

    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon

    def start(self):
        """Execute the target synchronously."""
        self.target()


def require_gradcafe_test_database():
    """Return DATABASE_URL only when the dedicated test DB is configured."""

    database_url = os.environ.get("DATABASE_URL", "")
    pgdatabase = os.environ.get("PGDATABASE", "")

    if not database_url:
        pytest.skip(
            "DATABASE_URL is not configured; PostgreSQL integration "
            "runs in GitHub Actions."
        )

    database_name = make_url(database_url).database

    if (
        database_name != "gradcafe_test"
        or pgdatabase != "gradcafe_test"
    ):
        pytest.skip(
            "PostgreSQL integration test is restricted to "
            "the gradcafe_test database."
        )

    return database_url


def fake_scraper_batches():
    """Return deterministic overlapping records with no network access."""

    applicant_1 = {
        "program": "Computer Science",
        "university": "Johns Hopkins University",
        "comments": "Integration test applicant one",
        "date_added": "Sep 1, 2026",
        "url": "https://www.thegradcafe.com/result/2147400001",
        "status": "Accepted",
        "term": "Fall 2026",
        "student_type": "American",
        "gre": "170",
        "gre_v": "165",
        "gre_aw": "5.0",
        "gpa": "3.90",
        "degree": "Masters",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "Johns Hopkins University",
    }

    applicant_2 = {
        "program": "Computer Science",
        "university": "Massachusetts Institute of Technology",
        "comments": "Integration test applicant two",
        "date_added": "Sep 2, 2026",
        "url": "https://www.thegradcafe.com/result/2147400002",
        "status": "Rejected",
        "term": "Fall 2026",
        "student_type": "International",
        "gre": "166",
        "gre_v": "160",
        "gre_aw": "4.0",
        "gpa": "3.70",
        "degree": "PhD",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": (
            "Massachusetts Institute of Technology"
        ),
    }

    applicant_3 = {
        "program": "Computer Science",
        "university": "Stanford University",
        "comments": "Integration test applicant three",
        "date_added": "Sep 3, 2026",
        "url": "https://www.thegradcafe.com/result/2147400003",
        "status": "Accepted",
        "term": "Fall 2026",
        "student_type": "International",
        "gre": "168",
        "gre_v": "162",
        "gre_aw": "4.5",
        "gpa": "3.80",
        "degree": "PhD",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "Stanford University",
    }

    return [
        [applicant_1, applicant_2],
        [applicant_2, applicant_3],
    ]


@pytest.mark.db
@pytest.mark.integration
def test_postgres_pull_update_render_and_overlap(
    tmp_path,
    monkeypatch,
):
    """
    Verify fake pull -> PostgreSQL -> update -> render -> overlap.

    The first fake scraper batch contains two records. The second batch
    deliberately repeats one record and adds one new record. The real
    PostgreSQL loaders are used, so ON CONFLICT behavior and the real ORM
    analysis are exercised without using the Internet or an LLM.
    """

    database_url = require_gradcafe_test_database()

    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    # This is a dedicated test database. Start from a deterministic state.
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE "
                "applicant_original_universities, applicants "
                "RESTART IDENTITY CASCADE"
            )
        )

    Session = sessionmaker(bind=engine)

    batches = fake_scraper_batches()
    pull_number = {"value": 0}
    test_json = tmp_path / "fake_scraper_records.json"

    # Make both real loaders consume the deterministic fake-scraper file.
    monkeypatch.setattr(load_data, "DATA_FILE", test_json)
    monkeypatch.setattr(
        load_original_universities,
        "DATA_FILE",
        test_json,
    )

    def fake_pull_runner():
        """Simulate one scraper pull, then use the real DB loaders."""

        batch = batches[pull_number["value"]]

        test_json.write_text(
            json.dumps(batch),
            encoding="utf-8",
        )

        load_data.main()
        load_original_universities.main()

        pull_number["value"] += 1

        return (
            f"Fake scraper loaded {len(batch)} records "
            "into PostgreSQL."
        )

    test_app = create_app(
        config={"TESTING": True},
        session_factory=lambda: Session(),
        analysis_query=get_analysis_results,
        pull_runner=fake_pull_runner,
    )

    monkeypatch.setattr(
        app_module,
        "Thread",
        SynchronousThread,
    )

    client = test_app.test_client()

    try:
        # -------------------------------------------------------------
        # First Pull Data operation: two unique fake records.
        # -------------------------------------------------------------
        pull_response = client.post("/pull-data")

        assert pull_response.status_code == 202
        assert pull_response.get_json() == {
            "ok": True,
            "busy": False,
        }

        with Session() as session:
            applicants = (
                session.query(Applicant)
                .order_by(Applicant.p_id)
                .all()
            )

            assert len(applicants) == 2

            # Verify required schema values reached PostgreSQL.
            for applicant in applicants:
                assert applicant.p_id is not None
                assert applicant.program is not None
                assert applicant.comments is not None
                assert applicant.url is not None
                assert applicant.status is not None
                assert applicant.date_added is not None
                assert applicant.term is not None
                assert applicant.us_or_international is not None
                assert applicant.gpa is not None
                assert applicant.gre is not None
                assert applicant.gre_v is not None
                assert applicant.gre_aw is not None
                assert applicant.degree is not None
                assert applicant.llm_generated_program is not None
                assert applicant.llm_generated_university is not None

            assert (
                session.query(ApplicantOriginalUniversity).count()
                == 2
            )

        # Update Analysis must query the real PostgreSQL rows and render them.
        update_response = client.post("/update-analysis")

        assert update_response.status_code == 200

        page = update_response.get_data(as_text=True)

        assert "GradCafe Data Analysis" in page
        assert "Answer:" in page
        assert "2 entries" in page
        assert "50.00%" in page
        assert "3.80" in page
        assert "3.90" in page

        # -------------------------------------------------------------
        # Second Pull Data operation: one overlapping + one new record.
        # -------------------------------------------------------------
        second_pull = client.post("/pull-data")

        assert second_pull.status_code == 202

        with Session() as session:
            assert session.query(Applicant).count() == 3

            # Applicant 2147400002 appeared in both scraper batches.
            # The PostgreSQL primary key + ON CONFLICT behavior must
            # keep exactly one copy.
            overlapping_count = (
                session.query(Applicant)
                .filter(
                    Applicant.p_id == 2147400002
                )
                .count()
            )

            assert overlapping_count == 1

            assert (
                session.query(ApplicantOriginalUniversity).count()
                == 3
            )

        second_update = client.post("/update-analysis")

        assert second_update.status_code == 200

        updated_page = second_update.get_data(as_text=True)

        assert "3 entries" in updated_page
        assert "66.67%" in updated_page
        assert "3.85" in updated_page

    finally:
        # Leave the dedicated CI/test database clean for later tests.
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE "
                    "applicant_original_universities, applicants "
                    "RESTART IDENTITY CASCADE"
                )
            )

        engine.dispose()
