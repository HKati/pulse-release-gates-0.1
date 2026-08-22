#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import io
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "load_pulsemech_compute_current_run_export_carrier_v0.py"
EXPECTATION_SCHEMA = (
    ROOT / "schemas" / "pulsemech_compute_current_run_export_expectation_v0.schema.json"
)
TOOLS_TESTS_MANIFEST = ROOT / "ci" / "tools-tests.list"
TEST_RELATIVE_PATH = (
    "tests/test_load_pulsemech_compute_current_run_export_carrier_v0.py"
)

EXPECTED_TOOL_LINES = 2633
EXPECTED_TOOL_BYTES = 86351
EXPECTED_TOOL_SHA256 = (
    "ccc50e052975e5727d8b5d95c71bb038b6cf9dac2116bbdb968b9a26227dd3ea"
)
EXPECTED_TOOL_GIT_BLOB_SHA1 = "afeae5ee27019891716bcaeae1995030d14ec431"

EXPECTED_TESTS = frozenset(
    {
        "test_loader_artifact_identity_matches_reviewed_head",
        "test_tools_tests_manifest_registers_loader_regression_exactly_once",
        "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract",
        "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit",
        "test_direct_nonisolated_execution_fails_before_argument_parsing",
        "test_isolated_help_exposes_complete_cli_surface",
        "test_canonical_inputs_unicode_slug_and_run_key_are_exact",
        "test_failure_diagnostic_and_content_boundary_are_non_authoritative",
        "test_carrier_record_matches_expectation_schema_contract",
        "test_opened_carrier_hashes_exact_bytes_once_and_detects_mutation",
        "test_opened_carrier_rejects_nonfinalized_alias_and_size_boundaries",
        "test_same_user_writable_open_handle_is_rejected",
        "test_output_boundary_rejects_protected_and_overlapping_paths",
        "test_transactional_output_stages_before_publication_and_cleans_residue",
        "test_transactional_output_restores_existing_inode_after_postpublish_failure",
        "test_transactional_output_removes_new_publication_after_postpublish_failure",
        "test_transactional_output_detects_path_replacement_during_readback",
        "test_git_subprocess_profile_forces_local_only_bounded_execution",
        "test_git_local_only_preflight_rejects_remote_boundary_configuration",
        "test_git_local_only_preflight_rejects_promisor_alternates_and_shallow_state",
        "test_git_config_capture_is_bounded_before_parse",
        "test_producer_source_binding_requires_exact_committed_worktree_bytes",
        "test_complete_isolated_cli_is_deterministic_schema_valid_and_non_authoritative",
        "test_complete_cli_fails_closed_on_run_key_output_and_mutable_carrier",
        "test_promisor_transport_sentinel_is_blocked_before_producer_object_access",
    }
)
EXPECTED_COLLECTED_TEST_ITEMS = len(EXPECTED_TESTS)
CRITICAL_TESTS = frozenset(
    {
        "test_loader_artifact_identity_matches_reviewed_head",
        "test_same_user_writable_open_handle_is_rejected",
        "test_transactional_output_stages_before_publication_and_cleans_residue",
        "test_transactional_output_restores_existing_inode_after_postpublish_failure",
        "test_transactional_output_removes_new_publication_after_postpublish_failure",
        "test_transactional_output_detects_path_replacement_during_readback",
        "test_git_local_only_preflight_rejects_remote_boundary_configuration",
        "test_git_config_capture_is_bounded_before_parse",
        "test_producer_source_binding_requires_exact_committed_worktree_bytes",
        "test_complete_isolated_cli_is_deterministic_schema_valid_and_non_authoritative",
        "test_promisor_transport_sentinel_is_blocked_before_producer_object_access",
    }
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    try:
        return hashlib.sha1(framed, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(framed).hexdigest()


def parse_json_bytes(payload: bytes) -> dict[str, Any]:
    value = json.loads(payload.decode("utf-8", errors="strict"))
    assert isinstance(value, dict)
    return value


def import_tool_module(path: Path = TOOL, *, suffix: str = "repository") -> Any:
    module_name = f"pulsemech_current_run_export_carrier_loader_v0_{suffix}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


TOOL_MODULE = import_tool_module()


def manifest_entries() -> list[str]:
    entries: list[str] = []
    for raw in TOOLS_TESTS_MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def _collected_test_name(item: Any) -> str:
    original_name = getattr(item, "originalname", None)
    if isinstance(original_name, str) and original_name:
        return original_name
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
        current_file = Path(__file__).resolve()
        collected = [
            item
            for item in session.items
            if Path(str(item.path)).resolve() == current_file
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
                "authoritative_carrier_regression_collection_contract_mismatch: "
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
                "authoritative_carrier_regression_critical_items_missing: "
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
                "=", "authoritative carrier regression contract failed"
            )
            terminal.write_line(detail)
        if int(exitstatus) == int(pytest.ExitCode.OK):
            session.exitstatus = int(pytest.ExitCode.TESTS_FAILED)


_AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS = (
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_PLUGINS",
)
_AUTHORITATIVE_LAUNCH_PROBE_CHILD = (
    "PULSEMECH_CARRIER_REGRESSION_LAUNCH_PROBE_CHILD"
)


def _run_authoritative_regression(
    *,
    pytest_main: Callable[..., Any] | None = None,
) -> int:
    previous_environment = {
        key: os.environ.get(key)
        for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
    }
    os.environ.pop("PYTEST_ADDOPTS", None)
    os.environ.pop("PYTEST_PLUGINS", None)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    contract = _AuthoritativeRegressionContract()
    runner = pytest.main if pytest_main is None else pytest_main
    try:
        result = runner(
            [
                "-o",
                "addopts=",
                "--noconftest",
                str(Path(__file__).resolve()),
            ],
            plugins=[contract],
        )
    finally:
        for key, value in previous_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    exit_code = int(result)
    if exit_code != int(pytest.ExitCode.OK):
        return exit_code
    if contract.completed_successfully:
        return exit_code
    sys.stderr.write(
        "authoritative_carrier_regression_session_contract_not_completed: "
        + json.dumps(contract.completion_state, sort_keys=True)
        + "\n"
    )
    return int(pytest.ExitCode.TESTS_FAILED)


def run_tool(
    *arguments: str,
    isolated: bool,
    tool: Path = TOOL,
    cwd: Path = ROOT,
    extra_env: dict[str, str] | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[bytes]:
    command = [sys.executable]
    if isolated:
        command.append("-I")
    command.extend([str(tool), *arguments])
    environment = dict(os.environ)
    if extra_env:
        environment.update(extra_env)
    return subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
        timeout=timeout,
    )


def deterministic_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo("current-run-export/PRESERVATION_MANIFEST_v0.json")
        info.date_time = (2026, 1, 1, 0, 0, 0)
        info.external_attr = 0o100444 << 16
        archive.writestr(info, b'{"record":"current-run"}\n')
    return buffer.getvalue()


def write_finalized_carrier(
    staging_root: Path,
    relative_path: str = "exports/current-run.zip",
    *,
    payload: bytes | None = None,
) -> Path:
    carrier = staging_root / PurePosixPath(relative_path)
    carrier.parent.mkdir(parents=True, exist_ok=True)
    carrier.write_bytes(deterministic_zip_bytes() if payload is None else payload)
    carrier.chmod(0o444)
    return carrier


def trusted_git_path(module: Any = TOOL_MODULE) -> Path:
    errors: list[str] = []
    for candidate in module.LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES:
        if not candidate.exists():
            errors.append(f"unavailable:{candidate}")
            continue
        try:
            validated = module._validated_trusted_git(candidate)
            module._require_trusted_git_local_only_support(validated)
        except module.CarrierError as exc:
            errors.append(str(exc))
            continue
        return validated
    pytest.fail(
        "authoritative_trusted_git_prerequisite_failed: "
        + json.dumps(errors, sort_keys=True)
    )


def git_run(
    repository: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    git = trusted_git_path()
    result = subprocess.run(
        [str(git), "-C", str(repository), *arguments],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C",
            "LC_ALL": "C",
        },
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"git command failed: {arguments!r}\n"
            + result.stderr.decode("utf-8", errors="replace")
        )
    return result


def initialize_control_plane_repository(
    root: Path,
    *,
    tool_bytes: bytes | None = None,
) -> tuple[Path, str]:
    root.mkdir(parents=True, exist_ok=True)
    git_run(root, "init", "-q")
    git_run(root, "config", "user.name", "PULSEmech Regression")
    git_run(root, "config", "user.email", "regression@example.invalid")
    tool_path = root / TOOL_MODULE.PRODUCER_SOURCE_PATH
    tool_path.parent.mkdir(parents=True, exist_ok=True)
    tool_path.write_bytes(TOOL.read_bytes() if tool_bytes is None else tool_bytes)
    git_run(root, "add", TOOL_MODULE.PRODUCER_SOURCE_PATH)
    git_run(root, "commit", "-q", "-m", "carrier loader regression fixture")
    revision = (
        git_run(root, "rev-parse", "HEAD")
        .stdout.decode("ascii", errors="strict")
        .strip()
    )
    assert re.fullmatch(r"[0-9a-f]{40}", revision)
    return tool_path, revision


def carrier_cli_arguments(
    *,
    tool_module: Any,
    staging_root: Path,
    control_root: Path,
    revision: str,
    output: Path | None = None,
    workflow_name: str = "Déploy Current Run",
    subject_run_key: str | None = None,
) -> list[str]:
    run_id = 9001
    run_number = 17
    run_attempt = 2
    key = subject_run_key or (
        f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT={run_attempt}"
        f"|GITHUB_WORKFLOW={workflow_name}"
    )
    arguments = [
        "--staging-root",
        str(staging_root),
        "--staged-relative-path",
        "exports/current-run.zip",
        "--root-prefix",
        "current-run-export/",
        "--carrier-id-namespace",
        "pulsemech/current-run",
        "--workflow-name",
        workflow_name,
        "--workflow-run-id",
        str(run_id),
        "--workflow-run-number",
        str(run_number),
        "--workflow-run-attempt",
        str(run_attempt),
        "--subject-run-key",
        key,
        "--finalized-utc",
        "2026-08-18T07:00:00Z",
        "--ci-workflow-or-job-identity",
        "PULSE CI / current-run carrier candidate",
        "--control-plane-root",
        str(control_root),
        "--control-plane-revision",
        revision,
        "--trusted-git",
        str(trusted_git_path(tool_module)),
    ]
    if output is not None:
        arguments.extend(("--output", str(output)))
    return arguments


def assert_no_transaction_residue(output: Path) -> None:
    residues = sorted(
        item.name
        for item in output.parent.iterdir()
        if item.name.startswith(f".{output.name}.")
    )
    assert residues == []


def test_loader_artifact_identity_matches_reviewed_head() -> None:
    payload = TOOL.read_bytes()
    assert len(payload) == EXPECTED_TOOL_BYTES
    assert payload.count(b"\n") == EXPECTED_TOOL_LINES
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in payload
    assert sha256_bytes(payload) == EXPECTED_TOOL_SHA256
    assert git_blob_sha1(payload) == EXPECTED_TOOL_GIT_BLOB_SHA1
    assert TOOL_MODULE.TOOL_NAME == "load_pulsemech_compute_current_run_export_carrier_v0"
    assert TOOL_MODULE.TOOL_VERSION == "0.1.0"
    assert TOOL_MODULE.DOCUMENT_TYPE == "pulsemech_compute_current_run_export_carrier"
    assert TOOL_MODULE.PRODUCER_SOURCE_PATH == TOOL.relative_to(ROOT).as_posix()


def test_tools_tests_manifest_registers_loader_regression_exactly_once() -> None:
    entries = manifest_entries()
    assert len(entries) == len(set(entries))
    assert entries.count(TEST_RELATIVE_PATH) == 1
    index = entries.index(TEST_RELATIVE_PATH)
    assert entries[index - 1] == (
        "tests/test_build_pulsemech_compute_current_run_export_expectation_v0.py"
    )
    assert entries[index + 1] == (
        "tests/test_build_pulsemech_compute_subject_input_packet_current_run_v0.py"
    )
    assert entries[index + 2] == (
        "tests/test_pulsemech_compute_current_run_export_candidate_workflow_v0.py"
    )
    assert entries[index + 3] == (
        "tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
    )
    assert entries[index + 4] == (
        "tests/test_build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"
    )
    assert entries[index + 5] == (
        "tests/test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py"
    )
    assert entries[index + 6] == (
        "tests/test_pulsemech_compute_subject_input_packet_schema_v0.py"
    )


def test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_ADDOPTS", "--help")
    monkeypatch.setenv("PYTEST_PLUGINS", "must_not_import")
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "0")
    observed: dict[str, Any] = {}

    def successful_main(arguments: list[str], *, plugins: list[Any]) -> int:
        observed["arguments"] = list(arguments)
        observed["environment"] = {
            key: os.environ.get(key)
            for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
        }
        contract = plugins[0]
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
    assert os.environ["PYTEST_ADDOPTS"] == "--help"
    assert os.environ["PYTEST_PLUGINS"] == "must_not_import"
    assert os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "0"

    def incomplete_main(_arguments: list[str], *, plugins: list[Any]) -> int:
        assert len(plugins) == 1
        return int(pytest.ExitCode.OK)

    assert _run_authoritative_regression(pytest_main=incomplete_main) == int(
        pytest.ExitCode.TESTS_FAILED
    )


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
        timeout=300,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    expected = str(EXPECTED_COLLECTED_TEST_ITEMS).encode("ascii")
    assert b"collected " + expected + b" items" in result.stdout
    assert expected + b" passed" in result.stdout
    assert b"usage: pytest" not in result.stdout.lower()


def test_direct_nonisolated_execution_fails_before_argument_parsing() -> None:
    first = run_tool("--help", isolated=False)
    second = run_tool("--not-a-real-option", isolated=False)
    assert first.returncode == second.returncode == 2
    assert first.stdout == second.stdout == b""
    assert first.stderr == second.stderr
    diagnostic = parse_json_bytes(first.stderr)
    assert diagnostic == {
        "authority_effect": "none",
        "document_type": "pulsemech_compute_current_run_export_carrier",
        "errors": ["isolated_python_runtime_required: launch with python -I"],
        "exit_kind": "python_runtime_boundary_error",
        "ok": False,
        "tool": "load_pulsemech_compute_current_run_export_carrier_v0",
        "tool_version": "0.1.0",
    }


def test_isolated_help_exposes_complete_cli_surface() -> None:
    result = run_tool("--help", isolated=True)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    text = result.stdout.decode("utf-8", errors="strict")
    for option in (
        "--staging-root",
        "--staged-relative-path",
        "--root-prefix",
        "--carrier-id-namespace",
        "--workflow-name",
        "--workflow-run-id",
        "--workflow-run-number",
        "--workflow-run-attempt",
        "--subject-run-key",
        "--finalized-utc",
        "--ci-workflow-or-job-identity",
        "--control-plane-root",
        "--control-plane-revision",
        "--trusted-git",
        "--max-carrier-bytes",
        "--output",
    ):
        assert option in text


def test_canonical_inputs_unicode_slug_and_run_key_are_exact() -> None:
    assert TOOL_MODULE._slug("Déploy Current Run") == "d-ploy-current-run"
    assert TOOL_MODULE._slug("１２ Run") == "run"
    assert TOOL_MODULE._slug("A..B__C++") == "a..b__c++"
    with pytest.raises(TOOL_MODULE.CarrierError, match="workflow_identity_slug_empty"):
        TOOL_MODULE._slug("部署")
    assert TOOL_MODULE._carrier_id(
        namespace="pulsemech/current-run",
        workflow_name="Déploy Current Run",
        workflow_run_number=17,
    ) == "carrier:pulsemech/current-run/d-ploy-current-run-17/v0"
    assert TOOL_MODULE._subject_run_key(
        workflow_run_id=9001,
        workflow_run_attempt=2,
        workflow_name="Déploy Current Run",
    ) == (
        "GITHUB_RUN_ID=9001|GITHUB_RUN_ATTEMPT=2|"
        "GITHUB_WORKFLOW=Déploy Current Run"
    )
    for value in ("/absolute.zip", "../escape.zip", "a\\b.zip", "a/./b.zip"):
        with pytest.raises(TOOL_MODULE.CarrierError):
            TOOL_MODULE._canonical_member_path(value, label="carrier")
    assert TOOL_MODULE._canonical_directory_prefix(
        "current-run-export/", label="root_prefix"
    ) == "current-run-export/"


def test_failure_diagnostic_and_content_boundary_are_non_authoritative() -> None:
    diagnostic = TOOL_MODULE.make_failure_diagnostic(
        error="synthetic failure",
        exit_kind="test_error",
    )
    rendered = TOOL_MODULE.render_json(diagnostic)
    assert rendered == TOOL_MODULE.render_json(parse_json_bytes(rendered))
    assert diagnostic["authority_effect"] == "none"
    assert diagnostic["ok"] is False
    source = TOOL.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "zipfile" not in imported
    assert "tarfile" not in imported
    assert "shutil" not in imported
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not {"extract", "extractall", "unpack_archive"}.intersection(calls)


def test_carrier_record_matches_expectation_schema_contract() -> None:
    producer = TOOL_MODULE._producer_record(
        ci_workflow_or_job_identity="PULSE CI / carrier",
        subject_run_key=(
            "GITHUB_RUN_ID=9001|GITHUB_RUN_ATTEMPT=2|"
            "GITHUB_WORKFLOW=Déploy Current Run"
        ),
        control_plane_revision="a" * 40,
        producer_source_sha256="b" * 64,
    )
    carrier = TOOL_MODULE._carrier_record(
        carrier_id="carrier:pulsemech/current-run/d-ploy-current-run-17/v0",
        staged_relative_path="exports/current-run.zip",
        root_prefix="current-run-export/",
        finalized_utc="2026-08-18T07:00:00Z",
        carrier_sha256="c" * 64,
        carrier_size_bytes=123,
        producer=producer,
    )
    schema = json.loads(EXPECTATION_SCHEMA.read_text(encoding="utf-8"))
    carrier_schema = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": "#/$defs/carrier",
    }
    jsonschema.Draft202012Validator(
        carrier_schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(carrier)
    assert set(carrier) == {
        "artifact_payload_mode",
        "carrier_id",
        "carrier_kind",
        "finalized",
        "finalized_utc",
        "immutable",
        "media_type",
        "path_base",
        "producer",
        "provider_binding",
        "root_prefix",
        "sha256",
        "size_bytes",
        "staged_relative_path",
    }
    assert carrier["provider_binding"] is None
    assert carrier["sha256"] == "c" * 64
    assert "carrier_sha256" not in carrier


def test_opened_carrier_hashes_exact_bytes_once_and_detects_mutation(
    tmp_path: Path,
) -> None:
    staging = tmp_path / "staging"
    carrier = write_finalized_carrier(staging)
    payload = carrier.read_bytes()
    observed_lease = None
    with TOOL_MODULE.OpenedCarrier.open(
        staging_root=staging,
        staged_relative_path="exports/current-run.zip",
        max_bytes=len(payload),
    ) as opened:
        observed_lease = opened.lease
        assert observed_lease.acquired is True
        observed_lease.verify()
        digest, size = opened.hash_once()
        assert digest == sha256_bytes(payload)
        assert size == len(payload)
        assert observed_lease.acquired is True
        observed_lease.verify()
        with pytest.raises(
            TOOL_MODULE.CarrierError, match="carrier_digest_already_materialized"
        ):
            opened.hash_once()
    assert observed_lease is not None
    assert observed_lease._closed is True
    assert observed_lease.acquired is False

    carrier_two = write_finalized_carrier(
        staging,
        relative_path="exports/mutable.zip",
    )
    with TOOL_MODULE.OpenedCarrier.open(
        staging_root=staging,
        staged_relative_path="exports/mutable.zip",
        max_bytes=10 * 1024 * 1024,
    ) as opened:
        carrier_two.chmod(0o644)
        carrier_two.write_bytes(payload + b"mutation")
        assert opened.lease.break_observed is True
        with pytest.raises(
            TOOL_MODULE.CarrierError, match="carrier_identity_changed_after_open"
        ):
            opened.verify_unchanged()

    carrier_three = write_finalized_carrier(
        staging,
        relative_path="exports/replaced.zip",
    )
    replacement = staging / "exports" / "replacement.zip"
    replacement.write_bytes(payload)
    replacement.chmod(0o444)
    with TOOL_MODULE.OpenedCarrier.open(
        staging_root=staging,
        staged_relative_path="exports/replaced.zip",
        max_bytes=10 * 1024 * 1024,
    ) as opened:
        os.replace(replacement, carrier_three)
        with pytest.raises(
            TOOL_MODULE.CarrierError, match="carrier_(?:identity_changed_after_open|path_binding_changed)"
        ):
            opened.verify_unchanged()


def test_opened_carrier_rejects_nonfinalized_alias_and_size_boundaries(
    tmp_path: Path,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()

    empty = staging / "empty.zip"
    empty.write_bytes(b"")
    empty.chmod(0o444)
    with pytest.raises(TOOL_MODULE.CarrierError, match="carrier_empty"):
        TOOL_MODULE.OpenedCarrier.open(
            staging_root=staging,
            staged_relative_path="empty.zip",
            max_bytes=100,
        )

    upper = staging / "carrier.ZIP"
    upper.write_bytes(b"x")
    upper.chmod(0o444)
    with pytest.raises(
        TOOL_MODULE.CarrierError, match="carrier_leaf_must_end_with_lowercase_zip"
    ):
        TOOL_MODULE.OpenedCarrier.open(
            staging_root=staging,
            staged_relative_path="carrier.ZIP",
            max_bytes=100,
        )

    writable = staging / "writable.zip"
    writable.write_bytes(b"abc")
    writable.chmod(0o644)
    with pytest.raises(
        TOOL_MODULE.CarrierError, match="carrier_not_finalized_read_only"
    ):
        TOOL_MODULE.OpenedCarrier.open(
            staging_root=staging,
            staged_relative_path="writable.zip",
            max_bytes=100,
        )

    original = staging / "hardlinked.zip"
    original.write_bytes(b"abc")
    original.chmod(0o444)
    os.link(original, staging / "alias.zip")
    with pytest.raises(
        TOOL_MODULE.CarrierError, match="carrier_hardlink_count_rejected"
    ):
        TOOL_MODULE.OpenedCarrier.open(
            staging_root=staging,
            staged_relative_path="hardlinked.zip",
            max_bytes=100,
        )

    target = staging / "target.zip"
    target.write_bytes(b"abc")
    target.chmod(0o444)
    (staging / "symlink.zip").symlink_to(target.name)
    with pytest.raises(TOOL_MODULE.CarrierError, match="carrier_open_failed"):
        TOOL_MODULE.OpenedCarrier.open(
            staging_root=staging,
            staged_relative_path="symlink.zip",
            max_bytes=100,
        )

    large = staging / "large.zip"
    large.write_bytes(b"abcd")
    large.chmod(0o444)
    with pytest.raises(TOOL_MODULE.CarrierError, match="carrier_too_large"):
        TOOL_MODULE.OpenedCarrier.open(
            staging_root=staging,
            staged_relative_path="large.zip",
            max_bytes=3,
        )


def test_same_user_writable_open_handle_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / "staging"
    carrier = staging / "writer.zip"
    staging.mkdir()
    carrier.write_bytes(b"writer-boundary")
    writer_fd = os.open(carrier, os.O_RDWR)
    carrier.chmod(0o444)
    try:
        with pytest.raises(
            TOOL_MODULE.CarrierError, match="carrier_open_for_writing"
        ):
            TOOL_MODULE.OpenedCarrier.open(
                staging_root=staging,
                staged_relative_path="writer.zip",
                max_bytes=100,
            )
    finally:
        os.close(writer_fd)

    unsupported = write_finalized_carrier(
        staging,
        relative_path="unsupported.zip",
    )
    assert unsupported.exists()
    real_fcntl = TOOL_MODULE.fcntl
    monkeypatch.setattr(TOOL_MODULE, "fcntl", None)
    with pytest.raises(
        TOOL_MODULE.CarrierError, match="carrier_read_lease_unsupported"
    ):
        TOOL_MODULE.OpenedCarrier.open(
            staging_root=staging,
            staged_relative_path="unsupported.zip",
            max_bytes=10 * 1024 * 1024,
        )
    monkeypatch.setattr(TOOL_MODULE, "fcntl", real_fcntl)

    lost = write_finalized_carrier(
        staging,
        relative_path="lost.zip",
    )
    assert lost.exists()

    class LostLeaseProxy:
        def __getattr__(self, name: str) -> Any:
            return getattr(real_fcntl, name)

        def fcntl(self, descriptor: int, operation: int, *arguments: Any) -> Any:
            if operation == real_fcntl.F_GETLEASE:
                return real_fcntl.F_UNLCK
            return real_fcntl.fcntl(descriptor, operation, *arguments)

    with TOOL_MODULE.OpenedCarrier.open(
        staging_root=staging,
        staged_relative_path="lost.zip",
        max_bytes=10 * 1024 * 1024,
    ) as opened:
        monkeypatch.setattr(TOOL_MODULE, "fcntl", LostLeaseProxy())
        with pytest.raises(
            TOOL_MODULE.CarrierError, match="carrier_read_lease_lost"
        ):
            opened.verify_unchanged()
        monkeypatch.setattr(TOOL_MODULE, "fcntl", real_fcntl)

    broken = write_finalized_carrier(
        staging,
        relative_path="broken.zip",
    )
    assert broken.exists()
    with TOOL_MODULE.OpenedCarrier.open(
        staging_root=staging,
        staged_relative_path="broken.zip",
        max_bytes=10 * 1024 * 1024,
    ) as opened:
        opened.lease.break_observed = True
        with pytest.raises(
            TOOL_MODULE.CarrierError, match="carrier_read_lease_break_observed"
        ):
            opened.verify_unchanged()


def test_output_boundary_rejects_protected_and_overlapping_paths(
    tmp_path: Path,
) -> None:
    staging = tmp_path / "staging"
    control = tmp_path / "control"
    external = tmp_path / "external"
    staging.mkdir()
    control.mkdir()
    external.mkdir()
    carrier = write_finalized_carrier(staging)
    source = control / TOOL_MODULE.PRODUCER_SOURCE_PATH
    source.parent.mkdir(parents=True)
    source.write_bytes(TOOL.read_bytes())

    with pytest.raises(TOOL_MODULE.CarrierError, match="output_name_protected"):
        TOOL_MODULE._reject_unsafe_output(
            external / "STATUS.JSON",
            staging_root=staging,
            control_plane_root=control,
            carrier_path=carrier,
            source_path=source,
        )
    for candidate, pattern in (
        (staging / "output.json", "output_inside_staging_root"),
        (control / "output.json", "output_inside_control_plane_root"),
        (carrier, "output_inside_staging_root"),
        (source, "output_inside_control_plane_root"),
    ):
        with pytest.raises(TOOL_MODULE.CarrierError, match=pattern):
            TOOL_MODULE._reject_unsafe_output(
                candidate,
                staging_root=staging,
                control_plane_root=control,
                carrier_path=carrier,
                source_path=source,
            )
    symlink_output = external / "symlink.json"
    target = external / "target.json"
    target.write_text("target", encoding="utf-8")
    symlink_output.symlink_to(target.name)
    with pytest.raises(
        TOOL_MODULE.CarrierError,
        match="output_existing_target_not_regular_file",
    ):
        TOOL_MODULE._reject_unsafe_output(
            symlink_output,
            staging_root=staging,
            control_plane_root=control,
            carrier_path=carrier,
            source_path=source,
        )
    safe = external / "carrier.json"
    assert TOOL_MODULE._reject_unsafe_output(
        safe,
        staging_root=staging,
        control_plane_root=control,
        carrier_path=carrier,
        source_path=source,
    ) == safe.resolve(strict=False)


def test_transactional_output_stages_before_publication_and_cleans_residue(
    tmp_path: Path,
) -> None:
    output = tmp_path / "carrier.json"
    output.write_bytes(b"previous")
    initial_inode = (output.stat().st_dev, output.stat().st_ino)
    payload = b'{"carrier":"new"}\n'
    observations: list[tuple[str, bytes]] = []

    def verify_inputs() -> None:
        observations.append(("verify", output.read_bytes()))

    def finalize_inputs() -> None:
        observations.append(("finalize", output.read_bytes()))

    TOOL_MODULE._atomic_write_external(
        output,
        payload,
        verify_inputs=verify_inputs,
        finalize_inputs=finalize_inputs,
    )
    assert observations == [
        ("verify", b"previous"),
        ("verify", payload),
        ("finalize", payload),
    ]
    assert output.read_bytes() == payload
    assert (output.stat().st_dev, output.stat().st_ino) != initial_inode
    assert stat.S_IMODE(output.stat().st_mode) == 0o644
    assert_no_transaction_residue(output)


def test_transactional_output_restores_existing_inode_after_postpublish_failure(
    tmp_path: Path,
) -> None:
    output = tmp_path / "carrier.json"
    output.write_bytes(b"previous-valid")
    initial = output.stat()
    calls = 0

    def verify_inputs() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise TOOL_MODULE.CarrierError(
                "synthetic_postpublish_input_change",
                exit_kind="producer_binding_error",
            )

    with pytest.raises(
        TOOL_MODULE.CarrierError, match="synthetic_postpublish_input_change"
    ):
        TOOL_MODULE._atomic_write_external(
            output,
            b'{"carrier":"new"}\n',
            verify_inputs=verify_inputs,
        )
    restored = output.stat()
    assert output.read_bytes() == b"previous-valid"
    assert (restored.st_dev, restored.st_ino) == (initial.st_dev, initial.st_ino)
    assert_no_transaction_residue(output)


def test_transactional_output_removes_new_publication_after_postpublish_failure(
    tmp_path: Path,
) -> None:
    output = tmp_path / "carrier.json"
    calls = 0

    def verify_inputs() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise TOOL_MODULE.CarrierError(
                "synthetic_postpublish_carrier_change",
                exit_kind="carrier_boundary_error",
            )

    with pytest.raises(
        TOOL_MODULE.CarrierError, match="synthetic_postpublish_carrier_change"
    ):
        TOOL_MODULE._atomic_write_external(
            output,
            b'{"carrier":"new"}\n',
            verify_inputs=verify_inputs,
        )
    assert not output.exists()
    assert_no_transaction_residue(output)


def test_transactional_output_detects_path_replacement_during_readback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "carrier.json"
    replacement = tmp_path / "replacement.json"
    replacement.write_bytes(b"attacker-replacement")
    original_reader = TOOL_MODULE._read_descriptor_bytes
    replaced = False

    def racing_reader(
        descriptor: int,
        *,
        label: str,
        max_bytes: int,
        expected_size: int | None = None,
    ) -> bytes:
        nonlocal replaced
        result = original_reader(
            descriptor,
            label=label,
            max_bytes=max_bytes,
            expected_size=expected_size,
        )
        if label == "written_output" and not replaced:
            os.replace(replacement, output)
            replaced = True
        return result

    monkeypatch.setattr(TOOL_MODULE, "_read_descriptor_bytes", racing_reader)
    with pytest.raises(
        TOOL_MODULE.CarrierError, match="written_output_(?:changed_during_readback|path_binding_changed)"
    ):
        TOOL_MODULE._atomic_write_external(
            output,
            b'{"carrier":"new"}\n',
            verify_inputs=lambda: None,
        )
    assert replaced is True
    assert output.read_bytes() == b"attacker-replacement"
    assert_no_transaction_residue(output)


def test_git_subprocess_profile_forces_local_only_bounded_execution(
    tmp_path: Path,
) -> None:
    git = trusted_git_path()
    command = TOOL_MODULE._git_command(
        git_path=git,
        repository_root=tmp_path,
        arguments=("rev-parse", "HEAD"),
    )
    assert command[0] == str(git)
    assert "--no-lazy-fetch" in command
    assert command.index("--no-lazy-fetch") < command.index("-C")
    joined = "\n".join(command)
    for required in (
        "protocol.allow=never",
        "protocol.ext.allow=never",
        "protocol.file.allow=never",
        "protocol.git.allow=never",
        "protocol.http.allow=never",
        "protocol.https.allow=never",
        "protocol.ssh.allow=never",
        "core.sshCommand=/bin/false",
        "credential.helper=",
        "credential.interactive=false",
    ):
        assert required in joined
    environment = TOOL_MODULE._git_environment(git)
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
    assert environment["GIT_ALLOW_PROTOCOL"] == ""
    assert environment["GIT_SSH_COMMAND"] == "/bin/false"
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["PATH"] == str(git.parent)

    with pytest.raises(
        TOOL_MODULE.CarrierError, match="synthetic_stdout_capture_limit_exceeded"
    ):
        TOOL_MODULE._run_bounded_command(
            command=(
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(b'x' * 17)",
            ),
            environment=dict(os.environ),
            label="synthetic",
            max_stdout_bytes=16,
            timeout_seconds=10,
        )


def test_git_local_only_preflight_rejects_remote_boundary_configuration(
    tmp_path: Path,
) -> None:
    cases = (
        ("local", "extensions.partialClone", "origin"),
        ("local", "remote.origin.promisor", "true"),
        ("local", "remote.origin.partialCloneFilter", "blob:none"),
        ("local", "core.sshCommand", "/tmp/subject-selected-ssh"),
        ("worktree", "core.sshCommand", "/tmp/worktree-selected-ssh"),
    )
    git = trusted_git_path()
    for index, (scope, key, value) in enumerate(cases):
        repository = tmp_path / f"repo-{index}"
        initialize_control_plane_repository(repository)
        if scope == "worktree":
            git_run(repository, "config", "extensions.worktreeConfig", "true")
            git_run(repository, "config", "--worktree", key, value)
        else:
            git_run(repository, "config", "--local", key, value)
        with pytest.raises(
            TOOL_MODULE.CarrierError,
            match="control_plane_git_local_only_config_rejected",
        ):
            TOOL_MODULE._verify_git_local_only_repository_state(
                git_path=git,
                repository_root=repository,
            )


def test_git_local_only_preflight_rejects_promisor_alternates_and_shallow_state(
    tmp_path: Path,
) -> None:
    git = trusted_git_path()

    promisor_repo = tmp_path / "promisor"
    initialize_control_plane_repository(promisor_repo)
    pack = promisor_repo / ".git" / "objects" / "pack"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "pack-test.promisor").write_bytes(b"")
    with pytest.raises(
        TOOL_MODULE.CarrierError,
        match="control_plane_git_promisor_pack_marker_rejected",
    ):
        TOOL_MODULE._verify_git_local_only_repository_state(
            git_path=git,
            repository_root=promisor_repo,
        )

    for name, relative, content, pattern in (
        (
            "alternates",
            ".git/objects/info/alternates",
            b"/tmp/untrusted-objects\n",
            "control_plane_git_alternates_rejected",
        ),
        (
            "http-alternates",
            ".git/objects/info/http-alternates",
            b"https://example.invalid/objects\n",
            "control_plane_git_http_alternates_rejected",
        ),
        (
            "shallow",
            ".git/shallow",
            (b"a" * 40) + b"\n",
            "control_plane_git_shallow_boundary_rejected",
        ),
    ):
        repository = tmp_path / name
        initialize_control_plane_repository(repository)
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        with pytest.raises(TOOL_MODULE.CarrierError, match=pattern):
            TOOL_MODULE._verify_git_local_only_repository_state(
                git_path=git,
                repository_root=repository,
            )


def test_git_config_capture_is_bounded_before_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "oversized-config"
    initialize_control_plane_repository(repository)
    config = repository / ".git" / "config"
    with config.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n[pulse \"oversized\"]\n")
        stream.write("payload = ")
        stream.write(
            "x"
            * (
                TOOL_MODULE.MAX_GIT_CONFIG_BYTES
                + TOOL_MODULE.GIT_CAPTURE_CHUNK_BYTES
            )
        )
        stream.write("\n")
    parser_called = False

    def forbidden_parser(_raw: bytes, *, label: str) -> list[tuple[str, str, str]]:
        nonlocal parser_called
        parser_called = True
        raise AssertionError(label)

    monkeypatch.setattr(TOOL_MODULE, "_parse_scoped_git_config", forbidden_parser)
    with pytest.raises(
        TOOL_MODULE.CarrierError,
        match="control_plane_git_config_stdout_capture_limit_exceeded",
    ):
        TOOL_MODULE._verify_git_local_only_repository_state(
            git_path=trusted_git_path(),
            repository_root=repository,
        )
    assert parser_called is False


def test_producer_source_binding_requires_exact_committed_worktree_bytes(
    tmp_path: Path,
) -> None:
    control = tmp_path / "control"
    tool_path, revision = initialize_control_plane_repository(control)
    module = import_tool_module(tool_path, suffix="temporary_control")
    git = trusted_git_path(module)
    module._verify_git_repository(
        git_path=git,
        repository_root=control,
        expected_revision=revision,
    )
    module._verify_git_local_only_repository_state(
        git_path=git,
        repository_root=control,
    )
    digest, committed, observed_path = module._verify_producer_source(
        git_path=git,
        control_plane_root=control,
        control_plane_revision=revision,
    )
    assert digest == EXPECTED_TOOL_SHA256
    assert committed == TOOL.read_bytes()
    assert observed_path == tool_path.resolve(strict=True)

    tool_path.write_bytes(tool_path.read_bytes() + b"\n# working-tree mutation\n")
    with pytest.raises(
        module.CarrierError,
        match="carrier_loader_working_tree_differs_from_exact_revision",
    ):
        module._verify_producer_source(
            git_path=git,
            control_plane_root=control,
            control_plane_revision=revision,
        )


def test_complete_isolated_cli_is_deterministic_schema_valid_and_non_authoritative(
    tmp_path: Path,
) -> None:
    control = tmp_path / "control"
    tool_path, revision = initialize_control_plane_repository(control)
    module = import_tool_module(tool_path, suffix="complete_cli")
    staging = tmp_path / "staging"
    carrier_path = write_finalized_carrier(staging)
    carrier_bytes = carrier_path.read_bytes()
    output = tmp_path / "output" / "carrier.json"
    output.parent.mkdir()
    arguments = carrier_cli_arguments(
        tool_module=module,
        staging_root=staging,
        control_root=control,
        revision=revision,
        output=output,
    )
    first = run_tool(
        *arguments,
        isolated=True,
        tool=tool_path,
        cwd=control,
        timeout=240,
    )
    second_arguments = carrier_cli_arguments(
        tool_module=module,
        staging_root=staging,
        control_root=control,
        revision=revision,
    )
    second = run_tool(
        *second_arguments,
        isolated=True,
        tool=tool_path,
        cwd=control,
        timeout=240,
    )
    assert first.returncode == second.returncode == 0, (
        first.stderr + second.stderr
    ).decode("utf-8", errors="replace")
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == output.read_bytes()
    carrier = parse_json_bytes(first.stdout)
    assert first.stdout == module.render_json(carrier)
    schema = json.loads(EXPECTATION_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/carrier"},
        format_checker=jsonschema.FormatChecker(),
    ).validate(carrier)
    assert carrier["carrier_id"] == (
        "carrier:pulsemech/current-run/d-ploy-current-run-17/v0"
    )
    assert carrier["sha256"] == sha256_bytes(carrier_bytes)
    assert carrier["size_bytes"] == len(carrier_bytes)
    assert carrier["provider_binding"] is None
    assert carrier["immutable"] is carrier["finalized"] is True
    assert carrier["producer"]["producer_source_revision"] == revision
    assert carrier["producer"]["producer_source_sha256"] == EXPECTED_TOOL_SHA256
    assert carrier["producer"]["production_mode"] == (
        "current_run_export_carrier_builder"
    )
    assert carrier_path.read_bytes() == carrier_bytes
    assert stat.S_IMODE(carrier_path.stat().st_mode) == 0o444
    assert_no_transaction_residue(output)


def test_complete_cli_fails_closed_on_run_key_output_and_mutable_carrier(
    tmp_path: Path,
) -> None:
    control = tmp_path / "control"
    tool_path, revision = initialize_control_plane_repository(control)
    module = import_tool_module(tool_path, suffix="negative_cli")
    staging = tmp_path / "staging"
    carrier = write_finalized_carrier(staging)

    wrong_key = run_tool(
        *carrier_cli_arguments(
            tool_module=module,
            staging_root=staging,
            control_root=control,
            revision=revision,
            subject_run_key="GITHUB_RUN_ID=1|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=wrong",
        ),
        isolated=True,
        tool=tool_path,
        cwd=control,
        timeout=240,
    )
    assert wrong_key.returncode == 2
    assert wrong_key.stdout == b""
    wrong_diagnostic = parse_json_bytes(wrong_key.stderr)
    assert wrong_diagnostic["authority_effect"] == "none"
    assert wrong_diagnostic["exit_kind"] == "input_boundary_error"
    assert any("subject_run_key_mismatch" in item for item in wrong_diagnostic["errors"])

    inside_output = run_tool(
        *carrier_cli_arguments(
            tool_module=module,
            staging_root=staging,
            control_root=control,
            revision=revision,
            output=staging / "carrier.json",
        ),
        isolated=True,
        tool=tool_path,
        cwd=control,
        timeout=240,
    )
    assert inside_output.returncode == 2
    assert parse_json_bytes(inside_output.stderr)["exit_kind"] == "output_boundary_error"

    carrier.chmod(0o644)
    mutable = run_tool(
        *carrier_cli_arguments(
            tool_module=module,
            staging_root=staging,
            control_root=control,
            revision=revision,
        ),
        isolated=True,
        tool=tool_path,
        cwd=control,
        timeout=240,
    )
    assert mutable.returncode == 2
    mutable_diagnostic = parse_json_bytes(mutable.stderr)
    assert mutable_diagnostic["authority_effect"] == "none"
    assert any(
        "carrier_not_finalized_read_only" in item
        for item in mutable_diagnostic["errors"]
    )


def test_promisor_transport_sentinel_is_blocked_before_producer_object_access(
    tmp_path: Path,
) -> None:
    control = tmp_path / "control"
    tool_path, revision = initialize_control_plane_repository(control)
    module = import_tool_module(tool_path, suffix="promisor_cli")
    staging = tmp_path / "staging"
    write_finalized_carrier(staging)
    marker = tmp_path / "transport-executed.txt"
    sentinel = tmp_path / "subject-selected-ssh.sh"
    sentinel.write_text(
        "#!/bin/sh\n"
        f"printf executed > {shlex.quote(str(marker))}\n"
        "exit 1\n",
        encoding="utf-8",
        newline="\n",
    )
    sentinel.chmod(0o755)
    git_run(control, "config", "--local", "remote.origin.promisor", "true")
    git_run(
        control,
        "config",
        "--local",
        "remote.origin.partialCloneFilter",
        "blob:none",
    )
    git_run(control, "config", "--local", "core.sshCommand", str(sentinel))
    git_run(control, "config", "--local", "remote.origin.url", "ssh://example.invalid/repo")

    blob = (
        git_run(control, "rev-parse", f"HEAD:{module.PRODUCER_SOURCE_PATH}")
        .stdout.decode("ascii", errors="strict")
        .strip()
    )
    loose_object = control / ".git" / "objects" / blob[:2] / blob[2:]
    assert loose_object.exists(), "fixture requires the committed loader as a loose object"
    loose_object.unlink()

    result = run_tool(
        *carrier_cli_arguments(
            tool_module=module,
            staging_root=staging,
            control_root=control,
            revision=revision,
        ),
        isolated=True,
        tool=tool_path,
        cwd=control,
        timeout=240,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    diagnostic = parse_json_bytes(result.stderr)
    assert diagnostic["authority_effect"] == "none"
    assert diagnostic["exit_kind"] == "trusted_git_error"
    assert any(
        "control_plane_git_local_only_config_rejected" in item
        for item in diagnostic["errors"]
    )
    assert not marker.exists()


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
