#!/usr/bin/env python3
"""Build recognition_surface_drift_v0 diagnostic artifacts.

This builder does not run an AI model.

It materializes a diagnostic artifact from structured analysis-run summaries:
- normative artifact basis;
- recognition surfaces;
- mechanism-first and recognition-surface analysis runs.

The produced artifact is non-normative.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "recognition_surface_drift_v0"
AUTHORITY_STATUS = "diagnostic_non_normative"
INVARIANT = (
    "non_normative_recognition_surfaces_must_not_override_"
    "normative_artifact_inspection"
)


def _load_json_object(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(obj, dict):
        raise ValueError(f"{path} must contain a JSON object")

    return obj


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _claims(run: dict[str, Any]) -> list[str]:
    value = run.get("claims", [])

    if not isinstance(value, list):
        return []

    return [str(item) for item in value]


def _normative_path(run: dict[str, Any]) -> str | None:
    value = run.get("normative_path")

    if isinstance(value, str) and value:
        return value

    value = run.get("normative_path_claim")

    if isinstance(value, str) and value:
        return value

    return None


def _find_mechanism_first_run(
    analysis_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    for run in analysis_runs:
        if run.get("condition") == "mechanism_first":
            return run

    raise ValueError("analysis_runs must include a mechanism_first baseline run")


def _compute_drift(
    analysis_runs: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    baseline = _find_mechanism_first_run(analysis_runs)
    variants = [run for run in analysis_runs if run is not baseline]

    if not variants:
        raise ValueError("analysis_runs must include at least one non-baseline run")

    baseline_classification = baseline.get("system_classification")
    baseline_authority_basis = baseline.get("authority_basis")
    baseline_claims = _claims(baseline)
    baseline_normative_path = _normative_path(baseline)

    identity_classification_changed = any(
        run.get("system_classification") != baseline_classification
        for run in variants
    )

    authority_boundary_changed = any(
        run.get("authority_basis") != baseline_authority_basis
        for run in variants
    )

    if baseline_normative_path is not None:
        normative_path_changed = any(
            _normative_path(run) != baseline_normative_path
            for run in variants
        )
    else:
        normative_path_changed = any(
            run.get("authority_basis") in ("recognition_surface", "mixed")
            for run in variants
        )

    mechanical_claims_changed = any(
        _claims(run) != baseline_claims
        for run in variants
    )

    changed_dimensions = [
        identity_classification_changed,
        authority_boundary_changed,
        normative_path_changed,
        mechanical_claims_changed,
    ]

    drift_score = sum(1 for item in changed_dimensions if item) / len(changed_dimensions)

    if drift_score == 0:
        result = "stable"
    elif drift_score >= 0.5:
        result = "contaminated"
    else:
        result = "unstable"

    drift = {
        "identity_classification_changed": identity_classification_changed,
        "authority_boundary_changed": authority_boundary_changed,
        "normative_path_changed": normative_path_changed,
        "mechanical_claims_changed": mechanical_claims_changed,
        "drift_score": drift_score,
    }

    return drift, result


def _require_list(name: str, value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")

    if not value:
        raise ValueError(f"{name} must not be empty")

    out: list[dict[str, Any]] = []

    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{name}[{index}] must be an object")
        out.append(item)

    return out


def build(input_obj: dict[str, Any]) -> dict[str, Any]:
    normative_artifact_basis = _require_list(
        "normative_artifact_basis",
        input_obj.get("normative_artifact_basis"),
    )
    recognition_surfaces = _require_list(
        "recognition_surfaces",
        input_obj.get("recognition_surfaces"),
    )
    analysis_runs = _require_list(
        "analysis_runs",
        input_obj.get("analysis_runs"),
    )

    drift, result = _compute_drift(analysis_runs)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "authority_status": AUTHORITY_STATUS,
        "invariant": INVARIANT,
        "normative_artifact_basis": normative_artifact_basis,
        "recognition_surfaces": recognition_surfaces,
        "analysis_runs": analysis_runs,
        "drift": drift,
        "result": result,
    }

    notes = input_obj.get("notes")
    if isinstance(notes, str) and notes:
        out["notes"] = notes

    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a recognition_surface_drift_v0 diagnostic artifact."
    )
    parser.add_argument("--input", required=True, help="Input bundle JSON.")
    parser.add_argument("--out", required=True, help="Output diagnostic JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        input_obj = _load_json_object(Path(args.input))
        output_obj = build(input_obj)
        _write_json(Path(args.out), output_obj)
    except Exception as exc:
        print(f"::error::failed to build recognition_surface_drift_v0: {exc}")
        return 1

    print(f"OK: wrote recognition_surface_drift_v0 artifact: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
