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


def _run(out_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUILDER), "--out-dir", str(out_dir)],
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


def test_minimal_packet_builder_smoke() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        result = _run(out)
        assert result.returncode == 0, result.stdout + result.stderr

        packet_root = out / "pulse_ref_evidence_packet_v0"
        assert packet_root.is_dir()

        for rel in CANONICAL_PATHS:
            assert (packet_root / rel).is_file(), rel

        manifest = _read_json(packet_root / "package_manifest.json")
        assert manifest["content_bearing"] is True
        assert manifest["digest_backed"] is True
        assert manifest["reconstructable"] is True
        assert manifest["release_grade_evidence"] is False
        assert manifest["creates_release_authority"] is False
        assert manifest["authority_boundary"]["is_ra1_verifier"] is False
        assert manifest["authority_boundary"]["is_release_authority"] is False
        assert manifest["authority_boundary"]["declared_policy_ci_release_decision"] is False

        for rel in [p for p in CANONICAL_PATHS if p.endswith(".json")]:
            obj = _read_json(packet_root / rel)
            assert obj["release_grade_evidence"] is False, rel
            assert obj["creates_release_authority"] is False, rel

        digests = _read_json(packet_root / "digests/package_digests.json")
        digest_map = digests["artifact_digests_sha256"]

        assert "digests/package_digests.json" not in digest_map
        for rel, expected in digest_map.items():
            assert _sha256(packet_root / rel) == expected, rel


def main() -> int:
    try:
        test_minimal_packet_builder_smoke()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: pulse_ref minimal content packet smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
