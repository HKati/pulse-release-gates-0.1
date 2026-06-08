#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

BUILD_VERIFIER_REPORT = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "build_release_evidence_verifier_report_v0.py"
)
BUILD_EXPECTATION_SUMMARY = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "build_release_evidence_expectation_summary_v0.py"
)
INPUT_MANIFEST_EXAMPLE = (
    REPO_ROOT / "examples" / "release_evidence_input_manifest_v0.minimal.example.json"
)

HEX40 = "a" * 40
HEX64 = "b" * 64
RUN_KEY = "GITHUB_RUN_ID=1|GITHUB_RUN_NUMBER=1|GITHUB_WORKFLOW=PULSE CI"

AUTHORITY_ARTIFACT_NAMES = (
    "status.json",
    "report_card.html",
    "release_authority_v0.json",
    "release_authority_audit_bundle",
    "release-authority-audit-bundle",
)


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            *args,
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _input_manifest(
    *,
    evidence_path: pathlib.Path,
    expected_sha256: str,
) -> dict[str, Any]:
    manifest = copy.deepcopy(_load_json(INPUT_MANIFEST_EXAMPLE))

    manifest["run_identity"]["git_sha"] = HEX40
    manifest["run_identity"]["run_key"] = RUN_KEY

    manifest["subject"]["repository"] = "HKati/pulse-release-gates-0.1"
    manifest["subject"]["commit_sha"] = HEX40
    manifest["subject"]["release_candidate"] = "candidate-v0"

    manifest["policy_binding"]["policy_sha256"] = HEX64
    manifest["registry_binding"]["registry_sha256"] = HEX64

    manifest["candidate_evidence"]["detector_report"]["path"] = str(evidence_path)
    manifest["candidate_evidence"]["detector_report"]["expected_sha256"] = (
        expected_sha256
    )
    manifest["candidate_evidence"]["detector_report"]["subject_binding"]["git_sha"] = (
        HEX40
    )
    manifest["candidate_evidence"]["detector_report"]["subject_binding"]["run_key"] = (
        RUN_KEY
    )

    return manifest


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _path_fingerprint(path: pathlib.Path) -> dict[str, Any]:
    """Return a stable-enough fingerprint for authority-artifact side effects.

    The contract needs to catch accidental writes in the execution root, not only
    under tmp_path.  Include mtime_ns so an overwrite of the same bytes is still
    visible to this test.
    """
    if not path.exists():
        return {"kind": "missing"}

    stat = path.stat()
    if path.is_file():
        return {
            "kind": "file",
            "sha256": _sha256_file(path),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }

    if path.is_dir():
        entries: list[tuple[Any, ...]] = [
            ("dir-root", stat.st_mtime_ns),
        ]
        for child in sorted(path.rglob("*"), key=lambda p: str(p.relative_to(path))):
            rel = str(child.relative_to(path))
            child_stat = child.stat()
            if child.is_file():
                entries.append(
                    (
                        "file",
                        rel,
                        _sha256_file(child),
                        child_stat.st_size,
                        child_stat.st_mtime_ns,
                    )
                )
            elif child.is_dir():
                entries.append(("dir", rel, child_stat.st_mtime_ns))
            else:
                entries.append(("other", rel, child_stat.st_mtime_ns))
        return {
            "kind": "dir",
            "entries": entries,
        }

    return {
        "kind": "other",
        "mtime_ns": stat.st_mtime_ns,
    }


def _authority_artifact_paths(tmp_root: pathlib.Path) -> list[pathlib.Path]:
    """Return all locations where authority artifacts must not appear/change.

    The subprocesses run with cwd=REPO_ROOT, so the invariant must watch:
    - the temp pipeline workspace;
    - the repository execution root;
    - the default safe-pack artifacts directory.
    """
    roots = (
        tmp_root,
        REPO_ROOT,
        REPO_ROOT / "PULSE_safe_pack_v0" / "artifacts",
    )

    return [
        root / artifact_name
        for root in roots
        for artifact_name in AUTHORITY_ARTIFACT_NAMES
    ]


def _authority_artifact_snapshot(tmp_root: pathlib.Path) -> dict[str, dict[str, Any]]:
    return {
        str(path): _path_fingerprint(path)
        for path in _authority_artifact_paths(tmp_root)
    }


def _assert_authority_artifacts_unchanged(
    before: dict[str, dict[str, Any]],
    tmp_root: pathlib.Path,
) -> None:
    after = _authority_artifact_snapshot(tmp_root)
    assert after == before


def test_pre_materialization_pipeline_exposes_gaps_without_authority(
    tmp_path: pathlib.Path,
) -> None:
    authority_before = _authority_artifact_snapshot(tmp_path)

    evidence_path = tmp_path / "detector_report.json"
    _write_json(
        evidence_path,
        {
            "schema_version": "detector_report_v0",
            "result": "candidate-only",
        },
    )
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=evidence_sha256,
        ),
    )

    verifier_report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    summary_path = tmp_path / "release_evidence_expectation_summary_v0.json"

    build_report = _run(
        str(BUILD_VERIFIER_REPORT),
        "--out",
        str(verifier_report_path),
        "--input-manifest",
        str(manifest_path),
    )

    assert build_report.returncode == 0, build_report.stderr
    assert verifier_report_path.exists()

    report = _load_json(verifier_report_path)

    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}

    assert len(report["evidence_inputs"]) == 1
    evidence_input = report["evidence_inputs"][0]
    assert evidence_input["kind"] == "detector_evidence"
    assert evidence_input["sha256"] == evidence_sha256
    assert evidence_input["provenance"]["trusted"] is False
    assert evidence_input["provenance"]["verification_status"] == "not_verified"
    assert evidence_input["provenance"]["candidate_evidence_id"] == "detector_report"
    assert evidence_input["provenance"]["actual_sha256_matches_expected"] is True

    failed_checks = "\n".join(report["failed_checks"])
    assert "expected candidate evidence recorded but not verified: detector_report" in failed_checks
    assert (
        "expected relation binding pending verification: "
        "detector_report_to_subject_commit"
    ) in failed_checks
    assert (
        "expected relation binding pending verification: "
        "detector_report_to_gate"
    ) in failed_checks
    assert (
        "expected gate materialization pending verification: "
        "detectors_materialized_ok"
    ) in failed_checks
    assert (
        "input manifest expected relation bindings are not verified by skeleton"
        in failed_checks
    )
    assert (
        "input manifest expected gate materialization bindings are not "
        "materialized by skeleton"
    ) in failed_checks

    _assert_authority_artifacts_unchanged(authority_before, tmp_path)

    build_summary = _run(
        str(BUILD_EXPECTATION_SUMMARY),
        "--report",
        str(verifier_report_path),
        "--out",
        str(summary_path),
    )

    assert build_summary.returncode == 0, build_summary.stderr
    assert summary_path.exists()

    summary = _load_json(summary_path)

    assert summary["schema_version"] == "release_evidence_expectation_summary_v0"
    assert summary["source_report"]["verifier_decision"] == "FAILED"
    assert summary["summary"]["verifier_readiness"] == "NOT_READY"

    assert summary["summary"]["evidence_inputs_total"] == 1
    assert summary["summary"]["verified_artifacts_total"] == 0
    assert summary["summary"]["relation_bindings_total"] == 0
    assert summary["summary"]["gate_materialization_total"] == 0

    assert summary["summary"]["candidate_evidence_not_verified_count"] >= 1
    assert summary["summary"]["pending_relation_binding_count"] >= 2
    assert summary["summary"]["pending_gate_materialization_count"] >= 1

    gap_kinds = {gap["kind"] for gap in summary["pre_materialization_gaps"]}
    assert "candidate_evidence_not_verified" in gap_kinds
    assert "pending_relation_binding" in gap_kinds
    assert "pending_gate_materialization" in gap_kinds

    boundary = summary["authority_boundary"]
    assert boundary["is_release_authority"] is False
    assert boundary["materializes_gates"] is False
    assert boundary["writes_status_json"] is False
    assert boundary["reopens_release_grade_materialization"] is False
    assert boundary["replaces_check_gates"] is False

    _assert_authority_artifacts_unchanged(authority_before, tmp_path)


def test_pre_materialization_pipeline_digest_mismatch_is_visible_but_non_authorizing(
    tmp_path: pathlib.Path,
) -> None:
    authority_before = _authority_artifact_snapshot(tmp_path)

    evidence_path = tmp_path / "detector_report.json"
    _write_json(
        evidence_path,
        {
            "schema_version": "detector_report_v0",
            "result": "candidate-only",
        },
    )

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=evidence_path,
            expected_sha256=HEX64,
        ),
    )

    verifier_report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    summary_path = tmp_path / "release_evidence_expectation_summary_v0.json"

    build_report = _run(
        str(BUILD_VERIFIER_REPORT),
        "--out",
        str(verifier_report_path),
        "--input-manifest",
        str(manifest_path),
    )

    assert build_report.returncode == 0, build_report.stderr

    report = _load_json(verifier_report_path)
    assert report["verifier_decision"] == "FAILED"
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}

    failed_checks = "\n".join(report["failed_checks"])
    assert "candidate evidence digest mismatch: detector_report" in failed_checks
    assert report["evidence_inputs"][0]["provenance"][
        "actual_sha256_matches_expected"
    ] is False

    _assert_authority_artifacts_unchanged(authority_before, tmp_path)

    build_summary = _run(
        str(BUILD_EXPECTATION_SUMMARY),
        "--report",
        str(verifier_report_path),
        "--out",
        str(summary_path),
    )

    assert build_summary.returncode == 0, build_summary.stderr

    summary = _load_json(summary_path)
    assert summary["summary"]["verifier_readiness"] == "NOT_READY"
    assert summary["summary"]["digest_mismatch_count"] >= 1
    assert any(
        gap["kind"] == "digest_mismatch" and gap["id"] == "detector_report"
        for gap in summary["pre_materialization_gaps"]
    )

    _assert_authority_artifacts_unchanged(authority_before, tmp_path)


def test_pre_materialization_pipeline_missing_candidate_stays_failed(
    tmp_path: pathlib.Path,
) -> None:
    authority_before = _authority_artifact_snapshot(tmp_path)

    missing_evidence_path = tmp_path / "missing_detector_report.json"

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(
        manifest_path,
        _input_manifest(
            evidence_path=missing_evidence_path,
            expected_sha256=HEX64,
        ),
    )

    verifier_report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    summary_path = tmp_path / "release_evidence_expectation_summary_v0.json"

    build_report = _run(
        str(BUILD_VERIFIER_REPORT),
        "--out",
        str(verifier_report_path),
        "--input-manifest",
        str(manifest_path),
    )

    assert build_report.returncode == 0, build_report.stderr

    report = _load_json(verifier_report_path)
    assert report["verifier_decision"] == "FAILED"
    assert report["evidence_inputs"] == []
    assert report["verified_artifacts"] == []
    assert report["relation_bindings"] == []
    assert report["gate_materialization"] == {}

    failed_checks = "\n".join(report["failed_checks"])
    assert "candidate evidence declared by manifest is missing" in failed_checks
    assert "expected candidate evidence not recorded: detector_report" in failed_checks
    assert (
        "expected gate materialization candidate evidence not recorded: "
        "detectors_materialized_ok -> detector_report"
    ) in failed_checks

    _assert_authority_artifacts_unchanged(authority_before, tmp_path)

    build_summary = _run(
        str(BUILD_EXPECTATION_SUMMARY),
        "--report",
        str(verifier_report_path),
        "--out",
        str(summary_path),
    )

    assert build_summary.returncode == 0, build_summary.stderr

    summary = _load_json(summary_path)
    assert summary["summary"]["verifier_readiness"] == "NOT_READY"
    gap_kinds = {gap["kind"] for gap in summary["pre_materialization_gaps"]}
    assert "missing_candidate_evidence" in gap_kinds
    assert "missing_gate_candidate_evidence" in gap_kinds

    _assert_authority_artifacts_unchanged(authority_before, tmp_path)


def test_pre_materialization_pipeline_invalid_manifest_fails_before_report(
    tmp_path: pathlib.Path,
) -> None:
    authority_before = _authority_artifact_snapshot(tmp_path)

    evidence_path = tmp_path / "detector_report.json"
    _write_json(evidence_path, {"schema_version": "detector_report_v0"})
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    manifest = _input_manifest(
        evidence_path=evidence_path,
        expected_sha256=evidence_sha256,
    )
    manifest["expected_gate_materialization"]["detectors_materialized_ok"][
        "materialization_allowed_without_verifier"
    ] = True

    manifest_path = tmp_path / "release_evidence_input_manifest_v0.json"
    _write_json(manifest_path, manifest)

    verifier_report_path = tmp_path / "release_evidence_verifier_report_v0.json"
    summary_path = tmp_path / "release_evidence_expectation_summary_v0.json"

    build_report = _run(
        str(BUILD_VERIFIER_REPORT),
        "--out",
        str(verifier_report_path),
        "--input-manifest",
        str(manifest_path),
    )

    assert build_report.returncode != 0
    assert "release evidence input manifest failed validation" in build_report.stderr
    assert not verifier_report_path.exists()
    assert not summary_path.exists()

    _assert_authority_artifacts_unchanged(authority_before, tmp_path)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
