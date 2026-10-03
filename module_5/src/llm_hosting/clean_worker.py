"""Worker utilities for cleaning applicant records with LLM assistance."""
# pylint: disable=duplicate-code

import json
import sys
from pathlib import Path

from app import _call_llm # pylint: disable=no-name-in-module


def load_json(path):
    """Load and return JSON data from the specified file."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data, path):
    """Write JSON data to the specified file."""
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def make_key(record):
    """Return a normalized program and university key for a record."""
    program = str(record.get("program", "")).strip()
    university = str(record.get("university", "")).strip()
    return program, university


def build_cache(cache_files):
    """
    Build a cache from records that have already been processed by the LLM.
    """
    cache = {}

    for path in cache_files:
        if not path.exists():
            continue

        records = load_json(path)

        for record in records:
            key = make_key(record)

            llm_program = record.get("llm-generated-program")
            llm_university = record.get("llm-generated-university")

            if llm_program is not None and llm_university is not None:
                cache[key] = {
                    "standardized_program": llm_program,
                    "standardized_university": llm_university,
                }

    return cache


def main():  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Clean the assigned range of applicant records using the LLM worker."""
    if len(sys.argv) != 5:
        print(
            "Usage: clean_worker.py "
            "<input_file> <output_file> <start_index> <end_index>"
        )
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    start_index = int(sys.argv[3])
    end_index = int(sys.argv[4])

    records = load_json(input_file)

    if start_index < 0 or end_index > len(records):
        raise ValueError("Start/end indexes are outside the input data range.")

    if start_index >= end_index:
        raise ValueError("start_index must be less than end_index.")

    if output_file.exists():
        cleaned = load_json(output_file)
    else:
        cleaned = []

    resume_index = start_index + len(cleaned)

    if resume_index > end_index:
        raise ValueError(
            "Output file contains more records than expected for this range."
        )

    # Previously cleaned data from all workers.
    cache_files = [
        Path("llm_extend_applicant_data.json"),
        Path("llm_part1.json"),
        Path("llm_part2.json"),
    ]

    cache = build_cache(cache_files)

    print(f"Assigned range: records {start_index + 1}-{end_index}")
    print(f"Already completed by this worker: {len(cleaned)}")
    print(f"Cached LLM combinations available: {len(cache)}")

    if resume_index < end_index:
        print(f"Resuming at record {resume_index + 1}")
    else:
        print("This worker is already complete.")

    llm_calls = 0
    cache_hits = 0

    for index in range(resume_index, end_index):
        original = records[index]

        program = str(original.get("program", "")).strip()
        university = str(original.get("university", "")).strip()

        key = (program, university)

        # Reuse an LLM result if this exact combination was already cleaned.
        if key in cache:
            result = cache[key]
            cache_hits += 1

        else:
            if university:
                llm_text = f"{program}, {university}"
            else:
                llm_text = program

            result = _call_llm(llm_text)
            cache[key] = result
            llm_calls += 1

        final_record = original.copy()

        final_record["llm-generated-program"] = result.get(
            "standardized_program", ""
        )

        final_record["llm-generated-university"] = result.get(
            "standardized_university", ""
        )

        cleaned.append(final_record)

        if len(cleaned) % 100 == 0:
            save_json(cleaned, output_file)

            print(
                f"Checkpoint: "
                f"{start_index + len(cleaned)} / {end_index} "
                f"| LLM calls: {llm_calls} "
                f"| Cache hits: {cache_hits}",
                flush=True,
            )

    save_json(cleaned, output_file)

    print("Complete.")
    print(f"Records cleaned by this worker: {len(cleaned)}")
    print(f"New LLM calls: {llm_calls}")
    print(f"Cache hits: {cache_hits}")


if __name__ == "__main__":
    main()
