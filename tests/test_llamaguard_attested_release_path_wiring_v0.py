#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

ATTEST_JOB = "attest_llamaguard_current_run_summary"
RELEASE_PATH_JOB = "release_grade_recorded_path"
RELEASE_BINDING_ATTEST_JOB = "attest_release_grade_artifact_binding"
PACKAGE_JOB = "assemble_release_grade_reference_package"
VERIFY_JOB = "verify_release_grade_reference_package"

PRE_ATTESTATION_UPLOAD_ARTIFACT = (
    "pulse-pre-attestation-"
    "${{ github.run_id }}-${{ github.run_attempt }}"
)

PRE_ATTESTATION_DOWNLOAD_ARTIFACT = (
    "pulse-pre-attestation-"
    "${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
)

ATTESTED_DOWNLOAD_ARTIFACT = (
    "llamaguard-attested-current-run-"
    "${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
)

HOSTED_MODE_GUARD_TOKEN = (
    "github.event.inputs.llamaguard_evidence_mode == 'hosted_full_runtime'"
)

NON_RELEASE_STEP_GUARD = (
    "steps.release_mode.outputs.is_release != '1'"
)

PRE_ATTESTATION_RELEASE_TOOLS = (
    "tools/build_recorded_release_candidates_v0.py",
    "tools/build_release_evidence_input_manifest_v0.py",
    "tools/check_recorded_release_evidence_v0.py",
    "tools/materialize_release_required_from_verifier_v0.py",
)

ATTESTED_EXTERNAL_FILENAMES = (
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


def _step_block(job_block: str, step_name: str) -> str:
    marker = f"      - name: {step_name}"
    start = job_block.find(marker)

    if start < 0:
        raise AssertionError(f"missing workflow step: {step_name}")

    next_start = job_block.find(
        "\n      - name:",
        start + len(marker),
    )

    if next_start < 0:
        return job_block[start:]

    return job_block[start:next_start]


def _workflow_and_jobs() -> tuple[str, dict[str, str]]:
    text = _read_workflow()
    blocks = _top_level_job_blocks(text)

    required_jobs = (
        "pulse",
        ATTEST_JOB,
        RELEASE_PATH_JOB,
        RELEASE_BINDING_ATTEST_JOB,
        PACKAGE_JOB,
        VERIFY_JOB,
        "tools-tests",
    )

    for name in required_jobs:
        if name not in blocks:
            raise AssertionError(f"missing workflow job: {name}")

    return text, blocks


def test_release_grade_job_order() -> None:
    text, _blocks = _workflow_and_jobs()

    pulse_index = text.index("  pulse:")
    attest_index = text.index(f"  {ATTEST_JOB}:")
    release_path_index = text.index(f"  {RELEASE_PATH_JOB}:")
    binding_attest_index = text.index(
        f"  {RELEASE_BINDING_ATTEST_JOB}:"
    )
    package_index = text.index(f"  {PACKAGE_JOB}:")
    verify_index = text.index(f"  {VERIFY_JOB}:")
    tools_index = text.index("  tools-tests:")

    assert (
        pulse_index
        < attest_index
        < release_path_index
        < binding_attest_index
        < package_index
        < verify_index
        < tools_index
    )


def test_attestation_job_is_hosted_external_model_only() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[ATTEST_JOB]

    assert _job_field(job, "needs") == "pulse"

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


def test_pre_attestation_artifact_is_uploaded_fail_closed() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]

    postconditions = _step_block(
        pulse,
        "release-grade pre-attestation artifact postconditions",
    )
    upload = _step_block(
        pulse,
        "Upload release-grade pre-attestation pulse artifacts",
    )

    assert PRE_ATTESTATION_UPLOAD_ARTIFACT in upload
    assert "if-no-files-found: error" in upload
    assert "retention-days: 30" in upload

    for required in (
        "status.json",
        "status_baseline.json",
        "status_summary_baseline.md",
        "status_summary_baseline.json",
        "required_gate_evidence_v0.json",
        "self_contained_pulse_evidence_floor_v0.json",
        "refusal_delta_summary.json",
        "llamaguard_raw.jsonl",
        "llamaguard_evaluator_manifest_v0.json",
        "llamaguard_summary.json",
    ):
        assert required in postconditions, required
        assert required in upload, required


def test_recorded_path_downloads_pre_attestation_artifact() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    download = _step_block(
        job,
        "Download pre-attestation pulse artifacts",
    )

    assert PRE_ATTESTATION_DOWNLOAD_ARTIFACT in download
    assert '--repo "${GITHUB_REPOSITORY}"' in download

    for required in (
        "status.json",
        "status_baseline.json",
        "status_summary_baseline.md",
        "status_summary_baseline.json",
        "required_gate_evidence_v0.json",
        "self_contained_pulse_evidence_floor_v0.json",
        "refusal_delta_summary.json",
    ):
        assert required in download, required


def test_release_grade_candidate_tools_remain_after_attestation() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]
    recorded = blocks[RELEASE_PATH_JOB]

    for tool in PRE_ATTESTATION_RELEASE_TOOLS:
        assert tool not in pulse, tool
        assert tool in recorded, tool


def test_pre_attestation_final_authority_steps_are_core_only() -> None:
    _text, blocks = _workflow_and_jobs()
    pulse = blocks["pulse"]

    step_names = (
        "Build release authority manifest (audit-only)",
        '"ci: enforce gates via check_gates (policy-derived)"',
        '"Release decision v0: materialize artifact"',
        (
            '"Release authority artifact binding v0: '
            'materialize and verify"'
        ),
        "Export JUnit and SARIF from final status",
        "Upload artifacts",
    )

    for step_name in step_names:
        block = _step_block(pulse, step_name)
        assert NON_RELEASE_STEP_GUARD in block, step_name


def test_recorded_path_restores_attested_evidence_before_verification() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    step_name = "Download attested LlamaGuard external evidence"
    download = _step_block(job, step_name)
    download_step_index = job.index(f"      - name: {step_name}")

    first_tool_index = min(
        job.index(tool)
        for tool in PRE_ATTESTATION_RELEASE_TOOLS
    )

    assert download_step_index < first_tool_index
    assert ATTESTED_DOWNLOAD_ARTIFACT in download
    assert (
        'CANONICAL_EXTERNAL="${GITHUB_WORKSPACE}/'
        'PULSE_safe_pack_v0/artifacts/external"'
        in download
    )
    assert "restore_external_artifact" in download

    for filename in ATTESTED_EXTERNAL_FILENAMES:
        assert f'"{filename}"' in download, filename
        destination = f'"${{CANONICAL_EXTERNAL}}/{filename}"'
        assert destination in download, destination

    for token in (
        'if [[ -z "${src}" ]]',
        'if [[ -L "${src}" ]]',
        'if [[ ! -f "${artifact}" || -L "${artifact}" || ! -s "${artifact}" ]]',
        'sha256sum "${artifact}"',
    ):
        assert token in download, token


def test_recorded_path_materializes_before_combined_enforcement() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    materializer = job.index(
        "tools/materialize_release_required_from_verifier_v0.py"
    )
    schema = job.index("release_grade_status_v1.schema.json")
    no_stub = job.index("ci/check_release_no_stub_status.py")
    enforcement = job.index(
        "release-grade enforce required and release-required gates"
    )

    assert materializer < schema < no_stub < enforcement

    enforcement_block = _step_block(
        job,
        "release-grade enforce required and release-required gates via check_gates",
    )

    for token in (
        "--set required",
        "--set release_required",
        "EFFECTIVE_GATES",
        "tools/check_gates.py",
        '--status "${STATUS}"',
        '--require "${EFFECTIVE_GATES[@]}"',
    ):
        assert token in enforcement_block, token


def test_final_authority_artifacts_follow_gate_enforcement() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    enforcement = job.index(
        "release-grade enforce required and release-required gates"
    )

    ordered_steps = (
        "Render final release-grade Quality Ledger",
        "Export final release-grade status summary",
        "Materialize final release decision v0",
        "Build and verify final release authority manifest",
        "Verify final Quality Ledger and status parity",
        (
            "Materialize and verify final release authority "
            "artifact binding"
        ),
        "Stage final release authority audit bundle",
        "Release-grade final artifact postconditions",
    )

    positions = [
        job.index(f"      - name: {name}")
        for name in ordered_steps
    ]

    assert enforcement < positions[0]
    assert positions == sorted(positions)


def test_recorded_path_uploads_final_package_inputs() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    for artifact_name in (
        "release-authority-v0",
        "release-authority-audit-bundle",
        "release-authority-artifact-binding-v0",
        "release-decision-v0",
        "pulse-report",
        (
            "release-grade-recorded-path-"
            "${{ github.run_id }}-${{ github.run_attempt }}"
        ),
    ):
        assert artifact_name in job, artifact_name

    for required_path in (
        "release_decision_v0.json",
        "artifact_provenance_binding_v0.json",
        "release_authority_v0.json",
        "report_card.html",
        "recorded_release_evidence_verifier_v0.json",
    ):
        assert required_path in job, required_path


def test_release_path_does_not_introduce_parallel_decision_engines() -> None:
    _text, blocks = _workflow_and_jobs()
    job = blocks[RELEASE_PATH_JOB]

    for forbidden in (
        "new_release_decision",
        "parallel_decision",
        "alternate_check_gates",
        "llamaguard_materializer",
        "llamaguard_verifier",
    ):
        assert forbidden not in job, forbidden


def test_downstream_package_dependency_chain_is_preserved() -> None:
    _text, blocks = _workflow_and_jobs()

    package = blocks[PACKAGE_JOB]

    assert _job_field(
        package,
        "needs",
    ) == (
        "[release_grade_recorded_path, "
        "attest_release_grade_artifact_binding]"
    )

    package_guard = _job_field(
        package,
        "if",
    )

    for token in (
        "needs.release_grade_recorded_path.result == 'success'",
        (
            "needs.attest_release_grade_artifact_binding.result "
            "== 'success'"
        ),
    ):
        assert token in package_guard, token

    assert _job_field(
        blocks[VERIFY_JOB],
        "needs",
    ) == PACKAGE_JOB

    assert _job_field(
        blocks["tools-tests"],
        "needs",
    ) == VERIFY_JOB


def test_workflow_wiring_smoke_registered() -> None:
    manifest = _read_tools_manifest()

    assert (
        "tests/test_llamaguard_attested_release_path_wiring_v0.py"
        in manifest
    )


ATTESTATION_INSTALL_STEP = "Install Python deps for LlamaGuard attestation envelope"
ATTESTATION_LOCK = REPO_ROOT / "PULSE_safe_pack_v0/requirements-attestation-v0.lock"


def _attestation_install_body() -> str:
    workflow = yaml.safe_load(_read_workflow())
    return next(
        step["run"]
        for step in workflow["jobs"][ATTEST_JOB]["steps"]
        if step.get("name") == ATTESTATION_INSTALL_STEP
    )


def _assert_attestation_lock_shape(text: str) -> set[str]:
    """Check lock syntax only, not wheel authenticity or dependency closure."""
    entries: dict[str, str] = {}
    logical = re.sub(r"\\\s*\n", " ", text)
    for line in logical.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(
            r"([A-Za-z0-9][A-Za-z0-9_.-]*)==([0-9][A-Za-z0-9.!+_-]*)"
            r"((?:\s+--hash=sha256:[0-9a-f]{64})+)",
            line,
        )
        assert match is not None, f"invalid/unpinned attestation lock entry: {line}"
        name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
        assert name not in entries, f"duplicate attestation requirement: {name}"
        entries[name] = match.group(2)
    assert {"pyyaml", "jsonschema"} <= entries.keys(), "missing attestation root requirements"
    return set(entries)


def test_attestation_install_is_isolated_hash_required_and_wheel_only() -> None:
    body = _attestation_install_body()
    for token in (
        'set -euo pipefail',
        '${GITHUB_WORKSPACE:?}/PULSE_safe_pack_v0/requirements-attestation-v0.lock',
        'sys.version_info[:2] != (3, 11)',
        'sys.implementation.name != "cpython"',
        'sys.platform != "linux"',
        'platform.machine() != "x86_64"',
        'python -I -m venv "${ATTESTATION_VENV}"',
        'PIP_CONFIG_FILE=/dev/null',
        '--isolated',
        '--disable-pip-version-check',
        '--no-cache-dir',
        '--require-virtualenv',
        '--index-url https://pypi.org/simple',
        '--require-hashes --only-binary=:all:',
        '--requirement "${ATTESTATION_LOCK}"',
        'site.ENABLE_USER_SITE is not False',
        'import yaml',
        'import jsonschema',
    ):
        assert token in body, token
    for forbidden in (
        '--upgrade', '--system-site-packages', '--extra-index-url',
        '--trusted-host', '--no-deps', 'install jsonschema',
        '-r requirements.txt', '|| true',
    ):
        assert forbidden not in body, forbidden
    workflow = yaml.safe_load(_read_workflow())
    job = workflow['jobs'][ATTEST_JOB]
    step = next(s for s in job['steps'] if s.get('name') == ATTESTATION_INSTALL_STEP)
    assert set(step) == {'name', 'shell', 'run'}, 'install may not become optional'
    assert step['shell'] == 'bash'
    assert job['permissions'] == {
        'contents': 'read', 'actions': 'read', 'id-token': 'write',
        'attestations': 'write', 'artifact-metadata': 'write',
    }
    steps = [s.get('name') for s in job['steps']]
    assert steps.index(ATTESTATION_INSTALL_STEP) < steps.index('Attest canonical LlamaGuard summary')


def test_attestation_dependency_lock_is_present_and_pinned() -> None:
    assert ATTESTATION_LOCK.is_file() and not ATTESTATION_LOCK.is_symlink(), (
        'missing reviewed attestation lock; assembly is not ready'
    )
    _assert_attestation_lock_shape(ATTESTATION_LOCK.read_text(encoding='utf-8', errors='strict'))


def test_attestation_lock_shape_rejects_missing_unpinned_or_bad_hash_entries() -> None:
    # Synthetic strings exercise only the test invariant; they are never a release lock.
    digest = '0' * 64
    good = f'PyYAML==0.0.1 --hash=sha256:{digest}\njsonschema==0.0.1 --hash=sha256:{digest}\n'
    assert _assert_attestation_lock_shape(good) == {'pyyaml', 'jsonschema'}
    cases = (
        '', good.replace(f' --hash=sha256:{digest}', '', 1),
        good.replace('PyYAML==0.0.1', 'PyYAML>=0.0.1'),
        good.replace('PyYAML==0.0.1', 'PyYAML'),
        good.replace('sha256:' + digest, 'sha256:abc', 1),
        good.replace('==0.0.1', '==0.0.*', 1),
        good + '--extra-index-url https://invalid.example\n',
        good + good.splitlines()[0] + '\n',
        good.splitlines()[0] + '\n',
    )
    for case in cases:
        try:
            _assert_attestation_lock_shape(case)
        except AssertionError:
            continue
        raise AssertionError(f'malformed lock unexpectedly accepted: {case!r}')


def _run_attestation_install_witness(
    *, lock_kind: str = 'regular', fail_stage: str = '',
) -> tuple[subprocess.CompletedProcess[str], list[dict[str, object]], str]:
    """Run the real shell with local call witnesses, NOT a Python 3.11 install.

    No package download, import proof, signing or hosted execution is performed.
    This fixture proves command routing, required options and fail-fast propagation.
    """
    with tempfile.TemporaryDirectory(prefix='pulse-attestation-routing-') as directory:
        root = Path(directory)
        pack = root / 'PULSE_safe_pack_v0'
        pack.mkdir()
        lock = pack / ATTESTATION_LOCK.name
        if lock_kind == 'regular':
            lock.write_text('# synthetic routing witness; not a dependency lock\n')
        elif lock_kind == 'empty':
            lock.touch()
        elif lock_kind == 'symlink':
            target = root / 'target'
            target.write_text('not a lock\n')
            lock.symlink_to(target)
        elif lock_kind == 'directory':
            lock.mkdir()
        else:
            assert lock_kind == 'missing'
        bin_dir = root / 'witness-bin'
        bin_dir.mkdir()
        shim = bin_dir / 'python'
        shim.write_text(
            f'#!{sys.executable}\n' + r'''
import json
import os
import shutil
import sys
from pathlib import Path

args = sys.argv[1:]
if args == ['-I', '-']:
    program = sys.stdin.read()
    stage = 'runtime' if 'sys.version_info' in program else 'imports'
elif args[:3] == ['-I', '-m', 'venv']:
    stage = 'venv'
elif args[:3] == ['-I', '-m', 'pip']:
    stage = 'install' if 'install' in args else 'check' if 'check' in args else 'pip_version'
else:
    raise SystemExit('unexpected witness invocation: ' + repr(args))
with open(os.environ['ATTESTATION_WITNESS_LOG'], 'a') as handle:
    handle.write(json.dumps({'stage': stage, 'args': args,
                            'config': os.environ.get('PIP_CONFIG_FILE')}) + '\n')
if stage == os.environ.get('ATTESTATION_WITNESS_FAIL'):
    raise SystemExit(73)
if stage == 'venv':
    binary = Path(args[-1]) / 'bin/python'
    binary.parent.mkdir()
    shutil.copyfile(__file__, binary)
    binary.chmod(0o755)
'''.lstrip(),
            encoding='utf-8',
        )
        shim.chmod(0o755)
        log = root / 'calls.jsonl'
        published = root / 'github-path'
        published.touch()
        environment = {
            'PATH': str(bin_dir) + os.pathsep + os.defpath,
            'HOME': str(root), 'GITHUB_WORKSPACE': str(root),
            'RUNNER_TEMP': str(root), 'GITHUB_PATH': str(published),
            'ATTESTATION_WITNESS_LOG': str(log),
            'ATTESTATION_WITNESS_FAIL': fail_stage,
        }
        result = subprocess.run(
            ['bash', '--noprofile', '--norc', '-c', _attestation_install_body()],
            cwd=root, env=environment, capture_output=True, text=True, timeout=30,
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, calls, published.read_text()


def test_attestation_install_rejects_unusable_locks_before_python() -> None:
    for kind in ('missing', 'empty', 'symlink', 'directory'):
        result, calls, published = _run_attestation_install_witness(lock_kind=kind)
        assert result.returncode != 0, kind
        assert 'dependency lock must be' in result.stdout, (kind, result.stdout, result.stderr)
        assert not calls, (kind, calls)
        assert not published, (kind, published)


def test_attestation_install_publishes_python_only_after_all_checks() -> None:
    result, calls, published = _run_attestation_install_witness()
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert [call['stage'] for call in calls] == [
        'runtime', 'venv', 'pip_version', 'install', 'check', 'imports',
    ]
    install = next(call for call in calls if call['stage'] == 'install')
    assert install['config'] == '/dev/null'
    for option in ('--isolated', '--require-hashes', '--only-binary=:all:',
                   '--require-virtualenv', '--no-cache-dir', '--requirement'):
        assert option in install['args'], option
    assert len(published.splitlines()) == 1
    assert published.strip().endswith('/bin')
    assert '/pulse-attestation-venv.' in published


def test_attestation_install_propagates_failures_without_publishing_python() -> None:
    stages = ['runtime', 'venv', 'pip_version', 'install', 'check', 'imports']
    for index, stage in enumerate(stages):
        result, calls, published = _run_attestation_install_witness(fail_stage=stage)
        assert result.returncode == 73, (stage, result.stdout, result.stderr)
        assert [call['stage'] for call in calls] == stages[:index + 1], stage
        assert not published, (stage, published)


def test_attestation_runtime_guard_rejects_wrong_python_or_platform() -> None:
    body = _attestation_install_body()
    guard = body.split("<<'PY_RUNTIME'\n", 1)[1].split('\nPY_RUNTIME', 1)[0]
    # Mutate only the subprocess's advertised identity to exercise the real guard.
    # A simulated identity is never used as target-environment installation evidence.
    prefixes = (
        'sys.version_info = (3, 13, 5)',
        'sys.version_info = (3, 11, 0); sys.platform = "darwin"',
        'sys.version_info = (3, 11, 0); platform.machine = lambda: "aarch64"',
        'sys.implementation = types.SimpleNamespace(name="pypy")',
    )
    for prefix in prefixes:
        program = 'import platform, sys, types\n' + prefix + '\n' + guard
        result = subprocess.run(
            [sys.executable, '-I', '-c', program], capture_output=True, text=True, timeout=20,
        )
        assert result.returncode != 0, prefix
        assert 'requires CPython 3.11 / Linux x86_64' in result.stderr, result.stderr


def test_attestation_installer_shell_syntax() -> None:
    result = subprocess.run(
        ['bash', '-n'], input=_attestation_install_body(),
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr


def main() -> int:
    test_release_grade_job_order()
    test_attestation_job_is_hosted_external_model_only()
    test_pre_attestation_artifact_is_uploaded_fail_closed()
    test_recorded_path_downloads_pre_attestation_artifact()
    test_release_grade_candidate_tools_remain_after_attestation()
    test_pre_attestation_final_authority_steps_are_core_only()
    test_recorded_path_restores_attested_evidence_before_verification()
    test_recorded_path_materializes_before_combined_enforcement()
    test_final_authority_artifacts_follow_gate_enforcement()
    test_recorded_path_uploads_final_package_inputs()
    test_release_path_does_not_introduce_parallel_decision_engines()
    test_downstream_package_dependency_chain_is_preserved()
    test_workflow_wiring_smoke_registered()
    test_attestation_install_is_isolated_hash_required_and_wheel_only()
    test_attestation_dependency_lock_is_present_and_pinned()
    test_attestation_lock_shape_rejects_missing_unpinned_or_bad_hash_entries()
    test_attestation_install_rejects_unusable_locks_before_python()
    test_attestation_install_publishes_python_only_after_all_checks()
    test_attestation_install_propagates_failures_without_publishing_python()
    test_attestation_runtime_guard_rejects_wrong_python_or_platform()
    test_attestation_installer_shell_syntax()

    print(
        "OK: attested release-grade phase boundary and "
        "final authority wiring locked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
