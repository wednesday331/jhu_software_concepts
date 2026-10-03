"""Tests for SQLAlchemy ORM analysis queries."""

import runpy

import pytest

import models
import orm_queries


class FakeQuery:
    """Chainable stand-in for a SQLAlchemy Query object."""

    def __init__(self, session):
        self.session = session

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def group_by(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def scalar(self):
        if not self.session.scalar_results:
            raise AssertionError(
                "No fake scalar result remains."
            )

        return self.session.scalar_results.pop(0)

    def one(self):
        if not self.session.one_results:
            raise AssertionError(
                "No fake one() result remains."
            )

        return self.session.one_results.pop(0)

    def all(self):
        if not self.session.all_results:
            raise AssertionError(
                "No fake all() result remains."
            )

        return self.session.all_results.pop(0)


class FakeSession:
    """Fake SQLAlchemy session with predetermined query results."""

    def __init__(
        self,
        scalar_results=None,
        one_results=None,
        all_results=None,
    ):
        self.scalar_results = list(
            scalar_results or []
        )

        self.one_results = list(
            one_results or []
        )

        self.all_results = list(
            all_results or []
        )

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False

    def query(self, *args, **kwargs):
        return FakeQuery(self)


def standard_session():
    """
    Return fake results matching the order used by
    main() and get_analysis_results().
    """

    return FakeSession(
        scalar_results=[
            29901,   # Question 1
            4657,    # Question 2 international
            10000,   # Question 2 classified
            3.79,    # Question 4
            100,     # Question 5 total
            48,      # Question 5 accepted
            3.78,    # Question 6
            8,       # Question 7
            28,      # Question 8
            24,      # Question 9
        ],
        one_results=[
            (
                3.77,
                165.88,
                160.80,
                4.36,
            ),
        ],
        all_results=[
            [
                (
                    "American",
                    100,
                    60,
                ),
                (
                    "International",
                    80,
                    40,
                ),
            ],
            [
                ("University A", 50),
                ("University B", 40),
                ("University C", 30),
                ("University D", 20),
                ("University E", 10),
            ],
        ],
    )


@pytest.mark.analysis
def test_format_helpers():
    """Formatting helpers should handle values and None."""

    assert (
        orm_queries.format_average(3.776)
        == "3.78"
    )

    assert (
        orm_queries.format_average(None)
        == "N/A"
    )

    assert (
        orm_queries.format_percentage(46.567)
        == "46.57%"
    )

    assert (
        orm_queries.format_percentage(None)
        == "N/A"
    )


@pytest.mark.analysis
def test_condition_helpers_build_sqlalchemy_expressions():
    """All reusable ORM conditions should construct expressions."""

    assert (
        orm_queries.normalized(
            models.Applicant.status
        )
        is not None
    )

    assert (
        orm_queries.accepted_condition()
        is not None
    )

    assert (
        orm_queries.fall_2026_condition()
        is not None
    )

    assert (
        orm_queries.fall_2025_condition()
        is not None
    )

    assert (
        orm_queries.phd_condition()
        is not None
    )

    assert (
        orm_queries.masters_condition()
        is not None
    )

    assert (
        orm_queries.computer_science_condition(
            models.Applicant.program
        )
        is not None
    )

    assert (
        orm_queries.university_condition(
            models.ApplicantOriginalUniversity.university
        )
        is not None
    )


@pytest.mark.analysis
def test_all_question_functions(
    capsys,
):
    """All eleven printable ORM analyses should run successfully."""

    session = standard_session()

    orm_queries.question_1(session)
    orm_queries.question_2(session)
    orm_queries.question_3(session)
    orm_queries.question_4(session)
    orm_queries.question_5(session)
    orm_queries.question_6(session)
    orm_queries.question_7(session)

    original_count = (
        orm_queries.question_8(
            session
        )
    )

    orm_queries.question_9(
        session,
        original_count,
    )

    orm_queries.original_question_1(
        session
    )

    orm_queries.original_question_2(
        session
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
        "Average GPA of American Fall 2026 "
        "applicants: 3.79"
        in output
    )

    assert (
        "Fall 2025 acceptance percentage: "
        "48.00%"
        in output
    )

    assert (
        "Average GPA of accepted Fall 2026 "
        "applicants: 3.78"
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


@pytest.mark.analysis
def test_zero_denominator_branches(
    capsys,
):
    """Percentage calculations should handle zero totals."""

    question_2_session = FakeSession(
        scalar_results=[
            0,
            0,
        ]
    )

    orm_queries.question_2(
        question_2_session
    )

    question_5_session = FakeSession(
        scalar_results=[
            0,
            0,
        ]
    )

    orm_queries.question_5(
        question_5_session
    )

    group_session = FakeSession(
        all_results=[
            [
                (
                    "American",
                    0,
                    0,
                )
            ]
        ]
    )

    orm_queries.original_question_1(
        group_session
    )

    output = capsys.readouterr().out

    assert (
        "Percent international: N/A"
        in output
    )

    assert (
        "Fall 2025 acceptance percentage: N/A"
        in output
    )

    assert (
        "American: 0 accepted out of "
        "0 applicants (N/A)"
        in output
    )


@pytest.mark.analysis
def test_get_analysis_results():
    """Flask analysis data should be assembled into one dictionary."""

    session = standard_session()

    results = orm_queries.get_analysis_results(
        session
    )

    assert (
        results["fall_2026_count"]
        == 29901
    )

    assert (
        results["international_percentage"]
        == pytest.approx(46.57)
    )

    assert (
        results["average_gpa"]
        == 3.77
    )

    assert (
        results["average_gre"]
        == 165.88
    )

    assert (
        results["average_gre_v"]
        == 160.80
    )

    assert (
        results["average_gre_aw"]
        == 4.36
    )

    assert (
        results["american_gpa"]
        == 3.79
    )

    assert (
        results[
            "fall_2025_acceptance_percentage"
        ]
        == 48.0
    )

    assert (
        results["accepted_gpa"]
        == 3.78
    )

    assert (
        results["jhu_count"]
        == 8
    )

    assert (
        results["original_count"]
        == 28
    )

    assert (
        results["llm_count"]
        == 24
    )

    assert (
        results["difference"]
        == -4
    )

    assert results[
        "acceptance_by_group"
    ] == [
        {
            "group": "American",
            "total": 100,
            "accepted": 60,
            "percentage": 60.0,
        },
        {
            "group": "International",
            "total": 80,
            "accepted": 40,
            "percentage": 50.0,
        },
    ]

    assert results[
        "top_universities"
    ][0] == {
        "university": "University A",
        "count": 50,
    }


@pytest.mark.analysis
def test_get_analysis_results_zero_totals():
    """Flask results should use None when percentages cannot be calculated."""

    session = FakeSession(
        scalar_results=[
            0,     # Fall 2026 count
            0,     # international
            0,     # classified
            None,  # American GPA
            0,     # Fall 2025 total
            0,     # accepted
            None,  # accepted GPA
            0,     # JHU count
            0,     # original count
            0,     # LLM count
        ],
        one_results=[
            (
                None,
                None,
                None,
                None,
            )
        ],
        all_results=[
            [
                (
                    "American",
                    0,
                    0,
                )
            ],
            [],
        ],
    )

    results = orm_queries.get_analysis_results(
        session
    )

    assert (
        results["international_percentage"]
        is None
    )

    assert (
        results[
            "fall_2025_acceptance_percentage"
        ]
        is None
    )

    assert (
        results[
            "acceptance_by_group"
        ][0]["percentage"]
        is None
    )

    assert (
        results["top_universities"]
        == []
    )

    assert (
        results["difference"]
        == 0
    )


@pytest.mark.integration
def test_main_runs_complete_workflow(
    monkeypatch,
    capsys,
):
    """main() should execute all ORM analyses."""

    session = standard_session()

    monkeypatch.setattr(
        orm_queries,
        "get_session",
        lambda: session,
    )

    orm_queries.main()

    output = capsys.readouterr().out

    assert "QUESTION 1" in output
    assert "QUESTION 9" in output

    assert (
        "ORIGINAL QUESTION 1"
        in output
    )

    assert (
        "ORIGINAL QUESTION 2"
        in output
    )

    assert (
        "Original-field count "
        "(Question 8): 28"
        in output
    )


@pytest.mark.integration
def test_orm_queries_main_entrypoint(
    monkeypatch,
    capsys,
):
    """Executing orm_queries.py directly should invoke main()."""

    session = standard_session()

    # runpy imports get_session from models again,
    # so patch models.get_session for this test.
    monkeypatch.setattr(
        models,
        "get_session",
        lambda: session,
    )

    runpy.run_path(
        orm_queries.__file__,
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