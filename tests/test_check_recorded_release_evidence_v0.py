#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.check_recorded_release_evidence_v0 import (
    REPORT_SCHEMA_VERSION,
    check_recorded_release_evidence,
)

CHECKER = (
    REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "check_recorded_release_evidence_v0.py"
)
HEX40 = "a" * 40
RUN_KEY = "run-prod-2026-01-01"
COMMIT_SHA = HEX40

POLICY_TEXT = """policy:
  id: pulse-gate-policy-v0
  version: "0.1.5"
  gates:
    release_required:
      - detectors_materialized_ok
      - external_summaries_present
      - external_all_pass
      - refusal_delta_evidence_present
"""

REGISTRY_TEXT = """version: gate_registry_v0
gates:
  detectors_materialized_ok:
    category: controls
  external_summaries_present:
    category: external
  external_all_pass:
    category: external
  refusal_delta_evidence_present:
    category: controls
"""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _write_text(path: pathlib.Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_artifact(
    *,
    schema_version: str,
    required_for_gates: list[str],
    raw_path: str,
    raw_sha256: str,
    trusted_producer: bool = True,
    policy_sha256: str,
    run_key: str = RUN_KEY,
    git_sha: str = COMMIT_SHA,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "run_identity": {
            "git_sha": git_sha,
            "run_key": run_key,
            "run_mode": "prod",
        },
        "subject_binding": {
            "git_sha": git_sha,
            "run_key": run_key,
        },
        "policy_binding": {
            "policy_set": "required+release_required",
            "policy_sha256": policy_sha256,
        },
        "provenance": {
            "trusted_producer": trusted_producer,
            "producer": "pulse_ci",
        },
        "raw_evidence_binding": {
            "path": raw_path,
            "sha256": raw_sha256,
        },
        "required_for_gates": required_for_gates,
    }


EVIDENCE_DEFS = {
    "detector_report": {
        "schema_version": "detector_report_v0",
        "artifact_path": "artifacts/detectors/detector_report.json",
        "raw_path": "artifacts/raw/detector_report.raw.json",
        "required_for_gates": ["detectors_materialized_ok"],
    },
    "external_summary": {
        "schema_version": "external_summary_v0",
        "artifact_path": "PULSE_safe_pack_v0/artifacts/external/gpt_summary.json",
        "raw_path": "artifacts/raw/gpt_summary.raw.json",
        "required_for_gates": ["external_summaries_present", "external_all_pass"],
    },
    "refusal_delta_summary": {
        "schema_version": "refusal_delta_summary_v0",
        "artifact_path": "PULSE_safe_pack_v0/artifacts/refusal/refusal_delta_summary.json",
        "raw_path": "artifacts/raw/refusal_delta.raw.json",
        "required_for_gates": ["refusal_delta_evidence_present"],
    },
}


def _manifest_template(policy_sha256: str, registry_sha256: str) -> dict[str, Any]:
    candidate_evidence: dict[str, Any] = {}
    expected_relation_bindings: dict[str, Any] = {}
    expected_gate_materialization: dict[str, Any] = {
        "detectors_materialized_ok": {
            "candidate_evidence_ids": ["detector_report"],
            "expected_value": True,
            "materialization_allowed_without_verifier": False,
            "policy_relation": "release_required",
            "relation_binding_ids": [
                "detector_report_to_subject_commit",
                "detector_report_to_gate",
            ],
        },
        "external_summaries_present": {
            "candidate_evidence_ids": ["external_summary"],
            "expected_value": True,
            "materialization_allowed_without_verifier": False,
            "policy_relation": "release_required",
            "relation_binding_ids": [
                "external_summary_to_subject_commit",
                "external_summary_to_gate_external_summaries_present",
            ],
        },
        "external_all_pass": {
            "candidate_evidence_ids": ["external_summary"],
            "expected_value": True,
            "materialization_allowed_without_verifier": False,
            "policy_relation": "release_required",
            "relation_binding_ids": [
                "external_summary_to_subject_commit",
                "external_summary_to_gate_external_all_pass",
            ],
        },
        "refusal_delta_evidence_present": {
            "candidate_evidence_ids": ["refusal_delta_summary"],
            "expected_value": True,
            "materialization_allowed_without_verifier": False,
            "policy_relation": "release_required",
            "relation_binding_ids": [
                "refusal_delta_summary_to_subject_commit",
                "refusal_delta_summary_to_gate",
            ],
        },
    }

    for evidence_id, definition in EVIDENCE_DEFS.items():
        candidate_evidence[evidence_id] = {
            "expected_sha256": None,
            "kind": "recorded_release_evidence",
            "path": definition["artifact_path"],
            "provenance_expectations": {
                "trusted_producer_required": True,
            },
            "required_for_gates": definition["required_for_gates"],
            "schema_version": definition["schema_version"],
            "subject_binding": {
                "git_sha": COMMIT_SHA,
                "run_key": RUN_KEY,
            },
            "verification_required": True,
        }
        expected_relation_bindings[f"{evidence_id}_to_subject_commit"] = {
            "binding_type": "artifact_to_subject",
            "expected_gate_id": definition["required_for_gates"][0],
            "failure_if_missing": "candidate evidence is not bound to subject commit",
            "required": True,
            "source_evidence_id": evidence_id,
            "target": "subject.commit_sha",
        }
        for gate_id in definition["required_for_gates"]:
            relation_id = (
                f"{evidence_id}_to_gate_{gate_id}"
                if evidence_id == "external_summary"
                else f"{evidence_id}_to_gate"
            )
            expected_relation_bindings[relation_id] = {
                "binding_type": "artifact_to_gate",
                "expected_gate_id": gate_id,
                "failure_if_missing": "candidate evidence is not bound to expected gate",
                "required": True,
                "source_evidence_id": evidence_id,
                "target": f"gate.{gate_id}",
            }

    return {
        "schema_version": "release_evidence_input_manifest_v0",
        "manifest_id": "release_evidence_input_manifest_v0",
        "manifest_version": "0.1.0",
        "created_utc": "2026-01-01T00:00:00Z",
        "run_identity": {
            "git_sha": COMMIT_SHA,
            "run_key": RUN_KEY,
            "run_mode": "prod",
        },
        "subject": {
            "commit_sha": COMMIT_SHA,
            "release_candidate": "v0.0.0-test",
            "repository": "HKati/pulse-release-gates-0.1",
        },
        "policy_binding": {
            "policy_path": "pulse_gate_policy_v0.yml",
            "policy_set": "required+release_required",
            "policy_sha256": policy_sha256,
        },
        "registry_binding": {
            "registry_path": "pulse_gate_registry_v0.yml",
            "registry_sha256": registry_sha256,
        },
        "candidate_evidence": candidate_evidence,
        "expected_relation_bindings": expected_relation_bindings,
        "expected_gate_materialization": expected_gate_materialization,
        "fail_closed_requirements": [
            "missing candidate evidence fails closed",
            "missing expected relation binding fails closed",
            "candidate evidence cannot materialize a gate without verifier output",
        ],
        "warnings": [],
    }


def _build_repo_fixture(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, dict[str, Any]]:
    policy_sha = _write_text(tmp_path / "pulse_gate_policy_v0.yml", POLICY_TEXT)
    registry_sha = _write_text(tmp_path / "pulse_gate_registry_v0.yml", REGISTRY_TEXT)
    manifest = _manifest_template(policy_sha, registry_sha)
    for evidence_id, definition in EVIDENCE_DEFS.items():
        raw_path = tmp_path / definition["raw_path"]
        raw_sha = _write_text(raw_path, f"raw::{evidence_id}\n")
        artifact_payload = _candidate_artifact(
            schema_version=definition["schema_version"],
            required_for_gates=definition["required_for_gates"],
            raw_path=definition["raw_path"],
            raw_sha256=raw_sha,
            policy_sha256=policy_sha,
        )
        artifact_path = tmp_path / definition["artifact_path"]
        artifact_sha = _write_json(artifact_path, artifact_payload)
        manifest["candidate_evidence"][evidence_id]["expected_sha256"] = artifact_sha

    manifest_path = (
        tmp_path / "PULSE_safe_pack_v0" / "artifacts" / "release_evidence_input_manifest_v0.json"
    )
    _write_json(manifest_path, manifest)
    return tmp_path, manifest_path, manifest


def _run_cli(
    repo_root: pathlib.Path,
    manifest_path: pathlib.Path,
    out_json: pathlib.Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--manifest",
            str(manifest_path),
            "--repo-root",
            str(repo_root),
            "--out-json",
            str(out_json),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_valid_recorded_release_evidence_passes(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, _ = _build_repo_fixture(tmp_path)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["schema_version"] == REPORT_SCHEMA_VERSION
    assert report["status"] == "verified"
    assert report["errors"] == []
    assert report["gate_materialization_admissibility"]["detectors_materialized_ok"][
        "admissible"
    ] is True


def test_cli_writes_report_and_passes(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, _ = _build_repo_fixture(tmp_path)
    out_json = (
        tmp_path
        / "PULSE_safe_pack_v0"
        / "artifacts"
        / "recorded_release_evidence_verifier_v0.json"
    )
    result = _run_cli(repo_root, manifest_path, out_json)
    assert result.returncode == 0, result.stderr
    assert "OK: recorded release-evidence verification satisfied" in result.stdout
    report = _read_json(out_json)
    assert report["status"] == "verified"


def test_empty_manifest_sections_fail_closed(tmp_path: pathlib.Path) -> None:
    policy_sha = _write_text(tmp_path / "pulse_gate_policy_v0.yml", POLICY_TEXT)
    registry_sha = _write_text(tmp_path / "pulse_gate_registry_v0.yml", REGISTRY_TEXT)
    manifest = {
        "schema_version": "release_evidence_input_manifest_v0",
        "run_identity": {"git_sha": COMMIT_SHA, "run_key": RUN_KEY, "run_mode": "prod"},
        "subject": {"commit_sha": COMMIT_SHA},
        "policy_binding": {
            "policy_path": "pulse_gate_policy_v0.yml",
            "policy_set": "required+release_required",
            "policy_sha256": policy_sha,
        },
        "registry_binding": {
            "registry_path": "pulse_gate_registry_v0.yml",
            "registry_sha256": registry_sha,
        },
        "candidate_evidence": {},
        "expected_relation_bindings": {},
        "expected_gate_materialization": {},
    }
    manifest_path = (
        tmp_path / "PULSE_safe_pack_v0" / "artifacts" / "release_evidence_input_manifest_v0.json"
    )
    _write_json(manifest_path, manifest)
    report = check_recorded_release_evidence(manifest_path, tmp_path)
    assert report["status"] == "failed"
    assert any("manifest.candidate_evidence must not be empty" in error for error in report["errors"])
    assert any(
        "manifest.expected_relation_bindings must not be empty" in error
        for error in report["errors"]
    )
    assert any(
        "manifest.expected_gate_materialization must not be empty" in error
        for error in report["errors"]
    )


def test_candidate_digest_mismatch_fails_closed(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, _ = _build_repo_fixture(tmp_path)
    detector_path = repo_root / EVIDENCE_DEFS["detector_report"]["artifact_path"]
    payload = _read_json(detector_path)
    payload["provenance"]["producer"] = "tampered"
    _write_json(detector_path, payload)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any("candidate artifact sha256 mismatch" in error for error in report["errors"])


def test_run_identity_mismatch_fails_closed(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, _ = _build_repo_fixture(tmp_path)
    detector_path = repo_root / EVIDENCE_DEFS["detector_report"]["artifact_path"]
    payload = _read_json(detector_path)
    payload["run_identity"]["run_key"] = "wrong-run-key"
    _write_json(detector_path, payload)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any("run_identity.run_key mismatch" in error for error in report["errors"])


def test_policy_binding_mismatch_fails_closed(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, _ = _build_repo_fixture(tmp_path)
    external_path = repo_root / EVIDENCE_DEFS["external_summary"]["artifact_path"]
    payload = _read_json(external_path)
    payload["policy_binding"]["policy_sha256"] = "d" * 64
    _write_json(external_path, payload)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any("policy_binding.policy_sha256 mismatch" in error for error in report["errors"])


def test_missing_raw_evidence_fails_closed(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, _ = _build_repo_fixture(tmp_path)
    raw_path = repo_root / EVIDENCE_DEFS["refusal_delta_summary"]["raw_path"]
    raw_path.unlink()
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any("raw evidence not found" in error for error in report["errors"])


def test_candidate_subject_must_bind_back_to_run_identity(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, _ = _build_repo_fixture(tmp_path)
    manifest = _read_json(manifest_path)
    manifest["subject"]["commit_sha"] = "b" * 40
    _write_json(manifest_path, manifest)
    detector_path = repo_root / EVIDENCE_DEFS["detector_report"]["artifact_path"]
    payload = _read_json(detector_path)
    payload["subject_binding"]["git_sha"] = "b" * 40
    _write_json(detector_path, payload)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any(
        "manifest.subject.commit_sha must match manifest.run_identity.git_sha" in error
        for error in report["errors"]
    )
    assert any("subject_binding_to_run_identity.git_sha mismatch" in error for error in report["errors"])


def test_gate_relation_must_match_current_gate(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, manifest = _build_repo_fixture(tmp_path)
    manifest["expected_gate_materialization"]["external_all_pass"]["relation_binding_ids"] = [
        "external_summary_to_subject_commit",
        "external_summary_to_gate_external_summaries_present",
    ]
    _write_json(manifest_path, manifest)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any(
        "relation 'external_summary_to_gate_external_summaries_present' must target expected_gate_id 'external_all_pass'"
        in error
        or "gate external_all_pass relation 'external_summary_to_gate_external_summaries_present'" in error
        for error in report["errors"]
    )
    assert report["gate_materialization_admissibility"]["external_all_pass"]["admissible"] is False


def test_duplicate_json_keys_fail_closed(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, _ = _build_repo_fixture(tmp_path)
    manifest = _read_json(manifest_path)
    detector_path = repo_root / EVIDENCE_DEFS["detector_report"]["artifact_path"]
    detector_path.write_text(
        "\n".join(
            [
                "{",
                '  "schema_version": "detector_report_v0",',
                '  "schema_version": "tampered",',
                '  "run_identity": {"git_sha": "' + COMMIT_SHA + '", "run_key": "' + RUN_KEY + '", "run_mode": "prod"},',
                '  "subject_binding": {"git_sha": "' + COMMIT_SHA + '", "run_key": "' + RUN_KEY + '"},',
                '  "policy_binding": {"policy_set": "required+release_required", "policy_sha256": "' + manifest["policy_binding"]["policy_sha256"] + '"},',
                '  "provenance": {"trusted_producer": true},',
                '  "raw_evidence_binding": {"path": "artifacts/raw/detector_report.raw.json", "sha256": "' + _sha256_bytes(b"raw::detector_report\n") + '"},',
                '  "required_for_gates": ["detectors_materialized_ok"]',
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any("duplicate JSON key" in error for error in report["errors"])


def test_duplicate_manifest_json_keys_fail_closed(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, manifest = _build_repo_fixture(tmp_path)
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True)
    manifest_path.write_text(
        manifest_text.replace(
            '  "schema_version": "release_evidence_input_manifest_v0",',
            '  "schema_version": "release_evidence_input_manifest_v0",\n'
            '  "schema_version": "tampered",',
            1,
        )
        + "\n",
        encoding="utf-8",
    )
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any("duplicate JSON key" in error for error in report["errors"])


def test_policy_and_registry_digest_mismatch_fail_closed(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, manifest = _build_repo_fixture(tmp_path)
    manifest["policy_binding"]["policy_sha256"] = "d" * 64
    manifest["registry_binding"]["registry_sha256"] = "e" * 64
    _write_json(manifest_path, manifest)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any("policy file sha256 mismatch" in error for error in report["errors"])
    assert any("registry file sha256 mismatch" in error for error in report["errors"])


def test_unknown_release_required_gate_fails_closed(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, manifest = _build_repo_fixture(tmp_path)
    manifest["expected_gate_materialization"]["totally_unknown_gate"] = {
        "candidate_evidence_ids": ["detector_report"],
        "expected_value": True,
        "materialization_allowed_without_verifier": False,
        "policy_relation": "release_required",
        "relation_binding_ids": ["detector_report_to_subject_commit", "detector_report_to_gate"],
    }
    _write_json(manifest_path, manifest)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any("not declared in policy.gates.release_required" in error for error in report["errors"])


def test_directory_candidate_path_fails_closed_with_report(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, manifest = _build_repo_fixture(tmp_path)
    bad_dir = repo_root / "artifacts" / "detectors" / "directory_artifact"
    bad_dir.mkdir(parents=True, exist_ok=True)
    manifest["candidate_evidence"]["detector_report"]["path"] = "artifacts/detectors/directory_artifact"
    _write_json(manifest_path, manifest)
    out_json = (
        tmp_path
        / "PULSE_safe_pack_v0"
        / "artifacts"
        / "recorded_release_evidence_verifier_v0.json"
    )
    result = _run_cli(repo_root, manifest_path, out_json)
    assert result.returncode == 1
    report = _read_json(out_json)
    assert report["status"] == "failed"
    assert any("candidate artifact must be a file" in error for error in report["errors"])


def test_missing_concrete_run_identity_fails_closed(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, manifest = _build_repo_fixture(tmp_path)
    manifest["run_identity"]["git_sha"] = "not-a-sha"
    manifest["run_identity"]["run_key"] = ""
    _write_json(manifest_path, manifest)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any(
        "manifest.run_identity.git_sha must be a 40-hex git sha" in error
        for error in report["errors"]
    )
    assert any(
        "manifest.run_identity.run_key must be a non-empty string" in error
        for error in report["errors"]
    )


def test_trusted_producer_expectation_must_be_explicit(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, manifest = _build_repo_fixture(tmp_path)
    del manifest["candidate_evidence"]["detector_report"]["provenance_expectations"]["trusted_producer_required"]
    _write_json(manifest_path, manifest)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any("trusted_producer_required must be literal true" in error for error in report["errors"])


def test_untrusted_producer_fails_when_required(tmp_path: pathlib.Path) -> None:
    repo_root, manifest_path, _ = _build_repo_fixture(tmp_path)
    detector_path = repo_root / EVIDENCE_DEFS["detector_report"]["artifact_path"]
    payload = _read_json(detector_path)
    payload["provenance"]["trusted_producer"] = False
    _write_json(detector_path, payload)
    report = check_recorded_release_evidence(manifest_path, repo_root)
    assert report["status"] == "failed"
    assert any(
        "candidate artifact detector_report.provenance.trusted_producer must be true" in error
        for error in report["errors"]
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
