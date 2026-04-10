#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

CONTRACT_CHECKER_VERSION = "relational_gain_contract_v0"
EXPECTED_ARTIFACT_CHECKER_VERSION = "relational_gain_v0"
ALLOWED_VERDICTS = {"PASS", "WARN", "FAIL"}

TOP_LEVEL_REQUIRED = {
    "checker_version",
    "verdict",
    "input",
    "metrics",
}
TOP_LEVEL_ALLOWED = set(TOP_LEVEL_REQUIRED)

INPUT_REQUIRED = {"path"}
INPUT_ALLOWED = set(INPUT_REQUIRED)

METRICS_REQUIRED = {
    "checked_edges",
    "checked_cycles",
    "max_edge_gain",
    "max_cycle_gain",
    "warn_threshold",
    "offending_edges",
    "offending_cycles",
    "near_boundary_edges",
    "near_boundary_cycles",
}
METRICS_ALLOWED = set(METRICS_REQUIRED)


def _add_issue(issues: list[dict[str, str]], path: str, message: str) -> None:
    issues.append({"path": path, "message": message})


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _is_nonnegative_number(value: Any) -> bool:
    return _is_finite_number(value) and float(value) >= 0.0


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"failed to read {path}: {exc}") from exc


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
            _add_issue(
                errors,
                f"{path}.{key}" if path else key,
                f"unexpected field: {key}",
            )


def _read_number_list(
    obj: dict[str, Any],
    key: str,
    errors: list[dict[str, str]],
) -> list[float] | None:
    value = obj.get(key)
    if not isinstance(value, list):
        _add_issue(errors, key, f"{key} must be an array")
        return None

    out: list[float] = []
    for idx, item in enumerate(value):
        if not _is_nonnegative_number(item):
            _add_issue(
                errors,
                f"{key}[{idx}]",
                f"{key} items must be finite non-negative numbers",
            )
            continue
        out.append(float(item))
    return out


def _validate_dimension_semantics(
    *,
    dimension: str,
    checked_count: int | None,
    max_gain: float | None,
    warn_threshold: float | None,
    offending: list[float] | None,
    near_boundary: list[float] | None,
    errors: list[dict[str, str]],
) -> None:
    if (
        checked_count is None
        or max_gain is None
        or warn_threshold is None
        or offending is None
        or near_boundary is None
    ):
        return

    if len(offending) + len(near_boundary) > checked_count:
        _add_issue(
            errors,
            f"metrics.{dimension}",
            f"{dimension} flagged entries must not exceed checked count",
        )

    for idx, value in enumerate(offending):
        if value <= 1.0:
            _add_issue(
                errors,
                f"metrics.offending_{dimension}[{idx}]",
                f"offending_{dimension} items must be > 1.0",
            )

    for idx, value in enumerate(near_boundary):
        if value < warn_threshold or value > 1.0:
            _add_issue(
                errors,
                f"metrics.near_boundary_{dimension}[{idx}]",
                f"near_boundary_{dimension} items must satisfy warn_threshold <= x <= 1.0",
            )

    if checked_count == 0:
        if not math.isclose(max_gain, 0.0, rel_tol=0.0, abs_tol=1e-12):
            _add_issue(
                errors,
                f"metrics.max_{dimension[:-1]}_gain",
                f"max_{dimension[:-1]}_gain must be 0 when checked_{dimension} is 0",
            )
        if offending:
            _add_issue(
                errors,
                f"metrics.offending_{dimension}",
                f"offending_{dimension} must be empty when checked_{dimension} is 0",
            )
        if near_boundary:
            _add_issue(
                errors,
                f"metrics.near_boundary_{dimension}",
                f"near_boundary_{dimension} must be empty when checked_{dimension} is 0",
            )
        return

    if offending:
        expected_max = max(offending)
        if max_gain <= 1.0:
            _add_issue(
                errors,
                f"metrics.max_{dimension[:-1]}_gain",
                f"max_{dimension[:-1]}_gain must be > 1.0 when offending_{dimension} is non-empty",
            )
        if not math.isclose(max_gain, expected_max, rel_tol=0.0, abs_tol=1e-12):
            _add_issue(
                errors,
                f"metrics.max_{dimension[:-1]}_gain",
                f"max_{dimension[:-1]}_gain must equal max(offending_{dimension}) when offending_{dimension} is non-empty",
            )
    else:
        if max_gain > 1.0:
            _add_issue(
                errors,
                f"metrics.max_{dimension[:-1]}_gain",
                f"max_{dimension[:-1]}_gain cannot exceed 1.0 when offending_{dimension} is empty",
            )

        if max_gain >= warn_threshold:
            if not near_boundary:
                _add_issue(
                    errors,
                    f"metrics.near_boundary_{dimension}",
                    f"near_boundary_{dimension} must be non-empty when offending_{dimension} is empty and max_{dimension[:-1]}_gain >= warn_threshold",
                )
            else:
                expected_max = max(near_boundary)
                if not math.isclose(max_gain, expected_max, rel_tol=0.0, abs_tol=1e-12):
                    _add_issue(
                        errors,
                        f"metrics.max_{dimension[:-1]}_gain",
                        f"max_{dimension[:-1]}_gain must equal max(near_boundary_{dimension}) when offending_{dimension} is empty and max_{dimension[:-1]}_gain >= warn_threshold",
                    )
        else:
            if near_boundary:
                _add_issue(
                    errors,
                    f"metrics.near_boundary_{dimension}",
                    f"near_boundary_{dimension} must be empty when max_{dimension[:-1]}_gain < warn_threshold",
                )


def validate_relational_gain_artifact(obj: Any) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not isinstance(obj, dict):
        _add_issue(errors, "$", "artifact must be a JSON object")
        return {
            "ok": False,
            "neutral": False,
            "contract_checker_version": CONTRACT_CHECKER_VERSION,
            "artifact_checker_version": None,
            "verdict": None,
            "errors": errors,
            "warnings": warnings,
        }

    _check_required_and_extra_keys(
        obj=obj,
        required=TOP_LEVEL_REQUIRED,
        allowed=TOP_LEVEL_ALLOWED,
        path="",
        errors=errors,
    )

    checker_version = obj.get("checker_version")
    if not _is_non_empty_str(checker_version):
        _add_issue(errors, "checker_version", "checker_version must be a non-empty string")
    elif checker_version != EXPECTED_ARTIFACT_CHECKER_VERSION:
        _add_issue(
            errors,
            "checker_version",
            f"checker_version must equal {EXPECTED_ARTIFACT_CHECKER_VERSION!r}",
        )

    verdict = obj.get("verdict")
    if verdict not in ALLOWED_VERDICTS:
        _add_issue(errors, "verdict", "verdict must be one of: PASS, WARN, FAIL")

    input_obj = obj.get("input")
    if not isinstance(input_obj, dict):
        _add_issue(errors, "input", "input must be an object")
    else:
        _check_required_and_extra_keys(
            obj=input_obj,
            required=INPUT_REQUIRED,
            allowed=INPUT_ALLOWED,
            path="input",
            errors=errors,
        )
        if not _is_non_empty_str(input_obj.get("path")):
            _add_issue(errors, "input.path", "input.path must be a non-empty string")

    metrics = obj.get("metrics")
    if not isinstance(metrics, dict):
        _add_issue(errors, "metrics", "metrics must be an object")
        metrics = None
    else:
        _check_required_and_extra_keys(
            obj=metrics,
            required=METRICS_REQUIRED,
            allowed=METRICS_ALLOWED,
            path="metrics",
            errors=errors,
        )

    checked_edges: int | None = None
    checked_cycles: int | None = None
    max_edge_gain: float | None = None
    max_cycle_gain: float | None = None
    warn_threshold: float | None = None
    offending_edges: list[float] | None = None
    offending_cycles: list[float] | None = None
    near_boundary_edges: list[float] | None = None
    near_boundary_cycles: list[float] | None = None

    if metrics is not None:
        value = metrics.get("checked_edges")
        if not _is_nonnegative_int(value):
            _add_issue(errors, "metrics.checked_edges", "checked_edges must be a non-negative integer")
        else:
            checked_edges = int(value)

        value = metrics.get("checked_cycles")
        if not _is_nonnegative_int(value):
            _add_issue(errors, "metrics.checked_cycles", "checked_cycles must be a non-negative integer")
        else:
            checked_cycles = int(value)

        value = metrics.get("max_edge_gain")
        if not _is_nonnegative_number(value):
            _add_issue(errors, "metrics.max_edge_gain", "max_edge_gain must be a finite non-negative number")
        else:
            max_edge_gain = float(value)

        value = metrics.get("max_cycle_gain")
        if not _is_nonnegative_number(value):
            _add_issue(errors, "metrics.max_cycle_gain", "max_cycle_gain must be a finite non-negative number")
        else:
            max_cycle_gain = float(value)

        value = metrics.get("warn_threshold")
        if not _is_nonnegative_number(value):
            _add_issue(errors, "metrics.warn_threshold", "warn_threshold must be a finite non-negative number")
        else:
            warn_threshold = float(value)

        offending_edges = _read_number_list(metrics, "offending_edges", errors)
        offending_cycles = _read_number_list(metrics, "offending_cycles", errors)
        near_boundary_edges = _read_number_list(metrics, "near_boundary_edges", errors)
        near_boundary_cycles = _read_number_list(metrics, "near_boundary_cycles", errors)

    _validate_dimension_semantics(
        dimension="edges",
        checked_count=checked_edges,
        max_gain=max_edge_gain,
        warn_threshold=warn_threshold,
        offending=offending_edges,
        near_boundary=near_boundary_edges,
        errors=errors,
    )
    _validate_dimension_semantics(
        dimension="cycles",
        checked_count=checked_cycles,
        max_gain=max_cycle_gain,
        warn_threshold=warn_threshold,
        offending=offending_cycles,
        near_boundary=near_boundary_cycles,
        errors=errors,
    )

    offending_present = bool((offending_edges or []) or (offending_cycles or []))
    near_boundary_present = bool((near_boundary_edges or []) or (near_boundary_cycles or []))

    if verdict == "PASS":
        if offending_present:
            _add_issue(errors, "verdict", "PASS artifacts must not contain offending edges or cycles")
        if near_boundary_present:
            _add_issue(errors, "verdict", "PASS artifacts must not contain near-boundary edges or cycles")

    if verdict == "WARN":
        if offending_present:
            _add_issue(errors, "verdict", "WARN artifacts must not contain offending edges or cycles")
        if not near_boundary_present:
            _add_issue(errors, "verdict", "WARN artifacts must contain at least one near-boundary edge or cycle")

    if verdict == "FAIL":
        if not offending_present:
            _add_issue(errors, "verdict", "FAIL artifacts must contain at least one offending edge or cycle")

    return {
        "ok": len(errors) == 0,
        "neutral": False,
        "contract_checker_version": CONTRACT_CHECKER_VERSION,
        "artifact_checker_version": checker_version if _is_non_empty_str(checker_version) else None,
        "verdict": verdict if isinstance(verdict, str) else None,
        "errors": errors,
        "warnings": warnings,
    }


def _write_result(result: dict[str, Any], output_path: Path | None) -> None:
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if output_path is not None:
        output_path.write_text(rendered + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the current Relational Gain shadow artifact contract.",
    )
    parser.add_argument("--input", required=True, help="Path to the Relational Gain shadow artifact JSON.")
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
            "artifact_checker_version": None,
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
            "artifact_checker_version": None,
            "verdict": None,
            "errors": [{"path": "input", "message": str(exc)}],
            "warnings": [],
        }
        _write_result(result, output_path)
        return 1

    result = validate_relational_gain_artifact(obj)
    _write_result(result, output_path)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
