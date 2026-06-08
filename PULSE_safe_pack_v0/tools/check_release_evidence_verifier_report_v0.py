#!/usr/bin/env python3
"""Check release_evidence_verifier_report_v0 relation integrity.

This checker validates verifier report structure and relation binding integrity.

It is not release authority.
It does not replace check_gates.py.
It does not change status.json, gate policy, CI behavior, or release semantics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except Exception:  # pragma: no cover
    jsonschema = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = (
    REPO_ROOT / "schemas" / "release_evidence_verifier_report_v0.schema.json"
)


def _json_path(parts: Any) -> str:
    items = [str(part) for part in parts]
    return ".".join(items) if items else "<root>"


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        errors.append(f"{label} not found: {path}")
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI should report parse failures
        errors.append(f"{label} is not valid JSON: {exc}")
        return None

    if not isinstance(payload, dict):
        errors.append(f"{label} must be a JSON object: {path}")
        return None

    return payload


def _validate_schema(
    report: dict[str, Any],
    *,
    schema_path: Path,
    errors: list[str],
) -> None:
    schema = _load_json(schema_path, "release_evidence_verifier_report_v0 schema", errors)
    if schema is None:
        return

    if jsonschema is None:
        required = schema.get("required")
        if isinstance(required, list):
            for key in required:
                if key not in report:
                    errors.append(f"schema validation error at <root>: {key!r} is required")

        if report.get("schema_version") != "release_evidence_verifier_report_v0":
            errors.append(
                "schema validation error at schema_version: must be "
                "'release_evidence_verifier_report_v0'"
            )

        if report.get("verifier_decision") not in {"VERIFIED", "FAILED"}:
            errors.append(
                "schema validation error at verifier_decision: must be VERIFIED or FAILED"
            )
        return

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"release_evidence_verifier_report_v0 schema is invalid: {exc}")
        return

    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(report), key=lambda item: list(item.path)):
        errors.append(
            f"schema validation error at {_json_path(error.path)}: {error.message}"
        )


def _relation_bindings(
    report: dict[str, Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    raw = report.get("relation_bindings")
    if not isinstance(raw, list):
        errors.append("report.relation_bindings must be an array")
        return {}

    by_id: dict[str, dict[str, Any]] = {}

    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"report.relation_bindings[{idx}] must be an object")
            continue

        relation_id = item.get("relation_id")
        if not isinstance(relation_id, str) or not relation_id.strip():
            errors.append(
                f"report.relation_bindings[{idx}].relation_id must be a non-empty string"
            )
            continue

        relation_id = relation_id.strip()
        if relation_id in by_id:
            errors.append(
                "duplicate relation_id in report.relation_bindings: "
                f"{relation_id}"
            )
            continue

        by_id[relation_id] = item

    return by_id


def _check_gate_relation_refs(
    report: dict[str, Any],
    relation_by_id: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    materialization = report.get("gate_materialization")
    if not isinstance(materialization, dict):
        errors.append("report.gate_materialization must be an object")
        return

    decision = report.get("verifier_decision")

    if decision == "FAILED":
        if materialization:
            errors.append("FAILED verifier reports must not materialize gates")
        return

    if decision == "VERIFIED" and not materialization:
        errors.append("VERIFIED verifier reports must materialize at least one gate")

    for gate_id, entry in materialization.items():
        if not isinstance(entry, dict):
            errors.append(f"gate_materialization.{gate_id} must be an object")
            continue

        refs = entry.get("relation_bindings")
        if not isinstance(refs, list) or not refs:
            errors.append(
                f"gate_materialization.{gate_id}.relation_bindings must be "
                "a non-empty array"
            )
            continue

        seen_refs: set[str] = set()
        for raw_ref in refs:
            if not isinstance(raw_ref, str) or not raw_ref.strip():
                errors.append(
                    f"gate_materialization.{gate_id}.relation_bindings contains "
                    "a non-empty-string violation"
                )
                continue

            relation_id = raw_ref.strip()
            if relation_id in seen_refs:
                errors.append(
                    f"gate_materialization.{gate_id}.relation_bindings contains "
                    f"duplicate relation reference: {relation_id}"
                )
                continue
            seen_refs.add(relation_id)

            relation = relation_by_id.get(relation_id)
            if relation is None:
                errors.append(
                    f"gate_materialization.{gate_id}.relation_bindings references "
                    f"missing relation_id: {relation_id}"
                )
                continue

            if relation.get("verified") is not True:
                errors.append(
                    f"gate_materialization.{gate_id}.relation_bindings references "
                    f"relation_id {relation_id} that is not verified=true"
                )


def check_release_evidence_verifier_report(
    report_path: Path,
    *,
    schema_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []

    report = _load_json(report_path, "release_evidence_verifier_report_v0", errors)
    if report is None:
        return errors

    _validate_schema(
        report,
        schema_path=schema_path or DEFAULT_SCHEMA_PATH,
        errors=errors,
    )

    relation_by_id = _relation_bindings(report, errors)
    _check_gate_relation_refs(report, relation_by_id, errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check release_evidence_verifier_report_v0 relation integrity."
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to release_evidence_verifier_report_v0.json",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to release_evidence_verifier_report_v0 JSON schema.",
    )

    args = parser.parse_args()

    errors = check_release_evidence_verifier_report(
        Path(args.report),
        schema_path=Path(args.schema),
    )

    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("OK: release evidence verifier report relation integrity satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
