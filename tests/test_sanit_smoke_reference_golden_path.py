#!/usr/bin/env python3
"""Golden-path smoke test for the checked-in sanit reference artefacts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import jsonschema


def _find_repo_root() -> Path:
    starts = []
    try:
        starts.append(Path(__file__).resolve().parent)
    except NameError:
        pass
    starts.append(Path.cwd().resolve())

    seen = set()
    for start in starts:
        for candidate in (start, *start.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            if (
                (candidate / "PULSE_safe_pack_v0" / "tools" / "build_sanit_smoke_reference_summary.py").is_file()
                and (candidate / "schemas" / "metrics" / "sanit_smoke_reference_summary_v0.schema.json").is_file()
                and (candidate / "examples" / "sanit_smoke_input_manifest.json").is_file()
                and (candidate / "examples" / "sanit_smoke_result.pass_v0.json").is_file()
                and (candidate / "examples" / "sanit_smoke_summary.example.json").is_file()
            ):
                return candidate
    raise RuntimeError("Could not locate repo root containing the sanit reference artefacts")


ROOT = _find_repo_root()
RUNNER = ROOT / "PULSE_safe_pack_v0" / "tools" / "build_sanit_smoke_reference_summary.py"
SCHEMA = ROOT / "schemas" / "metrics" / "sanit_smoke_reference_summary_v0.schema.json"
MANIFEST = ROOT / "examples" / "sanit_smoke_input_manifest.json"
RESULT = ROOT / "examples" / "sanit_smoke_result.pass_v0.json"
EXAMPLE = ROOT / "examples" / "sanit_smoke_summary.example.json"

MANIFEST_REL = "examples/sanit_smoke_input_manifest.json"
RESULT_REL = "examples/sanit_smoke_result.pass_v0.json"

RUN_ID = "sanit-ref-2026-04-05T20:30:00Z"
CREATED_UTC = "2026-04-05T20:30:00Z"
TOOL = "PULSE_sanit_reference"
TOOL_VERSION = "0.1.0-dev"
GIT_SHA = "example-sanit-ref"
NOTES = "Minimal example artefact for schema consumers and tests."


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pretty_json(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def _run_runner() -> tuple[subprocess.CompletedProcess[str], dict | None]:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "sanit_reference_summary.json"
        cmd = [
            sys.executable,
            str(RUNNER),
            "--result_json",
            RESULT_REL,
            "--out",
            str(out_path),
            "--input_manifest",
            MANIFEST_REL,
            "--run_id",
            RUN_ID,
            "--created_utc",
            CREATED_UTC,
            "--tool",
            TOOL,
            "--tool_version",
            TOOL_VERSION,
            "--git_sha",
            GIT_SHA,
            "--notes",
            NOTES,
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        summary = None
        if out_path.is_file():
            summary = _load_json(out_path)
        return proc, summary


def test_checked_in_sanit_summary_example_matches_schema() -> None:
    schema = _load_json(SCHEMA)
    example = _load_json(EXAMPLE)

    jsonschema.validate(instance=example, schema=schema)

    assert example["spec_id"] == "sanit_smoke_reference_v0"
    assert example["spec_version"] == "0.1.0"
    assert example["run_id"] == RUN_ID
    assert example["created_utc"] == CREATED_UTC
    assert example["primary_metric_id"] == "pass_controls_sanit"
    assert example["secondary_metric_id"] == "sanitization_effective"
    assert example["pass_controls_sanit"] is True
    assert example["sanitization_effective"] is True
    assert example["source_status"] == "completed"
    assert example["provenance"]["input_manifest"] == MANIFEST_REL
    assert example["provenance"]["result_json"] == RESULT_REL
    assert example["provenance"]["tool"] == TOOL
    assert example["provenance"]["tool_version"] == TOOL_VERSION
    assert example["provenance"]["git_sha"] == GIT_SHA


def test_runner_reproduces_checked_in_sanit_summary_example() -> None:
    schema = _load_json(SCHEMA)
    expected = _load_json(EXAMPLE)

    proc, actual = _run_runner()

    if proc.returncode != 0:
        raise AssertionError(
            f"Runner returned non-zero exit code: {proc.returncode}\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}\n"
        )

    if actual is None:
        raise AssertionError("Runner did not emit an output summary artefact")

    jsonschema.validate(instance=actual, schema=schema)

    if actual != expected:
        raise AssertionError(
            "Checked-in sanit summary example drifted from current runner output.\n\n"
            f"EXPECTED:\n{_pretty_json(expected)}\n\n"
            f"ACTUAL:\n{_pretty_json(actual)}\n"
        )


def main() -> int:
    try:
        test_checked_in_sanit_summary_example_matches_schema()
        test_runner_reproduces_checked_in_sanit_summary_example()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1

    print("OK: sanit reference golden-path smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
