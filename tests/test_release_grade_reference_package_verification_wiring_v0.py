#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

RECORDED_PATH_JOB = "release_grade_recorded_path"
PACKAGE_JOB = "assemble_release_grade_reference_package"
VERIFY_JOB = "verify_release_grade_reference_package"
TOOLS_JOB = "tools-tests"

PACKAGE_ARTIFACT = (
    "complete-release-grade-reference-package-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)
VERIFY_ARTIFACT = (
    "release-grade-reference-package-verification-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)

VERIFY_TOOL = (
    "PULSE_safe_pack_v0/tools/"
    "verify_release_grade_reference_package_v0.py"
)
VERIFY_TOOL_PATH = REPO_ROOT / VERIFY_TOOL

VERIFY_REPORT = (
    "release_grade_reference_package_verification_v0.json"
)

STRICT_RELEASE_GUARD_TOKENS = (
    "github.event_name != 'pull_request'",
    "needs.assemble_release_grade_reference_package.result == 'success'",
    "strict_external_evidence == 'true'",
    "startsWith(github.ref, 'refs/tags/v')",
    "startsWith(github.ref, 'refs/tags/V')",
)

REQUIRED_VERIFY_INPUTS = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
    "artifacts/recorded_release_candidates",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/external/llamaguard_raw.jsonl",
    "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    "artifacts/external/llamaguard_summary.json",
    "artifacts/external/llamaguard_summary.bundle.json",
    "artifacts/external/llamaguard_summary.envelope.json",
    "artifacts/external/llamaguard_attestation_verifier_v1.json",
    "artifacts/status.json",
    "artifacts/release_decision_v0.json",
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/release_authority_v0.json",
    "artifacts/report_card.html",
    "release-authority-audit-bundle",
)


def _read_workflow() -> str:
    assert WORKFLOW.is_file(), f"missing workflow: {WORKFLOW}"
    return WORKFLOW.read_text(
        encoding="utf-8",
        errors="strict",
    )


def _read_tools_manifest() -> str:
    assert TOOLS_TESTS_LIST.is_file(), (
        f"missing tools manifest: {TOOLS_TESTS_LIST}"
    )
    return TOOLS_TESTS_LIST.read_text(
        encoding="utf-8",
        errors="strict",
    )


def _top_level_job_blocks(text: str) -> dict[str, str]:
    starts: list[tuple[str, int]] = []
    offset = 0

    for line in text.splitlines(keepends=True):
        if (
            line.startswith("  ")
            and not line.startswith("    ")
            and line.strip().endswith(":")
        ):
            starts.append((line.strip()[:-1], offset))

        offset += len(line)

    blocks: dict[str, str] = {}

    for index, (name, start) in enumerate(starts):
        end = (
            starts[index + 1][1]
            if index + 1 < len(starts)
            else len(text)
        )
        blocks[name] = text[start:end]

    return blocks


def _workflow_and_jobs() -> tuple[str, dict[str, str]]:
    text = _read_workflow()
    blocks = _top_level_job_blocks(text)

    for name in (
        "pulse",
        "attest_llamaguard_current_run_summary",
        RECORDED_PATH_JOB,
        PACKAGE_JOB,
        VERIFY_JOB,
        TOOLS_JOB,
    ):
        assert name in blocks, f"missing workflow job: {name}"

    return text, blocks


def _job_field(job_block: str, field_name: str) -> str:
    prefix = f"    {field_name}:"

    for line in job_block.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()

    raise AssertionError(f"missing job field: {field_name}")


def _assert_job_needs(job_block: str, expected: str) -> None:
    needs = _job_field(job_block, "needs")
    assert expected in needs, (
        f"job needs must include {expected!r}; got {needs!r}"
    )


def test_complete_package_verification_job_order_and_dependencies() -> None:
    text, blocks = _workflow_and_jobs()

    pulse_index = text.index("  pulse:")
    attest_index = text.index("  attest_llamaguard_current_run_summary:")
    recorded_index = text.index(f"  {RECORDED_PATH_JOB}:")
    package_index = text.index(f"  {PACKAGE_JOB}:")
    verify_index = text.index(f"  {VERIFY_JOB}:")
    tools_index = text.index(f"  {TOOLS_JOB}:")

    assert (
        pulse_index
        < attest_index
        < recorded_index
        < package_index
        < verify_index
        < tools_index
    )

    _assert_job_needs(blocks[PACKAGE_JOB], RECORDED_PATH_JOB)
    _assert_job_needs(blocks[VERIFY_JOB], PACKAGE_JOB)
    _assert_job_needs(blocks[TOOLS_JOB], VERIFY_JOB)


def test_complete_package_verification_job_is_release_grade_only() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]
    guard = _job_field(verify_job, "if")

    for token in STRICT_RELEASE_GUARD_TOKENS:
        assert token in guard, token


def test_complete_package_verification_downloads_complete_package() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    assert PACKAGE_ARTIFACT in verify_job
    assert "gh run download" in verify_job
    assert "complete-release-grade-reference-package" in verify_job

    for required in REQUIRED_VERIFY_INPUTS:
        assert required in verify_job, required


def test_complete_package_verification_uses_canonical_read_only_tool() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    assert VERIFY_TOOL_PATH.is_file(), (
        f"missing canonical verifier tool: {VERIFY_TOOL_PATH}"
    )
    assert VERIFY_TOOL in verify_job
    assert "--repo-root" in verify_job
    assert "--package-dir" in verify_job
    assert "--out" in verify_job
    assert "--repository" in verify_job
    assert "--git-sha" in verify_job
    assert "--workflow-ref" in verify_job
    assert "--run-id" in verify_job
    assert "--run-attempt" in verify_job
    assert "--run-key" in verify_job


def test_complete_package_verification_uploads_report_artifact() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    assert VERIFY_REPORT in verify_job
    assert VERIFY_ARTIFACT in verify_job
    assert "actions/upload-artifact@" in verify_job
    assert "if-no-files-found: error" in verify_job


def test_complete_package_verification_is_non_authorizing() -> None:
    _text, blocks = _workflow_and_jobs()
    verify_job = blocks[VERIFY_JOB]

    forbidden = (
        "tools/check_gates.py",
        "tools/materialize_release_required_from_verifier_v0.py",
        "tools/check_recorded_release_evidence_v0.py",
        "build_recorded_release_candidates_v0.py",
        "build_release_evidence_input_manifest_v0.py",
        "new_release_decision",
        "parallel_decision",
        "authorize_release",
    )

    for token in forbidden:
        assert token not in verify_job, token


def test_complete_package_verification_wiring_smoke_registered() -> None:
    manifest = _read_tools_manifest()

    assert (
        "tests/test_release_grade_reference_package_verification_wiring_v0.py"
        in manifest
    )


# These are synthetic package-content examples, not observed release runs,
# signature-verification evidence, or a second package verifier. Each report
# below is written by the actual verifier CLI; no success result is mocked.
_SUMMARY_IDENTITY = {
    "repository": "example-org/package-summary-fixture",
    "git_sha": "a" * 40,
    "workflow_ref": (
        "example-org/package-summary-fixture/.github/workflows/pulse_ci.yml"
        "@refs/heads/main"
    ),
    "run_id": "9001",
    "run_attempt": "1",
    "run_key": "GITHUB_RUN_ID=9001|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
}
_SUMMARY_AUTHORITY_BOUNDARY = {
    "read_only": True,
    "creates_release_authority": False,
    "authorizes_release": False,
    "blocks_release": False,
    "materializes_status": False,
    "materializes_release_required": False,
    "verifies_recorded_release_evidence_as_authority": False,
    "replaces_check_gates": False,
    "package_acceptance_only": True,
}


def _summary_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2)
        + "\n"
    ).encode("utf-8")


def _summary_sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _summary_package(directory: Path, *, extra_file: bool = False) -> None:
    """Create internally bound test data; do not invent an acquired run."""
    run = {key: _SUMMARY_IDENTITY[key]
           for key in ("repository", "git_sha", "workflow_ref", "run_key")}
    external = "artifacts/external/"
    raw_name = external + "llamaguard_raw.jsonl"
    evaluator_name = external + "llamaguard_evaluator_manifest_v0.json"
    summary_name = external + "llamaguard_summary.json"
    envelope_name = external + "llamaguard_summary.envelope.json"
    bundle_name = external + "llamaguard_summary.bundle.json"
    members = {
        raw_name: _summary_json({"run": run}).replace(b"\n", b"") + b"\n",
        evaluator_name: _summary_json({"run": run}),
        bundle_name: _summary_json({"synthetic_signature_placeholder": True}),
        "artifacts/report_card.html": b"<p>Synthetic package summary test</p>\n",
        "release-authority-audit-bundle/example.json": _summary_json({"synthetic": True}),
    }
    members[summary_name] = _summary_json({
        "evidence": {"raw_artifact_uri": raw_name,
                     "raw_artifact_digest": _summary_sha(members[raw_name])},
        "extensions": {"repository": run["repository"],
                       "source_commit": run["git_sha"],
                       "evaluator_manifest_sha256": _summary_sha(members[evaluator_name])},
        "run": {"run_id": run["run_key"]},
    })
    members[envelope_name] = _summary_json({
        "extensions": {"repository": run["repository"],
                       "source_commit": run["git_sha"],
                       "workflow_ref": run["workflow_ref"],
                       "raw_evidence_sha256": _summary_sha(members[raw_name]),
                       "bundle_sha256": _summary_sha(members[bundle_name])},
        "summary_digest": {"algorithm": "sha256", "value": _summary_sha(members[summary_name])},
        "signing": {"bundle_uri": bundle_name},
    })
    members[external + "llamaguard_attestation_verifier_v1.json"] = _summary_json({
        "status": "verified", "errors": [],
        "summary": {"sha256": _summary_sha(members[summary_name])},
        "envelope": {"sha256": _summary_sha(members[envelope_name])},
    })
    members["run_metadata_v0.json"] = _summary_json({
        **run, "run_id": 9001, "run_attempt": 1,
        "authority_boundary": {"authorizes_release": False, "package_only": True},
    })
    for name in ("status.json", "status_baseline.json"):
        members["artifacts/" + name] = _summary_json({
            "metrics": {"git_sha": run["git_sha"], "run_key": run["run_key"]},
        })
    for name in ("required_gate_evidence_v0.json", "release_decision_v0.json",
                 "artifact_provenance_binding_v0.json", "release_authority_v0.json",
                 "release_evidence_input_manifest_v0.json",
                 "recorded_release_candidate_index_v0.json"):
        members["artifacts/" + name] = _summary_json({"synthetic": True})
    members["artifacts/recorded_release_evidence_verifier_v0.json"] = _summary_json({
        "status": "verified", "errors": [],
    })
    members["artifacts/recorded_release_candidates/synthetic.json"] = _summary_json({
        "validation": {"status": "passed"},
        "authority_boundary": {"creates_release_authority": False,
                               "eligible_without_verifier": False},
    })
    if extra_file:
        members["synthetic-extra.txt"] = b"Extra inventory entry; no new observation.\n"
    members["package_digest_inventory_v0.json"] = _summary_json({
        "schema_version": "release_grade_reference_package_digest_inventory_v0",
        "algorithm": "sha256", "file_count": len(members),
        "files": [{"path": name, "size_bytes": len(raw), "sha256": _summary_sha(raw)}
                  for name, raw in sorted(members.items())],
    })
    for name, raw in members.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def _summary_snapshot(directory: Path) -> dict[str, str]:
    if not directory.exists():
        return {}
    return {p.relative_to(directory).as_posix(): _summary_sha(p.read_bytes())
            for p in sorted(directory.rglob("*")) if p.is_file()}


def _run_summary_verifier(
    package: Path, output: Path, *, identity: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    expected = _SUMMARY_IDENTITY if identity is None else identity
    command = [sys.executable, "-I", "-B", str(VERIFY_TOOL_PATH),
               "--repo-root", str(REPO_ROOT), "--package-dir", str(package),
               "--out", str(output)]
    for key, value in expected.items():
        command.extend(["--" + key.replace("_", "-"), value])
    before = _summary_snapshot(package)
    source_before = VERIFY_TOOL_PATH.read_bytes()
    result = subprocess.run(command, cwd=REPO_ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=30, check=False)
    assert result.stderr == "", result.stderr
    assert output.is_file(), result.stdout
    report = json.loads(output.read_bytes())
    assert isinstance(report, dict)
    assert before == _summary_snapshot(package), "verifier mutated its input package"
    assert source_before == VERIFY_TOOL_PATH.read_bytes(), "verifier source changed"
    return result, report


def _assert_summary_matches_checks(report: dict[str, object]) -> None:
    checks = report["checks"]
    summary = report["summary"]
    assert isinstance(checks, list) and isinstance(summary, dict)
    assert set(summary) == {"checks_total", "checks_failed"}
    assert type(summary["checks_total"]) is int
    assert type(summary["checks_failed"]) is int
    passed = [item for item in checks if item["passed"] is True]
    failed = [item for item in checks if item["passed"] is False]
    assert len(passed) + len(failed) == len(checks)
    assert summary["checks_total"] == len(checks)
    assert summary["checks_failed"] == len(failed)
    assert report["authority_boundary"] == _SUMMARY_AUTHORITY_BOUNDARY


def _summary_consumer() -> types.ModuleType:
    path = (REPO_ROOT / "tools" /
            "build_pulsemech_compute_subject_input_packet_current_run_v0.py")
    # Load the unchanged consumer from its actual bytes, without importing
    # a test double or writing bytecode into the repository.
    name = "package_summary_real_current_run_consumer"
    module = types.ModuleType(name)
    module.__file__ = str(path)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    return module


def test_package_verifier_summary_successful_cli() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-summary-") as temp:
        root = Path(temp)
        _summary_package(root / "package")
        result, report = _run_summary_verifier(root / "package", root / "report.json")
        assert result.returncode == 0, result.stdout
        assert report["status"] == "verified" and report["verified"] is True
        assert report["errors"] == [] and report["checks"]
        _assert_summary_matches_checks(report)
        assert report["summary"]["checks_failed"] == 0


def test_package_verifier_summary_tracks_actual_inventory() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-summary-") as temp:
        root = Path(temp)
        totals = []
        for extra in (False, True):
            package = root / ("extra" if extra else "base")
            _summary_package(package, extra_file=extra)
            result, report = _run_summary_verifier(package, root / (package.name + ".json"))
            assert result.returncode == 0, result.stdout
            _assert_summary_matches_checks(report)
            totals.append(report["summary"]["checks_total"])
        # One extra member adds its actual digest and size checks.
        assert totals[1] == totals[0] + 2


def test_package_verifier_summary_failed_checks_cli() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-summary-") as temp:
        root = Path(temp)
        package = root / "package"
        _summary_package(package)
        status = package / "artifacts/status.json"
        status.write_bytes(_summary_json({"metrics": {"git_sha": "b" * 40,
                                                     "run_key": "different-run"}}))
        result, report = _run_summary_verifier(package, root / "report.json")
        assert result.returncode == 1, result.stdout
        assert report["status"] == "failed" and report["verified"] is False
        assert report["errors"]
        _assert_summary_matches_checks(report)
        assert report["summary"]["checks_failed"] >= 3
        ids = {row["check_id"] for row in report["checks"] if row["passed"] is False}
        assert {"status.git_sha", "status.run_key",
                "digest_inventory.digest:artifacts/status.json"} <= ids


def test_package_verifier_summary_before_any_check_cli() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-summary-") as temp:
        root = Path(temp)
        result, report = _run_summary_verifier(root / "absent", root / "report.json")
        assert result.returncode == 1, result.stdout
        assert report["status"] == "failed" and report["verified"] is False
        assert report["errors"] and "package_dir" in report["errors"][0]
        assert report["checks"] == []
        _assert_summary_matches_checks(report)
        # No check ran. Zero failed checks is NOT a successful verification.
        assert report["summary"] == {"checks_total": 0, "checks_failed": 0}


def test_package_verifier_summary_invalid_identity_cli() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-summary-") as temp:
        root = Path(temp)
        _summary_package(root / "package")
        identity = {**_SUMMARY_IDENTITY, "git_sha": "not-a-commit"}
        result, report = _run_summary_verifier(root / "package", root / "report.json",
                                             identity=identity)
        assert result.returncode == 1, result.stdout
        assert report["status"] == "failed" and report["verified"] is False
        assert report["errors"] and "git_sha" in report["errors"][0]
        assert report["checks"] == []
        _assert_summary_matches_checks(report)


def test_package_verifier_summary_partial_exception_cli() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-summary-") as temp:
        root = Path(temp)
        package = root / "package"
        _summary_package(package)
        (package / "artifacts/external/llamaguard_raw.jsonl").unlink()
        result, report = _run_summary_verifier(package, root / "report.json")
        assert result.returncode == 1, result.stdout
        assert report["status"] == "failed" and report["verified"] is False
        _assert_summary_matches_checks(report)
        assert 0 < report["summary"]["checks_failed"] < report["summary"]["checks_total"]
        # The terminal exception is an error, not a fabricated check record.
        assert len(report["errors"]) > report["summary"]["checks_failed"]


def test_current_run_consumer_accepts_verifier_emitted_summary() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-summary-") as temp:
        root = Path(temp)
        _summary_package(root / "package")
        result, report = _run_summary_verifier(root / "package", root / "report.json")
        assert result.returncode == 0, result.stdout
        before = _summary_json(report)
        consumer = _summary_consumer()
        indexed = consumer._report_checks_by_id(document=report, label="package_verification")
        assert set(indexed) == {row["check_id"] for row in report["checks"]}
        assert len(indexed) == report["summary"]["checks_total"]
        assert _summary_json(report) == before


def test_current_run_consumer_rejects_missing_or_inconsistent_summary() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-summary-") as temp:
        root = Path(temp)
        _summary_package(root / "package")
        result, original = _run_summary_verifier(root / "package", root / "report.json")
        assert result.returncode == 0, result.stdout
        consumer = _summary_consumer()
        for kind, expected_code in (
            ("absent", "package_verification_summary_not_object"),
            ("not_object", "package_verification_summary_not_object"),
            ("wrong_total", "package_verification_checks_total"),
            ("wrong_failed", "package_verification_checks_failed"),
        ):
            report = copy.deepcopy(original)
            if kind == "absent":
                report.pop("summary")
            elif kind == "not_object":
                report["summary"] = None
            elif kind == "wrong_total":
                report["summary"]["checks_total"] += 1
            else:
                report["summary"]["checks_failed"] = 1
            try:
                consumer._report_checks_by_id(document=report, label="package_verification")
            except consumer.WrapperError as exc:
                assert expected_code in str(exc), str(exc)
            else:
                raise AssertionError(f"consumer accepted {kind} summary")


def main() -> int:
    test_complete_package_verification_job_order_and_dependencies()
    test_complete_package_verification_job_is_release_grade_only()
    test_complete_package_verification_downloads_complete_package()
    test_complete_package_verification_uses_canonical_read_only_tool()
    test_complete_package_verification_uploads_report_artifact()
    test_complete_package_verification_is_non_authorizing()
    test_complete_package_verification_wiring_smoke_registered()
    test_package_verifier_summary_successful_cli()
    test_package_verifier_summary_tracks_actual_inventory()
    test_package_verifier_summary_failed_checks_cli()
    test_package_verifier_summary_before_any_check_cli()
    test_package_verifier_summary_invalid_identity_cli()
    test_package_verifier_summary_partial_exception_cli()
    test_current_run_consumer_accepts_verifier_emitted_summary()
    test_current_run_consumer_rejects_missing_or_inconsistent_summary()
    print(
        "release-grade reference package verification workflow wiring "
        "smoke passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
