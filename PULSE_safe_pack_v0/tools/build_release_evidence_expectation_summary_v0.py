#!/usr/bin/env python3
"""Build a reader-only release evidence expectation summary v0.

This tool summarizes a release_evidence_verifier_report_v0 artifact.

It does not verify evidence.
It does not satisfy relation bindings.
It does not materialize gates.
It does not write status.json.
It does not reopen --release-grade-materialized.
It does not replace check_gates.py.

It is a pre-materialization reader/diagnostic surface only.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any

try:
    import jsonschema
except Exception:  # pragma: no cover
    jsonschema = None


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.check_release_evidence_verifier_report_v0 import (  # noqa: E402
    check_release_evidence_verifier_report,
)


SCHEMA_VERSION = "release_evidence_expectation_summary_v0"
SUMMARY_ID = "pulse_release_evidence_expectation_summary_v0"
SUMMARY_VERSION = "0.1.0"
DEFAULT_SCHEMA_PATH = (
    REPO_ROOT / "schemas" / "release_evidence_expectation_summary_v0.schema.json"
)


def _utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _repo_relative_or_input(path: pathlib.Path, raw: str) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return raw


def _load_json_object(path: pathlib.Path, *, label: str) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"{label} is not valid JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")

    return obj


def _validate_summary(summary: dict[str, Any], *, schema_path: pathlib.Path) -> list[str]:
    errors: list[str] = []

    if jsonschema is None:
        return [
            "jsonschema is required for "
            "release_evidence_expectation_summary_v0 schema validation; "
            "partial fallback validation is not allowed"
        ]

    try:
        schema = _load_json_object(schema_path, label="release evidence expectation summary schema")
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        for error in sorted(validator.iter_errors(summary), key=lambda item: list(item.path)):
            path = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"schema validation error at {path}: {error.message}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"release evidence expectation summary schema validation failed: {exc}")

    return errors


def _gap_id_from_message(prefix: str, message: str) -> str | None:
    if not message.startswith(prefix):
        return None

    suffix = message[len(prefix):].strip()
    if not suffix:
        return None

    if " -> " in suffix:
        return suffix.split(" -> ", 1)[0].strip() or None

    return suffix


def _classify_failed_check(message: str) -> dict[str, Any]:
    classifiers = [
        (
            "expected candidate evidence recorded but not verified: ",
            "candidate_evidence_not_verified",
        ),
        (
            "expected candidate evidence not recorded: ",
            "missing_candidate_evidence",
        ),
        (
            "candidate evidence declared by manifest is missing: ",
            "missing_candidate_evidence",
        ),
        (
            "candidate evidence digest mismatch: ",
            "digest_mismatch",
        ),
        (
            "expected relation binding pending verification: ",
            "pending_relation_binding",
        ),
        (
            "expected gate materialization pending verification: ",
            "pending_gate_materialization",
        ),
        (
            "expected gate materialization candidate evidence not recorded: ",
            "missing_gate_candidate_evidence",
        ),
        (
            "no candidate evidence inputs were supplied",
            "no_candidate_evidence",
        ),
        (
            "no verified relation bindings present",
            "no_verified_relation_bindings",
        ),
        (
            "no gate materialization performed",
            "no_gate_materialization",
        )
    ]

    for prefix, kind in classifiers:
        if message == prefix or message.startswith(prefix):
            return {
                "kind": kind,
                "id": _gap_id_from_message(prefix, message),
                "message": message,
            }

    return {
        "kind": "other_failed_check",
        "id": None,
        "message": message,
    }


def build_summary(
    *,
    report_path: pathlib.Path,
) -> dict[str, Any]:
    checker_errors = check_release_evidence_verifier_report(report_path)
    if checker_errors:
        joined = "\n  - ".join(checker_errors)
        raise ValueError(
            "release evidence verifier report failed validation:\n"
            f"  - {joined}"
        )

    report = _load_json_object(report_path, label="release evidence verifier report")

    failed_checks = [
        str(item)
        for item in report.get("failed_checks", [])
        if isinstance(item, str) and item.strip()
    ]
    warnings = [
        str(item)
        for item in report.get("warnings", [])
        if isinstance(item, str) and item.strip()
    ]

    gaps = [_classify_failed_check(message) for message in failed_checks]

    counts = {
        "candidate_evidence_not_verified_count": sum(
            1 for gap in gaps if gap["kind"] == "candidate_evidence_not_verified"
        ),
        "missing_candidate_evidence_count": sum(
            1 for gap in gaps if gap["kind"] == "missing_candidate_evidence"
        ),
        "digest_mismatch_count": sum(
            1 for gap in gaps if gap["kind"] == "digest_mismatch"
        ),
        "pending_relation_binding_count": sum(
            1 for gap in gaps if gap["kind"] == "pending_relation_binding"
        ),
        "pending_gate_materialization_count": sum(
            1 for gap in gaps if gap["kind"] == "pending_gate_materialization"
        ),
        "other_failed_check_count": sum(
            1 for gap in gaps if gap["kind"] == "other_failed_check"
        ),
    }

    decision = report.get("verifier_decision")
    readiness = (
        "REPORT_VERIFIED_NON_AUTHORITY"
        if decision == "VERIFIED" and not gaps
        else "NOT_READY"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "created_utc": _utc_now(),
        "summary_id": SUMMARY_ID,
        "summary_version": SUMMARY_VERSION,
        "source_report": {
            "path": _repo_relative_or_input(report_path, str(report_path)),
            "sha256": _sha256_file(report_path),
            "verifier_decision": decision,
        },
        "summary": {
            "verifier_readiness": readiness,
            "evidence_inputs_total": len(report.get("evidence_inputs", []))
            if isinstance(report.get("evidence_inputs"), list)
            else 0,
            "verified_artifacts_total": len(report.get("verified_artifacts", []))
            if isinstance(report.get("verified_artifacts"), list)
            else 0,
            "relation_bindings_total": len(report.get("relation_bindings", []))
            if isinstance(report.get("relation_bindings"), list)
            else 0,
            "gate_materialization_total": len(report.get("gate_materialization", {}))
            if isinstance(report.get("gate_materialization"), dict)
            else 0,
            "failed_checks_total": len(failed_checks),
            "warnings_total": len(warnings),
            **counts,
        },
        "pre_materialization_gaps": gaps,
        "warnings": warnings,
        "authority_boundary": {
            "is_release_authority": False,
            "materializes_gates": False,
            "writes_status_json": False,
            "reopens_release_grade_materialization": False,
            "replaces_check_gates": False,
        },
    }


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build release_evidence_expectation_summary_v0 from a verifier report."
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to release_evidence_verifier_report_v0.json.",
    )
    parser.add_argument(
        "--out",
        default="PULSE_safe_pack_v0/artifacts/release_evidence_expectation_summary_v0.json",
        help="Output path for release_evidence_expectation_summary_v0.json.",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to release_evidence_expectation_summary_v0 JSON schema.",
    )

    args = parser.parse_args()

    report_path = pathlib.Path(args.report)
    if not report_path.is_absolute():
        report_path = (REPO_ROOT / report_path).resolve()
    else:
        report_path = report_path.resolve()

    out_path = pathlib.Path(args.out)
    if not out_path.is_absolute():
        out_path = (REPO_ROOT / out_path).resolve()
    else:
        out_path = out_path.resolve()

    schema_path = pathlib.Path(args.schema)
    if not schema_path.is_absolute():
        schema_path = (REPO_ROOT / schema_path).resolve()
    else:
        schema_path = schema_path.resolve()

    try:
        summary = build_summary(report_path=report_path)
        validation_errors = _validate_summary(summary, schema_path=schema_path)
        if validation_errors:
            joined = "\n  - ".join(validation_errors)
            raise ValueError(
                "release evidence expectation summary failed validation:\n"
                f"  - {joined}"
            )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    write_json(out_path, summary)
    print(f"OK: wrote release evidence expectation summary: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
