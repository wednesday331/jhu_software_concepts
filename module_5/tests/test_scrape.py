"""Tests for GradCafe HTML parsing and saved-page scraping."""

from pathlib import Path

import runpy
import urllib.robotparser
import pytest
from bs4 import BeautifulSoup

import scrape


@pytest.mark.analysis
def test_robots_allows(monkeypatch):
    """robots_allows should configure and query RobotFileParser."""

    calls = {}

    class FakeRobotParser:
        def set_url(self, url):
            calls["url"] = url

        def read(self):
            calls["read"] = True

        def can_fetch(self, agent, url):
            calls["agent"] = agent
            calls["target"] = url
            return True

    monkeypatch.setattr(
        scrape,
        "RobotFileParser",
        FakeRobotParser,
    )

    result = scrape.robots_allows(
        "https://www.thegradcafe.com/survey/"
    )

    assert result is True
    assert calls["url"] == scrape.ROBOTS_URL
    assert calls["read"] is True
    assert calls["agent"] == "*"


@pytest.mark.analysis
def test_save_and_load_data(tmp_path):
    """Saved applicant JSON should load back unchanged."""

    path = tmp_path / "applicants.json"

    data = [
        {
            "program": "Computer Science",
            "url": "https://example.com/result/1",
        }
    ]

    scrape.save_data(data, path)

    assert scrape.load_data(path) == data


@pytest.mark.analysis
def test_load_data_returns_empty_when_file_missing(tmp_path):
    """A missing applicant file should return an empty list."""

    missing = tmp_path / "missing.json"

    assert scrape.load_data(missing) == []


@pytest.mark.analysis
def test_get_result_links_returns_unique_result_urls():
    """Only unique /result/ links should be collected."""

    html = """
    <html>
        <body>
            <a href="/result/100">One</a>
            <a href="/result/100">Duplicate</a>
            <a href="/result/200">Two</a>
            <a href="/survey/">Ignore</a>
        </body>
    </html>
    """

    result = scrape._get_result_links(html)

    assert result == [
        "https://www.thegradcafe.com/result/100",
        "https://www.thegradcafe.com/result/200",
    ]


@pytest.mark.analysis
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        ("Not provided", ""),
        ("N/A", ""),
        ("None", ""),
        ("  3.90  ", "3.90"),
    ],
)
def test_normalize_missing(value, expected):
    """Known missing labels should normalize to an empty string."""

    assert scrape._normalize_missing(value) == expected


@pytest.mark.analysis
def test_parse_survey_row_without_result_link():
    """Rows without a result URL should be ignored."""

    soup = BeautifulSoup(
        "<tr><td>School</td></tr>",
        "html.parser",
    )

    assert scrape._parse_survey_row(soup.tr) is None


@pytest.mark.analysis
def test_parse_survey_row_with_too_few_cells():
    """Rows with fewer than four cells should be ignored."""

    html = """
    <tr>
        <td>
            <a href="/result/1">School</a>
        </td>
        <td>Program</td>
    </tr>
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    assert scrape._parse_survey_row(soup.tr) is None


@pytest.mark.analysis
def test_parse_survey_row_with_extra_row():
    """A valid survey row should include its following detail row."""

    html = """
    <table>
        <tr>
            <td>
                <a href="/result/123">Johns Hopkins University</a>
            </td>
            <td>Computer Science</td>
            <td>Sep 12</td>
            <td>Accepted on Sep 11</td>
        </tr>
        <tr>
            <td colspan="4">
                Fall 2026 International GPA 3.90
                GRE 168 GRE V 162 GRE AW 4.5 PhD
            </td>
        </tr>
    </table>
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    record = scrape._parse_survey_row(
        soup.find("tr")
    )

    assert record["program"] == "Computer Science"
    assert record["university"] == "Johns Hopkins University"
    assert record["date_added"] == "Sep 12"

    assert (
        record["url"]
        == "https://www.thegradcafe.com/result/123"
    )

    assert "Fall 2026" in record["raw_text"]


@pytest.mark.analysis
def test_parse_survey_row_without_extra_row():
    """A valid standalone row should still parse."""

    html = """
    <tr>
        <td>
            <a href="/result/5">Example University</a>
        </td>
        <td>Mathematics</td>
        <td>Jan 01</td>
        <td>Interview</td>
    </tr>
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    record = scrape._parse_survey_row(
        soup.tr
    )

    assert record["program"] == "Mathematics"
    assert record["status"] == "Interview"


@pytest.mark.analysis
def test_extract_extra_fields_accepted_international_phd():
    """Accepted international PhD details should be extracted."""

    record = {
        "status": "Accepted on Sep 11",
        "raw_text": (
            "Fall 2026 International "
            "GPA 3.90 GRE 168 "
            "GRE V 162 GRE AW 4.5 PhD"
        ),
        "decision_date": "",
        "acceptance_date": "",
        "rejection_date": "",
        "term": "",
        "student_type": "",
        "gpa": "",
        "gre": "",
        "gre_v": "",
        "gre_aw": "",
        "degree": "",
    }

    result = scrape._extract_extra_fields(record)

    assert result["status"] == "Accepted"
    assert result["decision_date"] == "Sep 11"
    assert result["acceptance_date"] == "Sep 11"
    assert result["term"] == "Fall 2026"
    assert result["student_type"] == "International"
    assert result["gpa"] == "3.90"
    assert result["gre"] == "168"
    assert result["gre_v"] == "162"
    assert result["gre_aw"] == "4.5"
    assert result["degree"] == "PhD"


@pytest.mark.analysis
def test_extract_extra_fields_rejected_american_masters():
    """Rejected American master's details should be extracted."""

    record = {
        "status": "Rejected on Apr 23",
        "raw_text": "Spring 2026 American Masters",
        "decision_date": "",
        "acceptance_date": "",
        "rejection_date": "",
        "term": "",
        "student_type": "",
        "gpa": "",
        "gre": "",
        "gre_v": "",
        "gre_aw": "",
        "degree": "",
    }

    result = scrape._extract_extra_fields(record)

    assert result["status"] == "Rejected"
    assert result["rejection_date"] == "Apr 23"
    assert result["student_type"] == "American"
    assert result["degree"] == "Masters"


@pytest.mark.analysis
def test_extract_extra_fields_other_mfa():
    """Other applicant type and MFA should be recognized."""

    record = {
        "status": "Wait listed on Sep 10",
        "raw_text": "Summer 2026 Other MFA",
        "decision_date": "",
        "acceptance_date": "",
        "rejection_date": "",
        "term": "",
        "student_type": "",
        "gpa": "",
        "gre": "",
        "gre_v": "",
        "gre_aw": "",
        "degree": "",
    }

    result = scrape._extract_extra_fields(record)

    assert result["status"] == "Wait listed"
    assert result["student_type"] == "Other"
    assert result["degree"] == "Masters"


@pytest.mark.analysis
def test_extract_extra_fields_interview_without_date():
    """Interview status without a date should remain valid."""

    record = {
        "status": "Interview",
        "raw_text": "No additional values",
        "decision_date": "",
        "acceptance_date": "",
        "rejection_date": "",
        "term": "",
        "student_type": "",
        "gpa": "",
        "gre": "",
        "gre_v": "",
        "gre_aw": "",
        "degree": "",
    }

    result = scrape._extract_extra_fields(record)

    assert result["status"] == "Interview"
    assert result["decision_date"] == ""
    assert result["degree"] == ""


@pytest.mark.analysis
def test_parse_survey_page():
    """parse_survey_page should skip invalid rows and parse valid ones."""

    html = """
    <table>
        <tr>
            <th>Header</th>
        </tr>

        <tr>
            <td>
                <a href="/result/77">Example University</a>
            </td>
            <td>Computer Science</td>
            <td>Sep 20</td>
            <td>Accepted on Sep 19</td>
        </tr>

        <tr>
            <td colspan="4">
                Fall 2026 International PhD
            </td>
        </tr>
    </table>
    """

    records = scrape.parse_survey_page(
        html
    )

    assert len(records) == 1
    assert records[0]["status"] == "Accepted"
    assert records[0]["term"] == "Fall 2026"


@pytest.mark.analysis
def test_parse_entry_accepted():
    """An individual accepted result page should parse all fields."""

    html = """
    <dl>
        <dt>Program</dt>
        <dd>Computer Science</dd>

        <dt>Institution</dt>
        <dd>Johns Hopkins University</dd>

        <dt>Decision</dt>
        <dd>Accepted</dd>

        <dt>Notification</dt>
        <dd>Sep 11</dd>

        <dt>Notes</dt>
        <dd>Test note</dd>

        <dt>Degree Type</dt>
        <dd>PhD</dd>

        <dt>Degree's Country of Origin</dt>
        <dd>American</dd>

        <dt>Undergrad GPA</dt>
        <dd>3.90</dd>

        <dt>GRE General</dt>
        <dd>N/A</dd>

        <dt>GRE Verbal</dt>
        <dd>162</dd>

        <dt>Analytical Writing</dt>
        <dd>4.5</dd>

        <dt>Unused Field</dt>
    </dl>
    """

    record = scrape._parse_entry(
        html,
        "https://example.com/result/1",
    )

    assert record["program"] == "Computer Science"
    assert record["status"] == "Accepted"
    assert record["acceptance_date"] == "Sep 11"
    assert record["rejection_date"] == ""
    assert record["gpa"] == "3.90"
    assert record["gre"] == ""


@pytest.mark.analysis
def test_parse_entry_rejected():
    """Rejected result pages should populate rejection_date."""

    html = """
    <dl>
        <dt>Decision</dt>
        <dd>Rejected</dd>

        <dt>Notification</dt>
        <dd>Apr 23</dd>
    </dl>
    """

    record = scrape._parse_entry(
        html,
        "https://example.com/result/2",
    )

    assert record["status"] == "Rejected"
    assert record["acceptance_date"] == ""
    assert record["rejection_date"] == "Apr 23"


@pytest.mark.analysis
def test_page_sort_key():
    """Saved survey pages should sort numerically."""

    assert (
        scrape._page_sort_key(
            Path("survey_page.html")
        )
        == 1
    )

    assert (
        scrape._page_sort_key(
            Path("survey_page_12.html")
        )
        == 12
    )

    assert (
        scrape._page_sort_key(
            Path("other.html")
        )
        == float("inf")
    )


@pytest.mark.integration
def test_scrape_data_stops_when_robots_disallows(
    monkeypatch,
    capsys,
):
    """scrape_data should stop when robots.txt disallows access."""

    monkeypatch.setattr(
        scrape,
        "robots_allows",
        lambda _url: False,
    )

    scrape.scrape_data()

    output = capsys.readouterr().out

    assert "does not permit scraping" in output


@pytest.mark.integration
def test_scrape_data_stops_when_no_saved_pages(
    tmp_path,
    monkeypatch,
    capsys,
):
    """scrape_data should stop if there are no saved survey pages."""

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        scrape,
        "robots_allows",
        lambda _url: True,
    )

    scrape.scrape_data()

    output = capsys.readouterr().out

    assert "No survey_page*.html files were found." in output


@pytest.mark.integration
def test_scrape_data_adds_only_new_records(
    tmp_path,
    monkeypatch,
):
    """Saved pages should append new URLs while avoiding duplicates."""

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        scrape,
        "robots_allows",
        lambda _url: True,
    )

    Path("survey_page.html").write_text(
        "<html>page one</html>",
        encoding="utf-8",
    )

    Path("survey_page_2.html").write_text(
        "<html>page two</html>",
        encoding="utf-8",
    )

    existing = [
        {
            "url": "https://example.com/result/1",
            "program": "Existing",
        }
    ]

    scrape.save_data(
        existing,
        "applicant_data.json",
    )

    responses = iter(
        [
            [
                {
                    "url": "https://example.com/result/1",
                    "program": "Duplicate",
                },
                {
                    "url": "https://example.com/result/2",
                    "program": "New 2",
                },
            ],
            [
                {
                    "url": "https://example.com/result/3",
                    "program": "New 3",
                }
            ],
        ]
    )

    monkeypatch.setattr(
        scrape,
        "parse_survey_page",
        lambda _html: next(responses),
    )

    scrape.scrape_data()

    saved = scrape.load_data(
        "applicant_data.json"
    )

    assert len(saved) == 3

    urls = {
        record["url"]
        for record in saved
    }

    assert urls == {
        "https://example.com/result/1",
        "https://example.com/result/2",
        "https://example.com/result/3",
    }

@pytest.mark.integration
def test_scrape_main_entrypoint(
    tmp_path,
    monkeypatch,
    capsys,
):
    """Running scrape.py directly should call scrape_data."""

    class FakeRobotParser:
        """Avoid accessing the real robots.txt during the test."""

        def set_url(self, _url):
            pass

        def read(self):
            pass

        def can_fetch(self, _agent, _url):
            return True

    monkeypatch.setattr(
        urllib.robotparser,
        "RobotFileParser",
        FakeRobotParser,
    )

    # Use an empty temporary directory so the workflow
    # exits safely when it finds no saved survey pages.
    monkeypatch.chdir(tmp_path)

    runpy.run_path(
        scrape.__file__,
        run_name="__main__",
    )

    output = capsys.readouterr().out

    assert "No survey_page*.html files were found." in output