
"""Flask analysis webpage for Module 3."""

from threading import Lock, Thread

from flask import Flask, jsonify, redirect, render_template, url_for

from models import get_session
from orm_queries import get_analysis_results
from pull_data_workflow import run_pull_data


app = Flask(__name__)

# Tracks the data-collection process for this local Flask app.
pull_lock = Lock()
pull_status = {
    "running": False,
    "message": "No data collection is currently running.",
}


def pull_data_worker():
    """Run the data-collection workflow in the background."""

    try:
        with pull_lock:
            pull_status["message"] = (
                "Retrieving new GradCafe records. "
                "Update Analysis remains available."
            )

        # Capture, clean, and import records into PostgreSQL.
        result_message = run_pull_data()

        with pull_lock:
            pull_status["message"] = result_message

    except Exception as exc:
        with pull_lock:
            pull_status["message"] = f"Pull Data stopped: {exc}"

    finally:
        with pull_lock:
            pull_status["running"] = False

@app.get("/")
def analysis():
    """Query PostgreSQL and display the current analysis results."""

    with get_session() as session:
        results = get_analysis_results(session)

    with pull_lock:
        status = pull_status.copy()

    return render_template(
        "analysis.html",
        results=results,
        pull_status=status,
    )


@app.post("/update-analysis")
def update_analysis():
    """Refresh the analysis without starting a scraping process."""

    return redirect(url_for("analysis"))


@app.post("/pull-data")
def pull_data():
    """Start one collection job at a time."""

    with pull_lock:
        if pull_status["running"]:
            pull_status["message"] = (
                "Data collection is already running. "
                "Please wait for it to finish."
            )
            return redirect(url_for("analysis"))

        pull_status["running"] = True
        pull_status["message"] = "Starting data collection..."

    Thread(target=pull_data_worker, daemon=True).start()

    return redirect(url_for("analysis"))

@app.get("/pull-status")
def get_pull_status():
    """Return the latest background-job status."""
    with pull_lock:
        return jsonify(pull_status.copy())


if __name__ == "__main__":
    # Avoid starting multiple local worker processes during development.
    app.run(debug=True, use_reloader=False)