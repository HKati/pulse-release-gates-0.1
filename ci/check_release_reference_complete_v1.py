#!/usr/bin/env python3
"""
PULSE-REF release-grade reference qualification guard v1.

This script checks whether a candidate status artifact satisfies the minimum
PULSE-REF release-grade reference requirements.

It does not create release authority.
It does not replace check_gates.py.
It does not make manifests, ledgers, dashboards, or audit bundles normative.

The normative release decision remains produced by declared-policy gate
enforcement and recorded through the CI outcome.

This guard verifies release-grade completeness conditions:
- non-stubbed run
- prod / release-grade run mode
- materialized detector evidence
- external summaries present
- external aggregate pass
- required + release_required gates are literal boolean true
- optional release-authority manifest exists
- optional audit bundle exists
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: missing JSON file: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise SystemExit(
            "ERROR: PyYAML is required to load the gate policy. "
            "Install pyyaml or run without --policy."
        ) from exc

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: missing YAML file: {path}")
    except Exception as exc:
        raise SystemExit(f"ERROR: invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: expected YAML mapping in {path}")

    return data


def is_literal_true(value: Any) -> bool:
    return value is True


def get_nested_bool(data: dict[str, Any], path: list[str]) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def extract_gate_set(policy: dict[str, Any], set_name: str) -> list[str]:
    """
    Extract a gate set from common policy layouts.

    Supported shapes include:
    - {"gates": {"required": [...]}}
    - {"required": [...]}
    - {"gate_sets": {"required": [...]}}
    - {"sets": {"required": [...]}}
    """
    def _normalize_gate_list(candidate: Any) -> list[str]:
        if not isinstance(candidate, list):
            return []

        gates: list[str] = []
        for item in candidate:
            if isinstance(item, str):
                gates.append(item)
            elif isinstance(item, dict):
                for key in ("name", "gate", "id"):
                    value = item.get(key)
                    if isinstance(value, str):
                        gates.append(value)
                        break
        return gates

    candidates: list[Any] = []

    gates_container = policy.get("gates")
    if isinstance(gates_container, dict) and set_name in gates_container:
        candidates.append(gates_container.get(set_name))

    if set_name in policy:
        candidates.append(policy.get(set_name))

    for container_key in ("gate_sets", "sets"):
        container = policy.get(container_key)
        if isinstance(container, dict) and set_name in container:
            candidates.append(container.get(set_name))

    for candidate in candidates:
        gates = _normalize_gate_list(candidate)
        if gates:
            return gates

    return []


def unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def path_exists_and_nonempty(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        return any(path.iterdir())
    return path.stat().st_size > 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check PULSE-REF release-grade reference completeness."
    )

    parser.add_argument(
        "--status",
        required=True,
        type=Path,
        help="Path to candidate status.json.",
    )

    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Path to pulse_gate_policy_v0.yml or compatible gate policy.",
    )

    parser.add_argument(
        "--required-sets",
        default="required,release_required",
        help="Comma-separated policy gate sets to enforce when --policy is supplied.",
    )

    parser.add_argument(
        "--allowed-run-modes",
        default="prod",
        help="Comma-separated allowed metrics.run_mode values. Default: prod.",
    )

    parser.add_argument(
        "--require-nonstubbed",
        action="store_true",
        help="Require diagnostics.gates_stubbed == false.",
    )

    parser.add_argument(
        "--require-nonscaffolded",
        action="store_true",
        help="Require diagnostics.scaffold == false.",
    )

    parser.add_argument(
        "--require-detectors-materialized",
        action="store_true",
        help="Require gates.detectors_materialized_ok == true.",
    )

    parser.add_argument(
        "--require-external-summaries",
        action="store_true",
        help="Require gates.external_summaries_present == true and gates.external_all_pass == true.",
    )

    parser.add_argument(
        "--require-release-authority",
        type=Path,
        default=None,
        help="Require release-authority manifest file to exist and be non-empty.",
    )

    parser.add_argument(
        "--require-audit-bundle",
        type=Path,
        default=None,
        help="Require audit bundle path to exist and be non-empty.",
    )

    parser.add_argument(
        "--require-gate",
        action="append",
        default=[],
        help="Additional gate name that must be literal boolean true. Can be repeated.",
    )

    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Report failures but exit 0. Use only for advisory rollout.",
    )

    args = parser.parse_args()

    status = load_json(args.status)

    errors: list[str] = []
    notes: list[str] = []

    metrics = status.get("metrics")
    gates = status.get("gates")
    diagnostics = status.get("diagnostics", {})

    if not isinstance(metrics, dict):
        errors.append("status.metrics is missing or not an object.")
        metrics = {}

    if not isinstance(gates, dict):
        errors.append("status.gates is missing or not an object.")
        gates = {}

    if not isinstance(diagnostics, dict):
        diagnostics = {}

    run_mode = metrics.get("run_mode")
    allowed_run_modes = {
        item.strip()
        for item in args.allowed_run_modes.split(",")
        if item.strip()
    }

    if run_mode not in allowed_run_modes:
        errors.append(
            f"metrics.run_mode must be one of {sorted(allowed_run_modes)}; got {run_mode!r}."
        )
    else:
        notes.append(f"run_mode={run_mode!r} accepted.")

    if args.require_nonstubbed:
        gates_stubbed = diagnostics.get("gates_stubbed")
        if gates_stubbed is not False:
            errors.append(
                "diagnostics.gates_stubbed must be literal boolean false "
                f"for release-grade reference; got {gates_stubbed!r}."
            )
        else:
            notes.append("non-stubbed check passed: diagnostics.gates_stubbed is literal false.")

    if args.require_nonscaffolded:
        scaffold = diagnostics.get("scaffold")
        if scaffold is not False:
            errors.append(
                "diagnostics.scaffold must be literal boolean false "
                f"for release-grade reference; got {scaffold!r}."
            )
        else:
            notes.append("non-scaffolded check passed: diagnostics.scaffold is literal false.")

    if args.require_detectors_materialized:
        value = gates.get("detectors_materialized_ok")
        if not is_literal_true(value):
            errors.append(
                "gates.detectors_materialized_ok must be literal boolean true "
                f"for release-grade reference; got {value!r}."
            )
        else:
            notes.append("detectors_materialized_ok is literal true.")

    if args.require_external_summaries:
        external_present = gates.get("external_summaries_present")
        external_all_pass = gates.get("external_all_pass")

        if not is_literal_true(external_present):
            errors.append(
                "gates.external_summaries_present must be literal boolean true "
                f"for release-grade reference; got {external_present!r}."
            )
        else:
            notes.append("external_summaries_present is literal true.")

        if not is_literal_true(external_all_pass):
            errors.append(
                "gates.external_all_pass must be literal boolean true "
                f"for release-grade reference; got {external_all_pass!r}."
            )
        else:
            notes.append("external_all_pass is literal true.")

    gates_to_check: list[str] = []

    if args.policy is not None:
        policy = load_yaml(args.policy)
        required_sets = [
            item.strip()
            for item in args.required_sets.split(",")
            if item.strip()
        ]

        for set_name in required_sets:
            extracted = extract_gate_set(policy, set_name)
            if not extracted:
                errors.append(f"Policy gate set {set_name!r} is missing or empty.")
            else:
                notes.append(f"Policy gate set {set_name!r}: {len(extracted)} gate(s).")
                gates_to_check.extend(extracted)

    gates_to_check.extend(args.require_gate)
    gates_to_check = unique_preserving_order(gates_to_check)

    for gate_name in gates_to_check:
        value = gates.get(gate_name)
        if not is_literal_true(value):
            errors.append(
                f"Required release-grade gate {gate_name!r} must be literal boolean true; got {value!r}."
            )

    if gates_to_check:
        notes.append(f"Checked {len(gates_to_check)} required gate(s) for literal true.")

    if args.require_release_authority is not None:
        if not path_exists_and_nonempty(args.require_release_authority):
            errors.append(
                f"Release-authority manifest is required but missing or empty: {args.require_release_authority}"
            )
        else:
            notes.append(f"Release-authority manifest present: {args.require_release_authority}")

    if args.require_audit_bundle is not None:
        if not path_exists_and_nonempty(args.require_audit_bundle):
            errors.append(
                f"Audit bundle is required but missing or empty: {args.require_audit_bundle}"
            )
        else:
            notes.append(f"Audit bundle present: {args.require_audit_bundle}")

    print("PULSE-REF release reference completeness check")
    print("=" * 56)

    if notes:
        print("\nNotes:")
        for note in notes:
            print(f"- {note}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"- {error}")

        if args.warn_only:
            print("\nResult: WARN-ONLY FAILURES PRESENT")
            return 0

        print("\nResult: FAIL")
        return 1

    print("\nResult: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
