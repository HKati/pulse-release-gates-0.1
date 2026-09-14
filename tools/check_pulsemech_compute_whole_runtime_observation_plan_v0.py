#!/usr/bin/env python3
"""Independently validate a Step 5C whole-runtime prelaunch plan.

The checker reads one externally identified plan, validates its canonical bytes
and schema, reconstructs the complete expected prelaunch graph from exact Git
objects, and requires byte-for-byte equality with that independent
reconstruction.  It does not import or execute the plan builder, call GitHub,
dispatch workflows, observe runtime activity, mutate status, materialize gates,
or create release authority.

Run with isolated Python on Linux::

    python -I tools/check_pulsemech_compute_whole_runtime_observation_plan_v0.py \
      --repository-root . \
      --plan /path/to/prelaunch-plan.json \
      --expected-source-commit <40-hex commit> \
      --expected-plan-sha256 <64-hex digest> \
      --expected-record-status observed

A deterministic diagnostic JSON document is written to stdout.  No output path
is opened or replaced by this tool.
"""
from __future__ import annotations

import sys

if __name__ == "__main__" and not (
    sys.flags.isolated == 1
    and sys.flags.ignore_environment == 1
    and sys.flags.no_user_site == 1
    and getattr(sys.flags, "safe_path", False)
):
    sys.stderr.write(
        '{"authority_effect":"none","error_code":"isolated_python_required",'
        '"ok":false,"tool":"check_pulsemech_compute_whole_runtime_observation_plan_v0"}\n'
    )
    raise SystemExit(2)

import argparse
import ast
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml


TOOL_ID = "build_pulsemech_compute_whole_runtime_observation_plan_v0"
TOOL_VERSION = "0.1.0"
CHECKER_TOOL_ID = "check_pulsemech_compute_whole_runtime_observation_plan_v0"
CHECKER_TOOL_VERSION = "0.1.0"
CHECK_DIAGNOSTIC_VERSION = "pulsemech_compute_whole_runtime_observation_plan_check_v0"
MAX_PLAN_BYTES = 16 * 1024 * 1024
EXECUTED_CHECKER_PATH = Path(__file__).absolute()
SCHEMA_VERSION = "pulsemech_compute_whole_runtime_observation_evidence_v0"
RECORD_TYPE = "prelaunch_plan"
PROFILE = "pulse_ci_hosted_release_grade_v0"
SCOPE = "one_current_run_pulse_ci_hosted_release_grade_declared_workflow_graph_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
SOURCE_REF = "refs/heads/main"
SOURCE_RELEASE_CANDIDATE = "main"
EVIDENCE_CANDIDATE_TEMPLATE = "pulse-ci-current-run:{workflow_run_id}:1"

SUBJECT_WORKFLOW_PATH = ".github/workflows/pulse_ci.yml"
PROVIDER_WORKFLOW_PATH = (
    ".github/workflows/pulsemech_compute_current_run_export_candidate.yml"
)
REFERENCE_WORKFLOW_PATH = (
    ".github/workflows/pulsemech_compute_whole_runtime_observation_reference.yml"
)
CONTRACT_PATH = (
    "docs/compute/PULSEMECH_COMPUTE_WHOLE_RUNTIME_OBSERVATION_CONTRACT_v0.md"
)
SCHEMA_PATH = (
    "schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json"
)
BUILDER_PATH = "tools/build_pulsemech_compute_whole_runtime_observation_plan_v0.py"
PLAN_CHECKER_PATH = "tools/check_pulsemech_compute_whole_runtime_observation_plan_v0.py"
ACQUIRE_PATH = "tools/acquire_pulsemech_compute_whole_runtime_observation_v0.py"
CAPTURE_PATH = "tools/capture_pulsemech_compute_whole_runtime_observation_v0.py"
VERIFIER_PATH = "tools/check_pulsemech_compute_whole_runtime_observation_v0.py"

RUNTIME_SCHEMA_PATH = "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json"
RUNTIME_VALIDATOR_PATH = "tools/check_pulsemech_compute_runtime_observation_packet_v0.py"
SUBJECT_INPUT_SCHEMA_PATH = "schemas/pulsemech_compute_subject_input_packet_v0.schema.json"
SUBJECT_INPUT_VALIDATOR_PATH = "tools/check_pulsemech_compute_subject_input_packet_v0.py"
CURRENT_RUN_EXPECTATION_BUILDER_PATH = (
    "tools/build_pulsemech_compute_current_run_export_expectation_v0.py"
)
CURRENT_RUN_CARRIER_LOADER_PATH = (
    "tools/load_pulsemech_compute_current_run_export_carrier_v0.py"
)
CURRENT_RUN_SUBJECT_INPUT_BUILDER_PATH = (
    "tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py"
)
CURRENT_RUN_BUNDLE_LOADER_PATH = (
    "tools/load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
)
CURRENT_RUN_ARTIFACT_PROOF_BUILDER_PATH = (
    "tools/build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"
)
BINDING_BRIDGE_PATH = "tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py"
ANALYZER_CORE_PATH = "tools/pulsemech_compute_binding_analyzer_core_v0.py"
BINDING_REPORT_SCHEMA_PATH = "schemas/pulsemech_compute_binding_report_v0.schema.json"
BINDING_REPORT_VALIDATOR_PATH = "tools/check_pulsemech_compute_binding_report_v0.py"
RELATION_BUILDER_PATH = "tools/build_pulsemech_compute_planned_observed_relation_v0.py"
RELATION_SCHEMA_PATH = "schemas/pulsemech_compute_planned_observed_relation_v0.schema.json"
RELATION_VALIDATOR_PATH = "tools/check_pulsemech_compute_planned_observed_relation_v0.py"
CANDIDATE_MATERIALIZER_PATH = "tools/fold_pulsemech_compute_planned_observed_relation_into_status_v0.py"

POLICY_PATH = "pulse_gate_policy_v0.yml"
REGISTRY_PATH = "pulse_gate_registry_v0.yml"
EXTERNAL_SIGNER_POLICY_PATH = "policy/external_signers_v1.yml"
THRESHOLD_POLICY_PATH = "PULSE_safe_pack_v0/profiles/external_thresholds.yaml"
LLAMAGUARD_DATASET_PATH = (
    "PULSE_safe_pack_v0/examples/llamaguard_current_run_cases_v0.jsonl"
)
LLAMAGUARD_RUNNER_PATH = "PULSE_safe_pack_v0/tools/run_llamaguard_current_evidence_v0.py"
LLAMAGUARD_REQUIREMENTS_PATH = "PULSE_safe_pack_v0/requirements-llamaguard-v0.txt"
REQUIREMENTS_PATH = "requirements.txt"

# The selected v0 topology is intentionally tied to these reviewed subject
# surfaces.  Adding Step 5C files changes the commit but must not silently
# change either subject workflow, the Step 3F provider, or the controlled case
# set.  A future change requires a reviewed profile revision.
EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1 = "adae42c8e9777d357ab5400ced5765de7059ed1e"
EXPECTED_PROVIDER_WORKFLOW_BLOB_SHA1 = "79e4a355cc1eab4af26f6b16e7563424e67d05f2"
EXPECTED_DATASET_BLOB_SHA1 = "3b6ca799f26c7374334c51c5c9c8ea26b35cf857"
EXPECTED_LLAMAGUARD_RUNNER_BLOB_SHA1 = "058edf0d16383db41a5a4500caf4b484321d2e57"

EXPECTED_MODEL_ID = "meta-llama/Llama-Guard-3-1B"
EXPECTED_MODEL_REVISION = "acf7aafa60f0410f8f42b1fa35e077d705892029"

API_VERSION = "2026-03-10"
API_ACCEPT = "application/vnd.github+json"
SUBJECT_DISPATCH_ENDPOINT = (
    "repos/HKati/pulse-release-gates-0.1/actions/workflows/pulse_ci.yml/dispatches"
)
PROVIDER_DISPATCH_ENDPOINT = (
    "repos/HKati/pulse-release-gates-0.1/actions/workflows/"
    "pulsemech_compute_current_run_export_candidate.yml/dispatches"
)

FINITE_LIMITS = {
    "api_request_timeout_seconds": 60,
    "subject_wait_seconds": 5400,
    "provider_wait_seconds": 2700,
    "max_jobs": 64,
    "max_platform_step_records": 2048,
    "max_artifacts": 256,
    "max_api_json_bytes": 16 * 1024 * 1024,
    "max_single_artifact_bytes": 768 * 1024 * 1024,
    "max_aggregate_artifact_bytes": 1536 * 1024 * 1024,
    "max_capture_members": 8192,
    "max_capture_uncompressed_bytes": 2048 * 1024 * 1024,
}

EXPECTED_CASE_IDS = (
    "benign_factual_response",
    "violent_harm_refusal",
    "credential_theft_refusal",
    "private_address_refusal",
    "self_harm_support",
    "hate_content_refusal",
)

PULSE_STEP_NAMES = (
    "Checkout",
    "ci guard single run_all invocation",
    "Enforce changelog for semantic changes",
    "Install system deps",
    "Set up Python",
    "Install Python deps",
    "Prepare pack dir (workspace)",
    "CI pack layout preflight (fail-closed on release-grade)",
    "Run pack gating pipeline",
    "release-grade reset candidate evidence outputs",
    "release-grade record current-run required-gate evidence",
    "Upload release-grade required-gate diagnostics",
    "release-grade build non-stubbed prod candidate status",
    "Preserve baseline status.json (pre-augment)",
    "ci: schema validate status_baseline.json (status_v1)",
    "ci: require prod run_mode on release-grade runs",
    "release-grade initialize current-run evidence identity",
    "release-grade build self-contained PULSE evidence floor",
    "upload self-contained PULSE evidence floor",
    "release-grade initialize LlamaGuard runtime identity",
    "release-grade install pinned LlamaGuard runtime",
    "release-grade produce current-run LlamaGuard raw evidence",
    "release-grade build canonical LlamaGuard summary",
    "release-grade upload current-run LlamaGuard evidence",
    "Show main status.json (head)",
    "Compute external evidence list (for snapshot)",
    "Export baseline summary for snapshot (pre-augment)",
    "Update artifacts for snapshot",
    "Write separation overlay and summary",
    "Show separation-phase overlay",
    "Write audit-metric summary",
    "Show audit-metric summary",
    "Write refusal-delta summary",
    "Show refusal-delta summary",
    "Strict external evidence: require external summaries present (pre-augment, fail-closed)",
    "release-grade pre-attestation artifact postconditions",
    "Upload release-grade pre-attestation pulse artifacts",
    "Augment status (external + top-level flags)",
    "ci: schema validate status.json (status_v1)",
    "Re-render Quality Ledger from final status",
    "Export final summary (post-augment)",
    "ci: forbid demo status on version tags",
    "Build release authority manifest (audit-only)",
    "Upload release authority manifest (audit-only)",
    "Summarize release authority manifest (audit-only)",
    "Insert release authority manifest section into Quality Ledger (audit-only)",
    "Stage release authority audit bundle (audit-only)",
    "Upload release authority audit bundle (audit-only)",
    "ci: enforce gates via check_gates (policy-derived)",
    "Gate registry sync check",
    "Policy ↔ registry consistency check",
    "Compute stability map",
    "Render stability map",
    "Compute field-level stability",
    "Compute field-level gating scores",
    "Compute EPF overlay",
    "Generate PULSE snapshot report (HTML)",
    "Generate PULSE snapshot report (Markdown)",
    "Write PULSE summary",
    "Prepare overlay outputs",
    "Export overlay HTML summary",
    "Copy overlay HTML to report root",
    "Write status.json key-order diagnosis (for debugging)",
    "Write separation-phase report (HTML)",
    "Write separation-phase report (Markdown)",
    "Write separation-phase per-gate matrix",
    "Write separation-phase per-gate matrix (MD)",
    "Generate separation-phase overlay for snapshot",
    "Release-grade artifact postconditions",
    "Release decision v0: materialize artifact",
    "Release decision v0: render ledger section",
    "Release decision v0: compose report card",
    "Release authority artifact binding v0: materialize and verify",
    "Upload release authority artifact binding v0",
    "Upload release decision v0 artifact bundle",
    "Release decision v0: summarize artifact",
    "Export JUnit and SARIF from final status",
    "Check release-grade reference run qualification (advisory)",
    "Quality Ledger / status parity",
    "mark release-grade reference parity state",
    "assemble release-grade reference bundle",
    "upload release-grade reference bundle",
    "Upload artifacts",
)

CORE_ATTEST_STEP_NAMES = (
    "Download verified release authority artifact binding",
    "Attest release authority artifact binding v0",
)

LLAMAGUARD_ATTEST_STEP_NAMES = (
    "Checkout",
    "Set up Python",
    "Install Python deps for LlamaGuard attestation envelope",
    "Download current-run LlamaGuard evidence",
    "Attest canonical LlamaGuard summary",
    "Build canonical LlamaGuard external-summary envelope",
    "Verify canonical LlamaGuard external-summary attestation",
    "Upload attested LlamaGuard external evidence",
)

RECORDED_PATH_STEP_NAMES = (
    "Checkout",
    "Set up Python",
    "Install Python deps for release-grade recorded path",
    "Download pre-attestation pulse artifacts",
    "Download attested LlamaGuard external evidence",
    "release-grade build verifier-facing candidate envelopes",
    "release-grade build release-evidence input manifest",
    "release-grade verify recorded release evidence",
    "release-grade materialize release-required from verifier",
    "ci: validate release-grade status contract (post-materialization)",
    "ci: forbid stubbed status on release-grade runs (post-materialization)",
    "release-grade enforce required and release-required gates via check_gates",
    "Render final release-grade Quality Ledger",
    "Export final release-grade status summary",
    "Materialize final release decision v0",
    "Render final release decision ledger section",
    "Build and verify final release authority manifest",
    "Insert final release authority manifest into Quality Ledger",
    "Compose final release decision report",
    "Verify final Quality Ledger and status parity",
    "Materialize and verify final release authority artifact binding",
    "Stage final release authority audit bundle",
    "Export final release-grade JUnit and SARIF",
    "Check release-grade reference run qualification (advisory)",
    "Assemble advisory release-grade reference bundle",
    "Release-grade final artifact postconditions",
    "Upload final release authority manifest",
    "Upload final release authority audit bundle",
    "Upload final release authority artifact binding",
    "Upload final release decision v0 artifact bundle",
    "Upload final pulse report",
    "Upload advisory release-grade reference bundle",
    "Upload release-grade recorded path artifacts",
)

RELEASE_ATTEST_STEP_NAMES = (
    "Download final release-grade artifact binding",
    "Attest final release-grade artifact binding v0",
)

ASSEMBLE_PACKAGE_STEP_NAMES = (
    "Checkout",
    "Set up Python",
    "Install Python deps for package assembly",
    "Download package assembly inputs",
    "Assemble complete release-grade reference package",
    "Upload complete release-grade reference package",
)

VERIFY_PACKAGE_STEP_NAMES = (
    "Checkout",
    "Set up Python",
    "Install Python deps for package verification",
    "Download complete release-grade reference package",
    "Check release-grade package completeness",
    "Upload release-grade package completeness report",
    "Verify complete release-grade reference package",
    "Upload release-grade reference package verification report",
)

TOOLS_TEST_STEP_NAMES = (
    "Checkout",
    "Set up Python",
    "Install Python deps (tools-tests)",
    "Run exporter + release-authority smoke tests",
    "Run targeted pytest suite",
)

EXPECTED_JOB_ORDER = (
    "pulse",
    "attest_release_authority_artifact_binding",
    "attest_llamaguard_current_run_summary",
    "release_grade_recorded_path",
    "attest_release_grade_artifact_binding",
    "assemble_release_grade_reference_package",
    "verify_release_grade_reference_package",
    "tools-tests",
)

EXPECTED_JOB_STEPS = {
    "pulse": PULSE_STEP_NAMES,
    "attest_release_authority_artifact_binding": CORE_ATTEST_STEP_NAMES,
    "attest_llamaguard_current_run_summary": LLAMAGUARD_ATTEST_STEP_NAMES,
    "release_grade_recorded_path": RECORDED_PATH_STEP_NAMES,
    "attest_release_grade_artifact_binding": RELEASE_ATTEST_STEP_NAMES,
    "assemble_release_grade_reference_package": ASSEMBLE_PACKAGE_STEP_NAMES,
    "verify_release_grade_reference_package": VERIFY_PACKAGE_STEP_NAMES,
    "tools-tests": TOOLS_TEST_STEP_NAMES,
}

EXPECTED_JOB_RESULTS = {
    job_id: ("skipped" if job_id == "attest_release_authority_artifact_binding" else "success")
    for job_id in EXPECTED_JOB_ORDER
}

PULSE_SUCCESS_ORDINALS = (
    frozenset(range(1, 9))
    | frozenset(range(10, 38))
    | frozenset({39, 50, 51})
)


# Reviewed semantics used by the recorded-evidence/status source projection.
_RECORDED_SEMANTIC_PINS = {
    'PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py':
        '6dcf6826d2c04143b86c7f7b6dfd6c8c43d028f7',
    'PULSE_safe_pack_v0/tools/build_release_evidence_input_manifest_v0.py':
        '95b457754514c0dea7ede27cd8b3204cf26f0a01',
    'PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py':
        '561e72a8e2ea2d25faa2a80cbecf025192435c38',
    'PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py':
        'a86aef9f2f5ccc6bb95997ee93eb6f9f95a8b85d',
    'PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py':
        '4298b7644acb0d8f7c50bbbac5308fb5038a501a',
    'PULSE_safe_pack_v0/tools/check_gates.py':
        '2a593bdef31c9c8cb565b1c4ca3d16a1e3093735',
    'tools/policy_to_require_args.py':
        '5b1d099485d0e3bfd90da3fff1213a4e949db850',
    'tools/validate_status_schema.py':
        'f329f882805615402a9fed99f67d4e7667891c06',
    'ci/check_release_no_stub_status.py':
        'edc5ac6899be5037188440e8d97267c25536cfc6',
}

SOURCE_ROLES = (
    ("subject_workflow", SUBJECT_WORKFLOW_PATH),
    ("provider_workflow", PROVIDER_WORKFLOW_PATH),
    ("reference_workflow", REFERENCE_WORKFLOW_PATH),
    ("normative_contract", CONTRACT_PATH),
    ("evidence_schema", SCHEMA_PATH),
    ("plan_builder", BUILDER_PATH),
    ("plan_checker", PLAN_CHECKER_PATH),
    ("acquisition_tool", ACQUIRE_PATH),
    ("capture_tool", CAPTURE_PATH),
    ("whole_runtime_verifier", VERIFIER_PATH),
    ("runtime_packet_schema", RUNTIME_SCHEMA_PATH),
    ("runtime_packet_validator", RUNTIME_VALIDATOR_PATH),
    ("subject_input_schema", SUBJECT_INPUT_SCHEMA_PATH),
    ("subject_input_validator", SUBJECT_INPUT_VALIDATOR_PATH),
    ("current_run_expectation_builder", CURRENT_RUN_EXPECTATION_BUILDER_PATH),
    ("current_run_carrier_loader", CURRENT_RUN_CARRIER_LOADER_PATH),
    ("current_run_subject_input_builder", CURRENT_RUN_SUBJECT_INPUT_BUILDER_PATH),
    ("current_run_bundle_loader", CURRENT_RUN_BUNDLE_LOADER_PATH),
    ("current_run_artifact_observed_proof_builder", CURRENT_RUN_ARTIFACT_PROOF_BUILDER_PATH),
    ("binding_bridge", BINDING_BRIDGE_PATH),
    ("binding_analyzer_core", ANALYZER_CORE_PATH),
    ("binding_report_schema", BINDING_REPORT_SCHEMA_PATH),
    ("binding_report_validator", BINDING_REPORT_VALIDATOR_PATH),
    ("planned_observed_relation_builder", RELATION_BUILDER_PATH),
    ("planned_observed_relation_schema", RELATION_SCHEMA_PATH),
    ("planned_observed_relation_validator", RELATION_VALIDATOR_PATH),
    ("candidate_materializer", CANDIDATE_MATERIALIZER_PATH),
    ("gate_policy", POLICY_PATH),
    ("gate_registry", REGISTRY_PATH),
    ("external_signer_policy", EXTERNAL_SIGNER_POLICY_PATH),
    ("threshold_policy", THRESHOLD_POLICY_PATH),
    ("llamaguard_case_dataset", LLAMAGUARD_DATASET_PATH),
    ("llamaguard_runner", LLAMAGUARD_RUNNER_PATH),
    ("llamaguard_runtime_requirements", LLAMAGUARD_REQUIREMENTS_PATH),
    ("repository_requirements", REQUIREMENTS_PATH),
    ('ledger_inplace_semantics', 'PULSE_safe_pack_v0/tools/insert_release_authority_manifest_ledger_section.py'),
    ('report_composer_semantics', 'PULSE_safe_pack_v0/tools/insert_release_decision_ledger_section.py'),
    ('ledger_parity_semantics', 'PULSE_safe_pack_v0/tools/check_quality_ledger_status_parity.py'),
    ("recorded_candidate_builder_semantics", 'PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py'),
    ("recorded_manifest_builder_semantics", 'PULSE_safe_pack_v0/tools/build_release_evidence_input_manifest_v0.py'),
    ("recorded_evidence_verifier_semantics", 'PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py'),
    ("release_required_materializer_semantics", 'PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py'),
    ("candidate_status_origin_semantics", 'PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py'),
    ("release_gate_checker_semantics", 'PULSE_safe_pack_v0/tools/check_gates.py'),
    ("policy_argument_derivation_semantics", 'tools/policy_to_require_args.py'),
    ("release_status_schema_guard_semantics", 'tools/validate_status_schema.py'),
    ("release_no_stub_guard_semantics", 'ci/check_release_no_stub_status.py'),
    ('package_assembler_semantics', 'PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py'),
    ('package_verifier_semantics', 'PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py'),
    ('package_completeness_semantics', 'tools/check_release_grade_package_complete_v1.py'),
)

AUTHORITY_BOUNDARY = {
    "authority_effect": "none",
    "same_run_release_authority_eligible": False,
    "active_gate_eligible": False,
    "changes_gate_policy": False,
    "changes_gate_registry": False,
    "changes_release_authority": False,
    "creates_compute_budget": False,
    "introduces_resource_measurement": False,
    "observer_in_subject_totals": False,
    "subject_artifacts_mutated": False,
    "writes_subject_status": False,
}

PRIVACY_BOUNDARY = {
    "raw_environment_included": False,
    "secret_values_included": False,
    "authorization_headers_included": False,
    "cookies_included": False,
    "request_bodies_included": False,
    "response_bodies_included": False,
    "raw_prompt_text_included": False,
    "raw_model_output_included": False,
    "private_or_arbitrary_user_prompt_admitted": False,
    "opaque_controlled_fixture_payloads_present": True,
    "redaction_applied": False,
    "redaction_rules_sha256": None,
}

TRUST_BOUNDARY = {
    "trusted_components": [
        "step5c_supervisor",
        "step5c_plan_builder",
        "step5c_plan_checker",
        "step5c_acquisition_tool",
        "step5c_capture_tool",
        "step5c_verifier",
        "cpython_runtime",
        "github_hosted_runner",
        "host_kernel",
        "github_control_plane",
        "pulse_ci_components",
        "step3f_components",
    ],
    "not_proven": [
        "privileged_host_integrity",
        "runner_image_integrity",
        "interpreter_integrity_against_privileged_host",
        "observer_integrity_against_privileged_host",
        "github_control_plane_integrity",
        "provider_internal_execution",
        "complete_network_activity",
        "complete_package_manager_activity",
    ],
}

RESULT_BOUNDARY = {
    "I_target": "complete",
    "E_target": "complete",
    "R_after_step5c": "partial",
    "C_after_step5c": "not_complete",
    "M_after_step5c": "unavailable",
    "generic_runtime_coverage": "partial",
}

LIFECYCLE_BOUNDARY = {
    "included_in_extent": False,
    "raw_records_preserved": True,
    "may_replace_declared_step": False,
    "matching_mode": "narrow_reviewed_allowlist",
    "allowed_classes": [
        "set_up_job",
        "post_action_cleanup",
        "complete_job",
    ],
}

TERMINAL_COUNTS = {
    "job_templates": 8,
    "successful_jobs": 7,
    "permitted_skipped_jobs": 1,
    "step_templates": 147,
    "instantiated_steps": 145,
    "successful_steps": 101,
    "permitted_skipped_steps": 44,
    "uninstantiated_steps": 2,
    "model_inference_occurrences": 6,
}

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
PLAN_ID_RE = re.compile(r"^step5c-plan:[A-Za-z0-9._:-]+$")
REPOSITORY_PATH_RE = re.compile(
    r"^(?!/)(?!.*(?:^|/)\.{1,2}(?:/|$))(?!.*\\)(?!.*\x00)"
    r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$"
)
ACTION_USES_RE = re.compile(
    r"^(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@"
    r"(?P<sha>[0-9a-f]{40})$"
)


class PlanError(RuntimeError):
    """Fail-closed plan construction error carrying a stable code."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code if detail is None else f"{code}: {detail}")
        self.code = code
        self.detail = detail


class StrictJsonError(PlanError):
    pass


class UniqueBaseLoader(yaml.BaseLoader):
    """BaseLoader variant that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: UniqueBaseLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise PlanError("duplicate_yaml_key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueBaseLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class GitObject:
    role: str
    path: str
    revision: str
    mode: str
    blob_sha1: str
    data: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    @property
    def executable(self) -> bool:
        return self.mode == "100755"

    def descriptor(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "path": self.path,
            "revision": self.revision,
            "git_blob_sha1": self.blob_sha1,
            "sha256": self.sha256,
            "size_bytes": len(self.data),
            "executable": self.executable,
        }


@dataclass
class PlanBuildContext:
    source_commit: str
    source_by_path: dict[str, GitObject]
    jobs: list[dict[str, Any]]
    step_by_key: dict[tuple[str, int], dict[str, Any]]
    external_operations: list[dict[str, Any]]
    model_inferences: list[dict[str, Any]]
    state_templates: list[dict[str, Any]]


def _require(condition: bool, code: str, detail: str | None = None) -> None:
    if not condition:
        raise PlanError(code, detail)


def _sha1_git_blob(data: bytes) -> str:
    framed = f"blob {len(data)}\0".encode("ascii") + data
    try:
        return hashlib.sha1(framed, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(framed).hexdigest()


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    _require_canonical_tree(value)
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


def _require_canonical_tree(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, bool) or type(value) is int:
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PlanError("non_finite_number", path)
        raise PlanError("fractional_number_not_allowed", path)
    if isinstance(value, str):
        _require(unicodedata.normalize("NFC", value) == value, "non_nfc_string", path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_canonical_tree(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _require(isinstance(key, str), "non_string_json_key", path)
            _require(unicodedata.normalize("NFC", key) == key, "non_nfc_json_key", path)
            _require_canonical_tree(item, f"{path}.{key}")
        return
    raise PlanError("unsupported_json_value", f"{path}: {type(value).__name__}")


def _strict_json_object(data: bytes, *, label: str) -> dict[str, Any]:
    _require(not data.startswith(b"\xef\xbb\xbf"), "json_bom_rejected", label)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise StrictJsonError("duplicate_json_key", label)
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise StrictJsonError("non_finite_json_number", f"{label}: {value}")

    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
            parse_constant=invalid_constant,
        )
    except PlanError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise StrictJsonError("invalid_json", label) from exc
    _require(isinstance(value, dict), "json_object_required", label)
    _require_canonical_tree(value, label)
    return value


def _git_environment(root: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "HOME": str(root),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
    }


def _git(root: Path, args: list[str], *, timeout: int = 30) -> bytes:
    try:
        result = subprocess.run(
            ["/usr/bin/git", "--no-replace-objects", "-C", str(root), *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
            env=_git_environment(root),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PlanError("git_execution_failed", " ".join(args)) from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace")[:512]
        raise PlanError("git_command_failed", f"{' '.join(args)}: {detail!r}")
    return result.stdout


def _validate_repository_root(value: Path) -> Path:
    root = Path(os.path.abspath(os.fspath(value)))
    _require(root.is_dir(), "repository_root_not_directory", str(root))
    _require(not root.is_symlink(), "repository_root_symlink_rejected", str(root))
    _require((root / ".git").exists(), "git_repository_required", str(root))
    return root


def _validate_source_commit(value: str) -> str:
    normalized = value.strip().lower()
    _require(SHA40_RE.fullmatch(normalized) is not None, "source_commit_not_sha40")
    return normalized


def _validate_plan_id(value: str) -> str:
    _require(PLAN_ID_RE.fullmatch(value) is not None, "plan_id_invalid")
    _require(len(value) <= 256, "plan_id_too_long")
    return value


def _read_git_object(
    root: Path,
    source_commit: str,
    *,
    role: str,
    path: str,
) -> GitObject:
    _require(REPOSITORY_PATH_RE.fullmatch(path) is not None, "unsafe_source_path", path)
    listing = _git(root, ["ls-tree", "-z", source_commit, "--", path])
    _require(listing.endswith(b"\0"), "source_tree_entry_missing", path)
    _require(listing.count(b"\0") == 1, "source_tree_entry_not_unique", path)
    entry = listing[:-1]
    try:
        metadata, encoded_path = entry.split(b"\t", 1)
        mode, object_type, blob_sha = metadata.decode("ascii").split(" ")
        decoded_path = encoded_path.decode("utf-8", errors="strict")
    except (ValueError, UnicodeError) as exc:
        raise PlanError("source_tree_entry_malformed", path) from exc
    _require(decoded_path == path, "source_tree_path_mismatch", path)
    _require(object_type == "blob", "source_not_blob", path)
    _require(mode in {"100644", "100755"}, "source_not_regular_file", path)
    _require(SHA40_RE.fullmatch(blob_sha) is not None, "source_blob_sha_invalid", path)
    data = _git(root, ["cat-file", "blob", blob_sha], timeout=60)
    _require(0 < len(data) <= 8 * 1024 * 1024, "source_size_out_of_range", path)
    _require(_sha1_git_blob(data) == blob_sha, "source_blob_identity_mismatch", path)
    return GitObject(
        role=role,
        path=path,
        revision=source_commit,
        mode=mode,
        blob_sha1=blob_sha,
        data=data,
    )


def _load_sources(root: Path, source_commit: str) -> dict[str, GitObject]:
    source_by_path: dict[str, GitObject] = {}
    roles: set[str] = set()
    for role, path in SOURCE_ROLES:
        _require(role not in roles, "duplicate_source_role", role)
        _require(path not in source_by_path, "duplicate_source_path", path)
        roles.add(role)
        source_by_path[path] = _read_git_object(
            root,
            source_commit,
            role=role,
            path=path,
        )

    exact_pins = {
        SUBJECT_WORKFLOW_PATH: EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1,
        PROVIDER_WORKFLOW_PATH: EXPECTED_PROVIDER_WORKFLOW_BLOB_SHA1,
        LLAMAGUARD_DATASET_PATH: EXPECTED_DATASET_BLOB_SHA1,
        LLAMAGUARD_RUNNER_PATH: EXPECTED_LLAMAGUARD_RUNNER_BLOB_SHA1,
        'PULSE_safe_pack_v0/tools/insert_release_authority_manifest_ledger_section.py': '80fc10a2d6fc564091d6954159dbe6afbb1b6a37',
        'PULSE_safe_pack_v0/tools/insert_release_decision_ledger_section.py': '5f0b8b43fa839dd6734edae265199bb5136b95ef',
        'PULSE_safe_pack_v0/tools/check_quality_ledger_status_parity.py': 'd65d9e13d0fe66c72f876c002f66156b16df4374',
    }
    exact_pins.update(_RECORDED_SEMANTIC_PINS)
    exact_pins.update(_PACKAGE_SEMANTIC_PINS)
    for path, expected in exact_pins.items():
        actual = source_by_path[path].blob_sha1
        _require(actual == expected, "reviewed_source_profile_mismatch", f"{path}: {actual}")
    return source_by_path


def _parse_yaml_document(data: bytes, *, label: str) -> dict[str, Any]:
    _require(not data.startswith(b"\xef\xbb\xbf"), "yaml_bom_rejected", label)
    try:
        value = yaml.load(
            data.decode("utf-8", errors="strict"),
            Loader=UniqueBaseLoader,
        )
    except PlanError:
        raise
    except (UnicodeError, yaml.YAMLError, RecursionError) as exc:
        raise PlanError("invalid_yaml", label) from exc
    _require(isinstance(value, dict), "yaml_object_required", label)
    return value


def _as_string(value: Any, *, label: str) -> str:
    _require(isinstance(value, str) and value != "", "non_empty_string_required", label)
    _require(unicodedata.normalize("NFC", value) == value, "non_nfc_string", label)
    return value


def _nullable_string(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _as_string(value, label=label)


def _normalize_needs(value: Any, *, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        result = [value]
    else:
        _require(isinstance(value, list), "job_needs_invalid", label)
        result = [_as_string(item, label=label) for item in value]
    _require(len(result) == len(set(result)), "job_needs_duplicate", label)
    return result


def _step_id(job_id: str, ordinal: int) -> str:
    return f"execution:step5c:step:{job_id}:{ordinal:03d}"


def _job_id(job_id: str) -> str:
    return f"execution:step5c:job:{job_id}"


def _collector_id() -> str:
    return "execution:step5c:collector:post-run-platform-export"


def _step_expected_result(job_id: str, ordinal: int) -> tuple[bool, str]:
    if job_id == "attest_release_authority_artifact_binding":
        return False, "not_instantiated"
    if job_id == "pulse":
        return True, "success" if ordinal in PULSE_SUCCESS_ORDINALS else "skipped"
    return True, "success"


def _shell_kind(value: Any) -> str:
    if value is None:
        return "bash"
    text = _as_string(value, label="step.shell").strip()
    first = text.split()[0]
    aliases = {
        "bash": "bash",
        "python": "python",
        "python3": "python",
        "pwsh": "pwsh",
        "powershell": "pwsh",
        "sh": "sh",
    }
    _require(first in aliases, "unsupported_step_shell", text)
    return aliases[first]


def _action_source(uses: str) -> dict[str, Any]:
    match = ACTION_USES_RE.fullmatch(uses)
    _require(match is not None, "github_action_not_full_sha_pinned", uses)
    sha = match.group("sha")
    return {
        "kind": "github_action",
        "uses": uses,
        "action_repository": match.group("repository"),
        "action_ref": sha,
        "action_commit_sha": sha,
    }


def _shell_source(step: dict[str, Any]) -> dict[str, Any]:
    run = _as_string(step.get("run"), label="step.run")
    return {
        "kind": "shell",
        "shell": _shell_kind(step.get("shell")),
        "run_sha256": hashlib.sha256(run.encode("utf-8")).hexdigest(),
        "raw_command_included": False,
    }


def _classify_action_operation(uses: str) -> str:
    repository = uses.split("@", 1)[0].lower()
    if repository == "actions/checkout":
        return "github_checkout_action"
    if repository == "actions/setup-python":
        return "github_setup_python_action"
    if repository == "actions/upload-artifact":
        return "github_artifact_upload"
    if repository == "actions/download-artifact":
        return "github_artifact_download"
    if repository.startswith("actions/attest"):
        return "github_attestation_action"
    return "other"


def _operation_id(job_id: str, ordinal: int, role: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._+-]+", "-", role).strip("-")
    return f"call:step5c:{job_id}:{ordinal:03d}:{safe}"


def _add_operation(
    operations: dict[str, dict[str, Any]],
    *,
    call_id: str,
    operation_class: str,
    owner: str,
    parent_occurrence_id: str | None,
    required: bool,
    capture_requirement: str,
) -> str:
    record = {
        "call_id": call_id,
        "operation_class": operation_class,
        "owner": owner,
        "parent_occurrence_id": parent_occurrence_id,
        "required": required,
        "capture_requirement": capture_requirement,
        "authorization_material_included": False,
        "cookies_included": False,
    }
    previous = operations.get(call_id)
    if previous is not None:
        _require(previous == record, "external_operation_identity_conflict", call_id)
    operations[call_id] = record
    return call_id


def _step_external_operations(
    *,
    job_id: str,
    ordinal: int,
    step: dict[str, Any],
    occurrence_id: str,
    expected_runtime_presence: bool,
    operations: dict[str, dict[str, Any]],
) -> list[str]:
    operation_ids: list[str] = []
    required = expected_runtime_presence
    uses = step.get("uses")
    run = step.get("run")

    if isinstance(uses, str):
        operation_class = _classify_action_operation(uses)
        operation_ids.append(
            _add_operation(
                operations,
                call_id=_operation_id(job_id, ordinal, operation_class),
                operation_class=operation_class,
                owner="subject",
                parent_occurrence_id=occurrence_id,
                required=required,
                capture_requirement="metadata_only",
            )
        )

    if isinstance(run, str):
        lower = run.lower()
        detected: list[tuple[str, str]] = []
        if "apt-get " in lower or "apt-get\n" in lower:
            detected.append(("system_package_installation", "system-packages"))
        if "pip install" in lower or "python -m pip" in lower:
            detected.append(("python_package_installation", "python-packages"))
        if "gh run download" in lower:
            detected.append(("github_artifact_download", "gh-artifact-download"))
        if "gh api" in lower:
            if "/artifacts" in lower:
                detected.append(("github_artifact_listing", "gh-artifact-listing"))
            else:
                detected.append(("github_run_metadata_retrieval", "gh-api"))
        if job_id == "pulse" and ordinal == 22:
            detected.extend(
                [
                    ("huggingface_model_revision_lookup", "hf-revision"),
                    ("huggingface_model_file_acquisition", "hf-model-files"),
                ]
            )
        seen_classes: set[tuple[str, str]] = set()
        for operation_class, role in detected:
            key = (operation_class, role)
            if key in seen_classes:
                continue
            seen_classes.add(key)
            operation_ids.append(
                _add_operation(
                    operations,
                    call_id=_operation_id(job_id, ordinal, role),
                    operation_class=operation_class,
                    owner="subject",
                    parent_occurrence_id=occurrence_id,
                    required=required,
                    capture_requirement=(
                        "not_recorded"
                        if operation_class
                        in {
                            "system_package_installation",
                            "python_package_installation",
                            "huggingface_model_file_acquisition",
                        }
                        else "metadata_only"
                    ),
                )
            )

    return sorted(operation_ids)


def _build_jobs(
    workflow: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[tuple[str, int], dict[str, Any]], list[dict[str, Any]]]:
    _require(workflow.get("name") == "PULSE CI", "subject_workflow_name_mismatch")
    jobs_value = workflow.get("jobs")
    _require(isinstance(jobs_value, dict), "subject_workflow_jobs_missing")
    actual_order = tuple(str(key) for key in jobs_value)
    _require(actual_order == EXPECTED_JOB_ORDER, "subject_job_order_mismatch")

    operations: dict[str, dict[str, Any]] = {}
    jobs: list[dict[str, Any]] = []
    step_by_key: dict[tuple[str, int], dict[str, Any]] = {}

    for job_ordinal, job_id in enumerate(EXPECTED_JOB_ORDER, start=1):
        raw_job = jobs_value.get(job_id)
        _require(isinstance(raw_job, dict), "subject_job_not_object", job_id)
        raw_steps = raw_job.get("steps")
        _require(isinstance(raw_steps, list), "subject_job_steps_missing", job_id)
        expected_names = EXPECTED_JOB_STEPS[job_id]
        _require(len(raw_steps) == len(expected_names), "subject_step_count_mismatch", job_id)

        built_steps: list[dict[str, Any]] = []
        for step_ordinal, (raw_step, expected_name) in enumerate(
            zip(raw_steps, expected_names, strict=True),
            start=1,
        ):
            _require(isinstance(raw_step, dict), "subject_step_not_object", expected_name)
            name = _as_string(raw_step.get("name"), label=f"{job_id}.step[{step_ordinal}].name")
            _require(name == expected_name, "subject_step_name_mismatch", f"{job_id}:{step_ordinal}")
            has_uses = isinstance(raw_step.get("uses"), str)
            has_run = isinstance(raw_step.get("run"), str)
            _require(has_uses ^ has_run, "step_requires_exactly_one_source", name)
            source = (
                _action_source(_as_string(raw_step.get("uses"), label=f"{name}.uses"))
                if has_uses
                else _shell_source(raw_step)
            )
            expected_presence, expected_result = _step_expected_result(job_id, step_ordinal)
            occurrence_id = _step_id(job_id, step_ordinal)
            external_operation_ids = _step_external_operations(
                job_id=job_id,
                ordinal=step_ordinal,
                step=raw_step,
                occurrence_id=occurrence_id,
                expected_runtime_presence=expected_presence,
                operations=operations,
            )
            model_inference_ids = (
                [f"inference:step5c:llamaguard:{case_id}" for case_id in EXPECTED_CASE_IDS]
                if job_id == "pulse" and step_ordinal == 22
                else []
            )
            built = {
                "occurrence_id": occurrence_id,
                "source_ordinal": step_ordinal,
                "name": name,
                "if_expression": _nullable_string(
                    raw_step.get("if"),
                    label=f"{job_id}.step[{step_ordinal}].if",
                ),
                "expected_runtime_presence": expected_presence,
                "expected_terminal_result": expected_result,
                "source": source,
                "external_operation_ids": external_operation_ids,
                "model_inference_ids": model_inference_ids,
                "input_state_ids": [],
                "output_state_ids": [],
            }
            built_steps.append(built)
            step_by_key[(job_id, step_ordinal)] = built

        jobs.append(
            {
                "occurrence_id": _job_id(job_id),
                "source_ordinal": job_ordinal,
                "source_job_id": job_id,
                "display_name": _as_string(
                    raw_job.get("name", job_id),
                    label=f"{job_id}.name",
                ),
                "needs": _normalize_needs(raw_job.get("needs"), label=f"{job_id}.needs"),
                "if_expression": _nullable_string(raw_job.get("if"), label=f"{job_id}.if"),
                "expected_terminal_result": EXPECTED_JOB_RESULTS[job_id],
                "steps": built_steps,
            }
        )

    # Supervisor and provider operations are outside the subject graph.
    collector = _collector_id()
    supervisor_operations = (
        ("subject-dispatch", "github_workflow_dispatch", True, "metadata_only"),
        ("subject-run-metadata", "github_run_metadata_retrieval", True, "metadata_only"),
        ("subject-job-metadata", "github_job_metadata_retrieval", True, "metadata_only"),
        ("subject-artifact-listing", "github_artifact_listing", True, "metadata_only"),
        ("subject-artifact-download", "github_artifact_download", True, "exact_digest"),
        ("provider-dispatch", "github_workflow_dispatch", True, "metadata_only"),
        ("provider-run-metadata", "github_run_metadata_retrieval", True, "metadata_only"),
        ("provider-artifact-listing", "github_artifact_listing", True, "metadata_only"),
        ("provider-artifact-download", "github_artifact_download", True, "exact_digest"),
        ("reference-artifact-upload", "github_artifact_upload", True, "metadata_only"),
    )
    for role, operation_class, required, capture_requirement in supervisor_operations:
        _add_operation(
            operations,
            call_id=f"call:step5c:supervisor:{role}",
            operation_class=operation_class,
            owner="supervisor",
            parent_occurrence_id=collector,
            required=required,
            capture_requirement=capture_requirement,
        )
    _add_operation(
        operations,
        call_id="call:step5c:provider:artifact-upload",
        operation_class="github_artifact_upload",
        owner="provider",
        parent_occurrence_id=None,
        required=True,
        capture_requirement="metadata_only",
    )

    return jobs, step_by_key, [operations[key] for key in sorted(operations)]


def _python_constant(data: bytes, *, name: str, label: str) -> str:
    try:
        tree = ast.parse(data.decode("utf-8", errors="strict"), filename=label, mode="exec")
    except (UnicodeError, SyntaxError) as exc:
        raise PlanError("python_source_parse_failed", label) from exc
    values: list[str] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == name for target in targets):
            continue
        value_node = node.value
        if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
            values.append(value_node.value)
    _require(len(values) == 1, "python_constant_not_unique", f"{label}:{name}")
    return values[0]


def _load_case_ids(data: bytes) -> tuple[str, ...]:
    _require(not data.startswith(b"\xef\xbb\xbf"), "dataset_bom_rejected")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise PlanError("dataset_utf8_invalid") from exc
    case_ids: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        _require(raw_line.strip() != "", "dataset_blank_line", str(line_number))
        record = _strict_json_object(raw_line.encode("utf-8"), label=f"dataset_line_{line_number}")
        _require(set(record) == {"case_id", "input", "output"}, "dataset_field_set_mismatch", str(line_number))
        case_id = _as_string(record.get("case_id"), label=f"dataset_line_{line_number}.case_id")
        _as_string(record.get("input"), label=f"dataset_line_{line_number}.input")
        _as_string(record.get("output"), label=f"dataset_line_{line_number}.output")
        _require(case_id not in case_ids, "dataset_case_id_duplicate", case_id)
        case_ids.append(case_id)
    result = tuple(case_ids)
    _require(result == EXPECTED_CASE_IDS, "dataset_case_order_mismatch")
    return result


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _bind_step_states(
    step_by_key: dict[tuple[str, int], dict[str, Any]],
    *,
    inputs: Iterable[tuple[str, int, str]] = (),
    outputs: Iterable[tuple[str, int, str]] = (),
) -> None:
    for job_id, ordinal, state_id in inputs:
        step = step_by_key[(job_id, ordinal)]
        _append_unique(step["input_state_ids"], state_id)
    for job_id, ordinal, state_id in outputs:
        step = step_by_key[(job_id, ordinal)]
        _append_unique(step["output_state_ids"], state_id)


def _state(
    *,
    state_id: str,
    state_type: str,
    role: str,
    path_or_uri: str,
    required: bool,
    content_requirement: str,
    producer: str | None,
    consumers: Iterable[str] = (),
    authority_bearing: bool,
    mutation_class: str,
) -> dict[str, Any]:
    return {
        "state_id": state_id,
        "state_type": state_type,
        "role": role,
        "path_or_uri": path_or_uri,
        "required": required,
        "content_requirement": content_requirement,
        "producer_occurrence_id": producer,
        "required_consumer_occurrence_ids": sorted(set(consumers)),
        "authority_bearing": authority_bearing,
        "mutation_class": mutation_class,
    }


# Independent source equations for the ledger/report mapping. No value in this
# projection is obtained from the builder's state table or generated plan.
def _checked_mapping_path(text: str, *, allow_temp: bool = False) -> str:
    _require(isinstance(text, str) and len(text) > 0, "source_mapping_path_invalid")
    roots = (("${PACK_DIR}/", "PULSE_safe_pack_v0/"),
             ("${{ env.PACK_DIR }}/", "PULSE_safe_pack_v0/"),
             ("${GITHUB_WORKSPACE}/", ""), ("$GITHUB_WORKSPACE/", ""))
    for prefix, replacement in roots:
        if text.startswith(prefix):
            text = replacement + text[len(prefix):]
            break
    tail = text
    if allow_temp and text.startswith("${RUNNER_TEMP}/"):
        tail = text[len("${RUNNER_TEMP}/"):]
    _require(re.fullmatch(r"[A-Za-z0-9_./-]+", tail) is not None,
             "source_mapping_dynamic_path", text)
    _require(not tail.startswith("/") and all(p not in ("", ".", "..") for p in tail.split("/")),
             "source_mapping_path_invalid", text)
    return text


def _checked_mapping_invocation(raw_steps: list[dict[str, Any]], tool: str) -> tuple[int, dict[str, str]]:
    matches: list[tuple[int, dict[str, str]]] = []
    for ordinal, step in enumerate(raw_steps, 1):
        source = step.get("run")
        if not isinstance(source, str):
            continue
        for line in source.replace("\\\n", " ").splitlines():
            if not re.match(r"^\s*python(?:3)?\s+", line):
                continue
            try:
                tokens = shlex.split(line, comments=False, posix=True)
            except ValueError as exc:
                raise PlanError("source_mapping_command_invalid", tool) from exc
            if len(tokens) < 2 or not tokens[1].endswith("/" + tool):
                continue
            _require(_checked_mapping_path(tokens[1]) == "PULSE_safe_pack_v0/tools/" + tool,
                     "source_mapping_tool_path_mismatch", tool)
            arguments = tokens[2:]
            _require(len(arguments) % 2 == 0, "source_mapping_argument_shape", tool)
            options: dict[str, str] = {}
            for key, value in zip(arguments[::2], arguments[1::2], strict=True):
                _require(re.fullmatch(r"--[a-z][a-z0-9_-]*", key) is not None
                         and key not in options and not value.startswith("--"),
                         "source_mapping_argument_shape", tool)
                options[key] = value
            matches.append((ordinal, options))
    _require(len(matches) == 1, "source_mapping_command_not_unique", tool)
    allowed_options = {
        "render_quality_ledger.py": {"--status", "--out"},
        "status_to_summary.py": {"--status", "--out_md", "--out_json"},
        "materialize_release_decision.py": {"--status", "--policy", "--target", "--out", "--status-schema"},
        "render_release_decision_ledger_section.py": {"--input", "--schema", "--out"},
        "build_release_authority_manifest_v0.py": {"--status", "--policy", "--registry", "--evaluator", "--policy-set", "--out", "--workflow-name", "--event-name", "--ref", "--git-sha"},
        "insert_release_authority_manifest_ledger_section.py": {"--report", "--manifest", "--href"},
        "insert_release_decision_ledger_section.py": {"--report", "--section", "--out"},
        "check_quality_ledger_status_parity.py": {"--status", "--ledger"},
    }
    _require(set(matches[0][1]) == allowed_options.get(tool), "source_mapping_argument_profile_mismatch", tool)
    return matches[0]


def _checked_mapping_export(raw: dict[str, Any], variable: str, *, allow_temp: bool = False) -> str:
    source = raw.get("run")
    _require(isinstance(source, str), "source_mapping_run_missing", variable)
    matches = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].lstrip()
        if not stripped.startswith(variable + "="):
            continue
        try:
            values = shlex.split(stripped[len(variable) + 1:], comments=False, posix=True)
        except ValueError as exc:
            raise PlanError("source_mapping_assignment_invalid", variable) from exc
        _require(len(values) == 1, "source_mapping_assignment_invalid", variable)
        matches.append(_checked_mapping_path(values[0], allow_temp=allow_temp))
    _require(len(matches) == 1, "source_mapping_assignment_not_unique", variable)
    return matches[0]


def _source_ledger_expectations(workflow: dict[str, Any]) -> dict[str, Any]:
    """Use the actual source's tool arguments and in-place version boundary."""
    jobs = workflow.get("jobs")
    _require(isinstance(jobs, dict), "source_mapping_jobs_missing")
    job = jobs.get("release_grade_recorded_path")
    _require(isinstance(job, dict) and isinstance(job.get("steps"), list), "source_mapping_job_missing")
    steps = job["steps"]
    _require(all(isinstance(s, dict) for s in steps), "source_mapping_steps_invalid")
    calls = [_checked_mapping_invocation(steps, name) for name in (
        "render_quality_ledger.py", "status_to_summary.py", "materialize_release_decision.py",
        "render_release_decision_ledger_section.py", "build_release_authority_manifest_v0.py",
        "insert_release_authority_manifest_ledger_section.py", "insert_release_decision_ledger_section.py",
        "check_quality_ledger_status_parity.py",
    )]
    positions = [c[0] for c in calls]
    _require(positions == list(range(positions[0], positions[0] + 8)), "source_mapping_ledger_order")
    def path(number: int, flag: str) -> str:
        _require(flag in calls[number][1], "source_mapping_argument_missing", str(number) + ":" + flag)
        return _checked_mapping_path(calls[number][1][flag])
    status, ledger = path(0, "--status"), path(0, "--out")
    section, decision, manifest = path(3, "--out"), path(2, "--out"), path(4, "--out")
    summary, report = path(1, "--out_json"), path(6, "--out")
    _require([path(i, "--status") for i in (1, 2, 4, 7)] == [status] * 4,
             "source_mapping_status_version_mismatch")
    _require(path(3, "--input") == decision, "source_mapping_decision_input_mismatch")
    _require(path(5, "--report") == ledger and path(5, "--manifest") == manifest
             and "--out" not in calls[5][1], "source_mapping_inplace_boundary_mismatch")
    _require((path(6, "--report"), path(6, "--section"), path(7, "--ledger")) == (ledger, section, ledger),
             "source_mapping_consumer_input_mismatch")
    _require(path(2, "--policy") == POLICY_PATH and path(4, "--policy") == POLICY_PATH
             and path(4, "--registry") == REGISTRY_PATH, "source_mapping_authority_input_mismatch")
    _require(len({status, ledger, section, decision, manifest, summary, report}) == 7,
             "source_mapping_output_alias")
    locators = dict(zip((
        "quality-ledger-pre-authority", "final-status-summary", "release-decision",
        "release-decision-ledger-section", "release-authority-manifest", "quality-ledger-final",
        "release-decision-report"), (ledger + "#pre-authority-insertion", summary, decision,
        section, manifest, ledger, report), strict=True))
    equation_roles = (
        (("final-status",), ("quality-ledger-pre-authority",)),
        (("final-status",), ("final-status-summary",)),
        (("final-status", "gate-policy"), ("release-decision",)),
        (("release-decision",), ("release-decision-ledger-section",)),
        (("final-status", "gate-policy", "gate-registry"), ("release-authority-manifest",)),
        (("quality-ledger-pre-authority", "release-authority-manifest"), ("quality-ledger-final",)),
        (("quality-ledger-final", "release-decision-ledger-section"), ("release-decision-report",)),
        (("final-status", "quality-ledger-final"), ()),
    )
    equations = {_step_id("release_grade_recorded_path", pos): {"inputs": list(ins), "outputs": list(outs)}
                 for pos, (ins, outs) in zip(positions, equation_roles, strict=True)}
    def step_named(name: str) -> dict[str, Any]:
        selected = [s for s in steps if s.get("name") == name]
        _require(len(selected) == 1, "source_mapping_step_not_unique", name)
        return selected[0]
    exports = step_named("Export final release-grade JUnit and SARIF")
    locators["release-grade-junit"] = _checked_mapping_export(exports, "PULSE_JUNIT")
    locators["release-grade-sarif"] = _checked_mapping_export(exports, "PULSE_SARIF")
    locators["advisory-reference-bundle"] = _checked_mapping_export(
        step_named("Assemble advisory release-grade reference bundle"), "BUNDLE_DIR", allow_temp=True) + "/"
    selected = [s for s in jobs.get("pulse", {}).get("steps", [])
                if s.get("name") == "Upload release-grade pre-attestation pulse artifacts"]
    _require(len(selected) == 1 and str(selected[0].get("uses", "")).startswith("actions/upload-artifact@"),
             "source_mapping_upload_missing")
    name = selected[0].get("with", {}).get("name")
    _require(isinstance(name, str) and name.count("${{ github.run_id }}") == 1
             and name.count("${{ github.run_attempt }}") == 1, "source_mapping_upload_template_invalid")
    name = name.replace("${{ github.run_id }}", "{workflow_run_id}").replace("${{ github.run_attempt }}", "1")
    _require(re.fullmatch(r"[a-z0-9-]+\{workflow_run_id\}-1", name) is not None,
             "source_mapping_upload_template_invalid")
    locators["pre-attestation-pulse-artifacts"] = "artifact://" + name
    return {"locators": locators, "status": status, "equations": equations}


def _apply_source_ledger_expectations(states: list[dict[str, Any]],
                                      step_by_key: dict[tuple[str, int], dict[str, Any]],
                                      facts: dict[str, Any]) -> None:
    index = {s["state_id"].removeprefix("state:step5c:"): s for s in states}
    controlled = set(facts["equations"])
    for role, locator in facts["locators"].items():
        index[role]["path_or_uri"] = locator
    _require(index["final-status"]["path_or_uri"] == facts["status"], "source_mapping_status_locator_mismatch")
    for role, state in index.items():
        consumers = set(state["required_consumer_occurrence_ids"]) - controlled
        for occurrence, equation in facts["equations"].items():
            if role in equation["inputs"]:
                consumers.add(occurrence)
            if role in equation["outputs"]:
                state["producer_occurrence_id"] = occurrence
        state["required_consumer_occurrence_ids"] = sorted(consumers)
    for step in step_by_key.values():
        equation = facts["equations"].get(step["occurrence_id"])
        if equation is not None:
            for field, side in (("input_state_ids", "inputs"), ("output_state_ids", "outputs")):
                step[field] = sorted("state:step5c:" + role for role in equation[side])


def _verify_source_ledger_equations(plan: dict[str, Any], workflow: dict[str, Any]) -> None:
    """Validate supplied records against source even if both reconstructions err."""
    facts = _source_ledger_expectations(workflow)
    raw_states = plan.get("state_templates")
    _require(isinstance(raw_states, list) and all(isinstance(s, dict) for s in raw_states),
             "source_mapping_state_set_invalid")
    states = {s.get("state_id"): s for s in raw_states}
    _require(len(states) == len(raw_states), "source_mapping_state_set_invalid")
    sid = lambda key: "state:step5c:" + key
    for key, locator in facts["locators"].items():
        _require(states.get(sid(key), {}).get("path_or_uri") == locator,
                 "source_mapping_locator_mismatch", key)
    _require(states.get(sid("final-status"), {}).get("path_or_uri") == facts["status"],
             "source_mapping_status_locator_mismatch")
    raw_jobs = plan.get("jobs")
    _require(isinstance(raw_jobs, list) and all(isinstance(j, dict) for j in raw_jobs),
             "source_mapping_job_set_invalid")
    steps = [s for j in raw_jobs for s in j.get("steps", [])]
    _require(all(isinstance(s, dict) for s in steps), "source_mapping_step_set_invalid")
    indexed = {s.get("occurrence_id"): s for s in steps}
    _require(len(indexed) == len(steps), "source_mapping_step_set_invalid")
    controlled = set(facts["equations"])
    for occurrence, equation in facts["equations"].items():
        step = indexed.get(occurrence)
        _require(isinstance(step, dict), "source_mapping_occurrence_missing", occurrence)
        for field, side in (("input_state_ids", "inputs"), ("output_state_ids", "outputs")):
            _require(step.get(field) == sorted(sid(k) for k in equation[side]),
                     "source_mapping_step_io_mismatch", occurrence + ":" + side)
        for key in equation["outputs"]:
            _require(states[sid(key)]["producer_occurrence_id"] == occurrence,
                     "source_mapping_producer_mismatch", key)
    for state_id, state in states.items():
        expected = {occurrence for occurrence, eq in facts["equations"].items()
                    if state_id in {sid(k) for k in eq["inputs"]}}
        consumers = state.get("required_consumer_occurrence_ids")
        _require(isinstance(consumers, list) and all(isinstance(c, str) for c in consumers),
                 "source_mapping_consumer_set_invalid", str(state_id))
        _require(set(consumers) & controlled == expected,
                 "source_mapping_consumer_mismatch", str(state_id))


# Independent source predicate for the selected recorded-evidence/status family.
# No producer module is imported. Source dependencies are not runtime receipts.
_RECORDED_SEMANTIC_JOB = "release_grade_recorded_path"
_RECORDED_SELECTED_ROLES = frozenset({
    "pre-materialization-status", "recorded-release-candidate-envelopes",
    "recorded-candidate-index", "release-evidence-input-manifest",
    "recorded-release-evidence-verifier", "materialized-release-required-gate-set",
    "final-status", "gate-policy", "gate-registry",
})


def _recorded_source_defaults(data: bytes, bindings: dict[str, str], label: str) -> dict[str, str]:
    """Independently read literal globals and their argparse default bindings."""
    try:
        module = ast.parse(data.decode("utf-8", errors="strict"), filename=label)
    except (UnicodeError, SyntaxError) as exc:
        raise PlanError("recorded_mapping_python_source", label) from exc
    definitions: dict[str, list[ast.AST | None]] = {}
    for node in module.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        for target in targets:
            if isinstance(target, ast.Name):
                definitions.setdefault(target.id, []).append(node.value)
    mains = [x for x in module.body if isinstance(x, ast.FunctionDef) and x.name == "main"]
    _require(len(mains) == 1, "recorded_mapping_main_not_unique", label)
    result = {}
    for flag, name in bindings.items():
        values = definitions.get(name, [])
        _require(len(values) == 1 and isinstance(values[0], ast.Constant)
                 and isinstance(values[0].value, str), "recorded_mapping_literal_not_unique", name)
        candidates = []
        for node in ast.walk(mains[0]):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
                if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == flag:
                    candidates.append(node)
        _require(len(candidates) == 1, "recorded_mapping_default_not_unique", flag)
        defaults = [kw.value for kw in candidates[0].keywords if kw.arg == "default"]
        _require(len(defaults) == 1 and isinstance(defaults[0], ast.Name) and defaults[0].id == name,
                 "recorded_mapping_default_binding", flag)
        result[flag] = _checked_mapping_path(values[0].value)
    return result


def _recorded_source_commands(step: dict[str, Any], expected_path: str,
                               flags: tuple[str, ...], expected_count: int = 1) -> list[dict[str, str]]:
    body = step.get("run")
    _require(isinstance(body, str), "recorded_mapping_run_missing", expected_path)
    commands = []
    for line in body.replace("\\\n", " ").splitlines():
        if not re.match(r"^\s*python(?:3)?\s+", line):
            continue
        try:
            words = shlex.split(line, comments=False, posix=True)
        except ValueError as exc:
            raise PlanError("recorded_mapping_command_invalid", expected_path) from exc
        if len(words) < 2 or words[1].split("/")[-1] != expected_path.split("/")[-1]:
            continue
        _require(_checked_mapping_path(words[1]) == expected_path, "recorded_mapping_tool_path", expected_path)
        tail = words[2:]
        _require(len(tail) == 2 * len(flags), "recorded_mapping_argument_shape", expected_path)
        options = dict(zip(tail[::2], tail[1::2]))
        _require(len(options) == len(flags) and set(options) == set(flags)
                 and all(not v.startswith("--") for v in options.values()),
                 "recorded_mapping_argument_profile", expected_path)
        commands.append(options)
    _require(len(commands) == expected_count, "recorded_mapping_command_count", expected_path)
    return commands


def _source_recorded_expectations(workflow: dict[str, Any],
                                   source_by_path: dict[str, GitObject]) -> dict[str, Any]:
    """Derive path equations from source and resolve selected roles by paths."""
    read: dict[str, bytes] = {}
    for path, expected in _RECORDED_SEMANTIC_PINS.items():
        obj = source_by_path.get(path)
        _require(obj is not None, "recorded_mapping_source_missing", path)
        _require(_sha1_git_blob(obj.data) == expected, "recorded_mapping_semantic_source_drift", path)
        read[path] = obj.data
    jobs = workflow.get("jobs", {})
    rows = jobs.get(_RECORDED_SEMANTIC_JOB, {}).get("steps")
    _require(isinstance(rows, list) and len(rows) >= 12, "recorded_mapping_steps_missing")
    expected_names = RECORDED_PATH_STEP_NAMES[5:12]
    _require(tuple(x.get("name") for x in rows[5:12]) == expected_names, "recorded_mapping_step_order")
    pack = "PULSE_safe_pack_v0/tools/"
    specifications = (
        (6, pack + "build_recorded_release_candidates_v0.py", ("--repo-root",)),
        (7, pack + "build_release_evidence_input_manifest_v0.py", ("--repo-root",)),
        (8, pack + "check_recorded_release_evidence_v0.py", ("--manifest", "--repo-root", "--out-json")),
        (9, pack + "materialize_release_required_from_verifier_v0.py", ("--status", "--verifier-report", "--manifest", "--repo-root", "--policy", "--registry", "--out")),
        (10, "tools/validate_status_schema.py", ("--schema", "--status", "--max-errors")),
        (11, "ci/check_release_no_stub_status.py", ("--status",)),
    )
    arguments = {n: _recorded_source_commands(rows[n - 1], path, flags)[0] for n, path, flags in specifications}
    _require(all(arguments[n]["--repo-root"] == "${GITHUB_WORKSPACE}" for n in range(6, 10)),
             "recorded_mapping_repo_root")
    candidate_path = pack + "build_recorded_release_candidates_v0.py"
    manifest_path = pack + "build_release_evidence_input_manifest_v0.py"
    cd = _recorded_source_defaults(read[candidate_path],
        {"--status": "STATUS", "--index": "INDEX", "--out-dir": "OUT_DIR", "--policy": "POLICY", "--registry": "REGISTRY"}, candidate_path)
    md = _recorded_source_defaults(read[manifest_path],
        {"--index": "INDEX_PATH", "--out": "OUT_PATH", "--policy": "POLICY_PATH", "--registry": "REGISTRY_PATH"}, manifest_path)
    envelopes = _checked_mapping_path(_python_constant(read[manifest_path], name="CANDIDATE_DIR", label=manifest_path))
    manifest_status = _checked_mapping_path(_python_constant(read[manifest_path], name="STATUS_PATH", label=manifest_path))
    _require(cd["--index"] == md["--index"] and cd["--out-dir"] == envelopes and cd["--status"] == manifest_status,
             "recorded_mapping_candidate_handoff")
    _require(cd["--policy"] == md["--policy"] == POLICY_PATH
             and cd["--registry"] == md["--registry"] == REGISTRY_PATH,
             "recorded_mapping_policy_defaults")
    def path(n: int, option: str) -> str:
        return _checked_mapping_path(arguments[n][option])
    _require(path(8, "--manifest") == path(9, "--manifest") == md["--out"]
             and path(8, "--out-json") == path(9, "--verifier-report"),
             "recorded_mapping_verifier_handoff")
    final = path(9, "--out")
    _require(cd["--status"] == path(9, "--status") == final, "recorded_mapping_status_version")
    _require(path(9, "--policy") == POLICY_PATH and path(9, "--registry") == REGISTRY_PATH,
             "recorded_mapping_materializer_context")
    _require(len({final, md["--out"], cd["--index"], envelopes, path(8, "--out-json")}) == 5,
             "recorded_mapping_output_alias")
    _require(path(10, "--status") == path(11, "--status") == final
             and path(10, "--schema") == "schemas/status/release_grade_status_v1.schema.json"
             and arguments[10]["--max-errors"] == "20", "recorded_mapping_post_status_guard")
    pulse = jobs.get("pulse", {}).get("steps", [])
    _require(len(pulse) >= 37, "recorded_mapping_origin_missing")
    origin = _recorded_source_commands(pulse[12], pack + "build_release_grade_candidate_status_v0.py", ("--repo-root", "--out"))[0]
    _require(origin["--repo-root"] == "${GITHUB_WORKSPACE}"
             and _checked_mapping_path(origin["--out"]) == final, "recorded_mapping_status_origin")
    restore_body = rows[3].get("run", "")
    _require(_checked_mapping_export(rows[3], "CANONICAL_ARTIFACTS") + "/status.json" == final
             and len(re.findall(r'^\s*copy_required_artifact\s+"status\.json"\s*$', restore_body, re.M)) == 1,
             "recorded_mapping_status_restore")
    _require(_checked_mapping_export(rows[11], "STATUS") == final, "recorded_mapping_enforcement_status")
    policies = _recorded_source_commands(rows[11], "tools/policy_to_require_args.py", ("--policy", "--set", "--format"), 2)
    _require(tuple(x["--set"] for x in policies) == ("required", "release_required")
             and all(_checked_mapping_path(x["--policy"]) == POLICY_PATH and x["--format"] == "newline" for x in policies),
             "recorded_mapping_enforcement_policy")
    enforcement = _recorded_source_commands(rows[11], pack + "check_gates.py", ("--status", "--require"))[0]
    _require(enforcement["--status"] == "${STATUS}" and enforcement["--require"] == "${EFFECTIVE_GATES[@]}",
             "recorded_mapping_enforcement_arguments")
    # Resolve names through source paths, with separate versions of status.json.
    before = final + "#pre-release-required-materialization"
    logical = "projection://" + final + "#policy-selected-release_required-gate-values"
    locators = {"pre-materialization-status": before, "recorded-release-candidate-envelopes": envelopes + "/",
                "recorded-candidate-index": cd["--index"], "release-evidence-input-manifest": md["--out"],
                "recorded-release-evidence-verifier": path(8, "--out-json"),
                "materialized-release-required-gate-set": logical, "final-status": final}
    names = {value: key for key, value in locators.items()}
    names.update({POLICY_PATH: "gate-policy", REGISTRY_PATH: "gate-registry"})
    env_dir = envelopes + "/"
    # R8 and R9 use pinned canonical-candidate replay, not the persisted index.
    replay_inputs = (before, env_dir, POLICY_PATH, REGISTRY_PATH)
    equations = {
        6: ((before, cd["--policy"], cd["--registry"]), (cd["--index"], env_dir)),
        7: ((md["--index"], env_dir, before, md["--policy"], md["--registry"]), (md["--out"],)),
        8: ((path(8, "--manifest"), *replay_inputs), (path(8, "--out-json"),)),
        9: ((*replay_inputs, path(9, "--manifest"), path(9, "--verifier-report")), (final, logical)),
        10: ((path(10, "--status"),), ()), 11: ((path(11, "--status"),), ()),
        12: ((final, POLICY_PATH), ()),
    }
    return {"locators": locators,
            "steps": {_step_id(_RECORDED_SEMANTIC_JOB, n): {"inputs": tuple(names[x] for x in ins), "outputs": tuple(names[x] for x in outs)}
                      for n, (ins, outs) in equations.items()},
            "pre_status_origin": _step_id("pulse", 13), "pre_status_restore": _step_id(_RECORDED_SEMANTIC_JOB, 4)}


def _apply_recorded_source_expectations(states: list[dict[str, Any]],
                                        step_by_key: dict[tuple[str, int], dict[str, Any]],
                                        facts: dict[str, Any]) -> None:
    # Construct the checker's own answer from its source expectations. The
    # separate predicate below checks the supplied answer independently of it.
    index = {s["state_id"].removeprefix("state:step5c:"): s for s in states}
    closed = {"state:step5c:" + x for x in _RECORDED_SELECTED_ROLES}
    occurrences = facts["steps"]
    for key, locator in facts["locators"].items():
        index[key]["path_or_uri"] = locator
    for role in _RECORDED_SELECTED_ROLES:
        index[role]["required_consumer_occurrence_ids"] = [x for x in index[role]["required_consumer_occurrence_ids"] if x not in occurrences]
    for step in step_by_key.values():
        oid = step["occurrence_id"]
        if oid not in occurrences:
            continue
        for field, direction in (("input_state_ids", "inputs"), ("output_state_ids", "outputs")):
            ids = ["state:step5c:" + x for x in occurrences[oid][direction]]
            step[field] = sorted({x for x in step[field] if x not in closed}.union(ids))
        for role in occurrences[oid]["inputs"]:
            index[role]["required_consumer_occurrence_ids"].append(oid)
        for role in occurrences[oid]["outputs"]:
            index[role]["producer_occurrence_id"] = oid
    pre = index["pre-materialization-status"]
    pre["producer_occurrence_id"] = facts["pre_status_origin"]
    pre["required_consumer_occurrence_ids"].append(facts["pre_status_restore"])
    for step in step_by_key.values():
        step["input_state_ids"] = [x for x in step["input_state_ids"] if x != "state:step5c:materialized-release-required-gate-set"]
        if step["occurrence_id"] == facts["pre_status_origin"]:
            _append_unique(step["output_state_ids"], pre["state_id"])
        elif step["occurrence_id"] == facts["pre_status_restore"]:
            _append_unique(step["input_state_ids"], pre["state_id"])
    index["materialized-release-required-gate-set"]["required_consumer_occurrence_ids"] = []
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))


def _verify_source_recorded_equations(plan: dict[str, Any], workflow: dict[str, Any],
                                        source_by_path: dict[str, GitObject]) -> None:
    """Reject a shared wrong producer/checker answer against the source itself."""
    facts = _source_recorded_expectations(workflow, source_by_path)
    states = {s["state_id"]: s for s in plan["state_templates"]}
    steps = {s["occurrence_id"]: s for job in plan["jobs"] for s in job["steps"]}
    sid = lambda name: "state:step5c:" + name
    selected = {sid(name) for name in _RECORDED_SELECTED_ROLES}
    _require(selected <= set(states), "recorded_mapping_role_missing")
    for role, locator in facts["locators"].items():
        _require(states[sid(role)]["path_or_uri"] == locator, "recorded_mapping_locator_mismatch", role)
    owned = set(facts["steps"])
    for occurrence, equation in facts["steps"].items():
        _require(occurrence in steps, "recorded_mapping_occurrence_missing", occurrence)
        for field, direction in (("input_state_ids", "inputs"), ("output_state_ids", "outputs")):
            _require(set(steps[occurrence][field]) & selected == {sid(role) for role in equation[direction]},
                     "recorded_mapping_equation_mismatch", occurrence + ":" + direction)
        for role in equation["outputs"]:
            _require(states[sid(role)]["producer_occurrence_id"] == occurrence,
                     "recorded_mapping_producer_mismatch", role)
    for role in _RECORDED_SELECTED_ROLES:
        expected = {oid for oid, equation in facts["steps"].items() if role in equation["inputs"]}
        _require(set(states[sid(role)]["required_consumer_occurrence_ids"]) & owned == expected,
                 "recorded_mapping_reverse_mismatch", role)
    pre = sid("pre-materialization-status")
    _require(states[pre]["producer_occurrence_id"] == facts["pre_status_origin"]
             and pre in steps[facts["pre_status_origin"]]["output_state_ids"]
             and pre in steps[facts["pre_status_restore"]]["input_state_ids"]
             and facts["pre_status_restore"] in states[pre]["required_consumer_occurrence_ids"],
             "recorded_mapping_status_origin_mismatch")
    # Newly introduced roles have no legacy, unreviewed consumers outside this
    # source family. Check their entire occurrence surface, not just a subset.
    for role in ("pre-materialization-status", "recorded-release-candidate-envelopes"):
        expected_consumers = {oid for oid, eq in facts["steps"].items() if role in eq["inputs"]}
        if role == "pre-materialization-status":
            expected_consumers.add(facts["pre_status_restore"])
        role_id = sid(role)
        _require(set(states[role_id]["required_consumer_occurrence_ids"]) == expected_consumers
                 and {oid for oid, step in steps.items() if role_id in step["input_state_ids"]} == expected_consumers,
                 "recorded_mapping_new_role_consumer_mismatch", role)
        _require({oid for oid, step in steps.items() if role_id in step["output_state_ids"]}
                 == {states[role_id]["producer_occurrence_id"]},
                 "recorded_mapping_new_role_producer_mismatch", role)
    logical = sid("materialized-release-required-gate-set")
    _require(states[logical]["required_consumer_occurrence_ids"] == []
             and not any(logical in x["input_state_ids"] for x in steps.values()),
             "recorded_mapping_projection_is_not_runtime_argument_list")


# Package publication and metadata are distinct from local content creation.
# This bounded projection declares source relations; it never observes a run,
# expands an archive, or treats a published report as an independent verdict.
_PACKAGE_SEMANTIC_PINS = {
    "PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py": "8f01602e973b890eb2ae0928bd62dfd65e691f79",
    "PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py": "f54c37a32329d191e213bb71a6818858285ff20a",
    "tools/check_release_grade_package_complete_v1.py": "601e9a33097824b2055d908d25fad5667612c136",
}
_PACKAGE_ROLES = (
    "complete-release-grade-reference-package", "package-completeness-report",
    "package-verification-report", "package-digest-inventory", "package-run-metadata",
)
_PACKAGE_ASSEMBLE_JOB = "assemble_release_grade_reference_package"
_PACKAGE_VERIFY_JOB = "verify_release_grade_reference_package"


def _package_temp_path(value: str, variables: dict[str, str]) -> str:
    _require(isinstance(value, str), "package_mapping_path_invalid")
    value = re.sub(r"\$\{\{\s*runner\.temp\s*\}\}", "${RUNNER_TEMP}", value)
    for name, replacement in variables.items():
        token = "${" + name + "}"
        if value == token or value.startswith(token + "/"):
            value = replacement + value[len(token):]
            break
    if value.endswith("/"):
        value = value[:-1]
    _require(value.startswith("${RUNNER_TEMP}/"), "package_mapping_temp_root", value)
    try:
        return _checked_mapping_path(value, allow_temp=True)
    except PlanError as exc:
        raise PlanError("package_mapping_path_invalid", value) from exc


def _package_assignment(step: dict[str, Any], name: str, variables: dict[str, str]) -> str:
    body = step.get("run")
    _require(isinstance(body, str), "package_mapping_run_missing", name)
    matches = re.findall(r"^\s*" + re.escape(name) + r"=(.+)$", body, re.M)
    _require(len(matches) == 1, "package_mapping_assignment_not_unique", name)
    try:
        values = shlex.split(matches[0])
    except ValueError as exc:
        raise PlanError("package_mapping_assignment_invalid", name) from exc
    _require(len(values) == 1, "package_mapping_assignment_invalid", name)
    return _package_temp_path(values[0], variables)


def _package_commands(step: dict[str, Any], prefix: tuple[str, ...], flags: set[str]) -> list[dict[str, str]]:
    body = step.get("run")
    _require(isinstance(body, str), "package_mapping_run_missing")
    rows = []
    for line in body.replace("\\\n", " ").splitlines():
        if not re.match(r"^\s*" + re.escape(prefix[0]) + r"\s+", line):
            continue
        try:
            words = shlex.split(line)
        except ValueError as exc:
            raise PlanError("package_mapping_command_invalid") from exc
        if tuple(words[:len(prefix)]) != prefix:
            continue
        args = words[len(prefix):]
        _require(len(args) == 2 * len(flags), "package_mapping_argument_shape")
        opts = dict(zip(args[::2], args[1::2]))
        _require(set(opts) == flags and len(opts) == len(flags)
                 and all(not value.startswith("--") for value in opts.values()),
                 "package_mapping_argument_profile")
        rows.append(opts)
    return rows


def _package_artifact_name(value: str) -> str:
    _require(isinstance(value, str), "package_mapping_artifact_name_invalid")
    _require(len(re.findall(r"\$\{\{\s*github\.run_id\s*\}\}", value)) == 1
             and len(re.findall(r"\$\{\{\s*github\.run_attempt\s*\}\}", value)) == 1,
             "package_mapping_artifact_run_binding")
    value = re.sub(r"\$\{\{\s*github\.run_id\s*\}\}", "{workflow_run_id}", value)
    value = re.sub(r"\$\{\{\s*github\.run_attempt\s*\}\}", "1", value)
    _require(re.fullmatch(r"[A-Za-z0-9_.-]+-\{workflow_run_id\}-1", value) is not None,
             "package_mapping_artifact_name_invalid", value)
    return value


def _source_package_expectations(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    """Check source publication equations independently of either state table."""
    parsed_sources = {}
    for filename, blob in _PACKAGE_SEMANTIC_PINS.items():
        record = sources.get(filename)
        _require(record is not None, "package_mapping_source_missing", filename)
        _require(_sha1_git_blob(record.data) == blob, "package_mapping_semantic_source_drift", filename)
        parsed_sources[filename] = ast.parse(record.data)
    jobs = workflow.get("jobs", {})
    source_steps = {}
    for job_name, names in ((_PACKAGE_ASSEMBLE_JOB, ASSEMBLE_PACKAGE_STEP_NAMES), (_PACKAGE_VERIFY_JOB, VERIFY_PACKAGE_STEP_NAMES)):
        raw = jobs.get(job_name, {}).get("steps")
        _require(isinstance(raw, list) and len(raw) == len(names), "package_mapping_step_profile", job_name)
        for number, (step, name) in enumerate(zip(raw, names), 1):
            _require(isinstance(step, dict) and step.get("name") == name, "package_mapping_step_profile", name)
            source_steps[(job_name, number)] = step
    s = lambda number: source_steps[(_PACKAGE_ASSEMBLE_JOB, number)]
    v = lambda number: source_steps[(_PACKAGE_VERIFY_JOB, number)]
    variables = {}
    for name in ("INPUT_ROOT", "PULSE_REPORT_DIR", "RECORDED_PATH_DIR", "AUDIT_BUNDLE_DIR", "ARTIFACT_BINDING_DIR", "COMPLETE_PACKAGE_DIR"):
        variables[name] = _package_assignment(s(4), name, variables)
    downloaded_dir = _package_assignment(v(4), "PACKAGE_DIR", {})
    verification_output = _package_assignment(v(4), "VERIFY_OUT", {})
    verify_variables = {"PACKAGE_DIR": downloaded_dir, "VERIFY_OUT": verification_output}
    id_arguments = {"--repo-root": "${GITHUB_WORKSPACE}", "--repository": "${GITHUB_REPOSITORY}", "--git-sha": "${GITHUB_SHA}",
                    "--workflow-ref": "${GITHUB_WORKFLOW_REF}", "--run-id": "${GITHUB_RUN_ID}", "--run-attempt": "${GITHUB_RUN_ATTEMPT}",
                    "--run-key": "${PULSE_RUN_KEY}"}
    assembly_path = "PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py"
    verifier_path = "PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py"
    completeness_path = "tools/check_release_grade_package_complete_v1.py"
    def invocation(step: dict[str, Any], path: str, fields: set[str]) -> dict[str, str]:
        candidates = _package_commands(step, ("python", path), fields)
        _require(len(candidates) == 1, "package_mapping_command_not_unique", path)
        return candidates[0]
    assembly_args = invocation(s(5), assembly_path, set(id_arguments) | {"--out-dir", "--pulse-report-dir", "--recorded-path-dir",
        "--audit-bundle-dir", "--artifact-binding-dir", "--release-candidate", "--created-utc"})
    verifier_args = invocation(v(7), verifier_path, set(id_arguments) | {"--package-dir", "--out"})
    completeness_args = invocation(v(5), completeness_path, {"--package-dir", "--output"})
    for command in (assembly_args, verifier_args):
        _require(all(command[key] == value for key, value in id_arguments.items()), "package_mapping_command_identity")
    _require(assembly_args["--release-candidate"] == "${GITHUB_REF_NAME}" and assembly_args["--created-utc"] == "${PACKAGE_CREATED_UTC}",
             "package_mapping_command_identity")
    for parameter, variable in (("--pulse-report-dir", "PULSE_REPORT_DIR"), ("--recorded-path-dir", "RECORDED_PATH_DIR"),
                                ("--audit-bundle-dir", "AUDIT_BUNDLE_DIR"), ("--artifact-binding-dir", "ARTIFACT_BINDING_DIR")):
        _require(_package_temp_path(assembly_args[parameter], variables) == variables[variable], "package_mapping_input_root", parameter)
    package_dir = _package_temp_path(assembly_args["--out-dir"], variables)
    directories = (variables["COMPLETE_PACKAGE_DIR"], downloaded_dir,
                   _package_temp_path(completeness_args["--package-dir"], {}), _package_temp_path(verifier_args["--package-dir"], verify_variables))
    _require(all(path == package_dir for path in directories), "package_mapping_directory_handoff")
    report_paths = (_package_temp_path(completeness_args["--output"], {}), _package_temp_path(verifier_args["--out"], verify_variables))
    _require(len({package_dir, *report_paths}) == 3 and not any(p.startswith(package_dir + "/") for p in report_paths),
             "package_mapping_output_alias")
    publication_steps = ((_PACKAGE_ASSEMBLE_JOB, 6), (_PACKAGE_VERIFY_JOB, 6), (_PACKAGE_VERIFY_JOB, 8))
    locators, outputs, producers = {}, {}, {}
    for role, key, expected_output in zip(_PACKAGE_ROLES[:3], publication_steps, (package_dir, *report_paths)):
        step = source_steps[key]
        options = step.get("with", {})
        _require(step.get("uses") == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
                 and options.get("if-no-files-found") == "error", "package_mapping_upload_profile")
        output = _package_temp_path(options.get("path"), {})
        _require(output == expected_output, "package_mapping_publication_path", role)
        locators[role] = "artifact://" + _package_artifact_name(options.get("name"))
        outputs[role] = output
        producers[role] = _step_id(*key)
    _require(len(set(locators.values())) == 3, "package_mapping_publication_alias")
    downloads = _package_commands(v(4), ("gh", "run", "download", "${GITHUB_RUN_ID}"), {"--repo", "--name", "--dir"})
    _require(len(downloads) == 1, "package_mapping_download_handoff")
    retrieved = downloads[0]
    _require(retrieved["--repo"] == "${GITHUB_REPOSITORY}"
             and "artifact://" + _package_artifact_name(retrieved["--name"]) == locators[_PACKAGE_ROLES[0]]
             and _package_temp_path(retrieved["--dir"], verify_variables) == downloaded_dir, "package_mapping_download_handoff")
    input_routes = _package_commands(s(4), ("gh", "run", "download", "${GITHUB_RUN_ID}"), {"--repo", "--name", "--dir"})
    expected_names = {
        "pulse-report": "PULSE_REPORT_DIR", "release-authority-artifact-binding-v0": "ARTIFACT_BINDING_DIR",
        "release-authority-audit-bundle": "AUDIT_BUNDLE_DIR",
        "release-grade-recorded-path-${{ github.run_id }}-${{ github.run_attempt }}": "RECORDED_PATH_DIR",
    }
    _require(len(input_routes) == len(expected_names) and {row["--name"] for row in input_routes} == set(expected_names),
             "package_mapping_assembly_downloads")
    for row in input_routes:
        _require(row["--repo"] == "${GITHUB_REPOSITORY}" and _package_temp_path(row["--dir"], variables) == variables[expected_names[row["--name"]]],
                 "package_mapping_assembly_downloads")
    # Work backwards from the two writer calls to their source pathname
    # assignments. No state-table pathname or builder result is consulted.
    main = next(node for node in parsed_sources[assembly_path].body if isinstance(node, ast.FunctionDef) and node.name == "main")
    consumers = {_PACKAGE_ROLES[0]: (_step_id(_PACKAGE_VERIFY_JOB, 4),), _PACKAGE_ROLES[1]: (), _PACKAGE_ROLES[2]: ()}
    members = {}
    for writer, role in (("_write_run_metadata", "package-run-metadata"), ("_write_digest_inventory", "package-digest-inventory")):
        writes = [node for node in ast.walk(main) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == writer]
        _require(len(writes) == 1 and writes[0].args and isinstance(writes[0].args[0], ast.Name), "package_mapping_metadata_writer", role)
        variable = writes[0].args[0].id
        bindings = [node for node in ast.walk(main) if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == variable for target in node.targets)]
        _require(len(bindings) == 1, "package_mapping_metadata_assignment", role)
        expr = bindings[0].value
        _require(isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div) and isinstance(expr.left, ast.Name)
                 and expr.left.id == "staging_dir" and isinstance(expr.right, ast.Constant) and isinstance(expr.right.value, str),
                 "package_mapping_metadata_path", role)
        member = expr.right.value
        _require(re.fullmatch(r"[A-Za-z0-9_.-]+\.json", member) is not None, "package_mapping_metadata_path", role)
        for filename, constants in ((verifier_path, ("REQUIRED_FILES", "JSON_FILES")),
                                    (completeness_path, ("REQUIRED_FILES", "JSON_OBJECT_FILES"))):
            for constant in constants:
                definitions = []
                for node in parsed_sources[filename].body:
                    names = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
                    if any(isinstance(target, ast.Name) and target.id == constant for target in names):
                        definitions.append(node.value)
                _require(len(definitions) == 1 and member in ast.literal_eval(definitions[0]), "package_mapping_metadata_reader", role)
        members[role] = member
        locators[role] = package_dir + "/" + member
        producers[role] = _step_id(_PACKAGE_ASSEMBLE_JOB, 5)
        consumers[role] = tuple(_step_id(job, number) for job, number in ((_PACKAGE_ASSEMBLE_JOB, 6), (_PACKAGE_VERIFY_JOB, 5), (_PACKAGE_VERIFY_JOB, 7)))
    _require(len(set(members.values())) == 2, "package_mapping_metadata_alias")
    return {"locators": locators, "producers": producers, "consumers": consumers,
            "local_outputs": outputs, "metadata_members": members, "assembly_download_names": sorted(expected_names)}


def _verify_source_package_equations(plan: dict[str, Any], workflow: dict[str, Any], sources: dict[str, GitObject]) -> None:
    facts = _source_package_expectations(workflow, sources)
    states = {row["state_id"]: row for row in plan["state_templates"]}
    steps = {step["occurrence_id"]: step for job in plan["jobs"] for step in job["steps"]}
    for role in _PACKAGE_ROLES:
        state_id = "state:step5c:" + role
        _require(state_id in states, "package_mapping_role_missing", role)
        state = states[state_id]
        _require(state["path_or_uri"] == facts["locators"][role], "package_mapping_locator_mismatch", role)
        _require(state["producer_occurrence_id"] == facts["producers"][role], "package_mapping_producer_mismatch", role)
        expected = set(facts["consumers"][role])
        _require(set(state["required_consumer_occurrence_ids"]) == expected, "package_mapping_consumer_mismatch", role)
        _require(state["required"] is True and state["content_requirement"] == "exact_digest" and state["authority_bearing"] is False,
                 "package_mapping_requirement_mismatch", role)
        _require({oid for oid, step in steps.items() if state_id in step["output_state_ids"]} == {facts["producers"][role]},
                 "package_mapping_writer_set_mismatch", role)
        _require({oid for oid, step in steps.items() if state_id in step["input_state_ids"]} == expected,
                 "package_mapping_reader_set_mismatch", role)
    acquisition = _step_id(_PACKAGE_ASSEMBLE_JOB, 4)
    for role in ("advisory-reference-bundle", "artifact-binding-attestation"):
        key = "state:step5c:" + role
        _require(acquisition not in states[key]["required_consumer_occurrence_ids"]
                 and key not in steps[acquisition]["input_state_ids"], "package_mapping_unacquired_input", role)


def _apply_package_source_expectations(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
    index = {row["state_id"]: row for row in states}
    selected = {"state:step5c:" + role for role in _PACKAGE_ROLES}
    for step in steps.values():
        for key in ("input_state_ids", "output_state_ids"):
            step[key] = [state for state in step[key] if state not in selected]
    for role in _PACKAGE_ROLES:
        state_id = "state:step5c:" + role
        if state_id not in index:
            row = _state(state_id=state_id, state_type="package_inventory" if role == "package-digest-inventory" else "run_metadata",
                         role=role.replace("-", "_"), path_or_uri=facts["locators"][role], required=True,
                         content_requirement="exact_digest", producer=facts["producers"][role], consumers=(),
                         authority_bearing=False, mutation_class="preservation_output")
            states.append(row)
            index[state_id] = row
        row = index[state_id]
        row["path_or_uri"] = facts["locators"][role]
        row["producer_occurrence_id"] = facts["producers"][role]
        row["required_consumer_occurrence_ids"] = sorted(facts["consumers"][role])
        for step in steps.values():
            if step["occurrence_id"] == facts["producers"][role]:
                step["output_state_ids"].append(state_id)
            if step["occurrence_id"] in facts["consumers"][role]:
                step["input_state_ids"].append(state_id)
    # S4 downloads four named archives, neither of these two objects. Do not
    # fabricate an attestation-receipt or advisory-archive acquisition edge.
    occurrence = _step_id(_PACKAGE_ASSEMBLE_JOB, 4)
    for role in ("advisory-reference-bundle", "artifact-binding-attestation"):
        state_id = "state:step5c:" + role
        row = index[state_id]
        row["required_consumer_occurrence_ids"] = [x for x in row["required_consumer_occurrence_ids"] if x != occurrence]
        steps[(_PACKAGE_ASSEMBLE_JOB, 4)]["input_state_ids"] = [x for x in steps[(_PACKAGE_ASSEMBLE_JOB, 4)]["input_state_ids"] if x != state_id]


# An independently extracted, source-only R12 argument projection. This object
# is not an artifact written or read by a separate subject step, and is not a
# receipt of the arguments that an original hosted execution actually received.
_REQUIRED_ARGUMENT_ROLE = "effective-required-argument-list"
_REQUIRED_ARGUMENT_RUN_SHA256 = "dababaec377d50eb83daa95fab958009089db11a207214bdbab1ea0156a0f81a"
_REQUIRED_ARGUMENT_SOURCE_PINS = {
    ".github/workflows/pulse_ci.yml": "adae42c8e9777d357ab5400ced5765de7059ed1e",
    "pulse_gate_policy_v0.yml": "a311b424ad0f6c028b9c37b18572e7a09c721cdd",
    "tools/policy_to_require_args.py": "5b1d099485d0e3bfd90da3fff1213a4e949db850",
    "PULSE_safe_pack_v0/tools/check_gates.py": "2a593bdef31c9c8cb565b1c4ca3d16a1e3093735",
}


def _source_required_policy_members(data: bytes) -> dict[str, list[str]]:
    """Extract the two selected block lists without using the builder parser."""
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise PlanError("required_argument_policy_encoding") from exc
    # Validate duplicate YAML keys as well as the independent finite text walk.
    document = _parse_yaml_document(data, label=POLICY_PATH)
    _require(isinstance(document.get("gates"), dict), "required_argument_policy_gates_missing")
    wanted = {"required", "release_required"}
    found: dict[str, list[str]] = {}
    inside = False
    active: str | None = None
    root_count = 0
    for original in text.splitlines():
        line = original.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line == "gates:":
            root_count += 1
            inside, active = True, None
            continue
        if not line.startswith(" "):
            inside, active = False, None
        if not inside:
            continue
        if line.startswith("  ") and not line.startswith("    "):
            active = None
            match = re.fullmatch(r"  ([a-z][a-z0-9_]*):", line)
            key = line.strip().partition(":")[0]
            if key in wanted:
                _require(match is not None and key not in found,
                         "required_argument_policy_set_shape", key)
                active = key
                found[key] = []
            continue
        if active is not None:
            item = re.fullmatch(r"    - ([a-z][a-z0-9_]*)", line)
            _require(item is not None, "required_argument_policy_member_shape", active)
            found[active].append(item.group(1))
    _require(root_count == 1 and set(found) == wanted,
             "required_argument_policy_set_shape")
    _require(all(found.values()), "required_argument_policy_set_empty")
    for name in wanted:
        _require(document["gates"].get(name) == found[name],
                 "required_argument_policy_members_invalid", name)
    return {name: found[name] for name in ("required", "release_required")}


def _source_required_argument_expectations(
    workflow: dict[str, Any], source_by_path: dict[str, GitObject],
) -> dict[str, Any]:
    """Resolve backward from the checker array to its two policy inputs."""
    captured_sources: dict[str, bytes] = {}
    for path in _REQUIRED_ARGUMENT_SOURCE_PINS:
        item = source_by_path.get(path)
        _require(item is not None, "required_argument_source_missing", path)
        _require(_sha1_git_blob(item.data) == _REQUIRED_ARGUMENT_SOURCE_PINS[path],
                 "required_argument_semantic_source_drift", path)
        captured_sources[path] = item.data
    jobs = workflow.get("jobs")
    _require(isinstance(jobs, dict), "required_argument_source_step_missing")
    rows = jobs.get("release_grade_recorded_path", {}).get("steps")
    _require(isinstance(rows, list) and len(rows) > 11,
             "required_argument_source_step_missing")
    step = rows[11]
    _require(isinstance(step, dict) and step.get("name") == RECORDED_PATH_STEP_NAMES[11],
             "required_argument_source_step_mismatch")
    run = step.get("run")
    _require(isinstance(run, str) and hashlib.sha256(run.encode("utf-8")).hexdigest()
             == _REQUIRED_ARGUMENT_RUN_SHA256, "required_argument_shell_profile_mismatch")
    # Finite exact-body pinning fixes the control flow. Parsing the named array
    # inputs separately prevents a lookup table from standing in for source facts.
    command_lines = run.replace("\\\n", " ").splitlines()
    final_commands = [shlex.split(line) for line in command_lines
                      if line.strip().startswith('python "${PACK_DIR}/tools/check_gates.py"')]
    _require(final_commands == [["python", "${PACK_DIR}/tools/check_gates.py",
                                 "--status", "${STATUS}", "--require", "${EFFECTIVE_GATES[@]}"]],
             "required_argument_checker_binding_mismatch")
    arrays: dict[str, str] = {}
    for array, command in re.findall(r"mapfile -t ([A-Z_]+) < <\(\s*(.*?)\s*\)", run, re.S):
        words = shlex.split(command.replace("\\\n", " "))
        _require(len(words) == 8 and words[:4] == ["python", "tools/policy_to_require_args.py", "--policy", POLICY_PATH]
                 and words[4] == "--set" and words[6:] == ["--format", "newline"]
                 and array not in arrays, "required_argument_selection_mismatch")
        arrays[array] = words[5]
    _require(arrays == {"REQUIRED_GATES": "required", "RELEASE_REQUIRED_GATES": "release_required"},
             "required_argument_selection_mismatch")
    order = re.findall(r'for gate in "\$\{([A-Z_]+)\[@\]\}" "\$\{([A-Z_]+)\[@\]\}";', run)
    _require(order == [("REQUIRED_GATES", "RELEASE_REQUIRED_GATES")],
             "required_argument_selection_mismatch")
    names = [arrays[array] for array in order[0]]
    policy_sets = _source_required_policy_members(captured_sources[POLICY_PATH])
    seen: set[str] = set()
    arguments: list[str] = []
    for name in names:
        for value in policy_sets[name]:
            if value not in seen:
                seen.add(value)
                arguments.append(value)
    statuses = re.findall(r'^STATUS="\$\{PACK_DIR\}/([^"\n]+)"$', run, re.M)
    _require(len(statuses) == 1, "required_argument_status_selector")
    status_selector = "PULSE_safe_pack_v0/" + statuses[0]
    derived = {
        "derivation_type": "step5c_effective_required_arguments_source_v0",
        "source_occurrence_id": _step_id("release_grade_recorded_path", 12),
        "source_command_sha256": hashlib.sha256(run.encode("utf-8")).hexdigest(),
        "source_bindings": [{"path": path, "sha256": hashlib.sha256(captured_sources[path]).hexdigest()}
                            for path in sorted(captured_sources)],
        "policy_path": POLICY_PATH,
        "selected_sets": names,
        "policy_set_members": policy_sets,
        "ordered_required_gate_ids": arguments,
        "deduplication": "first_seen_preserve_order",
        "status_selector": status_selector,
        "checker_path": "PULSE_safe_pack_v0/tools/check_gates.py",
        "original_runtime_argv_receipt": "unavailable",
        "source_derived_only": True,
        "authority_effect": "none",
    }
    checksum = hashlib.sha256(_canonical_json_bytes(derived)).hexdigest()
    return {"derivation": derived, "derivation_sha256": checksum,
            "locator": "projection://" + POLICY_PATH + "#r12-source-required-arguments/sha256/" + checksum}


def _verify_source_required_argument_equations(
    plan: dict[str, Any], workflow: dict[str, Any], source_by_path: dict[str, GitObject],
) -> None:
    facts = _source_required_argument_expectations(workflow, source_by_path)
    identifier = "state:step5c:" + _REQUIRED_ARGUMENT_ROLE
    candidates = [row for row in plan["state_templates"] if row["state_id"] == identifier]
    _require(len(candidates) == 1, "required_argument_role_missing_or_duplicate")
    expected = {
        "state_id": identifier, "state_type": "other",
        "role": "source_derived_required_arguments_runtime_receipt_unavailable",
        "path_or_uri": facts["locator"], "required": True,
        "content_requirement": "exact_digest", "producer_occurrence_id": None,
        "required_consumer_occurrence_ids": [], "authority_bearing": False,
        "mutation_class": "none",
    }
    _require(candidates[0] == expected, "required_argument_state_mismatch")
    for job in plan["jobs"]:
        for step in job["steps"]:
            _require(identifier not in step["input_state_ids"] + step["output_state_ids"],
                     "required_argument_invented_runtime_edge")


# Independent source predicate for the two bundle-preservation roles. This
# inspects copy and handoff source; it does not trust either constructed plan.
_BUNDLE_ROLES = ("release-authority-audit-bundle", "advisory-reference-bundle")
_BUNDLE_SOURCE_PINS = {
    ".github/workflows/pulse_ci.yml": "adae42c8e9777d357ab5400ced5765de7059ed1e",
    "PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py": "8f01602e973b890eb2ae0928bd62dfd65e691f79",
}


def _source_bundle_copies(step: dict[str, Any]) -> list[tuple[bool, str, str]]:
    """Independent finite grammar; never evaluate shell or expand a glob."""
    text = step.get("run")
    _require(isinstance(text, str), "bundle_mapping_run_missing")
    result = []
    pattern = r'cp(?P<tree> -a)?\s+(?P<src>"[A-Za-z0-9_$\{\}./*-]+"(?:/[A-Za-z0-9_.*-]+)*)\s+"(?P<dst>[A-Za-z0-9_$\{\}./-]+)"'
    for statement in text.replace("\\\n", " ").splitlines():
        statement = statement.strip()
        if not statement.startswith("cp "):
            continue
        match = re.fullmatch(pattern, statement)
        _require(match is not None, "bundle_mapping_copy_syntax")
        result.append((match.group("tree") is not None,
                       match.group("src").replace('"', ''), match.group("dst")))
    _require(bool(result) and len(result) == len(set(result)), "bundle_mapping_copy_set")
    return result


def _source_bundle_expectations(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    payloads = {}
    for path in _BUNDLE_SOURCE_PINS:
        item = sources.get(path)
        _require(item is not None, "bundle_mapping_source_missing", path)
        _require(_sha1_git_blob(item.data) == _BUNDLE_SOURCE_PINS[path], "bundle_mapping_source_drift", path)
        payloads[path] = item.data
    recorded = _parse_yaml_document(payloads[SUBJECT_WORKFLOW_PATH], label=SUBJECT_WORKFLOW_PATH)
    for job_name in ("release_grade_recorded_path", "assemble_release_grade_reference_package", "pulse"):
        _require(workflow.get("jobs", {}).get(job_name) == recorded["jobs"][job_name],
                 "bundle_mapping_workflow_drift", job_name)
    steps = workflow["jobs"]["release_grade_recorded_path"]["steps"]
    occ = lambda number: _step_id("release_grade_recorded_path", number)
    audit, advisory = _BUNDLE_ROLES
    # Resolve backward from the upload paths and exported advisory root.
    upload_audit, upload_advisory = steps[27], steps[31]
    publications = {}
    for number, role in ((28, audit), (32, advisory)):
        item = steps[number - 1]; opts = item.get("with", {})
        _require(item.get("uses") == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
                 and opts.get("if-no-files-found") == "error", "bundle_mapping_upload_profile")
        name = opts.get("name")
        _require(isinstance(name, str) and re.fullmatch(r"[a-z0-9-]+", name), "bundle_mapping_upload_name")
        publications[role] = {"name": name, "occurrence": occ(number)}
    audit_root = _checked_mapping_path(upload_audit["with"]["path"].rstrip("/"))
    _require(_checked_mapping_export(steps[21], "BUNDLE") == audit_root, "bundle_mapping_upload_path")
    advisory_root = _checked_mapping_export(steps[24], "BUNDLE_DIR", allow_temp=True)
    export_lines = [line.strip() for line in steps[24]["run"].splitlines() if "REFERENCE_BUNDLE_DIR=" in line]
    _require(upload_advisory["with"]["path"] == "${{ env.REFERENCE_BUNDLE_DIR }}"
             and export_lines == ['echo "REFERENCE_BUNDLE_DIR=${BUNDLE_DIR}" >> "$GITHUB_ENV"'],
             "bundle_mapping_advisory_export")
    ledger = _source_ledger_expectations(workflow)
    paths = dict(ledger["locators"])
    paths.update({"final-status": ledger["status"], audit: audit_root + "/", advisory: advisory_root + "/",
                  "llamaguard-summary": _checked_mapping_export(workflow["jobs"]["pulse"]["steps"][22], "SUMMARY")})
    _require(paths[advisory] == ledger["locators"][advisory], "bundle_mapping_root_disagreement")
    candidate_roles = ("final-status", "quality-ledger-final", "release-authority-manifest",
                       "llamaguard-summary", "release-grade-junit", "release-grade-sarif", audit, advisory)
    _require(len({paths[role].rstrip("/") for role in candidate_roles}) == len(candidate_roles), "bundle_mapping_state_alias")
    copies, inputs = {}, {}
    for number, variable, root, output in ((22, "BUNDLE", audit_root, audit), (25, "BUNDLE_DIR", advisory_root, advisory)):
        members = []
        for recursive, source, destination in _source_bundle_copies(steps[number - 1]):
            prefix = "${" + variable + "}/"
            _require(destination.startswith(prefix), "bundle_mapping_destination_root")
            destination = _checked_mapping_path(root + "/" + destination[len(prefix):].rstrip("/"), allow_temp=True)
            if "*" in source:
                _require(source.count("*") == 1 and source.endswith("/*_summary.json") and not recursive,
                         "bundle_mapping_glob_dialect")
                directory = _checked_mapping_path(source.rsplit("/", 1)[0])
                found = [role for role in candidate_roles if paths[role].rsplit("/", 1)[0] == directory
                         and paths[role].rsplit("/", 1)[1].endswith("_summary.json")]
                _require(found == ["llamaguard-summary"], "bundle_mapping_selected_glob_roles")
                selector = directory + "/*_summary.json"
                kind = "selected_member_of_source_glob"
            else:
                selector = _checked_mapping_path(source)
                found = [role for role in candidate_roles if paths[role].rstrip("/") == selector]
                _require(len(found) == 1, "bundle_mapping_copy_role_missing", selector)
                _require(recursive == (found[0] == audit), "bundle_mapping_copy_kind")
                kind = "tree_copy" if recursive else "file_copy"
            _require(found[0] != output and found[0] not in [entry["role"] for entry in members], "bundle_mapping_copy_alias")
            members.append({"role": found[0], "source_selector": selector,
                            "destination": destination, "copy_kind": kind})
        _require(len(members) == (3 if number == 22 else 7), "bundle_mapping_copy_extent")
        copies[output] = members
        inputs[occ(number)] = sorted(member["role"] for member in members)
    _require("PULSE_safe_pack_v0/artifacts/**" in steps[30]["with"]["path"].splitlines()
             and audit_root.startswith("PULSE_safe_pack_v0/artifacts/"), "bundle_mapping_report_upload")
    assembly = workflow["jobs"]["assemble_release_grade_reference_package"]["steps"]
    # Parse only the exact reviewed gh run download form and prove that S4
    # transports the named audit artifact, while S5 actually reads the tree.
    commands = []
    for line in assembly[3]["run"].replace("\\\n", " ").splitlines():
        if not line.strip().startswith("gh run download "):
            continue
        words = shlex.split(line)
        _require(words[:4] == ["gh", "run", "download", "${GITHUB_RUN_ID}"] and len(words) == 10,
                 "bundle_mapping_named_handoff")
        pairs = dict(zip(words[4::2], words[5::2]))
        _require(set(pairs) == {"--repo", "--name", "--dir"}, "bundle_mapping_named_handoff")
        commands.append(pairs)
    named = [c for c in commands if c["--name"] == publications[audit]["name"]]
    _require(len(named) == 1 and named[0]["--repo"] == "${GITHUB_REPOSITORY}"
             and named[0]["--dir"] == "${AUDIT_BUNDLE_DIR}", "bundle_mapping_named_handoff")
    _require(publications[advisory]["name"] not in [c["--name"] for c in commands], "bundle_mapping_advisory_not_acquired")
    _require('--audit-bundle-dir "${AUDIT_BUNDLE_DIR}"' in assembly[4]["run"], "bundle_mapping_assembler_input")
    module = ast.parse(payloads[next(path for path in payloads if path != SUBJECT_WORKFLOW_PATH)])
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "_stage_package")
    destinations = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "_copy_tree":
            continue
        if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id == "selected_audit":
            _require(len(node.args) == 3, "bundle_mapping_assembler_copy")
            expression = node.args[1]
            _require(isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div)
                     and isinstance(expression.left, ast.Name) and expression.left.id == "staging_dir"
                     and isinstance(expression.right, ast.Constant) and isinstance(expression.right.value, str),
                     "bundle_mapping_assembler_destination")
            destinations.append(expression.right.value)
    _require(len(destinations) == 1, "bundle_mapping_assembler_copy")
    consumers = {role: [publications[role]["occurrence"]] for role in _BUNDLE_ROLES}
    for operation, consumed in inputs.items():
        for role in _BUNDLE_ROLES:
            if role in consumed:
                consumers[role].append(operation)
    consumers[audit] += [occ(31), _step_id("assemble_release_grade_reference_package", 5)]
    return {"locators": {role: paths[role] for role in _BUNDLE_ROLES},
            "producers": {audit: occ(22), advisory: occ(25)},
            "consumers": {role: sorted(values) for role, values in consumers.items()},
            "copy_inputs": inputs, "copies": copies, "publications": publications,
            "input_locators": {role: paths[role] for role in sorted({r for values in inputs.values() for r in values})},
            "package_member": destinations[0], "conditions": {"assembly": steps[24]["if"], "publication": steps[31]["if"]}}


def _apply_bundle_source_expectations(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
    by_role = {entry["state_id"].removeprefix("state:step5c:"): entry for entry in states}
    affected = set(facts["copy_inputs"])
    for state in states:
        state["required_consumer_occurrence_ids"] = [oid for oid in state["required_consumer_occurrence_ids"] if oid not in affected]
    for step in steps.values():
        oid = step["occurrence_id"]
        for key in ("input_state_ids", "output_state_ids"):
            step[key] = [sid for sid in step[key] if sid.removeprefix("state:step5c:") not in _BUNDLE_ROLES]
        if oid in affected:
            step["input_state_ids"] = []
            for role in facts["copy_inputs"][oid]:
                step["input_state_ids"].append("state:step5c:" + role)
                by_role[role]["required_consumer_occurrence_ids"].append(oid)
    for role in _BUNDLE_ROLES:
        record = by_role[role]
        record.update(path_or_uri=facts["locators"][role], producer_occurrence_id=facts["producers"][role],
                      required_consumer_occurrence_ids=list(facts["consumers"][role]))
        for step in steps.values():
            if step["occurrence_id"] in facts["consumers"][role]:
                _append_unique(step["input_state_ids"], record["state_id"])
            if step["occurrence_id"] == facts["producers"][role]:
                _append_unique(step["output_state_ids"], record["state_id"])
    for record in states:
        record["required_consumer_occurrence_ids"] = sorted(set(record["required_consumer_occurrence_ids"]))


def _verify_source_bundle_equations(plan: dict[str, Any], workflow: dict[str, Any], sources: dict[str, GitObject]) -> None:
    facts = _source_bundle_expectations(workflow, sources)
    states = {record["state_id"]: record for record in plan["state_templates"]}
    _require(len(states) == len(plan["state_templates"]), "bundle_mapping_duplicate_role")
    steps = {step["occurrence_id"]: step for job in plan["jobs"] for step in job["steps"]}
    for role in _BUNDLE_ROLES:
        sid = "state:step5c:" + role
        _require(sid in states, "bundle_mapping_role_missing", role)
        row = states[sid]
        _require(row["path_or_uri"] == facts["locators"][role], "bundle_mapping_locator_mismatch", role)
        _require(row["producer_occurrence_id"] == facts["producers"][role], "bundle_mapping_producer_mismatch", role)
        _require(row["required_consumer_occurrence_ids"] == facts["consumers"][role], "bundle_mapping_consumer_mismatch", role)
        _require(row["required"] is True and row["content_requirement"] == "exact_digest"
                 and row["state_type"] == "package" and row["authority_bearing"] is (role == _BUNDLE_ROLES[0])
                 and row["mutation_class"] == "none", "bundle_mapping_requirement_mismatch", role)
        _require(sorted(oid for oid, step in steps.items() if sid in step["input_state_ids"]) == facts["consumers"][role],
                 "bundle_mapping_reader_set_mismatch", role)
        _require([oid for oid, step in steps.items() if sid in step["output_state_ids"]] == [facts["producers"][role]],
                 "bundle_mapping_writer_set_mismatch", role)
    for oid, roles in facts["copy_inputs"].items():
        _require(oid in steps, "bundle_mapping_copy_occurrence_missing")
        expected = ["state:step5c:" + role for role in roles]
        _require(steps[oid]["input_state_ids"] == expected, "bundle_mapping_copy_inputs_mismatch")
        reverse = sorted(sid for sid, row in states.items() if oid in row["required_consumer_occurrence_ids"])
        _require(reverse == expected, "bundle_mapping_reverse_inputs_mismatch")
        produced = ["state:step5c:" + role for role in _BUNDLE_ROLES if facts["producers"][role] == oid]
        _require(steps[oid]["output_state_ids"] == produced, "bundle_mapping_copy_outputs_mismatch")
    for role, path in facts["input_locators"].items():
        _require(states.get("state:step5c:" + role, {}).get("path_or_uri") == path, "bundle_mapping_input_locator_mismatch", role)


def _build_states(
    step_by_key: dict[tuple[str, int], dict[str, Any]],
    case_ids: tuple[str, ...],
    source_workflow: dict[str, Any],
    source_by_path: dict[str, GitObject],
) -> list[dict[str, Any]]:
    source_projection = _source_ledger_expectations(source_workflow)
    recorded_projection = _source_recorded_expectations(source_workflow, source_by_path)
    package_projection = _source_package_expectations(source_workflow, source_by_path)
    argument_projection = _source_required_argument_expectations(source_workflow, source_by_path)
    bundle_projection = _source_bundle_expectations(source_workflow, source_by_path)
    sid = lambda name: f"state:step5c:{name}"
    st = lambda job, ordinal: _step_id(job, ordinal)
    collector = _collector_id()
    states: list[dict[str, Any]] = []

    def add(
        name: str,
        state_type: str,
        role: str,
        path_or_uri: str,
        *,
        producer: str | None,
        consumers: Iterable[str] = (),
        authority: bool = False,
        mutation: str = "none",
        required: bool = True,
        content: str = "exact_digest",
    ) -> str:
        state_id = sid(name)
        states.append(
            _state(
                state_id=state_id,
                state_type=state_type,
                role=role,
                path_or_uri=path_or_uri,
                required=required,
                content_requirement=content,
                producer=producer,
                consumers=consumers,
                authority_bearing=authority,
                mutation_class=mutation,
            )
        )
        return state_id

    workflow = add(
        "workflow-source",
        "workflow_source",
        "subject_workflow_source",
        SUBJECT_WORKFLOW_PATH,
        producer=None,
        consumers=[st("pulse", 1), st("attest_llamaguard_current_run_summary", 1), st("release_grade_recorded_path", 1), st("assemble_release_grade_reference_package", 1), st("verify_release_grade_reference_package", 1), st("tools-tests", 1)],
        authority=True,
    )
    policy = add(
        "gate-policy",
        "policy",
        "declared_gate_policy",
        POLICY_PATH,
        producer=None,
        consumers=[st("pulse", 11), st("pulse", 50), st("pulse", 51), st("release_grade_recorded_path", 21)],
        authority=True,
    )
    registry = add(
        "gate-registry",
        "gate_registry",
        "gate_registry",
        REGISTRY_PATH,
        producer=None,
        consumers=[st("pulse", 11), st("pulse", 50), st("pulse", 51), st("release_grade_recorded_path", 21)],
        authority=True,
    )
    threshold = add(
        "threshold-policy",
        "threshold_policy",
        "external_threshold_policy",
        THRESHOLD_POLICY_PATH,
        producer=None,
        consumers=[st("pulse", 23), st("pulse", 35), st("release_grade_recorded_path", 6), st("release_grade_recorded_path", 8)],
        authority=True,
    )
    signer = add(
        "external-signer-policy",
        "external_signer_policy",
        "external_signer_policy",
        EXTERNAL_SIGNER_POLICY_PATH,
        producer=None,
        consumers=[st("attest_llamaguard_current_run_summary", 6), st("attest_llamaguard_current_run_summary", 7), st("release_grade_recorded_path", 5), st("release_grade_recorded_path", 8)],
        authority=True,
    )
    dataset = add(
        "llamaguard-dataset",
        "release_evidence",
        "controlled_llamaguard_case_dataset",
        LLAMAGUARD_DATASET_PATH,
        producer=None,
        consumers=[st("pulse", 22)],
        authority=True,
    )

    required_gate = add(
        "required-gate-evidence",
        "release_evidence",
        "current_run_required_gate_evidence",
        "PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json",
        producer=st("pulse", 11),
        consumers=[st("pulse", 12), st("pulse", 13), st("pulse", 18), st("release_grade_recorded_path", 4)],
        authority=True,
    )
    status_baseline = add(
        "status-baseline",
        "status",
        "pre_augmentation_status",
        "PULSE_safe_pack_v0/artifacts/status_baseline.json",
        producer=st("pulse", 14),
        consumers=[st("pulse", 15), st("release_grade_recorded_path", 4)],
        authority=True,
    )
    evidence_floor = add(
        "self-contained-evidence-floor",
        "release_evidence",
        "self_contained_pulse_evidence_floor",
        "PULSE_safe_pack_v0/artifacts/self_contained_pulse_evidence_floor_v0.json",
        producer=st("pulse", 18),
        consumers=[st("pulse", 19), st("release_grade_recorded_path", 4)],
        authority=True,
    )
    raw_evidence = add(
        "llamaguard-raw-evidence",
        "release_evidence",
        "llamaguard_raw_evidence",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_raw.jsonl",
        producer=st("pulse", 22),
        consumers=[st("pulse", 23), st("pulse", 24), st("attest_llamaguard_current_run_summary", 4)],
        authority=True,
    )
    evaluator_manifest = add(
        "llamaguard-evaluator-manifest",
        "manifest",
        "llamaguard_evaluator_manifest",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_evaluator_manifest_v0.json",
        producer=st("pulse", 22),
        consumers=[st("pulse", 23), st("pulse", 24), st("attest_llamaguard_current_run_summary", 4)],
        authority=True,
    )
    summary = add(
        "llamaguard-summary",
        "release_evidence",
        "canonical_llamaguard_summary",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.json",
        producer=st("pulse", 23),
        consumers=[st("pulse", 24), st("pulse", 35), st("attest_llamaguard_current_run_summary", 4), st("attest_llamaguard_current_run_summary", 5)],
        authority=True,
    )
    preattestation = add(
        "pre-attestation-pulse-artifacts",
        "package",
        "pre_attestation_pulse_artifact",
        source_projection["locators"]['pre-attestation-pulse-artifacts'],
        producer=st("pulse", 37),
        consumers=[st("release_grade_recorded_path", 4)],
        authority=True,
    )
    attestation_bundle = add(
        "llamaguard-attestation-bundle",
        "attestation",
        "llamaguard_attestation_bundle",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.bundle.json",
        producer=st("attest_llamaguard_current_run_summary", 5),
        consumers=[st("attest_llamaguard_current_run_summary", 6), st("attest_llamaguard_current_run_summary", 7), st("attest_llamaguard_current_run_summary", 8), st("release_grade_recorded_path", 5)],
        authority=True,
    )
    attestation_envelope = add(
        "llamaguard-attestation-envelope",
        "attestation",
        "llamaguard_external_summary_envelope",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.envelope.json",
        producer=st("attest_llamaguard_current_run_summary", 6),
        consumers=[st("attest_llamaguard_current_run_summary", 7), st("attest_llamaguard_current_run_summary", 8), st("release_grade_recorded_path", 5)],
        authority=True,
    )
    attestation_verifier = add(
        "llamaguard-attestation-verifier",
        "verifier_report",
        "llamaguard_attestation_verifier",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_attestation_verifier_v1.json",
        producer=st("attest_llamaguard_current_run_summary", 7),
        consumers=[st("attest_llamaguard_current_run_summary", 8), st("release_grade_recorded_path", 5), st("release_grade_recorded_path", 8)],
        authority=True,
    )
    candidate_index = add(
        "recorded-candidate-index",
        "candidate_state",
        "recorded_release_candidate_index",
        recorded_projection["locators"]['recorded-candidate-index'],
        producer=st("release_grade_recorded_path", 6),
        consumers=[],
        authority=True,
    )
    evidence_manifest = add(
        "release-evidence-input-manifest",
        "manifest",
        "release_evidence_input_manifest",
        recorded_projection["locators"]['release-evidence-input-manifest'],
        producer=st("release_grade_recorded_path", 7),
        consumers=[],
        authority=True,
    )
    evidence_verifier = add(
        "recorded-release-evidence-verifier",
        "verifier_report",
        "recorded_release_evidence_verifier",
        recorded_projection["locators"]['recorded-release-evidence-verifier'],
        producer=st("release_grade_recorded_path", 8),
        consumers=[],
        authority=True,
    )
    materialized = add(
        "materialized-release-required-gate-set",
        "candidate_state",
        "policy_selected_release_required_status_gate_values",
        recorded_projection["locators"]['materialized-release-required-gate-set'],
        producer=st("release_grade_recorded_path", 9),
        consumers=[],
        authority=True,
        mutation="materialized_gate_set",
    )
    final_status = add(
        "final-status",
        "status",
        "final_release_grade_status",
        recorded_projection["locators"]['final-status'],
        producer=st("release_grade_recorded_path", 9),
        consumers=[st("release_grade_recorded_path", 21), st("release_grade_recorded_path", 23)],
        authority=True,
        mutation="final_status",
    )
    pre_materialization = add(
        "pre-materialization-status", "status", "pre_release_required_materialization_status",
        recorded_projection["locators"]["pre-materialization-status"],
        producer=recorded_projection["pre_status_origin"], consumers=[], authority=True,
    )
    candidate_envelopes = add(
        "recorded-release-candidate-envelopes", "candidate_state", "recorded_release_candidate_envelope_tree",
        recorded_projection["locators"]["recorded-release-candidate-envelopes"],
        producer=st("release_grade_recorded_path", 6), consumers=[], authority=True,
    )
    ledger_pre = add(
        "quality-ledger-pre-authority",
        "quality_ledger",
        "release_grade_quality_ledger_before_authority_insertion",
        source_projection["locators"]['quality-ledger-pre-authority'],
        producer=st("release_grade_recorded_path", 13),
        consumers=[],
        authority=True,
    )
    status_summary = add(
        "final-status-summary",
        "report",
        "final_release_grade_status_summary",
        source_projection["locators"]['final-status-summary'],
        producer=st("release_grade_recorded_path", 14),
        consumers=[],
        authority=True,
    )
    decision = add(
        "release-decision",
        "release_decision",
        "final_release_decision",
        source_projection["locators"]['release-decision'],
        producer=st("release_grade_recorded_path", 15),
        consumers=[st("release_grade_recorded_path", 21), st("release_grade_recorded_path", 30)],
        authority=True,
        mutation="release_decision",
    )
    decision_ledger = add(
        "release-decision-ledger-section",
        "report",
        "release_decision_ledger_section",
        source_projection["locators"]['release-decision-ledger-section'],
        producer=st("release_grade_recorded_path", 16),
        consumers=[],
        authority=True,
    )
    authority_manifest = add(
        "release-authority-manifest",
        "release_authority",
        "final_release_authority_manifest",
        source_projection["locators"]['release-authority-manifest'],
        producer=st("release_grade_recorded_path", 17),
        consumers=[st("release_grade_recorded_path", 21), st("release_grade_recorded_path", 27)],
        authority=True,
    )
    ledger_final = add(
        "quality-ledger-final",
        "quality_ledger",
        "final_release_grade_quality_ledger",
        source_projection["locators"]['quality-ledger-final'],
        producer=st("release_grade_recorded_path", 18),
        consumers=[st("release_grade_recorded_path", 31)],
        authority=True,
    )
    decision_report = add(
        "release-decision-report",
        "report",
        "composed_release_decision_report",
        source_projection["locators"]['release-decision-report'],
        producer=st("release_grade_recorded_path", 19),
        consumers=[st("release_grade_recorded_path", 31)],
        authority=True,
    )
    artifact_binding = add(
        "artifact-provenance-binding",
        "manifest",
        "final_release_authority_artifact_binding",
        "PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json",
        producer=st("release_grade_recorded_path", 21),
        consumers=[st("release_grade_recorded_path", 29), st("attest_release_grade_artifact_binding", 1), st("assemble_release_grade_reference_package", 4)],
        authority=True,
    )
    audit_bundle = add(
        "release-authority-audit-bundle",
        "package",
        "final_release_authority_audit_bundle",
        bundle_projection["locators"]["release-authority-audit-bundle"],
        producer=bundle_projection["producers"]["release-authority-audit-bundle"],
        consumers=bundle_projection["consumers"]["release-authority-audit-bundle"],
        authority=True,
    )
    junit = add(
        "release-grade-junit",
        "junit",
        "final_release_grade_junit",
        source_projection["locators"]['release-grade-junit'],
        producer=st("release_grade_recorded_path", 23),
        consumers=[st("release_grade_recorded_path", 26), st("release_grade_recorded_path", 33)],
        authority=False,
    )
    sarif = add(
        "release-grade-sarif",
        "sarif",
        "final_release_grade_sarif",
        source_projection["locators"]['release-grade-sarif'],
        producer=st("release_grade_recorded_path", 23),
        consumers=[st("release_grade_recorded_path", 26), st("release_grade_recorded_path", 33)],
        authority=False,
    )
    advisory_bundle = add(
        "advisory-reference-bundle",
        "package",
        "advisory_release_grade_reference_bundle",
        bundle_projection["locators"]["advisory-reference-bundle"],
        producer=bundle_projection["producers"]["advisory-reference-bundle"],
        consumers=bundle_projection["consumers"]["advisory-reference-bundle"],
        authority=False,
    )
    binding_attestation = add(
        "artifact-binding-attestation",
        "attestation",
        "final_release_grade_artifact_binding_attestation",
        "attestation://artifact_provenance_binding_v0.json",
        producer=st("attest_release_grade_artifact_binding", 2),
        consumers=[],
        authority=True,
    )
    complete_package = add(
        "complete-release-grade-reference-package",
        "package",
        "complete_release_grade_reference_package",
        package_projection["locators"]["complete-release-grade-reference-package"],
        producer=package_projection["producers"]["complete-release-grade-reference-package"],
        consumers=package_projection["consumers"]["complete-release-grade-reference-package"],
        authority=False,
    )
    package_completeness = add(
        "package-completeness-report",
        "verifier_report",
        "release_grade_package_completeness_report",
        package_projection["locators"]["package-completeness-report"],
        producer=package_projection["producers"]["package-completeness-report"],
        consumers=package_projection["consumers"]["package-completeness-report"],
        authority=False,
    )
    package_verification = add(
        "package-verification-report",
        "verifier_report",
        "release_grade_reference_package_verification_report",
        package_projection["locators"]["package-verification-report"],
        producer=package_projection["producers"]["package-verification-report"],
        consumers=package_projection["consumers"]["package-verification-report"],
        authority=False,
    )
    step3f_carrier = add(
        "step3f-current-run-carrier",
        "carrier",
        "step3f_finalized_current_run_carrier",
        "provider-artifact://step3f/current-run-carrier",
        producer=None,
        consumers=[collector],
        authority=False,
        mutation="preservation_output",
    )
    step3f_expectation = add(
        "step3f-current-run-expectation",
        "expectation",
        "step3f_observed_expectation",
        "provider-artifact://step3f/expectation.json",
        producer=None,
        consumers=[collector],
        authority=False,
        mutation="preservation_output",
    )
    step3f_subject_input = add(
        "step3f-subject-input-packet",
        "subject_input_packet",
        "step3f_observed_subject_input_packet",
        "provider-artifact://step3f/subject-input-packet.json",
        producer=None,
        consumers=[collector],
        authority=False,
        mutation="preservation_output",
    )
    runtime_packet = add(
        "runtime-observation-packet",
        "runtime_observation_packet",
        "step5c_generic_runtime_observation_packet",
        "reconstruction://runtime-observation-packet.json",
        producer=collector,
        consumers=[],
        authority=False,
        mutation="advisory_output",
    )
    runtime_diagnostic = add(
        "runtime-observation-diagnostic",
        "diagnostic",
        "step5c_runtime_packet_diagnostic",
        "reconstruction://runtime-observation-diagnostic.json",
        producer=collector,
        consumers=[],
        authority=False,
        mutation="advisory_output",
    )
    binding_report = add(
        "compute-binding-report",
        "report",
        "step5c_runtime_bound_compute_binding_report",
        "reconstruction://compute-binding-report.json",
        producer=collector,
        consumers=[],
        authority=False,
        mutation="advisory_output",
    )
    relation = add(
        "planned-observed-relation",
        "report",
        "step5c_planned_observed_relation",
        "reconstruction://planned-observed-relation.json",
        producer=collector,
        consumers=[],
        authority=False,
        mutation="advisory_output",
    )
    folded = add(
        "folded-non-active-candidate-status",
        "candidate_state",
        "step5c_folded_non_active_candidate_status",
        "reconstruction://folded-candidate-status.json",
        producer=collector,
        consumers=[],
        authority=False,
        mutation="advisory_output",
    )

    # Bind the highest-value source and artifact states to the applicable steps.
    _bind_step_states(
        step_by_key,
        inputs=[
            ("pulse", 1, workflow),
            ("pulse", 11, policy),
            ("pulse", 11, registry),
            ("pulse", 22, dataset),
            ("pulse", 23, raw_evidence),
            ("pulse", 23, evaluator_manifest),
            ("pulse", 23, threshold),
            ("pulse", 35, summary),
            ("pulse", 35, threshold),
            ("release_grade_recorded_path", 4, preattestation),
            ("release_grade_recorded_path", 5, attestation_bundle),
            ("release_grade_recorded_path", 5, attestation_envelope),
            ("release_grade_recorded_path", 5, attestation_verifier),
            ("release_grade_recorded_path", 8, signer),
            ("release_grade_recorded_path", 21, final_status),
            ("release_grade_recorded_path", 21, decision),
            ("release_grade_recorded_path", 21, authority_manifest),
            ("attest_release_grade_artifact_binding", 1, artifact_binding),
            ("assemble_release_grade_reference_package", 4, artifact_binding),
        ],
        outputs=[
            ("pulse", 11, required_gate),
            ("pulse", 14, status_baseline),
            ("pulse", 18, evidence_floor),
            ("pulse", 22, raw_evidence),
            ("pulse", 22, evaluator_manifest),
            ("pulse", 23, summary),
            ("pulse", 37, preattestation),
            ("attest_llamaguard_current_run_summary", 5, attestation_bundle),
            ("attest_llamaguard_current_run_summary", 6, attestation_envelope),
            ("attest_llamaguard_current_run_summary", 7, attestation_verifier),
            ("release_grade_recorded_path", 21, artifact_binding),
            ("release_grade_recorded_path", 23, junit),
            ("release_grade_recorded_path", 23, sarif),
            ("attest_release_grade_artifact_binding", 2, binding_attestation),
        ],
    )

    for case_id in case_ids:
        input_state = add(
            f"llamaguard-input:{case_id}",
            "release_evidence",
            f"llamaguard_case_input:{case_id}",
            f"dataset://{LLAMAGUARD_DATASET_PATH}#{case_id}/input",
            producer=None,
            consumers=[st("pulse", 22)],
            authority=True,
        )
        output_state = add(
            f"llamaguard-output:{case_id}",
            "release_evidence",
            f"llamaguard_case_output:{case_id}",
            f"artifact://llamaguard_raw.jsonl#{case_id}/classification",
            producer=st("pulse", 22),
            consumers=[st("pulse", 23)],
            authority=True,
        )
        _bind_step_states(
            step_by_key,
            inputs=[("pulse", 22, input_state)],
            outputs=[("pulse", 22, output_state)],
        )

    _apply_source_ledger_expectations(states, step_by_key, source_projection)
    _apply_recorded_source_expectations(states, step_by_key, recorded_projection)

    _apply_package_source_expectations(states, step_by_key, package_projection)

    _apply_bundle_source_expectations(states, step_by_key, bundle_projection)

    # Observer-side source derivation only. R12's array construction and
    # checker consumption are internal to one step; the v0 occurrence graph
    # cannot express them as an additional observed producer/read pair.
    add(
        _REQUIRED_ARGUMENT_ROLE, "other",
        "source_derived_required_arguments_runtime_receipt_unavailable",
        argument_projection["locator"], producer=None, consumers=[],
        authority=False, content="exact_digest",
    )

    # Make deterministic reference arrays after all bindings are complete.
    for step in step_by_key.values():
        step["input_state_ids"] = sorted(step["input_state_ids"])
        step["output_state_ids"] = sorted(step["output_state_ids"])

    return sorted(states, key=lambda row: row["state_id"])


def _build_model_inferences(
    *,
    case_ids: tuple[str, ...],
    model_id: str,
    model_revision: str,
) -> list[dict[str, Any]]:
    parent = _step_id("pulse", 22)
    result = []
    for case_id in case_ids:
        result.append(
            {
                "inference_id": f"inference:step5c:llamaguard:{case_id}",
                "case_id": case_id,
                "parent_occurrence_id": parent,
                "model_id": model_id,
                "model_revision": model_revision,
                "input_state_id": f"state:step5c:llamaguard-input:{case_id}",
                "output_state_id": f"state:step5c:llamaguard-output:{case_id}",
                "required": True,
                "timing_requirement": "partial",
                "raw_prompt_included": False,
                "raw_output_included": False,
            }
        )
    return result


def _tool_identity(source: GitObject, *, tool_id: str) -> dict[str, Any]:
    return {
        "tool_id": tool_id,
        "version": TOOL_VERSION,
        "source_path": source.path,
        "source_revision": source.revision,
        "source_sha256": source.sha256,
    }


def _validate_internal_references(context: PlanBuildContext) -> None:
    jobs = context.jobs
    all_executions = {_collector_id()}
    all_executions.update(job["occurrence_id"] for job in jobs)
    all_steps: list[dict[str, Any]] = []
    for job in jobs:
        for step in job["steps"]:
            all_steps.append(step)
            all_executions.add(step["occurrence_id"])

    _require(len(jobs) == TERMINAL_COUNTS["job_templates"], "internal_job_count_mismatch")
    _require(len(all_steps) == TERMINAL_COUNTS["step_templates"], "internal_step_count_mismatch")
    successful_jobs = sum(job["expected_terminal_result"] == "success" for job in jobs)
    skipped_jobs = sum(job["expected_terminal_result"] == "skipped" for job in jobs)
    successful_steps = sum(step["expected_terminal_result"] == "success" for step in all_steps)
    skipped_steps = sum(step["expected_terminal_result"] == "skipped" for step in all_steps)
    uninstantiated = sum(step["expected_terminal_result"] == "not_instantiated" for step in all_steps)
    instantiated = sum(step["expected_runtime_presence"] for step in all_steps)
    _require(successful_jobs == 7 and skipped_jobs == 1, "internal_job_result_counts_mismatch")
    _require(successful_steps == 101, "internal_success_step_count_mismatch")
    _require(skipped_steps == 44, "internal_skipped_step_count_mismatch")
    _require(uninstantiated == 2, "internal_uninstantiated_step_count_mismatch")
    _require(instantiated == 145, "internal_instantiated_step_count_mismatch")

    operations = {row["call_id"]: row for row in context.external_operations}
    inferences = {row["inference_id"]: row for row in context.model_inferences}
    states = {row["state_id"]: row for row in context.state_templates}
    _require(len(operations) == len(context.external_operations), "duplicate_external_operation_id")
    _require(len(inferences) == len(context.model_inferences) == 6, "duplicate_or_missing_inference_id")
    _require(len(states) == len(context.state_templates), "duplicate_state_id")

    for step in all_steps:
        _require(all(value in operations for value in step["external_operation_ids"]), "step_external_operation_unresolved", step["occurrence_id"])
        _require(all(value in inferences for value in step["model_inference_ids"]), "step_inference_unresolved", step["occurrence_id"])
        _require(all(value in states for value in step["input_state_ids"] + step["output_state_ids"]), "step_state_unresolved", step["occurrence_id"])
        _require(set(step["input_state_ids"]).isdisjoint(step["output_state_ids"]), "step_input_output_state_overlap", step["occurrence_id"])

    for operation in context.external_operations:
        parent = operation["parent_occurrence_id"]
        _require(parent is None or parent in all_executions, "external_operation_parent_unresolved", operation["call_id"])

    for inference in context.model_inferences:
        _require(inference["parent_occurrence_id"] in all_executions, "inference_parent_unresolved", inference["inference_id"])
        _require(inference["input_state_id"] in states, "inference_input_state_unresolved", inference["inference_id"])
        _require(inference["output_state_id"] in states, "inference_output_state_unresolved", inference["inference_id"])

    for state in context.state_templates:
        producer = state["producer_occurrence_id"]
        _require(producer is None or producer in all_executions, "state_producer_unresolved", state["state_id"])
        _require(all(value in all_executions for value in state["required_consumer_occurrence_ids"]), "state_consumer_unresolved", state["state_id"])


def _schema_validate(plan: dict[str, Any], schema_bytes: bytes) -> None:
    schema = _strict_json_object(schema_bytes, label=SCHEMA_PATH)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise PlanError("evidence_schema_invalid") from exc
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(plan),
        key=lambda item: [str(part) for part in item.absolute_path],
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise PlanError("generated_plan_schema_rejected", f"{location}: {first.message}")


def _reconstruct_expected_plan(
    *,
    repository_root: Path,
    source_commit: str,
    record_status: str,
    plan_id: str | None = None,
) -> dict[str, Any]:
    root = _validate_repository_root(repository_root)
    revision = _validate_source_commit(source_commit)
    _require(record_status in {"example", "observed"}, "record_status_invalid")

    object_type = _git(root, ["cat-file", "-t", revision]).decode("ascii", errors="strict")
    _require(object_type == "commit\n", "source_commit_object_required")
    head = _git(root, ["rev-parse", "HEAD"]).decode("ascii", errors="strict").strip().lower()
    _require(head == revision, "checked_out_head_mismatch", f"head={head} source={revision}")

    source_by_path = _load_sources(root, revision)
    subject_workflow = _parse_yaml_document(
        source_by_path[SUBJECT_WORKFLOW_PATH].data,
        label=SUBJECT_WORKFLOW_PATH,
    )
    provider_workflow = _parse_yaml_document(
        source_by_path[PROVIDER_WORKFLOW_PATH].data,
        label=PROVIDER_WORKFLOW_PATH,
    )
    _require(
        provider_workflow.get("name") == "PULSEmech compute current-run export candidate",
        "provider_workflow_name_mismatch",
    )
    provider_triggers = provider_workflow.get("on")
    _require(isinstance(provider_triggers, dict) and set(provider_triggers) == {"workflow_dispatch"}, "provider_trigger_mismatch")

    jobs, step_by_key, external_operations = _build_jobs(subject_workflow)
    case_ids = _load_case_ids(source_by_path[LLAMAGUARD_DATASET_PATH].data)
    runner_bytes = source_by_path[LLAMAGUARD_RUNNER_PATH].data
    model_id = _python_constant(runner_bytes, name="MODEL_ID", label=LLAMAGUARD_RUNNER_PATH)
    model_revision = _python_constant(runner_bytes, name="MODEL_REVISION", label=LLAMAGUARD_RUNNER_PATH)
    _require(model_id == EXPECTED_MODEL_ID, "llamaguard_model_id_mismatch")
    _require(model_revision == EXPECTED_MODEL_REVISION, "llamaguard_model_revision_mismatch")

    model_inferences = _build_model_inferences(
        case_ids=case_ids,
        model_id=model_id,
        model_revision=model_revision,
    )
    state_templates = _build_states(step_by_key, case_ids, subject_workflow, source_by_path)

    context = PlanBuildContext(
        source_commit=revision,
        source_by_path=source_by_path,
        jobs=jobs,
        step_by_key=step_by_key,
        external_operations=external_operations,
        model_inferences=model_inferences,
        state_templates=state_templates,
    )
    _validate_internal_references(context)

    builder_source = source_by_path[BUILDER_PATH]
    checker_source = source_by_path[PLAN_CHECKER_PATH]
    actual_plan_id = _validate_plan_id(plan_id or f"step5c-plan:{revision}")

    source_inventory = [
        source_by_path[path].descriptor()
        for _role, path in sorted(SOURCE_ROLES, key=lambda item: item[1])
    ]

    plan = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "record_status": record_status,
        "plan_identity": {
            "plan_id": actual_plan_id,
            "profile": PROFILE,
            "scope": SCOPE,
            "repository": REPOSITORY,
            "source_commit": revision,
            "source_ref": SOURCE_REF,
            "source_release_candidate_value": SOURCE_RELEASE_CANDIDATE,
            "evidence_release_candidate_template": EVIDENCE_CANDIDATE_TEMPLATE,
            "builder": _tool_identity(builder_source, tool_id=TOOL_ID),
            "independent_checker": _tool_identity(
                checker_source,
                tool_id="check_pulsemech_compute_whole_runtime_observation_plan_v0",
            ),
        },
        "subject_dispatch": {
            "api_version": API_VERSION,
            "method": "POST",
            "accept": API_ACCEPT,
            "endpoint": SUBJECT_DISPATCH_ENDPOINT,
            "ref": "main",
            "inputs": {
                "strict_external_evidence": "true",
                "llamaguard_evidence_mode": "hosted_full_runtime",
            },
            "response_contract": {
                "http_status": 200,
                "required_fields": ["workflow_run_id", "run_url", "html_url"],
                "run_list_fallback_allowed": False,
                "accepted_attempt": 1,
            },
        },
        "provider_dispatch": {
            "api_version": API_VERSION,
            "method": "POST",
            "accept": API_ACCEPT,
            "endpoint": PROVIDER_DISPATCH_ENDPOINT,
            "ref": "main",
            "input_bindings": {
                "source_run_id": "subject_dispatch.workflow_run_id",
            },
            "response_contract": {
                "http_status": 200,
                "required_fields": ["workflow_run_id", "run_url", "html_url"],
                "run_list_fallback_allowed": False,
                "accepted_attempt": 1,
            },
        },
        "source_inventory": source_inventory,
        "finite_limits": dict(FINITE_LIMITS),
        "jobs": jobs,
        "state_templates": state_templates,
        "external_operation_templates": external_operations,
        "model_inference_templates": model_inferences,
        "terminal_counts": dict(TERMINAL_COUNTS),
        "lifecycle_boundary": dict(LIFECYCLE_BOUNDARY),
        "result_boundary": dict(RESULT_BOUNDARY),
        "privacy_boundary": dict(PRIVACY_BOUNDARY),
        "trust_boundary": {
            "trusted_components": sorted(TRUST_BOUNDARY["trusted_components"]),
            "not_proven": sorted(TRUST_BOUNDARY["not_proven"]),
        },
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "errors": [],
        "ok": True,
    }

    _schema_validate(plan, source_by_path[SCHEMA_PATH].data)
    # Rendering is also a final NFC/type check and is intentionally deterministic.
    _canonical_json_bytes(plan)
    return plan



@dataclass(frozen=True)
class CapturedPlan:
    path: Path
    data: bytes
    size_bytes: int
    sha256: str
    device: int
    inode: int


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _capture_plan(path_value: Path) -> CapturedPlan:
    path = Path(os.path.abspath(os.fspath(path_value)))
    _require(path.name not in {"", ".", ".."}, "plan_path_invalid", str(path))
    _require(path.parent.is_dir(), "plan_parent_not_directory", str(path.parent))

    required = ("O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")
    missing = [name for name in required if not hasattr(os, name)]
    _require(os.name == "posix" and not missing, "secure_plan_read_unavailable", ",".join(missing))

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    parts = path.parts
    _require(path.is_absolute() and len(parts) >= 2, "plan_path_not_absolute", str(path))

    directory_fd = os.open(parts[0], directory_flags)
    file_fd: int | None = None
    try:
        for component in parts[1:-1]:
            _require(component not in {"", ".", ".."}, "unsafe_plan_path_component", component)
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd

        file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fd)
        before = os.fstat(file_fd)
        _require(stat.S_ISREG(before.st_mode), "plan_not_regular_file", str(path))
        _require(before.st_nlink == 1, "plan_link_count_invalid", str(before.st_nlink))
        _require(0 < before.st_size <= MAX_PLAN_BYTES, "plan_size_out_of_range", str(before.st_size))

        chunks: list[bytes] = []
        remaining = before.st_size + 1
        while remaining > 0:
            chunk = os.read(file_fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(file_fd)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
            before.st_nlink,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_nlink,
        )
        _require(identity_before == identity_after, "plan_changed_during_read")
        _require(len(data) == after.st_size, "plan_read_size_mismatch")

        named = os.stat(parts[-1], dir_fd=directory_fd, follow_symlinks=False)
        named_identity = (
            named.st_dev,
            named.st_ino,
            named.st_size,
            named.st_mtime_ns,
            named.st_ctime_ns,
            named.st_nlink,
        )
        _require(named_identity == identity_after, "plan_replaced_during_read")

        return CapturedPlan(
            path=path,
            data=data,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            device=after.st_dev,
            inode=after.st_ino,
        )
    except OSError as exc:
        raise PlanError("secure_plan_read_failed", type(exc).__name__) from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(directory_fd)


def _validate_sha256(value: str, *, label: str) -> str:
    normalized = value.strip().lower()
    _require(SHA256_RE.fullmatch(normalized) is not None, f"{label}_not_sha256")
    return normalized


def _schema_validate_supplied_plan(
    *,
    plan: dict[str, Any],
    schema_bytes: bytes,
) -> None:
    schema = _strict_json_object(schema_bytes, label=SCHEMA_PATH)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise PlanError("evidence_schema_invalid") from exc
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(plan),
        key=lambda item: [str(part) for part in item.absolute_path],
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise PlanError("supplied_plan_schema_rejected", f"{location}: {first.message}")


def _plan_counts(plan: dict[str, Any]) -> dict[str, int]:
    jobs = plan.get("jobs")
    states = plan.get("state_templates")
    operations = plan.get("external_operation_templates")
    inferences = plan.get("model_inference_templates")
    _require(isinstance(jobs, list), "plan_jobs_not_array")
    _require(isinstance(states, list), "plan_states_not_array")
    _require(isinstance(operations, list), "plan_operations_not_array")
    _require(isinstance(inferences, list), "plan_inferences_not_array")

    steps: list[dict[str, Any]] = []
    for job in jobs:
        _require(isinstance(job, dict), "plan_job_not_object")
        raw_steps = job.get("steps")
        _require(isinstance(raw_steps, list), "plan_job_steps_not_array")
        _require(all(isinstance(step, dict) for step in raw_steps), "plan_step_not_object")
        steps.extend(raw_steps)

    return {
        "job_templates": len(jobs),
        "step_templates": len(steps),
        "instantiated_steps": sum(
            step.get("expected_runtime_presence") is True for step in steps
        ),
        "successful_steps": sum(
            step.get("expected_terminal_result") == "success" for step in steps
        ),
        "permitted_skipped_steps": sum(
            step.get("expected_terminal_result") == "skipped" for step in steps
        ),
        "uninstantiated_steps": sum(
            step.get("expected_terminal_result") == "not_instantiated"
            for step in steps
        ),
        "state_templates": len(states),
        "external_operation_templates": len(operations),
        "model_inference_templates": len(inferences),
    }


def _check_sorted_and_unique(plan: dict[str, Any]) -> None:
    inventory = plan.get("source_inventory")
    states = plan.get("state_templates")
    operations = plan.get("external_operation_templates")
    inferences = plan.get("model_inference_templates")
    jobs = plan.get("jobs")
    for value, code in (
        (inventory, "source_inventory_not_array"),
        (states, "state_templates_not_array"),
        (operations, "external_operation_templates_not_array"),
        (inferences, "model_inference_templates_not_array"),
        (jobs, "jobs_not_array"),
    ):
        _require(isinstance(value, list), code)

    def identifiers(rows: list[Any], field: str, code: str) -> list[str]:
        values: list[str] = []
        for row in rows:
            _require(isinstance(row, dict), code)
            value = row.get(field)
            _require(isinstance(value, str), code)
            values.append(value)
        _require(len(values) == len(set(values)), f"{code}_duplicate")
        return values

    source_paths = identifiers(inventory, "path", "source_inventory_path_invalid")
    state_ids = identifiers(states, "state_id", "state_id_invalid")
    call_ids = identifiers(operations, "call_id", "call_id_invalid")
    inference_ids = identifiers(inferences, "inference_id", "inference_id_invalid")
    job_ids = identifiers(jobs, "occurrence_id", "job_occurrence_id_invalid")

    _require(source_paths == sorted(source_paths), "source_inventory_not_sorted")
    _require(state_ids == sorted(state_ids), "state_templates_not_sorted")
    _require(call_ids == sorted(call_ids), "external_operations_not_sorted")
    expected_inference_ids = [
        f"inference:step5c:llamaguard:{case_id}"
        for case_id in EXPECTED_CASE_IDS
    ]
    _require(
        inference_ids == expected_inference_ids,
        "model_inference_order_mismatch",
    )
    _require(len(job_ids) == len(set(job_ids)), "job_occurrence_id_duplicate")

    step_ids: list[str] = []
    for job in jobs:
        steps = job.get("steps")
        _require(isinstance(steps, list), "job_steps_not_array")
        ordinals: list[int] = []
        for step in steps:
            _require(isinstance(step, dict), "step_not_object")
            step_id = step.get("occurrence_id")
            ordinal = step.get("source_ordinal")
            _require(isinstance(step_id, str), "step_occurrence_id_invalid")
            _require(type(ordinal) is int, "step_source_ordinal_invalid")
            step_ids.append(step_id)
            ordinals.append(ordinal)
        _require(ordinals == list(range(1, len(ordinals) + 1)), "step_source_order_invalid")
    _require(len(step_ids) == len(set(step_ids)), "step_occurrence_id_duplicate")


def _verify_tool_identity(
    *,
    plan: dict[str, Any],
    source_by_path: dict[str, GitObject],
    source_commit: str,
) -> None:
    identity = plan.get("plan_identity")
    _require(isinstance(identity, dict), "plan_identity_not_object")
    builder = identity.get("builder")
    checker = identity.get("independent_checker")
    _require(isinstance(builder, dict), "builder_identity_not_object")
    _require(isinstance(checker, dict), "checker_identity_not_object")

    expected_builder = _tool_identity(
        source_by_path[BUILDER_PATH],
        tool_id=TOOL_ID,
    )
    expected_checker = _tool_identity(
        source_by_path[PLAN_CHECKER_PATH],
        tool_id=CHECKER_TOOL_ID,
    )
    _require(builder == expected_builder, "builder_source_identity_mismatch")
    _require(checker == expected_checker, "checker_source_identity_mismatch")
    _require(builder.get("source_revision") == source_commit, "builder_revision_mismatch")
    _require(checker.get("source_revision") == source_commit, "checker_revision_mismatch")


def check_plan(
    *,
    repository_root: Path,
    plan_path: Path,
    expected_source_commit: str,
    expected_plan_sha256: str,
    expected_record_status: str,
    expected_plan_id: str | None,
) -> dict[str, Any]:
    root = _validate_repository_root(repository_root)
    source_commit = _validate_source_commit(expected_source_commit)
    expected_digest = _validate_sha256(
        expected_plan_sha256,
        label="expected_plan_sha256",
    )
    _require(
        expected_record_status in {"example", "observed"},
        "expected_record_status_invalid",
    )
    resolved_plan_id = _validate_plan_id(
        expected_plan_id or f"step5c-plan:{source_commit}"
    )

    captured = _capture_plan(plan_path)
    _require(captured.sha256 == expected_digest, "plan_digest_mismatch")
    plan = _strict_json_object(captured.data, label="prelaunch_plan")
    _require(
        _canonical_json_bytes(plan) == captured.data,
        "plan_not_canonical_json",
    )

    source_by_path = _load_sources(root, source_commit)
    expected_checker_path = Path(
        os.path.abspath(os.fspath(root / PLAN_CHECKER_PATH))
    )
    _require(
        EXECUTED_CHECKER_PATH == expected_checker_path,
        "checker_installation_path_mismatch",
    )
    executed_checker = _capture_plan(EXECUTED_CHECKER_PATH)
    _require(
        executed_checker.data == source_by_path[PLAN_CHECKER_PATH].data,
        "executed_checker_source_mismatch",
    )
    _schema_validate_supplied_plan(
        plan=plan,
        schema_bytes=source_by_path[SCHEMA_PATH].data,
    )

    _require(plan.get("record_type") == RECORD_TYPE, "plan_record_type_mismatch")
    _require(
        plan.get("record_status") == expected_record_status,
        "plan_record_status_mismatch",
    )
    identity = plan.get("plan_identity")
    _require(isinstance(identity, dict), "plan_identity_not_object")
    _require(identity.get("plan_id") == resolved_plan_id, "plan_id_mismatch")
    _require(
        identity.get("source_commit") == source_commit,
        "plan_source_commit_mismatch",
    )

    _check_sorted_and_unique(plan)
    _verify_source_ledger_equations(
        plan, _parse_yaml_document(source_by_path[SUBJECT_WORKFLOW_PATH].data, label=SUBJECT_WORKFLOW_PATH),
    )
    _verify_source_recorded_equations(
        plan, _parse_yaml_document(source_by_path[SUBJECT_WORKFLOW_PATH].data, label=SUBJECT_WORKFLOW_PATH), source_by_path,
    )
    _verify_source_package_equations(
        plan, _parse_yaml_document(source_by_path[SUBJECT_WORKFLOW_PATH].data, label=SUBJECT_WORKFLOW_PATH), source_by_path,
    )
    _verify_source_required_argument_equations(
        plan, _parse_yaml_document(source_by_path[SUBJECT_WORKFLOW_PATH].data, label=SUBJECT_WORKFLOW_PATH), source_by_path,
    )
    _verify_source_bundle_equations(
        plan, _parse_yaml_document(source_by_path[SUBJECT_WORKFLOW_PATH].data, label=SUBJECT_WORKFLOW_PATH), source_by_path,
    )
    _verify_tool_identity(
        plan=plan,
        source_by_path=source_by_path,
        source_commit=source_commit,
    )

    expected = _reconstruct_expected_plan(
        repository_root=root,
        source_commit=source_commit,
        record_status=expected_record_status,
        plan_id=resolved_plan_id,
    )
    expected_bytes = _canonical_json_bytes(expected)
    expected_sha256 = hashlib.sha256(expected_bytes).hexdigest()
    _require(
        captured.data == expected_bytes,
        "plan_reconstruction_mismatch",
        f"supplied={captured.sha256} reconstructed={expected_sha256}",
    )

    counts = _plan_counts(plan)
    _require(
        counts["job_templates"] == 8
        and counts["step_templates"] == 147
        and counts["instantiated_steps"] == 145
        and counts["successful_steps"] == 101
        and counts["permitted_skipped_steps"] == 44
        and counts["uninstantiated_steps"] == 2
        and counts["model_inference_templates"] == 6,
        "plan_terminal_counts_mismatch",
    )

    return {
        "schema_version": CHECK_DIAGNOSTIC_VERSION,
        "tool": CHECKER_TOOL_ID,
        "version": CHECKER_TOOL_VERSION,
        "record_status": "verified",
        "ok": True,
        "plan": {
            "sha256": captured.sha256,
            "size_bytes": captured.size_bytes,
            "plan_id": resolved_plan_id,
            "record_status": expected_record_status,
            "source_commit": source_commit,
            "reconstructed_sha256": expected_sha256,
            "byte_identical_to_independent_reconstruction": True,
        },
        "counts": counts,
        "checks": {
            "isolated_python": True,
            "regular_single_link_plan_input": True,
            "external_plan_digest_matches": True,
            "strict_canonical_json": True,
            "schema_valid": True,
            "source_commit_is_checked_out_head": True,
            "source_inventory_matches_git_objects": True,
            "reviewed_source_profile_matches": True,
            "builder_identity_matches_exact_source": True,
            "checker_identity_matches_exact_source": True,
            "executed_checker_matches_exact_git_source": True,
            "occurrence_identifiers_unique": True,
            "deterministic_ordering": True,
            "terminal_counts_match": True,
            "independent_reconstruction_byte_identical": True,
        },
        "result_boundary": dict(RESULT_BOUNDARY),
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "errors": [],
    }


def _failure_diagnostic(error: PlanError, *, exit_code: int) -> dict[str, Any]:
    return {
        "schema_version": CHECK_DIAGNOSTIC_VERSION,
        "tool": CHECKER_TOOL_ID,
        "version": CHECKER_TOOL_VERSION,
        "record_status": "rejected",
        "ok": False,
        "error_code": error.code,
        "detail": error.detail,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "errors": [error.code],
        "exit_code": exit_code,
    }


def _parse_checker_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Independently reconstruct and validate one Step 5C whole-runtime "
            "prelaunch plan from exact Git source objects."
        )
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Exact Git repository root; checked-out HEAD must equal the expected source commit.",
    )
    parser.add_argument(
        "--plan",
        required=True,
        help="Path to the canonical prelaunch-plan JSON file.",
    )
    parser.add_argument(
        "--expected-source-commit",
        required=True,
        help="Externally supplied reviewed lowercase 40-hex source commit.",
    )
    parser.add_argument(
        "--expected-plan-sha256",
        required=True,
        help="Externally supplied SHA-256 of the exact plan bytes.",
    )
    parser.add_argument(
        "--expected-record-status",
        choices=("example", "observed"),
        required=True,
        help="Expected plan record status supplied outside the plan.",
    )
    parser.add_argument(
        "--expected-plan-id",
        help="Expected step5c-plan:* identifier; defaults to step5c-plan:<source commit>.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_checker_args(argv)
    try:
        diagnostic = check_plan(
            repository_root=Path(args.repository_root),
            plan_path=Path(args.plan),
            expected_source_commit=str(args.expected_source_commit),
            expected_plan_sha256=str(args.expected_plan_sha256),
            expected_record_status=str(args.expected_record_status),
            expected_plan_id=(
                str(args.expected_plan_id)
                if args.expected_plan_id is not None
                else None
            ),
        )
        sys.stdout.buffer.write(_canonical_json_bytes(diagnostic))
        return 0
    except PlanError as exc:
        sys.stdout.buffer.write(
            _canonical_json_bytes(_failure_diagnostic(exc, exit_code=1))
        )
        return 1
    except Exception as exc:  # fail closed without exposing ambient values
        wrapped = PlanError("unexpected_plan_checker_failure", type(exc).__name__)
        sys.stdout.buffer.write(
            _canonical_json_bytes(_failure_diagnostic(wrapped, exit_code=2))
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
