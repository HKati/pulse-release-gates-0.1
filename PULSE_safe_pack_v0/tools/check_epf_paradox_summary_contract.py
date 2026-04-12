#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CONTRACT_CHECKER_VERSION = "epf_paradox_summary_contract_v0"

TOP_LEVEL_REQUIRED = {
    "deps_rc",
    "runall_rc",
    "baseline_rc",
    "epf_rc",
    "total_gates",
    "changed",
    "examples",
}
TOP_LEVEL_ALLOWED = set(TOP_LEVEL_REQUIRED)

EXAMPLE_REQUIRED = {
    "gate",
    "baseline",
    "epf",
}
EXAMPLE_ALLOWED = set(EXAMPLE_REQUIRED)

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


def _parse_rc_string(value: Any, path: str, errors: list[dict[str, str]]) -> int | None:
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


def _validate_example(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
) -> tuple[str | None, Any, Any] | None:
    if not isinstance(value, dict):
        _add_issue(errors, path, "example must be an object")
        return None

    _check_required_and_extra_keys(
        obj=value,
        required=EXAMPLE_REQUIRED,
        allowed=EXAMPLE_ALLOWED,
        path=path,
        errors=errors,
    )

    gate = value.get("gate")
    if not _is_non_empty_str(gate):
        _add_issue(errors, f"{path}.gate", "gate must be a non-empty string")
        gate_s = None
    else:
        gate_s = str(gate)

    baseline = value.get("baseline")
    epf = value.get("epf")

    if "baseline" in value and "epf" in value and baseline == epf:
        _add_issue(errors, path, "baseline and epf must differ for changed-gate examples")

    return (gate_s, baseline, epf)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"failed to read {path}: {exc}") from exc


def validate_epf_paradox_summary(obj: Any) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not isinstance(obj, dict):
        _add_issue(errors, "$", "artifact must be a JSON object")
        return {
            "ok": False,
            "neutral": False,
            "contract_checker_version": CONTRACT_CHECKER_VERSION,
            "changed": None,
            "total_gates": None,
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

    deps_rc = _parse_rc_string(obj.get("deps_rc"), "deps_rc", errors)
    runall_rc = _parse_rc_string(obj.get("runall_rc"), "runall_rc", errors)
    baseline_rc = _parse_rc_string(obj.get("baseline_rc"), "baseline_rc", errors)
    epf_rc = _parse_rc_string(obj.get("epf_rc"), "epf_rc", errors)

    total_gates = _parse_non_negative_int(obj.get("total_gates"), "total_gates", errors)
    changed = _parse_non_negative_int(obj.get("changed"), "changed", errors)

    examples = obj.get("examples")
    parsed_examples: list[tuple[str | None, Any, Any]] = []
    if not isinstance(examples, list):
        _add_issue(errors, "examples", "examples must be an array")
        examples_count = None
    else:
        examples_count = len(examples)
        seen_gates: dict[str, int] = {}
        for idx, example in enumerate(examples):
            parsed = _validate_example(example, f"examples[{idx}]", errors)
            if parsed is None:
                continue
            gate, baseline, epf = parsed
            parsed_examples.append((gate, baseline, epf))
            if gate is not None:
                if gate in seen_gates:
                    _add_issue(
                        errors,
                        f"examples[{idx}].gate",
                        f"duplicate gate example: {gate} (already used by examples[{seen_gates[gate]}])",
                    )
                else:
                    seen_gates[gate] = idx

    if total_gates is not None and changed is not None and changed > total_gates:
        _add_issue(errors, "changed", "changed must not exceed total_gates")

    if changed is not None and examples_count is not None:
        if changed == 0 and examples_count != 0:
            _add_issue(errors, "examples", "examples must be empty when changed is 0")
        if changed > 0 and examples_count == 0:
            _add_issue(errors, "examples", "examples must be non-empty when changed is greater than 0")
        if examples_count > changed:
            _add_issue(errors, "examples", "examples length must not exceed changed")

    return {
        "ok": len(errors) == 0,
        "neutral": False,
        "contract_checker_version": CONTRACT_CHECKER_VERSION,
        "deps_rc": deps_rc,
        "runall_rc": runall_rc,
        "baseline_rc": baseline_rc,
        "epf_rc": epf_rc,
        "total_gates": total_gates,
        "changed": changed,
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
        description="Validate the current EPF paradox summary artifact contract.",
    )
    parser.add_argument("--input", required=True, help="Path to the EPF paradox summary JSON.")
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
            "deps_rc": None,
            "runall_rc": None,
            "baseline_rc": None,
            "epf_rc": None,
            "total_gates": None,
            "changed": None,
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
            "deps_rc": None,
            "runall_rc": None,
            "baseline_rc": None,
            "epf_rc": None,
            "total_gates": None,
            "changed": None,
            "errors": [{"path": "input", "message": str(exc)}],
            "warnings": [],
        }
        _write_result(result, output_path)
        return 1

    result = validate_epf_paradox_summary(obj)
    _write_result(result, output_path)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
