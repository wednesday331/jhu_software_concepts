"""End-to-end integration tests for the Module 4 Flask application."""

import pytest

import app as app_module
import runpy
import sys
from types import ModuleType

from flask import Flask



class SynchronousThread:
    """
    Replacement for threading.Thread used during tests.

    Calling start() immediately executes the target function, which
    makes the background workflow deterministic for integration tests.
    """

    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon

    def start(self):
        """Run the target immediately instead of creating a real thread."""
        self.target()


@pytest.mark.integration
def test_end_to_end_analysis_page_flow(client):
    """A user should be able to open and refresh the Analysis page."""

    response = client.get(
        "/",
        follow_redirects=True,
    )

    assert response.status_code == 200

    page = response.get_data(as_text=True)

    assert "GradCafe Data Analysis" in page
    assert "Answer:" in page
    assert "39.28%" in page

    response = client.post("/update-analysis")

    assert response.status_code == 200

    updated_page = response.get_data(as_text=True)

    assert "GradCafe Data Analysis" in updated_page
    assert "Answer:" in updated_page


@pytest.mark.integration
def test_end_to_end_pull_data_success(
    app,
    client,
    monkeypatch,
):
    """A successful Pull Data request should complete the worker."""

    monkeypatch.setattr(
        app_module,
        "Thread",
        SynchronousThread,
    )

    response = client.post("/pull-data")

    assert response.status_code == 202

    response_data = response.get_json()

    assert response_data["ok"] is True
    assert response_data["busy"] is False

    status_response = client.get("/pull-status")

    assert status_response.status_code == 200

    status = status_response.get_json()

    assert status["running"] is False
    assert status["message"] == "Fake pull completed."


@pytest.mark.integration
def test_end_to_end_pull_data_failure(
    app,
    client,
    monkeypatch,
):
    """A failed background workflow should report the error cleanly."""

    def failing_runner():
        raise RuntimeError("Simulated data pull failure")

    app.config["PULL_RUNNER"] = failing_runner

    monkeypatch.setattr(
        app_module,
        "Thread",
        SynchronousThread,
    )

    response = client.post("/pull-data")

    assert response.status_code == 202

    status_response = client.get("/pull-status")

    assert status_response.status_code == 200

    status = status_response.get_json()

    assert status["running"] is False

    assert (
        status["message"]
        == "Pull Data stopped: Simulated data pull failure"
    )


@pytest.mark.integration
def test_analysis_available_after_pull_completion(
    app,
    client,
    monkeypatch,
):
    """The Analysis page should remain available after Pull Data finishes."""

    monkeypatch.setattr(
        app_module,
        "Thread",
        SynchronousThread,
    )

    pull_response = client.post("/pull-data")

    assert pull_response.status_code == 202

    analysis_response = client.get("/analysis")

    assert analysis_response.status_code == 200

    page = analysis_response.get_data(as_text=True)

    assert "GradCafe Data Analysis" in page
    assert "Answer:" in page

@pytest.mark.integration
def test_pull_data_uses_default_runner_when_not_injected(
    monkeypatch,
):
    """The app should lazily import the real Pull Data runner when needed."""

    fake_workflow = ModuleType(
        "pull_data_workflow"
    )

    calls = []

    def fake_run_pull_data():
        calls.append(True)
        return "Default runner completed."

    fake_workflow.run_pull_data = (
        fake_run_pull_data
    )

    monkeypatch.setitem(
        sys.modules,
        "pull_data_workflow",
        fake_workflow,
    )

    test_app = app_module.create_app(
        config={
            "TESTING": True,
        },
        session_factory=lambda: None,
        analysis_query=lambda session: None,
        pull_runner=None,
    )

    class SynchronousThread:
        """Execute the background target immediately."""

        def __init__(
            self,
            target,
            daemon,
        ):
            self.target = target
            self.daemon = daemon

        def start(self):
            self.target()

    monkeypatch.setattr(
        app_module,
        "Thread",
        SynchronousThread,
    )

    client = test_app.test_client()

    response = client.post(
        "/pull-data"
    )

    assert response.status_code == 202

    assert calls == [True]

    status = client.get(
        "/pull-status"
    ).get_json()

    assert status["running"] is False

    assert (
        status["message"]
        == "Default runner completed."
    )


@pytest.mark.integration
def test_app_main_entrypoint(
    monkeypatch,
):
    """Executing app.py directly should call Flask.run()."""

    calls = []

    def fake_run(
        self,
        *args,
        **kwargs,
    ):
        calls.append(
            kwargs
        )

    monkeypatch.setattr(
        Flask,
        "run",
        fake_run,
    )

    runpy.run_path(
        app_module.__file__,
        run_name="__main__",
    )

    assert len(calls) == 1

    assert (
        calls[0]["debug"]
        is True
    )

    assert (
        calls[0]["use_reloader"]
        is False
    )