"""Clean GradCafe records using the local standardization LLM."""

import json
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent

INPUT_FILE = MODULE_DIR / "applicant_data.json"
OUTPUT_FILE = MODULE_DIR / "llm_extend_applicant_data.json"

CHECKPOINT_INTERVAL = 100


def load_data(path):
    """Load JSON data from a file."""

    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data, path):
    """Save JSON data to a file."""

    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def _make_key(record):
    """Return the exact program/university pair used for memoization."""

    program = str(
        record.get("program", "")
    ).strip()

    university = str(
        record.get("university", "")
    ).strip()

    return program, university


def _build_llm_text(record):
    """
    Build the text sent to the local LLM.

    The program and university are combined temporarily
    for standardization.
    """

    program, university = _make_key(record)

    if university:
        return f"{program}, {university}"

    return program


def _build_cache(cleaned_records):
    """
    Build a cache of program/university pairs already standardized.
    """

    cache = {}

    for record in cleaned_records:
        llm_program = record.get(
            "llm-generated-program"
        )

        llm_university = record.get(
            "llm-generated-university"
        )

        if (
            llm_program is None
            or llm_university is None
        ):
            continue

        cache[_make_key(record)] = {
            "standardized_program":
                llm_program,
            "standardized_university":
                llm_university,
        }

    return cache


def clean_data(  # pylint: disable=too-many-locals
    input_file=INPUT_FILE,
    output_file=OUTPUT_FILE,
    llm_caller=None,
):
    """
    Standardize GradCafe program and university values.

    Parameters
    ----------
    input_file : pathlib.Path or str
        Raw applicant JSON file.

    output_file : pathlib.Path or str
        Cleaned applicant JSON file.

    llm_caller : callable, optional
        Function used to standardize a record. Tests may inject
        a fake function so no real LLM or network dependency
        is required.

    Returns
    -------
    list
        Cleaned applicant records.
    """

    input_file = Path(input_file)
    output_file = Path(output_file)

    if not input_file.exists():
        raise FileNotFoundError(
            f"Missing input file: {input_file}"
        )

    original_records = load_data(input_file)

    print(
        f"Input records: "
        f"{len(original_records)}"
    )

    if output_file.exists():
        cleaned_records = load_data(
            output_file
        )

        if len(cleaned_records) > len(
            original_records
        ):
            raise ValueError(
                "Output file contains more records "
                "than the input file."
            )

        start_index = len(
            cleaned_records
        )

        print(
            f"Existing cleaned records found: "
            f"{start_index}. Resuming..."
        )

    else:
        cleaned_records = []
        start_index = 0

    if start_index == len(
        original_records
    ):
        print(
            "All records are already cleaned."
        )

        return cleaned_records

    # Only import the real LLM when it is actually needed.
    # Pytest can inject a fake llm_caller instead.
    if llm_caller is None:
        from llm_hosting.app import _call_llm  # pylint: disable=import-outside-toplevel

        llm_caller = _call_llm

    cache = _build_cache(
        cleaned_records
    )

    print(
        f"Cached combinations available: "
        f"{len(cache)}"
    )

    print(
        "Remaining records: "
        f"{len(original_records) - start_index}"
    )

    llm_calls = 0
    cache_hits = 0

    for index in range(
        start_index,
        len(original_records),
    ):
        original = original_records[
            index
        ]

        key = _make_key(
            original
        )

        if key in cache:
            result = cache[key]
            cache_hits += 1

        else:
            llm_text = _build_llm_text(
                original
            )

            result = llm_caller(
                llm_text
            )

            cache[key] = result
            llm_calls += 1

        final_record = (
            original.copy()
        )

        final_record[
            "llm-generated-program"
        ] = result.get(
            "standardized_program",
            "",
        )

        final_record[
            "llm-generated-university"
        ] = result.get(
            "standardized_university",
            "",
        )

        cleaned_records.append(
            final_record
        )

        if (
            len(cleaned_records)
            % CHECKPOINT_INTERVAL
            == 0
        ):
            save_data(
                cleaned_records,
                output_file,
            )

            print(
                "Checkpoint: "
                f"{len(cleaned_records)} / "
                f"{len(original_records)} "
                f"| LLM calls: "
                f"{llm_calls} "
                f"| Cache hits: "
                f"{cache_hits}",
                flush=True,
            )

    save_data(
        cleaned_records,
        output_file,
    )

    print()
    print(
        "LLM cleaning complete."
    )
    print(
        f"Cleaned records: "
        f"{len(cleaned_records)}"
    )
    print(
        f"New LLM calls: "
        f"{llm_calls}"
    )
    print(
        f"Cache hits: "
        f"{cache_hits}"
    )
    print(
        f"Saved: {output_file}"
    )

    return cleaned_records


if __name__ == "__main__":
    clean_data()
