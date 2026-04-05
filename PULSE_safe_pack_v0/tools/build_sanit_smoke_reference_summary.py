#!/usr/bin/env python3
"""
Build a deterministic sanit-smoke reference summary from a checked-in archived
result artifact.

This builder is intended for artifact-first Core/reference materialization.
It reads a single archived sanit-smoke result JSON and produces a stable
summary JSON that downstream schema/tests/run_all wiring can consume.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CANONICAL_SUCCESS_STATUSES = {"completed", "succeeded"}

PASS_CONTROLS_SANIT_BASIS = (
    "status_completed_or_succeeded_and_zero_failures_and_zero_errors"
)
SANITIZATION_EFFECTIVE_BASIS = (
    "pass_controls_sanit_true_and_source_sanitization_effective_true"
)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build a deterministic sanit-smoke reference summary."
    )
    p.add_argument("--result_json", required=True, help="Archived sanit-smoke result JSON")
    p.add_argument("--out", required=True, help="Output summary JSON path")
    p.add_argument("--input_manifest", required=True, help="Checked-in input manifest path")
    p.add_argument("--run_id", required=True, help="Run identifier to stamp into the summary")
    p.add_argument("--created_utc", required=True, help="Created UTC timestamp")
    p.add_argument("--tool", required=True, help="Tool name recorded in provenance")
    p.add_argument("--tool_version", required=True, help="Tool version recorded in provenance")
    p.add_argument("--git_sha", default="", help="Optional git SHA recorded in provenance")
    p.add_argument("--notes", default="", help="Optional human note recorded in summary")
    return p


def _read_json_object(path: Path, *, parser: argparse.ArgumentParser, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        parser.error(f"{label} does not exist: {path}")
    except OSError as exc:
        parser.error(f"{label} is not readable: {path} ({exc})")
    except json.JSONDecodeError as exc:
        parser.error(f"{label} is not valid JSON: {path} ({exc})")

    if not isinstance(payload, dict):
        parser.error(f"{label} must be a JSON object: {path}")

    return payload


def _require_non_negative_int(
    value: Any,
    *,
    parser: argparse.ArgumentParser,
    label: str,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        parser.error(f"{label} must be an integer")
    if value < 0:
        parser.error(f"{label} must be >= 0")
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = _parser()
    args = parser.parse_args()

    result_path = Path(args.result_json)
    out_path = Path(args.out)

    source = _read_json_object(
        result_path,
        parser=parser,
        label="--result_json",
    )

    source_status = source.get("status")
    if not isinstance(source_status, str) or not source_status.strip():
        parser.error("source result missing non-empty string field: status")
    source_status = source_status.strip()

    result_counts = source.get("result_counts")
    if not isinstance(result_counts, dict):
        parser.error("source result missing object field: result_counts")

    total = _require_non_negative_int(
        result_counts.get("total"),
        parser=parser,
        label="result_counts.total",
    )
    passed = _require_non_negative_int(
        result_counts.get("passed"),
        parser=parser,
        label="result_counts.passed",
    )
    failed = _require_non_negative_int(
        result_counts.get("failed"),
        parser=parser,
        label="result_counts.failed",
    )
    errored = _require_non_negative_int(
        result_counts.get("errored"),
        parser=parser,
        label="result_counts.errored",
    )

    counts_consistent = (passed + failed + errored) == total
    insufficient_evidence = total == 0
    status_ok = source_status in CANONICAL_SUCCESS_STATUSES

    source_sanitization_effective = source.get("sanitization_effective")
    if isinstance(source_sanitization_effective, bool):
        sanitization_effective_input = source_sanitization_effective
    else:
        sanitization_effective_input = False

    pass_controls_sanit = (
        status_ok
        and not insufficient_evidence
        and counts_consistent
        and failed == 0
        and errored == 0
    )

    sanitization_effective = bool(
        pass_controls_sanit and sanitization_effective_input is True
    )

    summary: dict[str, Any] = {
        "spec_id": "sanit_smoke_reference_v0",
        "spec_version": "0.1.0",
        "run_id": args.run_id,
        "created_utc": args.created_utc,
        "source_status": source_status,
        "status_ok": status_ok,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "insufficient_evidence": insufficient_evidence,
        "counts_consistent": counts_consistent,
        "pass_controls_sanit": pass_controls_sanit,
        "pass_controls_sanit_basis": PASS_CONTROLS_SANIT_BASIS,
        "sanitization_effective": sanitization_effective,
        "sanitization_effective_basis": SANITIZATION_EFFECTIVE_BASIS,
        "primary_metric_id": "pass_controls_sanit",
        "secondary_metric_id": "sanitization_effective",
        "source_result": {
            "status": source_status,
            "result_counts": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "errored": errored,
            },
            "sanitization_effective": sanitization_effective_input,
        },
        "method": {
            "kind": "reference",
            "deterministic": True,
            "notes": "Reducer over archived sanit-smoke result artefacts.",
        },
        "provenance": {
            "input_manifest": args.input_manifest,
            "result_json": args.result_json,
            "tool": args.tool,
            "tool_version": args.tool_version,
        },
        "decision_rule": [
            "Read an archived sanit_smoke_result.json artefact.",
            "Require exact status token in {completed, succeeded}.",
            "Require total > 0.",
            "Require failed == 0 and errored == 0.",
            "Require result_counts consistency.",
            "Set pass_controls_sanit true iff all sanit control conditions hold.",
            "Set sanitization_effective true iff pass_controls_sanit is true and source sanitization_effective is true.",
        ],
    }

    git_sha = str(args.git_sha).strip()
    if git_sha:
        summary["provenance"]["git_sha"] = git_sha

    notes = str(args.notes).strip()
    if notes:
        summary["notes"] = notes

    _write_json(out_path, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
