"""Tests for Flask app creation and Analysis page rendering."""

import pytest
from bs4 import BeautifulSoup

from app import create_app


@pytest.mark.web
def test_create_app_has_required_routes():
    """The Flask factory should create all required routes."""

    test_app = create_app(
        config={"TESTING": True},
        session_factory=lambda: None,
        analysis_query=lambda session: None,
        pull_runner=lambda: "done",
    )

    routes = {rule.rule for rule in test_app.url_map.iter_rules()}

    assert "/" in routes
    assert "/analysis" in routes
    assert "/pull-data" in routes
    assert "/update-analysis" in routes
    assert "/pull-status" in routes


@pytest.mark.web
def test_root_redirects_to_analysis(client):
    """GET / should redirect users to the Analysis page."""

    response = client.get("/")

    assert response.status_code in (301, 302, 307, 308)
    assert response.headers["Location"].endswith("/analysis")


@pytest.mark.web
def test_analysis_page_loads(client):
    """GET /analysis should render successfully."""

    response = client.get("/analysis")

    assert response.status_code == 200


@pytest.mark.web
def test_analysis_page_contains_required_components(client):
    """The Analysis page should contain required text and buttons."""

    response = client.get("/analysis")

    assert response.status_code == 200

    soup = BeautifulSoup(
        response.get_data(as_text=True),
        "html.parser",
    )

    page_text = soup.get_text(" ", strip=True)

    assert "Analysis" in page_text
    assert "Answer:" in page_text

    pull_button = soup.find(
        "button",
        attrs={"data-testid": "pull-data-btn"},
    )

    update_button = soup.find(
        "button",
        attrs={"data-testid": "update-analysis-btn"},
    )

    assert pull_button is not None
    assert update_button is not None

    assert "Pull Data" in pull_button.get_text(strip=True)
    assert "Update Analysis" in update_button.get_text(strip=True)