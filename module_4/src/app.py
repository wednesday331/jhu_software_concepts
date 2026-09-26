"""Flask analysis webpage for Module 4."""

from threading import Lock, Thread

from flask import Flask, jsonify, redirect, render_template, url_for

from models import get_session
from orm_queries import get_analysis_results


def create_app(
    config=None,
    session_factory=None,
    analysis_query=None,
    pull_runner=None,
):
    """
    Create and configure the Grad Cafe Flask application.

    Dependencies may be injected during testing so tests do not need
    live scraping, LLM calls, or a production database.
    """

    app = Flask(__name__)

    if config:
        app.config.update(config)

    # Dependency injection points used by the pytest suite.
    app.config["SESSION_FACTORY"] = session_factory or get_session
    app.config["ANALYSIS_QUERY"] = analysis_query or get_analysis_results
    app.config["PULL_RUNNER"] = pull_runner

    # Per-application busy state.
    pull_lock = Lock()
    pull_status = {
        "running": False,
        "message": "No data collection is currently running.",
    }

    # Expose state for deterministic tests.
    app.config["PULL_LOCK"] = pull_lock
    app.config["PULL_STATUS"] = pull_status

    def pull_data_worker():
        """Run the data-collection workflow in the background."""

        try:
            runner = app.config["PULL_RUNNER"]

            # Import the real workflow only when it is actually needed.
            # Tests can inject a fake runner and avoid network/LLM calls.
            if runner is None:
                from pull_data_workflow import run_pull_data

                runner = run_pull_data

            with pull_lock:
                pull_status["message"] = (
                    "Retrieving new GradCafe records. "
                    "Update Analysis remains available."
                )

            result_message = runner()

            with pull_lock:
                pull_status["message"] = result_message

        except Exception as exc:
            with pull_lock:
                pull_status["message"] = f"Pull Data stopped: {exc}"

        finally:
            with pull_lock:
                pull_status["running"] = False

    @app.get("/")
    def home():
        """Redirect the root URL to the Analysis page."""

        return redirect(url_for("analysis"))

    @app.get("/analysis")
    def analysis():
        """Query the database and display current analysis results."""

        session_factory_func = app.config["SESSION_FACTORY"]
        analysis_query_func = app.config["ANALYSIS_QUERY"]

        with session_factory_func() as session:
            results = analysis_query_func(session)

        with pull_lock:
            status = pull_status.copy()

        return render_template(
            "analysis.html",
            results=results,
            pull_status=status,
        )

    @app.post("/update-analysis")
    def update_analysis():
        """Refresh analysis when no data pull is currently running."""

        with pull_lock:
            if pull_status["running"]:
                return jsonify(
                    {
                        "ok": False,
                        "busy": True,
                    }
                ), 409

        # Rendering the Analysis page directly gives the required HTTP 200.
        return analysis()

    @app.post("/pull-data")
    def pull_data():
        """Start one data-collection job at a time."""

        with pull_lock:
            if pull_status["running"]:
                pull_status["message"] = (
                    "Data collection is already running. "
                    "Please wait for it to finish."
                )

                return jsonify(
                    {
                        "ok": False,
                        "busy": True,
                    }
                ), 409

            pull_status["running"] = True
            pull_status["message"] = "Starting data collection..."

        Thread(
            target=pull_data_worker,
            daemon=True,
        ).start()

        return jsonify(
            {
                "ok": True,
                "busy": False,
            }
        ), 202

    @app.get("/pull-status")
    def get_pull_status():
        """Return the latest background-job status."""

        with pull_lock:
            return jsonify(pull_status.copy())

    return app


# Default application used when running locally.
app = create_app()


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)