#!/usr/bin/env python3
"""Build a minimal content-bearing PULSE-REF evidence packet v0.

This builder produces a non-authoritative, non-release-grade packet scaffold with
minimal content payloads at canonical paths and a package digest manifest.

It does not run RA1 and does not create release authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

CANONICAL_PATHS = [
    "README.md",
    "package_manifest.json",
    "status/status.json",
    "policy/pulse_gate_policy_v0.yml",
    "policy/pulse_gate_registry_v0.yml",
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _json_text(obj: dict[str, Any]) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def _base_obj(schema: str, packet_id: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "packet_id": packet_id,
        "release_grade_evidence": False,
        "creates_release_authority": False,
        "authority_boundary": {
            "creates_release_authority": False,
            "is_release_authority": False,
            "is_ra1_verifier": False,
            "declared_policy_ci_release_decision": False,
        },
    }


def build_packet(out_dir: Path, packet_dir_name: str = "pulse_ref_evidence_packet_v0") -> Path:
    packet_root = out_dir / packet_dir_name
    packet_root.mkdir(parents=True, exist_ok=True)
    packet_id = "pulse-ref-minimal-content-packet-v0"

    _write(packet_root / "README.md", """# PULSE-REF minimal content-bearing packet v0

Status: generated minimal content packet (non-authoritative)

This packet is content-bearing, digest-backed, and reconstructable for smoke purposes.
It is not release-grade evidence.
It does not authorize, block, override, or create release authority.
It is not RA1 and not a declared-policy CI release decision.
""")

    _write(packet_root / "policy/pulse_gate_policy_v0.yml", """schema: pulse_gate_policy_v0
release_grade_evidence: false
creates_release_authority: false
note: minimal content policy stub for packet reconstruction only
""")
    _write(packet_root / "policy/pulse_gate_registry_v0.yml", """schema: pulse_gate_registry_v0
release_grade_evidence: false
creates_release_authority: false
note: minimal content registry stub for packet reconstruction only
""")

    json_files: dict[str, dict[str, Any]] = {
        "status/status.json": {**_base_obj("status_v1", packet_id), "result": "non_authoritative_placeholder_with_content"},
        "gates/materialized_gate_sets.json": {**_base_obj("pulse_ref_materialized_gate_sets_v0", packet_id), "effective_required_gates": ["q1", "q2", "q3", "q4"]},
        "ci/ci_outcome.json": {**_base_obj("pulse_ref_ci_outcome_v0", packet_id), "gate_check_conclusion": "non_authoritative_reference_only"},
        "release_authority/release_authority_manifest.json": {**_base_obj("release_authority_v0", packet_id), "release_decision": "not_authoritative"},
        "audit/release_authority_audit_bundle/status.json": {**_base_obj("status_v1", packet_id), "note": "audit copy"},
        "audit/release_authority_audit_bundle/release_authority_manifest.json": {**_base_obj("release_authority_v0", packet_id), "note": "audit copy"},
        "handoff/operator_handoff_report.json": {**_base_obj("pulse_ref_operator_handoff_report_v0", packet_id), "gate_mode": "reference"},
        "publication/publication_snapshot.json": {**_base_obj("pulse_ref_publication_snapshot_v0", packet_id), "public_surfaces": ["readme"]},
        "field/field_point_authority_map_v0.json": {**_base_obj("field_point_authority_map_v0", packet_id), "authority_status": "diagnostic_non_normative"},
        "admissibility/evidence_fold_in_admissibility_v0.json": {**_base_obj("evidence_fold_in_admissibility_v0", packet_id), "admissibility": "non_normative"},
        "hpc/hpc_evidence_bundle_v0.json": {**_base_obj("hpc_evidence_bundle_v0", packet_id), "content_class": "optional_diagnostic"},
        "recognition/recognition_surface_drift_v0.json": {**_base_obj("recognition_surface_drift_v0", packet_id), "drift_assessment": "not_evaluated"},
    }

    for rel, obj in json_files.items():
        _write(packet_root / rel, _json_text(obj))

    _write(packet_root / "audit/release_authority_audit_bundle/README.md", "Non-release-grade audit bundle placeholder with minimal content.\n")
    _write(packet_root / "audit/release_authority_audit_bundle/report_card.html", "<html><body><h1>Non-authoritative report card placeholder</h1></body></html>\n")
    _write(packet_root / "external/summaries/README.md", "External summaries are optional and non-authoritative in this packet.\n")
    _write(packet_root / "reconstruction/reconstruction_instructions.md", "Reconstruction: verify digests in digests/package_digests.json against listed files.\n")

    package_manifest = {
        **_base_obj("pulse_ref_evidence_packet_minimal_content_packet_v0", packet_id),
        "fixture_type": "minimal_content_bearing_packet",
        "canonical_paths": CANONICAL_PATHS,
        "content_bearing": True,
        "digest_backed": True,
        "reconstructable": True,
    }
    _write(packet_root / "package_manifest.json", _json_text(package_manifest))

    digest_map: dict[str, str] = {}
    for rel in CANONICAL_PATHS:
        if rel == "digests/package_digests.json":
            continue
        data = (packet_root / rel).read_bytes()
        digest_map[rel] = _sha256_bytes(data)

    package_digests = {
        **_base_obj("pulse_ref_package_digests_v0", packet_id),
        "artifact_digests_sha256": digest_map,
        "artifact_paths": sorted(digest_map.keys()),
        "missing_artifact_handling": "fail_closed",
        "unexpected_artifact_handling": "diagnostic_only",
    }
    _write(packet_root / "digests/package_digests.json", _json_text(package_digests))

    return packet_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PULSE-REF minimal content packet v0")
    parser.add_argument("--out-dir", required=True, help="Output directory where packet folder is created")
    parser.add_argument("--packet-dir-name", default="pulse_ref_evidence_packet_v0")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    packet_root = build_packet(out_dir, args.packet_dir_name)
    print(f"OK: built minimal content-bearing packet: {packet_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
