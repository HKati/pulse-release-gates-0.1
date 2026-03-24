#!/usr/bin/env python3
"""
Smoke / regression test for the Q1 reference groundedness summary runner.

This test is intentionally:
- artifact-first
- self-contained
- runnable as a standalone script
- compatible with pytest discovery

It locks down:
1. a passing deterministic summary build
2. deterministic created_utc resolution from SOURCE_DATE_EPOCH
3. fail-closed behavior on insufficient eligible evidence
4. fail-closed behavior on invalid labels
5. fail-closed behavior when no stable created_utc source is available
6. schema conformance of emitted summary artefacts
"""

from __future__ import annotations

import json
import os
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
                candidate / "PULSE_safe_pack_v0" / "tools" / "build_q1_reference_summary.py"
            ).is_file() and (
                candidate / "schemas" / "metrics" / "q1_groundedness_summary_v0.schema.json"
            ).is_file():
                return candidate

    raise RuntimeError(
        "Could not locate repo root containing the Q1 runner and schema"
    )


ROOT = _find_repo_root()
RUNNER = ROOT / "PULSE_safe_pack_v0" / "tools" / "build_q1_reference_summary.py"
SCHEMA = ROOT / "schemas" / "metrics" / "q1_groundedness_summary_v0.schema.json"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def _run_runner(
    rows: list[dict],
    *,
    created_utc: str | None = "2026-03-09T20:00:00Z",
    source_date_epoch: str | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict | None]:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        labels_path = td / "labels.jsonl"
        out_path = td / "q1_summary.json"
        manifest_path = td / "input_manifest.json"

        _write_jsonl(labels_path, rows)
        manifest_path.write_text(
            json.dumps({"dataset": "q1-reference-fixture"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        if source_date_epoch is None:
            env.pop("SOURCE_DATE_EPOCH", None)
        else:
            env["SOURCE_DATE_EPOCH"] = source_date_epoch

        cmd = [
            sys.executable,
            str(RUNNER),
            "--labels_jsonl",
            str(labels_path),
            "--out",
            str(out_path),
            "--input_manifest",
            str(manifest_path),
            "--run_id",
            "q1-ref-test",
            "--tool",
            "PULSE_q1_reference",
            "--tool_version",
            "0.1.0-test",
            "--git_sha",
            "deadbeef",
        ]

        if created_utc is not None:
            cmd.extend(["--created_utc", created_utc])

        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )

        summary = None
        if out_path.is_file():
            summary = json.loads(out_path.read_text(encoding="utf-8"))

        return proc, summary


def test_builds_passing_summary_and_matches_schema() -> None:
    schema = _load_schema()

    rows = (
        [{"label": "SUPPORTED"} for _ in range(175)]
        + [{"label": "ABSTAIN"} for _ in range(15)]
        + [{"label": "UNSUPPORTED"} for _ in range(5)]
        + [{"label": "UNKNOWN"} for _ in range(5)]
        + [{"label": "SUPPORTED", "eligible": False} for _ in range(3)]
    )

    proc, summary = _run_runner(rows, created_utc="2026-03-09T20:00:00Z")

    if proc.returncode != 0:
        raise AssertionError(
            f"Runner returned non-zero exit code: {proc.returncode}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}\n"
        )
    if summary is None:
        raise AssertionError("Runner did not emit an output summary artefact")

    jsonschema.validate(instance=summary, schema=schema)

    assert summary["spec_id"] == "q1_groundedness_v0"
    assert summary["spec_version"] == "0.1.0"
    assert summary["run_id"] == "q1-ref-test"
    assert summary["created_utc"] == "2026-03-09T20:00:00Z"

    assert summary["n"] == 200
    assert abs(summary["score"] - 0.95) < 1e-12
    assert abs(summary["threshold"] - 0.85) < 1e-12
    assert summary["pass"] is True

    assert summary["primary_metric_id"] == "grounded_rate"
    assert summary["pass_basis"] == "wilson_lower_bound"
    assert abs(summary["alpha"] - 0.05) < 1e-12
    assert summary["min_n_eligible"] == 100
    assert summary["insufficient_evidence"] is False

    assert summary["method"]["kind"] == "reference"
    assert summary["method"]["deterministic"] is True

    assert summary["provenance"]["tool"] == "PULSE_q1_reference"
    assert summary["provenance"]["tool_version"] == "0.1.0-test"
    assert summary["provenance"]["git_sha"] == "deadbeef"
    assert str(summary["provenance"]["input_manifest"]).endswith("input_manifest.json")
    assert str(summary["provenance"]["labels_jsonl"]).endswith("labels.jsonl")

    counts = summary["counts"]
    assert counts["SUPPORTED"] == 175
    assert counts["ABSTAIN"] == 15
    assert counts["UNSUPPORTED"] == 5
    assert counts["UNKNOWN"] == 5
    assert counts["n_total"] == 203
    assert counts["n_eligible"] == 200
    assert counts["n_excluded"] == 3

    # Sanity bounds for Wilson lower bound
    assert 0.85 <= summary["wilson_lower_bound"] <= summary["score"]


def test_uses_source_date_epoch_when_created_utc_is_omitted() -> None:
    schema = _load_schema()

    rows = [{"label": "SUPPORTED"} for _ in range(100)]

    proc, summary = _run_runner(
        rows,
        created_utc=None,
        source_date_epoch="0",
    )

    if proc.returncode != 0:
        raise AssertionError(
            f"Runner returned non-zero exit code: {proc.returncode}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}\n"
        )
    if summary is None:
        raise AssertionError("Runner did not emit an output summary artefact")

    jsonschema.validate(instance=summary, schema=schema)

    assert summary["created_utc"] == "1970-01-01T00:00:00Z"
    assert summary["n"] == 100
    assert abs(summary["score"] - 1.0) < 1e-12
    assert summary["insufficient_evidence"] is False
    assert summary["pass"] is True


def test_fails_closed_on_insufficient_evidence() -> None:
    schema = _load_schema()

    rows = [{"label": "SUPPORTED"} for _ in range(99)]

    proc, summary = _run_runner(rows, created_utc="2026-03-09T20:00:00Z")

    if proc.returncode != 0:
        raise AssertionError(
            f"Runner returned non-zero exit code: {proc.returncode}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}\n"
        )
    if summary is None:
        raise AssertionError("Runner did not emit an output summary artefact")

    jsonschema.validate(instance=summary, schema=schema)

    assert summary["n"] == 99
    assert abs(summary["score"] - 1.0) < 1e-12
    assert summary["insufficient_evidence"] is True
    assert summary["pass"] is False
    assert summary["counts"]["n_eligible"] == 99
    assert summary["counts"]["SUPPORTED"] == 99


def test_fails_on_invalid_label() -> None:
    rows = [
        {"label": "SUPPORTED"},
        {"label": "BROKEN_LABEL"},
    ]

    proc, summary = _run_runner(rows, created_utc="2026-03-09T20:00:00Z")

    if proc.returncode == 0:
        raise AssertionError(
            f"Runner unexpectedly succeeded.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}\n"
        )

    if summary is not None:
        raise AssertionError("Runner emitted an output artefact despite invalid input")

    stderr = proc.stderr or ""
    if "invalid label" not in stderr and "BROKEN_LABEL" not in stderr:
        raise AssertionError(
            f"Expected invalid-label failure in stderr.\nSTDERR:\n{stderr}\n"
        )


def test_fails_when_no_stable_created_utc_source_is_available() -> None:
    rows = [{"label": "SUPPORTED"} for _ in range(100)]

    proc, summary = _run_runner(
        rows,
        created_utc=None,
        source_date_epoch=None,
    )

    if proc.returncode == 0:
        raise AssertionError(
            f"Runner unexpectedly succeeded without a stable timestamp source.\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}\n"
        )

    if summary is not None:
        raise AssertionError(
            "Runner emitted an output artefact despite missing created_utc and SOURCE_DATE_EPOCH"
        )

    stderr = proc.stderr or ""
    if "created_utc" not in stderr and "SOURCE_DATE_EPOCH" not in stderr:
        raise AssertionError(
            f"Expected deterministic-timestamp failure in stderr.\nSTDERR:\n{stderr}\n"
        )


def main() -> int:
    try:
        test_builds_passing_summary_and_matches_schema()
        test_uses_source_date_epoch_when_created_utc_is_omitted()
        test_fails_closed_on_insufficient_evidence()
        test_fails_on_invalid_label()
        test_fails_when_no_stable_created_utc_source_is_available()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1

    print("OK: Q1 reference summary runner smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
