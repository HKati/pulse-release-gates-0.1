#!/usr/bin/env python3
"""
PULSE no-stub release boundary checker.

This tool enforces a narrow but important invariant:

- core/demo/field/scaffold runs may exist for exploration and baseline validation
- release-grade/prod lanes must not treat stubbed, scaffolded, smoke, or
  non-materialized evidence as release authority

This checker is intentionally separate from check_gates.py.

check_gates.py verifies required gates.
check_no_stub_release.py verifies that a release-like lane is not built on
stub/scaffold evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


EXIT_PASS = 0
EXIT_FAIL = 2

RELEASE_LANES = {
    "release",
    "release-grade",
    "prod",
    "production",
}

NON_RELEASE_LANES = {
    "core",
    "field",
    "demo",
    "smoke",
    "scaffold",
    "shadow",
    "advisory",
}

DANGEROUS_STUB_PROFILE_TOKENS = (
    "all_true",
    "all-true",
    "smoke",
    "stub",
    "scaffold",
)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
    except Exception as exc:
        print(f"FAIL: could not read status JSON: {exc}", file=sys.stderr)
        sys.exit(EXIT_FAIL)

    if not isinstance(value, dict):
        print("FAIL: status JSON root must be an object", file=sys.stderr)
        sys.exit(EXIT_FAIL)

    return value


def normalize_lane(value: str) -> str:
    text = value.strip().lower().replace("_", "-").replace(" ", "-")

    while "--" in text:
        text = text.replace("--", "-")

    return text


def get_object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_repr(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return repr(value)


def collect_diagnostic_sources(
    status: Dict[str, Any],
) -> Tuple[List[Tuple[str, Dict[str, Any]]], List[str]]:
    """
    Collect diagnostics from known status locations without masking conflicts.

    Important boundary rule:

    A blocking diagnostic signal from any source must fail release-grade checks.
    Top-level diagnostics must not silently overwrite nested diagnostics.
    """

    sources: List[Tuple[str, Dict[str, Any]]] = []
    failures: List[str] = []

    def add_source(path: str, value: Any) -> None:
        if value is None:
            return

        if not isinstance(value, dict):
            failures.append(f"{path} is present but not an object")
            return

        if value:
            sources.append((path, value))

    meta = get_object(status.get("meta"))
    add_source("meta.diagnostics", meta.get("diagnostics"))

    metrics = get_object(status.get("metrics"))
    add_source("metrics.diagnostics", metrics.get("diagnostics"))

    add_source("diagnostics", status.get("diagnostics"))

    return sources, failures


def get_run_mode(status: Dict[str, Any]) -> Any:
    metrics = get_object(status.get("metrics"))
    return metrics.get("run_mode", status.get("run_mode"))


def profile_indicates_stub(value: Any) -> bool:
    if value is None:
        return False

    text = str(value).strip().lower()

    return any(token in text for token in DANGEROUS_STUB_PROFILE_TOKENS)


def format_source_values(values: List[Tuple[str, Any]]) -> str:
    return ", ".join(f"{path}={safe_repr(value)}" for path, value in values)


def require_consistent_literal_false(
    diagnostic_sources: List[Tuple[str, Dict[str, Any]]],
    key: str,
    failures: List[str],
) -> None:
    """
    In release-like lanes, a stub/scaffold flag must be explicitly false.

    If multiple diagnostic sources contain the key, they must not disagree.
    Any non-false value is blocking.
    """

    values = [
        (path, diagnostics[key])
        for path, diagnostics in diagnostic_sources
        if key in diagnostics
    ]

    if not values:
        failures.append(
            f"diagnostics.{key} is missing across diagnostic sources; "
            "release-grade evidence must be explicit"
        )
        return

    unique_values = {safe_repr(value) for _, value in values}

    if len(unique_values) > 1:
        failures.append(
            f"diagnostics.{key} has conflicting values across diagnostic sources: "
            f"{format_source_values(values)}"
        )

    for path, value in values:
        if value is not False:
            failures.append(f"{path}.{key} is not literal false")


def check_stub_profiles(
    diagnostic_sources: List[Tuple[str, Dict[str, Any]]],
    failures: List[str],
) -> None:
    values = [
        (path, diagnostics["stub_profile"])
        for path, diagnostics in diagnostic_sources
        if "stub_profile" in diagnostics
    ]

    if not values:
        return

    unique_values = {safe_repr(value) for _, value in values}

    if len(unique_values) > 1:
        failures.append(
            "diagnostics.stub_profile has conflicting values across diagnostic sources: "
            f"{format_source_values(values)}"
        )

    for path, value in values:
        if profile_indicates_stub(value):
            failures.append(
                f"{path}.stub_profile indicates stub/scaffold/smoke profile: {value}"
            )


def require_gate_true(
    gates: Dict[str, Any],
    key: str,
    failures: List[str],
) -> None:
    if gates.get(key) is not True:
        failures.append(f"gates.{key} is missing or not literal true")


def check_release_boundary(status: Dict[str, Any]) -> List[str]:
    failures: List[str] = []

    gates_value = status.get("gates")
    if not isinstance(gates_value, dict):
        failures.append("status.gates is missing or not an object")
        gates: Dict[str, Any] = {}
    else:
        gates = gates_value

    diagnostic_sources, diagnostic_shape_failures = collect_diagnostic_sources(status)
    failures.extend(diagnostic_shape_failures)

    if not diagnostic_sources:
        failures.append(
            "diagnostics object is missing or empty; "
            "release-grade evidence must be explicit"
        )
    else:
        require_consistent_literal_false(
            diagnostic_sources,
            "gates_stubbed",
            failures,
        )
        require_consistent_literal_false(
            diagnostic_sources,
            "scaffold",
            failures,
        )
        check_stub_profiles(diagnostic_sources, failures)

    run_mode = get_run_mode(status)

    if run_mode is None or str(run_mode).strip() == "":
        failures.append("run_mode is missing or empty")
    else:
        normalized_run_mode = normalize_lane(str(run_mode))

        if normalized_run_mode not in RELEASE_LANES:
            failures.append(
                "run_mode is not release-like for release boundary check: "
                f"{run_mode}"
            )

    require_gate_true(gates, "detectors_materialized_ok", failures)
    require_gate_true(gates, "external_summaries_present", failures)
    require_gate_true(gates, "external_all_pass", failures)

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail closed if a release-grade/prod PULSE status is based on "
            "stubbed, scaffolded, smoke, or non-materialized evidence."
        )
    )
    parser.add_argument("status_json", help="Path to PULSE status JSON")
    parser.add_argument(
        "--lane",
        required=True,
        help="Lane being checked: core, field, demo, release-grade, prod, etc.",
    )

    args = parser.parse_args()

    lane = normalize_lane(args.lane)
    status = load_json(Path(args.status_json))

    if lane in NON_RELEASE_LANES:
        print("PASS: no-stub release boundary is not enforced for non-release lane.")
        return EXIT_PASS

    if lane not in RELEASE_LANES:
        print(
            f"FAIL: unknown lane '{args.lane}'. "
            "Use an explicit release or non-release lane.",
            file=sys.stderr,
        )
        return EXIT_FAIL

    failures = check_release_boundary(status)

    if failures:
        print(
            "FAIL: release-grade/prod lane cannot use stubbed, scaffolded, "
            "smoke, or non-materialized evidence.",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return EXIT_FAIL

    print("PASS: release-grade/prod status is not stub/scaffold evidence.")
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
