#!/usr/bin/env python3
"""Build the deterministic Step 5C whole-runtime prelaunch plan.

This tool reads only exact Git objects from one reviewed repository commit.  It
constructs the prelaunch subject graph before any workflow is dispatched.  It
does not call GitHub, execute the subject, create runtime observations, mutate
status, materialize gates, or create release authority.

Run the CLI with isolated Python on Linux::

    python -I tools/build_pulsemech_compute_whole_runtime_observation_plan_v0.py \
      --repository-root . \
      --source-commit <40-hex commit> \
      --record-status observed

The canonical JSON plan is written to stdout.  Redirect it to a new file in the
workflow preparation stage; this tool never opens an output pathname itself.
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
        '"ok":false,"tool":"build_pulsemech_compute_whole_runtime_observation_plan_v0"}\n'
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
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml


TOOL_ID = "build_pulsemech_compute_whole_runtime_observation_plan_v0"
TOOL_VERSION = "0.1.0"
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
EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1 = "ad1f165ad695c65827c590cbef9466e300d6b6e9"
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
    ("artifact_provenance_builder_semantics", "PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py"),
    ("artifact_provenance_verifier_semantics", "PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py"),
    ("self_contained_floor_semantics", "PULSE_safe_pack_v0/tools/build_self_contained_pulse_evidence_floor_v0.py"),
    ("llamaguard_envelope_builder_semantics", "PULSE_safe_pack_v0/tools/build_llamaguard_attestation_envelope_v1.py"),
    ("llamaguard_attestation_verifier_semantics", "PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py"),
    ("llamaguard_summary_ingest_semantics", "PULSE_safe_pack_v0/tools/adapters/llamaguard_ingest.py"),
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
    exact_pins.update(_PROVENANCE_SOURCE_PINS)
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


# A bounded source projection for the ledger/report subgraph. This is a source
# declaration, not an observed read receipt. The remaining state families and
# the R2 evidence-record switch are deliberately not reinterpreted here.
_MAPPING_JOB = "release_grade_recorded_path"
_MAPPING_TOOLS = {
    "render": "render_quality_ledger.py",
    "summary": "status_to_summary.py",
    "decision": "materialize_release_decision.py",
    "section": "render_release_decision_ledger_section.py",
    "authority": "build_release_authority_manifest_v0.py",
    "insert": "insert_release_authority_manifest_ledger_section.py",
    "compose": "insert_release_decision_ledger_section.py",
    "parity": "check_quality_ledger_status_parity.py",
}


def _mapping_path(value: str, *, symbolic_temp: bool = False) -> str:
    """Resolve only the reviewed workspace/pack roots; never evaluate shell."""
    _require(isinstance(value, str) and bool(value), "source_mapping_path_invalid")
    replacements = (
        ("${{ env.PACK_DIR }}/", "PULSE_safe_pack_v0/"),
        ("${PACK_DIR}/", "PULSE_safe_pack_v0/"),
        ("${GITHUB_WORKSPACE}/", ""),
        ("$GITHUB_WORKSPACE/", ""),
    )
    for old, new in replacements:
        if value.startswith(old):
            value = new + value[len(old):]
            break
    tested = value
    if symbolic_temp and value.startswith("${RUNNER_TEMP}/"):
        tested = value[len("${RUNNER_TEMP}/"):]
    _require(re.fullmatch(r"[A-Za-z0-9_./-]+", tested) is not None,
             "source_mapping_dynamic_path", value)
    _require(not tested.startswith("/") and all(part not in {"", ".", ".."}
             for part in tested.split("/")), "source_mapping_path_invalid", value)
    return value


def _mapping_options(raw: dict[str, Any], tool: str) -> dict[str, str]:
    """Read one exact Python tool invocation from backslash-continued lines."""
    body = raw.get("run")
    _require(isinstance(body, str), "source_mapping_run_missing", tool)
    matches: list[list[str]] = []
    for line in body.replace("\\\n", " ").splitlines():
        if not re.match(r"^\s*python(?:3)?\s+", line):
            continue
        try:
            words = shlex.split(line, comments=False, posix=True)
        except ValueError as exc:
            raise PlanError("source_mapping_command_invalid", tool) from exc
        if len(words) > 1 and words[1].endswith("/" + tool):
            _require(_mapping_path(words[1]) == "PULSE_safe_pack_v0/tools/" + tool,
                     "source_mapping_tool_path_mismatch", tool)
            matches.append(words)
    _require(len(matches) == 1, "source_mapping_command_not_unique", tool)
    words = matches[0][2:]
    _require(len(words) % 2 == 0, "source_mapping_argument_shape", tool)
    options: dict[str, str] = {}
    for index in range(0, len(words), 2):
        key, value = words[index:index + 2]
        _require(re.fullmatch(r"--[a-z][a-z0-9_-]*", key) is not None
                 and key not in options and not value.startswith("--"),
                 "source_mapping_argument_shape", tool)
        options[key] = value
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
    _require(set(options) == allowed_options.get(tool), "source_mapping_argument_profile_mismatch", tool)
    return options


def _mapping_assignment(raw: dict[str, Any], name: str, *, symbolic_temp: bool = False) -> str:
    body = raw.get("run")
    _require(isinstance(body, str), "source_mapping_run_missing", name)
    matches = re.findall(r"^\s*(?:export\s+)?" + re.escape(name) + r"=(.+)$", body, re.M)
    _require(len(matches) == 1, "source_mapping_assignment_not_unique", name)
    try:
        words = shlex.split(matches[0], comments=False, posix=True)
    except ValueError as exc:
        raise PlanError("source_mapping_assignment_invalid", name) from exc
    _require(len(words) == 1, "source_mapping_assignment_invalid", name)
    return _mapping_path(words[0], symbolic_temp=symbolic_temp)


def _ledger_source_projection(workflow: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct supported source equations, independent of state tables."""
    raw_jobs = workflow.get("jobs")
    _require(isinstance(raw_jobs, dict), "source_mapping_jobs_missing")
    raw_job = raw_jobs.get(_MAPPING_JOB)
    _require(isinstance(raw_job, dict), "source_mapping_job_missing")
    steps = raw_job.get("steps")
    _require(isinstance(steps, list) and all(isinstance(s, dict) for s in steps),
             "source_mapping_steps_invalid")
    found: dict[str, tuple[str, dict[str, str]]] = {}
    for key, tool in _MAPPING_TOOLS.items():
        candidates = [(i, s) for i, s in enumerate(steps, 1)
                      if isinstance(s.get("run"), str)
                      and re.search(r"(?:/|\b)" + re.escape(tool) + r"(?:[\"'\s]|$)", s["run"])]
        _require(len(candidates) == 1, "source_mapping_step_not_unique", key)
        ordinal, raw = candidates[0]
        found[key] = (_step_id(_MAPPING_JOB, ordinal), _mapping_options(raw, tool))
    # A workflow profile is source-pinned elsewhere. This projection also guards
    # order locally so it cannot alias the before/after versions on its own.
    ordinals = [int(found[key][0].rsplit(":", 1)[1]) for key in _MAPPING_TOOLS]
    _require(ordinals == list(range(ordinals[0], ordinals[0] + len(ordinals))),
             "source_mapping_ledger_order")

    def arg(key: str, option: str) -> str:
        options = found[key][1]
        _require(option in options, "source_mapping_argument_missing", key + ":" + option)
        return _mapping_path(options[option])

    status = arg("render", "--status")
    ledger = arg("render", "--out")
    section = arg("section", "--out")
    decision = arg("decision", "--out")
    manifest = arg("authority", "--out")
    composed = arg("compose", "--out")
    _require(all(arg(key, "--status") == status for key in
                 ("summary", "decision", "authority", "parity")),
             "source_mapping_status_version_mismatch")
    _require(arg("section", "--input") == decision,
             "source_mapping_decision_input_mismatch")
    _require(arg("insert", "--report") == ledger
             and arg("insert", "--manifest") == manifest
             and "--out" not in found["insert"][1], "source_mapping_inplace_boundary_mismatch")
    _require(arg("compose", "--report") == ledger and arg("compose", "--section") == section
             and arg("parity", "--ledger") == ledger,
             "source_mapping_consumer_input_mismatch")
    _require(arg("decision", "--policy") == POLICY_PATH
             and arg("authority", "--policy") == POLICY_PATH
             and arg("authority", "--registry") == REGISTRY_PATH,
             "source_mapping_authority_input_mismatch")
    _require(len({status, ledger, section, decision, manifest, composed,
                  arg("summary", "--out_json")}) == 7, "source_mapping_output_alias")

    locators = {
        "quality-ledger-pre-authority": ledger + "#pre-authority-insertion",
        "final-status-summary": arg("summary", "--out_json"),
        "release-decision": decision,
        "release-decision-ledger-section": section,
        "release-authority-manifest": manifest,
        "quality-ledger-final": ledger,
        "release-decision-report": composed,
    }
    io_roles = {
        "render": (("final-status",), ("quality-ledger-pre-authority",)),
        "summary": (("final-status",), ("final-status-summary",)),
        "decision": (("final-status", "gate-policy"), ("release-decision",)),
        "section": (("release-decision",), ("release-decision-ledger-section",)),
        "authority": (("final-status", "gate-policy", "gate-registry"), ("release-authority-manifest",)),
        "insert": (("quality-ledger-pre-authority", "release-authority-manifest"), ("quality-ledger-final",)),
        "compose": (("quality-ledger-final", "release-decision-ledger-section"), ("release-decision-report",)),
        "parity": (("final-status", "quality-ledger-final"), ()),
    }
    def named(name: str) -> dict[str, Any]:
        rows = [s for s in steps if s.get("name") == name]
        _require(len(rows) == 1, "source_mapping_step_not_unique", name)
        return rows[0]
    exporter = named("Export final release-grade JUnit and SARIF")
    locators["release-grade-junit"] = _mapping_assignment(exporter, "PULSE_JUNIT")
    locators["release-grade-sarif"] = _mapping_assignment(exporter, "PULSE_SARIF")
    advisory = named("Assemble advisory release-grade reference bundle")
    locators["advisory-reference-bundle"] = _mapping_assignment(advisory, "BUNDLE_DIR", symbolic_temp=True) + "/"
    pulse_steps = raw_jobs.get("pulse", {}).get("steps", [])
    uploads = [s for s in pulse_steps if s.get("name") == "Upload release-grade pre-attestation pulse artifacts"]
    _require(len(uploads) == 1 and str(uploads[0].get("uses", "")).startswith("actions/upload-artifact@"),
             "source_mapping_upload_missing")
    template = uploads[0].get("with", {}).get("name")
    _require(isinstance(template, str) and template.count("${{ github.run_id }}") == 1
             and template.count("${{ github.run_attempt }}") == 1,
             "source_mapping_upload_template_invalid")
    template = template.replace("${{ github.run_id }}", "{workflow_run_id}").replace("${{ github.run_attempt }}", "1")
    _require(re.fullmatch(r"[a-z0-9-]+\{workflow_run_id\}-1", template) is not None,
             "source_mapping_upload_template_invalid")
    locators["pre-attestation-pulse-artifacts"] = "artifact://" + template
    return {"locators": locators, "status": status,
            "equations": {found[k][0]: {"inputs": list(v[0]), "outputs": list(v[1])}
                          for k, v in io_roles.items()}}


def _install_ledger_source_projection(
    states: list[dict[str, Any]], step_by_key: dict[tuple[str, int], dict[str, Any]],
    projection: dict[str, Any],
) -> None:
    """Install the closed subgraph in both directions; preserve outside duties."""
    sid = lambda key: "state:step5c:" + key
    index = {row["state_id"]: row for row in states}
    equations = projection["equations"]
    for row in states:
        row["required_consumer_occurrence_ids"] = [
            c for c in row["required_consumer_occurrence_ids"] if c not in equations]
    for key, path in projection["locators"].items():
        index[sid(key)]["path_or_uri"] = path
    _require(index[sid("final-status")]["path_or_uri"] == projection["status"],
             "source_mapping_status_locator_mismatch")
    steps = {s["occurrence_id"]: s for s in step_by_key.values()}
    for occurrence, equation in equations.items():
        _require(occurrence in steps, "source_mapping_occurrence_missing", occurrence)
        steps[occurrence]["input_state_ids"] = sorted(sid(k) for k in equation["inputs"])
        steps[occurrence]["output_state_ids"] = sorted(sid(k) for k in equation["outputs"])
        for key in equation["inputs"]:
            index[sid(key)]["required_consumer_occurrence_ids"].append(occurrence)
        for key in equation["outputs"]:
            index[sid(key)]["producer_occurrence_id"] = occurrence
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))


# The recorded-evidence subgraph is a projection of the pinned source, not a
# record of actual runtime reads. R2 carrier activation remains a separate step.
_RECORDED_JOB = "release_grade_recorded_path"
_RECORDED_PACK_TOOLS = "PULSE_safe_pack_v0/tools/"
_RECORDED_ROLES = frozenset({
    "pre-materialization-status", "recorded-release-candidate-envelopes",
    "recorded-candidate-index", "release-evidence-input-manifest",
    "recorded-release-evidence-verifier", "materialized-release-required-gate-set",
    "final-status", "gate-policy", "gate-registry",
})


def _recorded_argv(raw: dict[str, Any], tool_path: str,
                   expected_options: set[str], *, count: int = 1) -> list[dict[str, str]]:
    """Parse only literal Python invocations in the selected source profile."""
    body = raw.get("run")
    _require(isinstance(body, str), "recorded_mapping_run_missing", tool_path)
    matches = []
    for line in body.replace("\\\n", " ").splitlines():
        if not re.match(r"^\s*python(?:3)?\s+", line):
            continue
        try:
            argv = shlex.split(line, comments=False, posix=True)
        except ValueError as exc:
            raise PlanError("recorded_mapping_command_invalid", tool_path) from exc
        if len(argv) < 2 or argv[1].rsplit("/", 1)[-1] != tool_path.rsplit("/", 1)[-1]:
            continue
        _require(_mapping_path(argv[1]) == tool_path, "recorded_mapping_tool_path", tool_path)
        args = argv[2:]
        _require(len(args) % 2 == 0, "recorded_mapping_argument_shape", tool_path)
        options: dict[str, str] = {}
        for i in range(0, len(args), 2):
            key, value = args[i:i + 2]
            _require(key in expected_options and key not in options and not value.startswith("--"),
                     "recorded_mapping_argument_shape", tool_path)
            options[key] = value
        _require(set(options) == expected_options, "recorded_mapping_argument_profile", tool_path)
        matches.append(options)
    _require(len(matches) == count, "recorded_mapping_command_count", tool_path)
    return matches


def _recorded_default(source: bytes, flag: str, constant: str, path: str) -> str:
    """Resolve a declared argparse default from a top-level literal constant."""
    try:
        tree = ast.parse(source.decode("utf-8", errors="strict"), filename=path)
    except (UnicodeError, SyntaxError) as exc:
        raise PlanError("recorded_mapping_python_source", path) from exc
    mains = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    _require(len(mains) == 1, "recorded_mapping_main_not_unique", path)
    calls = [node for node in ast.walk(mains[0]) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"
             and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == flag]
    _require(len(calls) == 1, "recorded_mapping_default_not_unique", flag)
    defaults = [kw.value for kw in calls[0].keywords if kw.arg == "default"]
    _require(len(defaults) == 1 and isinstance(defaults[0], ast.Name)
             and defaults[0].id == constant, "recorded_mapping_default_binding", flag)
    return _mapping_path(_python_constant(source, name=constant, label=path))


def _recorded_source_projection(workflow: dict[str, Any],
                                source_by_path: dict[str, GitObject]) -> dict[str, Any]:
    """Resolve the selected candidate/status family; do not execute its tools."""
    jobs = workflow.get("jobs", {})
    raw_steps = jobs.get(_RECORDED_JOB, {}).get("steps")
    _require(isinstance(raw_steps, list) and len(raw_steps) >= 12,
             "recorded_mapping_steps_missing")
    for ordinal in range(6, 13):
        _require(raw_steps[ordinal - 1].get("name") == RECORDED_PATH_STEP_NAMES[ordinal - 1],
                 "recorded_mapping_step_order", str(ordinal))
    pack = _RECORDED_PACK_TOOLS
    def call(ordinal: int, name: str, options: set[str]) -> dict[str, str]:
        return _recorded_argv(raw_steps[ordinal - 1], pack + name, options)[0]
    def payload(path: str) -> bytes:
        obj = source_by_path.get(path)
        _require(obj is not None, "recorded_mapping_source_missing", path)
        _require(_sha1_git_blob(obj.data) == _RECORDED_SEMANTIC_PINS[path],
                 "recorded_mapping_semantic_source_drift", path)
        return obj.data
    # Pin the semantics of every interpreted helper, not only its printed name.
    for path in _RECORDED_SEMANTIC_PINS:
        payload(path)
    candidate_path = pack + "build_recorded_release_candidates_v0.py"
    manifest_path = pack + "build_release_evidence_input_manifest_v0.py"
    candidate = call(6, "build_recorded_release_candidates_v0.py", {"--repo-root"})
    manifest = call(7, "build_release_evidence_input_manifest_v0.py", {"--repo-root"})
    verifier = call(8, "check_recorded_release_evidence_v0.py", {"--manifest", "--repo-root", "--out-json"})
    materializer = call(9, "materialize_release_required_from_verifier_v0.py",
                        {"--status", "--verifier-report", "--manifest", "--repo-root", "--policy", "--registry", "--out"})
    _require(all(row["--repo-root"] == "${GITHUB_WORKSPACE}" for row in
                 (candidate, manifest, verifier, materializer)), "recorded_mapping_repo_root")
    status = _recorded_default(payload(candidate_path), "--status", "STATUS", candidate_path)
    index = _recorded_default(payload(candidate_path), "--index", "INDEX", candidate_path)
    envelopes = _recorded_default(payload(candidate_path), "--out-dir", "OUT_DIR", candidate_path)
    manifest_out = _recorded_default(payload(manifest_path), "--out", "OUT_PATH", manifest_path)
    manifest_index = _recorded_default(payload(manifest_path), "--index", "INDEX_PATH", manifest_path)
    manifest_envelopes = _mapping_path(_python_constant(payload(manifest_path), name="CANDIDATE_DIR", label=manifest_path))
    manifest_status = _mapping_path(_python_constant(payload(manifest_path), name="STATUS_PATH", label=manifest_path))
    _require(index == manifest_index and envelopes == manifest_envelopes and status == manifest_status,
             "recorded_mapping_candidate_handoff")
    for path, names in ((candidate_path, ("POLICY", "REGISTRY")),
                        (manifest_path, ("POLICY_PATH", "REGISTRY_PATH"))):
        _require(_recorded_default(payload(path), "--policy", names[0], path) == POLICY_PATH
                 and _recorded_default(payload(path), "--registry", names[1], path) == REGISTRY_PATH,
                 "recorded_mapping_policy_defaults")
    report = _mapping_path(verifier["--out-json"])
    _require(_mapping_path(verifier["--manifest"]) == manifest_out
             and _mapping_path(materializer["--manifest"]) == manifest_out
             and _mapping_path(materializer["--verifier-report"]) == report,
             "recorded_mapping_verifier_handoff")
    _require(_mapping_path(materializer["--status"]) == status
             and _mapping_path(materializer["--out"]) == status,
             "recorded_mapping_status_version")
    _require(_mapping_path(materializer["--policy"]) == POLICY_PATH
             and _mapping_path(materializer["--registry"]) == REGISTRY_PATH,
             "recorded_mapping_materializer_context")
    _require(len({status, index, envelopes, manifest_out, report}) == 5,
             "recorded_mapping_output_alias")
    pulse_steps = jobs.get("pulse", {}).get("steps", [])
    _require(len(pulse_steps) >= 37, "recorded_mapping_origin_missing")
    origin = _recorded_argv(pulse_steps[12], pack + "build_release_grade_candidate_status_v0.py",
                            {"--repo-root", "--out"})[0]
    _require(origin["--repo-root"] == "${GITHUB_WORKSPACE}" and _mapping_path(origin["--out"]) == status,
             "recorded_mapping_status_origin")
    restored = _mapping_assignment(raw_steps[3], "CANONICAL_ARTIFACTS")
    restore_calls = re.findall(r'^\s*copy_required_artifact\s+"([^"\n]+)"\s*$', raw_steps[3].get("run", ""), re.M)
    _require(restore_calls.count("status.json") == 1 and restored + "/status.json" == status,
             "recorded_mapping_status_restore")
    contract = _recorded_argv(raw_steps[9], "tools/validate_status_schema.py", {"--schema", "--status", "--max-errors"})[0]
    no_stub = _recorded_argv(raw_steps[10], "ci/check_release_no_stub_status.py", {"--status"})[0]
    _require(_mapping_path(contract["--status"]) == status and _mapping_path(no_stub["--status"]) == status
             and contract["--max-errors"] == "20"
             and _mapping_path(contract["--schema"]) == "schemas/status/release_grade_status_v1.schema.json",
             "recorded_mapping_post_status_guard")
    enforce = raw_steps[11]
    _require(_mapping_assignment(enforce, "STATUS") == status, "recorded_mapping_enforcement_status")
    policy_calls = _recorded_argv(enforce, "tools/policy_to_require_args.py", {"--policy", "--set", "--format"}, count=2)
    _require([row["--set"] for row in policy_calls] == ["required", "release_required"]
             and all(_mapping_path(row["--policy"]) == POLICY_PATH and row["--format"] == "newline" for row in policy_calls),
             "recorded_mapping_enforcement_policy")
    gate_call = _recorded_argv(enforce, pack + "check_gates.py", {"--status", "--require"})[0]
    _require(gate_call == {"--status": "${STATUS}", "--require": "${EFFECTIVE_GATES[@]}"},
             "recorded_mapping_enforcement_arguments")
    # Exact workflow pinning also fixes the shell's ordered deduplication and
    # non-empty guards. This is not an original runtime argv receipt.
    locators = {
        "pre-materialization-status": status + "#pre-release-required-materialization",
        "recorded-release-candidate-envelopes": envelopes + "/",
        "recorded-candidate-index": index,
        "release-evidence-input-manifest": manifest_out,
        "recorded-release-evidence-verifier": report,
        "materialized-release-required-gate-set": "projection://" + status + "#policy-selected-release_required-gate-values",
        "final-status": status,
    }
    # These are source-declared dependencies for this selected state family.
    # Transitive evidence replay is not presented as an observed read receipt.
    io = {
        6: (("pre-materialization-status", "gate-policy", "gate-registry"),
            ("recorded-candidate-index", "recorded-release-candidate-envelopes")),
        7: (("recorded-candidate-index", "recorded-release-candidate-envelopes", "pre-materialization-status", "gate-policy", "gate-registry"),
            ("release-evidence-input-manifest",)),
        8: (("release-evidence-input-manifest", "recorded-release-candidate-envelopes", "pre-materialization-status", "gate-policy", "gate-registry"),
            ("recorded-release-evidence-verifier",)),
        9: (("pre-materialization-status", "release-evidence-input-manifest", "recorded-release-evidence-verifier",
             "recorded-release-candidate-envelopes", "gate-policy", "gate-registry"),
            ("final-status", "materialized-release-required-gate-set")),
        10: (("final-status",), ()), 11: (("final-status",), ()),
        12: (("final-status", "gate-policy"), ()),
    }
    return {"locators": locators, "steps": {_step_id(_RECORDED_JOB, n): {"inputs": a, "outputs": z}
                                             for n, (a, z) in io.items()},
            "pre_status_origin": _step_id("pulse", 13), "pre_status_restore": _step_id(_RECORDED_JOB, 4)}


def _install_recorded_source_projection(states: list[dict[str, Any]],
                                        step_by_key: dict[tuple[str, int], dict[str, Any]],
                                        facts: dict[str, Any]) -> None:
    sid = lambda role: "state:step5c:" + role
    index = {row["state_id"]: row for row in states}
    selected = {sid(role) for role in _RECORDED_ROLES}
    owned = set(facts["steps"])
    for role, locator in facts["locators"].items():
        index[sid(role)]["path_or_uri"] = locator
    for row in states:
        if row["state_id"] in selected:
            row["required_consumer_occurrence_ids"] = [x for x in row["required_consumer_occurrence_ids"] if x not in owned]
    for step in step_by_key.values():
        occurrence = step["occurrence_id"]
        if occurrence not in owned:
            continue
        equation = facts["steps"][occurrence]
        for field, key in (("input_state_ids", "inputs"), ("output_state_ids", "outputs")):
            step[field] = sorted(set(step[field]) - selected | {sid(role) for role in equation[key]})
        for role in equation["inputs"]:
            index[sid(role)]["required_consumer_occurrence_ids"].append(occurrence)
        for role in equation["outputs"]:
            index[sid(role)]["producer_occurrence_id"] = occurrence
    pre = sid("pre-materialization-status")
    _append_unique(step_by_key[("pulse", 13)]["output_state_ids"], pre)
    _append_unique(step_by_key[(_RECORDED_JOB, 4)]["input_state_ids"], pre)
    index[pre]["producer_occurrence_id"] = facts["pre_status_origin"]
    _append_unique(index[pre]["required_consumer_occurrence_ids"], facts["pre_status_restore"])
    # The logical gate-value projection is not a separate file consumed by any
    # later command. Those commands consume final-status instead.
    logical = sid("materialized-release-required-gate-set")
    index[logical]["required_consumer_occurrence_ids"] = []
    for step in step_by_key.values():
        step["input_state_ids"] = [x for x in step["input_state_ids"] if x != logical]
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))


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
        return _mapping_path(value, symbolic_temp=True)
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


def _package_source_projection(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    """Derive the five-role package subgraph from commands and pinned tools."""
    payloads = {}
    for path, expected in _PACKAGE_SEMANTIC_PINS.items():
        obj = sources.get(path)
        _require(obj is not None, "package_mapping_source_missing", path)
        _require(_sha1_git_blob(obj.data) == expected, "package_mapping_semantic_source_drift", path)
        payloads[path] = obj.data
    jobs = workflow.get("jobs", {})
    blocks = {}
    for job, names in ((_PACKAGE_ASSEMBLE_JOB, ASSEMBLE_PACKAGE_STEP_NAMES),
                       (_PACKAGE_VERIFY_JOB, VERIFY_PACKAGE_STEP_NAMES)):
        steps = jobs.get(job, {}).get("steps")
        _require(isinstance(steps, list) and len(steps) == len(names)
                 and all(isinstance(s, dict) for s in steps)
                 and [s.get("name") for s in steps] == list(names),
                 "package_mapping_step_profile", job)
        blocks[job] = steps
    assembly, verification = blocks[_PACKAGE_ASSEMBLE_JOB], blocks[_PACKAGE_VERIFY_JOB]
    roots = {}
    for name in ("INPUT_ROOT", "PULSE_REPORT_DIR", "RECORDED_PATH_DIR", "AUDIT_BUNDLE_DIR",
                 "ARTIFACT_BINDING_DIR", "COMPLETE_PACKAGE_DIR"):
        roots[name] = _package_assignment(assembly[3], name, roots)
    vroot = {name: _package_assignment(verification[3], name, {}) for name in ("PACKAGE_DIR", "VERIFY_OUT")}
    common = {"--repo-root", "--repository", "--git-sha", "--workflow-ref", "--run-id", "--run-attempt", "--run-key"}
    paths = list(_PACKAGE_SEMANTIC_PINS)
    definitions = (
        (assembly[4], paths[0], common | {"--out-dir", "--pulse-report-dir", "--recorded-path-dir", "--audit-bundle-dir", "--artifact-binding-dir", "--release-candidate", "--created-utc"}),
        (verification[4], paths[2], {"--package-dir", "--output"}),
        (verification[6], paths[1], common | {"--package-dir", "--out"}),
    )
    calls = []
    for step, path, flags in definitions:
        candidates = _package_commands(step, ("python", path), flags)
        _require(len(candidates) == 1, "package_mapping_command_not_unique", path)
        calls.append(candidates[0])
    assemble, complete, verify = calls
    identity = {"--repo-root": "${GITHUB_WORKSPACE}", "--repository": "${GITHUB_REPOSITORY}",
                "--git-sha": "${GITHUB_SHA}", "--workflow-ref": "${GITHUB_WORKFLOW_REF}",
                "--run-id": "${GITHUB_RUN_ID}", "--run-attempt": "${GITHUB_RUN_ATTEMPT}", "--run-key": "${PULSE_RUN_KEY}"}
    _require(all(c[k] == value for c in (assemble, verify) for k, value in identity.items()),
             "package_mapping_command_identity")
    _require(assemble["--release-candidate"] == "${GITHUB_REF_NAME}" and assemble["--created-utc"] == "${PACKAGE_CREATED_UTC}",
             "package_mapping_command_identity")
    for flag, variable in (("--pulse-report-dir", "PULSE_REPORT_DIR"), ("--recorded-path-dir", "RECORDED_PATH_DIR"),
                           ("--audit-bundle-dir", "AUDIT_BUNDLE_DIR"), ("--artifact-binding-dir", "ARTIFACT_BINDING_DIR")):
        _require(_package_temp_path(assemble[flag], roots) == roots[variable], "package_mapping_input_root", flag)
    out_dir = _package_temp_path(assemble["--out-dir"], roots)
    _require(out_dir == roots["COMPLETE_PACKAGE_DIR"] == vroot["PACKAGE_DIR"]
             == _package_temp_path(complete["--package-dir"], {})
             == _package_temp_path(verify["--package-dir"], vroot), "package_mapping_directory_handoff")
    local_outputs = [out_dir, _package_temp_path(complete["--output"], {}), _package_temp_path(verify["--out"], vroot)]
    _require(len(set(local_outputs)) == 3 and all(not p.startswith(out_dir + "/") for p in local_outputs[1:]),
             "package_mapping_output_alias")
    publications = []
    for step, local in zip((assembly[5], verification[5], verification[7]), local_outputs):
        options = step.get("with", {})
        _require(step.get("uses") == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
                 and options.get("if-no-files-found") == "error", "package_mapping_upload_profile")
        _require(_package_temp_path(options.get("path"), {}) == local, "package_mapping_publication_path")
        publications.append(_package_artifact_name(options.get("name")))
    _require(len(set(publications)) == 3, "package_mapping_publication_alias")
    downloads = _package_commands(verification[3], ("gh", "run", "download", "${GITHUB_RUN_ID}"), {"--repo", "--name", "--dir"})
    _require(len(downloads) == 1 and downloads[0]["--repo"] == "${GITHUB_REPOSITORY}"
             and _package_artifact_name(downloads[0]["--name"]) == publications[0]
             and _package_temp_path(downloads[0]["--dir"], vroot) == out_dir,
             "package_mapping_download_handoff")
    acquisition = _package_commands(assembly[3], ("gh", "run", "download", "${GITHUB_RUN_ID}"), {"--repo", "--name", "--dir"})
    expected_downloads = {"pulse-report": roots["PULSE_REPORT_DIR"],
        "release-grade-recorded-path-${{ github.run_id }}-${{ github.run_attempt }}": roots["RECORDED_PATH_DIR"],
        "release-authority-audit-bundle": roots["AUDIT_BUNDLE_DIR"],
        "release-authority-artifact-binding-v0": roots["ARTIFACT_BINDING_DIR"]}
    _require(len(acquisition) == 4 and {c["--name"] for c in acquisition} == set(expected_downloads)
             and all(c["--repo"] == "${GITHUB_REPOSITORY}" and _package_temp_path(c["--dir"], roots) == expected_downloads[c["--name"]]
                     for c in acquisition), "package_mapping_assembly_downloads")
    # Resolve the actual writer arguments, not names copied from legacy tables.
    module = ast.parse(payloads[paths[0]])
    main = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    members = {}
    for role, variable, writer in (("package-digest-inventory", "digest_inventory", "_write_digest_inventory"),
                                   ("package-run-metadata", "run_metadata", "_write_run_metadata")):
        assignments = [n.value for n in ast.walk(main) if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == variable for t in n.targets)]
        _require(len(assignments) == 1, "package_mapping_metadata_assignment", role)
        expr = assignments[0]
        _require(isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div)
                 and isinstance(expr.left, ast.Name) and expr.left.id == "staging_dir"
                 and isinstance(expr.right, ast.Constant) and isinstance(expr.right.value, str),
                 "package_mapping_metadata_path", role)
        member = expr.right.value
        _require(re.fullmatch(r"[A-Za-z0-9_.-]+\.json", member) is not None, "package_mapping_metadata_path", role)
        writers = [n for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == writer]
        _require(len(writers) == 1 and writers[0].args and isinstance(writers[0].args[0], ast.Name)
                 and writers[0].args[0].id == variable, "package_mapping_metadata_writer", role)
        for reader_path in paths[1:]:
            tree = ast.parse(payloads[reader_path])
            for constant in ("REQUIRED_FILES", "JSON_OBJECT_FILES" if reader_path.startswith("tools/") else "JSON_FILES"):
                values = [n.value for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))
                          and any(isinstance(t, ast.Name) and t.id == constant for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))]
                _require(len(values) == 1 and member in ast.literal_eval(values[0]), "package_mapping_metadata_reader", role)
        members[role] = member
    _require(len(set(members.values())) == 2, "package_mapping_metadata_alias")
    s = lambda n: _step_id(_PACKAGE_ASSEMBLE_JOB, n)
    v = lambda n: _step_id(_PACKAGE_VERIFY_JOB, n)
    producers = dict(zip(_PACKAGE_ROLES, (s(6), v(6), v(8), s(5), s(5))))
    consumers = dict(zip(_PACKAGE_ROLES, ((v(4),), (), (), (s(6), v(5), v(7)), (s(6), v(5), v(7)))))
    locators = dict(zip(_PACKAGE_ROLES[:3], ("artifact://" + name for name in publications)))
    locators.update({role: out_dir + "/" + member for role, member in members.items()})
    return {"locators": locators, "producers": producers, "consumers": consumers,
            "local_outputs": dict(zip(_PACKAGE_ROLES[:3], local_outputs)), "metadata_members": members,
            "assembly_download_names": sorted(expected_downloads)}


def _install_package_source_projection(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
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


# R12's ordered --require list is a source derivation, not a captured runtime
# argv. The containing shell step creates and consumes its arrays internally;
# no separate subject occurrence or cross-step state edge is invented here.
_REQUIRED_ARGUMENT_ROLE = "effective-required-argument-list"
_REQUIRED_ARGUMENT_RUN_SHA256 = "dababaec377d50eb83daa95fab958009089db11a207214bdbab1ea0156a0f81a"
_REQUIRED_ARGUMENT_SOURCE_PINS = {
    ".github/workflows/pulse_ci.yml": "ad1f165ad695c65827c590cbef9466e300d6b6e9",
    "pulse_gate_policy_v0.yml": "a311b424ad0f6c028b9c37b18572e7a09c721cdd",
    "tools/policy_to_require_args.py": "5b1d099485d0e3bfd90da3fff1213a4e949db850",
    "PULSE_safe_pack_v0/tools/check_gates.py": "2a593bdef31c9c8cb565b1c4ca3d16a1e3093735",
}


def _required_argument_policy_sets(data: bytes) -> dict[str, list[str]]:
    """Read the reviewed bare-identifier block-list policy dialect only."""
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise PlanError("required_argument_policy_encoding") from exc
    # Quoting, aliases, tags and flow collections are outside this source
    # profile, even where a general YAML reader could interpret them.
    clean_lines = [line.split("#", 1)[0].rstrip() for line in text.splitlines()]
    selected = ("required", "release_required")
    for name in selected:
        headers = [i for i, line in enumerate(clean_lines) if line == "  " + name + ":"]
        _require(len(headers) == 1, "required_argument_policy_set_shape", name)
        members = []
        for line in clean_lines[headers[0] + 1:]:
            if not line.strip():
                continue
            if not line.startswith("    "):
                break
            _require(re.fullmatch(r"    - [a-z][a-z0-9_]*", line) is not None,
                     "required_argument_policy_member_shape", name)
            members.append(line[6:])
        _require(bool(members), "required_argument_policy_set_empty", name)
    document = _parse_yaml_document(data, label=POLICY_PATH)
    gate_sets = document.get("gates")
    _require(isinstance(gate_sets, dict), "required_argument_policy_gates_missing")
    result: dict[str, list[str]] = {}
    for name in selected:
        values = gate_sets.get(name)
        _require(isinstance(values, list) and bool(values)
                 and all(isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]*", value)
                         for value in values), "required_argument_policy_members_invalid", name)
        result[name] = list(values)
    return result


def _required_arguments_source_projection(
    workflow: dict[str, Any], source_by_path: dict[str, GitObject],
) -> dict[str, Any]:
    """Derive the exact policy/source object without executing subject code."""
    bindings = []
    for path, pin in sorted(_REQUIRED_ARGUMENT_SOURCE_PINS.items()):
        source = source_by_path.get(path)
        _require(source is not None, "required_argument_source_missing", path)
        _require(_sha1_git_blob(source.data) == pin,
                 "required_argument_semantic_source_drift", path)
        bindings.append({"path": path, "sha256": hashlib.sha256(source.data).hexdigest()})
    rows = workflow.get("jobs", {}).get("release_grade_recorded_path", {}).get("steps")
    _require(isinstance(rows, list) and len(rows) >= 12,
             "required_argument_source_step_missing")
    step = rows[11]
    _require(isinstance(step, dict) and step.get("name") == RECORDED_PATH_STEP_NAMES[11],
             "required_argument_source_step_mismatch")
    body = step.get("run")
    _require(isinstance(body, str) and hashlib.sha256(body.encode("utf-8")).hexdigest()
             == _REQUIRED_ARGUMENT_RUN_SHA256, "required_argument_shell_profile_mismatch")
    # The exact body binds mapfile, non-empty guards, first-seen deduplication,
    # quoted array expansion, command order and the final checker invocation.
    calls = _recorded_argv(step, "tools/policy_to_require_args.py",
                           {"--policy", "--set", "--format"}, count=2)
    _require([call["--set"] for call in calls] == ["required", "release_required"]
             and all(call["--policy"] == POLICY_PATH and call["--format"] == "newline"
                     for call in calls), "required_argument_selection_mismatch")
    invocation = _recorded_argv(step, "PULSE_safe_pack_v0/tools/check_gates.py",
                                {"--status", "--require"})[0]
    _require(invocation == {"--status": "${STATUS}", "--require": "${EFFECTIVE_GATES[@]}"},
             "required_argument_checker_binding_mismatch")
    sets = _required_argument_policy_sets(source_by_path[POLICY_PATH].data)
    ordered = []
    for name in ("required", "release_required"):
        for gate in sets[name]:
            if gate not in ordered:
                ordered.append(gate)
    derivation = {
        "derivation_type": "step5c_effective_required_arguments_source_v0",
        "source_occurrence_id": _step_id("release_grade_recorded_path", 12),
        "source_command_sha256": _REQUIRED_ARGUMENT_RUN_SHA256,
        "source_bindings": bindings,
        "policy_path": POLICY_PATH,
        "selected_sets": ["required", "release_required"],
        "policy_set_members": sets,
        "ordered_required_gate_ids": ordered,
        "deduplication": "first_seen_preserve_order",
        "status_selector": _mapping_assignment(step, "STATUS"),
        "checker_path": "PULSE_safe_pack_v0/tools/check_gates.py",
        "original_runtime_argv_receipt": "unavailable",
        "source_derived_only": True,
        "authority_effect": "none",
    }
    derived_sha = hashlib.sha256(_canonical_json_bytes(derivation)).hexdigest()
    return {
        "derivation": derivation,
        "derivation_sha256": derived_sha,
        "locator": "projection://" + POLICY_PATH + "#r12-source-required-arguments/sha256/" + derived_sha,
    }


# Source-only preservation graph for the audit and advisory bundle family.
# A copy or upload declaration is not an observed runtime read receipt.
_BUNDLE_ROLES = ("release-authority-audit-bundle", "advisory-reference-bundle")
_BUNDLE_SOURCE_PINS = {
    ".github/workflows/pulse_ci.yml": "ad1f165ad695c65827c590cbef9466e300d6b6e9",
    "PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py": "8f01602e973b890eb2ae0928bd62dfd65e691f79",
}


def _bundle_copy_commands(step: dict[str, Any]) -> list[tuple[bool, str, str]]:
    """Read the finite cp dialect used in the pinned preservation steps."""
    body = step.get("run")
    _require(isinstance(body, str), "bundle_mapping_run_missing")
    copies = []
    for line in body.replace("\\\n", " ").splitlines():
        if not re.match(r"^\s*cp\s", line):
            continue
        try:
            words = shlex.split(line, posix=True, comments=False)
        except ValueError as exc:
            raise PlanError("bundle_mapping_copy_syntax") from exc
        tree = words[1:2] == ["-a"]
        args = words[2:] if tree else words[1:]
        _require(len(args) == 2 and all(not item.startswith("-") for item in args),
                 "bundle_mapping_copy_syntax")
        _require(all(re.fullmatch(r"[A-Za-z0-9_$\{\}./*-]+", item) for item in args),
                 "bundle_mapping_copy_syntax")
        copies.append((tree, args[0], args[1]))
    _require(bool(copies) and len(copies) == len(set(copies)), "bundle_mapping_copy_set")
    return copies


def _bundle_source_projection(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    """Derive content origins, copies, publishers and the distinct S5 reader."""
    payloads = {}
    for path, pin in _BUNDLE_SOURCE_PINS.items():
        obj = sources.get(path)
        _require(obj is not None, "bundle_mapping_source_missing", path)
        _require(_sha1_git_blob(obj.data) == pin, "bundle_mapping_source_drift", path)
        payloads[path] = obj.data
    original = _parse_yaml_document(payloads[SUBJECT_WORKFLOW_PATH], label=SUBJECT_WORKFLOW_PATH)
    # Finite reviewed profile: do not reinterpret changed control flow, glob
    # semantics, copy commands, publication conditions or acquisition roots.
    for job in ("release_grade_recorded_path", "assemble_release_grade_reference_package", "pulse"):
        _require(workflow.get("jobs", {}).get(job) == original["jobs"][job],
                 "bundle_mapping_workflow_drift", job)
    rows = workflow["jobs"]["release_grade_recorded_path"]["steps"]
    ledger = _ledger_source_projection(workflow)
    paths = dict(ledger["locators"])
    paths["final-status"] = ledger["status"]
    paths["llamaguard-summary"] = _mapping_assignment(workflow["jobs"]["pulse"]["steps"][22], "SUMMARY")
    audit_root = _mapping_assignment(rows[21], "BUNDLE")
    advisory_root = _mapping_assignment(rows[24], "BUNDLE_DIR", symbolic_temp=True)
    paths[_BUNDLE_ROLES[0]] = audit_root + "/"
    paths[_BUNDLE_ROLES[1]] = advisory_root + "/"
    _require(paths[_BUNDLE_ROLES[1]] == ledger["locators"][_BUNDLE_ROLES[1]], "bundle_mapping_root_disagreement")
    selected = ("final-status", "quality-ledger-final", "release-authority-manifest",
                "llamaguard-summary", "release-grade-junit", "release-grade-sarif", *_BUNDLE_ROLES)
    reverse = {paths[role].rstrip("/"): role for role in selected}
    _require(len(reverse) == len(selected), "bundle_mapping_state_alias")
    copies: dict[str, list[dict[str, str]]] = {}
    inputs: dict[str, list[str]] = {}
    for number, variable, root, output_role in ((22, "BUNDLE", audit_root, _BUNDLE_ROLES[0]),
                                               (25, "BUNDLE_DIR", advisory_root, _BUNDLE_ROLES[1])):
        records, readers = [], []
        for tree, raw_source, raw_destination in _bundle_copy_commands(rows[number - 1]):
            _require(raw_destination.startswith("${" + variable + "}/"), "bundle_mapping_destination_root")
            suffix = raw_destination[len(variable) + 4:]
            destination = _mapping_path(root + "/" + suffix.rstrip("/"), symbolic_temp=True)
            if "*" in raw_source:
                _require(not tree and raw_source.endswith("/*_summary.json") and raw_source.count("*") == 1,
                         "bundle_mapping_glob_dialect")
                source_root = _mapping_path(raw_source[:-len("/*_summary.json")])
                matching = [role for path, role in reverse.items()
                            if path.startswith(source_root + "/") and "/" not in path[len(source_root) + 1:]
                            and path.endswith("_summary.json")]
                _require(matching == ["llamaguard-summary"], "bundle_mapping_selected_glob_roles")
                role = matching[0]
                kind = "selected_member_of_source_glob"
                selector = source_root + "/*_summary.json"
            else:
                selector = _mapping_path(raw_source)
                _require(selector in reverse, "bundle_mapping_copy_role_missing", selector)
                role = reverse[selector]
                kind = "tree_copy" if tree else "file_copy"
                _require(tree == (role == _BUNDLE_ROLES[0]), "bundle_mapping_copy_kind")
            _require(role != output_role and role not in readers, "bundle_mapping_copy_alias")
            readers.append(role)
            records.append({"role": role, "source_selector": selector,
                            "destination": destination, "copy_kind": kind})
        occurrence = _step_id("release_grade_recorded_path", number)
        inputs[occurrence] = sorted(readers)
        copies[output_role] = records
    _require(len(copies[_BUNDLE_ROLES[0]]) == 3 and len(copies[_BUNDLE_ROLES[1]]) == 7,
             "bundle_mapping_copy_extent")
    publications = {}
    for number, role in ((28, _BUNDLE_ROLES[0]), (32, _BUNDLE_ROLES[1])):
        step = rows[number - 1]; options = step.get("with", {})
        _require(step.get("uses") == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
                 and options.get("if-no-files-found") == "error", "bundle_mapping_upload_profile")
        path = options.get("path")
        if role == _BUNDLE_ROLES[1]:
            _require(path == "${{ env.REFERENCE_BUNDLE_DIR }}"
                     and 'echo "REFERENCE_BUNDLE_DIR=${BUNDLE_DIR}" >> "$GITHUB_ENV"' in rows[24]["run"],
                     "bundle_mapping_advisory_export")
            path = advisory_root
        _require(isinstance(path, str) and _mapping_path(path.rstrip("/"), symbolic_temp=True)
                 == paths[role].rstrip("/"), "bundle_mapping_upload_path")
        name = options.get("name")
        _require(isinstance(name, str) and re.fullmatch(r"[a-z0-9-]+", name), "bundle_mapping_upload_name")
        publications[role] = {"name": name, "occurrence": _step_id("release_grade_recorded_path", number)}
    # R31 also reads the audit tree through its artifacts/** selector. R26
    # checks the directory metadata only; it does not read that tree's files.
    selectors = rows[30]["with"]["path"].splitlines()
    _require(audit_root.startswith("PULSE_safe_pack_v0/artifacts/")
             and "PULSE_safe_pack_v0/artifacts/**" in selectors, "bundle_mapping_report_upload")
    assembly = workflow["jobs"]["assemble_release_grade_reference_package"]["steps"]
    downloads = _package_commands(assembly[3], ("gh", "run", "download", "${GITHUB_RUN_ID}"), {"--repo", "--name", "--dir"})
    audit_downloads = [d for d in downloads if d["--name"] == publications[_BUNDLE_ROLES[0]]["name"]]
    _require(len(audit_downloads) == 1 and audit_downloads[0]["--repo"] == "${GITHUB_REPOSITORY}"
             and audit_downloads[0]["--dir"] == "${AUDIT_BUNDLE_DIR}", "bundle_mapping_named_handoff")
    _require(not any(d["--name"] == publications[_BUNDLE_ROLES[1]]["name"] for d in downloads),
             "bundle_mapping_advisory_not_acquired")
    _require('--audit-bundle-dir "${AUDIT_BUNDLE_DIR}"' in assembly[4]["run"], "bundle_mapping_assembler_input")
    tree = ast.parse(payloads[next(p for p in payloads if p != SUBJECT_WORKFLOW_PATH)])
    stage = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_stage_package")
    audit_calls = [n for n in ast.walk(stage) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == "_copy_tree" and n.args and isinstance(n.args[0], ast.Name) and n.args[0].id == "selected_audit"]
    _require(len(audit_calls) == 1, "bundle_mapping_assembler_copy")
    out = audit_calls[0].args[1]
    _require(isinstance(out, ast.BinOp) and isinstance(out.op, ast.Div) and isinstance(out.left, ast.Name)
             and out.left.id == "staging_dir" and isinstance(out.right, ast.Constant)
             and isinstance(out.right.value, str), "bundle_mapping_assembler_destination")
    consumers = {role: [publications[role]["occurrence"]] for role in _BUNDLE_ROLES}
    for operation, consumed in inputs.items():
        for role in _BUNDLE_ROLES:
            if role in consumed:
                consumers[role].append(operation)
    consumers[_BUNDLE_ROLES[0]] += [_step_id("release_grade_recorded_path", 31), _step_id("assemble_release_grade_reference_package", 5)]
    consumers = {role: sorted(values) for role, values in consumers.items()}
    return {"locators": {role: paths[role] for role in _BUNDLE_ROLES},
            "producers": {role: _step_id("release_grade_recorded_path", n) for role, n in zip(_BUNDLE_ROLES, (22, 25))},
            "consumers": consumers, "copy_inputs": inputs, "copies": copies,
            "publications": publications, "package_member": out.right.value,
            "input_locators": {role: paths[role] for role in sorted({r for values in inputs.values() for r in values})},
            "conditions": {"assembly": rows[24]["if"], "publication": rows[31]["if"]}}


def _install_bundle_source_projection(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
    index = {row["state_id"].removeprefix("state:step5c:"): row for row in states}
    selected = {"state:step5c:" + role for role in _BUNDLE_ROLES}
    equations = set(facts["copy_inputs"])
    for row in states:
        row["required_consumer_occurrence_ids"] = [oid for oid in row["required_consumer_occurrence_ids"] if oid not in equations]
    for step in steps.values():
        oid = step["occurrence_id"]
        for key in ("input_state_ids", "output_state_ids"):
            step[key] = [sid for sid in step[key] if sid not in selected]
        if oid in equations:
            step["input_state_ids"] = ["state:step5c:" + role for role in facts["copy_inputs"][oid]]
            for role in facts["copy_inputs"][oid]:
                index[role]["required_consumer_occurrence_ids"].append(oid)
    for role in _BUNDLE_ROLES:
        row = index[role]; sid = row["state_id"]
        row["path_or_uri"] = facts["locators"][role]
        row["producer_occurrence_id"] = facts["producers"][role]
        row["required_consumer_occurrence_ids"] = facts["consumers"][role][:]
        for step in steps.values():
            if step["occurrence_id"] == facts["producers"][role]:
                step["output_state_ids"].append(sid)
            if step["occurrence_id"] in facts["consumers"][role]:
                _append_unique(step["input_state_ids"], sid)
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))


# Source-only provenance equations. A local file, its upload and the signed
# attestation receipt are distinct roles. No hosted read receipt is inferred.
_PROVENANCE_BUILD = "PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py"
_PROVENANCE_VERIFY = "PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py"
_PROVENANCE_ASSEMBLER = "PULSE_safe_pack_v0/tools/assemble_release_grade_reference_package_v0.py"
_PROVENANCE_ROLE = "artifact-provenance-binding"
_PROVENANCE_JOB = "release_grade_recorded_path"
_PROVENANCE_SOURCE_PINS = {
    SUBJECT_WORKFLOW_PATH: "ad1f165ad695c65827c590cbef9466e300d6b6e9",
    _PROVENANCE_BUILD: "d3f07cbbf8fd38831a42d8fe8e891c23df4c7792",
    _PROVENANCE_VERIFY: "665398c8841e4dd9534875831c93c749c3ccf94b",
    _PROVENANCE_ASSEMBLER: "8f01602e973b890eb2ae0928bd62dfd65e691f79",
    "tools/check_release_grade_package_complete_v1.py": "601e9a33097824b2055d908d25fad5667612c136",
    "PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py": "f54c37a32329d191e213bb71a6818858285ff20a",
}


def _provenance_literal(data: bytes, name: str) -> Any:
    nodes = []
    for node in ast.parse(data).body:
        names = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(target, ast.Name) and target.id == name for target in names):
            nodes.append(node.value)
    _require(len(nodes) == 1, "provenance_mapping_literal_missing", name)
    return ast.literal_eval(nodes[0])


def _provenance_commands(step: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """Tokenize the two reviewed invocations; never evaluate POLICY_ARGS."""
    result = []
    for line in step["run"].replace("\\\n", " ").splitlines():
        if re.match(r"^\s*python\s+", line):
            try:
                words = shlex.split(line)
            except ValueError as exc:
                raise PlanError("provenance_mapping_command_syntax") from exc
            _require(len(words) >= 2, "provenance_mapping_command_syntax")
            result.append((_mapping_path(words[1]), words[2:]))
    _require([tool for tool, _ in result] == [_PROVENANCE_BUILD, _PROVENANCE_VERIFY],
             "provenance_mapping_command_order")
    return result


def _provenance_source_projection(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    for path, pin in _PROVENANCE_SOURCE_PINS.items():
        _require(path in sources and sources[path].path == path, "provenance_mapping_source_missing", path)
        _require(_sha1_git_blob(sources[path].data) == pin, "provenance_mapping_source_drift", path)
    _require(workflow == _parse_yaml_document(sources[SUBJECT_WORKFLOW_PATH].data, label=SUBJECT_WORKFLOW_PATH),
             "provenance_mapping_workflow_drift")
    rows = workflow["jobs"][_PROVENANCE_JOB]["steps"]
    creation = rows[20]
    (_, build_args), (_, check_args) = _provenance_commands(creation)
    _require(build_args[-1:] == ["${POLICY_ARGS[@]}"], "provenance_mapping_policy_expansion")
    options = dict(zip(build_args[:-1:2], build_args[1:-1:2]))
    flags = {"--status": "final-status", "--policy": "gate-policy", "--ledger": "quality-ledger-final",
             "--release-decision": "release-decision", "--release-authority-manifest": "release-authority-manifest"}
    _require(len(build_args) == 13 and set(options) == set(flags) | {"--out"}, "provenance_mapping_arguments")
    policy_array = re.findall(r"(?m)^POLICY_ARGS=\((.*?)^\)", creation["run"], re.S)
    _require(len(policy_array) == 1 and shlex.split(policy_array[0]) ==
             ["--policy-set", "required", "--policy-set", "release_required"], "provenance_mapping_policy_sets")
    locator = _mapping_path(options["--out"])
    _require(check_args == ["--binding", options["--out"]], "provenance_mapping_verifier_input")

    # The producer's actual hashing calls establish the five content reads.
    tree = ast.parse(sources[_PROVENANCE_BUILD].data)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_binding")
    hashed = {call.args[0].id for call in ast.walk(function) if isinstance(call, ast.Call)
              and isinstance(call.func, ast.Name) and call.func.id == "sha256_file"
              and len(call.args) == 1 and isinstance(call.args[0], ast.Name)}
    _require(hashed == {flag[2:].replace("-", "_") + "_path" for flag in flags}, "provenance_mapping_producer_reads")
    input_locators = {role: _mapping_path(options[flag]) for flag, role in flags.items()}
    leaf = locator.rsplit("/", 1)[-1]
    publication = rows[28]
    _require(_mapping_path(publication["with"]["path"]) == locator, "provenance_mapping_upload_selector")
    _require(locator in rows[32]["with"]["path"].splitlines(), "provenance_mapping_recorded_copy")
    required = re.findall(r"(?m)^REQUIRED_FILES=\((.*?)^\)", rows[25]["run"], re.S)
    _require(len(required) == 1 and locator in [_mapping_path(x) for x in shlex.split(required[0])]
             and 'sha256sum "${artifact}"' in rows[25]["run"], "provenance_mapping_postcondition_read")

    attestation = workflow["jobs"]["attest_release_grade_artifact_binding"]["steps"]
    transfer = _package_commands(attestation[0], ("gh", "run", "download", "${GITHUB_RUN_ID}"), {"--repo", "--name", "--dir"})
    _require(len(transfer) == 1 and transfer[0]["--repo"] == "${GITHUB_REPOSITORY}"
             and transfer[0]["--name"] == publication["with"]["name"], "provenance_mapping_attestation_transfer")
    attested_path = _mapping_path(transfer[0]["--dir"] + "/" + leaf)
    _require(attestation[1]["with"]["subject-path"] == attested_path
             and 'sha256sum "' + attested_path + '"' in attestation[0]["run"], "provenance_mapping_attestation_subject")

    assembly = workflow["jobs"]["assemble_release_grade_reference_package"]["steps"]
    downloads = _package_commands(assembly[3], ("gh", "run", "download", "${GITHUB_RUN_ID}"), {"--repo", "--name", "--dir"})
    selected = [row for row in downloads if row["--name"] == publication["with"]["name"]]
    _require(len(selected) == 1 and selected[0]["--repo"] == "${GITHUB_REPOSITORY}"
             and selected[0]["--dir"] == "${ARTIFACT_BINDING_DIR}"
             and '--artifact-binding-dir "${ARTIFACT_BINDING_DIR}"' in assembly[4]["run"], "provenance_mapping_package_transfer")
    copies = _provenance_literal(sources[_PROVENANCE_ASSEMBLER].data, "ARTIFACT_FILES")
    matches = [row for row in copies if row[:2] == ("artifact_binding", leaf)]
    _require(len(matches) == 1, "provenance_mapping_package_member")
    member = matches[0][2]
    for path, constant in (("tools/check_release_grade_package_complete_v1.py", "JSON_OBJECT_FILES"),
                           ("PULSE_safe_pack_v0/tools/verify_release_grade_reference_package_v0.py", "JSON_FILES")):
        _require(member in _provenance_literal(sources[path].data, constant), "provenance_mapping_package_reader")
    readers = [(_PROVENANCE_JOB, n) for n in (26, 29, 33)] + [
        ("attest_release_grade_artifact_binding", 1), ("attest_release_grade_artifact_binding", 2),
        ("assemble_release_grade_reference_package", 5), ("verify_release_grade_reference_package", 5),
        ("verify_release_grade_reference_package", 7)]
    return {"locator": locator, "input_locators": input_locators, "producer": _step_id(_PROVENANCE_JOB, 21),
            "consumers": sorted(_step_id(job, n) for job, n in readers), "package_member": member,
            "attestation_subject": attested_path, "publication_name": publication["with"]["name"],
            "policy_sets": ["required", "release_required"]}


def _install_provenance_source_projection(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
    sid = "state:step5c:" + _PROVENANCE_ROLE
    by_role = {row["state_id"].removeprefix("state:step5c:"): row for row in states}
    for row in states:
        row["required_consumer_occurrence_ids"] = [oid for oid in row["required_consumer_occurrence_ids"] if oid != facts["producer"]]
    for step in steps.values():
        for key in ("input_state_ids", "output_state_ids"):
            step[key] = [item for item in step[key] if item != sid]
        if step["occurrence_id"] == facts["producer"]:
            step["input_state_ids"] = sorted("state:step5c:" + role for role in facts["input_locators"])
            step["output_state_ids"] = [sid]
        if step["occurrence_id"] in facts["consumers"]:
            _append_unique(step["input_state_ids"], sid)
    for role in facts["input_locators"]:
        _require(by_role[role]["path_or_uri"] == facts["input_locators"][role], "provenance_mapping_input_locator", role)
        _append_unique(by_role[role]["required_consumer_occurrence_ids"], facts["producer"])
    binding = by_role[_PROVENANCE_ROLE]
    binding["path_or_uri"] = facts["locator"]
    binding["producer_occurrence_id"] = facts["producer"]
    binding["required_consumer_occurrence_ids"] = facts["consumers"][:]
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))


# Selected pre-augmentation baseline/floor relations. These are source facts,
# not observed hosted-run reads or acceptance of the floor's own verdict.
_FLOOR_BUILD_PATH = "PULSE_safe_pack_v0/tools/build_self_contained_pulse_evidence_floor_v0.py"
_FLOOR_SOURCE_PINS = {
    SUBJECT_WORKFLOW_PATH: EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1,
    _FLOOR_BUILD_PATH: "2f7776e609ef7ef2fb8fcd40d5ee30e46ed46f6a",
    "PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py": "4298b7644acb0d8f7c50bbbac5308fb5038a501a",
    "tools/validate_status_schema.py": "f329f882805615402a9fed99f67d4e7667891c06",
}
_FLOOR_FLAGS = (
    "--repo-root", "--status", "--policy", "--registry", "--required-gate-evidence",
    "--out", "--repository", "--git-sha", "--run-key", "--workflow-ref",
    "--created-utc", "--external-model-status",
)


def _baseline_floor_source_projection(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    """Derive the bounded P14-P19 family from command and loader sources."""
    for path, pin in _FLOOR_SOURCE_PINS.items():
        _require(path in sources and sources[path].path == path, "floor_mapping_source_missing", path)
        _require(_sha1_git_blob(sources[path].data) == pin, "floor_mapping_source_drift", path)
    _require(workflow == _parse_yaml_document(sources[SUBJECT_WORKFLOW_PATH].data, label=SUBJECT_WORKFLOW_PATH),
             "floor_mapping_workflow_drift")
    rows = workflow["jobs"]["pulse"]["steps"]
    args = _recorded_argv(rows[17], _FLOOR_BUILD_PATH, set(_FLOOR_FLAGS))[0]
    origin = _recorded_argv(rows[12], "PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py",
                            {"--repo-root", "--out"})[0]
    status = _mapping_path(args["--status"])
    baseline = _mapping_assignment(rows[13], "DST")
    _require(_mapping_path(origin["--out"]) == status == _mapping_assignment(rows[13], "SRC"),
             "floor_mapping_status_version")
    copies = [shlex.split(line) for line in rows[13]["run"].splitlines() if line.strip().startswith("cp ")]
    _require(copies == [["cp", "$SRC", "$DST"]] and baseline != status, "floor_mapping_baseline_copy")
    guard = _recorded_argv(rows[14], "tools/validate_status_schema.py", {"--schema", "--status"})[0]
    _require(guard == {"--schema": "$SCHEMA", "--status": "$STATUS"}
             and _mapping_assignment(rows[14], "STATUS") == baseline
             and _mapping_assignment(rows[14], "SCHEMA") == "schemas/status/status_v1.schema.json",
             "floor_mapping_baseline_guard")
    inline = re.fullmatch(r"set -euo pipefail\npython - <<'PY'\n(.*?)\nPY\n", rows[15]["run"], re.S)
    _require(inline is not None, "floor_mapping_status_guard_source")
    tree = ast.parse(inline.group(1))
    paths = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "p" for t in node.targets)
             and isinstance(node.value, ast.Constant)]
    _require(paths == [status] and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "open" and n.args and isinstance(n.args[0], ast.Name)
             and n.args[0].id == "p" for n in ast.walk(tree)), "floor_mapping_status_guard_read")
    functions = {n.name: n for n in ast.parse(sources[_FLOOR_BUILD_PATH].data).body if isinstance(n, ast.FunctionDef)}
    loads = [(n.func.id, n.args[1].id) for n in ast.walk(functions["build_floor"])
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id in {"_load_json", "_load_yaml"} and len(n.args) >= 2 and isinstance(n.args[1], ast.Name)]
    _require(sorted(loads) == sorted([("_load_json", "status_path"), ("_load_yaml", "policy_path"),
                                    ("_load_yaml", "registry_path"), ("_load_json", "required_evidence_path")]),
             "floor_mapping_input_loaders")
    role_flags = {"pre-materialization-status": "--status", "gate-policy": "--policy",
                  "gate-registry": "--registry", "required-gate-evidence": "--required-gate-evidence"}
    inputs = {role: _mapping_path(args[flag]) for role, flag in role_flags.items()}
    _require(inputs["gate-policy"] == POLICY_PATH and inputs["gate-registry"] == REGISTRY_PATH
             and args["--repo-root"] == origin["--repo-root"] == "${GITHUB_WORKSPACE}"
             and args["--external-model-status"] == "not_required_for_tier0", "floor_mapping_context")
    floor = _mapping_path(args["--out"])
    _require(len({status, baseline, floor, *inputs.values()}) == 6, "floor_mapping_path_alias")
    _require(_mapping_assignment(rows[17], "FLOOR") == floor
             and 'sha256sum "${FLOOR}"' in rows[17]["run"], "floor_mapping_output_hash")
    upload = rows[18]
    _require(upload["uses"].startswith("actions/upload-artifact@")
             and upload["with"]["path"].splitlines() == [floor]
             and upload["with"]["if-no-files-found"] == "error", "floor_mapping_upload")
    inputs["pre-materialization-status"] += "#pre-release-required-materialization"
    locators = {**inputs, "status-baseline": baseline, "self-contained-evidence-floor": floor}
    equations = {
        14: (["pre-materialization-status"], ["status-baseline"]),
        15: (["status-baseline"], []), 16: (["pre-materialization-status"], []),
        18: (sorted(inputs), ["self-contained-evidence-floor"]),
        19: (["self-contained-evidence-floor"], []),
    }
    return {"locators": locators,
            "producers": {"status-baseline": _step_id("pulse", 14), "self-contained-evidence-floor": _step_id("pulse", 18)},
            "steps": {_step_id("pulse", n): {"inputs": a, "outputs": b} for n, (a, b) in equations.items()}}


def _install_baseline_floor_projection(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
    """Replace only the owned P14/P15/P16/P18/P19 selected-state equations."""
    by_role = {row["state_id"].removeprefix("state:step5c:"): row for row in states}
    for role, path in facts["locators"].items():
        _require(role in by_role, "floor_mapping_role_missing", role)
        if role in facts["producers"]:
            by_role[role]["path_or_uri"] = path
            by_role[role]["producer_occurrence_id"] = facts["producers"][role]
        else:
            _require(by_role[role]["path_or_uri"] == path, "floor_mapping_input_locator", role)
    owned = set(facts["steps"])
    for row in states:
        row["required_consumer_occurrence_ids"] = [oid for oid in row["required_consumer_occurrence_ids"] if oid not in owned]
    for step in steps.values():
        oid = step["occurrence_id"]
        if oid not in owned:
            continue
        for field, direction in (("input_state_ids", "inputs"), ("output_state_ids", "outputs")):
            step[field] = sorted("state:step5c:" + role for role in facts["steps"][oid][direction])
        for role in facts["steps"][oid]["inputs"]:
            _append_unique(by_role[role]["required_consumer_occurrence_ids"], oid)
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))


# Selected pre-attestation preservation. Source selectors are not observed
# member receipts, and restoring content does not create a new content origin.
_PRESERVATION_ARCHIVE_ROLE = "pre-attestation-pulse-artifacts"
_PRESERVATION_RUNNER_FLAGS = (
    "--repo-root", "--dataset", "--raw-out", "--manifest-out", "--manifest-schema",
    "--model-revision", "--token-env", "--repository", "--git-sha", "--run-key",
    "--workflow-ref", "--release-candidate", "--created-utc", "--torch-threads", "--max-new-tokens",
)


def _preattest_preservation_source_projection(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    """Derive upload membership and the bounded restore/copy input equations."""
    obj = sources.get(SUBJECT_WORKFLOW_PATH)
    _require(obj is not None and obj.path == SUBJECT_WORKFLOW_PATH, "preservation_mapping_source_missing")
    _require(_sha1_git_blob(obj.data) == EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1, "preservation_mapping_source_drift")
    _require(workflow == _parse_yaml_document(obj.data, label=SUBJECT_WORKFLOW_PATH), "preservation_mapping_workflow_drift")
    floor = _baseline_floor_source_projection(workflow, sources)
    pulse = workflow["jobs"]["pulse"]["steps"]
    restore = workflow["jobs"][_RECORDED_JOB]["steps"][3]
    upload = pulse[36]
    _require(upload["uses"].startswith("actions/upload-artifact@")
             and upload["with"]["if-no-files-found"] == "error", "preservation_mapping_upload_profile")
    selected = {role: locator for role, locator in floor["locators"].items()
                if role not in {"gate-policy", "gate-registry"}}
    runner = _recorded_argv(pulse[21], LLAMAGUARD_RUNNER_PATH, set(_PRESERVATION_RUNNER_FLAGS))[0]
    selected["llamaguard-raw-evidence"] = _mapping_path(runner["--raw-out"])
    selected["llamaguard-evaluator-manifest"] = _mapping_path(runner["--manifest-out"])
    selected["llamaguard-summary"] = _mapping_assignment(pulse[22], "SUMMARY")
    # There is no state role for three additional source-selected files in the
    # current graph. Retain those selectors as unresolved extent, not as claims
    # that the seven selected local roles exhaust this artifact's contents.
    upload_paths = [_mapping_path(line) for line in upload["with"]["path"].splitlines()]
    physical = {locator.split("#", 1)[0]: role for role, locator in selected.items()}
    _require(len(physical) == len(selected) == 7 and len(upload_paths) == len(set(upload_paths)) == 10
             and set(physical) <= set(upload_paths), "preservation_mapping_upload_members")
    download_dir = _mapping_assignment(restore, "DOWNLOAD_DIR", symbolic_temp=True)
    canonical_dir = _mapping_assignment(restore, "CANONICAL_ARTIFACTS")
    download = _package_commands(restore, ("gh", "run", "download", "${GITHUB_RUN_ID}"),
                                 {"--repo", "--name", "--dir"})
    _require(len(download) == 1 and download[0]["--repo"] == "${GITHUB_REPOSITORY}"
             and download[0]["--dir"] == "${DOWNLOAD_DIR}", "preservation_mapping_download_context")
    archive_name = _package_artifact_name(upload["with"]["name"])
    downloaded_name = download[0]["--name"].replace("${GITHUB_RUN_ID}", "{workflow_run_id}").replace("${GITHUB_RUN_ATTEMPT}", "1")
    _require(downloaded_name == archive_name, "preservation_mapping_archive_identity")
    body = restore["run"]
    copies = [shlex.split(line)[1] for line in body.splitlines() if line.startswith('copy_required_artifact "')]
    _require(len(copies) == len(set(copies)) == 7
             and all(re.fullmatch(r"[A-Za-z0-9_.-]+", name) for name in copies), "preservation_mapping_restore_members")
    _require('local name="$1"' in body and 'cp "${src}" "${CANONICAL_ARTIFACTS}/${name}"' in body
             and 'find "${DOWNLOAD_DIR}" -type f -name "${name}" | head -n 1 || true' in body,
             "preservation_mapping_copy_source")
    restored_paths = [_mapping_path(canonical_dir + "/" + name) for name in copies]
    loops = re.findall(r"^for artifact in (.*?)^do$", body, re.M | re.S)
    _require(len(loops) == 1, "preservation_mapping_hash_loop")
    hashed_paths = [_mapping_path(word.replace("${CANONICAL_ARTIFACTS}/", canonical_dir + "/"))
                    for word in shlex.split(loops[0].replace("\\\n", " "))]
    _require(hashed_paths == restored_paths and 'sha256sum "${artifact}"' in body
             and '! -f "${artifact}" || -L "${artifact}" || ! -s "${artifact}"' in body,
             "preservation_mapping_restore_hash")
    _require(set(restored_paths) <= set(upload_paths), "preservation_mapping_restore_not_uploaded")
    restored_roles = sorted(physical[path] for path in restored_paths if path in physical)
    _require(len(restored_roles) == 4 and "pre-materialization-status" in restored_roles,
             "preservation_mapping_restore_role_extent")
    publish_id, restore_id = _step_id("pulse", 37), _step_id(_RECORDED_JOB, 4)
    origins = {"pre-materialization-status": _step_id("pulse", 13),
               "required-gate-evidence": _step_id("pulse", 11), **floor["producers"],
               "llamaguard-raw-evidence": _step_id("pulse", 22),
               "llamaguard-evaluator-manifest": _step_id("pulse", 22),
               "llamaguard-summary": _step_id("pulse", 23), _PRESERVATION_ARCHIVE_ROLE: publish_id}
    return {"locators": {**selected, _PRESERVATION_ARCHIVE_ROLE: "artifact://" + archive_name},
            "origins": origins, "upload_paths": sorted(upload_paths), "restored_paths": sorted(restored_paths),
            "unmodeled_upload_paths": sorted(set(upload_paths) - set(physical)),
            "unmodeled_restore_paths": sorted(set(restored_paths) - set(physical)),
            "download_directory": download_dir,
            "steps": {publish_id: {"inputs": sorted(selected), "outputs": [_PRESERVATION_ARCHIVE_ROLE]},
                      restore_id: {"inputs": sorted([_PRESERVATION_ARCHIVE_ROLE, *restored_roles]), "outputs": []}}}


def _install_preattest_preservation_projection(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
    """Bind only P37 and R4; retain every local content origin and outside duty."""
    by_role = {row["state_id"].removeprefix("state:step5c:"): row for row in states}
    for role, locator in facts["locators"].items():
        _require(role in by_role and by_role[role]["path_or_uri"] == locator,
                 "preservation_mapping_input_locator", role)
        _require(by_role[role]["producer_occurrence_id"] == facts["origins"][role],
                 "preservation_mapping_input_origin", role)
    owned = set(facts["steps"])
    for row in states:
        row["required_consumer_occurrence_ids"] = [oid for oid in row["required_consumer_occurrence_ids"] if oid not in owned]
    for step in steps.values():
        oid = step["occurrence_id"]
        if oid not in owned:
            continue
        for field, direction in (("input_state_ids", "inputs"), ("output_state_ids", "outputs")):
            step[field] = sorted("state:step5c:" + role for role in facts["steps"][oid][direction])
        for role in facts["steps"][oid]["inputs"]:
            _append_unique(by_role[role]["required_consumer_occurrence_ids"], oid)
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))


# Selected LlamaGuard preservation paths. File content, an artifact transport,
# and an attestation result are different objects. These equations observe no
# new runtime reads and do not verify the archived bytes or an attestation.
_LG_PRESERVATION_JOB = "attest_llamaguard_current_run_summary"
_LG_PRESERVATION_FILES = {
    "llamaguard_raw.jsonl": "llamaguard-raw-evidence",
    "llamaguard_evaluator_manifest_v0.json": "llamaguard-evaluator-manifest",
    "llamaguard_summary.json": "llamaguard-summary",
    "llamaguard_summary.bundle.json": "llamaguard-attestation-bundle",
    "llamaguard_summary.envelope.json": "llamaguard-attestation-envelope",
    "llamaguard_attestation_verifier_v1.json": "llamaguard-attestation-verifier",
}


def _llamaguard_preservation_source_projection(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    """Start at each literal upload list and verify its copy/hash handoff."""
    obj = sources.get(SUBJECT_WORKFLOW_PATH)
    _require(obj is not None and obj.path == SUBJECT_WORKFLOW_PATH, "lg_preservation_source_missing")
    _require(_sha1_git_blob(obj.data) == EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1,
             "lg_preservation_source_drift")
    _require(workflow == _parse_yaml_document(obj.data, label=SUBJECT_WORKFLOW_PATH),
             "lg_preservation_workflow_drift")
    jobs = workflow["jobs"]
    locators: dict[str, str] = {}
    equations: dict[str, Any] = {}
    handoffs: list[dict[str, Any]] = []
    for up_job, up_n, read_job, read_n, variable, count in (
        ("pulse", 24, _LG_PRESERVATION_JOB, 4, "CANONICAL_DIR", 3),
        (_LG_PRESERVATION_JOB, 8, "release_grade_recorded_path", 5, "CANONICAL_EXTERNAL", 6),
    ):
        upload = jobs[up_job]["steps"][up_n - 1]
        restored = jobs[read_job]["steps"][read_n - 1]
        _require(upload.get("uses") == "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
                 and upload["with"].get("if-no-files-found") == "error", "lg_preservation_upload_profile")
        paths = [_mapping_path(line) for line in upload["with"]["path"].splitlines()]
        names = [path.rsplit("/", 1)[-1] for path in paths]
        expected_names = list(_LG_PRESERVATION_FILES)[:count]
        _require(len(paths) == len(set(paths)) == len(set(names)) == count
                 and names == expected_names, "lg_preservation_upload_members")
        for path, name in zip(paths, names):
            role = _LG_PRESERVATION_FILES[name]
            _require(role not in locators or locators[role] == path, "lg_preservation_version_alias")
            locators[role] = path
        root = _mapping_assignment(restored, variable)
        download_root = _mapping_assignment(restored, "DOWNLOAD_DIR", symbolic_temp=True)
        downloads = _package_commands(restored, ("gh", "run", "download", "${GITHUB_RUN_ID}"),
                                      {"--repo", "--name", "--dir"})
        name = _package_artifact_name(upload["with"]["name"])
        _require(len(downloads) == 1 and downloads[0]["--repo"] == "${GITHUB_REPOSITORY}"
                 and downloads[0]["--dir"] == "${DOWNLOAD_DIR}"
                 and downloads[0]["--name"].replace("${GITHUB_RUN_ID}", "{workflow_run_id}").replace("${GITHUB_RUN_ATTEMPT}", "1") == name,
                 "lg_preservation_download_context")
        body = restored["run"]
        if count == 3:
            loops = re.findall(r"^for name in (.*?)^do$", body, re.M | re.S)
            _require(len(loops) == 1, "lg_preservation_copy_loop")
            copied_names = shlex.split(loops[0].replace("\\\n", " "))
            _require('cp "${src}" "${CANONICAL_DIR}/${name}"' in body, "lg_preservation_copy_destination")
            destinations = [root + "/" + leaf for leaf in copied_names]
        else:
            calls = [shlex.split(line)[1:] for line in body.replace("\\\n", " ").splitlines()
                     if line.startswith("restore_external_artifact ") and not line.startswith("restore_external_artifact ()")]
            _require(all(len(args) == 2 for args in calls), "lg_preservation_copy_arguments")
            copied_names = [args[0] for args in calls]
            destinations = [_mapping_path(args[1].replace("${CANONICAL_EXTERNAL}/", root + "/")) for args in calls]
            _require('local name="$1"' in body and 'local dst="$2"' in body
                     and 'cp "${src}" "${dst}"' in body, "lg_preservation_copy_destination")
        _require(copied_names == names and destinations == paths
                 and 'find "${DOWNLOAD_DIR}" -type f -name "${name}" | head -n 1 || true' in body,
                 "lg_preservation_copy_members")
        hashes = re.findall(r"^for artifact in (.*?)^do$", body, re.M | re.S)
        _require(len(hashes) == 1, "lg_preservation_hash_loop")
        hashed = [_mapping_path(word.replace("${" + variable + "}/", root + "/"))
                  for word in shlex.split(hashes[0].replace("\\\n", " "))]
        _require(hashed == paths and 'sha256sum "${artifact}"' in body
                 and '! -f "${artifact}" || -L "${artifact}"' in body,
                 "lg_preservation_hash_members")
        # L4 does not enforce non-empty content. R5 does. Retain this difference
        # rather than assigning stronger semantics to the original copy shell.
        nonempty = '|| ! -s "${artifact}"' in body
        _require(nonempty is (count == 6), "lg_preservation_nonempty_guard")
        publisher, restorer = _step_id(up_job, up_n), _step_id(read_job, read_n)
        roles = sorted(_LG_PRESERVATION_FILES[leaf] for leaf in names)
        equations[publisher] = {"inputs": roles, "outputs": []}
        equations[restorer] = {"inputs": roles, "outputs": []}
        handoffs.append({"publisher": publisher, "restorer": restorer,
                         "artifact_name_template": name, "upload_paths": paths,
                         "restore_paths": destinations, "hash_paths": hashed,
                         "download_directory": download_root, "requires_nonempty": nonempty,
                         "upload_condition": upload.get("if"), "restore_condition": restored.get("if"),
                         "archive_state_modeled": False})
    origins = {role: _step_id(job, n) for role, job, n in (
        ("llamaguard-raw-evidence", "pulse", 22), ("llamaguard-evaluator-manifest", "pulse", 22),
        ("llamaguard-summary", "pulse", 23), ("llamaguard-attestation-bundle", _LG_PRESERVATION_JOB, 5),
        ("llamaguard-attestation-envelope", _LG_PRESERVATION_JOB, 6),
        ("llamaguard-attestation-verifier", _LG_PRESERVATION_JOB, 7),
    )}
    return {"locators": locators, "origins": origins, "steps": equations, "handoffs": handoffs}


def _install_llamaguard_preservation_projection(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
    """Replace only the four selected preservation operations, not file origins."""
    rows = {row["state_id"].removeprefix("state:step5c:"): row for row in states}
    for role, path in facts["locators"].items():
        _require(role in rows and rows[role]["path_or_uri"] == path, "lg_preservation_input_locator", role)
        _require(rows[role]["producer_occurrence_id"] == facts["origins"][role], "lg_preservation_input_origin", role)
    owned = set(facts["steps"])
    for row in states:
        row["required_consumer_occurrence_ids"] = [oid for oid in row["required_consumer_occurrence_ids"] if oid not in owned]
    for step in steps.values():
        oid = step["occurrence_id"]
        if oid not in owned:
            continue
        equation = facts["steps"][oid]
        step["input_state_ids"] = sorted("state:step5c:" + role for role in equation["inputs"])
        step["output_state_ids"] = []
        for role in equation["inputs"]:
            _append_unique(rows[role]["required_consumer_occurrence_ids"], oid)
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))


# L5/L6/L7 attestation-path projection. These are source-declared selected
# state reads, not captured read receipts or cryptographic verification results.
_LG_ATTEST_BUILD = "PULSE_safe_pack_v0/tools/build_llamaguard_attestation_envelope_v1.py"
_LG_ATTEST_CHECK = "PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py"
_LG_ATTEST_PINS = {
    SUBJECT_WORKFLOW_PATH: EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1,
    _LG_ATTEST_BUILD: "ecbef6ce1d2a48b5c466b79c916d1161de9df377",
    _LG_ATTEST_CHECK: "7fa6539f614d3d30bb603c523889f38bf4c012c1",
}


def _llamaguard_attestation_source_projection(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    """Resolve L6 defaults, then bind the action and L7 replay selectors."""
    for path, expected in _LG_ATTEST_PINS.items():
        obj = sources.get(path)
        _require(obj is not None and obj.path == path, "lg_attestation_source_missing", path)
        _require(_sha1_git_blob(obj.data) == expected, "lg_attestation_source_drift", path)
    _require(workflow == _parse_yaml_document(sources[SUBJECT_WORKFLOW_PATH].data, label=SUBJECT_WORKFLOW_PATH),
             "lg_attestation_workflow_drift")
    job = "attest_llamaguard_current_run_summary"
    action, envelope_step, verifier_step = workflow["jobs"][job]["steps"][4:7]
    build_args = _recorded_argv(envelope_step, _LG_ATTEST_BUILD, {
        "--repo-root", "--bundle-source", "--repository", "--source-digest", "--workflow-ref",
        "--signer-identity", "--verified-at", "--attestation-id", "--attestation-url", "--attestation-action-ref",
    })[0]
    replay_args = _recorded_argv(verifier_step, _LG_ATTEST_CHECK, {
        "--repo-root", "--summary", "--envelope", "--summary-schema", "--envelope-schema",
        "--signer-policy", "--repository", "--source-digest", "--out",
    })[0]
    _require(build_args["--repo-root"] == replay_args["--repo-root"] == "${GITHUB_WORKSPACE}"
             and build_args["--repository"] == replay_args["--repository"] == "${GITHUB_REPOSITORY}"
             and build_args["--source-digest"] == replay_args["--source-digest"] == "${GITHUB_SHA}",
             "lg_attestation_execution_context")
    _require(action.get("uses") == build_args["--attestation-action-ref"]
             == "actions/attest@f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6"
             and action.get("id") == "attest_llamaguard_summary", "lg_attestation_action_identity")
    for flag, output in (("--bundle-source", "bundle-path"), ("--attestation-id", "attestation-id"),
                         ("--attestation-url", "attestation-url")):
        _require(build_args[flag] == "${{ steps." + action["id"] + ".outputs." + output + " }}",
                 "lg_attestation_action_output_binding", flag)
    source = sources[_LG_ATTEST_BUILD].data
    tree = ast.parse(source)
    parser = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_parser")
    defaults: dict[str, str] = {}
    for node in ast.walk(parser):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument" and node.args and isinstance(node.args[0], ast.Constant)):
            continue
        default = [kw.value for kw in node.keywords if kw.arg == "default"]
        if len(default) == 1 and isinstance(default[0], ast.Name):
            flag = node.args[0].value
            _require(flag not in defaults, "lg_attestation_duplicate_default", flag)
            defaults[flag] = _mapping_path(_python_constant(source, name=default[0].id, label=_LG_ATTEST_BUILD))
    roles = {
        "llamaguard-summary": "--summary", "llamaguard-raw-evidence": "--raw-evidence",
        "llamaguard-evaluator-manifest": "--evaluator-manifest", "llamaguard-dataset": "--dataset",
        "external-signer-policy": "--signer-policy", "threshold-policy": "--threshold-policy",
        "workflow-source": "--workflow", "llamaguard-attestation-bundle": "--bundle-out",
        "llamaguard-attestation-envelope": "--out",
    }
    _require(set(roles.values()) <= set(defaults), "lg_attestation_default_extent")
    locators = {role: defaults[flag] for role, flag in roles.items()}
    locators["llamaguard-attestation-verifier"] = _mapping_path(replay_args["--out"])
    for flag, role in (("--summary", "llamaguard-summary"), ("--envelope", "llamaguard-attestation-envelope"),
                       ("--signer-policy", "external-signer-policy")):
        _require(_mapping_path(replay_args[flag]) == locators[role], "lg_attestation_replay_selector", flag)
    for flag in ("--summary-schema", "--envelope-schema"):
        _require(_mapping_path(replay_args[flag]) == defaults[flag], "lg_attestation_schema_selector", flag)
    _require(_mapping_path(action["with"]["subject-path"]) == locators["llamaguard-summary"],
             "lg_attestation_subject_selector")
    _require(locators["llamaguard-attestation-verifier"] == _python_constant(source, name="VERIFIER_REPORT_REL", label=_LG_ATTEST_BUILD),
             "lg_attestation_report_selector")
    # These semantics are fixed by the exact called-tool pin, not inferred
    # merely because a filename or a policy reference occurs in the source.
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    reads = {n.args[0].id for function in ("main", "_validate_summary") for n in ast.walk(functions[function])
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_sha256_file"
             and n.args and isinstance(n.args[0], ast.Name)}
    _require({"summary_path", "raw_path", "dataset_path", "evaluator_manifest_path", "signer_policy_path",
              "threshold_policy_path", "workflow_path"} <= reads, "lg_attestation_selected_digest_reads")
    persist = ast.unparse(functions["_persist_bundle"])
    _require("source_bytes = source.read_bytes()" in persist
             and "_write_bytes_atomic(destination, source_bytes," in persist
             and "destination.read_bytes() != source_bytes" in persist, "lg_attestation_bundle_preservation")
    l5, l6, l7 = (_step_id(job, n) for n in (5, 6, 7))
    envelope_inputs = sorted(role for role in roles if role != "llamaguard-attestation-envelope")
    return {"locators": locators,
            "origins": {**{role: None for role in ("workflow-source", "threshold-policy", "external-signer-policy", "llamaguard-dataset")},
                        "llamaguard-raw-evidence": _step_id("pulse", 22), "llamaguard-evaluator-manifest": _step_id("pulse", 22),
                        "llamaguard-summary": _step_id("pulse", 23), "llamaguard-attestation-bundle": l5,
                        "llamaguard-attestation-envelope": l6, "llamaguard-attestation-verifier": l7},
            "steps": {l5: {"inputs": ["llamaguard-summary"], "outputs": ["llamaguard-attestation-bundle"]},
                      l6: {"inputs": envelope_inputs, "outputs": ["llamaguard-attestation-envelope"]},
                      l7: {"inputs": sorted(("llamaguard-summary", "llamaguard-attestation-envelope", "external-signer-policy",
                                               "llamaguard-attestation-bundle")), "outputs": ["llamaguard-attestation-verifier"]}},
            "bundle_handoff": {"action_output_selector": build_args["--bundle-source"],
                               "canonical_preservation_path": locators["llamaguard-attestation-bundle"],
                               "preservation_occurrence_id": l6, "content_origin_occurrence_id": l5,
                               "source_requires_byte_identity": True}}


def _install_llamaguard_attestation_projection(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
    """Bind the three steps without relabeling content origins or other reads."""
    rows = {row["state_id"].removeprefix("state:step5c:"): row for row in states}
    for role, path in facts["locators"].items():
        _require(role in rows and rows[role]["path_or_uri"] == path, "lg_attestation_input_locator", role)
        _require(rows[role]["producer_occurrence_id"] == facts["origins"][role], "lg_attestation_input_origin", role)
    owned = set(facts["steps"])
    for row in states:
        row["required_consumer_occurrence_ids"] = [oid for oid in row["required_consumer_occurrence_ids"] if oid not in owned]
    for step in steps.values():
        oid = step["occurrence_id"]
        if oid not in owned:
            continue
        equation = facts["steps"][oid]
        step["input_state_ids"] = sorted("state:step5c:" + role for role in equation["inputs"])
        step["output_state_ids"] = sorted("state:step5c:" + role for role in equation["outputs"])
        for role in equation["inputs"]:
            _append_unique(rows[role]["required_consumer_occurrence_ids"], oid)
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))


# Selected raw-producer / summary-ingest family. Source traversal of the
# controlled records is not an observed read receipt or case-ID admission.
_LG_INGEST_PATH = "PULSE_safe_pack_v0/tools/adapters/llamaguard_ingest.py"
_LG_PRODUCTION_PINS = {
    SUBJECT_WORKFLOW_PATH: EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1,
    LLAMAGUARD_RUNNER_PATH: EXPECTED_LLAMAGUARD_RUNNER_BLOB_SHA1,
    LLAMAGUARD_DATASET_PATH: EXPECTED_DATASET_BLOB_SHA1,
    _LG_INGEST_PATH: "b0e0479c4939110b08350655be234badffa189f1",
}


def _llamaguard_production_source_projection(workflow: dict[str, Any], sources: dict[str, GitObject]) -> dict[str, Any]:
    """Resolve the producer's paths, then the ingester's bound file reads."""
    for path, expected in _LG_PRODUCTION_PINS.items():
        obj = sources.get(path)
        _require(obj is not None and obj.path == path, "lg_production_source_missing", path)
        _require(_sha1_git_blob(obj.data) == expected, "lg_production_source_drift", path)
    _require(workflow == _parse_yaml_document(sources[SUBJECT_WORKFLOW_PATH].data, label=SUBJECT_WORKFLOW_PATH),
             "lg_production_workflow_drift")
    rows = workflow["jobs"]["pulse"]["steps"]
    producer = _recorded_argv(rows[21], LLAMAGUARD_RUNNER_PATH, {
        "--repo-root", "--dataset", "--raw-out", "--manifest-out", "--manifest-schema",
        "--model-revision", "--token-env", "--repository", "--git-sha", "--run-key",
        "--workflow-ref", "--release-candidate", "--created-utc", "--torch-threads", "--max-new-tokens",
    })[0]
    ingest = _recorded_argv(rows[22], _LG_INGEST_PATH, {
        "--repo-root", "--in", "--dataset", "--evaluator-manifest", "--out", "--schema",
        "--thresholds", "--run-id", "--generated-at", "--release-candidate", "--git-sha",
        "--repository", "--signer-identity", "--tool-version",
    })[0]
    runner = sources[LLAMAGUARD_RUNNER_PATH].data
    adapter = sources[_LG_INGEST_PATH].data
    locators: dict[str, str] = {}
    for role, flag, constant in (
        ("llamaguard-dataset", "--dataset", "DATASET_REL"),
        ("llamaguard-raw-evidence", "--raw-out", "RAW_REL"),
        ("llamaguard-evaluator-manifest", "--manifest-out", "MANIFEST_REL"),
    ):
        locators[role] = _mapping_path(producer[flag])
        _require(locators[role] == _python_constant(runner, name=constant, label=LLAMAGUARD_RUNNER_PATH),
                 "lg_production_canonical_path", role)
    for flag, role in (("--in", "llamaguard-raw-evidence"), ("--dataset", "llamaguard-dataset"),
                       ("--evaluator-manifest", "llamaguard-evaluator-manifest")):
        _require(_mapping_path(ingest[flag]) == locators[role], "lg_production_input_handoff", role)
    locators["threshold-policy"] = _mapping_path(ingest["--thresholds"])
    _require(locators["threshold-policy"] == THRESHOLD_POLICY_PATH
             == _python_constant(adapter, name="THRESHOLDS_REL", label=_LG_INGEST_PATH),
             "lg_production_threshold_path")
    locators["llamaguard-summary"] = _mapping_path(ingest["--out"])
    _require(locators["llamaguard-summary"] == _mapping_assignment(rows[22], "SUMMARY"),
             "lg_production_summary_postcondition")
    _require(producer["--model-revision"] == ingest["--tool-version"] == "${LLAMAGUARD_VERSION}"
             and producer["--run-key"] == ingest["--run-id"] == "${PULSE_RUN_KEY}"
             and producer["--repo-root"] == ingest["--repo-root"] == "${GITHUB_WORKSPACE}"
             and producer["--git-sha"] == ingest["--git-sha"] == "${GITHUB_SHA}"
             and producer["--repository"] == ingest["--repository"] == "${GITHUB_REPOSITORY}",
             "lg_production_source_context")
    funcs = {node.name: node for node in ast.parse(runner).body if isinstance(node, ast.FunctionDef)}
    main = ast.unparse(funcs["main"])
    for expression in (
        "cases = _load_cases(dataset_path)", "dataset_sha256 = _sha256_file(dataset_path)",
        "for case_index, case in enumerate(cases):", "_classify_case(torch, model, tokenizer, case, args.max_new_tokens)",
        "'case_id': case['case_id']", "'llamaguard': {'label': label, 'categories': categories",
        "for record in records", "_write_text_atomic(raw_path, raw_text)", "_write_json_atomic(manifest_path, manifest)",
    ):
        _require(expression in main, "lg_production_record_traversal", expression)
    af = {node.name: node for node in ast.parse(adapter).body if isinstance(node, ast.FunctionDef)}
    build_text = ast.unparse(af["_build_summary"])
    # The dataset and manifest are hashed, not parsed/admitted by this adapter.
    for expression in (
        "_read_llamaguard_jsonl(raw_path)", "_load_threshold(thresholds_path)",
        "_sha256_file(raw_path)", "_sha256_file(dataset_path)", "_sha256_file(evaluator_manifest_path)",
    ):
        _require(expression in build_text, "lg_production_ingest_read", expression)
    reader = ast.unparse(af["_read_llamaguard_jsonl"])
    for expression in ("for line_number, raw_line in enumerate(handle, start=1):",
                       "classification = record.get('llamaguard')", "label_raw = classification.get('label')"):
        _require(expression in reader, "lg_production_classification_reader", expression)
    adapter_main = ast.unparse(af["main"])
    for expression in ("Path(args.raw_input)", "Path(args.dataset)", "Path(args.evaluator_manifest)",
                       "Path(args.thresholds)", "_write_json_atomic(output_path, summary)"):
        _require(expression in adapter_main, "lg_production_ingest_forwarding", expression)
    case_ids = _load_case_ids(sources[LLAMAGUARD_DATASET_PATH].data)
    p22, p23 = (_step_id("pulse", n) for n in (22, 23))
    origins: dict[str, str | None] = {
        "llamaguard-dataset": None, "threshold-policy": None,
        "llamaguard-raw-evidence": p22, "llamaguard-evaluator-manifest": p22,
        "llamaguard-summary": p23,
    }
    inputs, outputs = [], []
    for case_id in case_ids:
        given, result = "llamaguard-input:" + case_id, "llamaguard-output:" + case_id
        inputs.append(given); outputs.append(result)
        locators[given] = "dataset://" + locators["llamaguard-dataset"] + "#" + case_id + "/input"
        locators[result] = "artifact://" + Path(locators["llamaguard-raw-evidence"]).name + "#" + case_id + "/classification"
        origins[given], origins[result] = None, p22
    return {
        "locators": locators, "origins": origins,
        "steps": {
            p22: {"inputs": sorted(["llamaguard-dataset", *inputs]),
                  "outputs": sorted(["llamaguard-raw-evidence", "llamaguard-evaluator-manifest", *outputs])},
            p23: {"inputs": sorted(["llamaguard-raw-evidence", "llamaguard-evaluator-manifest",
                                      "llamaguard-dataset", "threshold-policy", *outputs]),
                  "outputs": ["llamaguard-summary"]},
        },
        "ingest_read_modes": {"llamaguard-raw-evidence": "classification_parse_and_digest",
                              "llamaguard-dataset": "digest_only", "llamaguard-evaluator-manifest": "digest_only",
                              "threshold-policy": "threshold_parse"},
        "classification_handoff": {"case_ids": list(case_ids), "producer_emits_one_record_per_case": True,
                                   "ingester_traverses_all_records": True, "ingester_checks_case_identity": False,
                                   "observed_consumption_proved": False},
    }


def _install_llamaguard_production_projection(states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any]) -> None:
    """Install only the selected source relations; retain all evidence duties."""
    rows = {row["state_id"].removeprefix("state:step5c:"): row for row in states}
    for role, path in facts["locators"].items():
        _require(role in rows and rows[role]["path_or_uri"] == path, "lg_production_input_locator", role)
        _require(rows[role]["producer_occurrence_id"] == facts["origins"][role], "lg_production_input_origin", role)
    owned = set(facts["steps"])
    for row in states:
        row["required_consumer_occurrence_ids"] = [oid for oid in row["required_consumer_occurrence_ids"] if oid not in owned]
    for step in steps.values():
        oid = step["occurrence_id"]
        if oid in owned:
            equation = facts["steps"][oid]
            step["input_state_ids"] = sorted("state:step5c:" + role for role in equation["inputs"])
            step["output_state_ids"] = sorted("state:step5c:" + role for role in equation["outputs"])
            for role in equation["inputs"]:
                _append_unique(rows[role]["required_consumer_occurrence_ids"], oid)
    for row in states:
        row["required_consumer_occurrence_ids"] = sorted(set(row["required_consumer_occurrence_ids"]))



# P36 hashes the pre-attestation file set before P37 publishes it. Hash reads
# are not signature/content admission and do not make P36 a content producer.
def _pre_attestation_postcondition_source_projection(
    workflow: dict[str, Any], sources: dict[str, GitObject],
) -> dict[str, Any]:
    source = sources.get(SUBJECT_WORKFLOW_PATH)
    _require(source is not None and source.path == SUBJECT_WORKFLOW_PATH,
             "pre_attest_postcondition_source_missing")
    _require(_sha1_git_blob(source.data) == EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1,
             "pre_attest_postcondition_source_drift")
    _require(workflow == _parse_yaml_document(source.data, label=SUBJECT_WORKFLOW_PATH),
             "pre_attest_postcondition_workflow_drift")
    rows = workflow["jobs"]["pulse"]["steps"]
    check, upload = rows[35], rows[36]
    _require(check["shell"] == "bash" and check["if"] == upload["if"],
             "pre_attest_postcondition_condition_mismatch")
    match = re.fullmatch(
        r'set -euo pipefail\n\nREQUIRED_FILES=\(\n(?P<paths>(?:  "[^"\n]+"\n)+)\)\n\n'
        r'for artifact in "\$\{REQUIRED_FILES\[@\]\}"; do\n'
        r'  if \[\[ ! -f "\$\{artifact\}" \|\| -L "\$\{artifact\}" \|\| ! -s "\$\{artifact\}" \]\]; then\n'
        r'    echo "::error::release-grade pre-attestation artifact is missing, empty, or symlinked: \$\{artifact\}"\n'
        r'    exit 1\n  fi\n\n  sha256sum "\$\{artifact\}"\ndone\n\n'
        r'echo "OK: release-grade pre-attestation artifact postconditions satisfied"\n',
        check["run"],
    )
    _require(match is not None, "pre_attest_postcondition_source_form")
    paths = [_mapping_path(shlex.split(line)[0]) for line in match.group("paths").splitlines()]
    publication = [_mapping_path(line) for line in upload["with"]["path"].splitlines()]
    _require(len(paths) == len(set(paths)) == 10 and paths == publication,
             "pre_attest_postcondition_path_inventory")
    preservation = _preattest_preservation_source_projection(workflow, sources)
    local = {role: path for role, path in preservation["locators"].items()
             if role != _PRESERVATION_ARCHIVE_ROLE}
    physical = {path.split("#", 1)[0]: role for role, path in local.items()}
    _require(len(physical) == len(local) == 7 and set(physical) <= set(paths),
             "pre_attest_postcondition_selected_extent")
    return {
        "locators": local,
        "origins": {role: preservation["origins"][role] for role in local},
        "checked_paths": paths,
        "unmodeled_checked_paths": sorted(set(paths) - set(physical)),
        "read_basis": "source_declared_file_hash_read",
        "observed_read_receipt": False,
        "semantic_content_admission": False,
        "steps": {_step_id("pulse", 36): {"inputs": sorted(local), "outputs": []}},
    }


def _install_pre_attestation_postcondition_projection(
    states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any],
) -> None:
    """Replace only P36's selected readers; retain all original content duties."""
    by_role = {row["state_id"].removeprefix("state:step5c:"): row for row in states}
    for role, locator in facts["locators"].items():
        _require(role in by_role and by_role[role]["path_or_uri"] == locator,
                 "pre_attest_postcondition_input_locator", role)
        _require(by_role[role]["producer_occurrence_id"] == facts["origins"][role],
                 "pre_attest_postcondition_input_origin", role)
    step = steps[("pulse", 36)]
    oid = _step_id("pulse", 36)
    _require(step["occurrence_id"] == oid and step["output_state_ids"] == [],
             "pre_attest_postcondition_not_a_writer")
    step["input_state_ids"] = sorted("state:step5c:" + role for role in facts["steps"][oid]["inputs"])
    for row in states:
        readers = set(row["required_consumer_occurrence_ids"]) - {oid}
        if row["state_id"] in step["input_state_ids"]:
            readers.add(oid)
        row["required_consumer_occurrence_ids"] = sorted(readers)


# R26 hashes final physical files and separately checks two directory entries.
# Neither operation admits content or witnesses an original runtime read.
def _final_artifact_postcondition_source_projection(
    workflow: dict[str, Any], sources: dict[str, GitObject],
) -> dict[str, Any]:
    source = sources.get(SUBJECT_WORKFLOW_PATH)
    _require(source is not None and source.path == SUBJECT_WORKFLOW_PATH,
             "final_postcondition_source_missing")
    _require(_sha1_git_blob(source.data) == EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1,
             "final_postcondition_source_drift")
    _require(workflow == _parse_yaml_document(source.data, label=SUBJECT_WORKFLOW_PATH),
             "final_postcondition_workflow_drift")
    rows = workflow["jobs"][_RECORDED_JOB]["steps"]
    reader = rows[25]
    _require(reader["name"] == "Release-grade final artifact postconditions"
             and reader["shell"] == "bash" and "if" not in reader,
             "final_postcondition_step_profile")
    match = re.fullmatch(
        r'set -euo pipefail\n\nREQUIRED_FILES=\(\n(?P<paths>(?:  "[^"\n]+"\n)+)\)\n\n'
        r'for artifact in "\$\{REQUIRED_FILES\[@\]\}"; do\n'
        r'  if \[\[ ! -f "\$\{artifact\}" \|\| -L "\$\{artifact\}" \|\| ! -s "\$\{artifact\}" \]\]; then\n'
        r'    echo "::error::final release-grade artifact is missing, empty, or symlinked: \$\{artifact\}"\n'
        r'    exit 1\n  fi\n\n  sha256sum "\$\{artifact\}"\ndone\n\n'
        r'if \[\[ ! -d "(?P<candidates>[^"\n]+)" \|\| -L "(?P=candidates)" \]\]; then\n'
        r'  echo "::error::recorded release candidate directory is missing or symlinked"\n'
        r'  exit 1\nfi\n\n'
        r'if \[\[ ! -d "(?P<audit>[^"\n]+)" \|\| -L "(?P=audit)" \]\]; then\n'
        r'  echo "::error::release authority audit bundle is missing or symlinked"\n'
        r'  exit 1\nfi\n\n'
        r'echo "OK: final release-grade artifact postconditions satisfied"\n',
        reader["run"],
    )
    _require(match is not None, "final_postcondition_source_form")
    paths = [_mapping_path(shlex.split(line)[0]) for line in match.group("paths").splitlines()]
    _require(len(paths) == len(set(paths)) == 25, "final_postcondition_file_extent")

    # Reuse the source-derived families, not the supplied or reconstructed state
    # table. Exact locator matching keeps final and pre-mutation versions apart.
    ledger = _ledger_source_projection(workflow)
    recorded = _recorded_source_projection(workflow, sources)
    preserved = _preattest_preservation_source_projection(workflow, sources)
    external = _llamaguard_preservation_source_projection(workflow, sources)
    binding = _provenance_source_projection(workflow, sources)
    catalog: dict[str, str] = {}
    for family in (ledger["locators"], recorded["locators"], preserved["locators"],
                   external["locators"], {_PROVENANCE_ROLE: binding["locator"]}):
        for role, locator in family.items():
            _require(role not in catalog or catalog[role] == locator,
                     "final_postcondition_source_locator_conflict", role)
            catalog[role] = locator
    selected = {role: locator for role, locator in catalog.items() if locator in paths}
    _require(len(selected) == len(set(selected.values())) == 21,
             "final_postcondition_selected_extent")
    origins: dict[str, str] = {}
    for equations in (ledger["equations"], recorded["steps"]):
        for oid, equation in equations.items():
            for role in equation["outputs"]:
                if role in selected:
                    _require(role not in origins, "final_postcondition_source_origin_conflict", role)
                    origins[role] = oid
    for family in (preserved["origins"], external["origins"],
                   {_PROVENANCE_ROLE: binding["producer"]}):
        for role, oid in family.items():
            if role in selected:
                _require(role not in origins or origins[role] == oid,
                         "final_postcondition_source_origin_conflict", role)
                origins[role] = oid
    exporter = [i for i, step in enumerate(rows, 1)
                if step.get("name") == "Export final release-grade JUnit and SARIF"]
    _require(exporter == [23], "final_postcondition_exporter_selector")
    for role in ("release-grade-junit", "release-grade-sarif"):
        origins[role] = _step_id(_RECORDED_JOB, exporter[0])
    _require(set(origins) == set(selected), "final_postcondition_origin_extent")

    directories = [_mapping_path(match.group(name)) for name in ("candidates", "audit")]
    expected_directories = [recorded["locators"]["recorded-release-candidate-envelopes"].rstrip("/"),
                            _mapping_assignment(rows[21], "BUNDLE")]
    _require(directories == expected_directories and len(set(directories)) == 2
             and not set(directories) & set(paths), "final_postcondition_directory_extent")
    published = [(_mapping_path(line[:-3]) + "/**" if line.endswith("/**") else _mapping_path(line))
                 for line in rows[32]["with"]["path"].splitlines()]
    _require(len(published) == len(set(published)) == 27 and set(paths) <= set(published),
             "final_postcondition_publication_correspondence")
    publication_only = sorted(set(published) - set(paths))
    _require(publication_only == sorted([directories[0] + "/**",
             preserved["locators"]["self-contained-evidence-floor"]]),
             "final_postcondition_publication_only_extent")
    return {
        "locators": selected, "origins": origins, "checked_paths": paths,
        "unmodeled_checked_paths": sorted(set(paths) - set(selected.values())),
        "metadata_only_directory_checks": directories,
        "publication_only_selectors": publication_only,
        "read_basis": "source_declared_file_hash_read",
        "observed_read_receipt": False, "semantic_content_admission": False,
        "directory_content_read": False,
        "steps": {_step_id(_RECORDED_JOB, 26): {"inputs": sorted(selected), "outputs": []}},
    }


def _install_final_artifact_postcondition_projection(
    states: list[dict[str, Any]], steps: dict[tuple[str, int], dict[str, Any]], facts: dict[str, Any],
) -> None:
    """Bind only R26 file reads. Directory metadata is not a content input."""
    index = {row["state_id"].removeprefix("state:step5c:"): row for row in states}
    for role, locator in facts["locators"].items():
        _require(role in index and index[role]["path_or_uri"] == locator,
                 "final_postcondition_input_locator", role)
        _require(index[role]["producer_occurrence_id"] == facts["origins"][role],
                 "final_postcondition_input_origin", role)
    oid = _step_id(_RECORDED_JOB, 26)
    step = steps[(_RECORDED_JOB, 26)]
    _require(step["occurrence_id"] == oid and step["output_state_ids"] == [],
             "final_postcondition_not_a_writer")
    step["input_state_ids"] = sorted("state:step5c:" + role for role in facts["steps"][oid]["inputs"])
    for row in states:
        readers = set(row["required_consumer_occurrence_ids"]) - {oid}
        if row["state_id"] in step["input_state_ids"]:
            readers.add(oid)
        row["required_consumer_occurrence_ids"] = sorted(readers)


def _build_states(
    step_by_key: dict[tuple[str, int], dict[str, Any]],
    case_ids: tuple[str, ...],
    source_workflow: dict[str, Any],
    source_by_path: dict[str, GitObject],
) -> list[dict[str, Any]]:
    source_projection = _ledger_source_projection(source_workflow)
    recorded_projection = _recorded_source_projection(source_workflow, source_by_path)
    package_projection = _package_source_projection(source_workflow, source_by_path)
    argument_projection = _required_arguments_source_projection(source_workflow, source_by_path)
    bundle_projection = _bundle_source_projection(source_workflow, source_by_path)
    binding_projection = _provenance_source_projection(source_workflow, source_by_path)
    baseline_floor_projection = _baseline_floor_source_projection(source_workflow, source_by_path)
    preservation_projection = _preattest_preservation_source_projection(source_workflow, source_by_path)
    llamaguard_preservation = _llamaguard_preservation_source_projection(source_workflow, source_by_path)
    llamaguard_attestation = _llamaguard_attestation_source_projection(source_workflow, source_by_path)
    llamaguard_production = _llamaguard_production_source_projection(source_workflow, source_by_path)
    pre_attestation_postcondition = _pre_attestation_postcondition_source_projection(source_workflow, source_by_path)
    final_artifact_postcondition = _final_artifact_postcondition_source_projection(source_workflow, source_by_path)
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
        consumers=[st("attest_llamaguard_current_run_summary", 6), st("attest_llamaguard_current_run_summary", 7), st("release_grade_recorded_path", 8)],
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
        consumers=[st("pulse", 12), st("pulse", 13), st("release_grade_recorded_path", 4)],
        authority=True,
    )
    status_baseline = add(
        "status-baseline",
        "status",
        "pre_augmentation_status",
        "PULSE_safe_pack_v0/artifacts/status_baseline.json",
        producer=st("pulse", 14),
        consumers=[st("release_grade_recorded_path", 4)],
        authority=True,
    )
    evidence_floor = add(
        "self-contained-evidence-floor",
        "release_evidence",
        "self_contained_pulse_evidence_floor",
        "PULSE_safe_pack_v0/artifacts/self_contained_pulse_evidence_floor_v0.json",
        producer=st("pulse", 18),
        consumers=[st("release_grade_recorded_path", 4)],
        authority=True,
    )
    raw_evidence = add(
        "llamaguard-raw-evidence",
        "release_evidence",
        "llamaguard_raw_evidence",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_raw.jsonl",
        producer=st("pulse", 22),
        consumers=[st("pulse", 23)],
        authority=True,
    )
    evaluator_manifest = add(
        "llamaguard-evaluator-manifest",
        "manifest",
        "llamaguard_evaluator_manifest",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_evaluator_manifest_v0.json",
        producer=st("pulse", 22),
        consumers=[st("pulse", 23)],
        authority=True,
    )
    summary = add(
        "llamaguard-summary",
        "release_evidence",
        "canonical_llamaguard_summary",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.json",
        producer=st("pulse", 23),
        consumers=[st("pulse", 35), st("attest_llamaguard_current_run_summary", 5)],
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
        consumers=[st("attest_llamaguard_current_run_summary", 6), st("attest_llamaguard_current_run_summary", 7)],
        authority=True,
    )
    attestation_envelope = add(
        "llamaguard-attestation-envelope",
        "attestation",
        "llamaguard_external_summary_envelope",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.envelope.json",
        producer=st("attest_llamaguard_current_run_summary", 6),
        consumers=[st("attest_llamaguard_current_run_summary", 7)],
        authority=True,
    )
    attestation_verifier = add(
        "llamaguard-attestation-verifier",
        "verifier_report",
        "llamaguard_attestation_verifier",
        "PULSE_safe_pack_v0/artifacts/external/llamaguard_attestation_verifier_v1.json",
        producer=st("attest_llamaguard_current_run_summary", 7),
        consumers=[st("release_grade_recorded_path", 8)],
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
        consumers=[st("release_grade_recorded_path", 23)],
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
        consumers=[st("release_grade_recorded_path", 30)],
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
        consumers=[st("release_grade_recorded_path", 27)],
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
        binding_projection["locator"],
        producer=binding_projection["producer"],
        consumers=binding_projection["consumers"],
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
            ("release_grade_recorded_path", 8, signer),
        ],
        outputs=[
            ("pulse", 11, required_gate),
            ("pulse", 22, raw_evidence),
            ("pulse", 22, evaluator_manifest),
            ("pulse", 23, summary),
            ("pulse", 37, preattestation),
            ("attest_llamaguard_current_run_summary", 5, attestation_bundle),
            ("attest_llamaguard_current_run_summary", 6, attestation_envelope),
            ("attest_llamaguard_current_run_summary", 7, attestation_verifier),
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

    _install_ledger_source_projection(states, step_by_key, source_projection)
    _install_recorded_source_projection(states, step_by_key, recorded_projection)

    _install_package_source_projection(states, step_by_key, package_projection)

    _install_bundle_source_projection(states, step_by_key, bundle_projection)
    _install_provenance_source_projection(states, step_by_key, binding_projection)
    _install_baseline_floor_projection(states, step_by_key, baseline_floor_projection)
    _install_preattest_preservation_projection(states, step_by_key, preservation_projection)
    _install_llamaguard_preservation_projection(states, step_by_key, llamaguard_preservation)
    _install_llamaguard_attestation_projection(states, step_by_key, llamaguard_attestation)
    _install_llamaguard_production_projection(states, step_by_key, llamaguard_production)
    _install_pre_attestation_postcondition_projection(states, step_by_key, pre_attestation_postcondition)
    _install_final_artifact_postcondition_projection(states, step_by_key, final_artifact_postcondition)

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


def build_plan(
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


def _diagnostic(error: PlanError, *, exit_code: int) -> bytes:
    value = {
        "tool": TOOL_ID,
        "version": TOOL_VERSION,
        "ok": False,
        "error_code": error.code,
        "detail": error.detail,
        "authority_effect": "none",
        "same_run_release_authority_eligible": False,
        "active_gate_eligible": False,
        "exit_code": exit_code,
    }
    return _canonical_json_bytes(value)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the deterministic Step 5C whole-runtime prelaunch plan "
            "from one exact reviewed repository commit."
        )
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Exact Git repository root; checked-out HEAD must equal source_commit.",
    )
    parser.add_argument(
        "--source-commit",
        required=True,
        help="Reviewed lowercase 40-hex commit containing every plan source.",
    )
    parser.add_argument(
        "--record-status",
        choices=("example", "observed"),
        default="example",
        help="Example for permanent regressions; observed for the owner-run preparation.",
    )
    parser.add_argument(
        "--plan-id",
        help="Optional deterministic step5c-plan:* identifier; defaults to source commit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        plan = build_plan(
            repository_root=Path(args.repository_root),
            source_commit=str(args.source_commit),
            record_status=str(args.record_status),
            plan_id=str(args.plan_id) if args.plan_id is not None else None,
        )
        sys.stdout.buffer.write(_canonical_json_bytes(plan))
        return 0
    except PlanError as exc:
        sys.stderr.buffer.write(_diagnostic(exc, exit_code=1))
        return 1
    except Exception as exc:  # fail closed without exposing ambient values
        wrapped = PlanError("unexpected_plan_builder_failure", type(exc).__name__)
        sys.stderr.buffer.write(_diagnostic(wrapped, exit_code=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
