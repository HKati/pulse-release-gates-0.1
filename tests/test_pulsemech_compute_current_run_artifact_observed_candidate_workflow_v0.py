#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (
    ROOT
    / ".github"
    / "workflows"
    / "pulsemech_compute_current_run_artifact_observed_candidate.yml"
)
TOOLS_TESTS_MANIFEST = ROOT / "ci" / "tools-tests.list"
TEST_RELATIVE_PATH = (
    "tests/"
    "test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py"
)

EXPECTED_WORKFLOW_LINES = 2065
EXPECTED_WORKFLOW_BYTES = 86927
EXPECTED_WORKFLOW_SHA256 = (
    "7c80c713b5bceb97b03bdc0638df17fac55fc94090b3a71285eab1e115366599"
)
EXPECTED_WORKFLOW_GIT_BLOB_SHA1 = "c422b0b50342876ee7ca094351b28d0beec98703"

EXPECTED_STEP_NAMES = (
    "Resolve exact Step 3F provider run and protected control plane",
    "Resolve exact Step 3F candidate artifact",
    "Checkout exact protected Step 3G control plane",
    "Verify protected Step 3G control-plane surface",
    "Set up protected Python",
    "Install protected control-plane dependencies",
    "Download and bind exact Step 3F candidate envelope",
    "Verify and materialize exact candidate-bundle intake",
    "Checkout exact current-run source subject",
    "Verify exact independent subject and control-plane checkouts",
    "Build checksum-closed artifact-observed proof",
    "Reverify provider, checkouts, intake, and proof bytes",
    "Upload non-active artifact-observed candidate proof",
    "Record candidate-only artifact-observed result",
)

EXPECTED_REUSABLE_ACTIONS = (
    "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
    "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
)

EXPECTED_CONTROL_PATHS = frozenset(
    {
        ".github/workflows/pulsemech_compute_current_run_artifact_observed_candidate.yml",
        ".github/workflows/pulsemech_compute_current_run_export_candidate.yml",
        ".github/workflows/pulse_ci.yml",
        "requirements.txt",
        "pulse_gate_policy_v0.yml",
        "pulse_gate_registry_v0.yml",
        "tools/load_pulsemech_compute_current_run_export_candidate_bundle_v0.py",
        "tools/build_pulsemech_compute_current_run_artifact_observed_proof_v0.py",
        "tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py",
        "schemas/pulsemech_compute_subject_input_packet_v0.schema.json",
        "tools/check_pulsemech_compute_subject_input_packet_v0.py",
        "tools/build_pulsemech_compute_binding_report_v0.py",
        "tools/pulsemech_compute_binding_analyzer_core_v0.py",
        "schemas/pulsemech_compute_binding_report_v0.schema.json",
        "tools/check_pulsemech_compute_binding_report_v0.py",
        "tools/plan_pulsemech_integration_v0.py",
        "schemas/pulsemech_integration_request_v0.schema.json",
        "schemas/pulsemech_integration_component_manifest_v0.schema.json",
        "schemas/pulsemech_integration_plan_v0.schema.json",
        "tools/build_pulsemech_compute_planned_observed_relation_v0.py",
        "schemas/pulsemech_compute_planned_observed_relation_v0.schema.json",
        "tools/check_pulsemech_compute_planned_observed_relation_v0.py",
        "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json",
        "tools/check_pulsemech_compute_runtime_observation_packet_v0.py",
        "tools/fold_pulsemech_compute_planned_observed_relation_into_status_v0.py",
    }
)

EXPECTED_CANDIDATE_GATES = frozenset(
    {
        "compute_transition_path_complete",
        "compute_transition_authority_binding_ok",
        "compute_transition_unbound_mutation_absent",
    }
)

EXPECTED_PROOF_PAYLOADS = frozenset(
    {
        "compute-binding-report.json",
        "current-run-plan.json",
        "planned-observed-relation.json",
        "candidate-materializer-report.json",
        "folded-candidate-status.json",
    }
)

EXPECTED_CURRENT_RUN_BLOCK = (
    "tests/test_check_pulsemech_compute_current_run_export_expectation_v0.py",
    "tests/test_build_pulsemech_compute_current_run_export_expectation_v0.py",
    "tests/test_load_pulsemech_compute_current_run_export_carrier_v0.py",
    "tests/test_build_pulsemech_compute_subject_input_packet_current_run_v0.py",
    "tests/test_pulsemech_compute_current_run_export_candidate_workflow_v0.py",
    "tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py",
    "tests/test_build_pulsemech_compute_current_run_artifact_observed_proof_v0.py",
    TEST_RELATIVE_PATH,
    "tests/test_pulsemech_compute_post_run_producer_input_capture_contract_v0.py",
    "tests/test_capture_pulsemech_compute_post_run_producer_input_v0.py",
    "tests/test_check_pulsemech_compute_post_run_producer_input_capture_v0.py",
    "tests/test_pulsemech_compute_subject_input_packet_schema_v0.py",
)

EXPECTED_TESTS = frozenset(
    {
        "test_workflow_artifact_identity_matches_reviewed_head",
        "test_tools_tests_manifest_registers_workflow_regression_exactly_once",
        "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract",
        "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit",
        "test_workflow_dispatch_is_the_only_trigger",
        "test_permissions_concurrency_and_job_are_manual_candidate_only",
        "test_all_reusable_actions_are_full_sha_pinned",
        "test_control_plane_and_subject_checkouts_are_exact_independent_and_noncredentialed",
        "test_provider_run_id_is_normalized_once_and_reused_canonically",
        "test_provider_run_resolution_requires_exact_same_repo_main_dispatch_success",
        "test_provider_artifact_selection_is_unique_metadata_bound_and_pagination_closed",
        "test_provider_artifact_name_binds_exact_source_run_identity",
        "test_download_binds_exact_artifact_id_digest_size_and_read_only_file",
        "test_protected_control_plane_surface_is_exact_and_regular",
        "test_candidate_bundle_loader_invocation_is_isolated_and_exact",
        "test_intake_report_closes_provider_subject_files_and_non_authority_boundary",
        "test_intake_directory_is_exact_flat_checksum_closed_and_read_only",
        "test_subject_checkout_uses_intake_bound_revision_and_is_independent",
        "test_artifact_observed_proof_builder_invocation_is_isolated_and_exact",
        "test_proof_manifest_preserves_false_missing_and_unresolved_candidate_state",
        "test_proof_bundle_manifest_closes_exact_file_surface",
        "test_final_reverification_closes_provider_workflow_artifact_and_envelope",
        "test_final_reverification_closes_checkouts_intake_producers_and_proof_bytes",
        "test_upload_occurs_only_after_final_reverification_and_is_candidate_only",
        "test_authority_boundary_remains_none_and_non_active",
        "test_workflow_does_not_directly_invoke_authority_runtime_or_release_steps",
        "test_all_shell_run_blocks_are_syntax_valid",
        "test_embedded_python_programs_compile",
    }
)
EXPECTED_COLLECTED_TEST_ITEMS = 28
CRITICAL_TESTS = frozenset(
    {
        "test_workflow_artifact_identity_matches_reviewed_head",
        "test_provider_run_id_is_normalized_once_and_reused_canonically",
        "test_provider_run_resolution_requires_exact_same_repo_main_dispatch_success",
        "test_provider_artifact_selection_is_unique_metadata_bound_and_pagination_closed",
        "test_download_binds_exact_artifact_id_digest_size_and_read_only_file",
        "test_candidate_bundle_loader_invocation_is_isolated_and_exact",
        "test_artifact_observed_proof_builder_invocation_is_isolated_and_exact",
        "test_final_reverification_closes_provider_workflow_artifact_and_envelope",
        "test_final_reverification_closes_checkouts_intake_producers_and_proof_bytes",
        "test_upload_occurs_only_after_final_reverification_and_is_candidate_only",
        "test_authority_boundary_remains_none_and_non_active",
    }
)

_AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS = (
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_PLUGINS",
)
_AUTHORITATIVE_LAUNCH_PROBE_CHILD = (
    "PULSEMECH_STEP_3G_WORKFLOW_REGRESSION_LAUNCH_PROBE_CHILD"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    try:
        return hashlib.sha1(framed, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(framed).hexdigest()


def manifest_entries() -> list[str]:
    entries: list[str] = []
    for raw in TOOLS_TESTS_MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def workflow_document() -> dict[str, Any]:
    value = yaml.load(workflow_text(), Loader=yaml.BaseLoader)
    assert isinstance(value, dict)
    return value


def workflow_job() -> dict[str, Any]:
    jobs = workflow_document().get("jobs")
    assert isinstance(jobs, dict)
    assert set(jobs) == {"build-current-run-artifact-observed-candidate"}
    job = jobs["build-current-run-artifact-observed-candidate"]
    assert isinstance(job, dict)
    return job


def workflow_steps() -> list[dict[str, Any]]:
    steps = workflow_job().get("steps")
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    return list(steps)


def step_by_name(name: str) -> dict[str, Any]:
    matches = [step for step in workflow_steps() if step.get("name") == name]
    assert len(matches) == 1, f"expected one step named {name!r}, got {len(matches)}"
    return matches[0]


def step_run(name: str) -> str:
    run = step_by_name(name).get("run")
    assert isinstance(run, str)
    return run


def shell_run_blocks() -> list[str]:
    result: list[str] = []
    for step in workflow_steps():
        run = step.get("run")
        if isinstance(run, str):
            result.append(run)
    return result


def embedded_python_programs() -> list[str]:
    programs: list[str] = []
    pattern = re.compile(
        r"python\s+-\s+<<'PY'\n(?P<body>.*?)(?m:^\s*PY\s*$)",
        re.DOTALL,
    )
    for run in shell_run_blocks():
        for match in pattern.finditer(run):
            programs.append(textwrap_dedent(match.group("body")))
    return programs


def textwrap_dedent(value: str) -> str:
    lines = value.splitlines()
    nonempty = [line for line in lines if line.strip()]
    if not nonempty:
        return ""
    indentation = min(len(line) - len(line.lstrip()) for line in nonempty)
    return "\n".join(line[indentation:] for line in lines) + "\n"


def _quoted_array_values(run: str, variable: str) -> frozenset[str]:
    match = re.search(
        rf"{re.escape(variable)}=\(\n(?P<body>.*?)\n\s*\)",
        run,
        flags=re.DOTALL,
    )
    assert match is not None, f"missing shell array {variable}"
    return frozenset(re.findall(r'"([^"\n]+)"', match.group("body")))


def _direct_python_tools() -> tuple[str, ...]:
    tools: list[str] = []
    pattern = re.compile(
        r"python\s+-I\s+\\\s*\n\s*"
        r'"[^"\n]*/tools/(?P<tool>[A-Za-z0-9_.-]+\.py)"',
        flags=re.MULTILINE,
    )
    for run in shell_run_blocks():
        tools.extend(match.group("tool") for match in pattern.finditer(run))
    return tuple(tools)


def _collected_test_name(item: Any) -> str:
    original = getattr(item, "originalname", None)
    if isinstance(original, str) and original:
        return original
    return str(item.name).split("[", 1)[0]


class _AuthoritativeRegressionContract:
    def __init__(self) -> None:
        self._expected_nodeids: set[str] = set()
        self._completed_nodeids: set[str] = set()
        self._skipped_nodeids: set[str] = set()
        self._collection_validated = False
        self._session_finished = False
        self._contract_satisfied = False

    @property
    def completed_successfully(self) -> bool:
        return self._contract_satisfied

    @property
    def completion_state(self) -> dict[str, bool]:
        return {
            "collection_validated": self._collection_validated,
            "contract_satisfied": self._contract_satisfied,
            "session_finished": self._session_finished,
        }

    def pytest_collection_finish(self, session: Any) -> None:
        current = Path(__file__).resolve()
        collected = [
            item
            for item in session.items
            if Path(str(item.path)).resolve() == current
        ]
        observed_names = [str(item.name) for item in collected]
        observed_functions = {_collected_test_name(item) for item in collected}
        duplicate_names = sorted(
            name for name in set(observed_names) if observed_names.count(name) > 1
        )
        missing = sorted(EXPECTED_TESTS - set(observed_names))
        unexpected = sorted(set(observed_names) - EXPECTED_TESTS)
        missing_functions = sorted(EXPECTED_TESTS - observed_functions)
        unexpected_functions = sorted(observed_functions - EXPECTED_TESTS)
        if (
            len(collected) != EXPECTED_COLLECTED_TEST_ITEMS
            or duplicate_names
            or missing
            or unexpected
            or missing_functions
            or unexpected_functions
        ):
            raise pytest.UsageError(
                "authoritative_step_3g_workflow_collection_contract_mismatch: "
                + json.dumps(
                    {
                        "duplicate_names": duplicate_names,
                        "expected_items": EXPECTED_COLLECTED_TEST_ITEMS,
                        "missing_functions": missing_functions,
                        "missing_items": missing,
                        "observed_items": len(collected),
                        "unexpected_functions": unexpected_functions,
                        "unexpected_items": unexpected,
                    },
                    sort_keys=True,
                )
            )
        missing_critical = sorted(CRITICAL_TESTS - set(observed_names))
        if missing_critical:
            raise pytest.UsageError(
                "authoritative_step_3g_workflow_critical_items_missing: "
                + json.dumps(missing_critical)
            )
        self._expected_nodeids = {item.nodeid for item in collected}
        self._collection_validated = True

    def pytest_runtest_logreport(self, report: Any) -> None:
        if report.nodeid not in self._expected_nodeids:
            return
        if report.skipped:
            self._skipped_nodeids.add(report.nodeid)
        if report.when == "call" and (report.passed or report.failed):
            self._completed_nodeids.add(report.nodeid)

    def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
        self._session_finished = True
        missing_execution = sorted(
            self._expected_nodeids - self._completed_nodeids
        )
        skipped = sorted(self._skipped_nodeids)
        if (
            self._collection_validated
            and not missing_execution
            and not skipped
            and int(exitstatus) == int(pytest.ExitCode.OK)
        ):
            self._contract_satisfied = True
            return

        terminal = session.config.pluginmanager.get_plugin("terminalreporter")
        detail = json.dumps(
            {
                "collection_validated": self._collection_validated,
                "missing_execution": missing_execution,
                "skipped": skipped,
            },
            sort_keys=True,
        )
        if terminal is not None:
            terminal.write_sep(
                "=",
                "authoritative Step 3G workflow regression failed",
            )
            terminal.write_line(detail)
        if int(exitstatus) == int(pytest.ExitCode.OK):
            session.exitstatus = int(pytest.ExitCode.TESTS_FAILED)


def _run_authoritative_regression(
    *,
    pytest_main: Callable[..., Any] | None = None,
) -> int:
    previous = {
        key: os.environ.get(key)
        for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
    }
    try:
        os.environ.pop("PYTEST_ADDOPTS", None)
        os.environ.pop("PYTEST_PLUGINS", None)
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        contract = _AuthoritativeRegressionContract()
        runner = pytest.main if pytest_main is None else pytest_main
        result = int(
            runner(
                [
                    "-o",
                    "addopts=",
                    "--noconftest",
                    str(Path(__file__).resolve()),
                ],
                plugins=[contract],
            )
        )
        if result == int(pytest.ExitCode.OK) and not contract.completed_successfully:
            return int(pytest.ExitCode.TESTS_FAILED)
        return result
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_workflow_artifact_identity_matches_reviewed_head() -> None:
    payload = WORKFLOW.read_bytes()
    assert len(payload.splitlines()) == EXPECTED_WORKFLOW_LINES
    assert len(payload) == EXPECTED_WORKFLOW_BYTES
    assert sha256_bytes(payload) == EXPECTED_WORKFLOW_SHA256
    assert git_blob_sha1(payload) == EXPECTED_WORKFLOW_GIT_BLOB_SHA1
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in payload
    assert b"\r" not in payload
    assert all(
        not line.endswith((b" ", b"\t"))
        for line in payload.splitlines()
    )


def test_tools_tests_manifest_registers_workflow_regression_exactly_once() -> None:
    entries = manifest_entries()
    assert len(entries) == 152
    assert len(entries) == len(set(entries))
    assert entries.count(TEST_RELATIVE_PATH) == 1
    index = entries.index(TEST_RELATIVE_PATH)
    assert entries[index - 1] == (
        "tests/"
        "test_build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"
    )
    assert entries[index + 1] == (
        "tests/"
        "test_pulsemech_compute_post_run_producer_input_capture_contract_v0.py"
    )
    start = entries.index(EXPECTED_CURRENT_RUN_BLOCK[0])
    assert tuple(
        entries[start : start + len(EXPECTED_CURRENT_RUN_BLOCK)]
    ) == EXPECTED_CURRENT_RUN_BLOCK


def test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inherited = {
        "PYTEST_ADDOPTS": "--help",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
        "PYTEST_PLUGINS": "must_not_import",
    }
    for key, value in inherited.items():
        monkeypatch.setenv(key, value)
    observed: dict[str, Any] = {}

    def successful_main(arguments: list[str], *, plugins: list[Any]) -> int:
        observed["arguments"] = list(arguments)
        observed["environment"] = {
            key: os.environ.get(key)
            for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
        }
        contract = plugins[0]
        assert isinstance(contract, _AuthoritativeRegressionContract)
        contract._collection_validated = True
        contract._session_finished = True
        contract._contract_satisfied = True
        return int(pytest.ExitCode.OK)

    assert _run_authoritative_regression(pytest_main=successful_main) == 0
    assert observed["arguments"] == [
        "-o",
        "addopts=",
        "--noconftest",
        str(Path(__file__).resolve()),
    ]
    assert observed["environment"] == {
        "PYTEST_ADDOPTS": None,
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_PLUGINS": None,
    }
    assert {
        key: os.environ.get(key)
        for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
    } == inherited

    def incomplete_main(arguments: list[str], *, plugins: list[Any]) -> int:
        del arguments
        contract = plugins[0]
        assert isinstance(contract, _AuthoritativeRegressionContract)
        return int(pytest.ExitCode.OK)

    assert _run_authoritative_regression(
        pytest_main=incomplete_main
    ) == int(pytest.ExitCode.TESTS_FAILED)


def test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit() -> None:
    if os.environ.get(_AUTHORITATIVE_LAUNCH_PROBE_CHILD) == "1":
        assert "PYTEST_ADDOPTS" not in os.environ
        assert "PYTEST_PLUGINS" not in os.environ
        assert os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == "1"
        return

    environment = dict(os.environ)
    environment.update(
        {
            _AUTHORITATIVE_LAUNCH_PROBE_CHILD: "1",
            "PYTEST_ADDOPTS": "--help",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
            "PYTEST_PLUGINS": "module_that_must_not_be_imported",
        }
    )
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr.decode(
        "utf-8",
        errors="replace",
    )
    assert result.stderr == b""
    expected = str(EXPECTED_COLLECTED_TEST_ITEMS).encode("ascii")
    assert b"collected " + expected + b" items" in result.stdout
    assert expected + b" passed" in result.stdout
    assert b"usage: pytest" not in result.stdout.lower()


def test_workflow_dispatch_is_the_only_trigger() -> None:
    document = workflow_document()
    assert document.get("name") == (
        "PULSEmech compute current-run artifact-observed candidate"
    )
    triggers = document.get("on")
    assert isinstance(triggers, dict)
    assert set(triggers) == {"workflow_dispatch"}
    dispatch = triggers["workflow_dispatch"]
    assert isinstance(dispatch, dict)
    inputs = dispatch.get("inputs")
    assert isinstance(inputs, dict)
    assert set(inputs) == {"provider_run_id"}
    provider_run_id = inputs["provider_run_id"]
    assert isinstance(provider_run_id, dict)
    assert provider_run_id.get("required") == "true"
    assert provider_run_id.get("type") == "string"


def test_permissions_concurrency_and_job_are_manual_candidate_only() -> None:
    document = workflow_document()
    assert document.get("permissions") == {
        "contents": "read",
        "actions": "read",
    }
    concurrency = document.get("concurrency")
    assert isinstance(concurrency, dict)
    assert concurrency.get("group") == (
        "pulsemech-compute-current-run-artifact-observed-"
        "${{ inputs.provider_run_id }}"
    )
    assert concurrency.get("cancel-in-progress") == "false"

    job = workflow_job()
    assert job.get("name") == (
        "Build non-active current-run artifact-observed candidate"
    )
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("timeout-minutes") == "45"
    assert job.get("permissions") == {
        "contents": "read",
        "actions": "read",
    }
    assert tuple(step.get("name") for step in workflow_steps()) == (
        EXPECTED_STEP_NAMES
    )


def test_all_reusable_actions_are_full_sha_pinned() -> None:
    action_refs = tuple(
        str(step["uses"])
        for step in workflow_steps()
        if "uses" in step
    )
    assert action_refs == EXPECTED_REUSABLE_ACTIONS
    for reference in action_refs:
        assert re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}",
            reference,
        ) is not None


def test_control_plane_and_subject_checkouts_are_exact_independent_and_noncredentialed() -> None:
    control = step_by_name("Checkout exact protected Step 3G control plane")
    subject = step_by_name("Checkout exact current-run source subject")
    assert control.get("uses") == EXPECTED_REUSABLE_ACTIONS[0]
    assert subject.get("uses") == EXPECTED_REUSABLE_ACTIONS[2]

    expected_common = {
        "repository": "${{ github.repository }}",
        "fetch-depth": "0",
        "persist-credentials": "false",
        "lfs": "false",
        "submodules": "false",
        "set-safe-directory": "false",
    }
    control_with = control.get("with")
    subject_with = subject.get("with")
    assert isinstance(control_with, dict)
    assert isinstance(subject_with, dict)
    for key, expected in expected_common.items():
        assert control_with.get(key) == expected
        assert subject_with.get(key) == expected
    assert control_with.get("ref") == (
        "${{ steps.provider.outputs.control_plane_revision }}"
    )
    assert control_with.get("path") == "control-plane-checkout"
    assert subject_with.get("ref") == (
        "${{ steps.intake.outputs.subject_revision }}"
    )
    assert subject_with.get("path") == "subject-checkout"

    verify = step_run(
        "Verify exact independent subject and control-plane checkouts"
    )
    for required in (
        'SUBJECT_ROOT="${GITHUB_WORKSPACE}/subject-checkout"',
        'CONTROL_ROOT="${GITHUB_WORKSPACE}/control-plane-checkout"',
        'git -C "${SUBJECT_ROOT}" rev-parse HEAD',
        'git -C "${CONTROL_ROOT}" rev-parse HEAD',
        'realpath "${SUBJECT_ROOT}"',
        'realpath "${CONTROL_ROOT}"',
    ):
        assert required in verify


def test_provider_run_id_is_normalized_once_and_reused_canonically() -> None:
    first = step_run(
        "Resolve exact Step 3F provider run and protected control plane"
    )
    assert 'os.environ["PROVIDER_RUN_ID_INPUT"]' in first
    assert ".strip()" in first
    assert r'r"[1-9][0-9]*"' in first
    assert "return int(normalized, 10)" in first
    assert '"provider_run_id": str(provider_run_id)' in first

    later = [
        run
        for name, run in (
            (str(step.get("name")), str(step.get("run")))
            for step in workflow_steps()
            if isinstance(step.get("run"), str)
        )
        if name != "Resolve exact Step 3F provider run and protected control plane"
    ]
    assert all("PROVIDER_RUN_ID_INPUT" not in run for run in later)

    artifact = step_by_name("Resolve exact Step 3F candidate artifact")
    assert artifact.get("env", {}).get("PROVIDER_RUN_ID") == (
        "${{ steps.provider.outputs.provider_run_id }}"
    )
    final = step_by_name(
        "Reverify provider, checkouts, intake, and proof bytes"
    )
    assert final.get("env", {}).get("PROVIDER_RUN_ID") == (
        "${{ steps.provider.outputs.provider_run_id }}"
    )
    final_run = step_run(
        "Reverify provider, checkouts, intake, and proof bytes"
    )
    assert (
        'f"/repos/{repository}/actions/runs/{provider_run_id}"'
        in final_run
    )
    assert (
        'f"/repos/{repository}/actions/runs/{provider_run_id}"'
        in first
    )


def test_provider_run_resolution_requires_exact_same_repo_main_dispatch_success() -> None:
    run = step_run(
        "Resolve exact Step 3F provider run and protected control plane"
    )
    required = (
        'os.environ.get("GITHUB_WORKFLOW")',
        '"STEP3G_WORKFLOW_NAME"',
        'os.environ["TRIGGER_EVENT"] != "workflow_dispatch"',
        'os.environ["TRIGGER_REF"] != "refs/heads/main"',
        "workflow_sha_and_trigger_sha_mismatch",
        "control_plane_workflow_ref_mismatch",
        'run.get("name") != os.environ["PROVIDER_WORKFLOW_NAME"]',
        'run.get("path") != os.environ["PROVIDER_WORKFLOW_PATH"]',
        'run.get("event") != "workflow_dispatch"',
        'run.get("status") != "completed"',
        'run.get("conclusion") != "success"',
        'run.get("head_branch") != "main"',
        'repository_record.get("full_name") != repository',
        'head_repository.get("full_name") != repository',
        'run.get("head_sha")',
        'run.get("run_number")',
        'run.get("run_attempt")',
        'run.get("updated_at")',
        'run.get("workflow_id")',
        'workflow.get("state") != "active"',
    )
    for value in required:
        assert value in run


def test_provider_artifact_selection_is_unique_metadata_bound_and_pagination_closed() -> None:
    run = step_run("Resolve exact Step 3F candidate artifact")
    required = (
        '"/artifacts?per_page=100"',
        "total_count != len(rows)",
        "artifact_listing_pagination_not_closed",
        "candidate_artifact_match_count_invalid",
        'artifact.get("id")',
        'artifact.get("size_in_bytes")',
        "artifact_size > MAX_ENVELOPE",
        r'r"sha256:[0-9a-f]{64}"',
        'artifact.get("expired") is not False',
        'artifact.get("created_at")',
        'artifact.get("expires_at")',
        "parse_utc(created_utc) >= parse_utc(expires_utc)",
    )
    for value in required:
        assert value in run


def test_provider_artifact_name_binds_exact_source_run_identity() -> None:
    run = step_run("Resolve exact Step 3F candidate artifact")
    assert (
        r'r"^pulsemech-compute-current-run-export-candidate-"'
        in run
    )
    assert r'r"([1-9][0-9]*)-([1-9][0-9]*)$"' in run
    assert "source_run_id = int(name_match.group(1), 10)" in run
    assert "source_run_attempt = int(name_match.group(2), 10)" in run
    assert (
        '"source_run_id_from_name": str(source_run_id)'
        in run
    )
    assert (
        '"source_run_attempt_from_name": str(source_run_attempt)'
        in run
    )


def test_download_binds_exact_artifact_id_digest_size_and_read_only_file() -> None:
    run = step_run("Download and bind exact Step 3F candidate envelope")
    required = (
        "timeout 180 gh api",
        '"/repos/${GITHUB_REPOSITORY}/actions/artifacts/'
        '${PROVIDER_ARTIFACT_ID}/zip"',
        'TEMP_PATH="${DOWNLOAD_ROOT}/.provider-artifact.$RANDOM.$RANDOM.tmp"',
        'FINAL_PATH="${DOWNLOAD_ROOT}/provider-candidate-envelope.zip"',
        '[[ ! -f "${TEMP_PATH}" || -L "${TEMP_PATH}" ]]',
        'stat -c \'%h\' "${TEMP_PATH}"',
        'stat -c \'%s\' "${TEMP_PATH}"',
        'sha256sum "${TEMP_PATH}"',
        '"${OBSERVED_SIZE}" != "${PROVIDER_ARTIFACT_SIZE}"',
        '"${OBSERVED_SHA256}" != "${PROVIDER_ARTIFACT_SHA256}"',
        'chmod 0444 "${TEMP_PATH}"',
        'mv -- "${TEMP_PATH}" "${FINAL_PATH}"',
        'test ! -L "${FINAL_PATH}"',
        'stat -c \'%h\' "${FINAL_PATH}"',
        'stat -c \'%s\' "${FINAL_PATH}"',
        'sha256sum "${FINAL_PATH}"',
    )
    for value in required:
        assert value in run
    assert "unzip" not in run
    assert "zipfile" not in run


def test_protected_control_plane_surface_is_exact_and_regular() -> None:
    run = step_run("Verify protected Step 3G control-plane surface")
    assert _quoted_array_values(run, "REQUIRED_CONTROL_PATHS") == (
        EXPECTED_CONTROL_PATHS
    )
    assert '[[ ! -f "${candidate}" || -L "${candidate}" ]]' in run
    assert (
        'git -C "${CONTROL_ROOT}" rev-parse HEAD'
        in run
    )


def test_candidate_bundle_loader_invocation_is_isolated_and_exact() -> None:
    run = step_run("Verify and materialize exact candidate-bundle intake")
    assert "python -I \\" in run
    assert (
        '"${CONTROL_ROOT}/tools/'
        'load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"'
        in run
    )
    expected_arguments = (
        "--artifact-envelope",
        "--repository",
        "--provider-workflow-name",
        "--provider-workflow-path",
        "--provider-workflow-run-id",
        "--provider-workflow-run-number",
        "--provider-workflow-run-attempt",
        "--provider-workflow-event",
        "--provider-workflow-head-branch",
        "--provider-workflow-revision",
        "--provider-workflow-status",
        "--provider-workflow-conclusion",
        "--provider-workflow-updated-utc",
        "--provider-artifact-id",
        "--provider-artifact-name",
        "--provider-artifact-created-utc",
        "--provider-artifact-expires-utc",
        "--provider-artifact-expired",
        "--provider-artifact-sha256",
        "--provider-artifact-size-bytes",
        "--producer-run-key",
        "--ci-workflow-or-job-identity",
        "--control-plane-root",
        "--control-plane-revision",
        "--output-directory",
    )
    for argument in expected_arguments:
        assert argument in run
    assert "cmp --silent" in run
    assert '"${STDOUT_PATH}"' in run
    assert (
        '"${INTAKE_DIRECTORY}/candidate-bundle-intake-report.json"'
        in run
    )


def test_intake_report_closes_provider_subject_files_and_non_authority_boundary() -> None:
    run = step_run("Verify and materialize exact candidate-bundle intake")
    required = (
        '"pulsemech_compute_current_run_export_candidate_bundle_intake_v0"',
        '"pulsemech_compute_current_run_export_candidate_bundle_intake"',
        'report.get("record_status") != "observed"',
        'report.get("ok") is not True',
        'report.get("errors") != []',
        '"activates_compute_gate": False',
        '"candidate_only": True',
        '"changes_release_authority": False',
        '"creates_compute_budget": False',
        '"creates_gate_result": False',
        '"creates_release_decision": False',
        '"materializes_candidate_gate_state": False',
        '"mutates_subject_run": False',
        '"non_active": True',
        '"provider_binding_only": True',
        '"produces_runtime_observation": False',
        '"produces_transition_relation": False',
        '"write_mode": "verified_bundle_copy_only"',
        '"writes_target_repository": False',
        'report.get("provider_binding")',
        'report.get("source_subject")',
        'report.get("files")',
        'report.get("producer")',
    )
    for value in required:
        assert value in run


def test_intake_directory_is_exact_flat_checksum_closed_and_read_only() -> None:
    run = step_run("Verify and materialize exact candidate-bundle intake")
    required = (
        "candidate.is_symlink() or not candidate.is_file()",
        "candidate.stat().st_size != size",
        "sha256_file(candidate) != digest",
        "intake_directory_contains_nonregular_entry",
        "intake_directory_closure_mismatch",
        '"candidate-bundle-intake-report.json"',
        "re.fullmatch(",
        r'r"[0-9a-f]{64}"',
        "name in declared",
        "actual != expected_actual",
    )
    for value in required:
        assert value in run


def test_subject_checkout_uses_intake_bound_revision_and_is_independent() -> None:
    subject = step_by_name("Checkout exact current-run source subject")
    subject_with = subject.get("with")
    assert isinstance(subject_with, dict)
    assert subject_with.get("ref") == (
        "${{ steps.intake.outputs.subject_revision }}"
    )
    assert subject_with.get("path") == "subject-checkout"

    verify = step_run(
        "Verify exact independent subject and control-plane checkouts"
    )
    assert (
        'test "$(git -C "${SUBJECT_ROOT}" rev-parse HEAD)" = '
        '"${SUBJECT_REVISION}"'
        in verify
    )
    assert (
        'test "$(git -C "${CONTROL_ROOT}" rev-parse HEAD)" = '
        '"${CONTROL_REVISION}"'
        in verify
    )
    assert (
        'test "$(realpath "${SUBJECT_ROOT}")" != '
        '"$(realpath "${CONTROL_ROOT}")"'
        in verify
    )


def test_artifact_observed_proof_builder_invocation_is_isolated_and_exact() -> None:
    run = step_run("Build checksum-closed artifact-observed proof")
    assert "python -I \\" in run
    assert (
        '"${CONTROL_ROOT}/tools/'
        'build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"'
        in run
    )
    expected_arguments = (
        "--intake-directory",
        "--subject-root",
        "--subject-repository",
        "--subject-revision",
        "--control-plane-root",
        "--control-plane-repository",
        "--control-plane-revision",
        "--analysis-run-key",
        "--producer-run-key",
        "--ci-workflow-or-job-identity",
        "--output-directory",
    )
    for argument in expected_arguments:
        assert argument in run
    assert "cmp --silent" in run
    assert '"${STDOUT_PATH}"' in run
    assert (
        '"${PROOF_DIRECTORY}/artifact-observed-proof-manifest.json"'
        in run
    )


def test_proof_manifest_preserves_false_missing_and_unresolved_candidate_state() -> None:
    run = step_run("Build checksum-closed artifact-observed proof")
    for gate in EXPECTED_CANDIDATE_GATES:
        assert f'"{gate}"' in run
    required = (
        'result.get("analysis_level") != "artifact_observed"',
        "set(gates) != expected_gate_ids",
        "any(type(value) is not bool for value in gates.values())",
        'result.get("candidate_all_true") is not all(gates.values())',
        '"compute_planned_observed_relation_candidate"',
        'result.get("relation_comparison_status") not in {',
        '"complete"',
        '"partial"',
        '"unknown"',
        'result.get("unresolved_reasons")',
        '"candidate_values_may_be_false": True',
        '"missing_and_unresolved_states_preserved": True',
        '"contains_compute_budget": False',
        '"contains_runtime_observation": False',
    )
    for value in required:
        assert value in run


def test_proof_bundle_manifest_closes_exact_file_surface() -> None:
    run = step_run("Build checksum-closed artifact-observed proof")
    for name in EXPECTED_PROOF_PAYLOADS:
        assert f'"{name}"' in run
    required = (
        '"all_proof_files_except_this_manifest"',
        '"artifact-observed-proof-manifest.json"',
        "layout.get(\"file_count\") != len(PAYLOAD_NAMES)",
        "candidate.is_symlink() or not candidate.is_file()",
        "candidate.stat().st_size != size",
        "sha256_file(candidate) != digest",
        "set(declared) != PAYLOAD_NAMES",
        "actual != expected_actual",
        "proof_directory_closure_mismatch",
        "candidate_bundle_intake_report",
        "proof_intake_report_binding_mismatch",
    )
    for value in required:
        assert value in run


def test_final_reverification_closes_provider_workflow_artifact_and_envelope() -> None:
    run = step_run(
        "Reverify provider, checkouts, intake, and proof bytes"
    )
    required = (
        'f"/repos/{repository}/actions/runs/{provider_run_id}"',
        'f"/repos/{repository}/actions/workflows/{workflow_id}"',
        '"/artifacts?per_page=100"',
        "provider_run_{field}_mismatch",
        "provider_run_{field}_repository_mismatch",
        "provider_workflow_identity_or_state_changed",
        "provider_artifact_listing_not_closed",
        "provider_artifact_id_not_unique",
        "provider_artifact_{field}_mismatch",
        "provider_envelope_missing_or_symlinked",
        "provider_envelope_size_changed",
        "provider_envelope_digest_changed",
        '"id": provider_run_id',
        '"name": "PULSEmech compute current-run export candidate"',
        '"event": "workflow_dispatch"',
        '"status": "completed"',
        '"conclusion": "success"',
        '"head_branch": "main"',
        '"expired": False',
    )
    for value in required:
        assert value in run


def test_final_reverification_closes_checkouts_intake_producers_and_proof_bytes() -> None:
    run = step_run(
        "Reverify provider, checkouts, intake, and proof bytes"
    )
    required = (
        'git -C "${SUBJECT_ROOT}" rev-parse HEAD',
        'git -C "${CONTROL_ROOT}" rev-parse HEAD',
        'realpath "${SUBJECT_ROOT}"',
        'realpath "${CONTROL_ROOT}"',
        "intake_directory_closure_changed",
        "proof_directory_closure_changed",
        "candidate-bundle-intake-report.json",
        "artifact-observed-proof-manifest.json",
        "load_pulsemech_compute_current_run_export_candidate_bundle_v0.py",
        "build_pulsemech_compute_current_run_artifact_observed_proof_v0.py",
        "producer_source_revision",
        "producer_source_sha256",
        "input_bindings",
        "candidate_bundle_intake_report",
        '"carrier"',
        '"expectation"',
        '"subject_input_packet"',
        '"provider_binding"',
        "sha256_file(candidate)",
        "candidate.stat().st_size",
    )
    for value in required:
        assert value in run


def test_upload_occurs_only_after_final_reverification_and_is_candidate_only() -> None:
    names = [str(step.get("name")) for step in workflow_steps()]
    reverify_index = names.index(
        "Reverify provider, checkouts, intake, and proof bytes"
    )
    upload_index = names.index(
        "Upload non-active artifact-observed candidate proof"
    )
    summary_index = names.index(
        "Record candidate-only artifact-observed result"
    )
    assert reverify_index + 1 == upload_index
    assert upload_index + 1 == summary_index

    upload = step_by_name(
        "Upload non-active artifact-observed candidate proof"
    )
    assert upload.get("uses") == EXPECTED_REUSABLE_ACTIONS[-1]
    with_values = upload.get("with")
    assert isinstance(with_values, dict)
    assert with_values == {
        "name": "${{ steps.proof.outputs.artifact_name }}",
        "path": "${{ steps.proof.outputs.proof_directory }}/",
        "if-no-files-found": "error",
        "retention-days": "30",
        "compression-level": "0",
        "overwrite": "false",
        "include-hidden-files": "false",
    }


def test_authority_boundary_remains_none_and_non_active() -> None:
    text = workflow_text()
    required = (
        '"candidate_only": True',
        '"non_active": True',
        '"activates_compute_gate": False',
        '"changes_gate_policy": False',
        '"changes_gate_semantics": False',
        '"changes_release_authority": False',
        '"creates_compute_budget": False',
        '"creates_gate_result": False',
        '"creates_release_decision": False',
        '"materializes_active_gate_state": False',
        '"proof_is_release_authority": False',
        '"produces_runtime_observation": False',
        '"writes_subject_status": False',
        '"writes_target_repository": False',
        '"write_mode": "external_proof_bundle_only"',
        "Candidate-only artifact-observed proof",
        "Non-active / pre-authority / authority effect none",
        "It does not activate a gate",
    )
    for value in required:
        assert value in text


def test_workflow_does_not_directly_invoke_authority_runtime_or_release_steps() -> None:
    assert _direct_python_tools() == (
        "load_pulsemech_compute_current_run_export_candidate_bundle_v0.py",
        "build_pulsemech_compute_current_run_artifact_observed_proof_v0.py",
    )
    forbidden = {
        "check_gates.py",
        "pulsemech_compute_binding_analyzer_core_v0.py",
        "build_pulsemech_compute_binding_report_v0.py",
        "plan_pulsemech_integration_v0.py",
        "build_pulsemech_compute_planned_observed_relation_v0.py",
        "fold_pulsemech_compute_planned_observed_relation_into_status_v0.py",
        "materialize_release_decision.py",
    }
    assert forbidden.isdisjoint(_direct_python_tools())
    for run in shell_run_blocks():
        assert "attest-build-provenance" not in run
        assert "deployment" not in run.lower()
        assert ".zenodo.json" not in run
        assert "zenodo" not in run.lower()
        assert "doi" not in run.lower()


def test_all_shell_run_blocks_are_syntax_valid() -> None:
    blocks = shell_run_blocks()
    assert len(blocks) == 10
    for index, block in enumerate(blocks, start=1):
        result = subprocess.run(
            ["bash", "-n"],
            input=block.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"shell block {index} failed bash -n:\n"
            + result.stderr.decode("utf-8", errors="replace")
        )


def test_embedded_python_programs_compile() -> None:
    programs = embedded_python_programs()
    assert len(programs) == 5
    for index, program in enumerate(programs, start=1):
        ast.parse(program, filename=f"<step3g-workflow-python-{index}>")


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
