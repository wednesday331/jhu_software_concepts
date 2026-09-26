
# Module 3 - Database Queries, SQLAlchemy, and Dynamic Webpages

## Overview

This module uses the GradCafe applicant dataset collected and cleaned in Module 2. The dataset contains 30,384 applicant records. The project loads the records into PostgreSQL, analyzes them using raw SQL and SQLAlchemy ORM, and compares the two approaches.

The project also includes a Flask webpage that displays database analysis results and provides controls for refreshing the analysis and starting the data collection workflow.

## Database and Data Loading

The PostgreSQL database is named `gradcafe`. The `applicants` table contains 30,384 records loaded from `llm_extend_applicant_data.json` using `load_data.py`.

The `applicant_original_universities` table preserves original university names from the downloaded data. It is joined to `applicants` for questions that require original university values rather than LLM-generated values.

Database connection settings are read from environment variables instead of being stored in the Python source files.

## Setup and Running the Project

Run the following commands from the `module_3` directory unless otherwise indicated.

### 1. Install dependencies

Create and activate a Python virtual environment if you do not already have one. Install the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

The LLM hosting component has additional dependencies listed in `llm_hosting/requirements.txt`.

### 2. Create the PostgreSQL database

Start PostgreSQL and create a database named `gradcafe` using pgAdmin or another PostgreSQL administration tool.

Set the PostgreSQL connection environment variables in PowerShell. Replace `YOUR_POSTGRES_USERNAME` with your PostgreSQL username:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "gradcafe"
$env:PGUSER = "YOUR_POSTGRES_USERNAME"
$env:PGPASSWORD = Read-Host "PostgreSQL password"
```

These settings apply to the current PowerShell session. Do not store your database password in the source code or commit it to GitHub.

### 3. Create and populate the database tables

Run the main data-loading script:

```powershell
python load_data.py
```

This script creates the `applicants` table if needed and loads the applicant records.

Before loading original university names into a new database, execute the following SQL in the `gradcafe` database using pgAdmin Query Tool:

```sql
CREATE TABLE IF NOT EXISTS applicant_original_universities (
    p_id INTEGER PRIMARY KEY REFERENCES applicants(p_id),
    university TEXT
);
```

Then run:

```powershell
python load_original_universities.py
```

The supplementary table stores original university names associated with applicant IDs.

### 4. Run the raw SQL and ORM analyses

```powershell
python query_data.py
python orm_queries.py
```

Both scripts analyze the existing PostgreSQL data and should produce the same results for all 11 questions. The questions, raw SQL statements, results, and explanations are documented in `query_results.pdf`.

### 5. Run the Flask application

With PostgreSQL running and the database populated, start the Flask application from the `module_3` directory:

```powershell
python app.py
```

Open the local address displayed in the terminal.

The webpage retrieves analysis results from PostgreSQL through SQLAlchemy ORM.

- **Update Analysis** refreshes the displayed analysis results.
- **Pull Data** starts the data collection and refresh workflow. The application displays workflow status and prevents conflicting simultaneous pull operations.

The Pull Data workflow may require additional local configuration for scraping and LLM processing. See `llm_hosting/README.md` for the additional setup and workflow instructions.

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

The raw SQL query is concise and shows the database operation directly, making the filtering and counting logic easy to inspect. SQLAlchemy ORM allows the query to use a mapped Python class and a reusable filtering function, which can help organize queries within a larger Python application.

An advantage of using an ORM is that common query conditions can be defined once and reused across multiple analyses. An advantage of writing SQL directly is having clear visibility and control over the SQL statement sent to PostgreSQL.

Both approaches returned **29,902 Fall 2026 applicant entries**.

## Running the Analysis

After installing the dependencies, loading the applicant data, and setting the PostgreSQL connection environment variables, run the following commands from the `module_3` directory:

```powershell
python query_data.py
python orm_queries.py
```

Both scripts should produce the same results for all 11 questions.

## Analysis Notes

Question 3 calculates each average independently and filters GPA and GRE values to the score ranges specified in the query. The GPA filter assumes a 0-4 scale, so values reported on other GPA scales are excluded from that average.

Questions 8 and 9 compare results obtained using original program and university fields with results obtained using LLM-generated fields. The original-field query returned 28 matching entries, while the LLM-field query returned 24, a difference of -4. This is a difference between the total matching counts; it does not establish that exactly four individual records were classified differently.

## Data Limitations

The GradCafe dataset consists of anonymously submitted applicant information. It is not a random sample of all graduate-school applicants. Self-selection, missing information, inconsistent reporting, and potentially inaccurate entries can affect the analysis.

The results describe the records in this dataset and should not be interpreted as representative admission rates or outcomes for all applicants. The implications of these limitations for the analysis are discussed in `limitations.pdf`.

## Project Files

- `github.txt` - contains the GitHub repository SSH URL.
- `load_data.py` - creates and populates the main PostgreSQL applicants table.
- `load_original_universities.py` - loads original university names into the supplementary table.
- `models.py` - defines the SQLAlchemy ORM mappings.
- `query_data.py` - executes the raw SQL analysis.
- `orm_queries.py` - executes the SQLAlchemy ORM analysis.
- `app.py` - runs the Flask application and displays database analysis results.
- `pull_data_workflow.py` - coordinates the data collection and refresh workflow.
- `scrape.py` - provides the scraping functionality.
- `llm_hosting/` - contains the LLM hosting application and additional setup instructions.
- `query_results.pdf` - documents the 11 SQL questions, queries, results, and explanations.
- `limitations.pdf` - discusses limitations of the applicant dataset.
- `llm_extend_applicant_data.json` - contains the cleaned applicant dataset.
- `requirements.txt` - lists the project dependencies.
- `raw_sql_output.png` - screenshot of the raw SQL analysis output.
- `orm_output.png` - screenshot of the ORM analysis output.
- `flask_webpage.png` - screenshot of the running Flask webpage.

## LLM Model Setup

The TinyLlama GGUF model file is not included in this submission because it is a large downloaded artifact.

The LLM hosting code in `llm_hosting/app.py` uses `hf_hub_download` to download `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` from `TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF` when the model is first needed.

An internet connection and the dependencies listed in `llm_hosting/requirements.txt` are required for that initial download. See `llm_hosting/README.md` for additional setup instructions.