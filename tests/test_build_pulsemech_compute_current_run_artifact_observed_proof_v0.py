#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = (
    ROOT
    / "tools"
    / "build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"
)
TOOLS_TESTS_MANIFEST = ROOT / "ci" / "tools-tests.list"
TEST_RELATIVE_PATH = (
    "tests/test_build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"
)
PREVIOUS_COMPUTE_REGRESSION = (
    "tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
)
FOLLOWING_COMPUTE_REGRESSION = (
    "tests/test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py"
)

EXPECTED_TOOL_LINES = 2908
EXPECTED_TOOL_BYTES = 106862
EXPECTED_TOOL_SHA256 = (
    "47fdfefb95fdd2e8484ee6c6b014df632c7942e34059998fd45c0378fe8fd2a1"
)
EXPECTED_TOOL_GIT_BLOB_SHA1 = "fa74cd02811587f24fcf81b717e72559e9f323e3"

EXPECTED_TESTS = frozenset(
    {
        "test_proof_builder_artifact_identity_matches_reviewed_head",
        "test_tools_tests_manifest_registers_proof_builder_regression_exactly_once",
        "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract",
        "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit",
        "test_direct_nonisolated_execution_fails_before_argument_parsing",
        "test_isolated_help_exposes_complete_cli_surface",
        "test_failure_diagnostic_and_boundaries_are_non_authoritative",
        "test_canonical_json_and_identity_helpers_fail_closed",
        "test_sanitized_environment_and_git_command_are_local_only",
        "test_bounded_process_rejects_stdout_overflow",
        "test_bounded_process_rejects_timeout",
        "test_repository_preflight_rejects_promisor_and_transport_configuration",
        "test_committed_worktree_binding_rehashes_object_and_rejects_drift",
        "test_directory_snapshot_requires_finalized_single_regular_files",
        "test_intake_directory_closes_exact_read_only_surface",
        "test_intake_directory_rejects_unexpected_member",
        "test_intake_binding_rejects_subject_control_and_producer_drift",
        "test_dynamic_plan_inputs_bind_current_subject_and_active_policy_sets",
        "test_report_validation_binds_subject_analysis_and_builder",
        "test_plan_validation_requires_exact_current_run_preserve_operation",
        "test_relation_validation_preserves_false_missing_and_unresolved_state",
        "test_relation_false_runtime_complete_claim_is_rejected",
        "test_materialization_preserves_false_candidate_values_in_separate_status",
        "test_materialization_rejects_gate_summary_or_folded_status_mismatch",
        "test_proof_manifest_closes_inputs_outputs_and_non_authority_boundary",
        "test_descriptor_relative_output_write_cannot_be_redirected",
        "test_directory_cleanup_refuses_attacker_substituted_path",
        "test_full_build_is_deterministic_checksum_closed_and_read_only",
        "test_full_build_preserves_false_unresolved_candidate_result",
        "test_full_build_failure_leaves_no_partial_or_stale_output",
        "test_postpublication_reverification_failure_removes_owned_output",
        "test_builder_invokes_only_existing_nonactive_chain_and_not_check_gates",
    }
)
EXPECTED_COLLECTED_TEST_ITEMS = len(EXPECTED_TESTS)
CRITICAL_TESTS = frozenset(
    {
        "test_proof_builder_artifact_identity_matches_reviewed_head",
        "test_repository_preflight_rejects_promisor_and_transport_configuration",
        "test_intake_directory_closes_exact_read_only_surface",
        "test_relation_validation_preserves_false_missing_and_unresolved_state",
        "test_materialization_preserves_false_candidate_values_in_separate_status",
        "test_descriptor_relative_output_write_cannot_be_redirected",
        "test_full_build_is_deterministic_checksum_closed_and_read_only",
        "test_full_build_preserves_false_unresolved_candidate_result",
        "test_full_build_failure_leaves_no_partial_or_stale_output",
        "test_postpublication_reverification_failure_removes_owned_output",
        "test_builder_invokes_only_existing_nonactive_chain_and_not_check_gates",
    }
)

_AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS = (
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_PLUGINS",
)
_AUTHORITATIVE_LAUNCH_PROBE_CHILD = (
    "PULSEMECH_STEP_3G_PROOF_BUILDER_REGRESSION_LAUNCH_PROBE_CHILD"
)


def _load_tool() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pulsemech_step_3g_artifact_observed_proof_builder_under_test",
        TOOL,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = _load_tool()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
        self._contract_satisfied = False

    @property
    def completed_successfully(self) -> bool:
        return self._contract_satisfied

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
                "authoritative_step_3g_proof_builder_collection_contract_mismatch: "
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
                "authoritative_step_3g_proof_builder_critical_items_missing: "
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
                "authoritative Step 3G artifact-observed proof-builder regression failed",
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


def canonical_json(value: Any) -> bytes:
    return M.render_json(value)


def captured(name: str, value: bytes) -> Any:
    return M.CapturedFile(
        name=name,
        bytes_value=value,
        sha256=sha256_bytes(value),
        size_bytes=len(value),
        inode_identity=(1, abs(hash(name)) % 100000 + 1),
        full_identity=(1, abs(hash(name)) % 100000 + 1, stat.S_IFREG | 0o444, 1, 0, 0, len(value), 1, 1),
    )


def component_binding(
    *,
    role: str,
    path: str,
    revision: str,
    value: bytes,
    root: Path,
) -> Any:
    target = root.joinpath(*Path(path).parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(value)
    target.chmod(0o444)
    return M.ComponentBinding(
        role=role,
        path=path,
        source_revision=revision,
        source_sha256=sha256_bytes(value),
        size_bytes=len(value),
        bytes_value=value,
        worktree_path=target,
    )


def make_component_sets(tmp_path: Path) -> dict[str, Any]:
    subject_root = tmp_path / "subject"
    control_root = tmp_path / "control"
    subject_root.mkdir(mode=0o700)
    control_root.mkdir(mode=0o700)
    subject_revision = "1" * 40
    control_revision = "2" * 40

    control_components: dict[str, Any] = {}
    for role, (path, _maximum) in M.CONTROL_COMPONENT_SPECS.items():
        if role == "proof_builder":
            value = TOOL.read_bytes()
        elif role.endswith("_schema"):
            value = canonical_json({"type": "object"})
        else:
            value = f"synthetic control component: {role}\n".encode("utf-8")
        control_components[role] = component_binding(
            role=role,
            path=path,
            revision=control_revision,
            value=value,
            root=control_root,
        )

    subject_components: dict[str, Any] = {}
    policy = (
        "version: 0.1.7\n"
        "gates:\n"
        "  required:\n"
        "    - required_gate_a\n"
        "  release_required:\n"
        "    - release_gate_b\n"
    ).encode("utf-8")
    for role, (path, _maximum) in M.SUBJECT_COMPONENT_SPECS.items():
        value = policy if role == "subject_policy" else f"subject: {role}\n".encode()
        subject_components[role] = component_binding(
            role=role,
            path=path,
            revision=subject_revision,
            value=value,
            root=subject_root,
        )

    return {
        "subject_root": subject_root,
        "control_root": control_root,
        "subject_revision": subject_revision,
        "control_revision": control_revision,
        "control_components": control_components,
        "subject_components": subject_components,
    }


def make_packet_and_expectation(parts: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    repository = "HKati/pulse-release-gates-0.1"
    run_id = 12345
    run_number = 77
    run_attempt = 2
    subject_run_key = (
        f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT={run_attempt}|"
        "GITHUB_WORKFLOW=PULSE CI"
    )
    base_status = {
        "created_utc": "2026-08-21T10:00:00Z",
        "gates": {"required_gate_a": True, "release_gate_b": True},
        "metrics": {"run_mode": "prod"},
        "version": "1",
    }
    base_status_bytes = canonical_json(base_status)
    subject = {
        "active_policy_sets": ["required", "release_required"],
        "decision": "ALLOW",
        "final_status_sha256": sha256_bytes(base_status_bytes),
        "materialized_gate_set_sha256": None,
        "policy_id": "pulse-gate-policy-v0",
        "policy_sha256": "3" * 64,
        "release_candidate_id": f"pulse-ci-current-run:{run_id}:{run_attempt}",
        "release_decision_sha256": "4" * 64,
        "repository": repository,
        "run_mode": "prod",
        "source_commit": parts["subject_revision"],
        "subject_run_key": subject_run_key,
        "workflow_name": "PULSE CI",
        "workflow_run_attempt": run_attempt,
        "workflow_run_id": run_id,
        "workflow_run_number": run_number,
    }
    packet = {
        "record_status": "observed",
        "role_bindings": {"final_status": "artifact:status"},
        "subject": subject,
    }
    expectation = {
        "record_status": "observed",
        "trusted_control_plane": {
            "repository": repository,
            "revision": parts["control_revision"],
        },
    }
    return packet, expectation


def write_read_only(path: Path, value: bytes) -> None:
    path.write_bytes(value)
    path.chmod(0o444)


def make_intake_fixture(tmp_path: Path, parts: Mapping[str, Any]) -> dict[str, Any]:
    packet, expectation = make_packet_and_expectation(parts)
    intake = tmp_path / "intake"
    intake.mkdir(mode=0o700)
    carrier_name = "pulsemech-current-run-export-12345-2-v0.zip"
    candidate_files: dict[str, bytes] = {
        M.CANDIDATE_MANIFEST_NAME: canonical_json({"candidate": "closed"}),
        M.CARRIER_METADATA_NAME: canonical_json({"carrier": "verified"}),
        M.EXPECTATION_NAME: canonical_json(expectation),
        M.PACKET_NAME: canonical_json(packet),
        M.SOURCE_RESOLUTION_NAME: canonical_json({"source": "resolved"}),
        M.SOURCE_SELECTION_NAME: canonical_json({"artifacts": "selected"}),
        carrier_name: b"synthetic finalized carrier bytes\n",
    }
    for name, value in candidate_files.items():
        write_read_only(intake / name, value)

    source_subject = {
        "release_candidate_id": packet["subject"]["release_candidate_id"],
        "repository": packet["subject"]["repository"],
        "source_run_attempt": packet["subject"]["workflow_run_attempt"],
        "source_run_id": packet["subject"]["workflow_run_id"],
        "source_run_key": packet["subject"]["subject_run_key"],
        "source_run_number": packet["subject"]["workflow_run_number"],
        "subject_revision": packet["subject"]["source_commit"],
        "workflow_name": M.SOURCE_WORKFLOW_NAME,
        "workflow_path": M.SOURCE_WORKFLOW_PATH,
    }
    loader = parts["control_components"]["candidate_bundle_loader"]
    rows = [
        {
            "path": name,
            "role": "finalized_carrier" if name == carrier_name else name.removesuffix(".json"),
            "sha256": sha256_bytes(value),
            "size_bytes": len(value),
        }
        for name, value in sorted(candidate_files.items())
    ]
    report = {
        "authority_boundary": dict(M.EXPECTED_INTAKE_AUTHORITY),
        "bundle_identity": {
            "candidate_manifest_sha256": sha256_bytes(
                candidate_files[M.CANDIDATE_MANIFEST_NAME]
            ),
            "candidate_manifest_size_bytes": len(
                candidate_files[M.CANDIDATE_MANIFEST_NAME]
            ),
            "carrier_name": carrier_name,
            "carrier_sha256": sha256_bytes(candidate_files[carrier_name]),
            "carrier_size_bytes": len(candidate_files[carrier_name]),
            "expectation_sha256": sha256_bytes(candidate_files[M.EXPECTATION_NAME]),
            "packet_sha256": sha256_bytes(candidate_files[M.PACKET_NAME]),
            "source_run_attempt": source_subject["source_run_attempt"],
            "source_run_id": source_subject["source_run_id"],
            "subject_revision": source_subject["subject_revision"],
        },
        "content_boundary": dict(M.EXPECTED_INTAKE_CONTENT),
        "document_type": (
            "pulsemech_compute_current_run_export_candidate_bundle_intake"
        ),
        "errors": [],
        "files": rows,
        "inner_carrier_verification": {"verified": True},
        "ok": True,
        "output_layout": {
            "intake_report_path": M.INTAKE_REPORT_NAME,
            "verified_candidate_files": sorted(candidate_files),
        },
        "producer": {
            "producer_id": (
                "producer:pulsemech-current-run-export-candidate-bundle-intake-v0"
            ),
            "producer_name": (
                "PULSEmech current-run export candidate bundle intake"
            ),
            "producer_source": loader.path,
            "producer_source_revision": parts["control_revision"],
            "producer_source_sha256": loader.source_sha256,
            "producer_version": "0.1.0",
            "production_mode": "current_run_export_candidate_bundle_intake",
        },
        "provider_binding": {
            "provider": "github_actions",
            "provider_artifact_id": "999",
        },
        "record_status": "observed",
        "schema_version": (
            "pulsemech_compute_current_run_export_candidate_bundle_intake_v0"
        ),
        "source_subject": source_subject,
    }
    report_bytes = canonical_json(report)
    write_read_only(intake / M.INTAKE_REPORT_NAME, report_bytes)
    intake.chmod(0o555)
    return {
        "intake": intake,
        "candidate_files": candidate_files,
        "report": report,
        "report_bytes": report_bytes,
        "packet": packet,
        "expectation": expectation,
        "base_status": {
            "created_utc": "2026-08-21T10:00:00Z",
            "gates": {"required_gate_a": True, "release_gate_b": True},
            "metrics": {"run_mode": "prod"},
            "version": "1",
        },
        "carrier_name": carrier_name,
    }


def make_chain_documents(parts: Mapping[str, Any], fixture: Mapping[str, Any]) -> dict[str, Any]:
    packet = fixture["packet"]
    subject = packet["subject"]
    analysis_run_key = "ANALYSIS_RUN=step-3g-artifact-observed-v0"
    producer_run_key = "PRODUCER_RUN=step-3g-artifact-observed-v0"
    report_subject = {
        "active_policy_sets": subject["active_policy_sets"],
        "decision": subject["decision"],
        "final_status_sha256": subject["final_status_sha256"],
        "materialized_gate_set_sha256": subject["materialized_gate_set_sha256"],
        "policy_id": subject["policy_id"],
        "policy_sha256": subject["policy_sha256"],
        "release_candidate_id": subject["release_candidate_id"],
        "release_decision_sha256": subject["release_decision_sha256"],
        "repository": subject["repository"],
        "run_mode": subject["run_mode"],
        "source_commit": subject["source_commit"],
        "workflow": subject["workflow_name"],
        "workflow_run_attempt": subject["workflow_run_attempt"],
        "workflow_run_id": subject["workflow_run_id"],
        "workflow_run_number": subject["workflow_run_number"],
    }
    report = {
        "analysis_boundary": {
            "analysis_level": "artifact_observed",
            "analysis_run_key": analysis_run_key,
            "subject_run_key": subject["subject_run_key"],
        },
        "compute_nodes": [{"node_id": "compute:check-gates"}],
        "edges": [],
        "errors": [],
        "findings": [],
        "inputs": [],
        "ok": True,
        "record_status": "observed",
        "report_type": "pulsemech_compute_binding_report",
        "resource_summary": {},
        "schema_version": "pulsemech_compute_binding_report_v0",
        "state_nodes": [],
        "subject": report_subject,
        "summary": {},
        "tool": {
            "id": "build_pulsemech_compute_binding_report_v0",
            "source_sha256": parts["control_components"][
                "fixed_report_builder"
            ].source_sha256,
            "version": "0.1.0",
        },
    }
    request, component_manifest = M._build_dynamic_plan_inputs(
        packet=packet,
        subject_components=parts["subject_components"],
    )
    check_gates = parts["subject_components"]["subject_check_gates"]
    plan = {
        "apply_eligible": True,
        "authority_boundary": {
            "changes_gate_policy": False,
            "changes_gate_semantics": False,
            "changes_release_authority": False,
            "creates_release_decision": False,
            "write_mode": "plan_only",
            "writes_target_repository": False,
        },
        "conflicts": [],
        "operations": [
            {
                "action": "preserve",
                "component_id": M.PLAN_COMPONENT_ID,
                "reason": "target file already matches source digest",
                "source_path": M.SUBJECT_CHECK_GATES_PATH,
                "source_sha256": check_gates.source_sha256,
                "source_size_bytes": check_gates.size_bytes,
                "target_path": M.SUBJECT_CHECK_GATES_PATH,
                "target_state": "identical",
            }
        ],
        "plan_type": "pulsemech_integration_plan",
        "request_id": request["request_id"],
        "schema_version": "pulsemech_integration_plan_v0",
        "selection": {
            "component_sets": [M.PLAN_COMPONENT_SET_ID],
            "declared_gate_sets": [],
            "resolved_components": [M.PLAN_COMPONENT_ID],
        },
        "source": {
            "component_manifest_path": "current-run-component-manifest.json",
            "component_manifest_sha256": sha256_bytes(
                canonical_json(component_manifest)
            ),
            "policy_path": M.SUBJECT_POLICY_PATH,
            "policy_sha256": subject["policy_sha256"],
            "repository": subject["repository"],
            "revision": subject["source_commit"],
        },
        "summary": {
            "conflict": 0,
            "create": 0,
            "files_total": 1,
            "preserve": 1,
            "source_missing": 0,
            "unresolved": 0,
        },
        "target": {
            "declared_ci_provider": "github_actions",
            "default_branch": "main",
            "detected_ci_providers": ["github_actions"],
            "repository_id": subject["repository"],
        },
        "tool": "plan_pulsemech_integration_v0",
        "unresolved": [],
    }
    relation = {
        "authority_boundary": dict(M.EXPECTED_RELATION_AUTHORITY),
        "comparison_boundary": {
            "observed_analysis_level": "artifact_observed",
        },
        "comparison_identity": {
            "relation_record_id": "planned-observed:synthetic/v0",
            "release_candidate_id": subject["release_candidate_id"],
            "subject_repository": subject["repository"],
            "subject_source_commit": subject["source_commit"],
        },
        "coverage": {
            "comparison_status": "partial",
            "runtime_observation_status": "absent",
            "unresolved_reasons": ["artifact_coverage_partial"],
        },
        "errors": [],
        "expectations": {"expectation:presence": {}},
        "findings": {
            "finding:comparison": {
                "finding_type": "comparison_coverage_partial",
                "severity": "advisory",
            }
        },
        "observation_bindings": {},
        "observations": {"observation:check-gates": {"coverage_status": "partial"}},
        "ok": True,
        "plan_binding": {"sha256": sha256_bytes(canonical_json(plan))},
        "record_status": "observed",
        "relation_type": "pulsemech_compute_planned_observed_relation",
        "relations": {
            "relation:check-gates": {
                "evaluation": {"coverage": "partial", "decisive": False},
                "relation_status": "unresolved_due_to_coverage",
            }
        },
        "schema_version": "pulsemech_compute_planned_observed_relation_v0",
        "summary": {
            "comparison_complete": False,
            "relations": 1,
            "unresolved_relations": 1,
        },
        "tool": {},
    }
    candidate_gates = {
        "compute_transition_path_complete": False,
        "compute_transition_authority_binding_ok": False,
        "compute_transition_unbound_mutation_absent": True,
    }
    materializer_report = {
        "candidate_all_true": False,
        "candidate_gate_set": M.CANDIDATE_GATE_SET,
        "candidate_gates": candidate_gates,
        "errors": [],
        "folded_gates": list(M.CANDIDATE_GATES),
        "ok": True,
        "output_status_written": True,
        "relation_validated": True,
        "tool": "fold_pulsemech_compute_planned_observed_relation_into_status_v0",
        "version": "0.1.0",
    }
    folded_status = copy.deepcopy(fixture["base_status"])
    folded_status["gates"].update(candidate_gates)
    return {
        "analysis_run_key": analysis_run_key,
        "producer_run_key": producer_run_key,
        "ci_identity": "Step 3G synthetic proof regression",
        "report": report,
        "request": request,
        "component_manifest": component_manifest,
        "plan": plan,
        "relation": relation,
        "candidate_gates": candidate_gates,
        "materializer_report": materializer_report,
        "folded_status": folded_status,
    }


def build_case(tmp_path: Path) -> dict[str, Any]:
    tmp_path.chmod(0o700)
    parts = make_component_sets(tmp_path)
    fixture = make_intake_fixture(tmp_path, parts)
    chain = make_chain_documents(parts, fixture)
    return {**parts, **fixture, **chain, "process_calls": []}


def namespace_for(case: Mapping[str, Any], output: Path) -> argparse.Namespace:
    return argparse.Namespace(
        intake_directory=str(case["intake"]),
        subject_root=str(case["subject_root"]),
        subject_repository="HKati/pulse-release-gates-0.1",
        subject_revision=case["subject_revision"],
        control_plane_root=str(case["control_root"]),
        control_plane_repository="HKati/pulse-release-gates-0.1",
        control_plane_revision=case["control_revision"],
        analysis_run_key=case["analysis_run_key"],
        producer_run_key=case["producer_run_key"],
        ci_workflow_or_job_identity=case["ci_identity"],
        output_directory=str(output),
        trusted_git=str(Path("/usr/bin/git")),
        subprocess_timeout_seconds=30,
        max_input_file_bytes=1024 * 1024,
    )


def patch_full_build(
    monkeypatch: pytest.MonkeyPatch,
    case: dict[str, Any],
    *,
    fail_process_label: str | None = None,
    fail_reverify_call: int | None = None,
) -> None:
    monkeypatch.setattr(M, "_select_trusted_git", lambda _explicit: Path("/usr/bin/git"))

    def verify_repository(*, root: Path, expected_revision: str, label: str, **_kw: Any) -> Path:
        resolved = Path(root).resolve()
        if label.startswith("subject"):
            assert expected_revision == case["subject_revision"]
            assert resolved == case["subject_root"].resolve()
        else:
            assert expected_revision == case["control_revision"]
            assert resolved == case["control_root"].resolve()
        return resolved

    monkeypatch.setattr(M, "_verify_repository", verify_repository)

    def verify_component_set(*, repository_root: Path, **_kw: Any) -> dict[str, Any]:
        if Path(repository_root).resolve() == case["control_root"].resolve():
            return case["control_components"]
        if Path(repository_root).resolve() == case["subject_root"].resolve():
            return case["subject_components"]
        raise AssertionError(repository_root)

    monkeypatch.setattr(M, "_verify_component_set", verify_component_set)
    reverify_calls = {"count": 0}

    def reverify_component_set(**_kw: Any) -> None:
        reverify_calls["count"] += 1
        if fail_reverify_call is not None and reverify_calls["count"] == fail_reverify_call:
            raise M.ProofError("synthetic_postpublication_component_drift")

    monkeypatch.setattr(M, "_reverify_component_set", reverify_component_set)
    monkeypatch.setattr(M, "_validate_json_schema", lambda **_kw: None)
    monkeypatch.setattr(
        M,
        "_extract_final_status",
        lambda **_kw: canonical_json(case["base_status"]),
    )

    def fake_process(
        command: list[str],
        *,
        label: str,
        **_kw: Any,
    ) -> Any:
        case["process_calls"].append((label, list(command)))
        if fail_process_label == label:
            raise M.ProofError(f"synthetic_process_failure: {label}")
        if label == "subject_input_report_bridge":
            return M.ProcessResult(0, canonical_json(case["report"]), b"")
        if label == "current_run_integration_planner":
            output = Path(command[command.index("--output") + 1])
            value = canonical_json(case["plan"])
            output.write_bytes(value)
            return M.ProcessResult(0, value, b"")
        if label == "planned_observed_relation_builder":
            output = Path(command[command.index("--output") + 1])
            value = canonical_json(case["relation"])
            output.write_bytes(value)
            return M.ProcessResult(0, value, b"")
        if label == "candidate_status_materializer":
            output = Path(command[command.index("--output") + 1])
            output.write_bytes(canonical_json(case["folded_status"]))
            return M.ProcessResult(
                0,
                canonical_json(case["materializer_report"]),
                b"",
            )
        raise AssertionError(label)

    monkeypatch.setattr(M, "_process_or_fail", fake_process)
    case["reverify_calls"] = reverify_calls


def make_output_rows() -> list[Any]:
    return [
        captured(name, canonical_json({"name": name}))
        for name in M.PROOF_PAYLOAD_NAMES
    ]


def restore_writable(path: Path) -> None:
    if not path.exists() or path.is_symlink():
        return
    if path.is_dir():
        path.chmod(0o700)
        for child in list(path.iterdir()):
            restore_writable(child)
        try:
            path.rmdir()
        except OSError:
            pass
    else:
        path.chmod(0o600)
        try:
            path.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Artifact, launcher and protected-runtime contract
# ---------------------------------------------------------------------------


def test_proof_builder_artifact_identity_matches_reviewed_head() -> None:
    payload = TOOL.read_bytes()
    assert len(payload.splitlines()) == EXPECTED_TOOL_LINES
    assert len(payload) == EXPECTED_TOOL_BYTES
    assert sha256_bytes(payload) == EXPECTED_TOOL_SHA256
    assert git_blob_sha1(payload) == EXPECTED_TOOL_GIT_BLOB_SHA1
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in payload
    assert b"\r" not in payload
    assert all(not line.endswith((b" ", b"\t")) for line in payload.splitlines())
    assert M.TOOL_NAME == "build_pulsemech_compute_current_run_artifact_observed_proof_v0"
    assert M.TOOL_VERSION == "0.1.0"
    assert M.SCHEMA_VERSION == "pulsemech_compute_current_run_artifact_observed_proof_v0"
    assert M.PRODUCER_SOURCE_PATH == TOOL.relative_to(ROOT).as_posix()


def test_tools_tests_manifest_registers_proof_builder_regression_exactly_once() -> None:
    entries = manifest_entries()
    assert len(entries) == len(set(entries))
    assert entries.count(TEST_RELATIVE_PATH) == 1
    index = entries.index(TEST_RELATIVE_PATH)
    assert entries[index - 1] == PREVIOUS_COMPUTE_REGRESSION
    assert entries[index + 1] == FOLLOWING_COMPUTE_REGRESSION


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
        timeout=300,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    expected = str(EXPECTED_COLLECTED_TEST_ITEMS).encode("ascii")
    assert b"collected " + expected + b" items" in result.stdout
    assert expected + b" passed" in result.stdout
    assert b"usage: pytest" not in result.stdout.lower()


def test_direct_nonisolated_execution_fails_before_argument_parsing() -> None:
    result = subprocess.run(
        [sys.executable, str(TOOL), "--help"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    diagnostic = json.loads(result.stderr.decode("utf-8"))
    assert diagnostic["authority_effect"] == "none"
    assert diagnostic["exit_kind"] == "python_runtime_boundary_error"
    assert diagnostic["ok"] is False


def test_isolated_help_exposes_complete_cli_surface() -> None:
    result = subprocess.run(
        [sys.executable, "-I", str(TOOL), "--help"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    text = result.stdout.decode("utf-8")
    for option in (
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
        "--trusted-git",
        "--subprocess-timeout-seconds",
        "--max-input-file-bytes",
    ):
        assert option in text


def test_failure_diagnostic_and_boundaries_are_non_authoritative() -> None:
    diagnostic = M.make_failure_diagnostic(
        error="synthetic failure",
        exit_kind="proof_error",
    )
    assert diagnostic == {
        "authority_effect": "none",
        "document_type": M.DOCUMENT_TYPE,
        "errors": ["synthetic failure"],
        "exit_kind": "proof_error",
        "ok": False,
        "tool": M.TOOL_NAME,
        "tool_version": M.TOOL_VERSION,
    }
    assert M.CLOSED_AUTHORITY_BOUNDARY["candidate_only"] is True
    assert M.CLOSED_AUTHORITY_BOUNDARY["non_active"] is True
    assert M.CLOSED_AUTHORITY_BOUNDARY["activates_compute_gate"] is False
    assert M.CLOSED_AUTHORITY_BOUNDARY["writes_subject_status"] is False
    assert M.CLOSED_AUTHORITY_BOUNDARY["changes_release_authority"] is False
    assert M.CLOSED_CONTENT_BOUNDARY["analysis_level"] == "artifact_observed"
    assert M.CLOSED_CONTENT_BOUNDARY["candidate_values_may_be_false"] is True
    assert M.CLOSED_CONTENT_BOUNDARY["missing_and_unresolved_states_preserved"] is True


def test_canonical_json_and_identity_helpers_fail_closed() -> None:
    rendered = M.render_json({"b": 2, "a": 1})
    assert rendered == b'{\n  "a": 1,\n  "b": 2\n}\n'
    assert M._parse_json_bytes(rendered, label="canonical", canonical_required=True) == {
        "a": 1,
        "b": 2,
    }
    with pytest.raises(M.StrictJsonError, match="duplicate_key"):
        M._parse_json_bytes(b'{"a":1,"a":2}\n', label="duplicate")
    with pytest.raises(M.StrictJsonError, match="not_canonical_json"):
        M._parse_json_bytes(b'{"b":2,"a":1}\n', label="noncanonical", canonical_required=True)
    with pytest.raises(M.ProofError, match="invalid_sha40"):
        M._canonical_sha40("A" * 40, label="revision")
    with pytest.raises(M.ProofError, match="unsafe_relative_path"):
        M._canonical_relative_path("../escape", label="path")


def test_sanitized_environment_and_git_command_are_local_only() -> None:
    git = Path("/usr/bin/git")
    root = Path("/tmp/example-repository")
    environment = M._sanitized_environment(trusted_git=git)
    assert environment["PATH"] == "/usr/bin"
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_ASKPASS"] == "/bin/false"
    assert environment["SSH_ASKPASS"] == "/bin/false"
    command = M._git_command(
        git=git,
        repository_root=root,
        arguments=("cat-file", "blob", "deadbeef"),
    )
    assert command[:4] == [
        "/usr/bin/git",
        "--no-pager",
        "--no-replace-objects",
        "--no-lazy-fetch",
    ]
    joined = "\n".join(command)
    for key, value in M.GIT_COMMAND_CONFIG:
        assert f"{key}={value}" in joined
    assert f"safe.directory={root}" in joined
    assert command[-3:] == ["cat-file", "blob", "deadbeef"]


def test_bounded_process_rejects_stdout_overflow(tmp_path: Path) -> None:
    with pytest.raises(M.ProofError, match="process_stdout_limit_exceeded"):
        M._run_bounded_process(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x'*4096)"],
            cwd=tmp_path,
            env=M._sanitized_environment(),
            timeout_seconds=10,
            max_stdout_bytes=1024,
            max_stderr_bytes=1024,
        )


def test_bounded_process_rejects_timeout(tmp_path: Path) -> None:
    started = time.monotonic()
    with pytest.raises(M.ProofError, match="process_timeout"):
        M._run_bounded_process(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            cwd=tmp_path,
            env=M._sanitized_environment(),
            timeout_seconds=1,
            max_stdout_bytes=1024,
            max_stderr_bytes=1024,
        )
    assert time.monotonic() - started < 4


def test_repository_preflight_rejects_promisor_and_transport_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    git_dir = root / ".git"
    git_dir.mkdir(parents=True)
    expected = "a" * 40

    def fake_run_git(*, arguments: tuple[str, ...], **_kw: Any) -> bytes:
        if arguments == ("rev-parse", "--show-toplevel"):
            return (str(root) + "\n").encode()
        if arguments == ("rev-parse", "HEAD"):
            return (expected + "\n").encode()
        if arguments == ("rev-parse", "--is-shallow-repository"):
            return b"false\n"
        if arguments == ("config", "--local", "--null", "--list"):
            return b"remote.origin.promisor\ntrue\x00core.sshCommand\n/tmp/evil\x00"
        if arguments == ("rev-parse", "--absolute-git-dir"):
            return (str(git_dir) + "\n").encode()
        raise AssertionError(arguments)

    monkeypatch.setattr(M, "_run_git", fake_run_git)
    with pytest.raises(M.ProofError, match="unsafe_git_config"):
        M._verify_repository(
            git=Path("/usr/bin/git"),
            root=root,
            expected_revision=expected,
            label="subject_repository",
        )


def test_committed_worktree_binding_rehashes_object_and_rejects_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    path = "tools/example.py"
    target = root / path
    target.parent.mkdir()
    payload = b"print('bound')\n"
    target.write_bytes(payload)
    revision = "b" * 40
    object_spec = f"{revision}:{path}"
    oid = M._blob_sha1(payload)

    def fake_run_git(*, arguments: tuple[str, ...], **_kw: Any) -> bytes:
        if arguments == ("cat-file", "-t", object_spec):
            return b"blob\n"
        if arguments == ("cat-file", "-s", object_spec):
            return f"{len(payload)}\n".encode()
        if arguments == ("cat-file", "blob", object_spec):
            return payload
        if arguments == ("rev-parse", object_spec):
            return (oid + "\n").encode()
        raise AssertionError(arguments)

    monkeypatch.setattr(M, "_run_git", fake_run_git)
    binding = M._verify_committed_worktree_file(
        git=Path("/usr/bin/git"),
        repository_root=root,
        revision=revision,
        repository_path=path,
        role="example",
        maximum=1024,
    )
    assert binding.source_sha256 == sha256_bytes(payload)
    target.write_bytes(b"drift\n")
    with pytest.raises(M.ProofError, match="committed_worktree_mismatch"):
        M._verify_committed_worktree_file(
            git=Path("/usr/bin/git"),
            repository_root=root,
            revision=revision,
            repository_path=path,
            role="example",
            maximum=1024,
        )


def test_directory_snapshot_requires_finalized_single_regular_files(tmp_path: Path) -> None:
    directory = tmp_path / "snapshot"
    directory.mkdir()
    writable = directory / "writable.txt"
    writable.write_text("writable", encoding="utf-8")
    with M.DirectorySnapshot(directory, label="snapshot") as snapshot:
        with pytest.raises(M.ProofError, match="not_finalized_read_only"):
            snapshot.capture_file("writable.txt", maximum=1024)
    writable.chmod(0o444)
    hardlink = directory / "hardlink.txt"
    os.link(writable, hardlink)
    with M.DirectorySnapshot(directory, label="snapshot") as snapshot:
        with pytest.raises(M.ProofError, match="not_single_regular"):
            snapshot.capture_file("writable.txt", maximum=1024)
    hardlink.unlink()


def test_intake_directory_closes_exact_read_only_surface(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    bundle = M._capture_intake_directory(case["intake"], maximum_file_bytes=1024 * 1024)
    assert bundle.carrier_name == case["carrier_name"]
    assert set(bundle.files) == {
        M.INTAKE_REPORT_NAME,
        M.CANDIDATE_MANIFEST_NAME,
        M.CARRIER_METADATA_NAME,
        M.EXPECTATION_NAME,
        M.PACKET_NAME,
        M.SOURCE_RESOLUTION_NAME,
        M.SOURCE_SELECTION_NAME,
        case["carrier_name"],
    }
    assert bundle.files[M.PACKET_NAME].bytes_value == canonical_json(case["packet"])


def test_intake_directory_rejects_unexpected_member(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    case["intake"].chmod(0o755)
    write_read_only(case["intake"] / "unexpected.json", canonical_json({"x": 1}))
    case["intake"].chmod(0o555)
    with pytest.raises(M.ProofError, match="intake_directory_closure_failed"):
        M._capture_intake_directory(case["intake"], maximum_file_bytes=1024 * 1024)


def test_intake_binding_rejects_subject_control_and_producer_drift(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    bundle = M._capture_intake_directory(case["intake"], maximum_file_bytes=1024 * 1024)
    expectation, packet = M._verify_intake_bindings(
        bundle=bundle,
        subject_repository="HKati/pulse-release-gates-0.1",
        subject_revision=case["subject_revision"],
        control_repository="HKati/pulse-release-gates-0.1",
        control_revision=case["control_revision"],
        components=case["control_components"],
    )
    assert expectation == case["expectation"]
    assert packet == case["packet"]
    with pytest.raises(M.ProofError, match="intake_subject_subject_revision_mismatch"):
        M._verify_intake_bindings(
            bundle=bundle,
            subject_repository="HKati/pulse-release-gates-0.1",
            subject_revision="9" * 40,
            control_repository="HKati/pulse-release-gates-0.1",
            control_revision=case["control_revision"],
            components=case["control_components"],
        )
    drifted = copy.deepcopy(bundle.intake_report)
    drifted["producer"]["producer_source_sha256"] = "0" * 64
    bad_bundle = M.InputBundle(
        intake_report=drifted,
        files=bundle.files,
        carrier_name=bundle.carrier_name,
        source_subject=bundle.source_subject,
    )
    with pytest.raises(M.ProofError, match="intake_producer_producer_source_sha256_mismatch"):
        M._verify_intake_bindings(
            bundle=bad_bundle,
            subject_repository="HKati/pulse-release-gates-0.1",
            subject_revision=case["subject_revision"],
            control_repository="HKati/pulse-release-gates-0.1",
            control_revision=case["control_revision"],
            components=case["control_components"],
        )


def test_dynamic_plan_inputs_bind_current_subject_and_active_policy_sets(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    request, manifest = M._build_dynamic_plan_inputs(
        packet=case["packet"],
        subject_components=case["subject_components"],
    )
    assert request["component_sets"] == [M.PLAN_COMPONENT_SET_ID]
    assert request["target_repository"]["repository_id"] == case["packet"]["subject"]["repository"]
    assert manifest["source_repository"] == case["packet"]["subject"]["repository"]
    assert manifest["component_sets"][0]["declared_gate_sets"] == [
        "required",
        "release_required",
    ]
    bad_packet = copy.deepcopy(case["packet"])
    bad_packet["subject"]["active_policy_sets"] = ["missing_set"]
    with pytest.raises(M.ProofError, match="subject_policy_gate_set_invalid"):
        M._build_dynamic_plan_inputs(
            packet=bad_packet,
            subject_components=case["subject_components"],
        )


def test_report_validation_binds_subject_analysis_and_builder(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    M._validate_report(
        case["report"],
        packet=case["packet"],
        components=case["control_components"],
        analysis_run_key=case["analysis_run_key"],
    )
    bad = copy.deepcopy(case["report"])
    bad["analysis_boundary"]["analysis_run_key"] = "wrong"
    with pytest.raises(M.ProofError, match="analysis_run_key_mismatch"):
        M._validate_report(
            bad,
            packet=case["packet"],
            components=case["control_components"],
            analysis_run_key=case["analysis_run_key"],
        )
    bad = copy.deepcopy(case["report"])
    bad["tool"]["source_sha256"] = "0" * 64
    with pytest.raises(M.ProofError, match="builder_source_mismatch"):
        M._validate_report(
            bad,
            packet=case["packet"],
            components=case["control_components"],
            analysis_run_key=case["analysis_run_key"],
        )


def test_plan_validation_requires_exact_current_run_preserve_operation(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    M._validate_plan(
        case["plan"],
        packet=case["packet"],
        request=case["request"],
        component_manifest=case["component_manifest"],
    )
    bad = copy.deepcopy(case["plan"])
    bad["operations"][0]["action"] = "create"
    with pytest.raises(M.ProofError, match="operation_action_mismatch"):
        M._validate_plan(
            bad,
            packet=case["packet"],
            request=case["request"],
            component_manifest=case["component_manifest"],
        )
    bad = copy.deepcopy(case["plan"])
    bad["source"]["component_manifest_sha256"] = "0" * 64
    with pytest.raises(M.ProofError, match="component_manifest_digest_mismatch"):
        M._validate_plan(
            bad,
            packet=case["packet"],
            request=case["request"],
            component_manifest=case["component_manifest"],
        )


def test_relation_validation_preserves_false_missing_and_unresolved_state(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    M._validate_relation(case["relation"], report=case["report"], plan=case["plan"])
    assert case["relation"]["coverage"]["comparison_status"] == "partial"
    assert case["relation"]["coverage"]["unresolved_reasons"] == [
        "artifact_coverage_partial"
    ]
    assert case["relation"]["summary"]["comparison_complete"] is False
    assert case["relation"]["findings"]["finding:comparison"]["finding_type"] == (
        "comparison_coverage_partial"
    )


def test_relation_false_runtime_complete_claim_is_rejected(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    bad = copy.deepcopy(case["relation"])
    bad["coverage"]["runtime_observation_status"] = "complete"
    with pytest.raises(M.ProofError, match="false_runtime_complete_claim"):
        M._validate_relation(bad, report=case["report"], plan=case["plan"])


def test_materialization_preserves_false_candidate_values_in_separate_status(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    gates = M._validate_materialization(
        report=case["materializer_report"],
        base_status=case["base_status"],
        folded_status=case["folded_status"],
    )
    assert gates == case["candidate_gates"]
    assert gates["compute_transition_path_complete"] is False
    assert gates["compute_transition_authority_binding_ok"] is False
    assert gates["compute_transition_unbound_mutation_absent"] is True
    assert set(case["base_status"]["gates"]) == {"required_gate_a", "release_gate_b"}


def test_materialization_rejects_gate_summary_or_folded_status_mismatch(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    bad_report = copy.deepcopy(case["materializer_report"])
    bad_report["candidate_all_true"] = True
    with pytest.raises(M.ProofError, match="all_true_mismatch"):
        M._validate_materialization(
            report=bad_report,
            base_status=case["base_status"],
            folded_status=case["folded_status"],
        )
    bad_status = copy.deepcopy(case["folded_status"])
    bad_status["gates"]["compute_transition_path_complete"] = True
    with pytest.raises(M.ProofError, match="folded_candidate_status_content_mismatch"):
        M._validate_materialization(
            report=case["materializer_report"],
            base_status=case["base_status"],
            folded_status=bad_status,
        )


def test_proof_manifest_closes_inputs_outputs_and_non_authority_boundary(tmp_path: Path) -> None:
    case = build_case(tmp_path)
    bundle = M._capture_intake_directory(case["intake"], maximum_file_bytes=1024 * 1024)
    manifest = M._make_proof_manifest(
        bundle=bundle,
        packet=case["packet"],
        report=case["report"],
        plan=case["plan"],
        relation=case["relation"],
        materializer_report=case["materializer_report"],
        candidate_gates=case["candidate_gates"],
        output_files=make_output_rows(),
        request=case["request"],
        component_manifest=case["component_manifest"],
        producer=case["control_components"]["proof_builder"],
        control_repository="HKati/pulse-release-gates-0.1",
        control_revision=case["control_revision"],
        analysis_run_key=case["analysis_run_key"],
        producer_run_key=case["producer_run_key"],
        ci_identity=case["ci_identity"],
    )
    assert manifest["authority_boundary"] == M.CLOSED_AUTHORITY_BOUNDARY
    assert manifest["content_boundary"] == M.CLOSED_CONTENT_BOUNDARY
    assert manifest["result"]["candidate_gates"] == case["candidate_gates"]
    assert manifest["result"]["candidate_all_true"] is False
    assert manifest["result"]["unresolved_reasons"] == ["artifact_coverage_partial"]
    assert manifest["output_layout"]["file_count"] == len(M.PROOF_PAYLOAD_NAMES)
    assert {row["path"] for row in manifest["output_layout"]["files"]} == set(
        M.PROOF_PAYLOAD_NAMES
    )


def test_descriptor_relative_output_write_cannot_be_redirected(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    parent.mkdir(mode=0o700)
    target = parent / "target"
    target.mkdir(mode=0o700)
    outside = parent / "outside"
    outside.mkdir(mode=0o700)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(target, flags)
    backup = parent / "target-moved"
    try:
        target.rename(backup)
        target.symlink_to(outside, target_is_directory=True)
        M._write_file_at(fd, "proof.json", canonical_json({"safe": True}), mode=0o444)
        assert not (outside / "proof.json").exists()
        assert (backup / "proof.json").read_bytes() == canonical_json({"safe": True})
    finally:
        os.close(fd)
        if target.is_symlink():
            target.unlink()
        restore_writable(backup)
        restore_writable(outside)


def test_directory_cleanup_refuses_attacker_substituted_path(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    parent.mkdir(mode=0o700)
    victim = parent / "victim"
    victim.mkdir(mode=0o700)
    identity = M._inode_identity(victim.stat())
    moved = parent / "moved"
    outside = parent / "outside"
    outside.mkdir(mode=0o700)
    victim.rename(moved)
    victim.symlink_to(outside, target_is_directory=True)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        M._remove_directory_by_fd(parent_fd, "victim", expected_identity=identity)
    finally:
        os.close(parent_fd)
    assert victim.is_symlink()
    assert moved.is_dir()
    assert outside.is_dir()
    victim.unlink()
    restore_writable(moved)
    restore_writable(outside)


def test_full_build_is_deterministic_checksum_closed_and_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_case(tmp_path)
    patch_full_build(monkeypatch, case)
    publication_source_modes: list[int] = []
    M._require_supported_execution_platform()
    monkeypatch.setattr(M, "_require_supported_execution_platform", lambda: None)
    real_rename = M.os.rename

    def checked_publication_rename(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> None:
        if source == "proof":
            source_metadata = os.stat(
                source,
                dir_fd=src_dir_fd,
                follow_symlinks=False,
            )
            source_mode = stat.S_IMODE(source_metadata.st_mode)
            publication_source_modes.append(source_mode)
            assert source_mode & stat.S_IWUSR
        real_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(M.os, "rename", checked_publication_rename)
    first = tmp_path / "proof-first"
    second = tmp_path / "proof-second"
    rendered_first = M._build(namespace_for(case, first))
    rendered_second = M._build(namespace_for(case, second))
    assert rendered_first == rendered_second
    assert publication_source_modes == [0o700, 0o700]
    manifest = json.loads(rendered_first.decode("utf-8"))
    assert manifest["ok"] is True
    assert manifest["authority_boundary"] == M.CLOSED_AUTHORITY_BOUNDARY
    assert manifest["output_layout"]["file_count"] == 5
    for output in (first, second):
        assert stat.S_IMODE(output.stat().st_mode) == 0o555
        names = {path.name for path in output.iterdir()}
        assert names == set(M.PROOF_PAYLOAD_NAMES) | {M.PROOF_MANIFEST_NAME}
        for path in output.iterdir():
            assert path.is_file() and not path.is_symlink()
            assert stat.S_IMODE(path.stat().st_mode) == 0o444
        stored = json.loads((output / M.PROOF_MANIFEST_NAME).read_text(encoding="utf-8"))
        for row in stored["output_layout"]["files"]:
            value = (output / row["path"]).read_bytes()
            assert row["sha256"] == sha256_bytes(value)
            assert row["size_bytes"] == len(value)


def test_full_build_preserves_false_unresolved_candidate_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_case(tmp_path)
    patch_full_build(monkeypatch, case)
    output = tmp_path / "proof"
    manifest = json.loads(M._build(namespace_for(case, output)).decode("utf-8"))
    result = manifest["result"]
    assert result["candidate_all_true"] is False
    assert result["candidate_gates"] == case["candidate_gates"]
    assert result["relation_comparison_status"] == "partial"
    assert result["unresolved_reasons"] == ["artifact_coverage_partial"]
    assert result["finding_types"] == ["comparison_coverage_partial"]
    folded = json.loads((output / M.FOLDED_STATUS_NAME).read_text(encoding="utf-8"))
    assert folded["gates"]["compute_transition_path_complete"] is False
    assert folded["gates"]["compute_transition_authority_binding_ok"] is False
    assert folded["gates"]["compute_transition_unbound_mutation_absent"] is True


def test_full_build_failure_leaves_no_partial_or_stale_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_case(tmp_path)
    patch_full_build(
        monkeypatch,
        case,
        fail_process_label="planned_observed_relation_builder",
    )
    output = tmp_path / "failed-proof"
    with pytest.raises(M.ProofError, match="synthetic_process_failure"):
        M._build(namespace_for(case, output))
    assert not output.exists()
    assert not any(path.name.startswith(".failed-proof.") for path in tmp_path.iterdir())


def test_postpublication_reverification_failure_removes_owned_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_case(tmp_path)
    patch_full_build(monkeypatch, case, fail_reverify_call=3)
    unlink_parent_modes: list[int] = []
    M._require_supported_execution_platform()
    monkeypatch.setattr(M, "_require_supported_execution_platform", lambda: None)
    real_unlink = M.os.unlink

    def checked_cleanup_unlink(
        path: str,
        *,
        dir_fd: int,
    ) -> None:
        parent_mode = stat.S_IMODE(os.fstat(dir_fd).st_mode)
        unlink_parent_modes.append(parent_mode)
        assert parent_mode & stat.S_IWUSR
        real_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(M.os, "unlink", checked_cleanup_unlink)
    output = tmp_path / "postpublish-proof"
    with pytest.raises(M.ProofError, match="synthetic_postpublication_component_drift"):
        M._build(namespace_for(case, output))
    assert case["reverify_calls"]["count"] == 3
    assert unlink_parent_modes
    assert all(mode & stat.S_IWUSR for mode in unlink_parent_modes)
    assert not output.exists()
    assert not any(path.name.startswith(".postpublish-proof.") for path in tmp_path.iterdir())


def test_builder_invokes_only_existing_nonactive_chain_and_not_check_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = build_case(tmp_path)
    patch_full_build(monkeypatch, case)
    output = tmp_path / "proof"
    M._build(namespace_for(case, output))
    labels = [label for label, _command in case["process_calls"]]
    assert labels == [
        "subject_input_report_bridge",
        "current_run_integration_planner",
        "planned_observed_relation_builder",
        "candidate_status_materializer",
    ]
    commands = [item for _label, command in case["process_calls"] for item in command]
    assert M.SUBJECT_CHECK_GATES_PATH not in commands
    assert all("check_gates.py" not in item for item in commands)
    assert "--runtime-packet" not in commands
    assert M.CLOSED_AUTHORITY_BOUNDARY["activates_compute_gate"] is False
    assert M.CLOSED_AUTHORITY_BOUNDARY["materializes_active_gate_state"] is False
    assert M.CLOSED_AUTHORITY_BOUNDARY["writes_subject_status"] is False


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
