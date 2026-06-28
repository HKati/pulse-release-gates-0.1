#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

ATTEST_JOB = "attest_llamaguard_current_run_summary"
RELEASE_PATH_JOB = "release_grade_recorded_path"
PACKAGE_JOB = "assemble_release_grade_reference_package"
VERIFY_JOB = "verify_release_grade_reference_package"
ATTESTED_ARTIFACT = (
    "llamaguard-attested-current-run-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)
HOSTED_MODE_GUARD_TOKEN = (
    "github.event.inputs.llamaguard_evidence_mode == 'hosted_full_runtime'"
)

STRICT_RELEASE_GUARD_TOKENS = (
    "github.event_name != 'pull_request'",
    "needs.attest_llamaguard_current_run_summary.result == 'success'",
    "strict_external_evidence == 'true'",
    "startsWith(github.ref, 'refs/tags/v')",
    "startsWith(github.ref, 'refs/tags/V')",
    HOSTED_MODE_GUARD_TOKEN,
)

PRE_ATTESTATION_RELEASE_TOOLS = (
    "tools/build_recorded_release_candidates_v0.py",
    "tools/build_release_evidence_input_manifest_v0.py",
    "tools/check_recorded_release_evidence_v0.py",
    "tools/materialize_release_required_from_verifier_v0.py",
)

RELEASE_PATH_TOOLS = (
    *PRE_ATTESTATION_RELEASE_TOOLS,
    "tools/check_gates.py",
)

ATTESTED_EXTERNAL_ARTIFACT_PATHS = (
    "PULSE_safe_pack_v0/artifacts/external/llamaguard_raw.jsonl",
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_evaluator_manifest_v0.json"
    ),
    "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.json",
    "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.bundle.json",
    "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.envelope.json",
    (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_attestation_verifier_v1.json"
    ),
)


def _read_workflow() -> str:
    if not WORKFLOW.is_file():
        raise AssertionError(f"missing workflow: {WORKFLOW}")

    return WORKFLOW.read_text(
        encoding="utf-8",
        errors="strict",
    )


def _read_tools_manifest() -> str:
    if not TOOLS_TESTS_LIST.is_file():
        raise AssertionError(
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


def _job_field(job_block: str, field_name: str) -> str:
    prefix = f"    {field_name}:"

    for line in job_block.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()

    raise AssertionError(f"missing job field: {field_name}")


def _workflow_and_jobs() -> tuple[str, dict[str, str]]:
    text = _read_workflow()
    blocks = _top_level_job_blocks(text)

    for name in (
        "pulse",
        ATTEST_JOB,
        RELEASE_PATH_JOB,
        PACKAGE_JOB,
        VERIFY_JOB,
        "tools-tests",
    ):
        if name not in blocks:
            raise AssertionError(f"missing workflow job: {name}")

    return text, blocks


def test_attested_release_path_job_order() -> None:
    text, _blocks = _workflow_and_jobs()

    pulse_index = text.index("  pulse:")
    attest_index = text.index(f"  {ATTEST_JOB}:")
    release_path_index = text.index(
        f"  {RELEASE_PATH_JOB}:"
    )
    package_index = text.index(f"  {PACKAGE_JOB}:")
    verify_index = text.index(f"  {VERIFY_JOB}:")
    tools_index = text.index("  tools-tests:")

    assert (
        pulse_index
        < attest_index
        < release_path_index
        < package_index
        < verify_index
        < tools_index
    )


def test_attestation_job_is_hosted_external_model_only() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[ATTEST_JOB]
    guard = _job_field(job, "if")

    for token in (
        "github.event_name != 'pull_request'",
        "needs.pulse.result == 'success'",
        "strict_external_evidence == 'true'",
        "startsWith(github.ref, 'refs/tags/v')",
        "startsWith(github.ref, 'refs/tags/V')",
        HOSTED_MODE_GUARD_TOKEN,
    ):
        assert token in guard, token


def test_release_path_depends_on_attested_llamaguard_job() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    assert _job_field(job, "needs") == ATTEST_JOB

    guard = _job_field(job, "if")

    for token in STRICT_RELEASE_GUARD_TOKENS:
        assert token in guard, token


def test_tools_tests_is_downstream_of_release_path_via_package_verifier() -> None:
    _text, blocks = _workflow_and_jobs()

    assert _job_field(blocks[PACKAGE_JOB], "needs") == (
        RELEASE_PATH_JOB
    )
    assert _job_field(blocks[VERIFY_JOB], "needs") == (
        PACKAGE_JOB
    )
    assert _job_field(blocks["tools-tests"], "needs") == (
        VERIFY_JOB
    )


def test_release_grade_candidate_path_runs_only_after_attestation() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]

    for tool in PRE_ATTESTATION_RELEASE_TOOLS:
        if tool in pulse:
            raise AssertionError(
                "release-grade candidate/verifier/materializer "
                "path must not run in the pre-attestation pulse "
                f"job: {tool}"
            )


def test_core_check_gates_remains_allowed_in_pulse_job() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]

    assert "tools/check_gates.py" in pulse
    assert "ci: enforce gates via check_gates (policy-derived)" in pulse


def test_release_path_downloads_attested_external_evidence_first() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    download_index = job.index(
        "Download attested LlamaGuard external evidence"
    )
    artifact_index = job.index(ATTESTED_ARTIFACT)

    assert download_index < artifact_index

    for artifact_path in ATTESTED_EXTERNAL_ARTIFACT_PATHS:
        restored_index = job.index(artifact_path)
        assert artifact_index < restored_index

    first_release_tool_index = min(
        job.index(tool)
        for tool in RELEASE_PATH_TOOLS
    )

    for artifact_path in ATTESTED_EXTERNAL_ARTIFACT_PATHS:
        assert job.index(artifact_path) < first_release_tool_index


def test_release_path_uses_existing_standing_tools_in_order() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    positions = [
        job.index(tool)
        for tool in RELEASE_PATH_TOOLS
    ]

    assert positions == sorted(positions), positions


def test_release_path_does_not_introduce_parallel_engines() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    forbidden = (
        "new_release_decision",
        "parallel_decision",
        "alternate_check_gates",
        "llamaguard_materializer",
        "llamaguard_verifier",
    )

    for token in forbidden:
        assert token not in job, token


def test_release_path_keeps_policy_derived_check_gates_enforcement() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    materializer_index = job.index(
        "tools/materialize_release_required_from_verifier_v0.py"
    )
    helper_index = job.index("tools/policy_to_require_args.py")
    set_index = job.index("--set release_required")
    check_gates_index = job.index("tools/check_gates.py")

    assert materializer_index < helper_index < set_index < check_gates_index
    assert "RELEASE_REQ_STR" in job
    assert '"${RELEASE_REQ[@]}"' in job
    assert "--status" in job
    assert "PULSE_safe_pack_v0/artifacts/status.json" in job


def test_release_grade_status_contract_validates_after_materialization() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]
    job = blocks[RELEASE_PATH_JOB]

    assert "release_grade_status_v1.schema.json" not in pulse

    materializer_index = job.index(
        "tools/materialize_release_required_from_verifier_v0.py"
    )
    schema_index = job.index("release_grade_status_v1.schema.json")
    check_gates_index = job.index("tools/check_gates.py")

    assert materializer_index < schema_index < check_gates_index


def test_no_stub_guard_runs_after_materialization() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]
    job = blocks[RELEASE_PATH_JOB]

    assert "check_release_no_stub_status.py" not in pulse

    materializer_index = job.index(
        "tools/materialize_release_required_from_verifier_v0.py"
    )
    schema_index = job.index("release_grade_status_v1.schema.json")
    no_stub_index = job.index("ci/check_release_no_stub_status.py")
    check_gates_index = job.index("tools/check_gates.py")

    assert materializer_index < schema_index < no_stub_index < check_gates_index


def test_pr3_workflow_wiring_smoke_registered() -> None:
    manifest = _read_tools_manifest()

    assert (
        "tests/test_llamaguard_attested_release_path_wiring_v0.py"
        in manifest
    )


def main() -> int:
    test_attested_release_path_job_order()
    test_release_path_depends_on_attested_llamaguard_job()
    test_attestation_job_is_hosted_external_model_only() 
    test_tools_tests_is_downstream_of_release_path_via_package_verifier()
    test_release_grade_candidate_path_runs_only_after_attestation()
    test_core_check_gates_remains_allowed_in_pulse_job()
    test_release_path_downloads_attested_external_evidence_first()
    test_release_path_uses_existing_standing_tools_in_order()
    test_release_path_does_not_introduce_parallel_engines()
    test_release_path_keeps_policy_derived_check_gates_enforcement()
    test_release_grade_status_contract_validates_after_materialization()
    test_no_stub_guard_runs_after_materialization()
    test_pr3_workflow_wiring_smoke_registered()
    print(
        "LlamaGuard attested release-path workflow wiring "
        "smoke passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
