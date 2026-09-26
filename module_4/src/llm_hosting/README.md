# Module 3 — Database Queries, SQLAlchemy, and Dynamic Webpages

## Overview

This module uses the GradCafe applicant dataset collected and cleaned in Module 2. The original cleaned Module 2 dataset contained 30,340 applicant records. After subsequent Pull Data imports, the PostgreSQL `applicants` table contains 30,384 records (verified in pgAdmin on September 20, 2026). The project loads records into PostgreSQL, analyzes them using raw SQL and SQLAlchemy ORM, and compares the two approaches.

## Database and Data Loading

The PostgreSQL database is named `gradcafe`. The `applicants` table contains 30,384 records at the time of the latest database count. Initial records were loaded from `llm_extend_applicant_data.json` using `load_data.py`; the Pull Data workflow can import additional records.

The `applicant_original_universities` table preserves original university names from the downloaded data. It is joined to `applicants` for questions that require original university values rather than LLM-generated values.

Database connection settings are read from environment variables instead of being stored in the Python source files.

## Raw SQL Analysis

`query_data.py` executes the nine required questions and two original questions using Psycopg and PostgreSQL SQL queries. The questions, results, SQL statements, and explanations are documented in `query_results.pdf`.

## SQLAlchemy ORM Analysis

`models.py` maps the existing PostgreSQL tables to Python classes. `orm_queries.py` uses SQLAlchemy ORM to execute the same 11 analysis questions.

The ORM script produced the same results as the raw SQL script for all 11 questions. Neither script needs to reload the applicant data.

## Part 7: Compare SQL and SQLAlchemy

For this comparison, I selected **Question 1: How many entries are from applicants who applied for Fall 2026?**

### Raw SQL Query

```sql
SELECT COUNT(*)
FROM applicants
WHERE LOWER(TRIM(term)) = 'fall 2026';
```

### Corresponding SQLAlchemy Query

```python
count = (
    session.query(func.count(Applicant.p_id))
    .filter(fall_2026_condition())
    .scalar()
)
```

The helper function used by the SQLAlchemy query is:

```python
def fall_2026_condition():
    return normalized(Applicant.term) == "fall 2026"
```

The `normalized()` helper applies `TRIM` and `LOWER` to the column, matching the raw SQL query.

### Comparison

The raw SQL query is concise and shows the database operation directly, making the filtering and counting logic easy to inspect. SQLAlchemy ORM allows the query to use a mapped Python class and a reusable filtering function, which can help organize queries within a larger Python application. An advantage of using an ORM is that common query conditions can be defined once and reused across multiple analyses. An advantage of writing SQL directly is having clear visibility and control over the SQL statement sent to PostgreSQL. Both approaches returned **29,902 Fall 2026 applicant entries** against the updated database.

## Setup and Running the Project

Run commands from the `module_3` directory. Python 3.11 and a local PostgreSQL server are used for this project. Create a PostgreSQL database named `gradcafe` and ensure that the `applicants` and `applicant_original_universities` tables have been created with the schema expected by `load_data.py`, `load_original_universities.py`, and `models.py`. The data-loading scripts must be run against that schema; they are not substitutes for creating the database and its tables. Use pgAdmin or your existing database setup to verify the schema before loading data.

Install dependencies in your Python environment:

```powershell
python -m pip install -r requirements.txt
```

Set the PostgreSQL environment variables in the PowerShell terminal where you will run the scripts. Substitute your actual database username and enter the password locally; never commit credentials to GitHub or include them in the ZIP:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "gradcafe"
$env:PGUSER = "YOUR_POSTGRES_USERNAME"
$securePassword = Read-Host "PostgreSQL password" -AsSecureString
$env:PGPASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
Remove-Variable securePassword
```

If the tables have not yet been populated, load the included cleaned dataset and original university names:

```powershell
python load_data.py
python load_original_universities.py
```

Run the analyses independently:

```powershell
python query_data.py
python orm_queries.py
```

Both scripts query the existing database and should agree on corresponding results. They do not start a scrape or reload the dataset. Run the Flask application with:

```powershell
python app.py
```

Open `http://127.0.0.1:5000/` in a browser. **Update Analysis** refreshes the displayed results from PostgreSQL without initiating data collection. **Pull Data** starts the capture, cleaning, and database-import workflow; the page reports progress and prevents a second simultaneous pull. The capture workflow uses a dedicated local Chrome window. If GradCafe requires verification, complete it manually in that window, navigate to a survey page showing results, and click Pull Data again. Newly imported records appear in the analysis after refreshing it. Pull Data requires the included Module 2 scraping and cleaning code, the supporting `llm_hosting` files, and a working local LLM configuration.

## Screenshots and Deliverables

The submission includes screenshots of the raw SQL console output, ORM console output, and running Flask webpage; `query_results.pdf` documents the SQL questions and results, while `limitations.pdf` discusses the limitations of the self-reported applicant data. `github.txt` contains the SSH URL for the private GitHub repository. The GitHub version and Canvas ZIP should contain the same final project files.

## Analysis Notes

Question 3 calculates each average independently and filters GPA and GRE values to the score ranges specified in the query. The GPA filter assumes a 0–4 scale, so values reported on other GPA scales are excluded from that average.

Questions 8 and 9 compare results obtained using original program and university fields with results obtained using LLM-generated fields. The original-field query returned 28 matching entries, while the LLM-field query returned 24, a difference of −4. This is a difference between the total matching counts; it does not establish that exactly four individual records were classified differently.

## Project Files

* `load_data.py` — loads applicant records into PostgreSQL.
* `load_original_universities.py` — loads original university names into the supplementary table.
* `models.py` — defines the SQLAlchemy ORM mappings.
* `query_data.py` — executes the raw SQL analysis.
* `orm_queries.py` — executes the SQLAlchemy ORM analysis.
* `query_results.pdf` — documents the 11 SQL questions, queries, results, and explanations.
* `llm_extend_applicant_data.json` — contains the cleaned applicant dataset.
* `app.py` and `pull_data_workflow.py` — Flask application and background Pull Data workflow.
* `capture_page.py`, `scrape.py`, and `clean.py` — GradCafe capture, parsing, and cleaning code reused from Module 2.
* `llm_hosting/` — supporting LLM cleaning code and model configuration files (excluding local virtual environments and credentials).
* `templates/analysis.html` and `static/style.css` — webpage template and styling.
* `applicant_data.json` — saved raw applicant records used by the data-refresh workflow.
* `limitations.pdf` — written reflection on data limitations.
* `github.txt` — private GitHub repository SSH URL.
* `requirements.txt` — lists the project dependencies.
