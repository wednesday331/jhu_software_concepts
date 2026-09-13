import json
from pathlib import Path

from llm_hosting.app import _call_llm

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
        json.dump(data, file, indent=2, ensure_ascii=False)


def _make_key(record):
    """Return the exact program/university pair used for memoization."""
    program = str(record.get("program", "")).strip()
    university = str(record.get("university", "")).strip()
    return program, university


def _build_llm_text(record):
    """
    Build the text sent to the local LLM.

    The instructor-provided LLM accepts one text field, so the original
    program and university are combined temporarily for standardization.
    """
    program, university = _make_key(record)

    if university:
        return f"{program}, {university}"

    return program


def _build_cache(cleaned_records):
    """
    Build a cache of exact program/university pairs that have already
    been standardized.
    """
    cache = {}

    for record in cleaned_records:
        llm_program = record.get("llm-generated-program")
        llm_university = record.get("llm-generated-university")

        if llm_program is None or llm_university is None:
            continue

        cache[_make_key(record)] = {
            "standardized_program": llm_program,
            "standardized_university": llm_university,
        }

    return cache


def clean_data(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    """
    Standardize GradCafe program and university values using the
    instructor-provided local LLM.

    Processing is resumable. Exact duplicate program/university pairs
    reuse the previously generated deterministic LLM result so redundant
    inference calls are avoided.
    """
    input_file = Path(input_file)
    output_file = Path(output_file)

    if not input_file.exists():
        raise FileNotFoundError(f"Missing input file: {input_file}")

    original_records = load_data(input_file)

    print(f"Input records: {len(original_records)}")

    if output_file.exists():
        cleaned_records = load_data(output_file)

        if len(cleaned_records) > len(original_records):
            raise ValueError(
                "Output file contains more records than the input file."
            )

        start_index = len(cleaned_records)

        print(
            f"Existing cleaned records found: {start_index}. "
            "Resuming..."
        )
    else:
        cleaned_records = []
        start_index = 0

    if start_index == len(original_records):
        print("All records are already cleaned.")
        return cleaned_records

    cache = _build_cache(cleaned_records)

    print(f"Cached combinations available: {len(cache)}")
    print(
        f"Remaining records: "
        f"{len(original_records) - start_index}"
    )

    llm_calls = 0
    cache_hits = 0

    for index in range(start_index, len(original_records)):
        original = original_records[index]

        key = _make_key(original)

        if key in cache:
            result = cache[key]
            cache_hits += 1
        else:
            llm_text = _build_llm_text(original)
            result = _call_llm(llm_text)

            cache[key] = result
            llm_calls += 1

        final_record = original.copy()

        final_record["llm-generated-program"] = result.get(
            "standardized_program",
            "",
        )

        final_record["llm-generated-university"] = result.get(
            "standardized_university",
            "",
        )

        cleaned_records.append(final_record)

        if len(cleaned_records) % CHECKPOINT_INTERVAL == 0:
            save_data(cleaned_records, output_file)

            print(
                f"Checkpoint: "
                f"{len(cleaned_records)} / {len(original_records)} "
                f"| LLM calls: {llm_calls} "
                f"| Cache hits: {cache_hits}",
                flush=True,
            )

    save_data(cleaned_records, output_file)

    print()
    print("LLM cleaning complete.")
    print(f"Cleaned records: {len(cleaned_records)}")
    print(f"New LLM calls: {llm_calls}")
    print(f"Cache hits: {cache_hits}")
    print(f"Saved: {output_file}")

    return cleaned_records


if __name__ == "__main__":
    clean_data()