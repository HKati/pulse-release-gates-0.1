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

        assert result.returncode == 1
        assert "missing canonical paths" in (result.stdout + result.stderr)
        assert "status/status.json" in (result.stdout + result.stderr)
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

        assert result.returncode == 1
        assert "canonical_paths mismatch" in (result.stdout + result.stderr)
        assert "ci/ci_outcome.json" in (result.stdout + result.stderr)
        assert "ci/not_ci_outcome.json" in (result.stdout + result.stderr)
    finally:
        td.cleanup()


def test_checker_rejects_placeholder_authority_claim() -> None:
    td, packet_root = _copy_skeleton()

    try:
        placeholder_path = packet_root / "field" / "field_point_authority_map_v0.json"
        placeholder = _read_json(placeholder_path)

        placeholder["creates_release_authority"] = True
        placeholder["authority_boundary"]["creates_release_authority"] = True

        _write_json(placeholder_path, placeholder)

        result = _run_checker(packet_root)

        assert result.returncode == 1
        combined = result.stdout + result.stderr
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

        assert result.returncode == 1
        assert "placeholder_path" in (result.stdout + result.stderr)
        assert "ci/ci_outcome.json" in (result.stdout + result.stderr)
    finally:
        td.cleanup()


def test_checker_rejects_reconstruction_authority_claim() -> None:
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

        assert result.returncode == 1
        assert "reconstruction/reconstruction_instructions.md" in (
            result.stdout + result.stderr
        )
        assert "does not create release authority" in (result.stdout + result.stderr)
    finally:
        td.cleanup()


def main() -> int:
    try:
        test_checker_accepts_layout_skeleton_fixture()
        test_checker_rejects_missing_canonical_path()
        test_checker_rejects_manifest_canonical_path_drift()
        test_checker_rejects_placeholder_authority_claim()
        test_checker_rejects_placeholder_path_mismatch()
        test_checker_rejects_reconstruction_authority_claim()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF evidence packet layout skeleton checker smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
