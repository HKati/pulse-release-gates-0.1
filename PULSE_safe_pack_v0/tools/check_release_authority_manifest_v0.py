#!/usr/bin/env python3
"""Validate a PULSE release_authority_v0.json audit manifest.

This checker validates both:

1. JSON Schema shape, using schemas/release_authority_v0.schema.json.
2. Minimal semantic consistency for the fail-closed release-authority chain.

It does not compute a new release decision.
It does not change gate policy, status.json semantics, CI behavior, or
shadow-layer authority.
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


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI should report parse errors clearly
        raise ValueError(f"failed to read JSON from {path}: {exc}") from exc


def _schema_validate(manifest: Any, schema_path: Path) -> list[str]:
    try:
        import jsonschema
    except Exception as exc:  # noqa: BLE001
        return [f"jsonschema is required for schema validation: {exc}"]

    try:
        schema = _load_json(schema_path)
    except ValueError as exc:
        return [str(exc)]

    validator_cls = jsonschema.Draft202012Validator

    try:
        validator_cls.check_schema(schema)
    except Exception as exc:  # noqa: BLE001
        return [f"invalid release authority schema {schema_path}: {exc}"]

    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))

    out: list[str] = []
    for err in errors:
        path = "$"
        if err.path:
            path += "." + ".".join(str(p) for p in err.path)
        out.append(f"{path}: {err.message}")

    return out


def _as_set(value: Any, label: str, errors: list[str]) -> set[str]:
    if value is None:
        return set()
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return set()

    out: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item:
            errors.append(f"{label} contains a non-string or empty gate id: {item!r}")
            continue
        out.add(item)

    return out


def _object_section(manifest: dict[str, Any], name: str, errors: list[str]) -> dict[str, Any]:
    """Return a top-level object section or record a validation error.

    Schema validation already rejects non-object sections, but semantic validation
    must not crash before the checker can report normal fail-closed errors.
    """
    if name not in manifest or manifest.get(name) is None:
        return {}

    value = manifest.get(name)
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return {}

    return value


def _semantic_validate(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    authority = _object_section(manifest, "authority", errors)
    evaluation = _object_section(manifest, "evaluation", errors)
    decision = _object_section(manifest, "decision", errors)
    diagnostics = _object_section(manifest, "diagnostics", errors)

    required_gates = _as_set(
        authority.get("effective_required_gates"),
        "authority.effective_required_gates",
        errors,
    )

    results_raw = evaluation.get("required_gate_results") or {}
    if not isinstance(results_raw, dict):
        errors.append("evaluation.required_gate_results must be an object")
        results: dict[str, Any] = {}
    else:
        results = dict(results_raw)

    failed = _as_set(
        evaluation.get("failed_required_gates"),
        "evaluation.failed_required_gates",
        errors,
    )
    missing = _as_set(
        evaluation.get("missing_required_gates"),
        "evaluation.missing_required_gates",
        errors,
    )

    result_gates = set(results)

    # Required-gate result keys should not introduce gates outside the
    # workflow-effective required set.
    extra_result_gates = sorted(result_gates - required_gates)
    if extra_result_gates:
        errors.append(
            "evaluation.required_gate_results contains gates outside "
            f"authority.effective_required_gates: {extra_result_gates}"
        )

    extra_failed = sorted(failed - required_gates)
    if extra_failed:
        errors.append(
            "evaluation.failed_required_gates contains gates outside "
            f"authority.effective_required_gates: {extra_failed}"
        )

    extra_missing = sorted(missing - required_gates)
    if extra_missing:
        errors.append(
            "evaluation.missing_required_gates contains gates outside "
            f"authority.effective_required_gates: {extra_missing}"
        )

    overlap_failed_missing = sorted(failed & missing)
    if overlap_failed_missing:
        errors.append(
            "gates cannot be both failed and missing: "
            f"{overlap_failed_missing}"
        )

    for gate in sorted(required_gates):
        if gate not in results:
            if gate not in missing:
                errors.append(
                    f"required gate {gate!r} is absent from required_gate_results "
                    "but not listed in missing_required_gates"
                )
            continue

        value = results[gate]
        if value is True:
            if gate in failed:
                errors.append(
                    f"required gate {gate!r} is true but listed in failed_required_gates"
                )
            if gate in missing:
                errors.append(
                    f"required gate {gate!r} is present but listed in missing_required_gates"
                )
        elif value is False:
            if gate not in failed:
                errors.append(
                    f"required gate {gate!r} is false but not listed in failed_required_gates"
                )
            if gate in missing:
                errors.append(
                    f"required gate {gate!r} is false and must not be listed as missing"
                )
        else:
            # Schema should already reject this, but keep the semantic error explicit.
            errors.append(
                f"required gate {gate!r} has non-boolean result {value!r}"
            )

    state = decision.get("state")
    if (failed or missing) and state != "FAIL":
        errors.append(
            "decision.state must be FAIL when failed_required_gates or "
            "missing_required_gates is non-empty"
        )

    if decision and decision.get("fail_closed") is not True:
        errors.append("decision.fail_closed must be true")

    if diagnostics:
        if diagnostics.get("shadow_surfaces_non_normative") is not True:
            errors.append(
                "diagnostics.shadow_surfaces_non_normative must be true when diagnostics is present"
            )

        for field in ("shadow_surfaces_present", "publication_surfaces_present"):
            surfaces = diagnostics.get(field) or []
            if not isinstance(surfaces, list):
                errors.append(f"diagnostics.{field} must be an array")
                continue

            for idx, surface in enumerate(surfaces):
                if not isinstance(surface, dict):
                    errors.append(f"diagnostics.{field}[{idx}] must be an object")
                    continue
                if surface.get("normative") is True:
                    errors.append(
                        f"diagnostics.{field}[{idx}] must not be normative by default"
                    )

    return errors

def validate_manifest(manifest_path: Path, schema_path: Path) -> list[str]:
    try:
        manifest = _load_json(manifest_path)
    except ValueError as exc:
        return [str(exc)]

    schema_errors = _schema_validate(manifest, schema_path)
    semantic_errors: list[str] = []

    if isinstance(manifest, dict):
        semantic_errors = _semantic_validate(manifest)
    else:
        semantic_errors.append("manifest must be a JSON object")

    return schema_errors + semantic_errors


def main(argv: list[str] | None = None) -> int:
    root = _repo_root_from_tool()

    parser = argparse.ArgumentParser(
        description="Validate release_authority_v0.json manifest shape and consistency."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to release_authority_v0.json or a fixture.",
    )
    parser.add_argument(
        "--schema",
        default=str(root / "schemas" / "release_authority_v0.schema.json"),
        help="Path to release_authority_v0.schema.json.",
    )

    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    schema_path = Path(args.schema)

    errors = validate_manifest(manifest_path, schema_path)

    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK: release authority manifest is valid: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
