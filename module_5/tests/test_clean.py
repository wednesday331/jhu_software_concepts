"""Tests for GradCafe cleaning helpers and workflow."""

import json
import sys
from types import ModuleType

import pytest

import clean
import io
import json
import runpy
import sys
from pathlib import Path
from types import ModuleType

import pytest

import clean

@pytest.mark.analysis
def test_save_and_load_data_round_trip(tmp_path):
    """JSON data should save and load without changing content."""

    path = tmp_path / "data.json"

    records = [
        {
            "program": "Computer Science",
            "university": "Johns Hopkins University",
        }
    ]

    clean.save_data(records, path)

    loaded = clean.load_data(path)

    assert loaded == records


@pytest.mark.analysis
def test_key_and_llm_text_helpers():
    """Cleaning helpers should normalize input text for cache keys."""

    record = {
        "program": "  Computer Science  ",
        "university": "  Johns Hopkins University  ",
    }

    assert clean._make_key(record) == (
        "Computer Science",
        "Johns Hopkins University",
    )

    assert (
        clean._build_llm_text(record)
        == "Computer Science, Johns Hopkins University"
    )

    record_without_university = {
        "program": "Computer Science",
        "university": "",
    }

    assert (
        clean._build_llm_text(record_without_university)
        == "Computer Science"
    )


@pytest.mark.analysis
def test_build_cache_uses_only_complete_cleaned_records():
    """Incomplete LLM results should not be added to the cache."""

    records = [
        {
            "program": "CS",
            "university": "JHU",
            "llm-generated-program": "Computer Science",
            "llm-generated-university":
                "Johns Hopkins University",
        },
        {
            "program": "Math",
            "university": "Test University",
            "llm-generated-program": None,
            "llm-generated-university":
                "Test University",
        },
    ]

    cache = clean._build_cache(records)

    assert ("CS", "JHU") in cache

    assert cache[("CS", "JHU")] == {
        "standardized_program":
            "Computer Science",
        "standardized_university":
            "Johns Hopkins University",
    }

    assert (
        "Math",
        "Test University",
    ) not in cache


@pytest.mark.analysis
def test_clean_data_raises_for_missing_input(tmp_path):
    """A missing source JSON file should fail clearly."""

    missing = tmp_path / "missing.json"
    output = tmp_path / "output.json"

    with pytest.raises(
        FileNotFoundError,
        match="Missing input file",
    ):
        clean.clean_data(
            missing,
            output,
            llm_caller=lambda text: {},
        )


@pytest.mark.analysis
def test_clean_data_rejects_output_larger_than_input(tmp_path):
    """A resume file cannot contain more records than the source."""

    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"

    clean.save_data(
        [
            {
                "program": "CS",
                "university": "JHU",
            }
        ],
        input_file,
    )

    clean.save_data(
        [
            {"program": "A"},
            {"program": "B"},
        ],
        output_file,
    )

    with pytest.raises(
        ValueError,
        match="Output file contains more records",
    ):
        clean.clean_data(
            input_file,
            output_file,
            llm_caller=lambda text: {},
        )


@pytest.mark.analysis
def test_clean_data_returns_when_already_complete(tmp_path):
    """An already-complete output should be returned unchanged."""

    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"

    original = [
        {
            "program": "CS",
            "university": "JHU",
        }
    ]

    cleaned = [
        {
            "program": "CS",
            "university": "JHU",
            "llm-generated-program":
                "Computer Science",
            "llm-generated-university":
                "Johns Hopkins University",
        }
    ]

    clean.save_data(
        original,
        input_file,
    )

    clean.save_data(
        cleaned,
        output_file,
    )

    result = clean.clean_data(
        input_file,
        output_file,
        llm_caller=lambda text: {
            "standardized_program": "unused",
            "standardized_university": "unused",
        },
    )

    assert result == cleaned


@pytest.mark.analysis
def test_clean_data_uses_fake_llm_and_saves_results(
    tmp_path,
    monkeypatch,
):
    """New records should be standardized using the injected LLM."""

    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"

    records = [
        {
            "program": "CS",
            "university": "JHU",
        },
        {
            "program": "Math",
            "university": "",
        },
    ]

    clean.save_data(
        records,
        input_file,
    )

    calls = []

    def fake_llm(text):
        calls.append(text)

        if text == "CS, JHU":
            return {
                "standardized_program":
                    "Computer Science",
                "standardized_university":
                    "Johns Hopkins University",
            }

        # Deliberately omit the university key to exercise
        # the default empty-string behavior.
        return {
            "standardized_program":
                "Mathematics",
        }

    # Exercise checkpoint saving without needing 100 records.
    monkeypatch.setattr(
        clean,
        "CHECKPOINT_INTERVAL",
        1,
    )

    result = clean.clean_data(
        input_file,
        output_file,
        llm_caller=fake_llm,
    )

    assert calls == [
        "CS, JHU",
        "Math",
    ]

    assert len(result) == 2

    assert (
        result[0]["llm-generated-program"]
        == "Computer Science"
    )

    assert (
        result[0]["llm-generated-university"]
        == "Johns Hopkins University"
    )

    assert (
        result[1]["llm-generated-program"]
        == "Mathematics"
    )

    assert (
        result[1]["llm-generated-university"]
        == ""
    )

    saved = clean.load_data(output_file)

    assert saved == result


@pytest.mark.analysis
def test_clean_data_resume_uses_cache(tmp_path):
    """A resumed run should reuse an existing standardized pair."""

    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"

    original = [
        {
            "program": "CS",
            "university": "JHU",
        },
        {
            "program": "CS",
            "university": "JHU",
        },
    ]

    existing = [
        {
            "program": "CS",
            "university": "JHU",
            "llm-generated-program":
                "Computer Science",
            "llm-generated-university":
                "Johns Hopkins University",
        }
    ]

    clean.save_data(
        original,
        input_file,
    )

    clean.save_data(
        existing,
        output_file,
    )

    def should_not_run(_text):
        raise AssertionError(
            "LLM should not be called for a cached pair."
        )

    result = clean.clean_data(
        input_file,
        output_file,
        llm_caller=should_not_run,
    )

    assert len(result) == 2

    assert (
        result[1]["llm-generated-program"]
        == "Computer Science"
    )

    assert (
        result[1]["llm-generated-university"]
        == "Johns Hopkins University"
    )


@pytest.mark.analysis
def test_clean_data_can_load_default_llm_dependency(
    tmp_path,
    monkeypatch,
):
    """The real LLM import path should remain injectable/testable."""

    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"

    clean.save_data(
        [
            {
                "program": "CS",
                "university": "JHU",
            }
        ],
        input_file,
    )

    fake_package = ModuleType(
        "llm_hosting"
    )

    fake_package.__path__ = []

    fake_app = ModuleType(
        "llm_hosting.app"
    )

    def fake_call_llm(_text):
        return {
            "standardized_program":
                "Computer Science",
            "standardized_university":
                "Johns Hopkins University",
        }

    fake_app._call_llm = fake_call_llm

    monkeypatch.setitem(
        sys.modules,
        "llm_hosting",
        fake_package,
    )

    monkeypatch.setitem(
        sys.modules,
        "llm_hosting.app",
        fake_app,
    )

    result = clean.clean_data(
        input_file,
        output_file,
    )

    assert (
        result[0]["llm-generated-program"]
        == "Computer Science"
    )

    assert (
        result[0]["llm-generated-university"]
        == "Johns Hopkins University"
    )

@pytest.mark.integration
def test_clean_main_entrypoint(
    monkeypatch,
    capsys,
):
    """Executing clean.py directly should invoke clean_data()."""

    input_records = [
        {
            "program": "CS",
            "university": "JHU",
        }
    ]

    cleaned_records = [
        {
            "program": "CS",
            "university": "JHU",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Johns Hopkins University",
        }
    ]

    input_json = json.dumps(
        input_records
    )

    cleaned_json = json.dumps(
        cleaned_records
    )

    original_open = Path.open
    original_exists = Path.exists

    def fake_exists(self):
        if self.name in {
            "applicant_data.json",
            "llm_extend_applicant_data.json",
        }:
            return True

        return original_exists(self)

    def fake_open(
        self,
        mode="r",
        *args,
        **kwargs,
    ):
        if (
            self.name == "applicant_data.json"
            and "r" in mode
        ):
            return io.StringIO(
                input_json
            )

        if (
            self.name
            == "llm_extend_applicant_data.json"
            and "r" in mode
        ):
            return io.StringIO(
                cleaned_json
            )

        return original_open(
            self,
            mode,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        Path,
        "exists",
        fake_exists,
    )

    monkeypatch.setattr(
        Path,
        "open",
        fake_open,
    )

    runpy.run_path(
        clean.__file__,
        run_name="__main__",
    )

    output = capsys.readouterr().out

    assert (
        "All records are already cleaned."
        in output
    )