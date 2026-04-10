#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RUN_REALITY_STATES = {
    "real",
    "partial",
    "stub",
    "degraded",
    "invalid",
    "absent",
}

VERDICTS = {
    "pass",
    "warn",
    "fail",
    "unknown",
    "invalid",
    "absent",
}

DEGRADED_STATES = {
    "partial",
    "stub",
    "degraded",
}


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _add_issue(issues: list[dict[str, str]], path: str, message: str) -> None:
    issues.append({"path": path, "message": message})


def _parse_datetime(value: Any) -> bool:
    if not _is_non_empty_str(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _validate_reason(value: Any, path: str, errors: list[dict[str, str]]) -> None:
    if not isinstance(value, dict):
        _add_issue(errors, path, "reason must be an object")
        return

    if not _is_non_empty_str(value.get("code")):
        _add_issue(errors, f"{path}.code", "reason.code must be a non-empty string")

    if not _is_non_empty_str(value.get("message")):
        _add_issue(errors, f"{path}.message", "reason.message must be a non-empty string")

    severity = value.get("severity")
    if severity is not None and severity not in {"info", "warn", "error"}:
        _add_issue(
            errors,
            f"{path}.severity",
            "reason.severity must be one of info, warn, error",
        )


def _validate_source_artifact(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
) -> None:
    if not isinstance(value, dict):
        _add_issue(errors, path, "source artifact must be an object")
        return

    has_path = _is_non_empty_str(value.get("path"))
    has_artifact_id = _is_non_empty_str(value.get("artifact_id"))

    if not (has_path or has_artifact_id):
        _add_issue(
            errors,
            path,
            "source artifact must contain at least one of path or artifact_id",
        )

    sha256 = value.get("sha256")
    if sha256 is not None:
        if not isinstance(sha256, str) or len(sha256) != 64:
            _add_issue(errors, f"{path}.sha256", "sha256 must be a 64-character hex string")
        else:
            try:
                int(sha256, 16)
            except ValueError:
                _add_issue(errors, f"{path}.sha256", "sha256 must be hexadecimal")


def validate_shadow_artifact(
    obj: Any,
    expected_layer_id: str | None = None,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not isinstance(obj, dict):
        _add_issue(errors, "$", "artifact must be a JSON object")
        return {
            "ok": False,
            "neutral": False,
            "errors": errors,
            "warnings": warnings,
        }

    required_fields = [
        "artifact_version",
        "layer_id",
        "producer",
        "created_utc",
        "run_reality_state",
        "verdict",
        "source_artifacts",
        "summary",
        "reasons",
    ]

    for field in required_fields:
        if field not in obj:
            _add_issue(errors, field, f"missing required field: {field}")

    artifact_version = obj.get("artifact_version")
    if artifact_version is not None and not _is_non_empty_str(artifact_version):
        _add_issue(errors, "artifact_version", "artifact_version must be a non-empty string")

    layer_id = obj.get("layer_id")
    if layer_id is not None and not _is_non_empty_str(layer_id):
        _add_issue(errors, "layer_id", "layer_id must be a non-empty string")

    if expected_layer_id is not None and layer_id is not None and layer_id != expected_layer_id:
        _add_issue(
            errors,
            "layer_id",
            f"layer_id must match expected layer id: {expected_layer_id}",
        )

    producer = obj.get("producer")
    if producer is not None:
        if not isinstance(producer, dict):
            _add_issue(errors, "producer", "producer must be an object")
        else:
            if not _is_non_empty_str(producer.get("name")):
                _add_issue(errors, "producer.name", "producer.name must be a non-empty string")
            if not _is_non_empty_str(producer.get("version")):
                _add_issue(
                    errors,
                    "producer.version",
                    "producer.version must be a non-empty string",
                )

    created_utc = obj.get("created_utc")
    if created_utc is not None and not _parse_datetime(created_utc):
        _add_issue(
            errors,
            "created_utc",
            "created_utc must be an RFC3339 / ISO-8601 timestamp",
        )

    run_reality_state = obj.get("run_reality_state")
    if run_reality_state is not None and run_reality_state not in RUN_REALITY_STATES:
        _add_issue(
            errors,
            "run_reality_state",
            "run_reality_state must be one of: real, partial, stub, degraded, invalid, absent",
        )

    verdict = obj.get("verdict")
    if verdict is not None and verdict not in VERDICTS:
        _add_issue(
            errors,
            "verdict",
            "verdict must be one of: pass, warn, fail, unknown, invalid, absent",
        )

    summary = obj.get("summary")
    if summary is not None:
        if not isinstance(summary, dict):
            _add_issue(errors, "summary", "summary must be an object")
        else:
            if not _is_non_empty_str(summary.get("headline")):
                _add_issue(errors, "summary.headline", "summary.headline must be a non-empty string")

    reasons = obj.get("reasons")
    if reasons is not None:
        if not isinstance(reasons, list):
            _add_issue(errors, "reasons", "reasons must be an array")
        elif len(reasons) == 0:
            _add_issue(errors, "reasons", "reasons must be a non-empty array")
        else:
            for idx, reason in enumerate(reasons):
                _validate_reason(reason, f"reasons[{idx}]", errors)

    degraded_reasons = obj.get("degraded_reasons", [])
    if degraded_reasons is not None:
        if not isinstance(degraded_reasons, list):
            _add_issue(errors, "degraded_reasons", "degraded_reasons must be an array")
        else:
            for idx, reason in enumerate(degraded_reasons):
                _validate_reason(reason, f"degraded_reasons[{idx}]", errors)

    source_artifacts = obj.get("source_artifacts")
    if source_artifacts is not None:
        if not isinstance(source_artifacts, list):
            _add_issue(errors, "source_artifacts", "source_artifacts must be an array")
        else:
            for idx, source_artifact in enumerate(source_artifacts):
                _validate_source_artifact(source_artifact, f"source_artifacts[{idx}]", errors)

    foldin_eligible = obj.get("foldin_eligible")
    if foldin_eligible is not None and not isinstance(foldin_eligible, bool):
        _add_issue(errors, "foldin_eligible", "foldin_eligible must be a boolean")

    if run_reality_state != "absent":
        if isinstance(source_artifacts, list) and len(source_artifacts) == 0:
            _add_issue(
                errors,
                "source_artifacts",
                "source_artifacts must not be empty when run_reality_state is not absent",
            )

    if run_reality_state in DEGRADED_STATES:
        if not isinstance(degraded_reasons, list) or len(degraded_reasons) == 0:
            _add_issue(
                errors,
                "degraded_reasons",
                "degraded_reasons must be a non-empty array for partial / stub / degraded runs",
            )

    if run_reality_state == "real":
        if isinstance(degraded_reasons, list) and len(degraded_reasons) > 0:
            _add_issue(
                errors,
                "degraded_reasons",
                "degraded_reasons must be empty for real runs",
            )
        if verdict in {"absent", "invalid"}:
            _add_issue(
                errors,
                "verdict",
                "real runs must not use absent or invalid verdict",
            )

    if run_reality_state == "absent":
        if verdict != "absent":
            _add_issue(errors, "verdict", "absent runs must use verdict=absent")
        if foldin_eligible is True:
            _add_issue(
                errors,
                "foldin_eligible",
                "absent runs must not be fold-in eligible",
            )

    if run_reality_state == "invalid":
        if verdict != "invalid":
            _add_issue(errors, "verdict", "invalid runs must use verdict=invalid")
        if foldin_eligible is True:
            _add_issue(
                errors,
                "foldin_eligible",
                "invalid runs must not be fold-in eligible",
            )

    return {
        "ok": len(errors) == 0,
        "neutral": False,
        "layer_id": layer_id,
        "artifact_version": artifact_version,
        "run_reality_state": run_reality_state,
        "verdict": verdict,
        "errors": errors,
        "warnings": warnings,
    }


def _write_result(result: dict[str, Any], output_path: Path | None) -> None:
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if output_path is not None:
        output_path.write_text(rendered + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the common shadow artifact contract envelope.",
    )
    parser.add_argument("--input", required=True, help="Path to the artifact JSON file")
    parser.add_argument(
        "--output",
        help="Optional path to write the checker result JSON",
    )
    parser.add_argument(
        "--expected-layer-id",
        help="Optional expected layer_id value",
    )
    parser.add_argument(
        "--if-input-present",
        action="store_true",
        help="Treat missing input as neutral success",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    if not input_path.exists():
        result = {
            "ok": bool(args.if_input_present),
            "neutral": bool(args.if_input_present),
            "layer_id": args.expected_layer_id,
            "artifact_version": None,
            "run_reality_state": "absent",
            "verdict": "absent",
            "errors": [] if args.if_input_present else [{"path": "input", "message": "input artifact not found"}],
            "warnings": [{"path": "input", "message": "input artifact not found; neutral absence preserved"}]
            if args.if_input_present
            else [],
        }
        _write_result(result, output_path)
        return 0 if args.if_input_present else 1

    try:
        obj = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result = {
            "ok": False,
            "neutral": False,
            "layer_id": None,
            "artifact_version": None,
            "run_reality_state": "invalid",
            "verdict": "invalid",
            "errors": [{"path": "input", "message": f"invalid JSON: {exc}"}],
            "warnings": [],
        }
        _write_result(result, output_path)
        return 1

    result = validate_shadow_artifact(
        obj=obj,
        expected_layer_id=args.expected_layer_id,
    )
    _write_result(result, output_path)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
