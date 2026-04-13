#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

CONTRACT_CHECKER_VERSION = "epf_shadow_run_manifest_contract_v0"
EXPECTED_ARTIFACT_VERSION = "epf_shadow_run_manifest_v0"
EXPECTED_LAYER_ID = "epf_shadow_experiment_v0"
EXPECTED_RELATION_SCOPE = "baseline_vs_epf_shadow"

BRANCH_STATES = {
    "real",
    "partial",
    "stub",
    "degraded",
    "invalid",
    "absent",
}
TOP_LEVEL_PAYLOAD_REQUIRED = {
    "command_rcs",
    "branch_states",
    "artifacts",
    "comparison",
}
TOP_LEVEL_PAYLOAD_ALLOWED = set(TOP_LEVEL_PAYLOAD_REQUIRED)

COMMAND_RCS_REQUIRED = {
    "deps_rc",
    "runall_rc",
    "baseline_rc",
    "epf_rc",
}
COMMAND_RCS_ALLOWED = set(COMMAND_RCS_REQUIRED)

BRANCH_STATES_REQUIRED = {
    "baseline_state",
    "epf_state",
}
BRANCH_STATES_ALLOWED = set(BRANCH_STATES_REQUIRED)

ARTIFACTS_REQUIRED = {
    "baseline_status_path",
    "epf_status_path",
    "paradox_summary_path",
}
ARTIFACTS_ALLOWED = ARTIFACTS_REQUIRED | {
    "epf_report_path",
}

COMPARISON_REQUIRED = {
    "total_gates",
    "changed",
    "example_count",
}
COMPARISON_ALLOWED = set(COMPARISON_REQUIRED)

INT_STRING_RE = re.compile(r"^-?[0-9]+$")


def _add_issue(issues: list[dict[str, str]], path: str, message: str) -> None:
    issues.append({"path": path, "message": message})


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _check_required_and_extra_keys(
    obj: dict[str, Any],
    required: set[str],
    allowed: set[str],
    path: str,
    errors: list[dict[str, str]],
) -> None:
    for key in sorted(required):
        if key not in obj:
            _add_issue(errors, f"{path}.{key}" if path else key, f"missing required field: {key}")

    for key in sorted(obj.keys()):
        if key not in allowed:
            _add_issue(errors, f"{path}.{key}" if path else key, f"unexpected field: {key}")


def _parse_int_string(value: Any, path: str, errors: list[dict[str, str]]) -> int | None:
    if not _is_non_empty_str(value):
        _add_issue(errors, path, f"{path} must be a non-empty integer string")
        return None

    value_s = str(value)
    if INT_STRING_RE.fullmatch(value_s) is None:
        _add_issue(errors, path, f"{path} must match ^-?[0-9]+$")
        return None

    try:
        return int(value_s)
    except ValueError:
        _add_issue(errors, path, f"{path} must parse as an integer")
        return None


def _parse_non_negative_int(value: Any, path: str, errors: list[dict[str, str]]) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool):
        _add_issue(errors, path, f"{path} must be a non-negative integer")
        return None
    if value < 0:
        _add_issue(errors, path, f"{path} must be a non-negative integer")
        return None
    return value


def _load_common_checker_module():
    checker_path = Path(__file__).resolve().parent / "check_shadow_artifact_contract.py"
    spec = importlib.util.spec_from_file_location("check_shadow_artifact_contract", checker_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load common shadow artifact checker module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_epf_shadow_run_manifest(obj: Any) -> dict[str, Any]:
    common_checker = _load_common_checker_module()
    common_result = common_checker.validate_shadow_artifact(
        obj=obj,
        expected_layer_id=EXPECTED_LAYER_ID,
    )

    errors: list[dict[str, str]] = list(common_result.get("errors", []))
    warnings: list[dict[str, str]] = list(common_result.get("warnings", []))

    if not isinstance(obj, dict):
        return {
            "ok": False,
            "neutral": False,
            "contract_checker_version": CONTRACT_CHECKER_VERSION,
            "artifact_version": None,
            "run_reality_state": None,
            "verdict": None,
            "errors": errors,
            "warnings": warnings,
        }

    artifact_version = obj.get("artifact_version")
    artifact_version_s: str | None = None
    if not _is_non_empty_str(artifact_version):
        _add_issue(errors, "artifact_version", "artifact_version must be a non-empty string")
    else:
        artifact_version_s = str(artifact_version)
        if artifact_version_s != EXPECTED_ARTIFACT_VERSION:
            _add_issue(
                errors,
                "artifact_version",
                f"artifact_version must equal {EXPECTED_ARTIFACT_VERSION!r}",
            )

    relation_scope = obj.get("relation_scope")
    if not _is_non_empty_str(relation_scope):
        _add_issue(errors, "relation_scope", "relation_scope must be a non-empty string")
    elif str(relation_scope) != EXPECTED_RELATION_SCOPE:
        _add_issue(
            errors,
            "relation_scope",
            f"relation_scope must equal {EXPECTED_RELATION_SCOPE!r}",
        )

    payload = obj.get("payload")
    if not isinstance(payload, dict):
        _add_issue(errors, "payload", "payload must be an object")
        payload = None

    run_reality_state = obj.get("run_reality_state")
    verdict = obj.get("verdict")

    deps_rc: int | None = None
    runall_rc: int | None = None
    baseline_rc: int | None = None
    epf_rc: int | None = None

    baseline_state: str | None = None
    epf_state: str | None = None

    baseline_status_path: str | None = None
    epf_status_path: str | None = None
    paradox_summary_path: str | None = None
    epf_report_path: str | None = None

    total_gates: int | None = None
    changed: int | None = None
    example_count: int | None = None

    if payload is not None:
        _check_required_and_extra_keys(
            obj=payload,
            required=TOP_LEVEL_PAYLOAD_REQUIRED,
            allowed=TOP_LEVEL_PAYLOAD_ALLOWED,
            path="payload",
            errors=errors,
        )

        command_rcs = payload.get("command_rcs")
        if not isinstance(command_rcs, dict):
            _add_issue(errors, "payload.command_rcs", "command_rcs must be an object")
        else:
            _check_required_and_extra_keys(
                obj=command_rcs,
                required=COMMAND_RCS_REQUIRED,
                allowed=COMMAND_RCS_ALLOWED,
                path="payload.command_rcs",
                errors=errors,
            )
            deps_rc = _parse_int_string(command_rcs.get("deps_rc"), "payload.command_rcs.deps_rc", errors)
            runall_rc = _parse_int_string(command_rcs.get("runall_rc"), "payload.command_rcs.runall_rc", errors)
            baseline_rc = _parse_int_string(command_rcs.get("baseline_rc"), "payload.command_rcs.baseline_rc", errors)
            epf_rc = _parse_int_string(command_rcs.get("epf_rc"), "payload.command_rcs.epf_rc", errors)

        branch_states = payload.get("branch_states")
        if not isinstance(branch_states, dict):
            _add_issue(errors, "payload.branch_states", "branch_states must be an object")
        else:
            _check_required_and_extra_keys(
                obj=branch_states,
                required=BRANCH_STATES_REQUIRED,
                allowed=BRANCH_STATES_ALLOWED,
                path="payload.branch_states",
                errors=errors,
            )
            baseline_state = branch_states.get("baseline_state")
            if baseline_state not in BRANCH_STATES:
                _add_issue(
                    errors,
                    "payload.branch_states.baseline_state",
                    f"baseline_state must be one of: {', '.join(sorted(BRANCH_STATES))}",
                )
                baseline_state = None
            else:
                baseline_state = str(baseline_state)

            epf_state = branch_states.get("epf_state")
            if epf_state not in BRANCH_STATES:
                _add_issue(
                    errors,
                    "payload.branch_states.epf_state",
                    f"epf_state must be one of: {', '.join(sorted(BRANCH_STATES))}",
                )
                epf_state = None
            else:
                epf_state = str(epf_state)

        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, dict):
            _add_issue(errors, "payload.artifacts", "artifacts must be an object")
        else:
            _check_required_and_extra_keys(
                obj=artifacts,
                required=ARTIFACTS_REQUIRED,
                allowed=ARTIFACTS_ALLOWED,
                path="payload.artifacts",
                errors=errors,
            )

            baseline_status_path = artifacts.get("baseline_status_path")
            if not _is_non_empty_str(baseline_status_path):
                _add_issue(
                    errors,
                    "payload.artifacts.baseline_status_path",
                    "baseline_status_path must be a non-empty string",
                )
                baseline_status_path = None
            else:
                baseline_status_path = str(baseline_status_path)

            epf_status_path = artifacts.get("epf_status_path")
            if not _is_non_empty_str(epf_status_path):
                _add_issue(
                    errors,
                    "payload.artifacts.epf_status_path",
                    "epf_status_path must be a non-empty string",
                )
                epf_status_path = None
            else:
                epf_status_path = str(epf_status_path)

            paradox_summary_path = artifacts.get("paradox_summary_path")
            if not _is_non_empty_str(paradox_summary_path):
                _add_issue(
                    errors,
                    "payload.artifacts.paradox_summary_path",
                    "paradox_summary_path must be a non-empty string",
                )
                paradox_summary_path = None
            else:
                paradox_summary_path = str(paradox_summary_path)

            if "epf_report_path" in artifacts:
                epf_report_path = artifacts.get("epf_report_path")
                if not _is_non_empty_str(epf_report_path):
                    _add_issue(
                        errors,
                        "payload.artifacts.epf_report_path",
                        "epf_report_path must be a non-empty string",
                    )
                    epf_report_path = None
                else:
                    epf_report_path = str(epf_report_path)

        comparison = payload.get("comparison")
        if not isinstance(comparison, dict):
            _add_issue(errors, "payload.comparison", "comparison must be an object")
        else:
            _check_required_and_extra_keys(
                obj=comparison,
                required=COMPARISON_REQUIRED,
                allowed=COMPARISON_ALLOWED,
                path="payload.comparison",
                errors=errors,
            )
            total_gates = _parse_non_negative_int(
                comparison.get("total_gates"),
                "payload.comparison.total_gates",
                errors,
            )
            changed = _parse_non_negative_int(
                comparison.get("changed"),
                "payload.comparison.changed",
                errors,
            )
            example_count = _parse_non_negative_int(
                comparison.get("example_count"),
                "payload.comparison.example_count",
                errors,
            )

    if total_gates is not None and changed is not None and changed > total_gates:
        _add_issue(
            errors,
            "payload.comparison.changed",
            "changed must not exceed total_gates",
        )

    if changed is not None and example_count is not None:
        if example_count > changed:
            _add_issue(
                errors,
                "payload.comparison.example_count",
                "example_count must not exceed changed",
            )

        if changed == 0 and example_count != 0:
            _add_issue(
                errors,
                "payload.comparison.example_count",
                "example_count must be 0 when changed is 0",
            )

        if changed > 0 and example_count == 0:
            _add_issue(
                errors,
                "payload.comparison.example_count",
                "example_count must be non-zero when changed is greater than 0",
            )

    if baseline_status_path is not None and epf_status_path is not None and baseline_status_path == epf_status_path:
        _add_issue(
            errors,
            "payload.artifacts",
            "baseline_status_path and epf_status_path must differ",
        )

    expected_source_paths = {
        p
        for p in (
            baseline_status_path,
            epf_status_path,
            paradox_summary_path,
            epf_report_path,
        )
        if p is not None
    }
    source_artifacts = obj.get("source_artifacts")
    if isinstance(source_artifacts, list):
        source_paths = {
            str(item.get("path"))
            for item in source_artifacts
            if isinstance(item, dict) and _is_non_empty_str(item.get("path"))
        }
        for expected_path in sorted(expected_source_paths):
            if expected_path not in source_paths:
                _add_issue(
                    errors,
                    "source_artifacts",
                    f"source_artifacts must contain path reference for {expected_path!r}",
                )

    if run_reality_state == "real":
        if baseline_state != "real":
            _add_issue(
                errors,
                "payload.branch_states.baseline_state",
                "baseline_state must be real when run_reality_state is real",
            )
        if epf_state != "real":
            _add_issue(
                errors,
                "payload.branch_states.epf_state",
                "epf_state must be real when run_reality_state is real",
            )

        if changed is not None:
            expected_verdict = "pass" if changed == 0 else "warn"
            if verdict != expected_verdict:
                _add_issue(
                    errors,
                    "verdict",
                    f"real EPF manifests must use verdict={expected_verdict!r} when changed={changed}",
                )

    if run_reality_state in {"partial", "stub", "degraded"}:
        if baseline_state == "real" and epf_state == "real":
            _add_issue(
                errors,
                "payload.branch_states",
                "at least one branch must be non-real when the overall run_reality_state is partial/stub/degraded",
            )
        if verdict not in {"warn", "unknown"}:
            _add_issue(
                errors,
                "verdict",
                "partial/stub/degraded EPF manifests must use verdict warn or unknown",
            )

    if run_reality_state == "invalid":
        if baseline_state != "invalid" and epf_state != "invalid":
            _add_issue(
                errors,
                "payload.branch_states",
                "at least one branch must be invalid when the overall run_reality_state is invalid",
            )

    if run_reality_state == "absent":
        if baseline_state != "absent":
            _add_issue(
                errors,
                "payload.branch_states.baseline_state",
                "baseline_state must be absent when run_reality_state is absent",
            )
        if epf_state != "absent":
            _add_issue(
                errors,
                "payload.branch_states.epf_state",
                "epf_state must be absent when run_reality_state is absent",
            )
        if total_gates not in {None, 0}:
            _add_issue(
                errors,
                "payload.comparison.total_gates",
                "total_gates must be 0 when run_reality_state is absent",
            )
        if changed not in {None, 0}:
            _add_issue(
                errors,
                "payload.comparison.changed",
                "changed must be 0 when run_reality_state is absent",
            )
        if example_count not in {None, 0}:
            _add_issue(
                errors,
                "payload.comparison.example_count",
                "example_count must be 0 when run_reality_state is absent",
            )

    return {
        "ok": len(errors) == 0,
        "neutral": False,
        "contract_checker_version": CONTRACT_CHECKER_VERSION,
        "artifact_version": artifact_version_s,
        "run_reality_state": run_reality_state if isinstance(run_reality_state, str) else None,
        "verdict": verdict if isinstance(verdict, str) else None,
        "errors": errors,
        "warnings": warnings,
    }


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"failed to read {path}: {exc}") from exc


def _write_result(result: dict[str, Any], output_path: Path | None) -> None:
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if output_path is not None:
        output_path.write_text(rendered + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the EPF shadow run manifest contract.",
    )
    parser.add_argument("--input", required=True, help="Path to the EPF shadow run manifest JSON.")
    parser.add_argument("--output", help="Optional path to write the checker result JSON.")
    parser.add_argument(
        "--if-input-present",
        action="store_true",
        help="Treat missing input as neutral success.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    if not input_path.exists():
        result = {
            "ok": bool(args.if_input_present),
            "neutral": bool(args.if_input_present),
            "contract_checker_version": CONTRACT_CHECKER_VERSION,
            "artifact_version": None,
            "run_reality_state": None,
            "verdict": None,
            "errors": [] if args.if_input_present else [{"path": "input", "message": "input artifact not found"}],
            "warnings": (
                [{"path": "input", "message": "input artifact not found; neutral absence preserved"}]
                if args.if_input_present
                else []
            ),
        }
        _write_result(result, output_path)
        return 0 if args.if_input_present else 1

    try:
        obj = _load_json(input_path)
    except ValueError as exc:
        result = {
            "ok": False,
            "neutral": False,
            "contract_checker_version": CONTRACT_CHECKER_VERSION,
            "artifact_version": None,
            "run_reality_state": None,
            "verdict": None,
            "errors": [{"path": "input", "message": str(exc)}],
            "warnings": [],
        }
        _write_result(result, output_path)
        return 1

    result = validate_epf_shadow_run_manifest(obj)
    _write_result(result, output_path)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
