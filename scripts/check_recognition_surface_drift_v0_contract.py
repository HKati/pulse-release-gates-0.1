#!/usr/bin/env python3
"""Contract check for recognition_surface_drift_v0 diagnostic artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "recognition_surface_drift_v0.schema.json"


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return obj


def _schema_errors(instance: dict[str, Any]) -> list[str]:
    schema = _load_json(SCHEMA)
    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )

    return [
        f"{list(error.absolute_path)}: {error.message}"
        for error in errors
    ]


def _semantic_errors(instance: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    recognition_surfaces = instance.get("recognition_surfaces", [])
    for idx, surface in enumerate(recognition_surfaces):
        if surface.get("authority_status") != "non_normative_recognition_surface":
            errors.append(
                f"recognition_surfaces[{idx}].authority_status must be non_normative_recognition_surface"
            )

    analysis_runs = instance.get("analysis_runs", [])
    if not any(run.get("condition") == "mechanism_first" for run in analysis_runs):
        errors.append("analysis_runs must include a mechanism_first baseline run")

    if not any(run.get("recognition_surface_available") is True for run in analysis_runs):
        errors.append("analysis_runs must include at least one recognition-surface run")

    result = instance.get("result")
    drift = instance.get("drift", {})
    changed = any(
        drift.get(key) is True
        for key in (
            "identity_classification_changed",
            "authority_boundary_changed",
            "normative_path_changed",
            "mechanical_claims_changed"
        )
    )

    if result == "stable" and changed:
        errors.append("stable result must not report changed drift dimensions")

    if result == "contaminated" and not changed:
        errors.append("contaminated result must report at least one changed drift dimension")

    if result == "stable" and drift.get("drift_score", 0) != 0:
        errors.append("stable result must have drift_score 0")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a recognition_surface_drift_v0 diagnostic artifact."
    )
    parser.add_argument("--in", dest="input_path", required=True)
    args = parser.parse_args()

    path = Path(args.input_path)

    try:
        instance = _load_json(path)
    except Exception as exc:
        print(f"::error::failed to load recognition surface drift artifact: {exc}")
        return 1

    errors = _schema_errors(instance)
    errors.extend(_semantic_errors(instance))

    if errors:
        print("::error::recognition_surface_drift_v0 contract failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"OK: recognition_surface_drift_v0 contract valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
