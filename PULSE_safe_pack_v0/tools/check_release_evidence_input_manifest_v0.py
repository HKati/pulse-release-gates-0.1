#!/usr/bin/env python3
"""Check release_evidence_input_manifest_v0 schema and relation integrity.

This checker validates a future verifier input manifest.

It is not the verifier.
It does not verify evidence.
It does not materialize gates.
It does not write status.json.
It does not replace check_gates.py.
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
    REPO_ROOT / "schemas" / "release_evidence_input_manifest_v0.schema.json"
)


def _reject_duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON object key: {key}")
        seen.add(key)
        out[key] = value
    return out


def _json_path(parts: Any) -> str:
    items = [str(part) for part in parts]
    return ".".join(items) if items else "<root>"


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        errors.append(f"{label} not found: {path}")
        return None

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_object_pairs,
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label} is not valid JSON: {exc}")
        return None

    if not isinstance(payload, dict):
        errors.append(f"{label} must be a JSON object: {path}")
        return None

    return payload


def _validate_schema(
    manifest: dict[str, Any],
    *,
    schema_path: Path,
    errors: list[str],
) -> None:
    schema = _load_json(schema_path, "release_evidence_input_manifest_v0 schema", errors)
    if schema is None:
        return

    if jsonschema is None:
        errors.append(
            "jsonschema is required for "
            "release_evidence_input_manifest_v0 schema validation; "
            "partial fallback validation is not allowed"
        )
        return

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"release_evidence_input_manifest_v0 schema is invalid: {exc}")
        return

    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(manifest), key=lambda item: list(item.path)):
        errors.append(
            f"schema validation error at {_json_path(error.path)}: {error.message}"
        )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check_integrity(manifest: dict[str, Any], errors: list[str]) -> None:
    candidate_evidence = _as_dict(manifest.get("candidate_evidence"))
    relation_bindings = _as_dict(manifest.get("expected_relation_bindings"))
    gate_materialization = _as_dict(manifest.get("expected_gate_materialization"))

    for relation_id, relation in relation_bindings.items():
        if not isinstance(relation, dict):
            errors.append(f"expected_relation_bindings.{relation_id} must be an object")
            continue

        source_evidence_id = relation.get("source_evidence_id")
        if source_evidence_id not in candidate_evidence:
            errors.append(
                f"expected_relation_bindings.{relation_id}.source_evidence_id "
                f"references missing candidate evidence: {source_evidence_id}"
            )

        expected_gate_id = relation.get("expected_gate_id")
        if expected_gate_id is not None and expected_gate_id not in gate_materialization:
            errors.append(
                f"expected_relation_bindings.{relation_id}.expected_gate_id "
                f"references missing expected gate: {expected_gate_id}"
            )

    for gate_id, gate in gate_materialization.items():
        if not isinstance(gate, dict):
            errors.append(f"expected_gate_materialization.{gate_id} must be an object")
            continue

        candidate_ids = gate.get("candidate_evidence_ids")
        if not isinstance(candidate_ids, list) or not candidate_ids:
            errors.append(
                f"expected_gate_materialization.{gate_id}.candidate_evidence_ids "
                "must be a non-empty array"
            )
        else:
            for evidence_id in candidate_ids:
                if evidence_id not in candidate_evidence:
                    errors.append(
                        f"expected_gate_materialization.{gate_id}.candidate_evidence_ids "
                        f"references missing candidate evidence: {evidence_id}"
                    )

        relation_ids = gate.get("relation_binding_ids")
        if not isinstance(relation_ids, list) or not relation_ids:
            errors.append(
                f"expected_gate_materialization.{gate_id}.relation_binding_ids "
                "must be a non-empty array"
            )
        else:
            seen_relations: set[str] = set()
            for relation_id in relation_ids:
                if relation_id in seen_relations:
                    errors.append(
                        f"expected_gate_materialization.{gate_id}.relation_binding_ids "
                        f"contains duplicate relation reference: {relation_id}"
                    )
                    continue

                seen_relations.add(str(relation_id))

                if relation_id not in relation_bindings:
                    errors.append(
                        f"expected_gate_materialization.{gate_id}.relation_binding_ids "
                        f"references missing expected relation: {relation_id}"
                    )


def check_release_evidence_input_manifest(
    manifest_path: Path,
    *,
    schema_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []

    manifest = _load_json(manifest_path, "release_evidence_input_manifest_v0", errors)
    if manifest is None:
        return errors

    _validate_schema(
        manifest,
        schema_path=schema_path or DEFAULT_SCHEMA_PATH,
        errors=errors,
    )
    _check_integrity(manifest, errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check release_evidence_input_manifest_v0 integrity."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to release_evidence_input_manifest_v0.json",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to release_evidence_input_manifest_v0 JSON schema.",
    )

    args = parser.parse_args()

    errors = check_release_evidence_input_manifest(
        Path(args.manifest),
        schema_path=Path(args.schema),
    )

    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("OK: release evidence input manifest integrity satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
