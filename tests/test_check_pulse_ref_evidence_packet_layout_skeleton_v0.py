#!/usr/bin/env python3
"""Smoke tests for check_pulse_ref_evidence_packet_layout_skeleton_v0.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_pulse_ref_evidence_packet_layout_skeleton_v0.py"
SKELETON_ROOT = (
    ROOT
    / "tests"
    / "fixtures"
    / "pulse_ref"
    / "evidence_packet_layout_skeleton_v0"
    / "pulse_ref_evidence_packet_v0"
)


def _run_checker(packet_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--packet-root",
            str(packet_root),
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


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _copy_skeleton() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    td = tempfile.TemporaryDirectory()
    packet_root = Path(td.name) / "pulse_ref_evidence_packet_v0"
    shutil.copytree(SKELETON_ROOT, packet_root)
    return td, packet_root


def test_checker_accepts_layout_skeleton_fixture() -> None:
    result = _run_checker(SKELETON_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: PULSE-REF evidence packet layout skeleton valid" in result.stdout


def test_checker_rejects_missing_canonical_path() -> None:
    td, packet_root = _copy_skeleton()

    try:
        (packet_root / "status" / "status.json").unlink()

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "missing canonical paths" in combined
        assert "status/status.json" in combined
    finally:
        td.cleanup()


def test_checker_rejects_manifest_canonical_path_drift() -> None:
    td, packet_root = _copy_skeleton()

    try:
        manifest_path = packet_root / "package_manifest.json"
        manifest = _read_json(manifest_path)

        canonical_paths = manifest["canonical_paths"]
        assert isinstance(canonical_paths, list)

        canonical_paths.remove("ci/ci_outcome.json")
        canonical_paths.append("ci/not_ci_outcome.json")

        _write_json(manifest_path, manifest)

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "canonical_paths mismatch" in combined
        assert "ci/ci_outcome.json" in combined
        assert "ci/not_ci_outcome.json" in combined
    finally:
        td.cleanup()


def test_checker_rejects_json_placeholder_authority_claim() -> None:
    td, packet_root = _copy_skeleton()

    try:
        placeholder_path = packet_root / "field" / "field_point_authority_map_v0.json"
        placeholder = _read_json(placeholder_path)

        placeholder["creates_release_authority"] = True
        placeholder["authority_boundary"]["creates_release_authority"] = True

        _write_json(placeholder_path, placeholder)

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "field/field_point_authority_map_v0.json" in combined
        assert "creates_release_authority=false" in combined
        assert "authority_boundary.creates_release_authority must be false" in combined
    finally:
        td.cleanup()


def test_checker_rejects_placeholder_path_mismatch() -> None:
    td, packet_root = _copy_skeleton()

    try:
        placeholder_path = packet_root / "ci" / "ci_outcome.json"
        placeholder = _read_json(placeholder_path)

        placeholder["placeholder_path"] = "ci/wrong.json"

        _write_json(placeholder_path, placeholder)

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "placeholder_path" in combined
        assert "ci/ci_outcome.json" in combined
    finally:
        td.cleanup()


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


def test_checker_rejects_root_readme_missing_authority_disclaimer() -> None:
    td, packet_root = _copy_skeleton()

    try:
        readme_path = packet_root / "README.md"
        readme_path.write_text(
            "# PULSE-REF Evidence Packet Layout Skeleton v0\n\n"
            "This file intentionally omits the authority-boundary disclaimer.\n",
            encoding="utf-8",
        )

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "README.md" in combined
        assert "does not authorize, block, override, or create release authority" in combined
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


def test_checker_rejects_reconstruction_missing_authority_disclaimer() -> None:
    td, packet_root = _copy_skeleton()

    try:
        reconstruction_path = (
            packet_root
            / "reconstruction"
            / "reconstruction_instructions.md"
        )

        reconstruction_path.write_text(
            "# Reconstruction Instructions — Layout Skeleton\n\n"
            "This file intentionally omits the authority-boundary disclaimer.\n",
            encoding="utf-8",
        )

        result = _run_checker(packet_root)

        combined = result.stdout + result.stderr
        assert result.returncode == 1
        assert "reconstruction/reconstruction_instructions.md" in combined
        assert "does not create release authority" in combined
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
        test_checker_accepts_layout_skeleton_fixture()
        test_checker_rejects_missing_canonical_path()
        test_checker_rejects_manifest_canonical_path_drift()
        test_checker_rejects_json_placeholder_authority_claim()
        test_checker_rejects_placeholder_path_mismatch()
        test_checker_rejects_yaml_placeholder_structural_authority_claim()
        test_checker_rejects_root_readme_missing_authority_disclaimer()
        test_checker_rejects_root_readme_contradictory_authority_claim()
        test_checker_rejects_audit_readme_contradictory_authority_claim()
        test_checker_rejects_external_summaries_readme_contradictory_authority_claim()
        test_checker_rejects_reconstruction_missing_authority_disclaimer()
        test_checker_rejects_reconstruction_contradictory_authority_claim()
        test_checker_rejects_report_card_contradictory_authority_claim()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF evidence packet layout skeleton checker smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
