#!/usr/bin/env python3
"""Build a minimal content-bearing PULSE-REF evidence packet v0.

This builder creates a generated bridge fixture between the existing
PULSE-REF layout skeleton and future release-grade evidence packets.

The packet is intentionally:

- content-bearing;
- digest-backed;
- reconstructable;
- non-release-grade;
- not RA1 verifier output;
- not release authority;
- not a declared-policy CI release decision.

Important schema rule:

When this builder uses an existing strict schema name, the emitted payload must
match that schema. For minimal/non-normative diagnostic artifacts that are not
being validated against existing strict schemas, this builder uses explicit
minimal-content schema names instead of pretending to satisfy stricter contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


CREATED_UTC = "2026-05-24T00:00:00Z"
PACKAGE_ID = "pulse-ref-minimal-content-packet-v0"
RUN_KEY = "pulse-ref-minimal-content-packet-v0"
GIT_SHA = "0000000000000000000000000000000000000000"
REPOSITORY = "HKati/pulse-release-gates-0.1"
RUN_ID = "0"
RUN_ATTEMPT = 1
RUN_URL = f"https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}"

POLICY_PATH = "policy/pulse_gate_policy_v0.yml"
REGISTRY_PATH = "policy/pulse_gate_registry_v0.yml"

REQUIRED_GATES = [
    "pass_controls_refusal",
    "pass_controls_sanit",
    "sanitization_effective",
    "q1_grounded_ok",
    "q4_slo_ok",
]

RELEASE_REQUIRED_GATES = [
    "detectors_materialized_ok",
    "external_summaries_present",
    "external_all_pass",
    "refusal_delta_evidence_present",
]

CANONICAL_PATHS = [
    "README.md",
    "package_manifest.json",
    "status/status.json",
    POLICY_PATH,
    REGISTRY_PATH,
    "gates/materialized_gate_sets.json",
    "ci/ci_outcome.json",
    "release_authority/release_authority_manifest.json",
    "audit/release_authority_audit_bundle/README.md",
    "audit/release_authority_audit_bundle/report_card.html",
    "audit/release_authority_audit_bundle/status.json",
    "audit/release_authority_audit_bundle/release_authority_manifest.json",
    "digests/package_digests.json",
    "handoff/operator_handoff_report.json",
    "publication/publication_snapshot.json",
    "field/field_point_authority_map_v0.json",
    "admissibility/evidence_fold_in_admissibility_v0.json",
    "external/summaries/README.md",
    "hpc/hpc_evidence_bundle_v0.json",
    "recognition/recognition_surface_drift_v0.json",
    "reconstruction/reconstruction_instructions.md",
]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    _write(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _artifact_ref(packet_root: Path, rel_path: str) -> dict[str, str]:
    return {
        "path": rel_path,
        "sha256": _sha256_file(packet_root / rel_path),
    }


def _authority_boundary_note() -> dict[str, Any]:
    return {
        "creates_release_authority": False,
        "is_release_authority": False,
        "is_ra1_verifier_output": False,
        "declared_policy_ci_release_decision": False,
        "note": (
            "Minimal content-bearing packet fixture only. "
            "Not release-grade evidence and not release authority."
        ),
    }


def _write_readme(packet_root: Path) -> None:
    _write(
        packet_root / "README.md",
        """# PULSE-REF minimal content-bearing packet v0

Status: generated minimal content-bearing packet fixture
Authority status: non-normative
Release-grade status: not release-grade evidence
RA1 status: not RA1 verifier output
Decision status: not a declared-policy CI release decision

This packet is content-bearing, digest-backed, and reconstructable for smoke
testing the bridge between the PULSE-REF layout skeleton and future
release-grade evidence packets.

It does not validate release-grade evidence.

It does not run RA1.

It does not authorize, block, override, or create release authority.

The normative PULSE release decision remains:

recorded release evidence
→ status.json
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI gate enforcement
→ declared-policy CI allow/block release decision
""",
    )


def _write_policy_and_registry(packet_root: Path) -> None:
    _write(
        packet_root / POLICY_PATH,
        """policy:
  id: pulse_ref_minimal_content_policy_v0
  version: "0"
schema: pulse_gate_policy_v0
fixture_type: minimal_content_bearing_packet
release_grade_evidence: false
creates_release_authority: false
gates:
  required:
    - pass_controls_refusal
    - pass_controls_sanit
    - sanitization_effective
    - q1_grounded_ok
    - q4_slo_ok
  release_required:
    - detectors_materialized_ok
    - external_summaries_present
    - external_all_pass
    - refusal_delta_evidence_present
authority_boundary:
  creates_release_authority: false
  note: minimal content policy fixture for packet reconstruction only
""",
    )

    registry_lines = [
        "schema: pulse_gate_registry_v0",
        "fixture_type: minimal_content_bearing_packet",
        "release_grade_evidence: false",
        "creates_release_authority: false",
        "gates:",
    ]

    for gate_id in REQUIRED_GATES + RELEASE_REQUIRED_GATES:
        registry_lines.extend(
            [
                f"  - id: {gate_id}",
                "    authority_role: registered_gate_id",
                "    creates_release_authority: false",
            ]
        )

    registry_lines.extend(
        [
            "authority_boundary:",
            "  creates_release_authority: false",
            "  note: minimal content registry fixture for packet reconstruction only",
            "",
        ]
    )

    _write(packet_root / REGISTRY_PATH, "\n".join(registry_lines))


def _status_obj() -> dict[str, Any]:
    gates: dict[str, bool] = {gate_id: True for gate_id in REQUIRED_GATES}
    gates.update({gate_id: False for gate_id in RELEASE_REQUIRED_GATES})

    return {
        "version": "status_v1",
        "created_utc": CREATED_UTC,
        "fixture_type": "minimal_content_bearing_packet",
        "release_grade_evidence": False,
        "creates_release_authority": False,
        "gates": gates,
        "metrics": {
            "run_mode": "core",
            "git_sha": GIT_SHA,
            "run_key": RUN_KEY,
            "gate_policy_path": POLICY_PATH,
        },
        "diagnostics": {
            "minimal_content_fixture": True,
            "release_grade_reference": False,
            "gates_stubbed": False,
            "scaffold": False,
            "not_ra1_verifier_output": True,
            "not_declared_policy_ci_release_decision": True,
        },
        "external": {
            "all_pass": False,
            "summaries_present": False,
            "summary_count": 0,
            "metrics": [],
        },
        "external_all_pass": False,
        "external_summaries_present": False,
        "authority_boundary": _authority_boundary_note(),
    }


def _write_status_and_gate_surfaces(packet_root: Path) -> None:
    _write_json(packet_root / "status/status.json", _status_obj())

    policy_sha = _sha256_file(packet_root / POLICY_PATH)

    materialized_gate_sets = {
        "schema": "pulse_ref_materialized_gate_sets_v0",
        "policy_path": POLICY_PATH,
        "policy_sha256": policy_sha,
        "sets": {
            "required": REQUIRED_GATES,
            "release_required": RELEASE_REQUIRED_GATES,
        },
        "effective_required_gates": REQUIRED_GATES,
        "authority_boundary": {
            "source": "declared_gate_policy",
            "materialization_role": "required_gate_set_reconstruction",
            "creates_release_authority": False,
        },
    }

    _write_json(
        packet_root / "gates/materialized_gate_sets.json",
        materialized_gate_sets,
    )

    ci_outcome = {
        "schema": "pulse_ref_ci_outcome_v0",
        "provider": "github_actions",
        "workflow": "minimal-content-packet-fixture",
        "run_id": RUN_ID,
        "run_attempt": RUN_ATTEMPT,
        "run_url": RUN_URL,
        "repository": REPOSITORY,
        "commit_sha": GIT_SHA,
        "gate_check_job": "minimal-content-packet-smoke",
        "gate_check_conclusion": "neutral",
        "created_utc": CREATED_UTC,
        "started_utc": CREATED_UTC,
        "completed_utc": CREATED_UTC,
        "authority_boundary": {
            "normative_decision_path": (
                "Not a declared-policy release decision; "
                "minimal content-bearing packet fixture only."
            ),
            "ci_role": "records_declared_policy_enforcement",
            "creates_release_authority": False,
        },
    }

    _write_json(packet_root / "ci/ci_outcome.json", ci_outcome)


def _release_authority_obj(packet_root: Path) -> dict[str, Any]:
    status_ref = _artifact_ref(packet_root, "status/status.json")
    policy_ref = _artifact_ref(packet_root, POLICY_PATH)
    registry_ref = _artifact_ref(packet_root, REGISTRY_PATH)
    ci_ref = _artifact_ref(packet_root, "ci/ci_outcome.json")

    return {
        "schema_version": "release_authority_v0",
        "created_utc": CREATED_UTC,
        "run_identity": {
            "run_mode": "core",
            "workflow_name": "minimal-content-packet-fixture",
            "event_name": "fixture",
            "ref": "refs/heads/minimal-content-fixture",
            "git_sha": GIT_SHA,
            "run_id": RUN_ID,
            "attempt": RUN_ATTEMPT,
            "actor": "pulse-ref-fixture",
        },
        "inputs": {
            "status_json": status_ref,
            "gate_policy": {
                **policy_ref,
                "policy_id": "pulse_ref_minimal_content_policy_v0",
                "version": "0",
            },
            "gate_registry": {
                **registry_ref,
                "version": "0",
            },
            "evaluator": ci_ref,
        },
        "authority": {
            "policy_set": "core_required",
            "effective_required_gates": REQUIRED_GATES,
            "release_required_materialized": False,
            "advisory_gates": [],
        },
        "evaluation": {
            "evaluator": "minimal-content-packet-builder",
            "required_gate_results": {gate_id: True for gate_id in REQUIRED_GATES},
            "failed_required_gates": [],
            "missing_required_gates": [],
        },
        "decision": {
            "state": "UNKNOWN",
            "fail_closed": True,
        },
        "diagnostics": {
            "shadow_surfaces_present": [],
            "shadow_surfaces_non_normative": True,
            "status_meta_foldins": [],
            "advisory_gates_present": [],
            "publication_surfaces_present": [
                {
                    "name": "minimal_content_publication_snapshot",
                    "role": "publication",
                    "path": "publication/publication_snapshot.json",
                    "normative": False,
                }
            ],
        },
    }


def _write_release_authority_and_audit(packet_root: Path) -> None:
    release_authority = _release_authority_obj(packet_root)

    _write_json(
        packet_root / "release_authority/release_authority_manifest.json",
        release_authority,
    )

    _write_json(
        packet_root / "audit/release_authority_audit_bundle/status.json",
        _status_obj(),
    )

    _write_json(
        packet_root
        / "audit/release_authority_audit_bundle/release_authority_manifest.json",
        release_authority,
    )

    _write(
        packet_root / "audit/release_authority_audit_bundle/README.md",
        """# Minimal content audit bundle

This audit bundle is part of a minimal content-bearing packet fixture.

It is not a release-grade audit bundle.

It does not authorize, block, override, or create release authority.
""",
    )

    _write(
        packet_root / "audit/release_authority_audit_bundle/report_card.html",
        """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>PULSE-REF minimal content report card</title></head>
<body>
<h1>PULSE-REF minimal content report card</h1>
<p>This is not a release-grade report card.</p>
<p>It does not create release authority.</p>
<p>It is not RA1 verifier output.</p>
</body>
</html>
""",
    )


def _write_handoff_publication_and_diagnostics(packet_root: Path) -> None:
    status_sha = _sha256_file(packet_root / "status/status.json")

    handoff = {
        "schema": "pulse_ref_minimal_content_operator_handoff_v0",
        "fixture_type": "minimal_content_bearing_packet",
        "package_id": PACKAGE_ID,
        "run_key": RUN_KEY,
        "git_sha": GIT_SHA,
        "created_utc": CREATED_UTC,
        "status_source": {
            "mode": "generated_minimal_content_fixture",
            "status_path": "status/status.json",
            "status_sha256": status_sha,
        },
        "materialized_gate_sets": {
            "required": REQUIRED_GATES,
            "release_required": RELEASE_REQUIRED_GATES,
        },
        "effective_required_gates": REQUIRED_GATES,
        "validation_commands": [
            "python scripts/build_pulse_ref_minimal_content_packet_v0.py --out-dir <out>",
            "python tests/test_pulse_ref_minimal_content_packet_v0.py",
        ],
        "release_grade_evidence": False,
        "creates_release_authority": False,
        "authority_boundary": _authority_boundary_note(),
    }

    _write_json(packet_root / "handoff/operator_handoff_report.json", handoff)

    publication = {
        "schema": "pulse_ref_publication_snapshot_v0",
        "snapshot_created_utc": CREATED_UTC,
        "package_id": PACKAGE_ID,
        "run_key": RUN_KEY,
        "git_sha": GIT_SHA,
        "quality_ledger_url": (
            "https://example.invalid/pulse-ref/minimal-content/quality-ledger"
        ),
        "status_json_url": (
            "https://example.invalid/pulse-ref/minimal-content/status.json"
        ),
        "release_authority_manifest_url": (
            "https://example.invalid/pulse-ref/minimal-content/"
            "release_authority_manifest.json"
        ),
        "audit_bundle_url": (
            "https://example.invalid/pulse-ref/minimal-content/audit-bundle"
        ),
        "operator_handoff_report_url": (
            "https://example.invalid/pulse-ref/minimal-content/operator-handoff.json"
        ),
        "ci_outcome_url": RUN_URL,
        "package_manifest_url": (
            "https://example.invalid/pulse-ref/minimal-content/package_manifest.json"
        ),
        "package_digests_url": (
            "https://example.invalid/pulse-ref/minimal-content/package_digests.json"
        ),
        "publication_surface": "minimal-content-fixture-placeholder-url-set",
        "creates_release_authority": False,
    }

    _write_json(packet_root / "publication/publication_snapshot.json", publication)

    field_map = {
        "schema": "pulse_ref_minimal_content_field_point_authority_map_v0",
        "fixture_type": "minimal_content_bearing_packet",
        "package_id": PACKAGE_ID,
        "authority_status": "diagnostic_non_normative",
        "normative_materialization_path": [
            "recorded release evidence",
            "status.json",
            "declared gate policy",
            "materialized required gate set",
            "strict fail-closed CI gate enforcement",
            "declared-policy CI allow/block release decision",
        ],
        "field_points": [
            {
                "path": "status/status.json",
                "role": "minimal_status_artifact",
                "authority_status": "non_release_grade_input_fixture",
            },
            {
                "path": "ci/ci_outcome.json",
                "role": "minimal_ci_outcome_fixture",
                "authority_status": "not_declared_policy_release_decision",
            },
        ],
        "release_grade_evidence": False,
        "creates_release_authority": False,
        "authority_boundary": _authority_boundary_note(),
    }

    _write_json(packet_root / "field/field_point_authority_map_v0.json", field_map)

    admissibility = {
        "schema": "pulse_ref_minimal_content_evidence_fold_in_admissibility_v0",
        "fixture_type": "minimal_content_bearing_packet",
        "package_id": PACKAGE_ID,
        "result": "advisory_only",
        "candidates": [],
        "release_grade_evidence": False,
        "creates_release_authority": False,
        "authority_boundary": _authority_boundary_note(),
    }

    _write_json(
        packet_root / "admissibility/evidence_fold_in_admissibility_v0.json",
        admissibility,
    )

    hpc_bundle = {
        "schema": "pulse_ref_minimal_content_hpc_evidence_bundle_v0",
        "fixture_type": "minimal_content_bearing_packet",
        "package_id": PACKAGE_ID,
        "content_class": "optional_diagnostic",
        "result": "not_evaluated",
        "release_grade_evidence": False,
        "creates_release_authority": False,
        "authority_boundary": _authority_boundary_note(),
    }

    _write_json(packet_root / "hpc/hpc_evidence_bundle_v0.json", hpc_bundle)

    recognition = {
        "schema": "pulse_ref_minimal_content_recognition_surface_drift_v0",
        "fixture_type": "minimal_content_bearing_packet",
        "package_id": PACKAGE_ID,
        "drift_assessment": "not_evaluated",
        "release_grade_evidence": False,
        "creates_release_authority": False,
        "authority_boundary": _authority_boundary_note(),
    }

    _write_json(
        packet_root / "recognition/recognition_surface_drift_v0.json",
        recognition,
    )

    _write(
        packet_root / "external/summaries/README.md",
        """# External summaries

This minimal content-bearing packet does not include canonical external detector
summaries.

External summaries are optional diagnostic candidate evidence here.

This file does not satisfy release-grade external evidence requirements.

It does not create release authority.
""",
    )

    _write(
        packet_root / "reconstruction/reconstruction_instructions.md",
        """# Reconstruction instructions

1. Verify `digests/package_digests.json`.
2. Verify each listed artifact SHA-256 digest.
3. Verify that strict-schema artifacts validate against their declared schemas.
4. Confirm this packet is not release-grade evidence.
5. Confirm this packet is not RA1 verifier output.
6. Confirm this packet is not a declared-policy CI release decision.

This skeleton is not reconstructable release-grade evidence.

This packet does not create release authority.
""",
    )


def _write_package_manifest(packet_root: Path) -> None:
    manifest = {
        "schema": "pulse_ref_minimal_content_packet_manifest_v0",
        "fixture_type": "minimal_content_bearing_packet",
        "package_id": PACKAGE_ID,
        "created_utc": CREATED_UTC,
        "run_key": RUN_KEY,
        "git_sha": GIT_SHA,
        "canonical_paths": CANONICAL_PATHS,
        "content_bearing": True,
        "digest_backed": True,
        "reconstructable": True,
        "release_grade_evidence": False,
        "creates_release_authority": False,
        "not_ra1_verifier_output": True,
        "not_declared_policy_ci_release_decision": True,
        "digest_manifest_path": "digests/package_digests.json",
        "authority_boundary": _authority_boundary_note(),
    }

    _write_json(packet_root / "package_manifest.json", manifest)


def _write_package_digests(packet_root: Path) -> None:
    artifacts: dict[str, str] = {}

    for rel_path in CANONICAL_PATHS:
        if rel_path == "digests/package_digests.json":
            continue

        artifacts[rel_path] = _sha256_file(packet_root / rel_path)

    package_digests = {
        "schema": "pulse_ref_package_digests_v0",
        "algorithm": "sha256",
        "created_utc": CREATED_UTC,
        "package_id": PACKAGE_ID,
        "artifacts": artifacts,
        "authority_boundary": {
            "digest_role": "artifact_integrity_verification",
            "creates_release_authority": False,
        },
    }

    _write_json(packet_root / "digests/package_digests.json", package_digests)


def build_packet(
    out_dir: Path,
    packet_dir_name: str = "pulse_ref_evidence_packet_v0",
) -> Path:
    packet_root = out_dir / packet_dir_name

    if packet_root.exists():
        shutil.rmtree(packet_root)

    packet_root.mkdir(parents=True, exist_ok=True)

    _write_readme(packet_root)
    _write_policy_and_registry(packet_root)
    _write_status_and_gate_surfaces(packet_root)
    _write_release_authority_and_audit(packet_root)
    _write_handoff_publication_and_diagnostics(packet_root)
    _write_package_manifest(packet_root)
    _write_package_digests(packet_root)

    return packet_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build PULSE-REF minimal content packet v0."
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Output directory where the packet folder is created.",
    )
    parser.add_argument(
        "--packet-dir-name",
        default="pulse_ref_evidence_packet_v0",
        help="Packet directory name under --out-dir.",
    )
    args = parser.parse_args()

    packet_root = build_packet(
        out_dir=Path(args.out_dir),
        packet_dir_name=args.packet_dir_name,
    )

    print(f"OK: built minimal content-bearing packet: {packet_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
