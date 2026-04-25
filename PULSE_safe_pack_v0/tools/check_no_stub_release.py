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
from typing import Any, Dict, List


EXIT_PASS = 0
EXIT_FAIL = 2

RELEASE_LANES = {
    "release",
    "release-grade",
    "release_grade",
    "prod",
    "production",
}

NON_RELEASE_LANES = {
    "core",
    "field",
    "demo",
    "smoke",
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
    return value.strip().lower().replace(" ", "-")


def get_object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def collect_diagnostics(status: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept diagnostics from a few known locations so the checker is resilient
    across current PULSE status variants.

    Top-level diagnostics wins over nested diagnostics.
    """

    merged: Dict[str, Any] = {}

    meta = get_object(status.get("meta"))
    meta_diagnostics = get_object(meta.get("diagnostics"))
    merged.update(meta_diagnostics)

    metrics = get_object(status.get("metrics"))
    metrics_diagnostics = get_object(metrics.get("diagnostics"))
    merged.update(metrics_diagnostics)

    top_level_diagnostics = get_object(status.get("diagnostics"))
    merged.update(top_level_diagnostics)

    return merged


def get_run_mode(status: Dict[str, Any]) -> Any:
    metrics = get_object(status.get("metrics"))
    return metrics.get("run_mode", status.get("run_mode"))


def profile_indicates_stub(value: Any) -> bool:
    if value is None:
        return False

    text = str(value).strip().lower()

    return any(token in text for token in DANGEROUS_STUB_PROFILE_TOKENS)


def require_literal_false(
    diagnostics: Dict[str, Any],
    key: str,
    failures: List[str],
) -> None:
    """
    In release-like lanes, absence or non-boolean values are not enough.

    A release-grade artifact should explicitly prove that it is not scaffolded
    or stubbed.
    """

    if key not in diagnostics:
        failures.append(f"diagnostics.{key} is missing; release-grade evidence must be explicit")
        return

    if diagnostics.get(key) is not False:
        failures.append(f"diagnostics.{key} is not literal false")


def require_gate_true(
    gates: Dict[str, Any],
    key: str,
    failures: List[str],
) -> None:
    if gates.get(key) is not True:
        failures.append(f"gates.{key} is missing or not literal true")


def check_release_boundary(status: Dict[str, Any]) -> List[str]:
    failures: List[str] = []

    gates = status.get("gates")
    if not isinstance(gates, dict):
        return ["status.gates is missing or not an object"]

    diagnostics = collect_diagnostics(status)
    if not diagnostics:
        failures.append("diagnostics object is missing; release-grade evidence must be explicit")

    run_mode = get_run_mode(status)
    if run_mode is None:
        failures.append("metrics.run_mode is missing")
    else:
        normalized_run_mode = normalize_lane(str(run_mode))
        if normalized_run_mode in {"core", "demo", "field", "smoke"}:
            failures.append(f"metrics.run_mode is non-release: {run_mode}")

    require_literal_false(diagnostics, "gates_stubbed", failures)
    require_literal_false(diagnostics, "scaffold", failures)

    stub_profile = diagnostics.get("stub_profile")
    if profile_indicates_stub(stub_profile):
        failures.append(
            "diagnostics.stub_profile indicates stub/scaffold/smoke profile: "
            f"{stub_profile}"
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
