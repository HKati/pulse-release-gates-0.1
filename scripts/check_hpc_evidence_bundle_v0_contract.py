#!/usr/bin/env python3
"""Contract checker for hpc_evidence_bundle_v0 diagnostic evidence bundles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "hpc_evidence_bundle_v0.schema.json"


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(obj, dict):
        raise ValueError(f"{path} must contain a JSON object")

    return obj


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _schema_errors(instance: dict[str, Any]) -> list[str]:
    schema = _load_json(SCHEMA_PATH)
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

    if instance.get("authority_status") != "diagnostic_non_normative":
        errors.append("authority_status must be diagnostic_non_normative")

    if instance.get("creates_release_authority") is not False:
        errors.append("creates_release_authority must be false")

    result = instance.get("result")
    evidence_items = instance.get("evidence_items")

    if not isinstance(evidence_items, list):
        return errors

    item_statuses: list[str] = []

    for index, item in enumerate(evidence_items):
        if not isinstance(item, dict):
            errors.append(f"evidence_items[{index}] must be an object")
            continue

        status = item.get("evidence_status")
        item_statuses.append(str(status))

        sha256 = item.get("sha256")

        if status == "present" and not _is_sha256(sha256):
            errors.append(
                f"evidence_items[{index}] is present but has no valid sha256 digest"
            )

        if item.get("folded_into_status") is True:
            if status != "present":
                errors.append(
                    f"evidence_items[{index}] is folded into status but is not present"
                )

            policy_route = item.get("policy_route")
            if not isinstance(policy_route, dict):
                errors.append(
                    f"evidence_items[{index}] is folded into status but lacks policy_route"
                )
            else:
                if not policy_route.get("policy_path"):
                    errors.append(
                        f"evidence_items[{index}].policy_route.policy_path is required"
                    )
                if not policy_route.get("gate_id"):
                    errors.append(
                        f"evidence_items[{index}].policy_route.gate_id is required"
                    )

    if result == "complete":
        for index, item in enumerate(evidence_items):
            if isinstance(item, dict) and item.get("evidence_status") != "present":
                errors.append(
                    f"complete bundle cannot contain non-present evidence item at index {index}"
                )

    if result == "incomplete":
        if all(status == "present" for status in item_statuses):
            errors.append("incomplete bundle must contain at least one non-present evidence item")

    return errors


def check(path: Path) -> tuple[bool, list[str]]:
    instance = _load_json(path)
    errors = _schema_errors(instance)
    errors.extend(_semantic_errors(instance))
    return errors == [], errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an hpc_evidence_bundle_v0 artifact."
    )
    parser.add_argument("--in", dest="input_path", required=True)
    args = parser.parse_args()

    path = Path(args.input_path)

    try:
        ok, errors = check(path)
    except Exception as exc:
        print(f"::error::failed to check hpc_evidence_bundle_v0: {exc}")
        return 1

    if not ok:
        print("::error::hpc_evidence_bundle_v0 contract failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"OK: hpc_evidence_bundle_v0 contract valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
