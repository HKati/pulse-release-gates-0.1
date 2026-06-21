#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools import (
    materialize_release_required_from_verifier_v0 as materializer_module,
)

COMMIT_SHA = "a" * 40
RUN_KEY = "run-prod-2026-01-01"
RELEASE_REQUIRED_GATES = [
    "detectors_materialized_ok",
    "external_summaries_present",
    "external_all_pass",
    "refusal_delta_evidence_present",
]

POLICY_TEXT = """policy:
  id: pulse-gate-policy-v0
  version: "0.1.5"

gates:
  required:
    - q1_grounded_ok
  core_required:
    - q1_grounded_ok
  release_required:
    - detectors_materialized_ok
    - external_summaries_present
    - external_all_pass
    - refusal_delta_evidence_present
  advisory:
    - external_summaries_present
"""

REGISTRY_TEXT = """version: gate_registry_v0
gates:
  q1_grounded_ok:
    category: quality
  detectors_materialized_ok:
    category: controls
  external_summaries_present:
    category: external
  external_all_pass:
    category: external
  refusal_delta_evidence_present:
    category: controls
"""


@dataclass
class Fixture:
    repo_root: pathlib.Path
    status_path: pathlib.Path
    verifier_path: pathlib.Path
    manifest_path: pathlib.Path
    policy_path: pathlib.Path
    registry_path: pathlib.Path
    canonical_report: dict[str, Any]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_text(path: pathlib.Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        indent=2,
        sort_keys=False,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _status_payload(
    policy_path: pathlib.Path,
    policy_sha: str,
) -> dict[str, Any]:
    return {
        "version": "1.0.0-prod",
        "created_utc": "2026-01-01T00:00:00Z",
        "metrics": {
            "run_mode": "prod",
            "git_sha": COMMIT_SHA,
            "run_key": RUN_KEY,
            "gate_policy_path": str(policy_path.resolve()),
            "gate_policy_sha256": policy_sha,
        },
        "diagnostics": {
            "gates_stubbed": False,
            "scaffold": False,
        },
        "gates": {
            "q1_grounded_ok": True,
        },
    }


def _verifier_payload(
    *,
    manifest_path: pathlib.Path,
    manifest_sha: str,
    policy_sha: str,
    registry_sha: str,
) -> dict[str, Any]:
    relation_results: dict[str, Any] = {}
    admissibility: dict[str, Any] = {}

    for gate_id in RELEASE_REQUIRED_GATES:
        relation_id = f"candidate_to_gate_{gate_id}"
        relation_results[relation_id] = {
            "status": "verified",
            "binding_type": "artifact_to_gate",
            "source_evidence_id": "candidate",
            "expected_gate_id": gate_id,
            "target": f"gate.{gate_id}",
            "errors": [],
        }
        admissibility[gate_id] = {
            "status": "verified",
            "expected_value": True,
            "candidate_evidence_ids": ["candidate"],
            "relation_binding_ids": [relation_id],
            "admissible": True,
            "errors": [],
        }

    return {
        "schema_version": "recorded_release_evidence_verifier_v0",
        "report_version": "0.2.0",
        "status": "verified",
        "manifest": {
            "path": str(manifest_path.resolve()),
            "sha256": manifest_sha,
            "schema_version": "release_evidence_input_manifest_v0",
        },
        "run_identity": {
            "git_sha": COMMIT_SHA,
            "run_key": RUN_KEY,
            "run_mode": "prod",
        },
        "subject": {
            "repository": "HKati/pulse-release-gates-test",
            "commit_sha": COMMIT_SHA,
            "release_candidate": "v-test",
        },
        "verified_subjects": {
            "git_sha": COMMIT_SHA,
            "run_key": RUN_KEY,
            "commit_sha": COMMIT_SHA,
        },
        "policy_binding": {
            "policy_path": "pulse_gate_policy_v0.yml",
            "policy_set": "required+release_required",
            "policy_sha256": policy_sha,
        },
        "registry_binding": {
            "registry_path": "pulse_gate_registry_v0.yml",
            "registry_sha256": registry_sha,
        },
        "evidence_results": {
            "candidate": {
                "path": "candidate.json",
                "expected_sha256": "e" * 64,
                "actual_sha256": "e" * 64,
                "schema_version": "candidate_v0",
                "status": "verified",
                "digest_match": True,
                "schema_version_match": True,
                "run_identity_match": True,
                "subject_binding_match": True,
                "policy_binding_match": True,
                "trusted_producer_verified": True,
                "raw_evidence_verified": True,
                "required_for_gates_match": True,
                "errors": [],
            }
        },
        "relation_binding_results": relation_results,
        "gate_materialization_admissibility": admissibility,
        "errors": [],
    }


def _build_fixture(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Fixture:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    registry_path = tmp_path / "pulse_gate_registry_v0.yml"
    policy_sha = _write_text(policy_path, POLICY_TEXT)
    registry_sha = _write_text(registry_path, REGISTRY_TEXT)

    artifact_dir = tmp_path / "PULSE_safe_pack_v0" / "artifacts"
    status_path = artifact_dir / "status.json"
    verifier_path = artifact_dir / "recorded_release_evidence_verifier_v0.json"
    manifest_path = artifact_dir / "release_evidence_input_manifest_v0.json"

    manifest_sha = _write_json(
        manifest_path,
        {
            "schema_version": "release_evidence_input_manifest_v0",
        },
    )

    canonical_report = _verifier_payload(
        manifest_path=manifest_path,
        manifest_sha=manifest_sha,
        policy_sha=policy_sha,
        registry_sha=registry_sha,
    )

    _write_json(
        status_path,
        _status_payload(policy_path, policy_sha),
    )
    _write_json(verifier_path, canonical_report)

    def replay(
        *,
        manifest_path: pathlib.Path,
        repo_root: pathlib.Path,
    ) -> dict[str, Any]:
        assert manifest_path.resolve() == (
            artifact_dir / "release_evidence_input_manifest_v0.json"
        ).resolve()
        assert repo_root.resolve() == tmp_path.resolve()
        return copy.deepcopy(canonical_report)

    monkeypatch.setattr(
        materializer_module,
        "check_recorded_release_evidence",
        replay,
    )

    return Fixture(
        repo_root=tmp_path,
        status_path=status_path,
        verifier_path=verifier_path,
        manifest_path=manifest_path,
        policy_path=policy_path,
        registry_path=registry_path,
        canonical_report=canonical_report,
    )


def _materialize(
    fixture: Fixture,
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    return materializer_module.materialize_release_required_from_verifier(
        status_path=fixture.status_path,
        verifier_report_path=fixture.verifier_path,
        manifest_path=fixture.manifest_path,
        repo_root=fixture.repo_root,
        policy_path=fixture.policy_path,
        registry_path=fixture.registry_path,
    )


def _main_args(
    fixture: Fixture,
    out_path: pathlib.Path,
) -> list[str]:
    return [
        "--status",
        str(fixture.status_path),
        "--verifier-report",
        str(fixture.verifier_path),
        "--manifest",
        str(fixture.manifest_path),
        "--repo-root",
        str(fixture.repo_root),
        "--policy",
        str(fixture.policy_path),
        "--registry",
        str(fixture.registry_path),
        "--out",
        str(out_path),
    ]


def test_materializes_release_required_gates_from_canonical_replay(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)

    status, materialized_gates, errors = _materialize(fixture)

    assert errors == []
    assert materialized_gates == RELEASE_REQUIRED_GATES
    assert status is not None
    assert status["gates"]["q1_grounded_ok"] is True

    for gate_id in RELEASE_REQUIRED_GATES:
        assert status["gates"][gate_id] is True


def test_cli_writes_materialized_status(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)
    out_path = fixture.status_path.with_name("status.materialized.json")

    result = materializer_module.main(
        _main_args(fixture, out_path)
    )

    assert result == 0
    written = _read_json(out_path)

    for gate_id in RELEASE_REQUIRED_GATES:
        assert written["gates"][gate_id] is True


@pytest.mark.parametrize(
    "field_name",
    ["evidence_results", "relation_binding_results"],
)
def test_rejects_report_missing_complete_proof_map(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)
    supplied = _read_json(fixture.verifier_path)
    supplied.pop(field_name)
    _write_json(fixture.verifier_path, supplied)

    status, materialized_gates, errors = _materialize(fixture)

    assert status is None
    assert materialized_gates == []
    assert any(
        f"verifier report {field_name} must be a non-empty object"
        in error
        for error in errors
    )
    assert any(
        "verifier report does not match canonical replay" in error
        for error in errors
    )


def test_rejects_modified_admissibility_after_verification(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)
    supplied = _read_json(fixture.verifier_path)
    supplied["gate_materialization_admissibility"][
        "external_all_pass"
    ]["candidate_evidence_ids"] = ["substituted-candidate"]
    _write_json(fixture.verifier_path, supplied)

    status, materialized_gates, errors = _materialize(fixture)

    assert status is None
    assert materialized_gates == []
    assert any(
        "verifier report does not match canonical replay" in error
        for error in errors
    )


def test_rejects_substituted_report_with_matching_identity_metadata(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)
    supplied = _read_json(fixture.verifier_path)
    supplied["evidence_results"]["candidate"][
        "actual_sha256"
    ] = "f" * 64
    _write_json(fixture.verifier_path, supplied)

    status, materialized_gates, errors = _materialize(fixture)

    assert status is None
    assert materialized_gates == []
    assert any(
        "verifier report does not match canonical replay" in error
        for error in errors
    )


def test_rejects_status_report_identity_mismatch(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)
    status_payload = _read_json(fixture.status_path)
    status_payload["metrics"]["git_sha"] = "b" * 40
    _write_json(fixture.status_path, status_payload)

    status, materialized_gates, errors = _materialize(fixture)

    assert status is None
    assert materialized_gates == []
    assert any(
        "status.metrics.git_sha must match "
        "verifier_report.run_identity.git_sha" in error
        for error in errors
    )


@pytest.mark.parametrize("field_name", ["gates_stubbed", "scaffold"])
def test_rejects_stubbed_or_scaffold_status(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)
    status_payload = _read_json(fixture.status_path)
    status_payload["diagnostics"][field_name] = True
    _write_json(fixture.status_path, status_payload)

    status, materialized_gates, errors = _materialize(fixture)

    assert status is None
    assert materialized_gates == []
    assert any(
        f"status.diagnostics.{field_name} must not be true" in error
        for error in errors
    )


def test_rejects_preexisting_false_release_required_without_overwrite(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)
    status_payload = _read_json(fixture.status_path)
    status_payload["gates"]["external_all_pass"] = False
    _write_json(fixture.status_path, status_payload)
    before = fixture.status_path.read_bytes()

    result = materializer_module.main(
        _main_args(fixture, fixture.status_path)
    )

    assert result == 1
    assert fixture.status_path.read_bytes() == before
    assert _read_json(fixture.status_path)["gates"][
        "external_all_pass"
    ] is False


def test_failed_admission_does_not_partially_materialize_or_write(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture.canonical_report["gate_materialization_admissibility"][
        "refusal_delta_evidence_present"
    ]["admissible"] = False
    _write_json(
        fixture.verifier_path,
        fixture.canonical_report,
    )
    before = fixture.status_path.read_bytes()

    status, materialized_gates, errors = _materialize(fixture)

    assert status is None
    assert materialized_gates == []
    assert any(
        "refusal_delta_evidence_present.admissible "
        "must be literal true" in error
        for error in errors
    )

    result = materializer_module.main(
        _main_args(fixture, fixture.status_path)
    )

    assert result == 1
    assert fixture.status_path.read_bytes() == before


def test_rejects_legacy_nested_policy_gates_shape(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(tmp_path, monkeypatch)
    legacy_nested_policy = """policy:
  id: pulse-gate-policy-v0
  version: "0.1.5"
  gates:
    release_required:
      - detectors_materialized_ok
      - external_summaries_present
      - external_all_pass
      - refusal_delta_evidence_present
"""
    policy_sha = _write_text(
        fixture.policy_path,
        legacy_nested_policy,
    )

    status_payload = _read_json(fixture.status_path)
    status_payload["metrics"]["gate_policy_sha256"] = policy_sha
    _write_json(fixture.status_path, status_payload)

    fixture.canonical_report["policy_binding"][
        "policy_sha256"
    ] = policy_sha
    _write_json(
        fixture.verifier_path,
        fixture.canonical_report,
    )

    status, materialized_gates, errors = _materialize(fixture)

    assert status is None
    assert materialized_gates == []
    assert any(
        "policy file must contain top-level gates mapping" in error
        for error in errors
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
