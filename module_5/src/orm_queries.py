"""
Module 3: SQLAlchemy ORM Query Analysis

Reproduce the nine required SQL questions and two original
questions using SQLAlchemy ORM queries.

The underlying PostgreSQL tables are not modified.
"""

# pylint: disable=not-callable

from sqlalchemy import func, or_

from models import (
    Applicant,
    ApplicantOriginalUniversity,
    get_session,
)


def normalized(column):
    """Trim whitespace and convert text to lowercase."""
    return func.lower(func.trim(column))


def accepted_condition():
    """Match admission statuses beginning with 'accept'."""
    return normalized(Applicant.status).like("accept%")


def fall_2026_condition():
    """Return the SQLAlchemy condition matching Fall 2026."""
    return normalized(Applicant.term) == "fall 2026"


def fall_2025_condition():
    """Return the SQLAlchemy condition matching Fall 2025."""
    return normalized(Applicant.term) == "fall 2025"


def phd_condition():
    """Match the PhD and doctoral degree labels used in the SQL analysis."""
    degree = normalized(Applicant.degree)

    return or_(
        degree.in_(
            [
                "phd",
                "ph.d.",
                "ph.d",
                "doctorate",
                "doctoral",
            ]
        ),
        degree.like("doctor%"),
    )


def masters_condition():
    """Match master's degree labels."""
    degree = normalized(Applicant.degree)

    return or_(
        degree.in_(
            [
                "masters",
                "master",
                "master's",
                "ms",
                "m.s.",
                "msc",
                "m.sc.",
            ]
        ),
        degree.like("master%"),
    )


def computer_science_condition(column):
    """Match Computer Science or the standalone abbreviation CS."""
    return or_(
        column.op("~*")(
            r"computer[[:space:]]*science"
        ),
        column.op("~*")(
            r"(^|[^[:alnum:]])cs([^[:alnum:]]|$)"
        ),
    )


def university_condition(column):
    """Match the four universities used in Questions 8 and 9."""
    return or_(
        column.op("~*")("georgetown"),
        column.op("~*")(
            r"massachusetts[[:space:]]+institute"
            r"[[:space:]]+of[[:space:]]+technology"
        ),
        column.op("~*")(
            r"(^|[^[:alnum:]])mit([^[:alnum:]]|$)"
        ),
        column.op("~*")("stanford"),
        column.op("~*")(
            r"carnegie[[:space:]]+mellon"
        ),
        column.op("~*")(
            r"(^|[^[:alnum:]])cmu([^[:alnum:]]|$)"
        ),
    )


def format_average(value):
    """Format an average to two decimal places or return N/A."""
    return f"{value:.2f}" if value is not None else "N/A"


def format_percentage(value):
    """Format a percentage to two decimal places or return N/A."""
    return f"{value:.2f}%" if value is not None else "N/A"


# ---------------------------------------------------------
# Question 1
# ---------------------------------------------------------


def question_1(session):
    """Print the Fall 2026 applicant count."""
    count = (
        session.query(func.count(Applicant.p_id))
        .filter(fall_2026_condition())
        .limit(1)
        .scalar()
    )

    print(f"Fall 2026 applicant count: {count:,}")


# ---------------------------------------------------------
# Question 2
# ---------------------------------------------------------


def question_2(session):
    """Print the percentage of classified applicants who are international."""
    nationality = normalized(Applicant.us_or_international)

    international_count = (
        session.query(func.count(Applicant.p_id))
        .filter(nationality == "international")
        .limit(1)
        .scalar()
    )

    classified_count = (
        session.query(func.count(Applicant.p_id))
        .filter(
            func.nullif(
                func.trim(Applicant.us_or_international),
                "",
            ).isnot(None)
        )
        .limit(1)
        .scalar()
    )

    percentage = (
        100.0 * international_count / classified_count
        if classified_count
        else None
    )

    print(f"Percent international: {format_percentage(percentage)}")


# ---------------------------------------------------------
# Question 3
# ---------------------------------------------------------


def question_3(session):
    """Print average GPA and GRE values for valid applicant records."""
    averages = (
        session.query(
            func.avg(Applicant.gpa).filter(
                Applicant.gpa.between(0, 4)
            ),
            func.avg(Applicant.gre).filter(
                Applicant.gre.between(130, 170)
            ),
            func.avg(Applicant.gre_v).filter(
                Applicant.gre_v.between(130, 170)
            ),
            func.avg(Applicant.gre_aw).filter(
                Applicant.gre_aw.between(0, 6)
            ),
        )
        .limit(1)
        .one()
    )

    print(f"Average GPA: {format_average(averages[0])}")
    print(f"Average GRE Quantitative: {format_average(averages[1])}")
    print(f"Average GRE Verbal: {format_average(averages[2])}")
    print(
        "Average GRE Analytical Writing: "
        f"{format_average(averages[3])}"
    )


# ---------------------------------------------------------
# Question 4
# ---------------------------------------------------------


def question_4(session):
    """Print the average GPA of American Fall 2026 applicants."""
    average = (
        session.query(func.avg(Applicant.gpa))
        .filter(
            fall_2026_condition(),
            normalized(Applicant.us_or_international) == "american",
            Applicant.gpa.isnot(None),
        )
        .limit(1)
        .scalar()
    )

    print(
        "Average GPA of American Fall 2026 applicants: "
        f"{format_average(average)}"
    )


# ---------------------------------------------------------
# Question 5
# ---------------------------------------------------------


def question_5(session):
    """Print the Fall 2025 acceptance percentage."""
    total = (
        session.query(func.count(Applicant.p_id))
        .filter(fall_2025_condition())
        .limit(1)
        .scalar()
    )

    accepted = (
        session.query(func.count(Applicant.p_id))
        .filter(
            fall_2025_condition(),
            accepted_condition(),
        )
        .limit(1)
        .scalar()
    )

    percentage = 100.0 * accepted / total if total else None

    print(
        "Fall 2025 acceptance percentage: "
        f"{format_percentage(percentage)}"
    )


# ---------------------------------------------------------
# Question 6
# ---------------------------------------------------------


def question_6(session):
    """Print the average GPA of accepted Fall 2026 applicants."""
    average = (
        session.query(func.avg(Applicant.gpa))
        .filter(
            fall_2026_condition(),
            accepted_condition(),
            Applicant.gpa.isnot(None),
        )
        .limit(1)
        .scalar()
    )

    print(
        "Average GPA of accepted Fall 2026 applicants: "
        f"{format_average(average)}"
    )


# ---------------------------------------------------------
# Question 7
# ---------------------------------------------------------


def question_7(session):
    """Print the JHU Computer Science master's applicant count."""
    university = ApplicantOriginalUniversity.university

    jhu_condition = or_(
        university.op("~*")(
            r"johns[[:space:]]*hopkins"
        ),
        university.op("~*")(
            r"(^|[^[:alnum:]])jhu([^[:alnum:]]|$)"
        ),
    )

    count = (
        session.query(func.count(Applicant.p_id))
        .join(
            ApplicantOriginalUniversity,
            Applicant.p_id == ApplicantOriginalUniversity.p_id,
        )
        .filter(
            jhu_condition,
            computer_science_condition(Applicant.program),
            masters_condition(),
        )
        .limit(1)
        .scalar()
    )

    print(
        "JHU Computer Science master's applicant count: "
        f"{count:,}"
    )


# ---------------------------------------------------------
# Question 8
# ---------------------------------------------------------


def question_8(session):
    """Print and return the original-field count for Question 8."""
    count = (
        session.query(func.count(Applicant.p_id))
        .join(
            ApplicantOriginalUniversity,
            Applicant.p_id == ApplicantOriginalUniversity.p_id,
        )
        .filter(
            fall_2026_condition(),
            accepted_condition(),
            phd_condition(),
            computer_science_condition(Applicant.program),
            university_condition(
                ApplicantOriginalUniversity.university
            ),
        )
        .limit(1)
        .scalar()
    )

    print(f"Original-field count (Question 8): {count:,}")

    return count


# ---------------------------------------------------------
# Question 9
# ---------------------------------------------------------


def question_9(session, original_count):
    """Print the LLM-field count and difference from Question 8."""
    llm_count = (
        session.query(func.count(Applicant.p_id))
        .filter(
            fall_2026_condition(),
            accepted_condition(),
            phd_condition(),
            computer_science_condition(
                Applicant.llm_generated_program
            ),
            university_condition(
                Applicant.llm_generated_university
            ),
        )
        .limit(1)
        .scalar()
    )

    difference = llm_count - original_count

    print(f"LLM-field count (Question 9): {llm_count:,}")
    print(
        "Difference (Question 9 minus Question 8): "
        f"{difference:+,}"
    )


# ---------------------------------------------------------
# Original Question 1
# ---------------------------------------------------------


def original_question_1(session):
    """Print Fall 2026 acceptance rates by applicant nationality group."""
    nationality = func.trim(Applicant.us_or_international)

    results = (
        session.query(
            nationality.label("nationality"),
            func.count(Applicant.p_id).label("applicant_count"),
            func.count(Applicant.p_id)
            .filter(accepted_condition())
            .label("accepted_count"),
        )
        .filter(
            fall_2026_condition(),
            normalized(Applicant.us_or_international).in_(
                ["american", "international"]
            ),
        )
        .group_by(nationality)
        .order_by(nationality)
        .limit(2)
        .all()
    )

    print(
        "Among Fall 2026 American and International applicants, "
        "what percentage of each group received an acceptance?"
    )

    for nationality_value, total, accepted in results:
        percentage = 100.0 * accepted / total if total else None

        print(
            f"{nationality_value}: "
            f"{accepted:,} accepted out of "
            f"{total:,} applicants "
            f"({format_percentage(percentage)})"
        )


# ---------------------------------------------------------
# Original Question 2
# ---------------------------------------------------------


def original_question_2(session):
    """Print the five universities with the most Fall 2026 applicants."""
    university = func.trim(
        ApplicantOriginalUniversity.university
    )

    results = (
        session.query(
            university.label("university"),
            func.count(Applicant.p_id).label("applicant_count"),
        )
        .join(
            ApplicantOriginalUniversity,
            Applicant.p_id == ApplicantOriginalUniversity.p_id,
        )
        .filter(
            fall_2026_condition(),
            func.nullif(university, "").isnot(None),
        )
        .group_by(university)
        .order_by(
            func.count(Applicant.p_id).desc(),
            university.asc(),
        )
        .limit(5)
        .all()
    )

    print(
        "Which five universities have the most Fall 2026 "
        "applicant entries?"
    )

    for rank, (university_name, count) in enumerate(
        results,
        start=1,
    ):
        print(f"{rank}. {university_name}: {count:,}")


def main():
    """Execute all eleven SQLAlchemy analyses."""

    with get_session() as session:
        print("QUESTION 1")
        question_1(session)

        print("\nQUESTION 2")
        question_2(session)

        print("\nQUESTION 3")
        question_3(session)

        print("\nQUESTION 4")
        question_4(session)

        print("\nQUESTION 5")
        question_5(session)

        print("\nQUESTION 6")
        question_6(session)

        print("\nQUESTION 7")
        question_7(session)

        print("\nQUESTION 8")
        original_count = question_8(session)

        print("\nQUESTION 9")
        question_9(session, original_count)

        print("\nORIGINAL QUESTION 1")
        original_question_1(session)

        print("\nORIGINAL QUESTION 2")
        original_question_2(session)


def get_analysis_results(session):  # pylint: disable=too-many-locals
    """Return all 11 analysis results for the Flask webpage."""

    nationality = normalized(Applicant.us_or_international)

    # Question 1
    fall_2026_count = (
        session.query(func.count(Applicant.p_id))
        .filter(fall_2026_condition())
        .limit(1)
        .scalar()
    )

    # Question 2
    international_count = (
        session.query(func.count(Applicant.p_id))
        .filter(nationality == "international")
        .limit(1)
        .scalar()
    )

    classified_count = (
        session.query(func.count(Applicant.p_id))
        .filter(
            func.nullif(
                func.trim(Applicant.us_or_international), ""
            ).isnot(None)
        )
        .limit(1)
        .scalar()
    )

    international_percentage = (
        100.0 * international_count / classified_count
        if classified_count else None
    )

    # Question 3
    averages = (
        session.query(
            func.avg(Applicant.gpa).filter(
                Applicant.gpa.between(0, 4)
            ),
            func.avg(Applicant.gre).filter(
                Applicant.gre.between(130, 170)
            ),
            func.avg(Applicant.gre_v).filter(
                Applicant.gre_v.between(130, 170)
            ),
            func.avg(Applicant.gre_aw).filter(
                Applicant.gre_aw.between(0, 6)
            ),
        )
        .limit(1)
        .one()
    )

    # Question 4
    american_gpa = (
        session.query(func.avg(Applicant.gpa))
        .filter(
            fall_2026_condition(),
            nationality == "american",
            Applicant.gpa.isnot(None),
        )
        .limit(1)
        .scalar()
    )

    # Question 5
    fall_2025_count = (
        session.query(func.count(Applicant.p_id))
        .filter(fall_2025_condition())
        .limit(1)
        .scalar()
    )

    fall_2025_accepted = (
        session.query(func.count(Applicant.p_id))
        .filter(
            fall_2025_condition(),
            accepted_condition(),
        )
        .limit(1)
        .scalar()
    )

    fall_2025_acceptance_percentage = (
        100.0 * fall_2025_accepted / fall_2025_count
        if fall_2025_count else None
    )

    # Question 6
    accepted_gpa = (
        session.query(func.avg(Applicant.gpa))
        .filter(
            fall_2026_condition(),
            accepted_condition(),
            Applicant.gpa.isnot(None),
        )
        .limit(1)
        .scalar()
    )

    # Question 7
    original_university = ApplicantOriginalUniversity.university

    jhu_count = (
        session.query(func.count(Applicant.p_id))
        .join(
            ApplicantOriginalUniversity,
            Applicant.p_id == ApplicantOriginalUniversity.p_id,
        )
        .filter(
            or_(
                original_university.op("~*")(
                    r"johns[[:space:]]*hopkins"
                ),
                original_university.op("~*")(
                    r"(^|[^[:alnum:]])jhu([^[:alnum:]]|$)"
                ),
            ),
            computer_science_condition(Applicant.program),
            masters_condition(),
        )
        .limit(1)
        .scalar()
    )

    # Question 8
    original_count = (
        session.query(func.count(Applicant.p_id))
        .join(
            ApplicantOriginalUniversity,
            Applicant.p_id == ApplicantOriginalUniversity.p_id,
        )
        .filter(
            fall_2026_condition(),
            accepted_condition(),
            phd_condition(),
            computer_science_condition(Applicant.program),
            university_condition(original_university),
        )
        .limit(1)
        .scalar()
    )

    # Question 9
    llm_count = (
        session.query(func.count(Applicant.p_id))
        .filter(
            fall_2026_condition(),
            accepted_condition(),
            phd_condition(),
            computer_science_condition(
                Applicant.llm_generated_program
            ),
            university_condition(
                Applicant.llm_generated_university
            ),
        )
        .limit(1)
        .scalar()
    )

    # Original Question 1
    group_results = (
        session.query(
            func.trim(Applicant.us_or_international).label("group"),
            func.count(Applicant.p_id).label("total"),
            func.count(Applicant.p_id)
            .filter(accepted_condition())
            .label("accepted"),
        )
        .filter(
            fall_2026_condition(),
            nationality.in_(["american", "international"]),
        )
        .group_by(func.trim(Applicant.us_or_international))
        .order_by(func.trim(Applicant.us_or_international))
        .limit(2)
        .all()
    )

    acceptance_by_group = [
        {
            "group": group,
            "total": total,
            "accepted": accepted,
            "percentage": (
                100.0 * accepted / total if total else None
            ),
        }
        for group, total, accepted in group_results
    ]

    # Original Question 2
    university_name = func.trim(
        ApplicantOriginalUniversity.university
    )

    top_universities = (
        session.query(
            university_name.label("university"),
            func.count(Applicant.p_id).label("count"),
        )
        .join(
            ApplicantOriginalUniversity,
            Applicant.p_id == ApplicantOriginalUniversity.p_id,
        )
        .filter(
            fall_2026_condition(),
            func.nullif(university_name, "").isnot(None),
        )
        .group_by(university_name)
        .order_by(
            func.count(Applicant.p_id).desc(),
            university_name.asc(),
        )
        .limit(5)
        .all()
    )

    return {
        "fall_2026_count": fall_2026_count,
        "international_percentage": international_percentage,
        "average_gpa": averages[0],
        "average_gre": averages[1],
        "average_gre_v": averages[2],
        "average_gre_aw": averages[3],
        "american_gpa": american_gpa,
        "fall_2025_acceptance_percentage":
            fall_2025_acceptance_percentage,
        "accepted_gpa": accepted_gpa,
        "jhu_count": jhu_count,
        "original_count": original_count,
        "llm_count": llm_count,
        "difference": llm_count - original_count,
        "acceptance_by_group": acceptance_by_group,
        "top_universities": [
            {"university": name, "count": count}
            for name, count in top_universities
        ],
    }


if __name__ == "__main__":
    main()
