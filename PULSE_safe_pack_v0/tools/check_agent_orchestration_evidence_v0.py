#!/usr/bin/env python3
"""Validate PULSE agent_orchestration_evidence_v0 payloads.

This checker validates diagnostic agent-orchestration proof-of-work evidence.

It checks both:

1. JSON Schema shape, using schemas/agent_orchestration_evidence_v0.schema.json.
2. Minimal semantic authority-boundary invariants.

It does not compute release authority.
It does not replace check_gates.py.
It does not change status.json, gate policy, CI behavior, or shadow-layer
authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _repo_root_from_tool() -> Path:
    # PULSE_safe_pack_v0/tools/<this file> -> repo root
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path, label: str, errors: list[str]) -> Any:
    if not path.exists():
        errors.append(f"{label} not found: {path}")
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI should report parse errors clearly
        errors.append(f"{label} is not valid JSON: {exc}")
        return None


def _schema_validate(payload: Any, schema_path: Path) -> list[str]:
    errors: list[str] = []

    try:
        import jsonschema
    except Exception as exc:  # noqa: BLE001
        return [f"jsonschema is required for schema validation: {exc}"]

    schema = _load_json(schema_path, "schema", errors)
    if errors:
        return errors

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:  # noqa: BLE001
        return [f"invalid schema {schema_path}: {exc}"]

    validator = jsonschema.Draft202012Validator(schema)
    validation_errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))

    for err in validation_errors:
        path = "$"
        if err.path:
            path += "." + ".".join(str(p) for p in err.path)
        errors.append(f"{path}: {err.message}")

    return errors


def _object_section(payload: dict[str, Any], name: str, errors: list[str]) -> dict[str, Any]:
    value = payload.get(name)
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return {}
    return value


def _semantic_validate(payload: Any) -> list[str]:
    errors: list[str] = []

    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    if payload.get("schema_version") != "agent_orchestration_evidence_v0":
        errors.append("schema_version must be agent_orchestration_evidence_v0")

    if payload.get("evidence_role") != "diagnostic":
        errors.append("evidence_role must be diagnostic")

    if payload.get("normative") is not False:
        errors.append("normative must be false")

    if payload.get("release_authority") is not False:
        errors.append("release_authority must be false")

    pulse_ingestion = _object_section(payload, "pulse_ingestion", errors)

    if pulse_ingestion:
        if pulse_ingestion.get("recommended_fold_in_target") != "status.meta.agent_work_evidence":
            errors.append(
                "pulse_ingestion.recommended_fold_in_target must be "
                "status.meta.agent_work_evidence"
            )

        if pulse_ingestion.get("gate_promotion") is not False:
            errors.append("pulse_ingestion.gate_promotion must be false")

        if pulse_ingestion.get("release_decision_claim") != "none":
            errors.append("pulse_ingestion.release_decision_claim must be none")

        authority_boundary = pulse_ingestion.get("authority_boundary")
        if not isinstance(authority_boundary, str) or not authority_boundary.strip():
            errors.append("pulse_ingestion.authority_boundary must be a non-empty string")

    return errors


def validate_payload(input_path: Path, schema_path: Path) -> list[str]:
    errors: list[str] = []

    payload = _load_json(input_path, "agent orchestration evidence payload", errors)
    if errors:
        return errors

    errors.extend(_schema_validate(payload, schema_path))
    errors.extend(_semantic_validate(payload))

    return errors


def main(argv: list[str] | None = None) -> int:
    root = _repo_root_from_tool()

    parser = argparse.ArgumentParser(
        description="Validate an agent_orchestration_evidence_v0 payload."
    )
    parser.add_argument(
        "--input",
        default=str(
            root
            / "examples"
            / "agent_orchestration_evidence_v0"
            / "symphony_work_evidence.example.json"
        ),
        help="Path to an agent_orchestration_evidence_v0 JSON payload.",
    )
    parser.add_argument(
        "--schema",
        default=str(root / "schemas" / "agent_orchestration_evidence_v0.schema.json"),
        help="Path to agent_orchestration_evidence_v0.schema.json.",
    )

    args = parser.parse_args(argv)

    errors = validate_payload(
        input_path=Path(args.input),
        schema_path=Path(args.schema),
    )

    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"OK: agent orchestration evidence payload is valid: {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
