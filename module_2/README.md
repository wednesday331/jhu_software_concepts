# Module 2 - GradCafe Web Scraping and LLM Data Cleaning

## Student Information

- Name: Shrey Shanbhag
- JHED ID: 33EBE2
- Module: Module 2
- Assignment: Web Scraping
- Due Date: September 13, 2026

## Overview

This project collects publicly available graduate admissions result data from GradCafe, parses the applicant information into structured JSON, and uses a local large language model (LLM) to normalize program and university names.

The project was designed to follow the Module 2 assignment requirements, including:

- reviewing `robots.txt` before scraping
- using `urllib` for URL access and management
- parsing admissions data from publicly accessible pages
- preserving original source text for traceability
- producing structured and valid JSON
- cleaning data using a local LLM
- avoiding login-protected and private information
- stopping rather than bypassing verification, blocking, or rate limiting

## robots.txt Review

Before collecting data, GradCafe's `robots.txt` file was reviewed.

The file contains rules permitting access to public portions of the website, including:

```text
User-agent: *
Allow: /
```

It also identifies restricted account-related paths such as sign-in, registration, password reset, email verification, and profile pages.

This project does not access those restricted, login-protected, or private pages.

A screenshot showing the reviewed `robots.txt` file is included in the project as:

```text
screenshot.jpg
```

## Cloudflare Limitation

During development, a direct request to GradCafe using `urllib` returned an HTTP 403 response.

GradCafe also presented Cloudflare verification when attempting to access the site programmatically.

The instructor-provided workaround was therefore followed:

1. GradCafe is opened manually in a normal Chrome browser.
2. Any Cloudflare verification is completed manually by the user.
3. A helper script captures the HTML already rendered in the manually verified browser session.
4. The saved public HTML is passed to the project's existing parser.
5. The process continues through normal public GradCafe pagination.

The program does not attempt to solve or bypass CAPTCHA, Cloudflare verification, rate limits, login controls, or other access restrictions.

If GradCafe presents a verification, blocking, or rate-limiting page, the automated process stops rather than attempting to circumvent it.

## Scraping Process

The primary scraping and parsing logic is implemented in:

```text
scrape.py
```

The Chrome capture and resumable pagination helper is implemented in:

```text
capture_page.py
```

The general workflow is:

1. Load previously collected records from `applicant_data.json`.
2. Read the currently rendered public GradCafe survey page.
3. Identify publicly available applicant result links.
4. Save the rendered HTML locally for traceability and recovery during collection.
5. Parse applicant information from the captured page.
6. Add only records whose result URL has not previously been saved.
7. Periodically save checkpoints to `applicant_data.json`.
8. Locate the normal cursor-based URL for the next GradCafe survey page.
9. Wait before navigating to the next public page.
10. Stop if verification, blocking, rate limiting, or an unexpected page is detected.

A polite delay is used between page navigations to avoid sending rapid requests to the website.

The scraper is resumable. Existing result URLs are loaded before new records are added, which prevents duplicate applicant records when the collection process is restarted.

## Applicant Data

When available on the source page, the parser collects information including:

- Program Name
- University
- Comments
- Date Added
- Result URL
- Applicant Status
- Acceptance Date
- Rejection Date
- Semester and Year
- International or American applicant status
- GRE
- GRE Verbal
- GRE Analytical Writing
- Degree Type
- GPA
- Original raw listing text

Missing information is represented consistently rather than fabricated.

The original raw listing text is preserved so that parsed and subsequently normalized information can be traced back to the source data.

## Scraped Data Output

The primary structured output is:

```text
applicant_data.json
```

The assignment requires at least 30,000 applicant entries. The final `applicant_data.json` dataset contains **30,340 unique applicant records**.

Each applicant is represented as a structured JSON record.

Result URLs are used as unique identifiers during collection to prevent duplicate records when the scraper is stopped and resumed. The final dataset contains **30,340 unique result URLs and zero duplicate result URLs**.

## LLM Data Cleaning

The assignment-provided local LLM hosting files are stored under:

```text
llm_hosting/
```

The local LLM is used to normalize program and university information after the scraping stage.

The extended dataset includes the following LLM-generated fields:

```text
llm-generated-program
llm-generated-university
```

The original program, university, and source information are retained for traceability.

The cleaning workflow is resumable and saves checkpoints periodically. The local LLM is loaded once during a cleaning run rather than being reloaded for every group of records.

To reduce redundant inference, exact duplicate `(program, university)` input pairs reuse a previously generated LLM result. The local LLM is configured for deterministic generation, so memoization avoids unnecessary repeated inference for identical inputs while preserving the generated mapping.

The completed `llm_extend_applicant_data.json` contains **30,340 records**. The original program, university, and result URL values remain preserved and in the same order as `applicant_data.json`.

All 30,340 records contain both `llm-generated-program` and `llm-generated-university`.

The final LLM-extended output is saved as:

```text
llm_extend_applicant_data.json
```

## Project Structure

The final project contains the following primary files and directories:

```text
module_2/
|-- scrape.py
|-- clean.py
|-- capture_page.py
|-- applicant_data.json
|-- llm_extend_applicant_data.json
|-- screenshot.jpg
|-- README.md
|-- requirements.txt
`-- llm_hosting/
```

Raw HTML pages were retained locally during development for recovery and validation but are excluded from the final repository. The original raw listing text needed for traceability is preserved within each structured applicant record.

The local Python virtual environment, downloaded LLM model files, temporary processing files, and intermediate worker outputs are also excluded from the repository.

## Installation

Python 3.10 or newer is required for the project.

Install the primary scraping dependencies from the `module_2` directory using:

```bash
pip install -r requirements.txt
```

The local LLM uses the additional dependencies supplied in:

```text
llm_hosting/requirements.txt
```

A Python 3.11 virtual environment was used for the local LLM because it provided compatibility with the required `llama-cpp-python` package.

The virtual environment and downloaded model files are local development dependencies and are intentionally excluded from Git.

## Running the Scraping Process

The GradCafe page is first opened in the separate Chrome capture window.

Any Cloudflare verification is completed manually.

Once normal applicant results are visible, the capture process can be started from the `module_2` directory with:

```bash
python capture_page.py
```

The script saves raw HTML pages locally and incrementally builds:

```text
applicant_data.json
```

The process can be stopped and resumed without intentionally duplicating previously collected result URLs.

## Running the LLM Cleaning Process

After the required applicant data has been collected, the local LLM cleaning process normalizes the program and university information.

On Windows, after creating the Python 3.11 virtual environment and installing the dependencies under `llm_hosting`, the cleaning workflow can be run from the repository root with:

```powershell
.\module_2\llm_hosting\.venv\Scripts\python.exe .\module_2\clean.py
```

The cleaning process is resumable and periodically saves progress to:

```text
llm_extend_applicant_data.json
```

If the output file already contains all 30,340 records, `clean.py` detects that the cleaning process is complete without rerunning the LLM.

The original applicant values are preserved alongside the LLM-generated normalized values.

## Ethical and Access Restrictions

This project is intentionally limited to publicly accessible admissions result pages.

The project:

- reviews and respects `robots.txt`
- uses only publicly accessible GradCafe pages
- does not access login-protected account information
- does not scrape private pages
- does not attempt to bypass CAPTCHA
- does not attempt to bypass Cloudflare verification
- does not bypass rate limits
- does not circumvent access controls
- stops when verification or blocking is detected
- uses delays between normal page navigations
- does not fabricate unavailable applicant data
- preserves original source text for traceability

## Final Deliverables

The final Module 2 submission includes:

- `scrape.py`
- `clean.py`
- `capture_page.py`
- the provided `llm_hosting` files
- `applicant_data.json`
- `llm_extend_applicant_data.json`
- `screenshot.jpg`
- `README.md`
- `requirements.txt`

All assignment materials are maintained under the `module_2` directory of the private `jhu_software_concepts` GitHub repository.