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
    / "pulsemech_compute_current_run_export_candidate.yml"
)
TOOLS_TESTS_MANIFEST = ROOT / "ci" / "tools-tests.list"
TEST_RELATIVE_PATH = (
    "tests/test_pulsemech_compute_current_run_export_candidate_workflow_v0.py"
)

EXPECTED_WORKFLOW_LINES = 2150
EXPECTED_WORKFLOW_BYTES = 92804
EXPECTED_WORKFLOW_SHA256 = (
    "d09c396aefcdfba2ed73364d6fba8aee81d98aca310079151eaf5d4e2f7faf2a"
)
EXPECTED_WORKFLOW_GIT_BLOB_SHA1 = "79e4a355cc1eab4af26f6b16e7563424e67d05f2"

EXPECTED_TESTS = frozenset(
    {
        "test_workflow_artifact_identity_matches_reviewed_fix",
        "test_tools_tests_manifest_registers_workflow_regression_exactly_once",
        "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract",
        "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit",
        "test_workflow_dispatch_is_the_only_trigger",
        "test_permissions_are_read_only_and_job_is_manual_candidate_only",
        "test_all_reusable_actions_are_full_sha_pinned",
        "test_checkouts_are_exact_independent_and_do_not_persist_credentials",
        "test_source_run_id_is_normalized_once_and_reused_everywhere",
        "test_source_run_resolution_requires_same_repo_main_dispatch_success",
        "test_source_artifact_selection_requires_exact_three_roles_and_closed_pagination",
        "test_artifact_selection_rejects_duplicate_expired_oversized_digest_and_size_drift",
        "test_retained_payloads_share_one_aggregate_byte_budget",
        "test_carrier_zip_is_deterministic_finalized_and_read_only",
        "test_carrier_loader_invocation_is_isolated_and_exact",
        "test_expectation_builder_invocation_is_isolated_and_exact",
        "test_current_run_packet_wrapper_invocation_is_isolated_and_exact",
        "test_carrier_digest_and_size_are_reused_across_outputs",
        "test_final_reverification_closes_run_artifact_checkout_and_candidate_bytes",
        "test_upload_occurs_only_after_final_reverification",
        "test_candidate_output_manifest_closes_exact_file_surface",
        "test_authority_boundary_remains_none_and_non_active",
        "test_workflow_does_not_invoke_forbidden_authority_or_transition_steps",
        "test_all_shell_run_blocks_are_syntax_valid",
        "test_embedded_python_programs_compile",
    }
)
EXPECTED_COLLECTED_TEST_ITEMS = len(EXPECTED_TESTS)
CRITICAL_TESTS = frozenset(
    {
        "test_workflow_artifact_identity_matches_reviewed_fix",
        "test_source_run_id_is_normalized_once_and_reused_everywhere",
        "test_source_run_resolution_requires_same_repo_main_dispatch_success",
        "test_source_artifact_selection_requires_exact_three_roles_and_closed_pagination",
        "test_retained_payloads_share_one_aggregate_byte_budget",
        "test_carrier_zip_is_deterministic_finalized_and_read_only",
        "test_carrier_loader_invocation_is_isolated_and_exact",
        "test_expectation_builder_invocation_is_isolated_and_exact",
        "test_current_run_packet_wrapper_invocation_is_isolated_and_exact",
        "test_final_reverification_closes_run_artifact_checkout_and_candidate_bytes",
        "test_upload_occurs_only_after_final_reverification",
        "test_authority_boundary_remains_none_and_non_active",
    }
)

_AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS = (
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_PLUGINS",
)
_AUTHORITATIVE_LAUNCH_PROBE_CHILD = (
    "PULSEMECH_STEP_3F_WORKFLOW_REGRESSION_LAUNCH_PROBE_CHILD"
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


def workflow_document() -> dict[str, Any]:
    value = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(value, dict)
    return value


def workflow_job() -> dict[str, Any]:
    document = workflow_document()
    jobs = document.get("jobs")
    assert isinstance(jobs, dict)
    job = jobs.get("build-current-run-candidate")
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
                "authoritative_step_3f_collection_contract_mismatch: "
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
                "authoritative_step_3f_critical_items_missing: "
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
            terminal.write_sep("=", "authoritative Step 3F regression failed")
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


def test_workflow_artifact_identity_matches_reviewed_fix() -> None:
    payload = WORKFLOW.read_bytes()
    assert len(payload.splitlines()) == EXPECTED_WORKFLOW_LINES
    assert len(payload) == EXPECTED_WORKFLOW_BYTES
    assert sha256_bytes(payload) == EXPECTED_WORKFLOW_SHA256
    assert git_blob_sha1(payload) == EXPECTED_WORKFLOW_GIT_BLOB_SHA1
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in payload
    assert b"\r" not in payload


def test_tools_tests_manifest_registers_workflow_regression_exactly_once() -> None:
    entries = manifest_entries()
    assert len(entries) == 146
    assert len(entries) == len(set(entries))
    assert entries.count(TEST_RELATIVE_PATH) == 1
    index = entries.index(TEST_RELATIVE_PATH)
    assert entries[index - 1] == (
        "tests/test_build_pulsemech_compute_subject_input_packet_current_run_v0.py"
    )
    assert entries[index + 1] == (
        "tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
    )
    expected_block = [
        "tests/test_check_pulsemech_compute_current_run_export_expectation_v0.py",
        "tests/test_build_pulsemech_compute_current_run_export_expectation_v0.py",
        "tests/test_load_pulsemech_compute_current_run_export_carrier_v0.py",
        "tests/test_build_pulsemech_compute_subject_input_packet_current_run_v0.py",
        TEST_RELATIVE_PATH,
        "tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py",
        "tests/test_build_pulsemech_compute_current_run_artifact_observed_proof_v0.py",
        "tests/test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py",
        "tests/test_pulsemech_compute_subject_input_packet_schema_v0.py",
    ]
    start = entries.index(expected_block[0])
    assert entries[start : start + len(expected_block)] == expected_block


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
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    expected = str(EXPECTED_COLLECTED_TEST_ITEMS).encode("ascii")
    assert b"collected " + expected + b" items" in result.stdout
    assert expected + b" passed" in result.stdout
    assert b"usage: pytest" not in result.stdout.lower()


def test_workflow_dispatch_is_the_only_trigger() -> None:
    document = workflow_document()
    assert document.get("name") == "PULSEmech compute current-run export candidate"
    triggers = document.get("on")
    assert isinstance(triggers, dict)
    assert set(triggers) == {"workflow_dispatch"}
    dispatch = triggers["workflow_dispatch"]
    assert isinstance(dispatch, dict)
    inputs = dispatch.get("inputs")
    assert isinstance(inputs, dict)
    assert set(inputs) == {"source_run_id"}
    source_run_id = inputs["source_run_id"]
    assert source_run_id.get("required") == "true"
    assert source_run_id.get("type") == "string"


def test_permissions_are_read_only_and_job_is_manual_candidate_only() -> None:
    document = workflow_document()
    assert document.get("permissions") == {"contents": "read", "actions": "read"}
    job = workflow_job()
    assert job.get("name") == "Build non-active current-run candidate"
    assert job.get("runs-on") == "ubuntu-latest"
    assert job.get("timeout-minutes") == "30"
    assert job.get("permissions") == {"contents": "read", "actions": "read"}
    assert job.get("env", {}).get("CANDIDATE_WORKFLOW_NAME") == (
        "PULSEmech compute current-run export candidate"
    )


def test_all_reusable_actions_are_full_sha_pinned() -> None:
    action_uses = [step["uses"] for step in workflow_steps() if "uses" in step]
    assert action_uses == [
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    ]
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", value) for value in action_uses)


def test_checkouts_are_exact_independent_and_do_not_persist_credentials() -> None:
    subject = step_by_name("Checkout exact source subject")
    control = step_by_name("Checkout independent protected control plane")
    assert subject["with"] == {
        "repository": "${{ github.repository }}",
        "ref": "${{ steps.source.outputs.subject_revision }}",
        "path": "subject-checkout",
        "fetch-depth": "0",
        "persist-credentials": "false",
        "lfs": "false",
        "submodules": "false",
        "set-safe-directory": "false",
    }
    assert control["with"] == {
        "repository": "${{ github.repository }}",
        "ref": "${{ steps.source.outputs.control_plane_revision }}",
        "path": "control-plane-checkout",
        "fetch-depth": "0",
        "persist-credentials": "false",
        "lfs": "false",
        "submodules": "false",
        "set-safe-directory": "false",
    }
    verification = step_run("Verify exact and independent checkouts")
    assert 'test "$(realpath "${SUBJECT_ROOT}")" != "$(realpath "${CONTROL_ROOT}")"' in verification
    assert verification.count("rev-parse HEAD") == 2


def test_source_run_id_is_normalized_once_and_reused_everywhere() -> None:
    source = step_run("Resolve exact source run and protected control plane")
    assert 'source_text = os.environ["SOURCE_RUN_ID_INPUT"].strip()' in source
    assert "source_run_id = int(source_text, 10)" in source
    assert '"source_run_id": str(source_run_id)' in source

    later_run_blocks = [
        str(step.get("run", ""))
        for step in workflow_steps()
        if step.get("name") != "Resolve exact source run and protected control plane"
    ]
    assert all("SOURCE_RUN_ID_INPUT" not in block for block in later_run_blocks)

    final_step = step_by_name(
        "Reverify source run, artifacts, checkouts, and candidate bytes"
    )
    assert final_step.get("env", {}).get("SOURCE_RUN_ID") == (
        "${{ steps.source.outputs.source_run_id }}"
    )
    final_run = str(final_step.get("run"))
    assert final_run.count(
        "/repos/${GITHUB_REPOSITORY}/actions/runs/${SOURCE_RUN_ID}"
    ) == 2
    assert "${SOURCE_RUN_ID_INPUT}" not in final_run


def test_source_run_resolution_requires_same_repo_main_dispatch_success() -> None:
    source = step_run("Resolve exact source run and protected control plane")
    required_fragments = (
        'os.environ["TRIGGER_EVENT"] != "workflow_dispatch"',
        'os.environ["TRIGGER_REF"] != "refs/heads/main"',
        'run.get("event") != "workflow_dispatch"',
        'run.get("status") != "completed" or run.get("conclusion") != "success"',
        'run.get("head_branch") != "main"',
        'repository_record.get("full_name") != repository',
        'head_repository.get("full_name") != repository',
        'run.get("path") != os.environ["SOURCE_WORKFLOW_PATH"]',
        'run.get("name") != os.environ["SOURCE_WORKFLOW_NAME"]',
        'workflow.get("state") != "active"',
    )
    for fragment in required_fragments:
        assert fragment in source


def test_source_artifact_selection_requires_exact_three_roles_and_closed_pagination() -> None:
    run = step_run("Resolve exact source artifacts")
    for role in (
        "complete_release_grade_reference_package",
        "structural_package_completeness_report",
        "independent_package_verification_report",
    ):
        assert role in run
    assert 'ROLE_BY_KEY = {' in run
    assert 'expected_names = {' in run
    assert 'selected.sort(key=lambda row: row["key"])' in run
    assert "if total_count != len(rows):" in run
    assert "artifact_listing_pagination_not_closed" in run
    assert "artifact_name_not_unique" in run
    assert 'if not isinstance(selected, list) or len(selected) != 3:' not in run


def test_artifact_selection_rejects_duplicate_expired_oversized_digest_and_size_drift() -> None:
    run = step_run("Resolve exact source artifacts")
    required_diagnostics = (
        "artifact_name_not_unique",
        "artifact_expired_or_state_unknown",
        "artifact_too_large",
        "selected_source_artifacts_too_large",
        "download_digest_mismatch",
        "download_size_mismatch",
        "download_not_regular_file",
    )
    for diagnostic in required_diagnostics:
        assert diagnostic in run
    assert "maximum_artifact_bytes = 256 * 1024 * 1024" in run
    assert "maximum_selected_bytes = 512 * 1024 * 1024" in run


def test_retained_payloads_share_one_aggregate_byte_budget() -> None:
    run = step_run("Assemble deterministic finalized current-run carrier")
    assert run.count("retained_budget = RetainedByteBudget(MAX_TOTAL_BYTES)") == 1
    assert run.count("budget=retained_budget") == 3
    assert "provider_archive_" in run
    assert "retained_budget.reserve(" in run
    assert "MAX_TOTAL_BYTES = 512 * 1024 * 1024" in run
    assert "retained_budget_exceeded" in run


def test_carrier_zip_is_deterministic_finalized_and_read_only() -> None:
    run = step_run("Assemble deterministic finalized current-run carrier")
    required = (
        "for name in sorted(output_members)",
        "info.date_time = (1980, 1, 1, 0, 0, 0)",
        "info.compress_type = zipfile.ZIP_STORED",
        "compression=zipfile.ZIP_STORED",
        "allowZip64=False",
        "info.external_attr = 0o100444 << 16",
        "temporary.chmod(0o444)",
        "temporary.replace(carrier_path)",
        "carrier_path.chmod(0o444)",
    )
    for fragment in required:
        assert fragment in run


def test_carrier_loader_invocation_is_isolated_and_exact() -> None:
    run = step_run("Materialize exact finalized carrier identity")
    assert "python -I \\\n" in run
    assert "load_pulsemech_compute_current_run_export_carrier_v0.py" in run
    assert '--control-plane-revision "${CONTROL_REVISION}"' in run
    assert '--output "${CARRIER_JSON}"' in run
    assert 'cmp --silent "${CARRIER_JSON}" "${CARRIER_STDOUT}"' in run


def test_expectation_builder_invocation_is_isolated_and_exact() -> None:
    run = step_run("Produce observed current-run expectation")
    assert "python -I \\\n" in run
    assert "build_pulsemech_compute_current_run_export_expectation_v0.py" in run
    assert "pulsemech_compute_current_run_export_expectation_v0.schema.json" in run
    assert "check_pulsemech_compute_current_run_export_expectation_v0.py" in run
    assert '--subject-revision "${SUBJECT_REVISION}"' in run
    assert '--control-plane-revision "${CONTROL_REVISION}"' in run
    assert '--output "${EXPECTATION_JSON}"' in run
    assert 'cmp --silent "${EXPECTATION_JSON}" "${EXPECTATION_STDOUT}"' in run


def test_current_run_packet_wrapper_invocation_is_isolated_and_exact() -> None:
    run = step_run("Produce observed current-run subject-input packet")
    assert "python -I \\\n" in run
    assert "build_pulsemech_compute_subject_input_packet_current_run_v0.py" in run
    assert '--expectation-sha256 "${EXPECTATION_SHA256}"' in run
    assert '--subject-revision "${SUBJECT_REVISION}"' in run
    assert '--control-plane-revision "${CONTROL_REVISION}"' in run
    assert '--output "${PACKET_JSON}"' in run
    assert 'cmp --silent "${PACKET_JSON}" "${PACKET_STDOUT}"' in run


def test_carrier_digest_and_size_are_reused_across_outputs() -> None:
    run = step_run("Verify candidate outputs and close non-authority boundary")
    assert "carrier_sha = hashlib.sha256(carrier_bytes).hexdigest()" in run
    assert "carrier_size = len(carrier_bytes)" in run
    assert 'carrier_meta.get("sha256") != carrier_sha' in run
    assert 'carrier_meta.get("size_bytes") != carrier_size' in run
    assert '("expectation", expectation_carrier)' in run
    assert '("packet", packet_carrier)' in run
    assert 'value.get("sha256") != carrier_sha' in run
    assert 'value.get("size_bytes") != carrier_size' in run


def test_final_reverification_closes_run_artifact_checkout_and_candidate_bytes() -> None:
    run = step_run("Reverify source run, artifacts, checkouts, and candidate bytes")
    required = (
        'test "$(git -C "${SUBJECT_ROOT}" rev-parse HEAD)" = "${SUBJECT_REVISION}"',
        'test "$(git -C "${CONTROL_ROOT}" rev-parse HEAD)" = "${CONTROL_REVISION}"',
        "source_run_recheck",
        "source_artifacts_recheck",
        "selected_artifact_missing",
        "selected_artifact_{field}_changed",
        "candidate_file_digest_changed",
        "candidate_file_size_changed",
        "candidate_manifest_closure_failed",
    )
    for fragment in required:
        assert fragment in run


def test_upload_occurs_only_after_final_reverification() -> None:
    steps = workflow_steps()
    names = [str(step.get("name")) for step in steps]
    final_index = names.index(
        "Reverify source run, artifacts, checkouts, and candidate bytes"
    )
    upload_index = names.index("Upload non-active current-run candidate")
    record_index = names.index("Record candidate-only result")
    assert final_index < upload_index < record_index
    upload = steps[upload_index]
    assert upload["uses"] == (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    )
    assert upload["with"]["path"] == "${{ steps.verify.outputs.candidate_root }}/"
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload["with"]["compression-level"] == "0"
    assert upload["with"]["overwrite"] == "false"
    assert upload["with"]["include-hidden-files"] == "false"


def test_candidate_output_manifest_closes_exact_file_surface() -> None:
    verify = step_run("Verify candidate outputs and close non-authority boundary")
    reverify = step_run(
        "Reverify source run, artifacts, checkouts, and candidate bytes"
    )
    assert '"manifest_scope": "all_candidate_files_except_this_manifest"' in verify
    assert '"candidate-output-manifest.json"' in verify
    assert '"file_count": len(manifest_files)' in verify
    assert "sorted(candidate_root.iterdir()" in verify
    assert "candidate_manifest_duplicate_path" in reverify
    assert "candidate_manifest_closure_failed" in reverify


def test_authority_boundary_remains_none_and_non_active() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    verify = step_run("Verify candidate outputs and close non-authority boundary")
    summary = step_run("Record candidate-only result")
    for field in (
        '"activates_compute_gate": False',
        '"changes_release_authority": False',
        '"creates_compute_budget": False',
        '"creates_gate_result": False',
        '"creates_release_decision": False',
    ):
        assert field in workflow
    assert '"candidate_only": True' in verify
    assert '"non_active": True' in verify
    assert '"produces_runtime_observation": False' in verify
    assert '"produces_transition_relation": False' in verify
    assert 'echo "| Candidate state | \\`non-active\\` |"' in summary
    assert 'echo "| Authority effect | \\`none\\` |"' in summary


def test_workflow_does_not_invoke_forbidden_authority_or_transition_steps() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    forbidden = (
        "check_gates.py",
        "pulsemech_compute_binding_analyzer_core_v0.py",
        "build_pulsemech_compute_binding_report_v0.py",
        "build_pulsemech_compute_planned_observed_relation_v0.py",
        "materialize_pulsemech_compute_planned_observed_candidate_v0.py",
        "materialize_release_decision.py",
        ".zenodo.json",
    )
    for token in forbidden:
        assert token not in workflow


def test_all_shell_run_blocks_are_syntax_valid() -> None:
    run_steps = [step for step in workflow_steps() if isinstance(step.get("run"), str)]
    assert len(run_steps) == 12
    for step in run_steps:
        result = subprocess.run(
            ["bash", "-n"],
            input=str(step["run"]).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert result.returncode == 0, (
            f"shell syntax failed for {step.get('name')!r}: "
            + result.stderr.decode("utf-8", errors="replace")
        )


def _embedded_python_programs(run: str) -> list[str]:
    lines = run.splitlines()
    programs: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != "python - <<'PY'":
            index += 1
            continue
        index += 1
        body: list[str] = []
        while index < len(lines) and lines[index].strip() != "PY":
            body.append(lines[index])
            index += 1
        assert index < len(lines), "unterminated embedded Python heredoc"
        minimum = min(
            (len(line) - len(line.lstrip()) for line in body if line.strip()),
            default=0,
        )
        programs.append("\n".join(line[minimum:] for line in body) + "\n")
        index += 1
    return programs


def test_embedded_python_programs_compile() -> None:
    programs: list[str] = []
    for step in workflow_steps():
        run = step.get("run")
        if isinstance(run, str):
            programs.extend(_embedded_python_programs(run))
    assert len(programs) == 7
    for index, program in enumerate(programs):
        ast.parse(program, filename=f"embedded-step3f-{index}.py", mode="exec")


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
