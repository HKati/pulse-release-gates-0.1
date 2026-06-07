#!/usr/bin/env python3
"""Check whether a run qualifies as a PULSE release-grade reference run v0.

This checker is an operational qualification tool for reference runs.

It validates that a candidate run is not merely a Core smoke run or stubbed
surface, and that it carries the expected release-grade evidence markers.

It does not compute release authority.
It does not replace check_gates.py.
It does not change status.json, gate policy, CI behavior, or shadow-layer
authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


RELEASE_REQUIRED_GATES = [
    "detectors_materialized_ok",
    "external_summaries_present",
    "external_all_pass",
    "refusal_delta_evidence_present",
]

VALID_PASS_STATES = {"PASS", "PROD-PASS"}


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        errors.append(f"{label} not found: {path}")
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI should report parse errors clearly
        errors.append(f"{label} is not valid JSON: {exc}")
        return None

    if not isinstance(data, dict):
        errors.append(f"{label} must be a JSON object")
        return None

    return data


def _section(
    obj: dict[str, Any],
    key: str,
    errors: list[str],
    label: str,
) -> dict[str, Any]:
    value = obj.get(key)
    if not isinstance(value, dict):
        errors.append(f"{label}.{key} must be an object")
        return {}
    return value


def _gate_true(gates: dict[str, Any], gate: str, errors: list[str]) -> None:
    if gates.get(gate) is not True:
        errors.append(
            f"status.gates.{gate} must be literal true "
            "for a release-grade reference run"
        )


def _check_status(status: dict[str, Any], errors: list[str]) -> None:
    metrics = _section(status, "metrics", errors, "status")
    gates = _section(status, "gates", errors, "status")

    run_mode = metrics.get("run_mode")
    if run_mode != "prod":
        errors.append(
            "status.metrics.run_mode must be 'prod' for a release-grade "
            f"reference run (got {run_mode!r})"
        )

    diagnostics = status.get("diagnostics")
    if not isinstance(diagnostics, dict):
        errors.append(
            "status.diagnostics must be an object for a release-grade reference run"
        )
    else:
        if diagnostics.get("gates_stubbed") is not False:
            errors.append(
                "status.diagnostics.gates_stubbed must be explicit false "
                "for a release-grade reference run"
            )
        if diagnostics.get("scaffold") is not False:
            errors.append(
                "status.diagnostics.scaffold must be explicit false "
                "for a release-grade reference run"
            )

    for gate in RELEASE_REQUIRED_GATES:
        _gate_true(gates, gate, errors)


def _check_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    schema_version = manifest.get("schema_version")
    if schema_version != "release_authority_v0":
        errors.append(
            "manifest.schema_version must be 'release_authority_v0' "
            f"(got {schema_version!r})"
        )

    run_identity = _section(manifest, "run_identity", errors, "manifest")
    authority = _section(manifest, "authority", errors, "manifest")
    evaluation = _section(manifest, "evaluation", errors, "manifest")
    decision = _section(manifest, "decision", errors, "manifest")

    manifest_run_mode = run_identity.get("run_mode")
    if manifest_run_mode != "prod":
        errors.append(
            f"manifest.run_identity.run_mode must be 'prod' "
            f"(got {manifest_run_mode!r})"
        )

    policy_set = authority.get("policy_set")
    if policy_set != "required+release_required":
        errors.append(
            "manifest.authority.policy_set must be 'required+release_required' "
            f"for a release-grade reference run (got {policy_set!r})"
        )

    if authority.get("release_required_materialized") is not True:
        errors.append("manifest.authority.release_required_materialized must be true")

    effective_required = authority.get("effective_required_gates")
    if not isinstance(effective_required, list):
        errors.append("manifest.authority.effective_required_gates must be an array")
        effective_required_set: set[str] = set()
    else:
        effective_required_set = {str(g) for g in effective_required}

    missing_release_required = [
        gate for gate in RELEASE_REQUIRED_GATES if gate not in effective_required_set
    ]
    if missing_release_required:
        errors.append(
            "manifest.authority.effective_required_gates must include "
            f"release-required gates: {missing_release_required}"
        )

    failed_required = evaluation.get("failed_required_gates")
    if failed_required not in ([], None):
        errors.append(
            "manifest.evaluation.failed_required_gates must be empty "
            "for a successful release-grade reference run"
        )

    missing_required = evaluation.get("missing_required_gates")
    if missing_required not in ([], None):
        errors.append(
            "manifest.evaluation.missing_required_gates must be empty "
            "for a successful release-grade reference run"
        )

    state = decision.get("state")
    if state not in VALID_PASS_STATES:
        errors.append(
            "manifest.decision.state must be PASS or PROD-PASS for a successful "
            f"release-grade reference run (got {state!r})"
        )

    if decision.get("fail_closed") is not True:
        errors.append("manifest.decision.fail_closed must be true")

    if "diagnostics" in manifest:
        diagnostics = manifest.get("diagnostics")
        if not isinstance(diagnostics, dict):
            errors.append("manifest.diagnostics must be an object when present")
        elif diagnostics.get("shadow_surfaces_non_normative") is not True:
            errors.append(
                "manifest.diagnostics.shadow_surfaces_non_normative must be true "
                "when diagnostics is present"
            )


def _check_optional_file(path: Path | None, label: str, errors: list[str]) -> None:
    if path is None:
        return
    if not path.exists():
        errors.append(f"{label} not found: {path}")


def check_release_grade_reference_run(
    status_path: Path,
    manifest_path: Path,
    report_path: Path | None = None,
    audit_bundle_dir: Path | None = None,
) -> list[str]:
    errors: list[str] = []

    status = _load_json(status_path, "status.json", errors)
    if status is not None:
        _check_status(status, errors)

    manifest = _load_json(manifest_path, "release_authority_v0.json", errors)
    if manifest is not None:
        _check_manifest(manifest, errors)

    _check_optional_file(report_path, "Quality Ledger report", errors)

    if audit_bundle_dir is not None:
        if not audit_bundle_dir.exists() or not audit_bundle_dir.is_dir():
            errors.append(
                f"release authority audit bundle directory not found: "
                f"{audit_bundle_dir}"
            )
        else:
            for name in ("report_card.html", "release_authority_v0.json", "status.json"):
                if not (audit_bundle_dir / name).exists():
                    errors.append(f"release authority audit bundle missing {name}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check whether a PULSE run qualifies as a release-grade "
            "reference run v0."
        )
    )
    parser.add_argument(
        "--status",
        default="PULSE_safe_pack_v0/artifacts/status.json",
        help="Path to the final status.json for the run.",
    )
    parser.add_argument(
        "--manifest",
        default="PULSE_safe_pack_v0/artifacts/release_authority_v0.json",
        help="Path to release_authority_v0.json for the run.",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Optional path to report_card.html / Quality Ledger.",
    )
    parser.add_argument(
        "--audit-bundle-dir",
        default=None,
        help="Optional path to release_authority_audit_bundle directory.",
    )

    args = parser.parse_args()

    errors = check_release_grade_reference_run(
        status_path=Path(args.status),
        manifest_path=Path(args.manifest),
        report_path=Path(args.report) if args.report else None,
        audit_bundle_dir=Path(args.audit_bundle_dir) if args.audit_bundle_dir else None,
    )

    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("OK: release-grade reference run criteria satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
