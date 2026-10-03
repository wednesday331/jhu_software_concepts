"""Tests for formatting of values on the Analysis page."""

import pytest


@pytest.mark.analysis
def test_percentage_values_use_two_decimal_places(client):
    """Percentages should be rendered with exactly two decimal places."""

    response = client.get("/analysis")

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    # 39.276 rounds to 39.28.
    assert "39.28%" in page

    # 47.956 rounds to 47.96.
    assert "47.96%" in page

    # Whole-number percentages must still show two decimal places.
    assert "60.00%" in page
    assert "50.00%" in page


@pytest.mark.analysis
def test_percentage_values_are_not_unrounded(client):
    """Raw percentage values should not appear in rendered HTML."""

    response = client.get("/analysis")

    page = response.get_data(as_text=True)

    assert "39.276%" not in page
    assert "47.956%" not in page


@pytest.mark.analysis
def test_average_values_use_two_decimal_places(client):
    """Average GPA and GRE values should use two decimal places."""

    response = client.get("/analysis")

    page = response.get_data(as_text=True)

    assert "3.77" in page
    assert "165.88" in page
    assert "160.80" in page
    assert "4.36" in page
    assert "3.79" in page
    assert "3.78" in page


@pytest.mark.analysis
def test_required_answer_labels_are_visible(client):
    """The rendered Analysis page should visibly label answers."""

    response = client.get("/analysis")

    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Answer:" in page


@pytest.mark.analysis
def test_counts_are_formatted_for_display(client):
    """Integer counts should render in the Analysis output."""

    response = client.get("/analysis")

    page = response.get_data(as_text=True)

    assert "100 entries" in page
    assert "8 entries" in page
    assert "28 entries" in page