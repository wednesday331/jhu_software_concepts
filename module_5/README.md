# Module 5 - Software Security, Dependency Analysis, and Packaging

## Overview

This module extends the GradCafe Analytics application developed in the
previous modules.

The application collects and cleans GradCafe applicant data, stores the
records in PostgreSQL, analyzes them using raw SQL and SQLAlchemy ORM, and
displays the results through a Flask web application.

Module 5 adds:

- Pylint static analysis with a 10.00/10 project score
- SQL injection defenses and parameterized database access
- bounded SQL query result limits
- tests for malicious SQL input
- PostgreSQL least-privilege database access
- environment-based database credentials
- `.env.example` configuration documentation
- pydeps and Graphviz dependency analysis
- `dependency.svg`
- reproducible installation with pip and uv
- setuptools project configuration through `setup.py`

The project retains the automated testing, 100% coverage, Flask application,
Sphinx documentation, and continuous integration work from Module 4.

## Repository

GitHub SSH URL:

```text
git@github.com:wednesday331/jhu_software_concepts.git
```

## Requirements

The project uses:

- Python 3.11
- PostgreSQL
- Graphviz
- Python packages listed in `requirements.txt`

Graphviz is a system dependency rather than a Python package.

On Windows it can be installed with:

```powershell
winget install --id Graphviz.Graphviz -e
```

Verify the installation with:

```powershell
dot -V
```

## Fresh Installation with pip

From `module_5`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

Verify installed dependencies:

```powershell
python -m pip check
```

## Fresh Installation with uv

If uv is not already installed:

```powershell
python -m pip install uv
```

Create and activate a Python 3.11 environment:

```powershell
uv venv .venv --python 3.11
.\.venv\Scripts\Activate.ps1
```

Install the requirements and project:

```powershell
uv pip install -r requirements.txt
uv pip install -e .
```

## PostgreSQL Configuration

The PostgreSQL database is named:

```text
gradcafe
```

The application uses a dedicated least-privilege PostgreSQL role:

```text
gradcafe_app
```

The application role is not a PostgreSQL superuser and cannot create
databases, create roles, create schema objects, replicate, bypass row-level
security, or delete application records.

For the `applicants` table, the application account has only:

```text
SELECT
INSERT
```

For `applicant_original_universities`, the application account has:

```text
SELECT
INSERT
UPDATE
```

`UPDATE` is required on the supplementary university table because the loader
uses PostgreSQL `ON CONFLICT ... DO UPDATE`.

The application account does not have `DELETE` permission on either table.

## Environment Variables

Database credentials are not stored in the Python source code.

The file:

```text
.env.example
```

documents the required variables using placeholder values only.

Direct Psycopg scripts use:

```text
PGHOST
PGPORT
PGDATABASE
PGUSER
PGPASSWORD
```

SQLAlchemy uses:

```text
DATABASE_URL
```

Example PowerShell configuration:

```powershell
$password = Read-Host "gradcafe_app password" -AsSecureString
$plainPassword = [System.Net.NetworkCredential]::new(
    "",
    $password
).Password
$encodedPassword = [System.Uri]::EscapeDataString($plainPassword)

$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "gradcafe"
$env:PGUSER = "gradcafe_app"
$env:PGPASSWORD = $plainPassword

$env:DATABASE_URL = (
    "postgresql+psycopg://gradcafe_app:" +
    "$encodedPassword@localhost:5432/gradcafe"
)
```

Do not store a real database password in `.env.example`, source code, or
GitHub.

A local `.env` file is excluded by `.gitignore`.

## Database Loading

The database schema must be provisioned before the application loader runs.

The runtime application account intentionally does not have permission to
create or alter the PostgreSQL schema.

From `module_5`:

```powershell
python .\src\load_data.py
python .\src\load_original_universities.py
```

The current dataset contains 30,384 applicant records.

## SQL Security

Raw SQL values are passed through Psycopg parameter binding rather than being
concatenated directly into SQL strings.

Dynamic SQL identifiers are restricted to an allowlist and composed using:

```text
psycopg.sql.SQL
psycopg.sql.Identifier
```

User-controlled query limits are clamped to the supported range of 1 through
100.

The test suite includes malicious SQL input intended to verify that values
such as SQL injection payloads remain query parameters rather than executable
SQL structure.

SQLAlchemy ORM queries also include explicit result limits where appropriate.

## Running the SQL Analyses

Raw Psycopg analysis:

```powershell
python .\src\query_data.py
```

SQLAlchemy ORM analysis:

```powershell
python .\src\orm_queries.py
```

The two implementations produce matching analysis results.

## Running the Flask Application

Make sure PostgreSQL is running and the required environment variables are
set.

From `module_5`:

```powershell
python .\src\app.py
```

The webpage provides:

- **Update Analysis** - refreshes the displayed analysis
- **Pull Data** - starts the GradCafe data collection workflow

The Flask application uses a `create_app()` application factory to support
dependency injection during testing.

## Automated Testing

Run:

```powershell
pytest
```

The current completed test suite reports:

```text
165 passed
1 skipped
988 statements
0 missed
100% coverage
```

Coverage configuration is defined in:

```text
pytest.ini
```

## Pylint

Run Pylint against every Python file under `src` with:

```powershell
$pyFiles = Get-ChildItem .\src -Recurse -Filter *.py |
    ForEach-Object { $_.FullName }

pylint $pyFiles
```

The current project rating is:

```text
10.00/10
```

## Dependency Analysis

Python module dependencies are analyzed with pydeps and rendered with
Graphviz.

Generate the dependency graph from `module_5` with:

```powershell
pydeps .\src --noshow -o dependency.svg
```

The generated dependency diagram is:

```text
dependency.svg
```

The dependency graph shows how the major Python modules in the application
interact with one another. The Flask application acts as an orchestration
layer, using the database models and ORM query functions to generate analysis
results and invoking the pull-data workflow when new applicant data is
requested. The `pull_data_workflow` module coordinates several lower-level
modules, including data capture, cleaning, PostgreSQL loading, and
original-university loading. The `orm_queries` module depends on `models` for
the SQLAlchemy models and database session management, keeping query logic
separate from the database model definitions. The data-loading modules are
also reused rather than duplicating database connection and data-processing
logic, which reduces unnecessary coupling and repeated code. Overall, the
dependency graph reflects a layered design in which the web interface
coordinates the workflow while specialized modules handle scraping,
cleaning, database access, and analysis.

## Sphinx Documentation

Documentation source files are stored in:

```text
docs/
```

Build the documentation from `module_5` with:

```powershell
python -m sphinx -W -b html .\docs .\docs\_build\html
```

## Main Module 5 Deliverables

- `README.md`
- `requirements.txt`
- `setup.py`
- `.env.example`
- `.gitignore`
- `dependency.svg`
- secured raw SQL implementation
- secured SQLAlchemy ORM implementation
- least-privilege PostgreSQL configuration
- SQL injection security tests
- complete Pytest suite
- 100% test coverage
- Pylint 10.00/10
- Sphinx documentation
