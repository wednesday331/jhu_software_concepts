Testing Guide
=============

Running the Test Suite
----------------------

From the repository root, run:

.. code-block:: console

   python -m pytest ./module_4/tests -v

The project's ``pytest.ini`` configures coverage measurement and requires
100 percent coverage for the Python source code under ``module_4/src``.


Test Markers
------------

The test suite uses Pytest markers to organize tests by purpose.

Available markers include:

``web``
    Flask page and route tests.

``buttons``
    Tests for Pull Data and Update Analysis behavior.

``analysis``
    Tests for analysis values, formatting, and rounding.

``db``
    Database schema, insert, and query tests.

``integration``
    End-to-end and multi-component tests.


Stable UI Selectors
-------------------

The Flask page provides stable selectors for important controls.

The Pull Data button uses:

.. code-block:: text

   data-testid="pull-data-btn"

The Update Analysis button uses:

.. code-block:: text

   data-testid="update-analysis-btn"

These selectors allow tests to locate controls without depending on
presentation or CSS styling.


Fixtures
--------

Shared Pytest fixtures are defined in ``tests/conftest.py``.

Fixtures provide reusable Flask application instances, test clients,
fake sessions, and predictable analysis results.


Test Doubles and Dependency Injection
-------------------------------------

Tests replace external dependencies with deterministic test doubles.

Examples include:

* fake database sessions
* fake analysis-query functions
* fake data-pull runners
* synchronous thread replacements
* mocked HTTP and scraper behavior

This keeps the test suite fast and avoids reliance on live external
services.


Coverage
--------

The project requires 100 percent source coverage.

The committed coverage evidence is available in:

.. code-block:: text

   module_4/coverage_summary.txt

The test suite currently covers the application, scraper, data loaders,
database models, ORM queries, data workflow, page capture, cleaning, and
analysis modules.


Continuous Integration
----------------------

GitHub Actions automatically runs the Module 4 test suite.

The workflow is located at:

.. code-block:: text

   .github/workflows/tests.yml

The workflow starts PostgreSQL, configures the test database environment,
installs the required test dependencies, and runs Pytest with the project's
100 percent coverage requirement.