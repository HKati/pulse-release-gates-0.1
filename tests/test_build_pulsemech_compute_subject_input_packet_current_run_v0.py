#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import textwrap
import warnings
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = (
    ROOT
    / "tools"
    / "build_pulsemech_compute_subject_input_packet_current_run_v0.py"
)
CARRIER_LOADER = (
    ROOT
    / "tools"
    / "load_pulsemech_compute_current_run_export_carrier_v0.py"
)
PRODUCER_CORE = (
    ROOT / "tools" / "pulsemech_compute_subject_input_packet_producer_core_v0.py"
)
SUBJECT_VALIDATOR = (
    ROOT / "tools" / "check_pulsemech_compute_subject_input_packet_v0.py"
)
TOOLS_TESTS_MANIFEST = ROOT / "ci" / "tools-tests.list"
TEST_RELATIVE_PATH = (
    "tests/test_build_pulsemech_compute_subject_input_packet_current_run_v0.py"
)

EXPECTED_TOOL_LINES = 5038
EXPECTED_TOOL_BYTES = 180475
EXPECTED_TOOL_SHA256 = (
    "0c4eabadef598b0834665d005bcbed92c4181cff1b643356c1aa6de937987b02"
)
EXPECTED_TOOL_GIT_BLOB_SHA1 = "41d3a4ffc9b796dc674f8f2ba83141d81bc204f9"

EXPECTED_TESTS = frozenset(
    {
        "test_wrapper_artifact_identity_matches_reviewed_candidate",
        "test_tools_tests_manifest_registers_current_run_wrapper_regression_exactly_once",
        "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract",
        "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit",
        "test_direct_nonisolated_execution_fails_before_argument_parsing",
        "test_isolated_help_exposes_complete_cli_surface",
        "test_source_reuses_existing_producer_core_without_second_packet_implementation",
        "test_component_set_and_closed_boundaries_are_exact",
        "test_strict_json_canonical_values_and_time_binding_fail_closed",
        "test_expectation_header_binds_exact_subject_control_digest_and_time",
        "test_expectation_header_rejects_noncanonical_bytes_and_stale_packet_time",
        "test_git_subprocess_profile_forces_local_only_bounded_execution",
        "test_git_config_capture_is_bounded_before_parse",
        "test_git_local_only_preflight_rejects_remote_boundary_configuration",
        "test_git_local_only_preflight_rejects_promisor_alternates_and_shallow_state",
        "test_verified_repository_blob_rehashes_and_binds_worktree_bytes",
        "test_independent_git_storage_rejects_shared_store",
        "test_archive_reader_rejects_duplicate_unsafe_encrypted_and_oversized_members",
        "test_nested_archives_share_one_aggregate_uncompressed_budget",
        "test_sha256sums_inventory_and_check_reports_are_exact",
        "test_preservation_manifest_binds_current_subject_and_provider_bytes",
        "test_current_run_bundle_verifies_layout_reports_and_counts",
        "test_profile_derivation_binds_expectation_without_second_profile_implementation",
        "test_packet_equivalence_requires_exact_subject_sources_carrier_and_boundaries",
        "test_output_boundary_rejects_protected_and_overlapping_paths",
        "test_failure_diagnostic_is_canonical_and_non_authoritative",
        "test_complete_isolated_cli_uses_verified_core_is_deterministic_and_non_authoritative",
        "test_complete_cli_fails_closed_on_expectation_digest_and_carrier_mutability",
        "test_missing_candidate_workflow_remains_a_fail_closed_activation_prerequisite",
        "test_completeness_semantic_report_requires_full_package_checks",
        "test_real_producer_core_source_ids_match_canonical_projection",
        "test_real_subject_validator_routes_producer_provenance_to_control_checkout",
    }
)
EXPECTED_COLLECTED_TEST_ITEMS = len(EXPECTED_TESTS)
CRITICAL_TESTS = frozenset(
    {
        "test_wrapper_artifact_identity_matches_reviewed_candidate",
        "test_source_reuses_existing_producer_core_without_second_packet_implementation",
        "test_git_config_capture_is_bounded_before_parse",
        "test_git_local_only_preflight_rejects_remote_boundary_configuration",
        "test_verified_repository_blob_rehashes_and_binds_worktree_bytes",
        "test_current_run_bundle_verifies_layout_reports_and_counts",
        "test_nested_archives_share_one_aggregate_uncompressed_budget",
        "test_sha256sums_inventory_and_check_reports_are_exact",
        "test_complete_isolated_cli_uses_verified_core_is_deterministic_and_non_authoritative",
        "test_complete_cli_fails_closed_on_expectation_digest_and_carrier_mutability",
        "test_missing_candidate_workflow_remains_a_fail_closed_activation_prerequisite",
        "test_completeness_semantic_report_requires_full_package_checks",
        "test_real_producer_core_source_ids_match_canonical_projection",
        "test_real_subject_validator_routes_producer_provenance_to_control_checkout",
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


def render_json(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def import_tool_module(path: Path = TOOL, *, suffix: str = "repository") -> Any:
    name = f"pulsemech_current_run_subject_input_wrapper_v0_{suffix}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
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
                "authoritative_current_run_wrapper_collection_contract_mismatch: "
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
                "authoritative_current_run_wrapper_critical_items_missing: "
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
                "=", "authoritative current-run wrapper regression failed"
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
    "PULSEMECH_CURRENT_RUN_WRAPPER_REGRESSION_LAUNCH_PROBE_CHILD"
)


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


def run_tool(
    *arguments: str,
    tool: Path = TOOL,
    isolated: bool = True,
    cwd: Path = ROOT,
    extra_env: dict[str, str] | None = None,
    timeout: int = 300,
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


def trusted_git_path(module: Any = TOOL_MODULE) -> Path:
    errors: list[str] = []
    for candidate in module.LINUX_TRUSTED_GIT_EXECUTABLE_CANDIDATES:
        if not candidate.exists():
            errors.append(f"unavailable:{candidate}")
            continue
        try:
            validated = module._validated_trusted_git(candidate)
            module._require_trusted_git_local_only_support(validated)
        except module.WrapperError as exc:
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


def initialize_git_repository(
    root: Path,
    files: dict[str, bytes],
    *,
    message: str,
) -> str:
    root.mkdir(parents=True, exist_ok=True)
    git_run(root, "init", "-q")
    git_run(root, "config", "user.name", "PULSEmech Regression")
    git_run(root, "config", "user.email", "regression@example.invalid")
    for relative, payload in files.items():
        path = root / PurePosixPath(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    git_run(root, "add", ".")
    git_run(root, "commit", "-q", "-m", message)
    revision = (
        git_run(root, "rev-parse", "HEAD")
        .stdout.decode("ascii", errors="strict")
        .strip()
    )
    assert re.fullmatch(r"[0-9a-f]{40}", revision)
    return revision


def deterministic_zip(payloads: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_STORED,
        allowZip64=False,
    ) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100444 << 16
            archive.writestr(info, payloads[name])
    return buffer.getvalue()


def synthetic_expectation_validator_source() -> bytes:
    return textwrap.dedent(
        '''
        import json

        TOOL_NAME = "check_pulsemech_compute_current_run_export_expectation_v0"
        TOOL_VERSION = "0.1.0"
        SCHEMA_VERSION = "pulsemech_compute_current_run_export_expectation_v0"
        DOCUMENT_TYPE = "pulsemech_compute_current_run_export_expectation"

        def render_json(value):
            return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\\n"

        def validate_instance(_schema, _value, *, label):
            return True, []

        def semantic_checks(_value, **_kwargs):
            return {"synthetic_semantics_verified": True}, [], {}

        def build_diagnostic(**_kwargs):
            return ({
                "authority_effect": "none",
                "ok": True,
                "record_status": "observed",
            }, 0)
        '''
    ).lstrip().encode("utf-8")


def synthetic_subject_validator_source() -> bytes:
    return textwrap.dedent(
        '''
        import json
        from datetime import datetime

        TOOL_NAME = "check_pulsemech_compute_subject_input_packet_v0"
        SCHEMA_VERSION = "pulsemech_compute_subject_input_packet_v0"
        PACKET_TYPE = "pulsemech_compute_subject_input_packet"

        def load_json_bytes(data, *, label):
            return json.loads(data.decode("utf-8"))

        def load_yaml_bytes(_data, *, label):
            return {"name": "PULSE CI"}

        def parse_utc(value):
            return datetime.fromisoformat(value[:-1] + "+00:00")

        def schema_errors(_schema, _value):
            return []

        def build_diagnostic(**_kwargs):
            return ({"ok": True}, 0, None, None)
        '''
    ).lstrip().encode("utf-8")


def synthetic_producer_core_source() -> bytes:
    return textwrap.dedent(
        '''
        import hashlib
        import json
        from dataclasses import dataclass
        from pathlib import Path

        TOOL_ID = "build_pulsemech_compute_subject_input_packet_v0"
        TOOL_NAME = "PULSEmech compute subject-input packet producer"
        TOOL_VERSION = "0.1.0"
        SCHEMA_VERSION = "pulsemech_compute_subject_input_packet_v0"
        PACKET_TYPE = "pulsemech_compute_subject_input_packet"

        class BuilderError(RuntimeError):
            pass

        @dataclass(frozen=True)
        class ProducerProfile:
            profile_id: str
            producer_source_path: str
            default_carrier: Path
            production_mode: str
            packet_scope: str
            packet_identity_mode: str
            carrier_id_namespace: str
            carrier_kind: str
            carrier_media_type: str
            carrier_artifact_payload_mode: str
            expected_carrier_sha256: str
            expected_carrier_size: int
            expected_repository: str
            expected_source_commit: str
            expected_run_key: str
            outer_prefix: str
            original_prefix: str
            complete_package_name: str
            completeness_archive_name: str
            verification_archive_name: str
            expected_provider_artifact_count: int
            expected_artifact_count: int
            expected_signer_policy_path: str

        @dataclass(frozen=True)
        class PacketInputs:
            profile: ProducerProfile
            carrier_path: Path
            carrier_location: str
            carrier_bytes: bytes
            bundle: object
            artifacts: tuple
            role_bindings: dict
            documents: dict

        def validate_profile(profile):
            return profile

        def slug(value):
            return value.lower().replace(" ", "-")

        def render_json(value):
            return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\\n"

        def build_artifacts(*, carrier, bundle, validator, profile):
            context = json.loads(bundle.complete_package_members["synthetic_context.json"].decode("utf-8"))
            return (), {"context": context}

        def role_bindings(_artifacts):
            return {}

        def build_subject_and_sources(*, inputs, repository_root, validator):
            context = inputs.documents["context"]
            sources = json.loads(json.dumps(context["authority_sources"]))
            sources["workflow"]["source_id"] = "source:workflow:pulse-ci"
            sources["policy"]["source_id"] = "source:policy:pulse-gate-policy-v0"
            sources["gate_registry"]["source_id"] = "source:registry:gate-registry-v0"
            canonical = {
                ("external_signer_policy", "policy/external_signers_v1.yml"):
                    "source:policy:external-signers-v1",
                (
                    "threshold_policy",
                    "PULSE_safe_pack_v0/profiles/external_thresholds.yaml",
                ): "source:policy:external-thresholds",
            }
            for row in sources["additional_sources"]:
                row["source_id"] = canonical[(row["role"], row["path_or_uri"])]
            sources["additional_sources"].sort(key=lambda row: row["source_id"])
            return context["subject"], sources

        def producer_identity(*, repository_root, revision, source_path, execution_identity, producer_run_key, profile):
            payload = source_path.read_bytes()
            return {
                "ci_workflow_or_job_identity": execution_identity,
                "producer_id": "producer:pulsemech-current-run-subject-input-wrapper-v0",
                "producer_name": "PULSEmech current-run subject-input wrapper",
                "producer_run_key": producer_run_key,
                "producer_source": profile.producer_source_path,
                "producer_source_revision": revision,
                "producer_source_sha256": hashlib.sha256(payload).hexdigest(),
                "producer_version": "0.1.0",
                "production_mode": profile.production_mode,
            }

        def build_packet(*, inputs, subject, sources, producer, packet_created_utc):
            workflow_slug = slug(subject["workflow_name"])
            carrier_id = f"carrier:{inputs.profile.carrier_id_namespace}/{workflow_slug}-{subject['workflow_run_number']}/v0"
            return {
                "analysis_boundary": {
                    "current_repository_state_substitution_allowed": False,
                    "observer_in_subject_totals": False,
                    "packet_is_compute_report": False,
                    "packet_is_runtime_observation": False,
                    "runtime_observation_included": False,
                    "runtime_observation_required_for_runtime_classification": True,
                    "target_analysis_level": "artifact_observed",
                },
                "artifacts": [],
                "authority_boundary": {
                    "activates_compute_gate": False,
                    "changes_gate_policy": False,
                    "changes_gate_semantics": False,
                    "changes_release_authority": False,
                    "creates_compute_budget": False,
                    "creates_gate_result": False,
                    "creates_release_decision": False,
                    "mutates_carrier": False,
                    "packet_is_release_authority": False,
                    "write_mode": "subject_input_only",
                    "writes_subject_run": False,
                    "writes_target_repository": False,
                },
                "authority_sources": sources,
                "carrier": {
                    "artifact_payload_mode": "external_carrier",
                    "carrier_id": carrier_id,
                    "carrier_kind": "current_run_export_archive",
                    "immutable": True,
                    "media_type": "application/zip",
                    "path_or_uri": inputs.carrier_location,
                    "provider_binding": None,
                    "root_prefix": inputs.profile.outer_prefix.rstrip("/"),
                    "sha256": hashlib.sha256(inputs.carrier_bytes).hexdigest(),
                    "size_bytes": len(inputs.carrier_bytes),
                },
                "content_boundary": {
                    "artifact_bytes_embedded": False,
                    "carrier_required_for_verification": True,
                    "packet_payload_mode": "metadata_only",
                    "raw_model_inputs_included": False,
                    "raw_model_outputs_included": False,
                    "raw_secrets_included": False,
                },
                "coverage": {
                    "artifact_graph_complete": False,
                    "artifacts_total": 0,
                    "carrier_binding_complete": True,
                    "coverage_status": "partial",
                    "missing_roles": [],
                    "provider_artifacts_bound": 0,
                    "provider_artifacts_total": 0,
                    "role_bindings_complete": False,
                    "role_bindings_resolved": 0,
                    "role_bindings_total": 0,
                    "source_bindings_complete": True,
                    "unresolved_artifact_ids": [],
                },
                "errors": [],
                "ok": True,
                "packet_identity": {
                    "canonicalization": "json-sort-keys-utf8-newline",
                    "carrier_id": carrier_id,
                    "packet_created_utc": packet_created_utc,
                    "packet_id": "subject-input:synthetic-current-run/v0",
                    "packet_scope": "current_run",
                    "subject_run_key": subject["subject_run_key"],
                },
                "packet_type": PACKET_TYPE,
                "producer": producer,
                "record_status": "observed",
                "role_bindings": {},
                "schema_version": SCHEMA_VERSION,
                "subject": subject,
            }

        def validate_generated_packet(**kwargs):
            packet = kwargs["packet"]
            rendered = kwargs["rendered"]
            if rendered != render_json(packet):
                raise BuilderError("generated_packet_not_canonical")
        '''
    ).lstrip().encode("utf-8")


def component_bindings(
    root: Path,
    revision: str,
    files: dict[str, bytes],
) -> dict[str, dict[str, Any]]:
    versions = {
        "carrier_loader": "0.1.0",
        "control_plane_workflow": "0.1.0",
        "expectation_builder": "0.1.0",
        "expectation_schema": "0",
        "expectation_validator": "0.1.0",
        "subject_input_producer_core": "0.1.0",
        "subject_input_producer_wrapper": "0.1.0",
        "subject_input_schema": "0",
        "subject_input_validator": "0.1.0",
    }
    by_path = {path: payload for path, payload in files.items()}
    result: dict[str, dict[str, Any]] = {}
    for name, path, _version in TOOL_MODULE.CONTROL_PLANE_COMPONENT_SPECS:
        payload = by_path[path]
        assert (root / path).read_bytes() == payload
        result[name] = {
            "path": path,
            "sha256": sha256_bytes(payload),
            "source_revision": revision,
            "version": versions[name],
        }
    return result


PACKAGE_REQUIRED_FILES: tuple[str, ...] = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
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
)
PACKAGE_REQUIRED_DIRS = (
    "artifacts/recorded_release_candidates",
    "release-authority-audit-bundle",
)
PACKAGE_JSON_OBJECT_FILES = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    "artifacts/external/llamaguard_summary.json",
    "artifacts/external/llamaguard_summary.bundle.json",
    "artifacts/external/llamaguard_summary.envelope.json",
    "artifacts/external/llamaguard_attestation_verifier_v1.json",
    "artifacts/status.json",
    "artifacts/release_decision_v0.json",
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/release_authority_v0.json",
)


def authority_sources(
    subject_root: Path,
    subject_revision: str,
    files: dict[str, bytes],
) -> dict[str, Any]:
    del subject_root

    def row(
        *,
        source_id: str,
        role: str,
        path: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = files[path]
        return {
            "path_or_uri": path,
            "role": role,
            "sha256": sha256_bytes(payload),
            "size_bytes": len(payload),
            "source_id": source_id,
            "source_revision": subject_revision,
            **dict(extra or {}),
        }

    workflow_path = ".github/workflows/pulse_ci.yml"
    additional = [
        row(
            source_id="source:external-signer-policy",
            role="external_signer_policy",
            path="policy/external_signers_v1.yml",
        ),
        row(
            source_id="source:threshold-policy",
            role="threshold_policy",
            path="PULSE_safe_pack_v0/profiles/external_thresholds.yaml",
        ),
    ]
    additional.sort(key=lambda item: item["source_id"])
    return {
        "additional_sources": additional,
        "gate_registry": row(
            source_id="source:gate-registry",
            role="gate_registry",
            path="pulse_gate_registry_v0.yml",
            extra={"registry_id": "registry:synthetic"},
        ),
        "policy": row(
            source_id="source:policy",
            role="policy",
            path="pulse_gate_policy_v0.yml",
            extra={"policy_id": "policy:synthetic"},
        ),
        "workflow": row(
            source_id="source:workflow",
            role="workflow",
            path=workflow_path,
            extra={
                "workflow_name": "PULSE CI",
                "workflow_ref": (
                    "example-org/example-subject/.github/workflows/pulse_ci.yml"
                    "@refs/heads/main"
                ),
            },
        ),
    }


def inventory_check_ids(
    *,
    inventory: dict[str, Any],
    report_kind: str,
) -> set[str]:
    rows = inventory["files"]
    assert isinstance(rows, list)
    if report_kind == "completeness":
        result = {
            "digest_inventory.schema_version",
            "digest_inventory.algorithm",
            "digest_inventory.unique_paths",
            "digest_inventory.file_count",
            "digest_inventory.exact_coverage",
        }
    elif report_kind == "verification":
        result = {
            "digest_inventory.schema",
            "digest_inventory.algorithm",
            "digest_inventory.unique_paths",
            "digest_inventory.file_count",
            "digest_inventory.no_missing_files",
        }
    else:
        raise AssertionError(report_kind)
    for row in rows:
        assert isinstance(row, dict)
        path = row["path"]
        result.add(f"digest_inventory.digest:{path}")
        result.add(f"digest_inventory.size_bytes:{path}")
    return result


def completeness_check_ids(
    *,
    members: dict[str, bytes],
    inventory: dict[str, Any],
) -> set[str]:
    result: set[str] = set()
    for path in PACKAGE_REQUIRED_FILES:
        assert path in members and members[path]
        result.add(f"required_file:{path}")
        result.add(f"non_empty_file:{path}")
    for directory in PACKAGE_REQUIRED_DIRS:
        assert any(path.startswith(directory + "/") for path in members)
        result.add(f"required_dir:{directory}")
    for path in PACKAGE_JSON_OBJECT_FILES:
        assert isinstance(parse_json_bytes(members[path]), dict)
        result.add(f"json_object:{path}")
        result.add(f"non_stub_json:{path}")
    result.add("jsonl:artifacts/external/llamaguard_raw.jsonl")
    result.update(
        {
            "status.release_grade.detectors_materialized_ok",
            "status.release_grade.gates_stubbed_false",
            "status.release_grade.scaffold_false",
            "report_card.marker_state_clear",
            "report_card.non_stub",
            "recorded_candidates.non_empty",
            "slsa_vsa.trusted_producer.current_contract_optional",
        }
    )
    for path in sorted(members):
        if path.startswith("artifacts/recorded_release_candidates/") and path.endswith(".json"):
            result.add(f"recorded_candidate.json:{path}")
            result.add(f"recorded_candidate.validation:{path}")
    result.update(inventory_check_ids(inventory=inventory, report_kind="completeness"))
    return result


def verification_check_ids(
    *,
    members: dict[str, bytes],
    inventory: dict[str, Any],
    subject: dict[str, Any],
) -> set[str]:
    del subject
    result = {f"required_file:{path}" for path in PACKAGE_REQUIRED_FILES}
    result.update(f"required_dir:{path}" for path in PACKAGE_REQUIRED_DIRS)
    result.update(f"json:{path}" for path in PACKAGE_JSON_OBJECT_FILES)
    result.update(inventory_check_ids(inventory=inventory, report_kind="verification"))
    result.update(
        {
            "metadata.repository",
            "metadata.git_sha",
            "metadata.workflow_ref",
            "metadata.run_key",
            "metadata.run_id",
            "metadata.run_attempt",
            "metadata.authority_boundary",
            "llamaguard.raw.record_count",
            "llamaguard.raw[0].repository",
            "llamaguard.raw[0].git_sha",
            "llamaguard.raw[0].run_key",
            "llamaguard.raw[0].workflow_ref",
            "llamaguard.evaluator.repository",
            "llamaguard.evaluator.git_sha",
            "llamaguard.evaluator.run_key",
            "llamaguard.evaluator.workflow_ref",
            "llamaguard.summary.repository",
            "llamaguard.summary.source_commit",
            "llamaguard.summary.run_key",
            "llamaguard.envelope.repository",
            "llamaguard.envelope.source_commit",
            "llamaguard.envelope.workflow_ref",
            "llamaguard.summary.raw_path",
            "llamaguard.summary.raw_digest",
            "llamaguard.summary.evaluator_digest",
            "llamaguard.envelope.summary_digest",
            "llamaguard.envelope.bundle_uri",
            "llamaguard.envelope.bundle_sha256",
            "llamaguard.envelope.raw_evidence_sha256",
            "llamaguard.attestation_report.status",
            "llamaguard.attestation_report.errors",
            "llamaguard.attestation_report.summary_digest",
            "llamaguard.attestation_report.envelope_digest",
            "recorded_candidates.non_empty",
            "recorded_verifier.status",
            "recorded_verifier.errors",
            "input_manifest.object",
            "candidate_index.object",
            "status.git_sha",
            "status.run_key",
            "baseline.git_sha",
            "baseline.run_key",
            "release_decision.object",
            "artifact_provenance_binding.object",
            "release_authority_manifest.object",
        }
    )
    for path in sorted(members):
        if path.startswith("artifacts/recorded_release_candidates/") and path.endswith(".json"):
            result.add(f"recorded_candidate.validation:{path}")
            result.add(f"recorded_candidate.authority_boundary:{path}")
    return result


def report_checks(check_ids: set[str]) -> list[dict[str, Any]]:
    return [
        {
            "check_id": check_id,
            "details": f"independent package replay check {check_id}",
            "passed": True,
        }
        for check_id in sorted(check_ids)
    ]


def make_complete_package_members(
    *,
    subject: dict[str, Any],
    sources: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    repository = subject["repository"]
    git_sha = subject["source_commit"]
    workflow_ref = subject["workflow_ref"]
    run_key = subject["subject_run_key"]
    run_id = subject["workflow_run_id"]
    run_attempt = subject["workflow_run_attempt"]

    raw = (
        json.dumps(
            {
                "run": {
                    "git_sha": git_sha,
                    "repository": repository,
                    "run_key": run_key,
                    "workflow_ref": workflow_ref,
                }
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    evaluator = render_json(
        {
            "run": {
                "git_sha": git_sha,
                "repository": repository,
                "run_key": run_key,
                "workflow_ref": workflow_ref,
            }
        }
    )
    bundle = render_json({"bundle_format": "sigstore-bundle-v0"})
    summary = render_json(
        {
            "evidence": {
                "raw_artifact_digest": sha256_bytes(raw),
                "raw_artifact_uri": "artifacts/external/llamaguard_raw.jsonl",
            },
            "extensions": {
                "evaluator_manifest_sha256": sha256_bytes(evaluator),
                "repository": repository,
                "source_commit": git_sha,
            },
            "run": {"run_id": run_key},
        }
    )
    envelope = render_json(
        {
            "extensions": {
                "bundle_sha256": sha256_bytes(bundle),
                "raw_evidence_sha256": sha256_bytes(raw),
                "repository": repository,
                "source_commit": git_sha,
                "workflow_ref": workflow_ref,
            },
            "signing": {
                "bundle_uri": "artifacts/external/llamaguard_summary.bundle.json"
            },
            "summary_digest": {
                "algorithm": "sha256",
                "value": sha256_bytes(summary),
            },
        }
    )
    attestation = render_json(
        {
            "envelope": {"sha256": sha256_bytes(envelope)},
            "errors": [],
            "status": "verified",
            "summary": {"sha256": sha256_bytes(summary)},
        }
    )
    context = render_json(
        {
            "authority_sources": sources,
            "subject": subject,
        }
    )
    candidate_path = "artifacts/recorded_release_candidates/candidate-v0.json"
    members: dict[str, bytes] = {
        "run_metadata_v0.json": render_json(
            {
                "authority_boundary": {
                    "authorizes_release": False,
                    "package_only": True,
                },
                "git_sha": git_sha,
                "release_candidate": subject["release_candidate_id"],
                "repository": repository,
                "run_attempt": run_attempt,
                "run_id": run_id,
                "run_key": run_key,
                "workflow_ref": workflow_ref,
            }
        ),
        "artifacts/required_gate_evidence_v0.json": render_json(
            {"evidence_status": "recorded"}
        ),
        "artifacts/status_baseline.json": render_json(
            {"metrics": {"git_sha": git_sha, "run_key": run_key}}
        ),
        "artifacts/recorded_release_candidate_index_v0.json": render_json(
            {
                "index_id": "candidate-index-v0",
                "source_bindings": {
                    "external_thresholds": {
                        "path": "PULSE_safe_pack_v0/profiles/external_thresholds.yaml",
                        "sha256": sources["additional_sources"][1]["sha256"],
                    }
                },
            }
        ),
        "artifacts/release_evidence_input_manifest_v0.json": render_json(
            {"manifest_id": "release-evidence-input-v0"}
        ),
        "artifacts/recorded_release_evidence_verifier_v0.json": render_json(
            {"errors": [], "status": "verified"}
        ),
        "artifacts/external/llamaguard_raw.jsonl": raw,
        "artifacts/external/llamaguard_evaluator_manifest_v0.json": evaluator,
        "artifacts/external/llamaguard_summary.json": summary,
        "artifacts/external/llamaguard_summary.bundle.json": bundle,
        "artifacts/external/llamaguard_summary.envelope.json": envelope,
        "artifacts/external/llamaguard_attestation_verifier_v1.json": attestation,
        "artifacts/status.json": render_json(
            {
                "diagnostics": {"gates_stubbed": False, "scaffold": False},
                "gates": {"detectors_materialized_ok": True},
                "metrics": {
                    "git_sha": git_sha,
                    "run_key": run_key,
                },
            }
        ),
        "artifacts/release_decision_v0.json": render_json(
            {"decision": subject["decision"], "decision_basis": "recorded evidence"}
        ),
        "artifacts/artifact_provenance_binding_v0.json": render_json(
            {"binding_id": "artifact-provenance-v0"}
        ),
        "artifacts/release_authority_v0.json": render_json(
            {
                "authority_id": "release-authority-v0",
                "run_identity": {
                    "event_name": subject["event_name"],
                    "ref": subject["source_ref"],
                    "workflow_name": subject["workflow_name"],
                },
            }
        ),
        "artifacts/report_card.html": (
            b"<html><body>Stub/scaffold marker state clear.</body></html>\n"
        ),
        candidate_path: render_json(
            {
                "authority_boundary": {
                    "creates_release_authority": False,
                    "eligible_without_verifier": False,
                },
                "validation": {"status": "passed"},
            }
        ),
        "release-authority-audit-bundle/README.txt": b"Audit bundle recorded.\n",
        "synthetic_context.json": context,
    }
    inventory_rows = [
        {
            "path": path,
            "sha256": sha256_bytes(payload),
            "size_bytes": len(payload),
        }
        for path, payload in sorted(members.items())
    ]
    inventory = {
        "algorithm": "sha256",
        "file_count": len(inventory_rows),
        "files": inventory_rows,
        "schema_version": "release_grade_reference_package_digest_inventory_v0",
    }
    members["package_digest_inventory_v0.json"] = render_json(inventory)
    return members, inventory


def make_current_run_carrier(
    *,
    subject: dict[str, Any],
    sources: dict[str, Any],
    layout: dict[str, Any],
) -> bytes:
    complete_members, inventory = make_complete_package_members(
        subject=subject,
        sources=sources,
    )
    complete = deterministic_zip(complete_members)
    completeness_ids = completeness_check_ids(
        members=complete_members,
        inventory=inventory,
    )
    completeness_checks = report_checks(completeness_ids)
    completeness_document = render_json(
        {
            "authority_boundary": copy.deepcopy(
                TOOL_MODULE.COMPLETENESS_REPORT_AUTHORITY_BOUNDARY
            ),
            "checks": completeness_checks,
            "errors": [],
            "ok": True,
            "package": {"path": "/synthetic/complete-package"},
            "schema_version": "release_grade_package_completeness_v1",
            "status": "complete",
            "summary": {
                "checks_failed": 0,
                "checks_total": len(completeness_checks),
                "required_dirs": len(PACKAGE_REQUIRED_DIRS),
                "required_files": len(PACKAGE_REQUIRED_FILES),
            },
            "tool": copy.deepcopy(TOOL_MODULE.COMPLETENESS_REPORT_TOOL),
        }
    )
    completeness = deterministic_zip(
        {"release_grade_package_completeness_v1.json": completeness_document}
    )
    verification_ids = verification_check_ids(
        members=complete_members,
        inventory=inventory,
        subject=subject,
    )
    verification_checks = report_checks(verification_ids)
    verification_document = render_json(
        {
            "authority_boundary": copy.deepcopy(
                TOOL_MODULE.VERIFICATION_REPORT_AUTHORITY_BOUNDARY
            ),
            "checked_utc": "2026-08-19T06:25:00Z",
            "checks": verification_checks,
            "errors": [],
            "package": {"path": "/synthetic/complete-package"},
            "schema_version": "release_grade_reference_package_verification_v0",
            "status": "verified",
            "summary": {
                "checks_failed": 0,
                "checks_total": len(verification_checks),
            },
            "tool": copy.deepcopy(TOOL_MODULE.VERIFICATION_REPORT_TOOL),
            "verified": True,
        }
    )
    verification = deterministic_zip(
        {
            "release_grade_reference_package_verification_v0.json": (
                verification_document
            )
        }
    )
    provider_payloads = {
        layout["complete_package_name"]: complete,
        layout["completeness_archive_name"]: completeness,
        layout["verification_archive_name"]: verification,
    }
    roles = {
        layout["complete_package_name"]: "complete_release_grade_reference_package",
        layout["completeness_archive_name"]: "structural_package_completeness_report",
        layout["verification_archive_name"]: "independent_package_verification_report",
    }
    rows: list[dict[str, Any]] = []
    for index, name in enumerate(sorted(provider_payloads), start=1):
        payload = provider_payloads[name]
        rows.append(
            {
                "artifact_id": 1000 + index,
                "artifact_name": name,
                "created_at": "2026-08-19T06:00:00Z",
                "downloaded_sha256": sha256_bytes(payload),
                "downloaded_size_bytes": len(payload),
                "expires_at": "2026-09-19T06:00:00Z",
                "file_name": name,
                "github_digest_match": True,
                "github_sha256": sha256_bytes(payload),
                "github_size_match": True,
                "role": roles[name],
                "size_bytes": len(payload),
            }
        )
    manifest = render_json(
        {
            "active_policy_sets": subject["active_policy_sets"],
            "authority_boundary": copy.deepcopy(
                TOOL_MODULE.PRESERVATION_AUTHORITY_BOUNDARY
            ),
            "github_artifacts": rows,
            "local_verification": {
                "all_outer_artifact_digests_match_github": True,
                "all_outer_artifact_sizes_match_github": True,
                "complete_package_inventory_entries": len(inventory["files"]),
                "complete_package_zip_members": len(complete_members),
                "independent_verification_checks_total": len(verification_checks),
                "independent_verification_verified": True,
                "structural_completeness_checks_total": len(completeness_checks),
                "structural_completeness_ok": True,
            },
            "primary_gate_result": (
                "allow" if subject["decision"] == "ALLOW" else "block"
            ),
            "repository": subject["repository"],
            "run_mode": subject["run_mode"],
            "schema_id": "pulse_ci_release_grade_artifact_preservation_manifest_v0",
            "schema_version": "0.1.0",
            "source_commit": subject["source_commit"],
            "source_ref": subject["source_ref"],
            "workflow": subject["workflow_name"],
            "workflow_run_attempt": subject["workflow_run_attempt"],
            "workflow_run_id": subject["workflow_run_id"],
            "workflow_run_number": subject["workflow_run_number"],
        }
    )
    readme = b"PULSEmech current-run preservation carrier.\n"
    visible = layout["visible_members"]
    relative_original = layout["original_artifacts_prefix"][len(layout["outer_prefix"]):]
    sums = {
        visible["preservation_manifest_name"]: sha256_bytes(manifest),
        visible["preservation_readme_name"]: sha256_bytes(readme),
        **{
            relative_original + name: sha256_bytes(payload)
            for name, payload in provider_payloads.items()
        },
    }
    sums_bytes = "".join(
        f"{digest}  {path}\n" for path, digest in sorted(sums.items())
    ).encode("utf-8")
    outer = {
        layout["outer_prefix"] + visible["preservation_manifest_name"]: manifest,
        layout["outer_prefix"] + visible["preservation_readme_name"]: readme,
        layout["outer_prefix"] + visible["preservation_checksums_name"]: sums_bytes,
        **{
            layout["original_artifacts_prefix"] + name: payload
            for name, payload in provider_payloads.items()
        },
    }
    return deterministic_zip(outer)

def complete_fixture(tmp_path: Path) -> dict[str, Any]:
    control_root = tmp_path / "control-plane"
    subject_root = tmp_path / "subject"
    staging_root = tmp_path / "staging"
    external_root = tmp_path / "external"
    staging_root.mkdir(parents=True)
    external_root.mkdir(parents=True)

    control_files = {
        TOOL_MODULE.CARRIER_LOADER_SOURCE_PATH: CARRIER_LOADER.read_bytes(),
        TOOL_MODULE.CONTROL_PLANE_WORKFLOW_SOURCE_PATH: (
            b"name: PULSEmech current-run export candidate\n"
        ),
        TOOL_MODULE.EXPECTATION_BUILDER_SOURCE_PATH: (
            b"#!/usr/bin/env python3\n# synthetic expectation builder\n"
        ),
        TOOL_MODULE.EXPECTATION_SCHEMA_SOURCE_PATH: render_json(
            {"type": "object"}
        ),
        TOOL_MODULE.EXPECTATION_VALIDATOR_SOURCE_PATH: (
            synthetic_expectation_validator_source()
        ),
        TOOL_MODULE.SUBJECT_INPUT_SCHEMA_SOURCE_PATH: render_json(
            {"type": "object"}
        ),
        TOOL_MODULE.SUBJECT_INPUT_VALIDATOR_SOURCE_PATH: (
            synthetic_subject_validator_source()
        ),
        TOOL_MODULE.PRODUCER_CORE_SOURCE_PATH: synthetic_producer_core_source(),
        TOOL_MODULE.WRAPPER_SOURCE_PATH: TOOL.read_bytes(),
    }
    control_revision = initialize_git_repository(
        control_root,
        control_files,
        message="current-run wrapper control plane fixture",
    )
    components = component_bindings(
        control_root,
        control_revision,
        control_files,
    )

    subject_files = {
        ".github/workflows/pulse_ci.yml": (
            b"name: PULSE CI\non:\n  workflow_dispatch:\n"
        ),
        "policy/external_signers_v1.yml": b"version: recorded\n",
        "PULSE_safe_pack_v0/profiles/external_thresholds.yaml": (
            b"thresholds:\n  refusal_delta: 0.10\n"
        ),
        "pulse_gate_policy_v0.yml": (
            b"policy:\n  id: policy:synthetic\n"
        ),
        "pulse_gate_registry_v0.yml": b"version: registry:synthetic\n",
    }
    subject_revision = initialize_git_repository(
        subject_root,
        subject_files,
        message="current-run wrapper subject fixture",
    )
    sources = authority_sources(
        subject_root,
        subject_revision,
        subject_files,
    )

    run_id = 9001
    run_number = 17
    run_attempt = 1
    workflow_name = "PULSE CI"
    run_key = (
        f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT={run_attempt}"
        f"|GITHUB_WORKFLOW={workflow_name}"
    )
    subject = {
        "active_policy_sets": ["required", "release_required"],
        "decision": "ALLOW",
        "event_name": "workflow_dispatch",
        "final_status_sha256": "1" * 64,
        "materialized_gate_set_sha256": None,
        "policy_id": "policy:synthetic",
        "policy_sha256": sources["policy"]["sha256"],
        "release_candidate_id": "synthetic-current-run-9001-1",
        "release_decision_sha256": "2" * 64,
        "repository": "example-org/example-subject",
        "run_mode": "prod",
        "source_commit": subject_revision,
        "source_ref": "refs/heads/main",
        "subject_run_key": run_key,
        "workflow_name": workflow_name,
        "workflow_path": ".github/workflows/pulse_ci.yml",
        "workflow_ref": (
            "example-org/example-subject/.github/workflows/pulse_ci.yml"
            "@refs/heads/main"
        ),
        "workflow_run_attempt": run_attempt,
        "workflow_run_id": run_id,
        "workflow_run_number": run_number,
    }
    layout = {
        "artifact_count_derivation": "provider_plus_non_provider",
        "complete_package_name": "complete-package-9001-1.zip",
        "completeness_archive_name": "completeness-9001-1.zip",
        "expected_non_provider_artifact_count": 26,
        "expected_provider_artifact_count": 3,
        "layout_id": "pulsemech_current_run_export_layout_v0",
        "layout_version": "0.1.0",
        "original_artifacts_prefix": (
            "synthetic-current-run/original-github-artifacts/"
        ),
        "outer_prefix": "synthetic-current-run/",
        "verification_archive_name": "verification-9001-1.zip",
        "visible_members": {
            "preservation_checksums_name": "SHA256SUMS",
            "preservation_manifest_name": "PRESERVATION_MANIFEST_v0.json",
            "preservation_readme_name": "README.md",
        },
    }
    carrier_bytes = make_current_run_carrier(
        subject=subject,
        sources=sources,
        layout=layout,
    )
    staged_relative_path = "exports/current-run-9001-1.zip"
    carrier_path = staging_root / PurePosixPath(staged_relative_path)
    carrier_path.parent.mkdir(parents=True)
    carrier_path.write_bytes(carrier_bytes)
    carrier_path.chmod(0o444)
    workflow_slug = "pulse-ci"
    carrier_id = f"carrier:current-run/{workflow_slug}-{run_number}/v0"
    carrier_loader_component = components["carrier_loader"]
    carrier = {
        "artifact_payload_mode": "external_carrier",
        "carrier_id": carrier_id,
        "carrier_kind": "current_run_export_archive",
        "finalized": True,
        "finalized_utc": "2026-08-19T06:30:00Z",
        "immutable": True,
        "media_type": "application/zip",
        "path_base": "current_run_export_staging_root",
        "producer": {
            "ci_workflow_or_job_identity": (
                "PULSE CI / current-run carrier candidate"
            ),
            "producer_id": (
                "producer:pulsemech-current-run-export-carrier-loader-v0"
            ),
            "producer_name": (
                "PULSEmech current-run export carrier loader"
            ),
            "producer_run_key": run_key,
            "producer_source": TOOL_MODULE.CARRIER_LOADER_SOURCE_PATH,
            "producer_source_revision": control_revision,
            "producer_source_sha256": carrier_loader_component["sha256"],
            "producer_version": "0.1.0",
            "production_mode": "current_run_export_carrier_builder",
        },
        "provider_binding": None,
        "root_prefix": layout["outer_prefix"],
        "sha256": sha256_bytes(carrier_bytes),
        "size_bytes": len(carrier_bytes),
        "staged_relative_path": staged_relative_path,
    }
    expectation = {
        "archive_layout": layout,
        "authority_boundary": copy.deepcopy(
            TOOL_MODULE.EXPECTED_EXPECTATION_AUTHORITY_BOUNDARY
        ),
        "authority_sources": sources,
        "carrier": carrier,
        "content_boundary": copy.deepcopy(
            TOOL_MODULE.EXPECTED_EXPECTATION_CONTENT_BOUNDARY
        ),
        "document_type": (
            "pulsemech_compute_current_run_export_expectation"
        ),
        "errors": [],
        "expectation_identity": {
            "canonicalization": "json-sort-keys-utf8-newline",
            "expectation_created_utc": "2026-08-19T06:31:00Z",
            "expectation_id": (
                "current-run-export-expectation:synthetic-9001-1"
            ),
            "expectation_scope": "current_run_export",
            "subject_run_key": run_key,
        },
        "expectation_producer": {
            "ci_workflow_or_job_identity": (
                "PULSE CI / current-run expectation candidate"
            ),
            "producer_id": (
                "producer:pulsemech-current-run-export-expectation-builder-v0"
            ),
            "producer_name": (
                "PULSEmech current-run export expectation builder"
            ),
            "producer_run_key": run_key,
            "producer_source": TOOL_MODULE.EXPECTATION_BUILDER_SOURCE_PATH,
            "producer_source_revision": control_revision,
            "producer_source_sha256": components["expectation_builder"][
                "sha256"
            ],
            "producer_version": "0.1.0",
            "production_mode": "current_run_expectation_builder",
        },
        "ok": True,
        "packet_contract": copy.deepcopy(TOOL_MODULE.EXPECTED_PACKET_CONTRACT),
        "packet_producer_profile": {
            "expected_archive_layout_id": (
                "pulsemech_current_run_export_layout_v0"
            ),
            "expected_carrier_artifact_payload_mode": "external_carrier",
            "expected_carrier_id_namespace": "current-run",
            "expected_carrier_kind": "current_run_export_archive",
            "expected_carrier_media_type": "application/zip",
            "expected_packet_identity_mode": "current-run",
            "expected_packet_scope": "current_run",
            "expected_producer_source_path": TOOL_MODULE.WRAPPER_SOURCE_PATH,
            "expected_production_mode": "current_run_export",
            "expected_repository": subject["repository"],
            "expected_signer_policy_path": "policy/external_signers_v1.yml",
            "expected_source_commit": subject_revision,
            "expected_subject_run_key": run_key,
            "profile_id": "pulsemech_current_run_export_synthetic_v0",
        },
        "record_status": "observed",
        "schema_version": (
            "pulsemech_compute_current_run_export_expectation_v0"
        ),
        "subject": subject,
        "trusted_control_plane": {
            "checkout_role": "protected_control_plane",
            "components": components,
            "repository": "example-org/example-control-plane",
            "revision": control_revision,
            "separate_from_subject_checkout": True,
            "subject_may_select_revision": False,
            "trust_mode": "protected_exact_revision",
        },
    }
    expectation_path = external_root / "expectation.json"
    expectation_bytes = render_json(expectation)
    expectation_path.write_bytes(expectation_bytes)
    output_path = external_root / "subject-input.json"
    arguments = [
        "--expectation",
        str(expectation_path),
        "--expectation-sha256",
        sha256_bytes(expectation_bytes),
        "--staging-root",
        str(staging_root),
        "--subject-root",
        str(subject_root),
        "--subject-repository",
        subject["repository"],
        "--subject-revision",
        subject_revision,
        "--control-plane-root",
        str(control_root),
        "--control-plane-repository",
        "example-org/example-control-plane",
        "--control-plane-revision",
        control_revision,
        "--packet-created-utc",
        "2026-08-19T06:32:00Z",
        "--producer-run-key",
        run_key,
        "--ci-workflow-or-job-identity",
        "PULSE CI / current-run subject-input candidate",
        "--trusted-git",
        str(trusted_git_path()),
    ]
    return {
        "arguments": arguments,
        "carrier_path": carrier_path,
        "control_files": control_files,
        "control_revision": control_revision,
        "control_root": control_root,
        "expectation": expectation,
        "expectation_bytes": expectation_bytes,
        "expectation_path": expectation_path,
        "output_path": output_path,
        "staging_root": staging_root,
        "subject_revision": subject_revision,
        "subject_root": subject_root,
        "tool": control_root / TOOL_MODULE.WRAPPER_SOURCE_PATH,
    }


def base_expectation() -> dict[str, Any]:
    run_key = (
        "GITHUB_RUN_ID=9001|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"
    )
    subject = {
        "repository": "example-org/example-subject",
        "source_commit": "1" * 40,
        "subject_run_key": run_key,
    }
    return {
        "authority_boundary": copy.deepcopy(
            TOOL_MODULE.EXPECTED_EXPECTATION_AUTHORITY_BOUNDARY
        ),
        "content_boundary": copy.deepcopy(
            TOOL_MODULE.EXPECTED_EXPECTATION_CONTENT_BOUNDARY
        ),
        "document_type": "pulsemech_compute_current_run_export_expectation",
        "errors": [],
        "expectation_identity": {
            "expectation_created_utc": "2026-08-19T06:00:00Z",
            "expectation_scope": "current_run_export",
            "subject_run_key": run_key,
        },
        "ok": True,
        "packet_contract": copy.deepcopy(TOOL_MODULE.EXPECTED_PACKET_CONTRACT),
        "record_status": "observed",
        "schema_version": "pulsemech_compute_current_run_export_expectation_v0",
        "subject": subject,
        "trusted_control_plane": {
            "checkout_role": "protected_control_plane",
            "repository": "example-org/example-control",
            "revision": "2" * 40,
            "separate_from_subject_checkout": True,
            "subject_may_select_revision": False,
            "trust_mode": "protected_exact_revision",
        },
    }


# ---------------------------------------------------------------------------
# Artifact, launcher, and fixed-scope proofs
# ---------------------------------------------------------------------------


def test_wrapper_artifact_identity_matches_reviewed_candidate() -> None:
    payload = TOOL.read_bytes()
    assert len(payload) == EXPECTED_TOOL_BYTES
    assert payload.count(b"\n") == EXPECTED_TOOL_LINES
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in payload
    assert b"\r" not in payload
    assert sha256_bytes(payload) == EXPECTED_TOOL_SHA256
    assert git_blob_sha1(payload) == EXPECTED_TOOL_GIT_BLOB_SHA1
    assert TOOL_MODULE.TOOL_NAME == (
        "build_pulsemech_compute_subject_input_packet_current_run_v0"
    )
    assert TOOL_MODULE.TOOL_VERSION == "0.1.0"
    assert TOOL_MODULE.DOCUMENT_TYPE == (
        "pulsemech_compute_subject_input_packet_current_run_wrapper"
    )
    assert TOOL_MODULE.OUTPUT_SCHEMA_VERSION == (
        "pulsemech_compute_subject_input_packet_v0"
    )
    assert TOOL_MODULE.WRAPPER_SOURCE_PATH == TOOL.relative_to(ROOT).as_posix()


def test_tools_tests_manifest_registers_current_run_wrapper_regression_exactly_once() -> None:
    entries = manifest_entries()
    assert len(entries) == len(set(entries))
    assert entries.count(TEST_RELATIVE_PATH) == 1
    index = entries.index(TEST_RELATIVE_PATH)
    assert entries[index - 1] == (
        "tests/test_load_pulsemech_compute_current_run_export_carrier_v0.py"
    )
    assert entries[index + 1] == (
        "tests/test_pulsemech_compute_current_run_export_candidate_workflow_v0.py"
    )
    assert entries[index + 2] == (
        "tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
    )
    assert entries[index + 3] == (
        "tests/test_build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"
    )
    assert entries[index + 4] == (
        "tests/test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py"
    )
    assert entries[index + 5] == (
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
        timeout=600,
    )
    assert result.returncode == 0, result.stderr.decode(
        "utf-8", errors="replace"
    )
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
        "document_type": (
            "pulsemech_compute_subject_input_packet_current_run_wrapper"
        ),
        "errors": ["isolated_python_runtime_required: launch with python -I"],
        "exit_kind": "python_runtime_boundary_error",
        "ok": False,
        "tool": "build_pulsemech_compute_subject_input_packet_current_run_v0",
        "tool_version": "0.1.0",
    }


def test_isolated_help_exposes_complete_cli_surface() -> None:
    result = run_tool("--help", isolated=True)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    text = result.stdout.decode("utf-8", errors="strict")
    for option in (
        "--expectation",
        "--expectation-sha256",
        "--staging-root",
        "--subject-root",
        "--subject-repository",
        "--subject-revision",
        "--control-plane-root",
        "--control-plane-repository",
        "--control-plane-revision",
        "--packet-created-utc",
        "--producer-run-key",
        "--ci-workflow-or-job-identity",
        "--trusted-git",
        "--max-carrier-bytes",
        "--max-total-uncompressed-bytes",
        "--output",
    ):
        assert option in text


def test_source_reuses_existing_producer_core_without_second_packet_implementation() -> None:
    source = TOOL.read_text(encoding="utf-8")
    tree = ast.parse(source)
    defined_functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "build_packet" not in defined_functions
    assert "build_artifacts" not in defined_functions
    assert "role_bindings" not in defined_functions
    assert "build_subject_and_sources" not in defined_functions
    assert "producer_identity" not in defined_functions
    assert "validate_generated_packet" not in defined_functions
    for exact_call in (
        "producer_core.build_artifacts(",
        "producer_core.role_bindings(",
        "producer_core.build_subject_and_sources(",
        "producer_core.producer_identity(",
        "producer_core.build_packet(",
        "producer_core.validate_generated_packet(",
    ):
        assert source.count(exact_call) == 1
    assert "class ProducerProfile" not in source
    assert "class PacketInputs" not in source
    assert "subject_input_producer_core" in source


def test_component_set_and_closed_boundaries_are_exact() -> None:
    assert TOOL_MODULE.CONTROL_PLANE_COMPONENT_SPECS == (
        (
            "carrier_loader",
            "tools/load_pulsemech_compute_current_run_export_carrier_v0.py",
            "0.1.0",
        ),
        (
            "control_plane_workflow",
            ".github/workflows/pulsemech_compute_current_run_export_candidate.yml",
            "0.1.0",
        ),
        (
            "expectation_builder",
            "tools/build_pulsemech_compute_current_run_export_expectation_v0.py",
            "0.1.0",
        ),
        (
            "expectation_schema",
            "schemas/pulsemech_compute_current_run_export_expectation_v0.schema.json",
            "0",
        ),
        (
            "expectation_validator",
            "tools/check_pulsemech_compute_current_run_export_expectation_v0.py",
            "0.1.0",
        ),
        (
            "subject_input_producer_core",
            "tools/pulsemech_compute_subject_input_packet_producer_core_v0.py",
            "0.1.0",
        ),
        (
            "subject_input_producer_wrapper",
            "tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py",
            "0.1.0",
        ),
        (
            "subject_input_schema",
            "schemas/pulsemech_compute_subject_input_packet_v0.schema.json",
            "0",
        ),
        (
            "subject_input_validator",
            "tools/check_pulsemech_compute_subject_input_packet_v0.py",
            "0.1.0",
        ),
    )
    assert TOOL_MODULE.EXPECTED_PACKET_CONTRACT["production_mode"] == (
        "current_run_export"
    )
    assert TOOL_MODULE.EXPECTED_PACKET_CONTRACT["packet_scope"] == "current_run"
    assert TOOL_MODULE.EXPECTED_PACKET_AUTHORITY_BOUNDARY[
        "write_mode"
    ] == "subject_input_only"
    assert all(
        value is False
        for key, value in TOOL_MODULE.EXPECTED_PACKET_AUTHORITY_BOUNDARY.items()
        if key != "write_mode"
    )
    assert TOOL_MODULE.EXPECTED_PACKET_CONTENT_BOUNDARY == {
        "artifact_bytes_embedded": False,
        "carrier_required_for_verification": True,
        "packet_payload_mode": "metadata_only",
        "raw_model_inputs_included": False,
        "raw_model_outputs_included": False,
        "raw_secrets_included": False,
    }


# ---------------------------------------------------------------------------
# Canonical input and expectation binding proofs
# ---------------------------------------------------------------------------


def test_strict_json_canonical_values_and_time_binding_fail_closed() -> None:
    value = {"a": 1, "b": [True, None]}
    rendered = TOOL_MODULE.render_json(value)
    assert rendered == b'{\n  "a": 1,\n  "b": [\n    true,\n    null\n  ]\n}\n'
    assert TOOL_MODULE.parse_json_object(rendered, label="value") == value
    with pytest.raises(TOOL_MODULE.WrapperError, match="utf8_bom"):
        TOOL_MODULE.parse_json_object(b"\xef\xbb\xbf{}\n", label="value")
    with pytest.raises(TOOL_MODULE.WrapperError, match="duplicate JSON key"):
        TOOL_MODULE.parse_json_object(b'{"a":1,"a":2}\n', label="value")
    with pytest.raises(TOOL_MODULE.WrapperError, match="non-finite"):
        TOOL_MODULE.parse_json_object(b'{"a":NaN}\n', label="value")
    assert TOOL_MODULE.canonical_member_path(
        "exports/current-run.zip", label="path"
    ) == "exports/current-run.zip"
    for invalid in ("", "/absolute", "../escape", "a/./b", "a\\b", "a/"):
        with pytest.raises(TOOL_MODULE.WrapperError):
            TOOL_MODULE.canonical_member_path(invalid, label="path")
    assert TOOL_MODULE.parse_utc(
        "2026-08-19T06:00:00Z", label="time"
    ).isoformat().endswith("+00:00")
    for invalid in ("2026-08-19", "2026-08-19T06:00:00+00:00", "bad"):
        with pytest.raises(TOOL_MODULE.WrapperError):
            TOOL_MODULE.parse_utc(invalid, label="time")


def test_expectation_header_binds_exact_subject_control_digest_and_time() -> None:
    expectation = base_expectation()
    payload = render_json(expectation)
    TOOL_MODULE._verify_expectation_header(
        expectation=expectation,
        expectation_bytes=payload,
        expectation_sha256=sha256_bytes(payload),
        subject_repository="example-org/example-subject",
        subject_revision="1" * 40,
        control_repository="example-org/example-control",
        control_revision="2" * 40,
        producer_run_key=(
            "GITHUB_RUN_ID=9001|GITHUB_RUN_ATTEMPT=1|"
            "GITHUB_WORKFLOW=PULSE CI"
        ),
        packet_created_utc="2026-08-19T06:00:00Z",
    )
    for key, replacement in (
        ("subject_repository", "other/repository"),
        ("subject_revision", "3" * 40),
        ("control_repository", "other/control"),
        ("control_revision", "4" * 40),
    ):
        kwargs = {
            "expectation": expectation,
            "expectation_bytes": payload,
            "expectation_sha256": sha256_bytes(payload),
            "subject_repository": "example-org/example-subject",
            "subject_revision": "1" * 40,
            "control_repository": "example-org/example-control",
            "control_revision": "2" * 40,
            "producer_run_key": expectation["subject"]["subject_run_key"],
            "packet_created_utc": "2026-08-19T06:00:00Z",
        }
        kwargs[key] = replacement
        with pytest.raises(TOOL_MODULE.WrapperError):
            TOOL_MODULE._verify_expectation_header(**kwargs)


def test_expectation_header_rejects_noncanonical_bytes_and_stale_packet_time() -> None:
    expectation = base_expectation()
    canonical = render_json(expectation)
    noncanonical = json.dumps(expectation, separators=(",", ":")).encode("utf-8")
    with pytest.raises(TOOL_MODULE.WrapperError, match="not_canonical"):
        TOOL_MODULE._verify_expectation_header(
            expectation=expectation,
            expectation_bytes=noncanonical,
            expectation_sha256=sha256_bytes(noncanonical),
            subject_repository="example-org/example-subject",
            subject_revision="1" * 40,
            control_repository="example-org/example-control",
            control_revision="2" * 40,
            producer_run_key=expectation["subject"]["subject_run_key"],
            packet_created_utc="2026-08-19T06:00:00Z",
        )
    with pytest.raises(TOOL_MODULE.WrapperError, match="packet_created_before"):
        TOOL_MODULE._verify_expectation_header(
            expectation=expectation,
            expectation_bytes=canonical,
            expectation_sha256=sha256_bytes(canonical),
            subject_repository="example-org/example-subject",
            subject_revision="1" * 40,
            control_repository="example-org/example-control",
            control_revision="2" * 40,
            producer_run_key=expectation["subject"]["subject_run_key"],
            packet_created_utc="2026-08-19T05:59:59Z",
        )


# ---------------------------------------------------------------------------
# Protected Git boundary proofs
# ---------------------------------------------------------------------------


def test_git_subprocess_profile_forces_local_only_bounded_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    git = trusted_git_path()
    observed: dict[str, Any] = {}

    def fake_bounded(**kwargs: Any) -> bytes:
        observed.update(kwargs)
        return b"ok"

    monkeypatch.setattr(TOOL_MODULE, "_run_bounded_command", fake_bounded)
    result = TOOL_MODULE._run_git(
        git_path=git,
        repository_root=tmp_path,
        arguments=("status", "--porcelain"),
        label="probe",
        max_stdout_bytes=1234,
        timeout_seconds=17,
    )
    assert result == b"ok"
    command = observed["command"]
    assert command[0] == str(git)
    assert "--no-lazy-fetch" in command
    assert "--no-replace-objects" in command
    assert command[-2:] == ["status", "--porcelain"]
    config = [
        command[index + 1]
        for index, value in enumerate(command[:-1])
        if value == "-c"
    ]
    for required in (
        "core.sshCommand=/bin/false",
        "credential.helper=",
        "protocol.allow=never",
        "protocol.file.allow=never",
        "protocol.ssh.allow=never",
    ):
        assert required in config
    environment = observed["environment"]
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
    assert environment["GIT_SSH_COMMAND"] == "/bin/false"
    assert environment["GIT_ASKPASS"] == "/bin/false"
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["PATH"] == str(git.parent)
    assert observed["max_stdout_bytes"] == 1234
    assert observed["timeout_seconds"] == 17


def test_git_config_capture_is_bounded_before_parse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    initialize_git_repository(
        repository,
        {"README.md": b"fixture\n"},
        message="bounded config fixture",
    )
    config_path = repository / ".git" / "config"
    with config_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n[pulse]\n")
        for index in range(320):
            handle.write(f"synthetic{index} = " + ("x" * 4096) + "\n")
    assert config_path.stat().st_size > TOOL_MODULE.MAX_GIT_CONFIG_BYTES
    called = False

    def parser_must_not_run(*_args: Any, **_kwargs: Any) -> Any:
        nonlocal called
        called = True
        raise AssertionError("config parser must not run after capture overflow")

    monkeypatch.setattr(
        TOOL_MODULE,
        "_parse_scoped_git_config",
        parser_must_not_run,
    )
    with pytest.raises(
        TOOL_MODULE.WrapperError,
        match="capture_limit_exceeded",
    ):
        TOOL_MODULE._verify_git_local_only_repository_state(
            git_path=trusted_git_path(),
            repository_root=repository,
            label="bounded",
        )
    assert called is False


def test_git_local_only_preflight_rejects_remote_boundary_configuration(
    tmp_path: Path,
) -> None:
    cases = (
        ("extensions.partialClone", "origin", False),
        ("remote.origin.promisor", "true", False),
        ("remote.origin.partialCloneFilter", "blob:none", False),
        ("core.sshCommand", "/tmp/subject-selected-ssh", False),
        ("core.sshCommand", "/tmp/worktree-selected-ssh", True),
    )
    for index, (key, value, worktree) in enumerate(cases):
        repository = tmp_path / f"repo-{index}"
        initialize_git_repository(
            repository,
            {"README.md": b"fixture\n"},
            message=f"remote boundary {index}",
        )
        if worktree:
            git_run(repository, "config", "extensions.worktreeConfig", "true")
            git_run(repository, "config", "--worktree", key, value)
        else:
            git_run(repository, "config", "--local", key, value)
        with pytest.raises(TOOL_MODULE.WrapperError, match="rejected"):
            TOOL_MODULE._verify_git_local_only_repository_state(
                git_path=trusted_git_path(),
                repository_root=repository,
                label=f"remote_{index}",
            )


def test_git_local_only_preflight_rejects_promisor_alternates_and_shallow_state(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    initialize_git_repository(
        repository,
        {"README.md": b"fixture\n"},
        message="git state fixture",
    )
    pack = repository / ".git" / "objects" / "pack"
    pack.mkdir(parents=True, exist_ok=True)
    marker = pack / "synthetic.promisor"
    marker.write_bytes(b"")
    with pytest.raises(TOOL_MODULE.WrapperError, match="promisor"):
        TOOL_MODULE._verify_git_local_only_repository_state(
            git_path=trusted_git_path(),
            repository_root=repository,
            label="promisor",
        )
    marker.unlink()

    alternates = repository / ".git" / "objects" / "info" / "alternates"
    alternates.parent.mkdir(parents=True, exist_ok=True)
    alternates.write_text("/tmp/other-objects\n", encoding="utf-8")
    with pytest.raises(TOOL_MODULE.WrapperError, match="alternate"):
        TOOL_MODULE._verify_git_local_only_repository_state(
            git_path=trusted_git_path(),
            repository_root=repository,
            label="alternate",
        )
    alternates.unlink()

    shallow = repository / ".git" / "shallow"
    shallow.write_text("0" * 40 + "\n", encoding="ascii")
    with pytest.raises(TOOL_MODULE.WrapperError, match="shallow"):
        TOOL_MODULE._verify_git_local_only_repository_state(
            git_path=trusted_git_path(),
            repository_root=repository,
            label="shallow",
        )


def test_verified_repository_blob_rehashes_and_binds_worktree_bytes(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    payload = b"exact committed bytes\n"
    revision = initialize_git_repository(
        repository,
        {"path/file.txt": payload},
        message="exact blob fixture",
    )
    observed = TOOL_MODULE._verified_repository_blob(
        git_path=trusted_git_path(),
        repository_root=repository,
        revision=revision,
        repository_path="path/file.txt",
        label="exact",
        max_bytes=1024,
    )
    assert observed.payload == payload
    assert observed.git_blob_sha1 == git_blob_sha1(payload)
    assert observed.sha256 == sha256_bytes(payload)
    (repository / "path" / "file.txt").write_bytes(b"modified\n")
    with pytest.raises(TOOL_MODULE.WrapperError, match="working_tree"):
        TOOL_MODULE._verified_repository_blob(
            git_path=trusted_git_path(),
            repository_root=repository,
            revision=revision,
            repository_path="path/file.txt",
            label="modified",
            max_bytes=1024,
        )


def test_independent_git_storage_rejects_shared_store(tmp_path: Path) -> None:
    subject = tmp_path / "subject"
    control = tmp_path / "control"
    subject.mkdir()
    control.mkdir()
    subject_storage = (subject / ".git", subject / ".git" / "objects")
    control_storage = (control / ".git", control / ".git" / "objects")
    TOOL_MODULE._verify_independent_git_storage(
        subject_storage=subject_storage,
        control_storage=control_storage,
        subject_root=subject,
        control_root=control,
    )
    with pytest.raises(TOOL_MODULE.WrapperError, match="independent"):
        TOOL_MODULE._verify_independent_git_storage(
            subject_storage=subject_storage,
            control_storage=subject_storage,
            subject_root=subject,
            control_root=control,
        )


# ---------------------------------------------------------------------------
# Carrier-content and packet binding proofs
# ---------------------------------------------------------------------------


def test_archive_reader_rejects_duplicate_unsafe_encrypted_and_oversized_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = deterministic_zip({"a.txt": b"a", "b.txt": b"b"})
    assert TOOL_MODULE._read_zip_payloads(
        valid,
        label="valid",
        budget=TOOL_MODULE.UncompressedByteBudget(maximum=16),
    ) == {"a.txt": b"a", "b.txt": b"b"}

    duplicate_buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(duplicate_buffer, "w") as archive:
            archive.writestr("a.txt", b"a")
            archive.writestr("a.txt", b"b")
    with pytest.raises(TOOL_MODULE.WrapperError, match="duplicate"):
        TOOL_MODULE._read_zip_payloads(
            duplicate_buffer.getvalue(),
            label="duplicate",
            budget=TOOL_MODULE.UncompressedByteBudget(maximum=16),
        )

    for unsafe in ("../escape", "/absolute", "a\\b", "folder/"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(unsafe, b"x")
        with pytest.raises(TOOL_MODULE.WrapperError):
            TOOL_MODULE._read_zip_payloads(
                buffer.getvalue(),
                label="unsafe",
                budget=TOOL_MODULE.UncompressedByteBudget(maximum=16),
            )

    encrypted = bytearray(deterministic_zip({"a.txt": b"a"}))
    # Set the encryption bit in both the local and central headers.
    local = encrypted.find(b"PK\x03\x04")
    central = encrypted.find(b"PK\x01\x02")
    assert local >= 0 and central >= 0
    encrypted[local + 6 : local + 8] = (1).to_bytes(2, "little")
    encrypted[central + 8 : central + 10] = (1).to_bytes(2, "little")
    with pytest.raises(TOOL_MODULE.WrapperError, match="encrypted"):
        TOOL_MODULE._read_zip_payloads(
            bytes(encrypted),
            label="encrypted",
            budget=TOOL_MODULE.UncompressedByteBudget(maximum=16),
        )

    with pytest.raises(
        TOOL_MODULE.WrapperError,
        match="aggregate_uncompressed",
    ):
        TOOL_MODULE._read_zip_payloads(
            deterministic_zip({"large.bin": b"x" * 17}),
            label="large",
            budget=TOOL_MODULE.UncompressedByteBudget(maximum=16),
        )


def test_nested_archives_share_one_aggregate_uncompressed_budget(
    tmp_path: Path,
) -> None:
    fixture = complete_fixture(tmp_path)
    carrier_bytes = fixture["carrier_path"].read_bytes()
    layout = fixture["expectation"]["archive_layout"]

    def declared_total(payload: bytes) -> int:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            return sum(info.file_size for info in archive.infolist())

    with zipfile.ZipFile(io.BytesIO(carrier_bytes), "r") as outer:
        complete_payload = outer.read(
            layout["original_artifacts_prefix"]
            + layout["complete_package_name"]
        )
        completeness_payload = outer.read(
            layout["original_artifacts_prefix"]
            + layout["completeness_archive_name"]
        )
        verification_payload = outer.read(
            layout["original_artifacts_prefix"]
            + layout["verification_archive_name"]
        )

    per_archive_totals = (
        declared_total(carrier_bytes),
        declared_total(complete_payload),
        declared_total(completeness_payload),
        declared_total(verification_payload),
    )
    aggregate_total = sum(per_archive_totals)
    assert aggregate_total - 1 > max(per_archive_totals)

    bundle = TOOL_MODULE.load_current_run_bundle(
        carrier_path=fixture["carrier_path"],
        carrier_bytes=carrier_bytes,
        expectation=fixture["expectation"],
        max_total_uncompressed_bytes=aggregate_total,
    )
    assert bundle.archive_size == len(carrier_bytes)

    with pytest.raises(
        TOOL_MODULE.WrapperError,
        match="aggregate_uncompressed",
    ):
        TOOL_MODULE.load_current_run_bundle(
            carrier_path=fixture["carrier_path"],
            carrier_bytes=carrier_bytes,
            expectation=fixture["expectation"],
            max_total_uncompressed_bytes=aggregate_total - 1,
        )


def test_sha256sums_inventory_and_check_reports_are_exact(tmp_path: Path) -> None:
    first = b"one\n"
    second = b"two\n"
    sums = TOOL_MODULE._parse_sha256sums(
        (
            f"{sha256_bytes(first)}  one.txt\n"
            f"{sha256_bytes(second)}  nested/two.txt\n"
        ).encode("ascii")
    )
    assert sums == {
        "one.txt": sha256_bytes(first),
        "nested/two.txt": sha256_bytes(second),
    }
    with pytest.raises(TOOL_MODULE.WrapperError, match="duplicate"):
        TOOL_MODULE._parse_sha256sums(
            (
                f"{sha256_bytes(first)}  one.txt\n"
                f"{sha256_bytes(first)}  one.txt\n"
            ).encode("ascii")
        )

    fixture = complete_fixture(tmp_path)
    subject = fixture["expectation"]["subject"]
    sources = fixture["expectation"]["authority_sources"]
    members, inventory = make_complete_package_members(
        subject=subject,
        sources=sources,
    )
    rows = TOOL_MODULE._validate_package_inventory(
        members=members,
        inventory=inventory,
    )
    assert len(rows) == len(members) - 1

    verification_ids = verification_check_ids(
        members=members,
        inventory=inventory,
        subject=subject,
    )
    checks = report_checks(verification_ids)
    report = {
        "authority_boundary": copy.deepcopy(
            TOOL_MODULE.VERIFICATION_REPORT_AUTHORITY_BOUNDARY
        ),
        "checked_utc": "2026-08-19T06:25:00Z",
        "checks": checks,
        "errors": [],
        "package": {"path": "/synthetic/complete-package"},
        "schema_version": "schema:v0",
        "status": "verified",
        "summary": {"checks_failed": 0, "checks_total": len(checks)},
        "tool": copy.deepcopy(TOOL_MODULE.VERIFICATION_REPORT_TOOL),
        "verified": True,
    }
    TOOL_MODULE._validate_check_report(
        document=report,
        schema_version="schema:v0",
        status_field="status",
        status_value="verified",
        label="report",
        report_kind="verification",
        members=members,
        inventory=inventory,
        inventory_rows=rows,
        subject=subject,
    )

    forged = copy.deepcopy(report)
    forged["checks"] = forged["checks"][1:]
    forged["summary"] = {
        "checks_failed": 0,
        "checks_total": len(forged["checks"]),
    }
    with pytest.raises(TOOL_MODULE.WrapperError, match="check_identity_set_mismatch"):
        TOOL_MODULE._validate_check_report(
            document=forged,
            schema_version="schema:v0",
            status_field="status",
            status_value="verified",
            label="report",
            report_kind="verification",
            members=members,
            inventory=inventory,
            inventory_rows=rows,
            subject=subject,
        )

    substituted = dict(members)
    substituted["artifacts/external/llamaguard_raw.jsonl"] = b"{}\n"
    with pytest.raises(TOOL_MODULE.WrapperError):
        TOOL_MODULE._validate_check_report(
            document=report,
            schema_version="schema:v0",
            status_field="status",
            status_value="verified",
            label="report",
            report_kind="verification",
            members=substituted,
            inventory=inventory,
            inventory_rows=rows,
            subject=subject,
        )


def test_completeness_semantic_report_requires_full_package_checks(
    tmp_path: Path,
) -> None:
    fixture = complete_fixture(tmp_path)
    subject = fixture["expectation"]["subject"]
    sources = fixture["expectation"]["authority_sources"]
    members, inventory = make_complete_package_members(
        subject=subject,
        sources=sources,
    )
    rows = TOOL_MODULE._validate_package_inventory(
        members=members,
        inventory=inventory,
    )
    ids = completeness_check_ids(members=members, inventory=inventory)
    checks = report_checks(ids)
    report = {
        "authority_boundary": copy.deepcopy(
            TOOL_MODULE.COMPLETENESS_REPORT_AUTHORITY_BOUNDARY
        ),
        "checks": checks,
        "errors": [],
        "ok": True,
        "package": {"path": "/synthetic/complete-package"},
        "schema_version": "release_grade_package_completeness_v1",
        "status": "complete",
        "summary": {
            "checks_failed": 0,
            "checks_total": len(checks),
            "required_dirs": len(PACKAGE_REQUIRED_DIRS),
            "required_files": len(PACKAGE_REQUIRED_FILES),
        },
        "tool": copy.deepcopy(TOOL_MODULE.COMPLETENESS_REPORT_TOOL),
    }
    TOOL_MODULE._validate_check_report(
        document=report,
        schema_version="release_grade_package_completeness_v1",
        status_field="status",
        status_value="complete",
        label="completeness",
        report_kind="completeness",
        members=members,
        inventory=inventory,
        inventory_rows=rows,
        subject=subject,
    )

    omitted = copy.deepcopy(report)
    omitted["checks"] = [
        item
        for item in omitted["checks"]
        if item["check_id"] != "report_card.non_stub"
    ]
    omitted["summary"]["checks_total"] = len(omitted["checks"])
    with pytest.raises(TOOL_MODULE.WrapperError, match="check_identity_set_mismatch"):
        TOOL_MODULE._validate_check_report(
            document=omitted,
            schema_version="release_grade_package_completeness_v1",
            status_field="status",
            status_value="complete",
            label="completeness",
            report_kind="completeness",
            members=members,
            inventory=inventory,
            inventory_rows=rows,
            subject=subject,
        )

    malformed = dict(members)
    malformed["artifacts/report_card.html"] = (
        b"<html><body>Placeholder report.</body></html>\n"
    )
    with pytest.raises(TOOL_MODULE.WrapperError, match="report_card"):
        TOOL_MODULE._validate_check_report(
            document=report,
            schema_version="release_grade_package_completeness_v1",
            status_field="status",
            status_value="complete",
            label="completeness",
            report_kind="completeness",
            members=malformed,
            inventory=inventory,
            inventory_rows=rows,
            subject=subject,
        )


def test_real_producer_core_source_ids_match_canonical_projection() -> None:
    source = PRODUCER_CORE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(PRODUCER_CORE))
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "build_subject_and_sources"
    )
    observed: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "git_source":
            continue
        for keyword in node.keywords:
            if keyword.arg == "source_id" and isinstance(keyword.value, ast.Constant):
                assert isinstance(keyword.value.value, str)
                observed.add(keyword.value.value)
    assert observed == {
        "source:workflow:pulse-ci",
        "source:policy:pulse-gate-policy-v0",
        "source:registry:gate-registry-v0",
        "source:policy:external-signers-v1",
        "source:policy:external-thresholds",
    }

    files = {
        ".github/workflows/pulse_ci.yml": b"name: PULSE CI\n",
        "policy/external_signers_v1.yml": b"version: recorded\n",
        "PULSE_safe_pack_v0/profiles/external_thresholds.yaml": b"thresholds: {}\n",
        "pulse_gate_policy_v0.yml": b"policy:\n  id: policy:synthetic\n",
        "pulse_gate_registry_v0.yml": b"version: registry:synthetic\n",
    }
    expectation_sources = authority_sources(
        Path("/unused"),
        "1" * 40,
        files,
    )
    projected = TOOL_MODULE._canonical_packet_authority_sources(
        expectation_sources
    )
    projected_ids = {
        projected["workflow"]["source_id"],
        projected["policy"]["source_id"],
        projected["gate_registry"]["source_id"],
        *(row["source_id"] for row in projected["additional_sources"]),
    }
    assert projected_ids == observed
    assert expectation_sources["workflow"]["source_id"] == "source:workflow"


def _import_repository_module(path: Path, *, suffix: str) -> Any:
    name = f"pulsemech_repository_contract_{suffix}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_real_subject_validator_routes_producer_provenance_to_control_checkout(
    tmp_path: Path,
) -> None:
    validator = _import_repository_module(
        SUBJECT_VALIDATOR,
        suffix="subject_validator_provenance",
    )
    subject_root = tmp_path / "subject"
    control_root = tmp_path / "control"
    subject_root.mkdir()
    control_root.mkdir()
    wrapper_path = control_root / TOOL_MODULE.WRAPPER_SOURCE_PATH
    wrapper_path.parent.mkdir(parents=True)
    wrapper_payload = TOOL.read_bytes()
    wrapper_path.write_bytes(wrapper_payload)
    subject_revision = "1" * 40
    control_revision = "2" * 40
    control_files = {
        "subject_input_producer_wrapper": TOOL_MODULE.VerifiedFile(
            role="subject_input_producer_wrapper",
            repository_root=control_root,
            revision=control_revision,
            repository_path=TOOL_MODULE.WRAPPER_SOURCE_PATH,
            path=wrapper_path,
            payload=wrapper_payload,
            git_blob_sha1=git_blob_sha1(wrapper_payload),
            sha256=sha256_bytes(wrapper_payload),
        )
    }
    TOOL_MODULE._bind_hardened_git_interfaces(
        producer_core=type("Core", (), {})(),
        subject_validator=validator,
        trusted_git=Path("/usr/bin/git"),
        subject_root=subject_root,
        subject_revision=subject_revision,
        control_root=control_root,
        control_revision=control_revision,
        control_files=control_files,
        authority_files={},
    )
    assert validator._git_blob_bytes(
        subject_root,
        revision=control_revision,
        path=TOOL_MODULE.WRAPPER_SOURCE_PATH,
    ) == wrapper_payload

    run_key = "GITHUB_RUN_ID=9|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"
    packet = {
        "carrier": {"carrier_kind": "current_run_export_archive"},
        "fixture_provenance": None,
        "packet_identity": {"packet_scope": "current_run"},
        "producer": {
            "producer_run_key": run_key,
            "producer_source": TOOL_MODULE.WRAPPER_SOURCE_PATH,
            "producer_source_revision": control_revision,
            "producer_source_sha256": sha256_bytes(wrapper_payload),
            "production_mode": "current_run_export",
        },
        "record_status": "observed",
        "subject": {"subject_run_key": run_key},
    }
    ok, errors = validator._verify_provenance(
        packet,
        packet_path=tmp_path / "packet.json",
        repository_root=subject_root,
    )
    assert ok is True
    assert errors == []

    altered = copy.deepcopy(packet)
    altered["producer"]["producer_source_revision"] = subject_revision
    ok, errors = validator._verify_provenance(
        altered,
        packet_path=tmp_path / "packet.json",
        repository_root=subject_root,
    )
    assert ok is False
    assert errors

def test_preservation_manifest_binds_current_subject_and_provider_bytes() -> None:
    subject = {
        "active_policy_sets": ["required"],
        "decision": "ALLOW",
        "repository": "example/repo",
        "run_mode": "prod",
        "source_commit": "1" * 40,
        "source_ref": "refs/heads/main",
        "workflow_name": "PULSE CI",
        "workflow_run_attempt": 1,
        "workflow_run_id": 9,
        "workflow_run_number": 2,
    }
    expectation = {"subject": subject}
    provider_names = {
        "complete": "complete.zip",
        "completeness": "completeness.zip",
        "verification": "verification.zip",
    }
    payloads = {name: name.encode("ascii") for name in provider_names.values()}
    rows = []
    roles = TOOL_MODULE.PROVIDER_ARCHIVE_ROLES
    for index, (role, name) in enumerate(provider_names.items(), start=1):
        payload = payloads[name]
        rows.append(
            {
                "artifact_id": index,
                "artifact_name": name,
                "created_at": "2026-08-19T00:00:00Z",
                "downloaded_sha256": sha256_bytes(payload),
                "downloaded_size_bytes": len(payload),
                "expires_at": "2026-09-19T00:00:00Z",
                "file_name": name,
                "github_digest_match": True,
                "github_sha256": sha256_bytes(payload),
                "github_size_match": True,
                "role": roles[role],
                "size_bytes": len(payload),
            }
        )
    manifest = {
        "active_policy_sets": subject["active_policy_sets"],
        "authority_boundary": copy.deepcopy(
            TOOL_MODULE.PRESERVATION_AUTHORITY_BOUNDARY
        ),
        "github_artifacts": rows,
        "primary_gate_result": "allow",
        "repository": subject["repository"],
        "run_mode": subject["run_mode"],
        "schema_id": "pulse_ci_release_grade_artifact_preservation_manifest_v0",
        "schema_version": "0.1.0",
        "source_commit": subject["source_commit"],
        "source_ref": subject["source_ref"],
        "workflow": subject["workflow_name"],
        "workflow_run_attempt": subject["workflow_run_attempt"],
        "workflow_run_id": subject["workflow_run_id"],
        "workflow_run_number": subject["workflow_run_number"],
    }
    indexed = TOOL_MODULE._validate_preservation_manifest(
        manifest=manifest,
        expectation=expectation,
        provider_names=provider_names,
        provider_payloads=payloads,
    )
    assert set(indexed) == set(provider_names.values())
    altered = copy.deepcopy(manifest)
    altered["workflow_run_id"] = 10
    with pytest.raises(TOOL_MODULE.WrapperError, match="workflow_run_id"):
        TOOL_MODULE._validate_preservation_manifest(
            manifest=altered,
            expectation=expectation,
            provider_names=provider_names,
            provider_payloads=payloads,
        )


def test_current_run_bundle_verifies_layout_reports_and_counts(tmp_path: Path) -> None:
    fixture = complete_fixture(tmp_path)
    bundle = TOOL_MODULE.load_current_run_bundle(
        carrier_path=fixture["carrier_path"],
        carrier_bytes=fixture["carrier_path"].read_bytes(),
        expectation=fixture["expectation"],
        max_total_uncompressed_bytes=1024 * 1024,
    )
    assert bundle.archive_sha256 == fixture["expectation"]["carrier"]["sha256"]
    assert bundle.archive_size == fixture["expectation"]["carrier"]["size_bytes"]
    assert set(PACKAGE_REQUIRED_FILES).issubset(bundle.complete_package_members)
    assert "synthetic_context.json" in bundle.complete_package_members
    assert len(bundle.complete_package_members) == 21
    assert bundle.completeness_report["status"] == "complete"
    assert bundle.verification_report["status"] == "verified"
    altered = copy.deepcopy(fixture["expectation"])
    altered["archive_layout"]["expected_non_provider_artifact_count"] = 27
    with pytest.raises(TOOL_MODULE.WrapperError, match="non_provider"):
        TOOL_MODULE.load_current_run_bundle(
            carrier_path=fixture["carrier_path"],
            carrier_bytes=fixture["carrier_path"].read_bytes(),
            expectation=altered,
            max_total_uncompressed_bytes=1024 * 1024,
        )


def test_profile_derivation_binds_expectation_without_second_profile_implementation(
    tmp_path: Path,
) -> None:
    fixture = complete_fixture(tmp_path)
    core_path = fixture["control_root"] / TOOL_MODULE.PRODUCER_CORE_SOURCE_PATH
    core = TOOL_MODULE._load_verified_module(
        verified=TOOL_MODULE.VerifiedFile(
            role="core",
            repository_root=fixture["control_root"],
            revision=fixture["control_revision"],
            repository_path=TOOL_MODULE.PRODUCER_CORE_SOURCE_PATH,
            path=core_path,
            payload=core_path.read_bytes(),
            git_blob_sha1=git_blob_sha1(core_path.read_bytes()),
            sha256=sha256_bytes(core_path.read_bytes()),
        ),
        module_name="synthetic_profile_core",
    )
    profile = TOOL_MODULE._derive_producer_profile(
        expectation=fixture["expectation"],
        producer_core=core,
        carrier_path=fixture["carrier_path"],
    )
    assert profile.production_mode == "current_run_export"
    assert profile.packet_scope == "current_run"
    assert profile.producer_source_path == TOOL_MODULE.WRAPPER_SOURCE_PATH
    assert profile.expected_carrier_sha256 == fixture["expectation"]["carrier"][
        "sha256"
    ]
    assert profile.expected_artifact_count == 29
    altered = copy.deepcopy(fixture["expectation"])
    altered["packet_producer_profile"]["expected_production_mode"] = "other"
    with pytest.raises(TOOL_MODULE.WrapperError, match="expected_production_mode"):
        TOOL_MODULE._derive_producer_profile(
            expectation=altered,
            producer_core=core,
            carrier_path=fixture["carrier_path"],
        )


def test_packet_equivalence_requires_exact_subject_sources_carrier_and_boundaries() -> None:
    source_payloads = {
        ".github/workflows/pulse_ci.yml": b"name: PULSE CI\n",
        "policy/external_signers_v1.yml": b"version: recorded\n",
        "PULSE_safe_pack_v0/profiles/external_thresholds.yaml": b"thresholds: {}\n",
        "pulse_gate_policy_v0.yml": b"policy:\n  id: policy:synthetic\n",
        "pulse_gate_registry_v0.yml": b"version: registry:synthetic\n",
    }
    expectation_sources = authority_sources(
        Path("/unused"),
        "1" * 40,
        source_payloads,
    )
    expectation = {
        "authority_sources": expectation_sources,
        "carrier": {
            "carrier_id": "carrier:current-run/pulse-ci-17/v0",
            "root_prefix": "root/",
            "staged_relative_path": "exports/current.zip",
        },
        "subject": {"subject_run_key": "run-key"},
    }

    class Profile:
        expected_run_key = "run-key"

    packet = {
        "authority_boundary": copy.deepcopy(
            TOOL_MODULE.EXPECTED_PACKET_AUTHORITY_BOUNDARY
        ),
        "authority_sources": TOOL_MODULE._canonical_packet_authority_sources(
            expectation_sources
        ),
        "carrier": {
            "artifact_payload_mode": "external_carrier",
            "carrier_id": expectation["carrier"]["carrier_id"],
            "carrier_kind": "current_run_export_archive",
            "immutable": True,
            "media_type": "application/zip",
            "path_or_uri": expectation["carrier"]["staged_relative_path"],
            "provider_binding": None,
            "root_prefix": "root",
            "sha256": "a" * 64,
            "size_bytes": 7,
        },
        "content_boundary": copy.deepcopy(
            TOOL_MODULE.EXPECTED_PACKET_CONTENT_BOUNDARY
        ),
        "errors": [],
        "ok": True,
        "packet_identity": {
            "carrier_id": expectation["carrier"]["carrier_id"],
            "subject_run_key": "run-key",
        },
        "packet_type": TOOL_MODULE.OUTPUT_PACKET_TYPE,
        "producer": {
            "producer_run_key": "run-key",
            "producer_source": TOOL_MODULE.WRAPPER_SOURCE_PATH,
            "production_mode": "current_run_export",
        },
        "record_status": "observed",
        "schema_version": TOOL_MODULE.OUTPUT_SCHEMA_VERSION,
        "subject": copy.deepcopy(expectation["subject"]),
    }
    TOOL_MODULE._verify_packet_equivalence(
        packet=packet,
        expectation=expectation,
        carrier_digest="a" * 64,
        carrier_size=7,
        profile=Profile(),
    )
    altered = copy.deepcopy(packet)
    altered["carrier"]["sha256"] = "b" * 64
    with pytest.raises(TOOL_MODULE.WrapperError, match="packet_carrier_sha256"):
        TOOL_MODULE._verify_packet_equivalence(
            packet=altered,
            expectation=expectation,
            carrier_digest="a" * 64,
            carrier_size=7,
            profile=Profile(),
        )

def test_output_boundary_rejects_protected_and_overlapping_paths(tmp_path: Path) -> None:
    subject = tmp_path / "subject"
    control = tmp_path / "control"
    staging = tmp_path / "staging"
    external = tmp_path / "external"
    for path in (subject, control, staging, external):
        path.mkdir()
    protected = external / "input.json"
    protected.write_text("{}\n", encoding="utf-8")
    safe = external / "packet.json"
    assert TOOL_MODULE._reject_unsafe_output(
        safe,
        subject_root=subject,
        control_root=control,
        staging_root=staging,
        protected_paths=[protected],
    ) == safe
    for rejected in (
        subject / "packet.json",
        control / "packet.json",
        staging / "packet.json",
        protected,
        external / "status.json",
        external / "release_authority_v0.json",
    ):
        with pytest.raises(TOOL_MODULE.WrapperError):
            TOOL_MODULE._reject_unsafe_output(
                rejected,
                subject_root=subject,
                control_root=control,
                staging_root=staging,
                protected_paths=[protected],
            )


def test_failure_diagnostic_is_canonical_and_non_authoritative() -> None:
    error = TOOL_MODULE.WrapperError(
        "synthetic_failure",
        exit_kind="synthetic_error",
        exit_code=7,
    )
    diagnostic = TOOL_MODULE._make_failure(error)
    assert diagnostic == {
        "authority_effect": "none",
        "document_type": (
            "pulsemech_compute_subject_input_packet_current_run_wrapper"
        ),
        "errors": ["synthetic_failure"],
        "exit_kind": "synthetic_error",
        "ok": False,
        "tool": "build_pulsemech_compute_subject_input_packet_current_run_v0",
        "tool_version": "0.1.0",
    }
    rendered = TOOL_MODULE.render_json(diagnostic)
    assert rendered == render_json(diagnostic)
    assert rendered.endswith(b"\n")
    assert b"\r" not in rendered


# ---------------------------------------------------------------------------
# Complete protected CLI and activation-boundary proofs
# ---------------------------------------------------------------------------


def test_complete_isolated_cli_uses_verified_core_is_deterministic_and_non_authoritative(
    tmp_path: Path,
) -> None:
    fixture = complete_fixture(tmp_path)
    first = run_tool(
        *fixture["arguments"],
        tool=fixture["tool"],
        cwd=fixture["control_root"],
        timeout=600,
    )
    assert first.returncode == 0, first.stderr.decode("utf-8", errors="replace")
    assert first.stderr == b""
    packet = parse_json_bytes(first.stdout)
    assert first.stdout == render_json(packet)
    assert packet["record_status"] == "observed"
    assert packet["producer"]["production_mode"] == "current_run_export"
    assert packet["producer"]["producer_source"] == TOOL_MODULE.WRAPPER_SOURCE_PATH
    assert packet["carrier"]["sha256"] == fixture["expectation"]["carrier"][
        "sha256"
    ]
    assert packet["carrier"]["size_bytes"] == fixture["expectation"]["carrier"][
        "size_bytes"
    ]
    assert packet["authority_boundary"] == (
        TOOL_MODULE.EXPECTED_PACKET_AUTHORITY_BOUNDARY
    )
    assert packet["content_boundary"] == (
        TOOL_MODULE.EXPECTED_PACKET_CONTENT_BOUNDARY
    )

    second = run_tool(
        *fixture["arguments"],
        "--output",
        str(fixture["output_path"]),
        tool=fixture["tool"],
        cwd=fixture["control_root"],
        timeout=600,
    )
    assert second.returncode == 0, second.stderr.decode("utf-8", errors="replace")
    assert second.stderr == b""
    assert second.stdout == first.stdout
    assert fixture["output_path"].read_bytes() == first.stdout
    residues = [
        path
        for path in fixture["output_path"].parent.iterdir()
        if path.name.startswith(f".{fixture['output_path'].name}.")
    ]
    assert residues == []


def test_complete_cli_fails_closed_on_expectation_digest_and_carrier_mutability(
    tmp_path: Path,
) -> None:
    digest_fixture = complete_fixture(tmp_path / "digest")
    arguments = list(digest_fixture["arguments"])
    index = arguments.index("--expectation-sha256") + 1
    arguments[index] = "0" * 64
    result = run_tool(
        *arguments,
        tool=digest_fixture["tool"],
        cwd=digest_fixture["control_root"],
        timeout=600,
    )
    assert result.returncode != 0
    assert result.stdout == b""
    diagnostic = parse_json_bytes(result.stderr)
    assert diagnostic["authority_effect"] == "none"
    assert any("expectation_sha256" in error for error in diagnostic["errors"])

    mode_fixture = complete_fixture(tmp_path / "mode")
    mode_fixture["carrier_path"].chmod(0o644)
    result = run_tool(
        *mode_fixture["arguments"],
        tool=mode_fixture["tool"],
        cwd=mode_fixture["control_root"],
        timeout=600,
    )
    assert result.returncode != 0
    assert result.stdout == b""
    diagnostic = parse_json_bytes(result.stderr)
    assert diagnostic["authority_effect"] == "none"
    assert any("write_bits" in error for error in diagnostic["errors"])


def test_missing_candidate_workflow_remains_a_fail_closed_activation_prerequisite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expectation = {
        "expectation_producer": {
            "producer_source": TOOL_MODULE.EXPECTATION_BUILDER_SOURCE_PATH,
            "producer_source_revision": "1" * 40,
            "producer_source_sha256": "2" * 64,
            "producer_version": "0.1.0",
            "production_mode": "current_run_expectation_builder",
        },
        "trusted_control_plane": {
            "components": {
                name: {
                    "path": path,
                    "sha256": "2" * 64,
                    "source_revision": "1" * 40,
                    "version": version,
                }
                for name, path, version in TOOL_MODULE.CONTROL_PLANE_COMPONENT_SPECS
            }
        },
    }

    def fake_blob(**kwargs: Any) -> Any:
        repository_path = kwargs["repository_path"]
        if repository_path == TOOL_MODULE.CONTROL_PLANE_WORKFLOW_SOURCE_PATH:
            raise TOOL_MODULE.WrapperError(
                "control_component_control_plane_workflow_object_missing",
                exit_kind="component_binding_error",
            )
        payload = b"synthetic\n"
        return TOOL_MODULE.VerifiedFile(
            role=kwargs["label"],
            repository_root=kwargs["repository_root"],
            revision=kwargs["revision"],
            repository_path=repository_path,
            path=kwargs["repository_root"] / repository_path,
            payload=payload,
            git_blob_sha1=git_blob_sha1(payload),
            sha256="2" * 64,
        )

    monkeypatch.setattr(TOOL_MODULE, "_verified_repository_blob", fake_blob)
    with pytest.raises(
        TOOL_MODULE.WrapperError,
        match="control_plane_workflow_object_missing",
    ):
        TOOL_MODULE._verify_control_plane_components(
            expectation=expectation,
            git_path=Path("/usr/bin/git"),
            control_root=tmp_path,
            control_revision="1" * 40,
        )


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
