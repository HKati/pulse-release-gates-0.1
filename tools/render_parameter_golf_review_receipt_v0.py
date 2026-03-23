#!/usr/bin/env python3
"""Render a shadow-only Parameter Golf review receipt from a v0 evidence artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from verify_parameter_golf_submission_v0 import (
    DEFAULT_SCHEMA,
    MissingDependencyError,
    _load_jsonschema,
    load_json,
    resolve_artifact_limit_default,
    semantic_checks,
    validate_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = Path("tools/verify_parameter_golf_submission_v0.py")


def _relativize(path: Path) -> str:
    """Return a repo-relative POSIX path when possible, else the original string."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()).as_posix())
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Parameter Golf review receipt from a v0 evidence artifact."
    )
    parser.add_argument(
        "--evidence",
        required=True,
        help="Path to the evidence JSON artifact.",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to the evidence schema JSON. Defaults to the repo-local v0 schema.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the rendered review receipt JSON.",
    )
    return parser.parse_args()


def emit_json(payload: dict[str, Any], output_path: Path | None) -> None:
    rendered = json.dumps(payload, indent=2) + "\n"
    if output_path is None:
        sys.stdout.write(rendered)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def build_validation_block(warnings: list[str]) -> dict[str, Any]:
    return {
        "valid_schema": True,
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def build_review_surface(evidence: dict[str, Any]) -> dict[str, Any]:
    artifact = evidence.get("artifact", {})
    train = evidence.get("train", {})
    evaluation = evidence.get("evaluation", {})
    stats = evidence.get("stats", {})

    total_bytes = artifact.get("total_bytes_int8_zlib")
    limit_bytes = artifact.get("artifact_limit_bytes")
    train_wallclock_s = train.get("train_wallclock_s")
    max_wallclock_s = train.get("max_wallclock_s")
    run_logs = stats.get("run_logs") or []

    artifact_within_limit: bool | None = None
    if isinstance(total_bytes, int) and isinstance(limit_bytes, int):
        artifact_within_limit = total_bytes <= limit_bytes

    train_within_declared_max: bool | None = None
    if isinstance(train_wallclock_s, (int, float)) and isinstance(max_wallclock_s, (int, float)):
        train_within_declared_max = train_wallclock_s <= max_wallclock_s

    return {
        "submission_type": evidence.get("submission_type"),
        "artifact_total_bytes_int8_zlib": total_bytes,
        "artifact_limit_bytes": limit_bytes,
        "artifact_within_limit": artifact_within_limit,
        "evaluation_mode": evaluation.get("mode"),
        "val_bpb": evaluation.get("val_bpb"),
        "train_wallclock_s": train_wallclock_s,
        "max_train_wallclock_s": max_wallclock_s,
        "train_within_declared_max": train_within_declared_max,
        "n_runs": stats.get("n_runs"),
        "run_log_count": len(run_logs) if isinstance(run_logs, list) else None,
        "p_value": stats.get("p_value"),
        "comparison_target": stats.get("comparison_target"),
    }


def build_claim_breakdown(evidence: dict[str, Any]) -> dict[str, Any]:
    artifact = evidence.get("artifact", {})
    evaluation = evidence.get("evaluation", {})
    stats = evidence.get("stats", {})

    return {
        "artifact_accounting": {
            "counted_code_bytes": artifact.get("code_bytes"),
            "compressed_model_bytes": artifact.get("model_bytes_int8_zlib"),
            "artifact_total_bytes": artifact.get("total_bytes_int8_zlib"),
            "tokenizer_counted": artifact.get("tokenizer_counted"),
            "tokenizer_bytes_if_counted": artifact.get("tokenizer_bytes_if_counted"),
        },
        "evaluation": {
            "mode": evaluation.get("mode"),
            "seq_len": evaluation.get("seq_len"),
            "stride": evaluation.get("stride"),
            "val_loss": evaluation.get("val_loss"),
            "val_bpb": evaluation.get("val_bpb"),
            "eval_wallclock_s": evaluation.get("eval_wallclock_s"),
            "roundtrip_val_loss": evaluation.get("roundtrip_val_loss"),
            "roundtrip_val_bpb": evaluation.get("roundtrip_val_bpb"),
        },
        "statistical_evidence": {
            "n_runs": stats.get("n_runs"),
            "run_logs": stats.get("run_logs"),
            "p_value": stats.get("p_value"),
            "comparison_target": stats.get("comparison_target"),
            "claim_exemption_reason": stats.get("claim_exemption_reason"),
        },
    }


def build_receipt(
    *,
    evidence_path: Path,
    schema_path: Path,
    evidence: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "receipt_version": "0.1",
        "receipt_kind": "parameter_golf_submission_review_receipt_v0",
        "generated_from": {
            "evidence_path": _relativize(evidence_path),
            "schema_path": _relativize(schema_path),
            "verifier": str(VERIFIER_PATH.as_posix()),
        },
        "validation": build_validation_block(warnings),
        "review_surface": build_review_surface(evidence),
        "claim_breakdown": build_claim_breakdown(evidence),
        "normative_boundary": {
            "shadow_only": True,
            "changes_pulse_release_outcome": False,
        },
        "notes": [
            "Generated from a v0 Parameter Golf evidence artifact.",
            "This artifact is diagnostic only and does not change PULSE release outcomes.",
        ],
    }


def build_invalid_receipt(
    *,
    evidence_path: Path,
    schema_path: Path,
    error_kind: str,
    message: str,
    path_key: str | None = None,
    path_value: list[Any] | None = None,
) -> dict[str, Any]:
    validation: dict[str, Any] = {
        "valid_schema": False,
        "warning_count": 0,
        "warnings": [],
        "error_kind": error_kind,
        "error": message,
    }
    if path_key is not None and path_value is not None:
        validation[path_key] = path_value

    return {
        "receipt_version": "0.1",
        "receipt_kind": "parameter_golf_submission_review_receipt_v0",
        "generated_from": {
            "evidence_path": _relativize(evidence_path),
            "schema_path": _relativize(schema_path),
            "verifier": str(VERIFIER_PATH.as_posix()),
        },
        "validation": validation,
        "normative_boundary": {
            "shadow_only": True,
            "changes_pulse_release_outcome": False,
        },
        "notes": [
            "Generated from a v0 Parameter Golf evidence artifact.",
            "This artifact is diagnostic only and does not change PULSE release outcomes.",
            "Invalid or unreadable evidence remains outside any normative PULSE path.",
        ],
    }


def emit_invalid_receipt_and_return(
    *,
    evidence_path: Path,
    schema_path: Path,
    output_path: Path | None,
    error_kind: str,
    message: str,
    exit_code: int = 1,
    stderr_message: str | None = None,
    path_key: str | None = None,
    path_value: list[Any] | None = None,
) -> int:
    payload = build_invalid_receipt(
        evidence_path=evidence_path,
        schema_path=schema_path,
        error_kind=error_kind,
        message=message,
        path_key=path_key,
        path_value=path_value,
    )
    emit_json(payload, output_path)
    if stderr_message is not None:
        print(stderr_message, file=sys.stderr)
    return exit_code


def main() -> int:
    args = parse_args()
    evidence_path = Path(args.evidence)
    schema_path = Path(args.schema)
    output_path = Path(args.output) if args.output else None

    try:
        evidence = load_json(evidence_path)
    except FileNotFoundError:
        return emit_invalid_receipt_and_return(
            evidence_path=evidence_path,
            schema_path=schema_path,
            output_path=output_path,
            error_kind="evidence_file_not_found",
            message=f"Evidence file not found: {evidence_path}",
            stderr_message=f"ERROR: evidence file not found: {evidence_path}",
        )
    except json.JSONDecodeError as exc:
        return emit_invalid_receipt_and_return(
            evidence_path=evidence_path,
            schema_path=schema_path,
            output_path=output_path,
            error_kind="evidence_json_decode_error",
            message=f"Invalid JSON in evidence file: {exc}",
            stderr_message=f"ERROR: invalid JSON in evidence file: {exc}",
        )

    try:
        schema = load_json(schema_path)
    except FileNotFoundError:
        return emit_invalid_receipt_and_return(
            evidence_path=evidence_path,
            schema_path=schema_path,
            output_path=output_path,
            error_kind="schema_file_not_found",
            message=f"Schema file not found: {schema_path}",
            stderr_message=f"ERROR: schema file not found: {schema_path}",
        )
    except json.JSONDecodeError as exc:
        return emit_invalid_receipt_and_return(
            evidence_path=evidence_path,
            schema_path=schema_path,
            output_path=output_path,
            error_kind="schema_json_decode_error",
            message=f"Invalid JSON in schema file: {exc}",
            stderr_message=f"ERROR: invalid JSON in schema file: {exc}",
        )

    artifact_limit_default = resolve_artifact_limit_default(schema)

    try:
        jsonschema_mod = _load_jsonschema()
    except MissingDependencyError as exc:
        return emit_invalid_receipt_and_return(
            evidence_path=evidence_path,
            schema_path=schema_path,
            output_path=output_path,
            error_kind="missing_dependency",
            message=str(exc),
            stderr_message=f"ERROR: {exc}",
            exit_code=2,
        )

    try:
        validate_schema(evidence, schema, jsonschema_mod)
    except jsonschema_mod.ValidationError as exc:
        payload = build_invalid_receipt(
            evidence_path=evidence_path,
            schema_path=schema_path,
            error_kind="validation_error",
            message=f"Schema validation failed: {exc.message}",
            path_key="path",
            path_value=list(exc.absolute_path),
        )
        emit_json(payload, output_path)
        return 1
    except jsonschema_mod.SchemaError as exc:
        payload = build_invalid_receipt(
            evidence_path=evidence_path,
            schema_path=schema_path,
            error_kind="schema_error",
            message=f"Provided schema is invalid: {exc.message}",
            path_key="schema_path",
            path_value=list(exc.absolute_schema_path),
        )
        emit_json(payload, output_path)
        return 1

    warnings = semantic_checks(
        evidence,
        artifact_limit_default=artifact_limit_default,
    )
    payload = build_receipt(
        evidence_path=evidence_path,
        schema_path=schema_path,
        evidence=evidence,
        warnings=warnings,
    )
    emit_json(payload, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
