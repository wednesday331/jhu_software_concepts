
"""
Module 3: SQL Query Analysis

Answers the nine required SQL questions using PostgreSQL
and Psycopg 3.

All analysis is performed in SQL. Python executes the queries
and formats their results for console output.
"""
# pylint: disable=duplicate-code


import os

import psycopg


def connect_to_database():
    """Connect to PostgreSQL using environment variables."""
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )


def fetch_one(connection, sql):
    """Execute a SQL query and return its first result row."""
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchone()


def format_average(value):
    """Format an average to two decimal places."""
    return f"{value:.2f}" if value is not None else "N/A"


def format_percentage(value):
    """Format a percentage to two decimal places."""
    return f"{value:.2f}%" if value is not None else "N/A"


# ---------------------------------------------------------
# Question 1
# How many entries are from applicants who applied for
# Fall 2026?
# ---------------------------------------------------------

def question_1(connection):
    """Print the Fall 2026 applicant count."""
    sql = """
        SELECT COUNT(*)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026';
    """

    count = fetch_one(connection, sql)[0]

    print(f"Fall 2026 applicant count: {count:,}")


# ---------------------------------------------------------
# Question 2
# What percentage of applicants with a usable nationality
# classification are international?
# ---------------------------------------------------------

def question_2(connection):
    """Print the percentage of classified applicants who are international."""
    sql = """
        SELECT
            100.0 * COUNT(*) FILTER (
                WHERE LOWER(TRIM(us_or_international)) = 'international'
            )
            / NULLIF(
                COUNT(*) FILTER (
                    WHERE NULLIF(TRIM(us_or_international), '') IS NOT NULL
                ),
                0
            )
        FROM applicants;
    """

    percentage = fetch_one(connection, sql)[0]

    print(f"Percent international: {format_percentage(percentage)}")


# ---------------------------------------------------------
# Question 3
# Calculate average GPA, GRE Quantitative, GRE Verbal,
# and GRE Analytical Writing independently.
# ---------------------------------------------------------


def question_3(connection):
    """
    Calculate each average independently.

    Exclude values outside the expected score range for
    the metric being calculated. Do not modify source data.
    """

    sql = """
        SELECT
            AVG(gpa) FILTER (
                WHERE gpa BETWEEN 0 AND 4
            ) AS average_gpa,

            AVG(gre) FILTER (
                WHERE gre BETWEEN 130 AND 170
            ) AS average_gre_quantitative,

            AVG(gre_v) FILTER (
                WHERE gre_v BETWEEN 130 AND 170
            ) AS average_gre_verbal,

            AVG(gre_aw) FILTER (
                WHERE gre_aw BETWEEN 0 AND 6
            ) AS average_gre_analytical_writing

        FROM applicants;
    """

    average_gpa, average_gre, average_gre_v, average_gre_aw = (
        fetch_one(connection, sql)
    )

    print(f"Average GPA: {format_average(average_gpa)}")
    print(f"Average GRE Quantitative: {format_average(average_gre)}")
    print(f"Average GRE Verbal: {format_average(average_gre_v)}")
    print(
        "Average GRE Analytical Writing: "
        f"{format_average(average_gre_aw)}"
    )


# ---------------------------------------------------------
# Question 4
# Average GPA of American applicants who applied for
# Fall 2026.
# ---------------------------------------------------------

def question_4(connection):
    """Print the average GPA of American Fall 2026 applicants."""
    sql = """
        SELECT AVG(gpa)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026'
          AND LOWER(TRIM(us_or_international)) = 'american'
          AND gpa IS NOT NULL;
    """

    average_gpa = fetch_one(connection, sql)[0]

    print(
        "Average GPA of American Fall 2026 applicants: "
        f"{format_average(average_gpa)}"
    )


# ---------------------------------------------------------
# Question 5
# Percentage of Fall 2025 entries that are acceptances.
# ---------------------------------------------------------

def question_5(connection):
    """Print the Fall 2025 acceptance percentage."""
    sql = """
        SELECT
            100.0 * COUNT(*) FILTER (
                WHERE LOWER(TRIM(status)) LIKE 'accept%'
            )
            / NULLIF(COUNT(*), 0)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2025';
    """

    percentage = fetch_one(connection, sql)[0]

    print(
        "Fall 2025 acceptance percentage: "
        f"{format_percentage(percentage)}"
    )


# ---------------------------------------------------------
# Question 6
# Average GPA of accepted Fall 2026 applicants.
# ---------------------------------------------------------

def question_6(connection):
    """Print the average GPA of accepted Fall 2026 applicants."""
    sql = """
        SELECT AVG(gpa)
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026'
          AND LOWER(TRIM(status)) LIKE 'accept%'
          AND gpa IS NOT NULL;
    """

    average_gpa = fetch_one(connection, sql)[0]

    print(
        "Average GPA of accepted Fall 2026 applicants: "
        f"{format_average(average_gpa)}"
    )


# ---------------------------------------------------------
# Question 7
# Count applicants to Johns Hopkins University for a
# master's degree in Computer Science.
#
# Use the original downloaded program and degree fields.
# ---------------------------------------------------------


def question_7(connection):
    """Count JHU Computer Science master's applicants using original fields."""

    sql = """
        SELECT COUNT(*)
        FROM applicants AS a
        JOIN applicant_original_universities AS u
          ON a.p_id = u.p_id
        WHERE (
            u.university ~* 'johns[[:space:]]*hopkins'
            OR u.university ~* '(^|[^[:alnum:]])jhu([^[:alnum:]]|$)'
        )
          AND (
              a.program ~* 'computer[[:space:]]*science'
              OR a.program ~* '(^|[^[:alnum:]])cs([^[:alnum:]]|$)'
          )
          AND (
              LOWER(TRIM(a.degree)) IN (
                  'masters', 'master', 'master''s',
                  'ms', 'm.s.', 'msc', 'm.sc.'
              )
              OR LOWER(TRIM(a.degree)) LIKE 'master%'
          );
    """

    count = fetch_one(connection, sql)[0]

    print(f"JHU Computer Science master's applicant count: {count:,}")


# ---------------------------------------------------------
# Shared SQL matching conditions for Questions 8 and 9.
#
# Question 8 uses the original program field.
# Question 9 uses the LLM-generated program and university.
# ---------------------------------------------------------


ORIGINAL_UNIVERSITY_CONDITION = """
    (
        u.university ~* 'georgetown'
        OR u.university ~* 'massachusetts[[:space:]]+institute[[:space:]]+of[[:space:]]+technology'
        OR u.university ~* '(^|[^[:alnum:]])mit([^[:alnum:]]|$)'
        OR u.university ~* 'stanford'
        OR u.university ~* 'carnegie[[:space:]]+mellon'
        OR u.university ~* '(^|[^[:alnum:]])cmu([^[:alnum:]]|$)'
    )
"""

ORIGINAL_CS_CONDITION = """
    (
        program ~* 'computer[[:space:]]*science'
        OR program ~* '(^|[^[:alnum:]])cs([^[:alnum:]]|$)'
    )
"""

LLM_UNIVERSITY_CONDITION = """
    (
        llm_generated_university ~* 'georgetown'
        OR llm_generated_university ~* 'massachusetts[[:space:]]+institute[[:space:]]+of[[:space:]]+technology'
        OR llm_generated_university ~* '(^|[^[:alnum:]])mit([^[:alnum:]]|$)'
        OR llm_generated_university ~* 'stanford'
        OR llm_generated_university ~* 'carnegie[[:space:]]+mellon'
        OR llm_generated_university ~* '(^|[^[:alnum:]])cmu([^[:alnum:]]|$)'
    )
"""

LLM_CS_CONDITION = """
    (
        llm_generated_program ~* 'computer[[:space:]]*science'
        OR llm_generated_program ~* '(^|[^[:alnum:]])cs([^[:alnum:]]|$)'
    )
"""

PHD_CONDITION = """
    (
        LOWER(TRIM(degree)) IN (
            'phd',
            'ph.d.',
            'ph.d',
            'doctorate',
            'doctoral'
        )
        OR LOWER(TRIM(degree)) LIKE 'doctor%'
    )
"""

ACCEPTED_CONDITION = """
    LOWER(TRIM(status)) LIKE 'accept%'
"""

FALL_2026_CONDITION = """
    LOWER(TRIM(term)) = 'fall 2026'
"""


# ---------------------------------------------------------
# Question 8
# Count accepted Fall 2026 Computer Science PhD applicants
# at Georgetown, MIT, Stanford, or Carnegie Mellon using
# the original downloaded fields.
# ---------------------------------------------------------


def question_8(connection):
    """Count accepted Fall 2026 CS PhD applicants using original fields."""

    sql = f"""
        SELECT COUNT(*)
        FROM applicants AS a
        JOIN applicant_original_universities AS u
          ON a.p_id = u.p_id
        WHERE LOWER(TRIM(a.term)) = 'fall 2026'
          AND LOWER(TRIM(a.status)) LIKE 'accept%'
          AND (
              LOWER(TRIM(a.degree)) IN (
                  'phd', 'ph.d.', 'ph.d',
                  'doctorate', 'doctoral'
              )
              OR LOWER(TRIM(a.degree)) LIKE 'doctor%'
          )
          AND (
              a.program ~* 'computer[[:space:]]*science'
              OR a.program ~* '(^|[^[:alnum:]])cs([^[:alnum:]]|$)'
          )
          AND {ORIGINAL_UNIVERSITY_CONDITION};
    """

    count = fetch_one(connection, sql)[0]

    print(f"Original-field count (Question 8): {count:,}")

    return count


# ---------------------------------------------------------
# Question 9
# Repeat Question 8 using the LLM-generated program and
# university fields. Report both counts and their difference.
# ---------------------------------------------------------

def question_9(connection, original_count):
    """Print the LLM-field count and difference from Question 8."""
    sql = f"""
        SELECT COUNT(*)
        FROM applicants
        WHERE {FALL_2026_CONDITION}
          AND {ACCEPTED_CONDITION}
          AND {PHD_CONDITION}
          AND {LLM_CS_CONDITION}
          AND {LLM_UNIVERSITY_CONDITION};
    """

    llm_count = fetch_one(connection, sql)[0]

    difference = llm_count - original_count

    print(f"LLM-field count (Question 9): {llm_count:,}")
    print(f"Difference (Question 9 minus Question 8): {difference:+,}")


# ---------------------------------------------------------
# Original Question 1
# Compare Fall 2026 acceptance percentages for American
# and International applicants.
# ---------------------------------------------------------

def original_question_1(connection):
    """Print Fall 2026 acceptance rates by applicant nationality group."""
    sql = """
        SELECT
            TRIM(us_or_international) AS nationality,
            COUNT(*) AS applicant_count,
            COUNT(*) FILTER (
                WHERE LOWER(TRIM(status)) LIKE 'accept%'
            ) AS accepted_count,
            100.0 * COUNT(*) FILTER (
                WHERE LOWER(TRIM(status)) LIKE 'accept%'
            ) / NULLIF(COUNT(*), 0) AS acceptance_percentage
        FROM applicants
        WHERE LOWER(TRIM(term)) = 'fall 2026'
          AND LOWER(TRIM(us_or_international))
              IN ('american', 'international')
        GROUP BY TRIM(us_or_international)
        ORDER BY nationality;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        results = cursor.fetchall()

    print(
        "Among Fall 2026 American and International applicants, "
        "what percentage of each group received an acceptance?"
    )

    for nationality, applicant_count, accepted_count, percentage in results:
        print(
            f"{nationality}: "
            f"{accepted_count:,} accepted out of "
            f"{applicant_count:,} applicants "
            f"({format_percentage(percentage)})"
        )


# ---------------------------------------------------------
# Original Question 2
# Identify the five universities with the most Fall 2026
# applicant entries using original university names.
# ---------------------------------------------------------

def original_question_2(connection):
    """Print the five universities with the most Fall 2026 applicants."""
    sql = """
        SELECT
            TRIM(u.university) AS university,
            COUNT(*) AS applicant_count
        FROM applicants AS a
        JOIN applicant_original_universities AS u
          ON a.p_id = u.p_id
        WHERE LOWER(TRIM(a.term)) = 'fall 2026'
          AND NULLIF(TRIM(u.university), '') IS NOT NULL
        GROUP BY TRIM(u.university)
        ORDER BY applicant_count DESC, university ASC
        LIMIT 5;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        results = cursor.fetchall()

    print(
        "Which five universities have the most Fall 2026 "
        "applicant entries?"
    )

    for rank, (university, applicant_count) in enumerate(results, start=1):
        print(f"{rank}. {university}: {applicant_count:,}")


def main():
    """Run all eleven SQL analysis questions."""

    with connect_to_database() as connection:

        print("QUESTION 1")
        question_1(connection)

        print("\nQUESTION 2")
        question_2(connection)

        print("\nQUESTION 3")
        question_3(connection)

        print("\nQUESTION 4")
        question_4(connection)

        print("\nQUESTION 5")
        question_5(connection)

        print("\nQUESTION 6")
        question_6(connection)

        print("\nQUESTION 7")
        question_7(connection)

        print("\nQUESTION 8")
        original_count = question_8(connection)

        print("\nQUESTION 9")
        question_9(connection, original_count)

        print("\nORIGINAL QUESTION 1")
        original_question_1(connection)

        print("\nORIGINAL QUESTION 2")
        original_question_2(connection)


if __name__ == "__main__":
    main()
