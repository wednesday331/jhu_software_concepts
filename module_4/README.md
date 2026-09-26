# Module 4 - Internet Documentation, Testing, and Continuous Integration

## Overview

This module extends the GradCafe Analytics application from Module 3.

The application collects and processes GradCafe applicant data, stores the
records in PostgreSQL, analyzes them using raw SQL and SQLAlchemy ORM, and
displays the results through a Flask webpage.

Module 4 adds:

- automated testing with Pytest
- 100% source-code coverage
- dependency injection for testability
- deterministic mocks, fakes, fixtures, and test doubles
- stable HTML selectors for automated UI testing
- GitHub Actions continuous integration
- Sphinx-generated documentation
- published documentation through Read the Docs

## Repository

GitHub SSH URL:

```text
git@github.com:wednesday331/jhu_software_concepts.git
```

## Installation

The project uses Python 3.11 and PostgreSQL.

From the repository root:

```powershell
python -m pip install -r .\module_4\requirements.txt
```

The optional local LLM component has additional dependencies under:

```text
module_4/src/llm_hosting/
```

The production LLM is not required for the normal test suite, GitHub Actions,
or Sphinx documentation.

## PostgreSQL Configuration

The PostgreSQL database is named `gradcafe`.

Direct Psycopg scripts such as `load_data.py` use the standard PostgreSQL
environment variables. The Flask and SQLAlchemy components use `DATABASE_URL`.

Example PowerShell configuration:

```powershell
$password = Read-Host "PostgreSQL password" -AsSecureString
$plainPassword = [System.Net.NetworkCredential]::new("", $password).Password
$encodedPassword = [System.Uri]::EscapeDataString($plainPassword)

$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "gradcafe"
$env:PGUSER = "postgres"
$env:PGPASSWORD = $plainPassword

$env:DATABASE_URL = "postgresql+psycopg://postgres:$encodedPassword@localhost:5432/gradcafe"
```

Do not store the real PostgreSQL password in source code or commit it to GitHub.

## Loading the Database

From the repository root:

```powershell
cd .\module_4\src
python load_data.py
python load_original_universities.py
```

The current dataset contains 30,384 applicant records.

## Running the Flask Application

Make sure PostgreSQL is running and the required environment variables are set.

From `module_4/src`:

```powershell
python app.py
```

The webpage provides:

- **Update Analysis** - refreshes the displayed analysis
- **Pull Data** - starts the GradCafe data collection workflow

The Flask application uses a `create_app()` application factory so tests can
override database sessions, analysis queries, and the Pull Data workflow.

Stable selectors include:

```text
data-testid="pull-data-btn"
data-testid="update-analysis-btn"
```

## Automated Testing

From the repository root:

```powershell
python -m pytest .\module_4\tests -v
```

The completed test suite reports:

```text
163 passed
979 statements
0 missed
100% coverage
```

The rubric marker command also passes with 100% coverage:

```powershell
python -m pytest .\module_4\tests -m "web or buttons or analysis or db or integration"
```

Coverage configuration is defined in:

```text
module_4/pytest.ini
```

Coverage proof is stored in:

```text
module_4/coverage_summary.txt
```

## GitHub Actions

Continuous integration is configured in:

```text
.github/workflows/tests.yml
```

The workflow starts PostgreSQL, configures the test database environment,
installs dependencies, and runs the complete Pytest suite with the 100%
coverage requirement.

Proof of the successful GitHub Actions run is included in:

```text
module_4/actions_success.png
```

## Sphinx Documentation

The Sphinx source files are located in:

```text
module_4/docs/
```

The documentation includes:

- setup and environment-variable instructions
- architecture documentation
- web, ETL, and database layers
- API/autodoc documentation
- testing guidance
- Pytest markers
- stable selectors
- fixtures and test doubles

Build the documentation from the repository root with:

```powershell
python -m sphinx -W -b html .\module_4\docs .\module_4\docs\_build\html
```

Generated HTML is stored in:

```text
module_4/docs/_build/html/
```

## Published Documentation

The Sphinx documentation is published through Read the Docs.

Published documentation:

https://wednesday331-jhu-software-concepts.readthedocs.io/en/latest/

Read the Docs configuration is defined in:

```text
.readthedocs.yaml
```

## Main Deliverables

- GitHub repository SSH URL
- `module_4/README.md`
- `module_4/requirements.txt`
- Sphinx-generated HTML under `module_4/docs/_build/html`
- `module_4/coverage_summary.txt`
- `module_4/actions_success.png`
- `.github/workflows/tests.yml`
- published Read the Docs documentation
- all required tests under `module_4/tests`
