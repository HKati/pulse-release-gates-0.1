#!/usr/bin/env python3
"""Validate a Parameter Golf evidence artifact against the v0 shadow contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


DEFAULT_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "parameter_golf_submission_evidence_v0.schema.json"
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema(evidence: dict[str, Any], schema: dict[str, Any]) -> None:
    jsonschema.validate(instance=evidence, schema=schema)


def semantic_checks(evidence: dict[str, Any]) -> list[str]:
    warnings: list[str] = []

    artifact = evidence.get("artifact", {})
    code_bytes = artifact.get("code_bytes")
    model_bytes = artifact.get("model_bytes_int8_zlib")
    total_bytes = artifact.get("total_bytes_int8_zlib")
    limit_bytes = artifact.get("artifact_limit_bytes", 16_000_000)

    if (
        isinstance(code_bytes, int)
        and isinstance(model_bytes, int)
        and isinstance(total_bytes, int)
        and total_bytes != code_bytes + model_bytes
    ):
        warnings.append(
            "artifact.total_bytes_int8_zlib does not equal "
            "artifact.code_bytes + artifact.model_bytes_int8_zlib"
        )

    if isinstance(total_bytes, int) and isinstance(limit_bytes, int) and total_bytes > limit_bytes:
        warnings.append(
            f"artifact total ({total_bytes}) exceeds declared limit ({limit_bytes})"
        )

    tokenizer_counted = artifact.get("tokenizer_counted")
    tokenizer_bytes = artifact.get("tokenizer_bytes_if_counted")
    if tokenizer_counted is False and tokenizer_bytes in (None, 0):
        warnings.append(
            "tokenizer_counted is false but tokenizer_bytes_if_counted is missing/zero; "
            "advisory visibility is reduced"
        )

    train = evidence.get("train", {})
    train_wallclock_s = train.get("train_wallclock_s")
    max_wallclock_s = train.get("max_wallclock_s")
    if (
        isinstance(train_wallclock_s, (int, float))
        and isinstance(max_wallclock_s, (int, float))
        and train_wallclock_s > max_wallclock_s
    ):
        warnings.append(
            f"train wallclock ({train_wallclock_s}) exceeds declared max ({max_wallclock_s})"
        )

    evaluation = evidence.get("evaluation", {})
    mode = evaluation.get("mode")
    stride = evaluation.get("stride")
    val_bpb = evaluation.get("val_bpb")

    if mode == "sliding_window" and stride in (None, 0):
        warnings.append("evaluation.mode is sliding_window but stride is missing")
    if mode == "standard" and stride not in (None,):
        warnings.append("evaluation.mode is standard but stride is present")
    if val_bpb is None:
        warnings.append("evaluation.val_bpb is missing")

    stats = evidence.get("stats", {})
    run_logs = stats.get("run_logs") or []
    n_runs = stats.get("n_runs")
    p_value = stats.get("p_value")
    exemption = stats.get("claim_exemption_reason")

    if p_value is not None and n_runs is None:
        warnings.append("stats.p_value is present but stats.n_runs is missing")
    if isinstance(n_runs, int) and len(run_logs) > 0 and len(run_logs) != n_runs:
        warnings.append(
            f"stats.n_runs ({n_runs}) does not match number of run_logs ({len(run_logs)})"
        )
    if evidence.get("submission_type") == "record":
        if not run_logs and not exemption:
            warnings.append(
                "record submission has neither run_logs nor claim_exemption_reason"
            )

    return warnings


def build_summary(evidence: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    artifact = evidence.get("artifact", {})
    evaluation = evidence.get("evaluation", {})
    return {
        "valid_schema": True,
        "warning_count": len(warnings),
        "warnings": warnings,
        "summary": {
            "submission_type": evidence.get("submission_type"),
            "total_bytes_int8_zlib": artifact.get("total_bytes_int8_zlib"),
            "artifact_limit_bytes": artifact.get("artifact_limit_bytes", 16_000_000),
            "evaluation_mode": evaluation.get("mode"),
            "val_bpb": evaluation.get("val_bpb"),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Parameter Golf evidence artifact."
    )
    parser.add_argument("--evidence", required=True, help="Path to evidence JSON.")
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to schema JSON. Defaults to the repo-local v0 schema.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat semantic warnings as a non-zero exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a structured JSON result instead of a text summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence_path = Path(args.evidence)
    schema_path = Path(args.schema)

    try:
        evidence = load_json(evidence_path)
    except FileNotFoundError:
        print(f"ERROR: evidence file not found: {evidence_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in evidence file: {exc}", file=sys.stderr)
        return 1

    try:
        schema = load_json(schema_path)
    except FileNotFoundError:
        print(f"ERROR: schema file not found: {schema_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in schema file: {exc}", file=sys.stderr)
        return 1

    try:
        validate_schema(evidence, schema)
    except jsonschema.ValidationError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "valid_schema": False,
                        "error": exc.message,
                        "path": list(exc.absolute_path),
                    },
                    indent=2,
                )
            )
        else:
            print("INVALID")
            print(f"Schema validation failed: {exc.message}")
            if exc.absolute_path:
                print(f"At path: {'/'.join(map(str, exc.absolute_path))}")
        return 1

    warnings = semantic_checks(evidence)
    result = build_summary(evidence, warnings)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("VALID")
        print(
            "Submission type: "
            f"{result['summary']['submission_type']} | "
            "mode: "
            f"{result['summary']['evaluation_mode']} | "
            "val_bpb: "
            f"{result['summary']['val_bpb']} | "
            "bytes: "
            f"{result['summary']['total_bytes_int8_zlib']}/"
            f"{result['summary']['artifact_limit_bytes']}"
        )
        if warnings:
            print("Warnings:")
            for item in warnings:
                print(f"- {item}")
        else:
            print("No semantic warnings.")

    if warnings and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
