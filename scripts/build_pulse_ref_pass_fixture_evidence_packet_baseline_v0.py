#!/usr/bin/env python3
"""Build a PULSE-REF pass-fixture evidence packet baseline candidate v0.

This builder maps the guarded release_reference_v1/pass fixture into a
packet-shaped, digest-backed, reconstructable baseline candidate.

It does not create release authority.

It does not validate release-grade evidence.

It does not run RA1.

It does not replace PULSEmech.

The output is a non-normative baseline candidate for future packet and RA1 work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


PACKAGE_ROOT_NAME = "pulse_ref_evidence_packet_v0"
PACKAGE_ID = "pulse-ref-pass-fixture-evidence-packet-baseline-v0"
PACKAGE_LAYOUT_VERSION = "pulse_ref_evidence_packet_v0"
PACKAGE_BASELINE_VERSION = "pass_fixture_baseline_v0"
CREATED_UTC = "2026-05-27T00:00:00Z"

SOURCE_FIXTURE = Path("tests/fixtures/release_reference_v1/pass")
SOURCE_STATUS = SOURCE_FIXTURE / "status.json"
SOURCE_EXPECTED_OUTCOME = SOURCE_FIXTURE / "expected_outcome.json"

POLICY_PATH = Path("pulse_gate_policy_v0.yml")
REGISTRY_PATH = Path("pulse_gate_registry_v0.yml")

RELEASE_REQUIRED_GATES = [
    "detectors_materialized_ok",
    "external_summaries_present",
    "external_all_pass",
    "refusal_delta_evidence_present",
]


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} did not contain a JSON object")
    return data


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    _write(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_ref(packet_root: Path, rel_path: str) -> dict[str, str]:
    return {
        "path": rel_path,
        "sha256": _sha256_file(packet_root / rel_path),
    }


def _authority_boundary() -> dict[str, Any]:
    return {
        "creates_release_authority": False,
        "validates_release_grade_evidence": False,
        "runs_ra1": False,
        "replaces_pulsemech": False,
        "note": (
            "Pass-fixture evidence packet baseline candidate only. "
            "Non-normative reconstruction surface."
        ),
    }


def _source_identity(status: dict[str, Any]) -> dict[str, Any]:
    metrics = status.get("metrics", {})
    diagnostics = status.get("diagnostics", {})
    gates = status.get("gates", {})

    if not isinstance(metrics, dict):
        metrics = {}
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    if not isinstance(gates, dict):
        gates = {}

    return {
        "source_fixture": str(SOURCE_FIXTURE),
        "status_path": str(SOURCE_STATUS),
        "expected_outcome_path": str(SOURCE_EXPECTED_OUTCOME),
        "run_mode": metrics.get("run_mode"),
        "fixture_id": metrics.get("fixture_id"),
        "fixture_kind": metrics.get("fixture_kind"),
        "gates_stubbed": diagnostics.get("gates_stubbed"),
        "scaffold": diagnostics.get("scaffold"),
        "gate_count": len(gates),
        "all_recorded_gates_literal_true": all(value is True for value in gates.values()),
    }


def _gate_sets_from_status(status: dict[str, Any]) -> dict[str, Any]:
    gates = status.get("gates")
    if not isinstance(gates, dict):
        raise ValueError("source status is missing a gates object")

    gate_ids = list(gates.keys())
    release_required = [gate for gate in RELEASE_REQUIRED_GATES if gate in gates]
    required = [gate for gate in gate_ids if gate not in release_required]

    return {
        "schema": "pulse_ref_pass_fixture_materialized_gate_sets_v0",
        "source_fixture": str(SOURCE_FIXTURE),
        "sets": {
            "required": required,
            "release_required": release_required,
        },
        "effective_required_gates": required + release_required,
        "gate_values": {gate: gates[gate] for gate in gate_ids},
        "ordering_rule": "source status.gates insertion order",
        "duplicate_gate_handling": "first materialized gate id wins; duplicate ids are not generated",
        "authority_boundary": _authority_boundary(),
    }


def _write_readme(packet_root: Path) -> None:
    _write(
        packet_root / "README.md",
        f"""# PULSE-REF pass fixture evidence packet baseline v0

Status: generated packet-shaped baseline candidate
Authority status: non-normative
Release-grade status: not release-grade evidence
Verifier status: not a verifier
Decision status: does not authorize, block, override, or create release authority

This packet is generated from:

`{SOURCE_FIXTURE}/`

The packet preserves a guarded positive release-reference fixture as a
packet-shaped, digest-backed, reconstructable baseline candidate.

It does not create release authority.

It does not validate release-grade evidence.

It does not run RA1.

The normative PULSEmech path remains:

recorded release evidence
→ recorded `status.json` artifact
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI gate enforcement
→ declared-policy CI allow/block release decision
""",
    )


def _write_ci_outcome(packet_root: Path, status: dict[str, Any]) -> None:
    gates = status.get("gates", {})
    all_pass = isinstance(gates, dict) and all(value is True for value in gates.values())

    ci_outcome = {
        "schema": "pulse_ref_pass_fixture_ci_outcome_v0",
        "created_utc": CREATED_UTC,
        "source_fixture": str(SOURCE_FIXTURE),
        "gate_check_conclusion": "PASS" if all_pass else "FAIL",
        "declared_policy_terminal_enforcement_result": "ALLOW" if all_pass else "BLOCK",
        "fail_closed": True,
        "effective_required_gate_source": "gates/materialized_gate_sets.json",
        "authority_boundary": _authority_boundary(),
    }

    _write_json(packet_root / "ci/ci_outcome.json", ci_outcome)


def _write_release_authority_manifest(packet_root: Path) -> None:
    manifest = {
        "schema_version": "pulse_ref_pass_fixture_release_authority_manifest_v0",
        "created_utc": CREATED_UTC,
        "package_id": PACKAGE_ID,
        "status": _artifact_ref(packet_root, "status/status.json"),
        "source_expected_outcome": _artifact_ref(
            packet_root,
            "reconstruction/source_expected_outcome.json",
        ),
        "policy": _artifact_ref(packet_root, "policy/pulse_gate_policy_v0.yml"),
        "registry": _artifact_ref(packet_root, "policy/pulse_gate_registry_v0.yml"),
        "materialized_gate_sets": _artifact_ref(
            packet_root,
            "gates/materialized_gate_sets.json",
        ),
        "ci_outcome": _artifact_ref(packet_root, "ci/ci_outcome.json"),
        "decision": {
            "state": "PASS_FIXTURE_BASELINE_CANDIDATE",
            "creates_release_authority": False,
        },
        "authority_boundary": _authority_boundary(),
    }

    _write_json(packet_root / "release_authority/release_authority_manifest.json", manifest)


def _write_audit_bundle(packet_root: Path) -> None:
    audit_root = packet_root / "audit/release_authority_audit_bundle"

    _write(
        audit_root / "README.md",
        """# PULSE-REF pass fixture audit bundle

Status: non-normative audit bundle for a pass-fixture packet baseline candidate.

This bundle preserves copies of the recorded status artifact and release authority
manifest for reconstruction.

It does not create release authority.
""",
    )

    _copy(packet_root / "status/status.json", audit_root / "status.json")
    _copy(
        packet_root / "release_authority/release_authority_manifest.json",
        audit_root / "release_authority_manifest.json",
    )

    _write(
        audit_root / "report_card.html",
        """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>PULSE-REF pass fixture baseline report</title></head>
<body>
<h1>PULSE-REF pass fixture evidence packet baseline</h1>
<p>Status: non-normative packet baseline candidate.</p>
<p>This report card does not create release authority.</p>
</body>
</html>
""",
    )


def _write_operator_handoff(packet_root: Path, status: dict[str, Any]) -> None:
    handoff = {
        "schema": "pulse_ref_pass_fixture_operator_handoff_v0",
        "created_utc": CREATED_UTC,
        "package_id": PACKAGE_ID,
        "source": _source_identity(status),
        "status": _artifact_ref(packet_root, "status/status.json"),
        "expected_outcome": _artifact_ref(
            packet_root,
            "reconstruction/source_expected_outcome.json",
        ),
        "materialized_gate_sets": _artifact_ref(
            packet_root,
            "gates/materialized_gate_sets.json",
        ),
        "ci_outcome": _artifact_ref(packet_root, "ci/ci_outcome.json"),
        "reconstruction_command": (
            "python scripts/build_pulse_ref_pass_fixture_evidence_packet_baseline_v0.py "
            "--out-dir <out>"
        ),
        "authority_boundary": _authority_boundary(),
    }

    _write_json(packet_root / "handoff/operator_handoff_report.json", handoff)


def _write_publication_snapshot(packet_root: Path) -> None:
    snapshot = {
        "schema": "pulse_ref_pass_fixture_publication_snapshot_v0",
        "created_utc": CREATED_UTC,
        "package_id": PACKAGE_ID,
        "publication_surface": "pass-fixture-baseline-local-candidate",
        "public_urls": [],
        "authority_boundary": _authority_boundary(),
    }

    _write_json(packet_root / "publication/publication_snapshot.json", snapshot)


def _write_field_map(packet_root: Path) -> None:
    field_map = {
        "schema": "pulse_ref_pass_fixture_field_point_authority_map_v0",
        "created_utc": CREATED_UTC,
        "package_id": PACKAGE_ID,
        "field_points": [
            {
                "path": "status/status.json",
                "role": "recorded_status_artifact",
                "authority_status": "normative_input_for_inspected_path",
            },
            {
                "path": "ci/ci_outcome.json",
                "role": "declared_policy_terminal_enforcement_result",
                "authority_status": "normative_enforcement_output_for_inspected_path",
            },
            {
                "path": "release_authority/release_authority_manifest.json",
                "role": "trace_manifest",
                "authority_status": "non_normative_reconstruction_surface",
            },
            {
                "path": "digests/package_digests.json",
                "role": "digest_coverage",
                "authority_status": "non_normative_reconstruction_surface",
            },
        ],
        "authority_boundary": _authority_boundary(),
    }

    _write_json(packet_root / "field/field_point_authority_map_v0.json", field_map)


def _write_admissibility(packet_root: Path) -> None:
    admissibility = {
        "schema": "pulse_ref_pass_fixture_evidence_fold_in_admissibility_v0",
        "created_utc": CREATED_UTC,
        "package_id": PACKAGE_ID,
        "source_fixture": str(SOURCE_FIXTURE),
        "fold_in_requested": False,
        "admissibility_result": "not_requested",
        "authority_boundary": _authority_boundary(),
    }

    _write_json(
        packet_root / "admissibility/evidence_fold_in_admissibility_v0.json",
        admissibility,
    )


def _write_external_and_optional_surfaces(packet_root: Path) -> None:
    _write(
        packet_root / "external/summaries/README.md",
        """# External summaries

This pass-fixture baseline candidate preserves external summary state from the
source fixture.

No external summary payload is promoted into release authority by this packet.
""",
    )

    _write_json(
        packet_root / "hpc/hpc_evidence_bundle_v0.json",
        {
            "schema": "pulse_ref_pass_fixture_hpc_evidence_bundle_v0",
            "included": False,
            "role": "optional_non_normative_compute_scale_reference",
            "authority_boundary": _authority_boundary(),
        },
    )

    _write_json(
        packet_root / "recognition/recognition_surface_drift_v0.json",
        {
            "schema": "pulse_ref_pass_fixture_recognition_surface_drift_v0",
            "included": False,
            "role": "optional_non_normative_recognition_surface_reference",
            "authority_boundary": _authority_boundary(),
        },
    )


def _write_reconstruction_instructions(packet_root: Path) -> None:
    _write(
        packet_root / "reconstruction/reconstruction_instructions.md",
        """# Reconstruction instructions

This packet was generated from `tests/fixtures/release_reference_v1/pass/`.

Reconstruction steps:

1. Verify `digests/package_digests.json`.
2. Inspect `status/status.json`.
3. Inspect `policy/pulse_gate_policy_v0.yml`.
4. Inspect `policy/pulse_gate_registry_v0.yml`.
5. Inspect `gates/materialized_gate_sets.json`.
6. Inspect `ci/ci_outcome.json`.
7. Inspect `release_authority/release_authority_manifest.json`.
8. Confirm that non-normative surfaces do not create release authority.

This packet is a baseline candidate only.

It does not create release authority.
""",
    )


def _write_package_manifest(packet_root: Path, status: dict[str, Any]) -> None:
    artifacts = []
    for path in sorted(packet_root.rglob("*")):
        if path.is_file() and path.relative_to(packet_root).as_posix() != "digests/package_digests.json":
            rel_path = path.relative_to(packet_root).as_posix()
            artifacts.append(_artifact_ref(packet_root, rel_path))

    manifest = {
        "schema": "pulse_ref_pass_fixture_package_manifest_v0",
        "package_id": PACKAGE_ID,
        "package_layout_version": PACKAGE_LAYOUT_VERSION,
        "package_baseline_version": PACKAGE_BASELINE_VERSION,
        "created_utc": CREATED_UTC,
        "source": _source_identity(status),
        "artifacts": artifacts,
        "authority_boundary": _authority_boundary(),
    }

    _write_json(packet_root / "package_manifest.json", manifest)


def _write_package_digests(packet_root: Path) -> None:
    digests: dict[str, str] = {}

    for path in sorted(packet_root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(packet_root).as_posix()
        if rel_path == "digests/package_digests.json":
            continue
        digests[rel_path] = _sha256_file(path)

    payload = {
        "schema": "pulse_ref_pass_fixture_package_digests_v0",
        "package_id": PACKAGE_ID,
        "created_utc": CREATED_UTC,
        "algorithm": "sha256",
        "digests": digests,
        "authority_boundary": _authority_boundary(),
    }

    _write_json(packet_root / "digests/package_digests.json", payload)


def build(out_dir: Path) -> Path:
    repo_root = Path.cwd()

    source_status = repo_root / SOURCE_STATUS
    source_expected = repo_root / SOURCE_EXPECTED_OUTCOME
    policy = repo_root / POLICY_PATH
    registry = repo_root / REGISTRY_PATH

    for path in [source_status, source_expected, policy, registry]:
        if not path.is_file():
            raise FileNotFoundError(path)

    packet_root = out_dir / PACKAGE_ROOT_NAME

    if packet_root.exists():
        shutil.rmtree(packet_root)

    packet_root.mkdir(parents=True, exist_ok=True)

    status = _load_json(source_status)
    expected = _load_json(source_expected)

    _write_readme(packet_root)
    _copy(source_status, packet_root / "status/status.json")
    _copy(source_expected, packet_root / "reconstruction/source_expected_outcome.json")
    _copy(policy, packet_root / "policy/pulse_gate_policy_v0.yml")
    _copy(registry, packet_root / "policy/pulse_gate_registry_v0.yml")

    _write_json(packet_root / "gates/materialized_gate_sets.json", _gate_sets_from_status(status))
    _write_ci_outcome(packet_root, status)
    _write_release_authority_manifest(packet_root)
    _write_audit_bundle(packet_root)
    _write_operator_handoff(packet_root, status)
    _write_publication_snapshot(packet_root)
    _write_field_map(packet_root)
    _write_admissibility(packet_root)
    _write_external_and_optional_surfaces(packet_root)
    _write_reconstruction_instructions(packet_root)

    # Keep expected loaded so invalid JSON fails early and is not silently ignored.
    if expected.get("expected_result") != "PASS":
        raise ValueError("source expected_outcome.json must declare PASS")

    _write_package_manifest(packet_root, status)
    _write_package_digests(packet_root)

    return packet_root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Output directory that will contain pulse_ref_evidence_packet_v0/.",
    )
    args = parser.parse_args()

    packet_root = build(args.out_dir)
    print(f"OK: wrote {packet_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
