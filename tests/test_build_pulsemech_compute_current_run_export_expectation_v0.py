#!/usr/bin/env python3
from __future__ import annotations

import copy
import gc
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import textwrap
import weakref
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = (
    ROOT
    / "tools"
    / "build_pulsemech_compute_current_run_export_expectation_v0.py"
)
TOOLS_TESTS_MANIFEST = ROOT / "ci" / "tools-tests.list"
TEST_RELATIVE_PATH = (
    "tests/test_build_pulsemech_compute_current_run_export_expectation_v0.py"
)

EXPECTED_TOOL_LINES = 4306
EXPECTED_TOOL_BYTES = 144793
EXPECTED_TOOL_SHA256 = (
    "56893caab8f5198a5e4d64dc55638f2d7365ed1660b85514eabc7461cc15b767"
)
EXPECTED_TOOL_GIT_BLOB_SHA1 = "f7b22613c759d32d5de0b30c7e86989a0c85bb10"


EXPECTED_UNPARAMETERIZED_TESTS = frozenset(
    {
        "test_builder_artifact_identity_matches_reviewed_merge",
        "test_validation_dependencies_are_not_imported_at_module_load",
        "test_tools_tests_manifest_registers_builder_regression_exactly_once",
        "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract",
        "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit",
        "test_direct_nonisolated_execution_fails_before_argument_parsing",
        "test_poisoned_pythonpath_cannot_execute_validation_modules",
        "test_isolated_help_exposes_the_complete_protected_cli_surface",
        "test_nonisolated_dependency_initialization_fails_closed",
        "test_isolated_dependency_initialization_uses_interpreter_roots",
        "test_isolated_dependency_initialization_rejects_preloaded_module",
        "test_canonical_json_and_strict_json_fail_closed",
        "test_trusted_current_run_binding_is_exact_and_dimension_preserving",
        "test_release_target_projection_stays_separate_from_workflow_sets",
        "test_observed_artifact_time_order_accepts_equality_and_rejects_inversion",
        "test_external_signer_policy_path_is_canonical_and_unique",
        "test_generated_expectation_preserves_closed_non_authority_boundary",
        "test_git_subprocess_profile_forces_local_only_object_access",
        "test_trusted_git_capability_probe_fails_closed_without_no_lazy_fetch",
        "test_git_local_only_config_capture_is_hard_bounded_before_parse",
        "test_git_local_only_preflight_rejects_promisor_pack_marker",
        "test_missing_promisor_object_cannot_execute_repository_ssh_command",
        "test_verified_tree_parser_and_final_mode_rejection",
        "test_rehashed_git_object_identity_rejects_substituted_payload",
        "test_independent_git_storage_rejects_shared_store",
        "test_output_boundary_rejects_case_aliases_and_repository_paths",
        "test_arbitrary_authority_payloads_are_not_retained_aggregately",
        "test_failure_diagnostic_is_canonical_and_non_authoritative",
        "test_authoritative_trusted_git_selection_continues_to_capable_candidate",
        "test_authoritative_trusted_git_prerequisite_fails_instead_of_skipping",
        "test_complete_synthetic_current_run_cli_is_deterministic",
    }
)
EXPECTED_PARAMETERIZED_TEST_CASES: dict[
    str,
    dict[str, dict[str, str]],
] = {
    "test_repository_paths_reject_noncanonical_forms": {
        "empty": {"value": ""},
        "absolute-path": {"value": "/absolute/path"},
        "windows-separator": {"value": "relative\\windows"},
        "parent-traversal": {"value": "relative/../escape"},
        "dot-component": {"value": "relative/./alias"},
        "trailing-slash": {"value": "relative/trailing/"},
        "single-dot": {"value": "."},
        "double-dot": {"value": ".."},
    },
    "test_git_local_only_preflight_rejects_remote_object_boundary_config": {
        "local-extensions-partial-clone": {
            "scope": "local",
            "key": "extensions.partialClone",
            "value": "origin",
        },
        "local-remote-promisor": {
            "scope": "local",
            "key": "remote.origin.promisor",
            "value": "true",
        },
        "local-remote-partial-clone-filter": {
            "scope": "local",
            "key": "remote.origin.partialCloneFilter",
            "value": "blob:none",
        },
        "local-core-ssh-command": {
            "scope": "local",
            "key": "core.sshCommand",
            "value": "/tmp/subject-selected-ssh",
        },
        "worktree-core-ssh-command": {
            "scope": "worktree",
            "key": "core.sshCommand",
            "value": "/tmp/worktree-selected-ssh",
        },
    },
}


def _expected_collected_item_parameters() -> dict[str, dict[str, str]]:
    expected = {name: {} for name in EXPECTED_UNPARAMETERIZED_TESTS}
    for function_name, cases in EXPECTED_PARAMETERIZED_TEST_CASES.items():
        for case_id, parameters in cases.items():
            expected[f"{function_name}[{case_id}]"] = dict(parameters)
    return expected


EXPECTED_COLLECTED_ITEM_PARAMETERS = _expected_collected_item_parameters()
EXPECTED_COLLECTED_TEST_ITEMS = len(EXPECTED_COLLECTED_ITEM_PARAMETERS)
EXPECTED_COLLECTED_TEST_FUNCTIONS = frozenset(
    EXPECTED_UNPARAMETERIZED_TESTS
    | frozenset(EXPECTED_PARAMETERIZED_TEST_CASES)
)
CRITICAL_REAL_GIT_ITEMS = frozenset(
    {
        "test_git_local_only_preflight_rejects_remote_object_boundary_config"
        "[local-extensions-partial-clone]",
        "test_git_local_only_preflight_rejects_remote_object_boundary_config"
        "[local-remote-promisor]",
        "test_git_local_only_preflight_rejects_remote_object_boundary_config"
        "[local-remote-partial-clone-filter]",
        "test_git_local_only_preflight_rejects_remote_object_boundary_config"
        "[local-core-ssh-command]",
        "test_git_local_only_preflight_rejects_remote_object_boundary_config"
        "[worktree-core-ssh-command]",
        "test_git_local_only_config_capture_is_hard_bounded_before_parse",
        "test_git_local_only_preflight_rejects_promisor_pack_marker",
        "test_missing_promisor_object_cannot_execute_repository_ssh_command",
        "test_complete_synthetic_current_run_cli_is_deterministic",
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


def import_tool_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pulsemech_current_run_export_expectation_builder_v0_under_test",
        TOOL,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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


def run_tool(
    *arguments: str,
    isolated: bool,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    command = [sys.executable]
    if isolated:
        command.append("-I")
    command.extend([str(TOOL), *arguments])
    environment = dict(os.environ)
    if extra_env:
        environment.update(extra_env)
    return subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
    )


def builder_error_text(error: BaseException) -> str:
    return str(error)



def _collected_test_name(item: Any) -> str:
    original_name = getattr(item, "originalname", None)
    if isinstance(original_name, str) and original_name:
        return original_name
    return str(item.name).split("[", 1)[0]


def _collected_item_parameters(item: Any) -> dict[str, Any]:
    callspec = getattr(item, "callspec", None)
    if callspec is None:
        return {}
    return dict(callspec.params)


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

        observed: dict[str, dict[str, Any]] = {}
        duplicate_item_names: list[str] = []
        for item in collected:
            item_name = str(item.name)
            if item_name in observed:
                duplicate_item_names.append(item_name)
                continue
            observed[item_name] = _collected_item_parameters(item)

        expected = EXPECTED_COLLECTED_ITEM_PARAMETERS
        missing = sorted(set(expected) - set(observed))
        unexpected = sorted(set(observed) - set(expected))
        parameter_mismatches = {
            name: {
                "expected": expected[name],
                "observed": observed[name],
            }
            for name in sorted(set(expected) & set(observed))
            if observed[name] != expected[name]
        }
        observed_function_names = {
            _collected_test_name(item) for item in collected
        }
        missing_functions = sorted(
            EXPECTED_COLLECTED_TEST_FUNCTIONS - observed_function_names
        )
        unexpected_functions = sorted(
            observed_function_names - EXPECTED_COLLECTED_TEST_FUNCTIONS
        )

        if (
            len(collected) != EXPECTED_COLLECTED_TEST_ITEMS
            or duplicate_item_names
            or missing
            or unexpected
            or parameter_mismatches
            or missing_functions
            or unexpected_functions
        ):
            raise pytest.UsageError(
                "authoritative_regression_collection_contract_mismatch: "
                + json.dumps(
                    {
                        "duplicate_item_names": sorted(duplicate_item_names),
                        "expected_items": EXPECTED_COLLECTED_TEST_ITEMS,
                        "missing_functions": missing_functions,
                        "missing_items": missing,
                        "observed_items": len(collected),
                        "parameter_mismatches": parameter_mismatches,
                        "unexpected_functions": unexpected_functions,
                        "unexpected_items": unexpected,
                    },
                    sort_keys=True,
                )
            )

        missing_critical = sorted(CRITICAL_REAL_GIT_ITEMS - set(observed))
        if missing_critical:
            raise pytest.UsageError(
                "authoritative_regression_critical_items_missing: "
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

        terminal = session.config.pluginmanager.get_plugin(
            "terminalreporter"
        )
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
                "authoritative regression execution contract failed",
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
    "PULSEMECH_AUTHORITATIVE_REGRESSION_LAUNCH_PROBE_CHILD"
)


def _run_authoritative_regression() -> int:
    previous_environment = {
        key: os.environ.get(key)
        for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
    }
    os.environ.pop("PYTEST_ADDOPTS", None)
    os.environ.pop("PYTEST_PLUGINS", None)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    contract = _AuthoritativeRegressionContract()
    try:
        result = pytest.main(
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
        "authoritative_regression_session_contract_not_completed: "
        + json.dumps(contract.completion_state, sort_keys=True)
        + "\n"
    )
    return int(pytest.ExitCode.TESTS_FAILED)


# ---------------------------------------------------------------------------
# Reviewed artifact identity and repository-native registration
# ---------------------------------------------------------------------------


def test_builder_artifact_identity_matches_reviewed_merge() -> None:
    payload = TOOL.read_bytes()
    assert len(payload.splitlines()) == EXPECTED_TOOL_LINES
    assert len(payload) == EXPECTED_TOOL_BYTES
    assert sha256_bytes(payload) == EXPECTED_TOOL_SHA256
    assert git_blob_sha1(payload) == EXPECTED_TOOL_GIT_BLOB_SHA1
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")

    assert TOOL_MODULE.TOOL_NAME == (
        "build_pulsemech_compute_current_run_export_expectation_v0"
    )
    assert TOOL_MODULE.TOOL_VERSION == "0.1.0"
    assert TOOL_MODULE.SCHEMA_VERSION == (
        "pulsemech_compute_current_run_export_expectation_v0"
    )
    assert TOOL_MODULE.DOCUMENT_TYPE == (
        "pulsemech_compute_current_run_export_expectation"
    )
    assert TOOL_MODULE.EXPECTATION_BUILDER_PATH == (
        "tools/build_pulsemech_compute_current_run_export_expectation_v0.py"
    )


def test_validation_dependencies_are_not_imported_at_module_load() -> None:
    assert TOOL_MODULE.jsonschema is None
    assert TOOL_MODULE.yaml is None
    assert TOOL_MODULE._StrictSafeLoader is None

    payload = TOOL.read_text(encoding="utf-8")
    bootstrap = payload.split("import argparse", 1)[0]
    assert "import jsonschema" not in bootstrap
    assert "import yaml" not in bootstrap
    assert "isolated_python_runtime_required: launch with python -I" in bootstrap


def test_tools_tests_manifest_registers_builder_regression_exactly_once() -> None:
    entries = manifest_entries()
    assert len(entries) == len(set(entries))
    assert entries.count(TEST_RELATIVE_PATH) == 1
    index = entries.index(TEST_RELATIVE_PATH)
    assert entries[index - 1] == (
        "tests/test_check_pulsemech_compute_current_run_export_expectation_v0.py"
    )
    assert entries[index + 1] == (
        "tests/test_load_pulsemech_compute_current_run_export_carrier_v0.py"
    )
    assert entries[index + 2] == (
        "tests/test_build_pulsemech_compute_subject_input_packet_current_run_v0.py"
    )
    assert entries[index + 3] == (
        "tests/test_pulsemech_compute_current_run_export_candidate_workflow_v0.py"
    )
    assert entries[index + 4] == (
        "tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
    )
    assert entries[index + 5] == (
        "tests/test_build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"
    )
    assert entries[index + 6] == (
        "tests/test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py"
    )
    assert entries[index + 7] == (
        "tests/test_pulsemech_compute_subject_input_packet_schema_v0.py"
    )


def test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inherited = {
        "PYTEST_ADDOPTS": "--help",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
        "PYTEST_PLUGINS": "subject_selected_plugin",
    }
    for key, value in inherited.items():
        monkeypatch.setenv(key, value)

    observed: dict[str, Any] = {}

    def successful_main(
        arguments: list[str],
        *,
        plugins: list[Any],
    ) -> pytest.ExitCode:
        observed["arguments"] = list(arguments)
        observed["plugins"] = list(plugins)
        observed["environment"] = {
            key: os.environ.get(key)
            for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
        }
        contract = plugins[0]
        assert isinstance(contract, _AuthoritativeRegressionContract)
        contract._collection_validated = True
        contract._session_finished = True
        contract._contract_satisfied = True
        return pytest.ExitCode.OK

    monkeypatch.setattr(pytest, "main", successful_main)
    assert _run_authoritative_regression() == int(pytest.ExitCode.OK)
    assert observed["arguments"] == [
        "-o",
        "addopts=",
        "--noconftest",
        str(Path(__file__).resolve()),
    ]
    assert len(observed["plugins"]) == 1
    assert observed["environment"] == {
        "PYTEST_ADDOPTS": None,
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_PLUGINS": None,
    }
    assert {
        key: os.environ.get(key)
        for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
    } == inherited

    def successful_early_exit(
        _arguments: list[str],
        *,
        plugins: list[Any],
    ) -> pytest.ExitCode:
        assert len(plugins) == 1
        return pytest.ExitCode.OK

    monkeypatch.setattr(pytest, "main", successful_early_exit)
    assert _run_authoritative_regression() == int(
        pytest.ExitCode.TESTS_FAILED
    )
    assert (
        "authoritative_regression_session_contract_not_completed"
        in capsys.readouterr().err
    )

    def nonzero_main(
        _arguments: list[str],
        *,
        plugins: list[Any],
    ) -> pytest.ExitCode:
        assert len(plugins) == 1
        return pytest.ExitCode.USAGE_ERROR

    monkeypatch.setattr(pytest, "main", nonzero_main)
    assert _run_authoritative_regression() == int(pytest.ExitCode.USAGE_ERROR)




# ---------------------------------------------------------------------------
# Direct execution and isolated Python dependency boundary
# ---------------------------------------------------------------------------


def test_direct_nonisolated_execution_fails_before_argument_parsing() -> None:
    first = run_tool("--help", isolated=False)
    second = run_tool("--help", isolated=False)

    assert first.returncode == second.returncode == 2
    assert first.stdout == second.stdout == b""
    assert first.stderr == second.stderr
    diagnostic = parse_json_bytes(first.stderr)
    assert diagnostic == {
        "authority_effect": "none",
        "document_type": (
            "pulsemech_compute_current_run_export_expectation"
        ),
        "errors": [
            "isolated_python_runtime_required: launch with python -I"
        ],
        "exit_kind": "python_runtime_boundary_error",
        "ok": False,
        "schema_version": (
            "pulsemech_compute_current_run_export_expectation_v0"
        ),
        "tool": (
            "build_pulsemech_compute_current_run_export_expectation_v0"
        ),
        "tool_version": "0.1.0",
    }
    assert first.stderr == TOOL_MODULE._ISOLATED_PYTHON_REQUIRED_DIAGNOSTIC.encode("utf-8")


def test_poisoned_pythonpath_cannot_execute_validation_modules(
    tmp_path: Path,
) -> None:
    poison = tmp_path / "poison"
    poison.mkdir()
    marker = tmp_path / "executed.txt"
    payload = (
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
    )
    (poison / "jsonschema.py").write_text(payload, encoding="utf-8")
    (poison / "yaml.py").write_text(payload, encoding="utf-8")

    result = run_tool(
        "--help",
        isolated=False,
        extra_env={"PYTHONPATH": str(poison)},
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert "isolated_python_runtime_required" in result.stderr.decode("utf-8")
    assert not marker.exists()


def test_isolated_help_exposes_the_complete_protected_cli_surface() -> None:
    result = run_tool("--help", isolated=True)
    assert result.returncode == 0
    assert result.stderr == b""
    help_text = result.stdout.decode("utf-8", errors="strict")
    for option in (
        "--input",
        "--subject-root",
        "--subject-repository",
        "--subject-revision",
        "--workflow-name",
        "--workflow-path",
        "--workflow-run-id",
        "--workflow-run-number",
        "--workflow-run-attempt",
        "--source-ref",
        "--event-name",
        "--release-candidate-id",
        "--run-mode",
        "--release-target",
        "--active-policy-set",
        "--expectation-created-utc",
        "--ci-workflow-or-job-identity",
        "--control-plane-root",
        "--control-plane-repository",
        "--control-plane-revision",
        "--trusted-git",
        "--final-status",
        "--release-decision",
        "--materialized-gate-set",
        "--output",
    ):
        assert option in help_text


def test_nonisolated_dependency_initialization_fails_closed(
    tmp_path: Path,
) -> None:
    subject = tmp_path / "subject"
    control = tmp_path / "control"
    subject.mkdir()
    control.mkdir()

    with pytest.raises(TOOL_MODULE.BuilderError) as captured:
        TOOL_MODULE._initialize_validation_dependencies(
            subject_root=subject,
            control_plane_root=control,
        )
    assert (
        "isolated_python_runtime_required: launch with python -I"
        in builder_error_text(captured.value)
    )
    assert captured.value.exit_kind == "python_runtime_boundary_error"
    assert captured.value.exit_code == 2


def test_isolated_dependency_initialization_uses_interpreter_roots(
    tmp_path: Path,
) -> None:
    subject = tmp_path / "subject"
    control = tmp_path / "control"
    subject.mkdir()
    control.mkdir()
    probe = tmp_path / "probe.py"
    probe.write_text(
        textwrap.dedent(
            """
            import importlib.util
            import json
            import sys
            from pathlib import Path

            tool = Path(sys.argv[1])
            subject = Path(sys.argv[2])
            control = Path(sys.argv[3])
            spec = importlib.util.spec_from_file_location(
                "isolated_builder_probe",
                tool,
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            module._initialize_validation_dependencies(
                subject_root=subject,
                control_plane_root=control,
            )
            print(
                json.dumps(
                    {
                        "isolated": sys.flags.isolated,
                        "ignore_environment": sys.flags.ignore_environment,
                        "no_user_site": sys.flags.no_user_site,
                        "safe_path": bool(
                            getattr(sys.flags, "safe_path", False)
                        ),
                        "jsonschema": module.jsonschema.__file__,
                        "yaml": module.yaml.__file__,
                    },
                    sort_keys=True,
                )
            )
            """
        ).lstrip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(probe),
            str(TOOL),
            str(subject),
            str(control),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode(
        "utf-8",
        errors="replace",
    )
    assert result.stderr == b""
    observed = parse_json_bytes(result.stdout)
    assert observed["isolated"] == 1
    assert observed["ignore_environment"] == 1
    assert observed["no_user_site"] == 1
    assert observed["safe_path"] is True
    for key in ("jsonschema", "yaml"):
        origin = Path(observed[key]).resolve(strict=True)
        assert origin.is_file()
        assert subject not in origin.parents
        assert control not in origin.parents


def test_isolated_dependency_initialization_rejects_preloaded_module(
    tmp_path: Path,
) -> None:
    subject = tmp_path / "subject"
    control = tmp_path / "control"
    subject.mkdir()
    control.mkdir()
    probe = tmp_path / "preloaded_probe.py"
    probe.write_text(
        textwrap.dedent(
            """
            import importlib.util
            import sys
            import types
            from pathlib import Path

            tool = Path(sys.argv[1])
            subject = Path(sys.argv[2])
            control = Path(sys.argv[3])
            spec = importlib.util.spec_from_file_location(
                "isolated_builder_preload_probe",
                tool,
            )
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            sys.modules["jsonschema"] = types.ModuleType("jsonschema")
            try:
                module._initialize_validation_dependencies(
                    subject_root=subject,
                    control_plane_root=control,
                )
            except module.BuilderError as exc:
                print(str(exc))
                raise SystemExit(exc.exit_code)
            raise SystemExit(0)
            """
        ).lstrip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(probe),
            str(TOOL),
            str(subject),
            str(control),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 2
    assert result.stderr == b""
    assert (
        b"validation_dependency_preloaded_before_protected_import"
        in result.stdout
    )


# ---------------------------------------------------------------------------
# Canonical inputs, fixed run identity, and closed authority boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/absolute/path",
        "relative\\windows",
        "relative/../escape",
        "relative/./alias",
        "relative/trailing/",
        ".",
        "..",
    ],
    ids=[
        "empty",
        "absolute-path",
        "windows-separator",
        "parent-traversal",
        "dot-component",
        "trailing-slash",
        "single-dot",
        "double-dot",
    ],
)
def test_repository_paths_reject_noncanonical_forms(value: str) -> None:
    assert TOOL_MODULE._canonical_repository_path(value) is None


def test_canonical_json_and_strict_json_fail_closed() -> None:
    value = {"z": 1, "a": {"β": True}}
    rendered = TOOL_MODULE.render_json(value)
    assert rendered == (
        '{\n'
        '  "a": {\n'
        '    "β": true\n'
        '  },\n'
        '  "z": 1\n'
        '}\n'
    ).encode("utf-8")
    assert TOOL_MODULE.parse_json_bytes(rendered, label="probe") == value

    with pytest.raises(TOOL_MODULE.BuilderError, match="duplicate JSON key"):
        TOOL_MODULE.parse_json_bytes(
            b'{"a":1,"a":2}\n',
            label="probe",
        )
    with pytest.raises(TOOL_MODULE.BuilderError, match="utf8_bom_not_permitted"):
        TOOL_MODULE.parse_json_bytes(
            b"\xef\xbb\xbf{}\n",
            label="probe",
        )
    with pytest.raises(TOOL_MODULE.BuilderError, match="non-finite JSON value"):
        TOOL_MODULE.parse_json_bytes(
            b'{"value":NaN}\n',
            label="probe",
        )


def canonical_subject() -> dict[str, Any]:
    repository = "HKati/pulse-release-gates-0.1"
    workflow_name = "PULSE CI"
    workflow_path = ".github/workflows/pulse_ci.yml"
    source_ref = "refs/heads/main"
    return {
        "repository": repository,
        "source_commit": "a" * 40,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "workflow_run_id": 1001,
        "workflow_run_number": 2002,
        "workflow_run_attempt": 1,
        "subject_run_key": (
            "GITHUB_RUN_ID=1001|GITHUB_RUN_ATTEMPT=1|"
            "GITHUB_WORKFLOW=PULSE CI"
        ),
        "workflow_ref": (
            f"{repository}/{workflow_path}@{source_ref}"
        ),
        "source_ref": source_ref,
        "event_name": "workflow_dispatch",
        "release_candidate_id": "candidate:regression",
        "run_mode": "core",
        "active_policy_sets": ["core_required"],
    }


def test_trusted_current_run_binding_is_exact_and_dimension_preserving() -> None:
    subject = canonical_subject()
    TOOL_MODULE._verify_trusted_current_run_binding(
        subject=subject,
        subject_repository=subject["repository"],
        subject_revision=subject["source_commit"],
        workflow_name=subject["workflow_name"],
        workflow_path=subject["workflow_path"],
        workflow_run_id=subject["workflow_run_id"],
        workflow_run_number=subject["workflow_run_number"],
        workflow_run_attempt=subject["workflow_run_attempt"],
        source_ref=subject["source_ref"],
        event_name=subject["event_name"],
        release_candidate_id=subject["release_candidate_id"],
        run_mode=subject["run_mode"],
        active_policy_sets=subject["active_policy_sets"],
    )

    modified = copy.deepcopy(subject)
    modified["active_policy_sets"] = ["required"]
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="trusted_current_run_active_policy_sets_mismatch",
    ):
        TOOL_MODULE._verify_trusted_current_run_binding(
            subject=modified,
            subject_repository=subject["repository"],
            subject_revision=subject["source_commit"],
            workflow_name=subject["workflow_name"],
            workflow_path=subject["workflow_path"],
            workflow_run_id=subject["workflow_run_id"],
            workflow_run_number=subject["workflow_run_number"],
            workflow_run_attempt=subject["workflow_run_attempt"],
            source_ref=subject["source_ref"],
            event_name=subject["event_name"],
            release_candidate_id=subject["release_candidate_id"],
            run_mode=subject["run_mode"],
            active_policy_sets=subject["active_policy_sets"],
        )


def test_release_target_projection_stays_separate_from_workflow_sets() -> None:
    policy = {
        "gates": {
            "core_required": ["core_gate"],
            "required": ["required_gate"],
            "release_required": ["release_gate"],
        }
    }
    final_status = {
        "gates": {
            "core_gate": True,
            "required_gate": True,
            "release_gate": True,
            "detectors_materialized_ok": True,
        }
    }
    status_validation = {
        "errors": [],
        "mode": "validated",
        "ok": True,
        "schema_path": TOOL_MODULE.STATUS_SCHEMA_PATH,
    }

    stage = TOOL_MODULE._derive_release_decision_projection(
        final_status=final_status,
        policy=policy,
        target="stage",
        status_schema_validation=status_validation,
    )
    prod = TOOL_MODULE._derive_release_decision_projection(
        final_status=final_status,
        policy=policy,
        target="prod",
        status_schema_validation=status_validation,
    )

    assert stage["active_gate_sets"] == ["required"]
    assert stage["effective_required_gates"] == ["required_gate"]
    assert stage["release_level"] == "STAGE-PASS"
    assert prod["active_gate_sets"] == ["required", "release_required"]
    assert prod["effective_required_gates"] == [
        "required_gate",
        "release_gate",
    ]
    assert prod["release_level"] == "PROD-PASS"


def test_observed_artifact_time_order_accepts_equality_and_rejects_inversion() -> None:
    first = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
    second = datetime(2026, 8, 15, 12, 1, tzinfo=timezone.utc)
    third = datetime(2026, 8, 15, 12, 2, tzinfo=timezone.utc)

    TOOL_MODULE._verify_observed_artifact_time_order(
        release_decision_created_utc=first,
        carrier_finalized_utc=second,
        expectation_created_utc=third,
    )
    TOOL_MODULE._verify_observed_artifact_time_order(
        release_decision_created_utc=first,
        carrier_finalized_utc=first,
        expectation_created_utc=first,
    )

    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="release_decision_created_after_carrier_finalization",
    ):
        TOOL_MODULE._verify_observed_artifact_time_order(
            release_decision_created_utc=second,
            carrier_finalized_utc=first,
            expectation_created_utc=third,
        )
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="carrier_finalized_after_expectation_creation",
    ):
        TOOL_MODULE._verify_observed_artifact_time_order(
            release_decision_created_utc=first,
            carrier_finalized_utc=third,
            expectation_created_utc=second,
        )


def signer_source(
    *,
    source_id: str,
    path: str,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "role": "external_signer_policy",
        "path_or_uri": path,
    }


def test_external_signer_policy_path_is_canonical_and_unique() -> None:
    canonical = TOOL_MODULE.EXTERNAL_SIGNER_POLICY_PATH
    assert TOOL_MODULE._external_signer_policy_source_path(
        {
            "additional_sources": [
                signer_source(
                    source_id="source:signer",
                    path=canonical,
                )
            ]
        }
    ) == canonical

    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="external_signer_policy_source_missing",
    ):
        TOOL_MODULE._external_signer_policy_source_path(
            {"additional_sources": []}
        )
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="external_signer_policy_source_ambiguous",
    ):
        TOOL_MODULE._external_signer_policy_source_path(
            {
                "additional_sources": [
                    signer_source(
                        source_id="source:one",
                        path=canonical,
                    ),
                    signer_source(
                        source_id="source:two",
                        path=canonical,
                    ),
                ]
            }
        )
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="external_signer_policy_source_path_mismatch",
    ):
        TOOL_MODULE._external_signer_policy_source_path(
            {
                "additional_sources": [
                    signer_source(
                        source_id="source:alternate",
                        path="policy/alternate_signers.yml",
                    )
                ]
            }
        )


def test_generated_expectation_preserves_closed_non_authority_boundary() -> None:
    subject = canonical_subject()
    builder_input = {
        "archive_layout": {"layout_id": "layout:regression"},
        "authority_sources": {"workflow": {"source_id": "source:workflow"}},
        "carrier": {
            "carrier_kind": "current_run_export_archive",
            "finalized_utc": "2026-08-15T12:01:00Z",
        },
        "packet_producer_profile": {
            "expected_repository": subject["repository"],
        },
        "subject": subject,
    }
    components = {
        "expectation_builder": {
            "path": TOOL_MODULE.EXPECTATION_BUILDER_PATH,
            "sha256": EXPECTED_TOOL_SHA256,
            "source_revision": "b" * 40,
            "version": "0.1.0",
        }
    }

    expectation = TOOL_MODULE.build_expectation(
        builder_input=builder_input,
        control_plane_repository=subject["repository"],
        control_plane_revision="b" * 40,
        components=components,
        authority_sources=builder_input["authority_sources"],
        expectation_created_utc="2026-08-15T12:02:00Z",
        ci_workflow_or_job_identity="PULSE CI / regression",
    )

    assert expectation["ok"] is True
    assert expectation["record_status"] == "observed"
    assert expectation["authority_boundary"] == (
        TOOL_MODULE.CLOSED_AUTHORITY_BOUNDARY
    )
    assert expectation["content_boundary"] == (
        TOOL_MODULE.CLOSED_CONTENT_BOUNDARY
    )
    assert expectation["authority_boundary"]["activates_compute_gate"] is False
    assert (
        expectation["authority_boundary"]["changes_release_authority"]
        is False
    )
    assert (
        expectation["authority_boundary"]["expectation_is_release_authority"]
        is False
    )
    assert expectation["authority_boundary"]["writes_subject_run"] is False
    assert (
        expectation["authority_boundary"]["writes_target_repository"]
        is False
    )
    assert expectation["expectation_producer"]["producer_source_sha256"] == (
        EXPECTED_TOOL_SHA256
    )

    expectation["subject"]["repository"] = "mutated"
    assert builder_input["subject"]["repository"] != "mutated"


# ---------------------------------------------------------------------------
# Git object identity, independent storage, and output non-interference
# ---------------------------------------------------------------------------


def test_git_subprocess_profile_forces_local_only_object_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> Any:
        captured["command"] = list(command)
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=b"ok\n",
            stderr=b"",
        )

    monkeypatch.setattr(TOOL_MODULE.subprocess, "run", fake_run)
    observed = TOOL_MODULE._run_git(
        git_path=Path("/usr/bin/git"),
        repository_root=ROOT,
        arguments=("rev-parse", "HEAD"),
        label="probe",
    )

    assert observed == b"ok\n"
    command = captured["command"]
    assert "--no-lazy-fetch" in command
    command_config = {
        command[index + 1]
        for index, value in enumerate(command[:-1])
        if value == "-c"
    }
    assert "core.fsmonitor=false" in command_config
    assert "core.sshCommand=/bin/false" in command_config
    assert "credential.helper=" in command_config
    assert "credential.interactive=false" in command_config
    assert "protocol.allow=never" in command_config
    assert "protocol.file.allow=never" in command_config
    assert "protocol.ssh.allow=never" in command_config

    environment = captured["kwargs"]["env"]
    assert environment["GIT_ALLOW_PROTOCOL"] == ""
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert environment["GIT_PROTOCOL_FROM_USER"] == "0"
    assert environment["GIT_SSH_COMMAND"] == "/bin/false"
    assert environment["GIT_ASKPASS"] == "/bin/false"
    assert environment["SSH_ASKPASS"] == "/bin/false"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


def test_trusted_git_capability_probe_fails_closed_without_no_lazy_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(command: list[str], **_kwargs: Any) -> Any:
        return subprocess.CompletedProcess(
            command,
            129,
            stdout=b"",
            stderr=b"unknown option: --no-lazy-fetch\n",
        )

    monkeypatch.setattr(TOOL_MODULE.subprocess, "run", fake_run)
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="trusted_git_no_lazy_fetch_unsupported",
    ):
        TOOL_MODULE._require_trusted_git_local_only_support(
            Path("/usr/bin/git")
        )


@pytest.mark.parametrize(
    ("scope", "key", "value"),
    [
        ("local", "extensions.partialClone", "origin"),
        ("local", "remote.origin.promisor", "true"),
        ("local", "remote.origin.partialCloneFilter", "blob:none"),
        ("local", "core.sshCommand", "/tmp/subject-selected-ssh"),
        ("worktree", "core.sshCommand", "/tmp/worktree-selected-ssh"),
    ],
    ids=[
        "local-extensions-partial-clone",
        "local-remote-promisor",
        "local-remote-partial-clone-filter",
        "local-core-ssh-command",
        "worktree-core-ssh-command",
    ],
)
def test_git_local_only_preflight_rejects_remote_object_boundary_config(
    tmp_path: Path,
    scope: str,
    key: str,
    value: str,
) -> None:
    repository = tmp_path / "repository"
    initialize_git_repository(repository, {"tracked.txt": b"tracked\n"})

    if key.casefold() == "extensions.partialclone":
        git_run(repository, "config", "core.repositoryFormatVersion", "1")
        git_run(
            repository,
            "config",
            "remote.origin.url",
            "ssh://example.invalid/repository",
        )
    if scope == "worktree":
        git_run(repository, "config", "core.repositoryFormatVersion", "1")
        git_run(repository, "config", "extensions.worktreeConfig", "true")
        git_run(repository, "config", "--worktree", key, value)
    else:
        git_run(repository, "config", "--local", key, value)

    object_store = (repository / ".git" / "objects").resolve(strict=True)
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="git_local_only_config_rejected",
    ):
        TOOL_MODULE._verify_git_local_only_repository_state(
            git_path=trusted_git_path(),
            repository_root=repository,
            object_store=object_store,
            label="probe",
        )


def test_git_local_only_config_capture_is_hard_bounded_before_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    initialize_git_repository(repository, {"tracked.txt": b"tracked\n"})
    config_path = repository / ".git" / "config"
    with config_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write('\n[pulse "oversized"]\n')
        stream.write("payload = ")
        stream.write(
            "x"
            * (
                TOOL_MODULE.MAX_GIT_CONFIG_BYTES
                + TOOL_MODULE.GIT_CAPTURE_CHUNK_BYTES
            )
        )
        stream.write("\n")

    def parser_must_not_run(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("oversized Git config reached the parser")

    monkeypatch.setattr(
        TOOL_MODULE,
        "_parse_scoped_git_config",
        parser_must_not_run,
    )
    object_store = (repository / ".git" / "objects").resolve(strict=True)
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="git_stdout_capture_limit_exceeded",
    ) as captured:
        TOOL_MODULE._verify_git_local_only_repository_state(
            git_path=trusted_git_path(),
            repository_root=repository,
            object_store=object_store,
            label="probe",
        )

    message = builder_error_text(captured.value)
    assert f"maximum={TOOL_MODULE.MAX_GIT_CONFIG_BYTES}" in message
    assert "observed_at_least=" in message


def test_git_local_only_preflight_rejects_promisor_pack_marker(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    initialize_git_repository(repository, {"tracked.txt": b"tracked\n"})
    object_store = (repository / ".git" / "objects").resolve(strict=True)
    pack_directory = object_store / "pack"
    pack_directory.mkdir(exist_ok=True)
    (pack_directory / "pack-synthetic.promisor").write_bytes(b"")

    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="git_promisor_pack_marker_rejected",
    ):
        TOOL_MODULE._verify_git_local_only_repository_state(
            git_path=trusted_git_path(),
            repository_root=repository,
            object_store=object_store,
            label="probe",
        )


def test_missing_promisor_object_cannot_execute_repository_ssh_command(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    partial = tmp_path / "partial"
    marker = tmp_path / "transport-command-executed.txt"
    sentinel = tmp_path / "subject-selected-ssh.sh"

    initialize_git_repository(
        source,
        {"promised.bin": b"PULSEmech promised object regression\n"},
    )
    git_run(source, "config", "uploadpack.allowFilter", "true")
    git_run(source, "config", "uploadpack.allowAnySHA1InWant", "true")
    git_run(
        tmp_path,
        "clone",
        "-q",
        "--no-local",
        "--no-checkout",
        "--filter=blob:none",
        source.as_uri(),
        str(partial),
    )
    promised_blob = git_run(source, "rev-parse", "HEAD:promised.bin")

    local_probe = subprocess.run(
        [
            str(trusted_git_path()),
            "--no-lazy-fetch",
            "-C",
            str(partial),
            "cat-file",
            "-e",
            promised_blob,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin",
        },
    )
    assert local_probe.returncode != 0

    sentinel.write_text(
        "#!/bin/sh\n"
        f"printf executed > {shlex.quote(str(marker))}\n"
        "exit 1\n",
        encoding="utf-8",
        newline="\n",
    )
    sentinel.chmod(0o755)
    git_run(
        partial,
        "config",
        "remote.origin.url",
        "ssh://example.invalid/repository",
    )
    git_run(partial, "config", "core.sshCommand", str(sentinel))

    vulnerable = subprocess.run(
        [
            str(trusted_git_path()),
            "-C",
            str(partial),
            "cat-file",
            "blob",
            promised_blob,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
        env={
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin",
        },
    )
    assert vulnerable.returncode != 0
    assert marker.read_text(encoding="utf-8") == "executed"
    marker.unlink()

    with pytest.raises(TOOL_MODULE.BuilderError, match="git_failed"):
        TOOL_MODULE._run_git(
            git_path=trusted_git_path(),
            repository_root=partial,
            arguments=("cat-file", "blob", promised_blob),
            label="promisor_probe",
        )
    assert not marker.exists()


def test_verified_tree_parser_and_final_mode_rejection() -> None:
    object_id = "ab" * 20
    entry = (
        b"100644 file.txt\x00"
        + bytes.fromhex(object_id)
    )
    parsed = TOOL_MODULE._parse_verified_git_tree_entries(
        entry,
        label="probe",
    )
    assert parsed == {b"file.txt": ("100644", object_id)}

    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="tree_entry_name_duplicate",
    ):
        TOOL_MODULE._parse_verified_git_tree_entries(
            entry + entry,
            label="probe",
        )

    root_tree_id = "cd" * 20
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="final_path_not_regular_blob",
    ):
        TOOL_MODULE._resolve_verified_git_blob_id(
            git_path=Path("/usr/bin/git"),
            repository_root=ROOT,
            root_tree_id=root_tree_id,
            repository_path="link",
            label="probe",
            object_cache={},
            tree_cache={
                root_tree_id: {
                    b"link": ("120000", object_id),
                }
            },
        )


def test_rehashed_git_object_identity_rejects_substituted_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_id = "0" * 40

    def fake_run_git(
        *,
        arguments: tuple[str, ...],
        input_payload: bytes | None = None,
        **_kwargs: Any,
    ) -> bytes:
        if arguments == ("cat-file", "-t", expected_id):
            return b"blob\n"
        if arguments == ("cat-file", "-s", expected_id):
            return b"4\n"
        if arguments == ("cat-file", "blob", expected_id):
            return b"evil"
        if arguments == ("hash-object", "-t", "blob", "--stdin"):
            assert input_payload == b"evil"
            return (b"1" * 40) + b"\n"
        raise AssertionError(arguments)

    monkeypatch.setattr(TOOL_MODULE, "_run_git", fake_run_git)
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="object_id_mismatch",
    ):
        TOOL_MODULE._verified_git_object_payload(
            git_path=Path("/usr/bin/git"),
            repository_root=ROOT,
            object_id=expected_id,
            expected_type="blob",
            label="probe",
            max_bytes=1024,
            object_cache={},
        )


def test_independent_git_storage_rejects_shared_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    subject_common = tmp_path / "subject-common"
    subject_objects = subject_common / "objects"
    control_common = tmp_path / "control-common"
    control_objects = control_common / "objects"
    for path in (
        subject_common,
        subject_objects,
        control_common,
        control_objects,
    ):
        path.mkdir(parents=True, exist_ok=True)

    def separated_identity(
        *,
        label: str,
        **_kwargs: Any,
    ) -> tuple[Path, Path]:
        if label == "subject":
            return subject_common, subject_objects
        return control_common, control_objects

    monkeypatch.setattr(
        TOOL_MODULE,
        "_git_storage_identity",
        separated_identity,
    )
    TOOL_MODULE._verify_independent_git_storage(
        git_path=Path("/usr/bin/git"),
        subject_root=tmp_path / "subject",
        control_plane_root=tmp_path / "control",
    )

    def shared_identity(
        *,
        label: str,
        **_kwargs: Any,
    ) -> tuple[Path, Path]:
        if label == "subject":
            return subject_common, subject_objects
        return subject_common, subject_objects

    monkeypatch.setattr(
        TOOL_MODULE,
        "_git_storage_identity",
        shared_identity,
    )
    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="git_storage_must_be_independent",
    ):
        TOOL_MODULE._verify_independent_git_storage(
            git_path=Path("/usr/bin/git"),
            subject_root=tmp_path / "subject",
            control_plane_root=tmp_path / "control",
        )


def test_output_boundary_rejects_case_aliases_and_repository_paths(
    tmp_path: Path,
) -> None:
    subject_root = tmp_path / "subject"
    control_root = tmp_path / "control"
    external_root = tmp_path / "external"
    for path in (subject_root, control_root, external_root):
        path.mkdir()

    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="output_name_protected",
    ):
        TOOL_MODULE._reject_unsafe_output(
            external_root / "RELEASE_AUTHORITY_V0.JSON",
            protected_paths=(),
            protected_roots=(subject_root, control_root),
        )

    with pytest.raises(
        TOOL_MODULE.BuilderError,
        match="output_inside_protected_repository",
    ):
        TOOL_MODULE._reject_unsafe_output(
            subject_root / "generated.json",
            protected_paths=(),
            protected_roots=(subject_root, control_root),
        )

    TOOL_MODULE._reject_unsafe_output(
        external_root / "generated-expectation.json",
        protected_paths=(),
        protected_roots=(subject_root, control_root),
    )


# ---------------------------------------------------------------------------
# Bounded authority-source retention without aggregate payload accumulation
# ---------------------------------------------------------------------------


class SyntheticPayload:
    __slots__ = ("path", "__weakref__")

    def __init__(self, path: str) -> None:
        self.path = path

    def __len__(self) -> int:
        return 1024 * 1024


def synthetic_payload_sha(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


def source_record(
    *,
    source_id: str,
    path: str,
    revision: str,
    role: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source_id": source_id,
        "path_or_uri": path,
        "source_revision": revision,
        "sha256": synthetic_payload_sha(path),
        "size_bytes": 1024 * 1024,
    }
    if role is not None:
        row["role"] = role
    row.update(extra)
    return row


def test_arbitrary_authority_payloads_are_not_retained_aggregately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = "a" * 40
    workflow_name = "PULSE CI"
    workflow_path = ".github/workflows/pulse_ci.yml"
    workflow_ref = (
        "HKati/pulse-release-gates-0.1/"
        ".github/workflows/pulse_ci.yml@refs/heads/main"
    )
    unique_additional_paths = [
        f"evidence/source-{index:03d}.bin"
        for index in range(128)
    ]
    repeated_path = unique_additional_paths[0]

    authority_sources = {
        "workflow": source_record(
            source_id="source:workflow",
            path=workflow_path,
            revision=revision,
            workflow_name=workflow_name,
            workflow_ref=workflow_ref,
        ),
        "policy": source_record(
            source_id="source:policy",
            path=TOOL_MODULE.POLICY_PATH,
            revision=revision,
            policy_id="policy:regression",
        ),
        "gate_registry": source_record(
            source_id="source:registry",
            path=TOOL_MODULE.GATE_REGISTRY_PATH,
            revision=revision,
            registry_id="registry:regression",
        ),
        "additional_sources": [
            source_record(
                source_id=f"source:additional:{index:03d}",
                path=path,
                revision=revision,
                role="evidence",
            )
            for index, path in enumerate(unique_additional_paths)
        ]
        + [
            source_record(
                source_id="source:additional:repeat",
                path=repeated_path,
                revision=revision,
                role="evidence",
            )
        ],
    }

    live: weakref.WeakSet[SyntheticPayload] = weakref.WeakSet()
    peak_live = 0
    verification_calls: list[str] = []

    def fake_verify(
        *,
        repository_path: str,
        **_kwargs: Any,
    ) -> SyntheticPayload:
        nonlocal peak_live
        gc.collect()
        payload = SyntheticPayload(repository_path)
        live.add(payload)
        peak_live = max(peak_live, len(live))
        verification_calls.append(repository_path)
        return payload

    def fake_sha256(payload: SyntheticPayload) -> str:
        return synthetic_payload_sha(payload.path)

    def fake_yaml(
        payload: SyntheticPayload,
        *,
        label: str,
    ) -> dict[str, Any]:
        if label == "verified_workflow":
            return {"name": workflow_name}
        if label == "verified_gate_registry":
            return {"version": "registry:regression"}
        raise AssertionError((label, payload.path))

    monkeypatch.setattr(
        TOOL_MODULE,
        "_verify_committed_worktree_file",
        fake_verify,
    )
    monkeypatch.setattr(TOOL_MODULE, "sha256_bytes", fake_sha256)
    monkeypatch.setattr(TOOL_MODULE, "parse_yaml_object", fake_yaml)

    _verified, retained = TOOL_MODULE._verify_authority_sources(
        git_path=Path("/usr/bin/git"),
        subject_root=ROOT,
        subject_revision=revision,
        authority_sources=authority_sources,
        trusted_workflow_name=workflow_name,
        trusted_workflow_path=workflow_path,
        trusted_workflow_ref=workflow_ref,
    )

    assert set(retained) == {"workflow", "policy", "gate_registry"}
    assert all(isinstance(value, SyntheticPayload) for value in retained.values())
    assert verification_calls.count(repeated_path) == 1
    assert len(verification_calls) == 3 + len(unique_additional_paths)

    # Three intentionally retained payloads plus at most the previous and
    # current arbitrary payload may be live while the next source is verified.
    # A cache of every distinct arbitrary payload would grow with source count.
    assert peak_live <= 5


def test_failure_diagnostic_is_canonical_and_non_authoritative() -> None:
    diagnostic = TOOL_MODULE.make_failure_diagnostic(
        error="synthetic",
        exit_kind="regression",
    )
    assert diagnostic["ok"] is False
    assert diagnostic["authority_effect"] == "none"
    assert diagnostic["errors"] == ["synthetic"]
    rendered = TOOL_MODULE.render_json(diagnostic)
    assert rendered.endswith(b"\n")
    assert b"\r\n" not in rendered
    assert parse_json_bytes(rendered) == diagnostic


# ---------------------------------------------------------------------------
# Complete synthetic current-run CLI construction
# ---------------------------------------------------------------------------


def trusted_git_path() -> Path:
    failures: list[dict[str, str]] = []
    for supplied_candidate in TOOL_MODULE._trusted_git_candidates():
        try:
            candidate = TOOL_MODULE._validated_trusted_git(
                supplied_candidate
            )
            TOOL_MODULE._require_trusted_git_local_only_support(candidate)
        except TOOL_MODULE.BuilderError as exc:
            failures.append(
                {
                    "candidate": str(supplied_candidate),
                    "error": str(exc),
                }
            )
            continue
        return candidate

    pytest.fail(
        "authoritative protected Git prerequisite unavailable: "
        + json.dumps(failures, sort_keys=True),
        pytrace=False,
    )


def test_authoritative_trusted_git_selection_continues_to_capable_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = Path("/usr/bin/git")
    second = Path("/usr/local/bin/git")
    attempted: list[Path] = []

    monkeypatch.setattr(
        TOOL_MODULE,
        "_trusted_git_candidates",
        lambda: (first, second),
    )
    monkeypatch.setattr(
        TOOL_MODULE,
        "_validated_trusted_git",
        lambda candidate: candidate,
    )

    def require_capability(candidate: Path) -> None:
        attempted.append(candidate)
        if candidate == first:
            raise TOOL_MODULE.BuilderError(
                "trusted_git_no_lazy_fetch_unsupported: synthetic old Git",
                exit_kind="trusted_git_error",
                exit_code=2,
            )

    monkeypatch.setattr(
        TOOL_MODULE,
        "_require_trusted_git_local_only_support",
        require_capability,
    )

    assert trusted_git_path() == second
    assert attempted == [first, second]


def test_authoritative_trusted_git_prerequisite_fails_instead_of_skipping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = Path("/usr/bin/git")
    second = Path("/usr/local/bin/git")

    monkeypatch.setattr(
        TOOL_MODULE,
        "_trusted_git_candidates",
        lambda: (first, second),
    )
    monkeypatch.setattr(
        TOOL_MODULE,
        "_validated_trusted_git",
        lambda candidate: candidate,
    )

    def unsupported(candidate: Path) -> None:
        raise TOOL_MODULE.BuilderError(
            f"trusted_git_no_lazy_fetch_unsupported: {candidate}",
            exit_kind="trusted_git_error",
            exit_code=2,
        )

    monkeypatch.setattr(
        TOOL_MODULE,
        "_require_trusted_git_local_only_support",
        unsupported,
    )
    with pytest.raises(
        pytest.fail.Exception,
        match="authoritative protected Git prerequisite unavailable",
    ) as captured:
        trusted_git_path()

    detail = str(captured.value)
    assert str(first) in detail
    assert str(second) in detail


def git_run(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        [str(trusted_git_path()), *arguments],
        cwd=repository,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env={
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin",
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def initialize_git_repository(
    repository: Path,
    files: dict[str, bytes],
) -> str:
    repository.mkdir()
    git_run(repository, "init", "-q")
    for relative, payload in files.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    git_run(repository, "add", "--", ".")
    git_run(
        repository,
        "-c",
        "user.name=PULSEmech builder regression",
        "-c",
        "user.email=pulsemech-builder@example.invalid",
        "commit",
        "-q",
        "-m",
        "synthetic protected state",
    )
    revision = git_run(repository, "rev-parse", "HEAD")
    assert len(revision) == 40
    return revision


def minimal_validator_source() -> bytes:
    return textwrap.dedent(
        """
        from __future__ import annotations

        import hashlib
        import json
        from pathlib import Path
        from typing import Any

        TOOL_NAME = "check_pulsemech_compute_current_run_export_expectation_v0"
        TOOL_VERSION = "0.1.0"
        SCHEMA_VERSION = "pulsemech_compute_current_run_export_expectation_v0"
        DOCUMENT_TYPE = "pulsemech_compute_current_run_export_expectation"

        ROOT = Path(__file__).resolve().parents[1]
        DEFAULT_SCHEMA = (
            ROOT
            / "schemas"
            / "pulsemech_compute_current_run_export_expectation_v0.schema.json"
        )
        DEFAULT_SUBJECT_INPUT_SCHEMA = (
            ROOT
            / "schemas"
            / "pulsemech_compute_subject_input_packet_v0.schema.json"
        )

        def render_json(value: Any) -> str:
            return (
                json.dumps(
                    value,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                    allow_nan=False,
                )
                + "\\n"
            )

        def schema_reference_policy_errors(
            _schema: Any,
            *,
            label: str,
        ) -> list[str]:
            assert label
            return []

        def validate_instance(
            _schema: Any,
            _instance: Any,
            *,
            label: str,
        ) -> tuple[bool, list[str]]:
            assert label
            return True, []

        def semantic_checks(
            _expectation: Any,
            **_kwargs: Any,
        ) -> tuple[dict[str, bool], list[str], dict[str, Any]]:
            return {"synthetic_contract_ok": True}, [], {}

        def build_diagnostic(
            *,
            schema_path: Path,
            expectation_path: Path,
            subject_input_schema_path: Path,
            repository_root: Path,
        ) -> tuple[dict[str, Any], int]:
            assert schema_path
            assert subject_input_schema_path
            assert repository_root
            payload = expectation_path.read_bytes()
            return (
                {
                    "authority_effect": "none",
                    "input_identities": {
                        "expectation": {
                            "sha256": hashlib.sha256(payload).hexdigest(),
                            "size_bytes": len(payload),
                        }
                    },
                    "ok": True,
                    "record_status": "observed",
                    "verification_boundary": {
                        "canonical_contract_semantics_verified": True,
                        "contract_semantics_verified": True,
                    },
                },
                0,
            )

        def atomic_write(path: Path, text: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\\n")
        """
    ).lstrip().encode("utf-8")


def permissive_expectation_schema() -> dict[str, Any]:
    object_schema = {"type": "object"}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": {
            "archive_layout": object_schema,
            "authority_sources": object_schema,
            "carrier": object_schema,
            "carrier_producer": object_schema,
            "packet_producer_profile": object_schema,
            "subject": object_schema,
        },
        "type": "object",
    }


def test_complete_synthetic_current_run_cli_is_deterministic(
    tmp_path: Path,
) -> None:
    control_root = tmp_path / "control-plane"
    subject_root = tmp_path / "subject"
    output = tmp_path / "generated" / "expectation.json"

    schema_bytes = TOOL_MODULE.render_json(permissive_expectation_schema())
    subject_schema_bytes = TOOL_MODULE.render_json(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
        }
    )
    validator_bytes = minimal_validator_source()
    carrier_loader_bytes = b"#!/usr/bin/env python3\n# synthetic carrier loader\n"

    control_files = {
        TOOL_MODULE.EXPECTATION_BUILDER_PATH: TOOL.read_bytes(),
        TOOL_MODULE.EXPECTATION_SCHEMA_PATH: schema_bytes,
        TOOL_MODULE.EXPECTATION_VALIDATOR_PATH: validator_bytes,
        TOOL_MODULE.SUBJECT_INPUT_SCHEMA_PATH: subject_schema_bytes,
        TOOL_MODULE.CURRENT_RUN_CARRIER_LOADER_PATH: carrier_loader_bytes,
        TOOL_MODULE.CONTROL_PLANE_WORKFLOW_PATH: (
            b"name: Synthetic current-run control plane\n"
        ),
        TOOL_MODULE.SUBJECT_INPUT_PRODUCER_CORE_PATH: (
            b"#!/usr/bin/env python3\n# synthetic producer core\n"
        ),
        TOOL_MODULE.SUBJECT_INPUT_PRODUCER_WRAPPER_PATH: (
            b"#!/usr/bin/env python3\n# synthetic producer wrapper\n"
        ),
        TOOL_MODULE.SUBJECT_INPUT_VALIDATOR_PATH: (
            b"#!/usr/bin/env python3\n# synthetic subject validator\n"
        ),
    }
    control_revision = initialize_git_repository(
        control_root,
        control_files,
    )

    workflow_name = "PULSE CI"
    workflow_path = ".github/workflows/pulse_ci.yml"
    workflow_bytes = (
        b"name: PULSE CI\n"
        b"on:\n"
        b"  workflow_dispatch:\n"
    )
    policy_bytes = (
        b"policy:\n"
        b"  id: policy:synthetic\n"
        b"  version: 0.1.0\n"
        b"gates:\n"
        b"  core_required:\n"
        b"    - required_gate\n"
        b"  required:\n"
        b"    - required_gate\n"
        b"  release_required:\n"
        b"    - release_gate\n"
    )
    registry_bytes = b"version: registry:synthetic\n"
    signer_policy_bytes = b"version: synthetic\n"
    simple_schema_bytes = TOOL_MODULE.render_json(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
        }
    )

    subject_files = {
        workflow_path: workflow_bytes,
        TOOL_MODULE.POLICY_PATH: policy_bytes,
        TOOL_MODULE.GATE_REGISTRY_PATH: registry_bytes,
        TOOL_MODULE.EXTERNAL_SIGNER_POLICY_PATH: signer_policy_bytes,
        TOOL_MODULE.STATUS_SCHEMA_PATH: simple_schema_bytes,
        TOOL_MODULE.RELEASE_DECISION_SCHEMA_PATH: simple_schema_bytes,
    }
    subject_revision = initialize_git_repository(
        subject_root,
        subject_files,
    )

    repository = "HKati/pulse-release-gates-0.1"
    source_ref = "refs/heads/main"
    run_id = 1001
    run_number = 2002
    run_attempt = 1
    subject_run_key = (
        "GITHUB_RUN_ID=1001|GITHUB_RUN_ATTEMPT=1|"
        "GITHUB_WORKFLOW=PULSE CI"
    )
    workflow_ref = f"{repository}/{workflow_path}@{source_ref}"
    policy_sha = sha256_bytes(policy_bytes)
    registry_sha = sha256_bytes(registry_bytes)

    final_status = {
        "created_utc": "2026-08-15T11:59:00Z",
        "gates": {
            "detectors_materialized_ok": True,
            "required_gate": True,
            "release_gate": True,
        },
        "metrics": {
            "gate_policy_sha256": policy_sha,
            "gate_registry_sha256": registry_sha,
            "git_sha": subject_revision,
            "run_key": subject_run_key,
            "run_mode": "core",
        },
        "version": "synthetic",
    }
    final_status_bytes = TOOL_MODULE.render_json(final_status)
    final_status_sha = sha256_bytes(final_status_bytes)
    status_validation = {
        "errors": [],
        "mode": "validated",
        "ok": True,
        "schema_path": TOOL_MODULE.STATUS_SCHEMA_PATH,
    }
    projection = TOOL_MODULE._derive_release_decision_projection(
        final_status=final_status,
        policy={
            "gates": {
                "core_required": ["required_gate"],
                "required": ["required_gate"],
                "release_required": ["release_gate"],
            }
        },
        target="stage",
        status_schema_validation=status_validation,
    )
    assert projection["release_level"] == "STAGE-PASS"

    release_decision = {
        "created_utc": "2026-08-15T12:00:00Z",
        "git_sha": subject_revision,
        "policy_path": TOOL_MODULE.POLICY_PATH,
        "policy_sha256": policy_sha,
        "producer": {
            "name": TOOL_MODULE.RELEASE_DECISION_PRODUCER_NAME,
            "version": TOOL_MODULE.RELEASE_DECISION_VERSION,
        },
        "run_mode": "core",
        "schema": TOOL_MODULE.RELEASE_DECISION_SCHEMA,
        "status_path": "status.json",
        "status_sha256": final_status_sha,
        "target": "stage",
        "version": TOOL_MODULE.RELEASE_DECISION_VERSION,
        **projection,
    }
    release_decision_bytes = TOOL_MODULE.render_json(release_decision)
    release_decision_sha = sha256_bytes(release_decision_bytes)

    def authority_row(
        *,
        source_id: str,
        path: str,
        payload: bytes,
        **extra: Any,
    ) -> dict[str, Any]:
        return {
            "path_or_uri": path,
            "sha256": sha256_bytes(payload),
            "size_bytes": len(payload),
            "source_id": source_id,
            "source_revision": subject_revision,
            **extra,
        }

    authority_sources = {
        "workflow": authority_row(
            source_id="source:workflow",
            path=workflow_path,
            payload=workflow_bytes,
            workflow_name=workflow_name,
            workflow_ref=workflow_ref,
        ),
        "policy": authority_row(
            source_id="source:policy",
            path=TOOL_MODULE.POLICY_PATH,
            payload=policy_bytes,
            policy_id="policy:synthetic",
        ),
        "gate_registry": authority_row(
            source_id="source:registry",
            path=TOOL_MODULE.GATE_REGISTRY_PATH,
            payload=registry_bytes,
            registry_id="registry:synthetic",
        ),
        "additional_sources": [
            authority_row(
                source_id="source:external-signer-policy",
                path=TOOL_MODULE.EXTERNAL_SIGNER_POLICY_PATH,
                payload=signer_policy_bytes,
                role="external_signer_policy",
            )
        ],
    }

    subject = {
        "active_policy_sets": ["core_required"],
        "decision": "ALLOW",
        "event_name": "workflow_dispatch",
        "final_status_sha256": final_status_sha,
        "materialized_gate_set_sha256": None,
        "policy_id": "policy:synthetic",
        "policy_sha256": policy_sha,
        "release_candidate_id": "candidate:synthetic",
        "release_decision_sha256": release_decision_sha,
        "repository": repository,
        "run_mode": "core",
        "source_commit": subject_revision,
        "source_ref": source_ref,
        "subject_run_key": subject_run_key,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "workflow_ref": workflow_ref,
        "workflow_run_attempt": run_attempt,
        "workflow_run_id": run_id,
        "workflow_run_number": run_number,
    }
    loader_sha = sha256_bytes(carrier_loader_bytes)
    builder_input = {
        "archive_layout": {"layout_id": "layout:synthetic"},
        "authority_sources": authority_sources,
        "carrier": {
            "carrier_kind": "current_run_export_archive",
            "finalized_utc": "2026-08-15T12:01:00Z",
            "producer": {
                "producer_run_key": subject_run_key,
                "producer_source": (
                    TOOL_MODULE.CURRENT_RUN_CARRIER_LOADER_PATH
                ),
                "producer_source_revision": control_revision,
                "producer_source_sha256": loader_sha,
                "producer_version": "0.1.0",
                "production_mode": (
                    "current_run_export_carrier_builder"
                ),
            },
        },
        "packet_producer_profile": {
            "expected_archive_layout_id": "layout:synthetic",
            "expected_producer_source_path": (
                TOOL_MODULE.SUBJECT_INPUT_PRODUCER_WRAPPER_PATH
            ),
            "expected_repository": repository,
            "expected_signer_policy_path": (
                TOOL_MODULE.EXTERNAL_SIGNER_POLICY_PATH
            ),
            "expected_source_commit": subject_revision,
            "expected_subject_run_key": subject_run_key,
        },
        "subject": subject,
    }

    final_status_path = subject_root / "status.json"
    release_decision_path = subject_root / "release_decision_v0.json"
    input_path = subject_root / "builder-input.json"
    final_status_path.write_bytes(final_status_bytes)
    release_decision_path.write_bytes(release_decision_bytes)
    input_path.write_bytes(TOOL_MODULE.render_json(builder_input))

    command = [
        sys.executable,
        "-I",
        str(
            control_root
            / TOOL_MODULE.EXPECTATION_BUILDER_PATH
        ),
        "--input",
        str(input_path),
        "--expectation-schema",
        str(control_root / TOOL_MODULE.EXPECTATION_SCHEMA_PATH),
        "--expectation-validator",
        str(control_root / TOOL_MODULE.EXPECTATION_VALIDATOR_PATH),
        "--subject-input-schema",
        str(control_root / TOOL_MODULE.SUBJECT_INPUT_SCHEMA_PATH),
        "--subject-root",
        str(subject_root),
        "--subject-repository",
        repository,
        "--subject-revision",
        subject_revision,
        "--workflow-name",
        workflow_name,
        "--workflow-path",
        workflow_path,
        "--workflow-run-id",
        str(run_id),
        "--workflow-run-number",
        str(run_number),
        "--workflow-run-attempt",
        str(run_attempt),
        "--source-ref",
        source_ref,
        "--event-name",
        "workflow_dispatch",
        "--release-candidate-id",
        "candidate:synthetic",
        "--run-mode",
        "core",
        "--release-target",
        "stage",
        "--active-policy-set",
        "core_required",
        "--expectation-created-utc",
        "2026-08-15T12:02:00Z",
        "--ci-workflow-or-job-identity",
        "PULSE CI / synthetic builder regression",
        "--control-plane-root",
        str(control_root),
        "--control-plane-repository",
        repository,
        "--control-plane-revision",
        control_revision,
        "--trusted-git",
        str(trusted_git_path()),
        "--final-status",
        str(final_status_path),
        "--release-decision",
        str(release_decision_path),
    ]

    first = subprocess.run(
        [*command, "--output", str(output)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    second = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert first.returncode == second.returncode == 0, (
        first.stderr + second.stderr
    ).decode("utf-8", errors="replace")
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    assert output.read_bytes() == first.stdout
    expectation = parse_json_bytes(first.stdout)
    assert first.stdout == TOOL_MODULE.render_json(expectation)
    assert expectation["ok"] is True
    assert expectation["record_status"] == "observed"
    assert expectation["subject"]["source_commit"] == subject_revision
    assert expectation["trusted_control_plane"]["revision"] == (
        control_revision
    )
    assert expectation["expectation_producer"]["producer_source_sha256"] == (
        EXPECTED_TOOL_SHA256
    )
    assert (
        expectation["packet_producer_profile"]["expected_signer_policy_path"]
        == TOOL_MODULE.EXTERNAL_SIGNER_POLICY_PATH
    )
    assert expectation["authority_boundary"]["activates_compute_gate"] is False
    assert (
        expectation["authority_boundary"]["changes_release_authority"]
        is False
    )

    # Full-CLI fail-closed proof: oversized repository-local configuration is
    # terminated at the hard capture boundary before config parsing continues.
    subject_config_path = subject_root / ".git" / "config"
    original_subject_config = subject_config_path.read_bytes()
    with subject_config_path.open(
        "a",
        encoding="utf-8",
        newline="\n",
    ) as stream:
        stream.write('\n[pulse "oversized"]\n')
        stream.write("payload = ")
        stream.write(
            "x"
            * (
                TOOL_MODULE.MAX_GIT_CONFIG_BYTES
                + TOOL_MODULE.GIT_CAPTURE_CHUNK_BYTES
            )
        )
        stream.write("\n")

    oversized = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert oversized.returncode == 2
    assert oversized.stdout == b""
    oversized_diagnostic = parse_json_bytes(oversized.stderr)
    assert oversized_diagnostic["ok"] is False
    assert oversized_diagnostic["authority_effect"] == "none"
    assert oversized_diagnostic["exit_kind"] == "trusted_git_error"
    assert any(
        "subject_git_config_git_stdout_capture_limit_exceeded" in error
        for error in oversized_diagnostic["errors"]
    )
    subject_config_path.write_bytes(original_subject_config)

    # Full-CLI fail-closed proof: repository-local promisor/transport state is
    # rejected before any object read can invoke the configured transport.
    marker = tmp_path / "full-cli-transport-command-executed.txt"
    sentinel = tmp_path / "full-cli-subject-selected-ssh.sh"
    sentinel.write_text(
        "#!/bin/sh\n"
        f"printf executed > {shlex.quote(str(marker))}\n"
        "exit 1\n",
        encoding="utf-8",
        newline="\n",
    )
    sentinel.chmod(0o755)
    git_run(
        subject_root,
        "config",
        "--local",
        "remote.origin.promisor",
        "true",
    )
    git_run(
        subject_root,
        "config",
        "--local",
        "remote.origin.partialCloneFilter",
        "blob:none",
    )
    git_run(
        subject_root,
        "config",
        "--local",
        "core.sshCommand",
        str(sentinel),
    )

    blocked = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert blocked.returncode == 2
    assert blocked.stdout == b""
    blocked_diagnostic = parse_json_bytes(blocked.stderr)
    assert blocked_diagnostic["ok"] is False
    assert blocked_diagnostic["authority_effect"] == "none"
    assert blocked_diagnostic["exit_kind"] == "trusted_git_error"
    assert any(
        "subject_git_local_only_config_rejected" in error
        for error in blocked_diagnostic["errors"]
    )
    assert not marker.exists()


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
    expected_count = str(EXPECTED_COLLECTED_TEST_ITEMS).encode("ascii")
    assert b"collected " + expected_count + b" items" in result.stdout
    assert expected_count + b" passed" in result.stdout
    assert b"usage: pytest" not in result.stdout.lower()


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
