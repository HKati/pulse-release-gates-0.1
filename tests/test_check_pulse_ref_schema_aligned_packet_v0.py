#!/usr/bin/env python3
"""Smoke tests for check_pulse_ref_schema_aligned_packet_v0.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
import hashlib


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_pulse_ref_schema_aligned_packet_v0.py"
VALID_PACKAGE = ROOT / "tests" / "fixtures" / "pulse_ref_ra1_package_minimal"


def _run_checker(packet_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--packet-root",
            str(packet_root),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _copy_package() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    td = tempfile.TemporaryDirectory()
    packet_root = Path(td.name) / "packet"
    shutil.copytree(VALID_PACKAGE, packet_root)
    return td, packet_root


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_checker_rejects_publication_snapshot_manifest_sha_mismatch() -> None:
    td, packet_root = _copy_package()
    try:
        manifest_path = packet_root / "package_manifest.json"
        payload = _read_json(manifest_path)
        payload["publication_snapshot"]["sha256"] = "0" * 64
        _write_json(manifest_path, payload)

        result = _run_checker(packet_root)
        combined = result.stdout + result.stderr

        assert result.returncode == 1, combined
        assert "package_manifest.json" in combined, combined
        assert "sha256 mismatch for publication_snapshot" in combined, combined
    finally:
        td.cleanup()


def test_checker_rejects_publication_snapshot_manifest_unsafe_path() -> None:
    td, packet_root = _copy_package()
    try:
        manifest_path = packet_root / "package_manifest.json"
        payload = _read_json(manifest_path)
        payload["publication_snapshot"]["path"] = "../publication_snapshot.json"
        payload["publication_snapshot"]["sha256"] = "0" * 64
        _write_json(manifest_path, payload)

        result = _run_checker(packet_root)
        combined = result.stdout + result.stderr

        assert result.returncode == 1, combined
        assert "package_manifest.json" in combined, combined
        assert "unsafe optional artifact ref publication_snapshot path" in combined, combined
    finally:
        td.cleanup()


def test_checker_rejects_publication_snapshot_wrong_canonical_path() -> None:
    td, packet_root = _copy_package()
    try:
        manifest_path = packet_root / "package_manifest.json"
        payload = _read_json(manifest_path)
        payload["publication_snapshot"]["path"] = "status/status.json"
        payload["publication_snapshot"]["sha256"] = _sha256_file(
            packet_root / "status/status.json"
        )
        _write_json(manifest_path, payload)

        result = _run_checker(packet_root)
        combined = result.stdout + result.stderr

        assert result.returncode == 1, combined
        assert "publication_snapshot must reference canonical path" in combined, combined
        assert "publication/publication_snapshot.json" in combined, combined
    finally:
        td.cleanup()


def test_checker_accepts_ra1_minimal_package_fixture() -> None:
    result = _run_checker(VALID_PACKAGE)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: PULSE-REF schema-aligned packet artifacts valid" in result.stdout


def test_checker_rejects_noncanonical_ci_outcome_schema() -> None:
    td, packet_root = _copy_package()
    try:
        ci_path = packet_root / "ci/ci_outcome.json"
        payload = _read_json(ci_path)
        payload["schema"] = "pulse_ref_pass_fixture_ci_outcome_v0"
        _write_json(ci_path, payload)

        result = _run_checker(packet_root)
        combined = result.stdout + result.stderr

        assert result.returncode == 1
        assert "ci/ci_outcome.json" in combined
        assert "pulse_ref_ci_outcome_v0" in combined
    finally:
        td.cleanup()


def test_checker_rejects_noncanonical_digest_shape() -> None:
    td, packet_root = _copy_package()
    try:
        digest_path = packet_root / "digests/package_digests.json"
        payload = _read_json(digest_path)
        payload["schema"] = "pulse_ref_pass_fixture_package_digests_v0"
        payload["digests"] = payload.pop("artifacts")
        _write_json(digest_path, payload)

        result = _run_checker(packet_root)
        combined = result.stdout + result.stderr

        assert result.returncode == 1
        assert "digests/package_digests.json" in combined
    finally:
        td.cleanup()


def test_checker_rejects_package_manifest_missing_named_ref() -> None:
    td, packet_root = _copy_package()
    try:
        manifest_path = packet_root / "package_manifest.json"
        payload = _read_json(manifest_path)
        payload.pop("ci_outcome")
        _write_json(manifest_path, payload)

        result = _run_checker(packet_root)
        combined = result.stdout + result.stderr

        assert result.returncode == 1
        assert "package_manifest.json" in combined
        assert "ci_outcome" in combined
    finally:
        td.cleanup()


def test_checker_rejects_materialized_gates_not_policy_derived() -> None:
    td, packet_root = _copy_package()
    try:
        gates_path = packet_root / "gates/materialized_gate_sets.json"
        payload = _read_json(gates_path)
        payload["sets"]["required"] = list(reversed(payload["sets"]["required"]))
        _write_json(gates_path, payload)

        result = _run_checker(packet_root)
        combined = result.stdout + result.stderr

        assert result.returncode == 1
        assert "required set is not policy-derived" in combined
    finally:
        td.cleanup()


def main() -> int:
    try:
        test_checker_accepts_ra1_minimal_package_fixture()
        test_checker_rejects_noncanonical_ci_outcome_schema()
        test_checker_rejects_noncanonical_digest_shape()
        test_checker_rejects_package_manifest_missing_named_ref()
        test_checker_rejects_materialized_gates_not_policy_derived()
        test_checker_rejects_publication_snapshot_manifest_sha_mismatch()
        test_checker_rejects_publication_snapshot_manifest_unsafe_path()
        test_checker_rejects_publication_snapshot_wrong_canonical_path()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: schema-aligned packet checker smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
