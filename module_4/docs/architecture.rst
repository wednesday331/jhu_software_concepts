Architecture
============

Overview
--------

GradCafe Analytics is organized into three primary layers:

* Web application layer
* ETL and data-processing layer
* Database layer


Web Application Layer
---------------------

The Flask application is implemented in ``src/app.py``.

The application uses an application factory named ``create_app()``,
which allows configuration and dependencies to be overridden during
testing.

The web application provides routes for:

* displaying GradCafe analysis results
* refreshing the analysis
* starting the data-pull workflow
* checking data-pull status

The HTML interface uses stable ``data-testid`` selectors so automated
tests can locate important controls reliably.


ETL and Data-Processing Layer
-----------------------------

The ETL workflow retrieves, cleans, standardizes, and loads GradCafe
application data.

Important modules include:

``scrape.py``
    Retrieves and parses GradCafe application records.

``capture_page.py``
    Supports collection of GradCafe source pages.

``clean.py``
    Standardizes university and program values and supports LLM-assisted
    cleaning.

``load_data.py``
    Loads applicant records into the database.

``load_original_universities.py``
    Loads original university information.

``pull_data_workflow.py``
    Coordinates the overall data retrieval and loading workflow.

``query_data.py``
    Performs analytical queries against the stored data.


Database Layer
--------------

The database layer uses PostgreSQL and SQLAlchemy.

``models.py`` defines the SQLAlchemy database models and creates
database engines and sessions.

The application reads its PostgreSQL connection string from the
``DATABASE_URL`` environment variable.

``orm_queries.py`` contains reusable SQLAlchemy queries used to generate
the analytical results displayed by the Flask application.


Dependency Injection
--------------------

Module 4 introduces dependency injection so tests can replace database
sessions, analysis functions, and the data-pull workflow with controlled
test doubles.

This design allows the application to be tested without requiring live
network access or the production GradCafe workflow.