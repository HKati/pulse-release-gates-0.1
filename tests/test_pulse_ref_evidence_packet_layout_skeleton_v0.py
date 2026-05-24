#!/usr/bin/env python3
"""Smoke tests for the PULSE-REF evidence packet layout skeleton."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET_ROOT = (
    ROOT
    / "tests"
    / "fixtures"
    / "pulse_ref"
    / "evidence_packet_layout_skeleton_v0"
    / "pulse_ref_evidence_packet_v0"
)

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


def _copy_skeleton() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    td = tempfile.TemporaryDirectory()
    packet_root = Path(td.name) / "pulse_ref_evidence_packet_v0"
    shutil.copytree(PACKET_ROOT, packet_root)
    return td, packet_root


def _run_checker(packet_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "check_pulse_ref_evidence_packet_layout_skeleton_v0.py"),
            "--packet-root",
            str(packet_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(obj, dict), f"{path} must contain a JSON object"
    return obj


def test_layout_skeleton_root_exists() -> None:
    assert PACKET_ROOT.is_dir()


def test_all_canonical_paths_exist() -> None:
    missing = [
        rel_path
        for rel_path in CANONICAL_PATHS
        if not (PACKET_ROOT / rel_path).is_file()
    ]

    assert missing == []


def test_package_manifest_lists_canonical_paths() -> None:
    manifest = _read_json(PACKET_ROOT / "package_manifest.json")

    assert manifest["schema"] == "pulse_ref_evidence_packet_layout_skeleton_v0"
    assert manifest["fixture_type"] == "layout_skeleton"
    assert manifest["release_grade_evidence"] is False
    assert manifest["creates_release_authority"] is False
    assert manifest["authority_boundary"]["creates_release_authority"] is False

    listed = manifest["canonical_paths"]
    assert sorted(listed) == sorted(CANONICAL_PATHS)


def test_json_placeholders_do_not_create_release_authority() -> None:
    json_paths = [
        rel_path
        for rel_path in CANONICAL_PATHS
        if rel_path.endswith(".json")
    ]

    for rel_path in json_paths:
        obj = _read_json(PACKET_ROOT / rel_path)
        assert obj.get("creates_release_authority") is False, rel_path

        boundary = obj.get("authority_boundary")
        if isinstance(boundary, dict):
            assert boundary.get("creates_release_authority") is False, rel_path


def test_root_readme_disclaims_release_grade_authority() -> None:
    text = (PACKET_ROOT / "README.md").read_text(encoding="utf-8")

    required = [
        "layout skeleton fixture",
        "not release-grade evidence",
        "does not authorize, block, override, or create release authority",
        "recorded release evidence",
        "status.json",
        "declared gate policy",
        "materialized required gate set",
        "strict fail-closed CI gate enforcement",
    ]

    for token in required:
        assert token in text, token


def test_reconstruction_instructions_disclaim_release_authority() -> None:
    text = (
        PACKET_ROOT
        / "reconstruction"
        / "reconstruction_instructions.md"
    ).read_text(encoding="utf-8")

    assert "This skeleton is not reconstructable release-grade evidence." in text
    assert "This skeleton does not create release authority." in text



def test_checker_rejects_yaml_placeholder_structural_authority_claim() -> None:
    td, packet_root = _copy_skeleton()

    try:
        policy_path = packet_root / "policy" / "pulse_gate_policy_v0.yml"

        policy_path.write_text(
            "schema: pulse_ref_evidence_packet_layout_placeholder_v0\n"
            "fixture_type: layout_skeleton_placeholder\n"
            "release_grade_evidence: false\n"
            "creates_release_authority: true\n"
            "authority_boundary:\n"
            "  creates_release_authority: true\n"
            "  note: \"contains creates_release_authority: false as text only\"\n"
            "placeholder_path: policy/pulse_gate_policy_v0.yml\n",
            encoding="utf-8",
        )

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "policy/pulse_gate_policy_v0.yml" in combined
        assert "creates_release_authority" in combined
        assert "authority_boundary.creates_release_authority must be false" in combined
    finally:
        td.cleanup()


def test_checker_rejects_root_readme_contradictory_authority_claim() -> None:
    td, packet_root = _copy_skeleton()

    try:
        readme_path = packet_root / "README.md"
        readme_path.write_text(
            readme_path.read_text(encoding="utf-8")
            + "\n\nThis skeleton creates release authority.\n",
            encoding="utf-8",
        )

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "README.md" in combined
        assert "contradictory authority claim" in combined
    finally:
        td.cleanup()


def test_checker_rejects_audit_readme_contradictory_authority_claim() -> None:
    td, packet_root = _copy_skeleton()

    try:
        audit_readme_path = (
            packet_root
            / "audit"
            / "release_authority_audit_bundle"
            / "README.md"
        )

        audit_readme_path.write_text(
            audit_readme_path.read_text(encoding="utf-8")
            + "\n\nThis audit bundle creates release authority.\n",
            encoding="utf-8",
        )

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "audit/release_authority_audit_bundle/README.md" in combined
        assert "contradictory authority claim" in combined
    finally:
        td.cleanup()


def test_checker_rejects_external_summaries_readme_contradictory_authority_claim() -> None:
    td, packet_root = _copy_skeleton()

    try:
        external_readme_path = packet_root / "external" / "summaries" / "README.md"

        external_readme_path.write_text(
            external_readme_path.read_text(encoding="utf-8")
            + "\n\nThis external summaries directory satisfies release-grade external evidence requirements.\n",
            encoding="utf-8",
        )

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "external/summaries/README.md" in combined
        assert "contradictory authority claim" in combined
    finally:
        td.cleanup()


def test_checker_rejects_reconstruction_contradictory_authority_claim() -> None:
    td, packet_root = _copy_skeleton()

    try:
        reconstruction_path = (
            packet_root
            / "reconstruction"
            / "reconstruction_instructions.md"
        )

        reconstruction_path.write_text(
            reconstruction_path.read_text(encoding="utf-8")
            + "\n\nThis skeleton is reconstructable release-grade evidence.\n",
            encoding="utf-8",
        )

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "reconstruction/reconstruction_instructions.md" in combined
        assert "contradictory authority claim" in combined
    finally:
        td.cleanup()


def test_checker_rejects_report_card_contradictory_authority_claim() -> None:
    td, packet_root = _copy_skeleton()

    try:
        report_path = (
            packet_root
            / "audit"
            / "release_authority_audit_bundle"
            / "report_card.html"
        )

        report_path.write_text(
            report_path.read_text(encoding="utf-8")
            + "\n<p>This report card creates release authority.</p>\n",
            encoding="utf-8",
        )

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "audit/release_authority_audit_bundle/report_card.html" in combined
        assert "contradictory authority claim" in combined
    finally:
        td.cleanup()

def main() -> int:
    try:
        test_layout_skeleton_root_exists()
        test_all_canonical_paths_exist()
        test_package_manifest_lists_canonical_paths()
        test_json_placeholders_do_not_create_release_authority()
        test_root_readme_disclaims_release_grade_authority()
        test_reconstruction_instructions_disclaim_release_authority()
        test_checker_rejects_yaml_placeholder_structural_authority_claim()
        test_checker_rejects_root_readme_contradictory_authority_claim()
        test_checker_rejects_audit_readme_contradictory_authority_claim()
        test_checker_rejects_external_summaries_readme_contradictory_authority_claim()
        test_checker_rejects_reconstruction_contradictory_authority_claim()
        test_checker_rejects_report_card_contradictory_authority_claim()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF evidence packet layout skeleton smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
