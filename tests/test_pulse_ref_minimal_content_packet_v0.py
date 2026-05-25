#!/usr/bin/env python3
"""Smoke tests for build_pulse_ref_minimal_content_packet_v0.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_pulse_ref_minimal_content_packet_v0.py"

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

STRICT_SCHEMA_TARGETS = {
    "status/status.json": "schemas/status/status_v1.schema.json",
    "audit/release_authority_audit_bundle/status.json": (
        "schemas/status/status_v1.schema.json"
    ),
    "gates/materialized_gate_sets.json": (
        "schemas/pulse_ref_materialized_gate_sets_v0.schema.json"
    ),
    "ci/ci_outcome.json": "schemas/pulse_ref_ci_outcome_v0.schema.json",
    "release_authority/release_authority_manifest.json": (
        "schemas/release_authority_v0.schema.json"
    ),
    "audit/release_authority_audit_bundle/release_authority_manifest.json": (
        "schemas/release_authority_v0.schema.json"
    ),
    "publication/publication_snapshot.json": (
        "schemas/pulse_ref_publication_snapshot_v0.schema.json"
    ),
    "digests/package_digests.json": "schemas/pulse_ref_package_digests_v0.schema.json",
}

SKELETON_PLACEHOLDER_MARKERS = [
    "pulse_ref_evidence_packet_layout_placeholder_v0",
    "layout_skeleton_placeholder",
]

FORBIDDEN_DIRECT_CLAIMS = [
    "This document creates release authority.",
    "This packet creates release authority.",
    "This packet is release-grade evidence.",
    "This packet is RA1 verifier output.",
    "This packet is a declared-policy CI release decision.",
]


def _run(out_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--out-dir",
            str(out_dir),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(obj, dict)
    return obj


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema_errors(instance: dict[str, Any], schema_path: Path) -> list[str]:
    schema = _read_json(schema_path)
    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )

    return [
        f"{list(error.absolute_path)}: {error.message}"
        for error in errors
    ]


def _walk_json(value: Any) -> list[Any]:
    found = [value]

    if isinstance(value, dict):
        for child in value.values():
            found.extend(_walk_json(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_json(child))

    return found


def _assert_no_authority_claim(obj: dict[str, Any], rel_path: str) -> None:
    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key == "creates_release_authority":
                    assert child is False, f"{rel_path}: {child_path} must be false"
                if key == "release_grade_evidence":
                    assert child is False, f"{rel_path}: {child_path} must be false"
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(obj, "$")


def _build_packet() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    td = tempfile.TemporaryDirectory()
    out = Path(td.name)
    result = _run(out)

    assert result.returncode == 0, result.stdout + result.stderr

    packet_root = out / "pulse_ref_evidence_packet_v0"
    assert packet_root.is_dir()

    return td, packet_root


def test_minimal_packet_builder_creates_canonical_files() -> None:
    td, packet_root = _build_packet()

    try:
        for rel_path in CANONICAL_PATHS:
            assert (packet_root / rel_path).is_file(), rel_path
    finally:
        td.cleanup()


def test_minimal_packet_builder_avoids_skeleton_placeholder_markers() -> None:
    td, packet_root = _build_packet()

    try:
        combined = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in packet_root.rglob("*")
            if path.is_file()
        )

        for marker in SKELETON_PLACEHOLDER_MARKERS:
            assert marker not in combined, marker

        for claim in FORBIDDEN_DIRECT_CLAIMS:
            assert claim not in combined, claim
    finally:
        td.cleanup()


def test_minimal_packet_builder_strict_schema_payloads_validate() -> None:
    td, packet_root = _build_packet()

    try:
        for rel_path, schema_rel in STRICT_SCHEMA_TARGETS.items():
            instance = _read_json(packet_root / rel_path)
            schema_path = ROOT / schema_rel

            errors = _schema_errors(instance, schema_path)
            assert errors == [], f"{rel_path}: {errors}"
    finally:
        td.cleanup()


def test_minimal_packet_preserves_non_authority_boundary() -> None:
    td, packet_root = _build_packet()

    try:
        manifest = _read_json(packet_root / "package_manifest.json")

        assert manifest["content_bearing"] is True
        assert manifest["digest_backed"] is True
        assert manifest["reconstructable"] is True
        assert manifest["release_grade_evidence"] is False
        assert manifest["creates_release_authority"] is False
        assert manifest["not_ra1_verifier_output"] is True
        assert manifest["not_declared_policy_ci_release_decision"] is True

        for rel_path in CANONICAL_PATHS:
            if not rel_path.endswith(".json"):
                continue

            obj = _read_json(packet_root / rel_path)
            _assert_no_authority_claim(obj, rel_path)

            for value in _walk_json(obj):
                if isinstance(value, str):
                    assert "This document creates release authority." not in value
                    assert "This packet creates release authority." not in value
                    assert "This packet is release-grade evidence." not in value

    finally:
        td.cleanup()


def test_minimal_packet_status_and_ci_remain_non_release_grade() -> None:
    td, packet_root = _build_packet()

    try:
        status = _read_json(packet_root / "status/status.json")
        ci_outcome = _read_json(packet_root / "ci/ci_outcome.json")
        release_authority = _read_json(
            packet_root / "release_authority/release_authority_manifest.json"
        )

        assert status["metrics"]["run_mode"] == "core"
        assert status["diagnostics"]["release_grade_reference"] is False
        assert status["diagnostics"]["not_ra1_verifier_output"] is True
        assert status["diagnostics"]["not_declared_policy_ci_release_decision"] is True
        assert status["gates"]["detectors_materialized_ok"] is False
        assert status["gates"]["external_summaries_present"] is False
        assert status["gates"]["external_all_pass"] is False
        assert status["gates"]["refusal_delta_evidence_present"] is False

        assert ci_outcome["gate_check_conclusion"] == "neutral"
        assert ci_outcome["authority_boundary"]["creates_release_authority"] is False
        assert "not a declared-policy release decision" in (
            ci_outcome["authority_boundary"]["normative_decision_path"].lower()
        )

        assert release_authority["run_identity"]["run_mode"] == "core"
        assert release_authority["authority"]["policy_set"] == "core_required"
        assert release_authority["authority"]["release_required_materialized"] is False
        assert release_authority["decision"]["state"] == "UNKNOWN"
        assert release_authority["decision"]["fail_closed"] is True
        assert (
            release_authority["diagnostics"]["shadow_surfaces_non_normative"]
            is True
        )
    finally:
        td.cleanup()


def test_minimal_packet_digest_manifest_matches_payload_files() -> None:
    td, packet_root = _build_packet()

    try:
        digests = _read_json(packet_root / "digests/package_digests.json")

        assert digests["schema"] == "pulse_ref_package_digests_v0"
        assert digests["algorithm"] == "sha256"
        assert "artifacts" in digests

        assert "artifact_digests_sha256" not in digests
        assert "artifact_paths" not in digests
        assert "digests/package_digests.json" not in digests["artifacts"]

        for rel_path, expected_sha256 in digests["artifacts"].items():
            assert rel_path in CANONICAL_PATHS, rel_path
            assert (packet_root / rel_path).is_file(), rel_path
            assert _sha256(packet_root / rel_path) == expected_sha256, rel_path
    finally:
        td.cleanup()


def main() -> int:
    try:
        test_minimal_packet_builder_creates_canonical_files()
        test_minimal_packet_builder_avoids_skeleton_placeholder_markers()
        test_minimal_packet_builder_strict_schema_payloads_validate()
        test_minimal_packet_preserves_non_authority_boundary()
        test_minimal_packet_status_and_ci_remain_non_release_grade()
        test_minimal_packet_digest_manifest_matches_payload_files()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF minimal content packet builder smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
