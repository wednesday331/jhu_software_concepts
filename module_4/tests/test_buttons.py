"""Tests for Update Analysis and Pull Data behavior."""

import pytest

import app as app_module


@pytest.mark.buttons
def test_update_analysis_returns_200(client):
    """Update Analysis should render the Analysis page."""

    response = client.post("/update-analysis")

    assert response.status_code == 200
    assert b"Answer:" in response.data


@pytest.mark.buttons
def test_update_analysis_returns_409_when_busy(app, client):
    """Update Analysis should report busy while a pull is running."""

    app.config["PULL_STATUS"]["running"] = True

    response = client.post("/update-analysis")

    assert response.status_code == 409

    data = response.get_json()

    assert data["ok"] is False
    assert data["busy"] is True


@pytest.mark.buttons
def test_pull_data_starts_background_job(app, client, monkeypatch):
    """Pull Data should start one background job and return HTTP 202."""

    class FakeThread:
        """Prevent a real background thread from starting during the test."""

        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            """Do not execute the background worker."""
            return None

    monkeypatch.setattr(
        app_module,
        "Thread",
        FakeThread,
    )

    response = client.post("/pull-data")

    assert response.status_code == 202

    data = response.get_json()

    assert data["ok"] is True
    assert data["busy"] is False

    assert app.config["PULL_STATUS"]["running"] is True
    assert (
        app.config["PULL_STATUS"]["message"]
        == "Starting data collection..."
    )


@pytest.mark.buttons
def test_pull_data_returns_409_when_already_running(app, client):
    """A second Pull Data request should be rejected while busy."""

    app.config["PULL_STATUS"]["running"] = True

    response = client.post("/pull-data")

    assert response.status_code == 409

    data = response.get_json()

    assert data["ok"] is False
    assert data["busy"] is True

    assert (
        app.config["PULL_STATUS"]["message"]
        == "Data collection is already running. "
        "Please wait for it to finish."
    )


@pytest.mark.buttons
def test_pull_status_reports_current_state(app, client):
    """The status endpoint should report the current pull state."""

    app.config["PULL_STATUS"]["running"] = True
    app.config["PULL_STATUS"]["message"] = "Testing status."

    response = client.get("/pull-status")

    assert response.status_code == 200

    data = response.get_json()

    assert data["running"] is True
    assert data["message"] == "Testing status."