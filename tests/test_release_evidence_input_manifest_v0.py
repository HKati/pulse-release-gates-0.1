#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.check_release_evidence_input_manifest_v0 import (
    check_release_evidence_input_manifest,
)

CHECKER = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "check_release_evidence_input_manifest_v0.py"
)
EXAMPLE = (
    REPO_ROOT / "examples" / "release_evidence_input_manifest_v0.minimal.example.json"
)

HEX40 = "a" * 40
HEX64 = "b" * 64


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _minimal_manifest() -> dict[str, Any]:
    manifest = copy.deepcopy(_load_json(EXAMPLE))
    manifest["run_identity"]["git_sha"] = HEX40
    manifest["subject"]["commit_sha"] = HEX40
    manifest["policy_binding"]["policy_sha256"] = HEX64
    manifest["registry_binding"]["registry_sha256"] = HEX64
    manifest["candidate_evidence"]["detector_report"]["expected_sha256"] = HEX64
    manifest["candidate_evidence"]["detector_report"]["subject_binding"]["git_sha"] = HEX40
    return manifest


def test_example_manifest_passes_checker() -> None:
    errors = check_release_evidence_input_manifest(EXAMPLE)

    assert errors == []


def test_minimal_manifest_passes_checker(tmp_path: pathlib.Path) -> None:
    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, _minimal_manifest())

    errors = check_release_evidence_input_manifest(manifest_path)

    assert errors == []


def test_core_run_mode_rejected(tmp_path: pathlib.Path) -> None:
    manifest = _minimal_manifest()
    manifest["run_identity"]["run_mode"] = "core"

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    errors = check_release_evidence_input_manifest(manifest_path)

    assert errors


def test_candidate_evidence_requires_verification_required_true(
    tmp_path: pathlib.Path,
) -> None:
    manifest = _minimal_manifest()
    manifest["candidate_evidence"]["detector_report"]["verification_required"] = False

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    errors = check_release_evidence_input_manifest(manifest_path)

    assert errors


def test_relation_source_evidence_id_must_exist(tmp_path: pathlib.Path) -> None:
    manifest = _minimal_manifest()
    manifest["expected_relation_bindings"]["detector_report_to_subject_commit"][
        "source_evidence_id"
    ] = "missing_evidence"

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    errors = check_release_evidence_input_manifest(manifest_path)

    assert any("references missing candidate evidence: missing_evidence" in e for e in errors)


def test_relation_expected_gate_id_must_exist(tmp_path: pathlib.Path) -> None:
    manifest = _minimal_manifest()
    manifest["expected_relation_bindings"]["detector_report_to_subject_commit"][
        "expected_gate_id"
    ] = "missing_gate"

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    errors = check_release_evidence_input_manifest(manifest_path)

    assert any("references missing expected gate: missing_gate" in e for e in errors)


def test_gate_candidate_evidence_id_must_exist(tmp_path: pathlib.Path) -> None:
    manifest = _minimal_manifest()
    manifest["expected_gate_materialization"]["detectors_materialized_ok"][
        "candidate_evidence_ids"
    ] = ["missing_evidence"]

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    errors = check_release_evidence_input_manifest(manifest_path)

    assert any("references missing candidate evidence: missing_evidence" in e for e in errors)


def test_gate_relation_binding_id_must_exist(tmp_path: pathlib.Path) -> None:
    manifest = _minimal_manifest()
    manifest["expected_gate_materialization"]["detectors_materialized_ok"][
        "relation_binding_ids"
    ] = ["missing_relation"]

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    errors = check_release_evidence_input_manifest(manifest_path)

    assert any("references missing expected relation: missing_relation" in e for e in errors)


def test_materialization_without_verifier_is_rejected_by_schema(
    tmp_path: pathlib.Path,
) -> None:
    manifest = _minimal_manifest()
    manifest["expected_gate_materialization"]["detectors_materialized_ok"][
        "materialization_allowed_without_verifier"
    ] = True

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    errors = check_release_evidence_input_manifest(manifest_path)

    assert errors


def test_duplicate_json_keys_fail_closed(tmp_path: pathlib.Path) -> None:
    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    manifest_path.write_text(
        '{'
        '"schema_version": "release_evidence_input_manifest_v0",'
        '"schema_version": "release_evidence_input_manifest_v0"'
        '}',
        encoding="utf-8",
    )

    errors = check_release_evidence_input_manifest(manifest_path)

    assert any("duplicate JSON object key" in error for error in errors)


def test_jsonschema_unavailable_fails_closed(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import PULSE_safe_pack_v0.tools.check_release_evidence_input_manifest_v0 as checker

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, _minimal_manifest())

    monkeypatch.setattr(checker, "jsonschema", None)

    errors = checker.check_release_evidence_input_manifest(manifest_path)

    assert any("jsonschema is required" in error for error in errors)
    assert any("partial fallback validation is not allowed" in error for error in errors)


def test_checker_cli_passes_example() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--manifest",
            str(EXAMPLE),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "OK: release evidence input manifest integrity satisfied" in result.stdout


def test_checker_cli_reports_errors(tmp_path: pathlib.Path) -> None:
    manifest = _minimal_manifest()
    manifest["expected_gate_materialization"]["detectors_materialized_ok"][
        "relation_binding_ids"
    ] = ["missing_relation"]

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--manifest",
            str(manifest_path),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode != 0
    assert "ERRORS (fail-closed):" in result.stderr
    assert "missing_relation" in result.stderr


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
