#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

ATTEST_JOB = "attest_llamaguard_current_run_summary"
RELEASE_PATH_JOB = "release_grade_recorded_path"
ATTESTED_ARTIFACT = (
    "llamaguard-attested-current-run-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)

STRICT_RELEASE_GUARD_TOKENS = (
    "github.event_name != 'pull_request'",
    "needs.attest_llamaguard_current_run_summary.result == 'success'",
    "strict_external_evidence == 'true'",
)

STANDING_RELEASE_TOOLS = (
    "tools/build_recorded_release_candidates_v0.py",
    "tools/build_release_evidence_input_manifest_v0.py",
    "tools/check_recorded_release_evidence_v0.py",
    "tools/materialize_release_required_from_verifier_v0.py",
    "tools/check_gates.py",
)

ATTESTED_EXTERNAL_ARTIFACTS = (
    "llamaguard_raw.jsonl",
    "llamaguard_evaluator_manifest_v0.json",
    "llamaguard_summary.json",
    "llamaguard_summary.bundle.json",
    "llamaguard_summary.envelope.json",
    "llamaguard_attestation_verifier_v1.json",
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
    tools_index = text.index("  tools-tests:")

    assert (
        pulse_index
        < attest_index
        < release_path_index
        < tools_index
    )


def test_release_path_depends_on_attested_llamaguard_job() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    assert _job_field(job, "needs") == ATTEST_JOB

    guard = _job_field(job, "if")

    for token in STRICT_RELEASE_GUARD_TOKENS:
        assert token in guard, token


def test_standing_release_tools_move_out_of_pulse_job() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]

    for tool in STANDING_RELEASE_TOOLS:
        if tool in pulse:
            raise AssertionError(
                "standing release-grade candidate/verifier/"
                "materializer/check_gates path must not run in "
                f"the pre-attestation pulse job: {tool}"
            )


def test_release_path_downloads_attested_external_evidence_first() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    download_index = job.index(
        "Download attested LlamaGuard external evidence"
    )
    artifact_index = job.index(ATTESTED_ARTIFACT)

    assert download_index < artifact_index

    for artifact in ATTESTED_EXTERNAL_ARTIFACTS:
        assert artifact in job, artifact

    first_standing_tool_index = min(
        job.index(tool)
        for tool in STANDING_RELEASE_TOOLS
    )

    assert artifact_index < first_standing_tool_index


def test_release_path_uses_existing_standing_tools_in_order() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    positions = [
        job.index(tool)
        for tool in STANDING_RELEASE_TOOLS
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


def test_release_path_keeps_check_gates_as_final_enforcement() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    materializer_index = job.index(
        "tools/materialize_release_required_from_verifier_v0.py"
    )
    check_gates_index = job.index("tools/check_gates.py")

    assert materializer_index < check_gates_index
    assert "--status" in job
    assert "PULSE_safe_pack_v0/artifacts/status.json" in job
    assert "--require" in job


def test_pr3_workflow_wiring_smoke_registered() -> None:
    manifest = _read_tools_manifest()

    assert (
        "tests/test_llamaguard_attested_release_path_wiring_v0.py"
        in manifest
    )


def main() -> int:
    test_attested_release_path_job_order()
    test_release_path_depends_on_attested_llamaguard_job()
    test_standing_release_tools_move_out_of_pulse_job()
    test_release_path_downloads_attested_external_evidence_first()
    test_release_path_uses_existing_standing_tools_in_order()
    test_release_path_does_not_introduce_parallel_engines()
    test_release_path_keeps_check_gates_as_final_enforcement()
    test_pr3_workflow_wiring_smoke_registered()
    print(
        "LlamaGuard attested release-path workflow wiring "
        "smoke passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
