# Module 3 — Database Queries, SQLAlchemy, and Dynamic Webpages

## Overview

This module uses the GradCafe applicant dataset collected and cleaned in Module 2. The dataset contains 30,340 applicant records. The project loads the records into PostgreSQL, analyzes them using raw SQL and SQLAlchemy ORM, and compares the two approaches.

## Database and Data Loading

The PostgreSQL database is named `gradcafe`. The `applicants` table contains 30,340 records loaded from `llm_extend_applicant_data.json` using `load_data.py`.

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

The raw SQL query is concise and shows the database operation directly, making the filtering and counting logic easy to inspect. SQLAlchemy ORM allows the query to use a mapped Python class and a reusable filtering function, which can help organize queries within a larger Python application. An advantage of using an ORM is that common query conditions can be defined once and reused across multiple analyses. An advantage of writing SQL directly is having clear visibility and control over the SQL statement sent to PostgreSQL. Both approaches returned **29,901 Fall 2026 applicant entries**.

## Running the Analysis

After installing the dependencies and setting the PostgreSQL connection environment variables, run the following commands from the `module_3` directory:

```powershell
python query_data.py
python orm_queries.py
```

Both scripts should produce the same results for all 11 questions.

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
* `requirements.txt` — lists the project dependencies.

### LLM model setup

The TinyLlama GGUF model file is not included in this submission because it is a large downloaded artifact. The LLM hosting code in `llm_hosting/app.py` uses `hf_hub_download` to download `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` from `TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF` when the model is first needed. An internet connection and the dependencies listed in `llm_hosting/requirements.txt` are required for that initial download.
