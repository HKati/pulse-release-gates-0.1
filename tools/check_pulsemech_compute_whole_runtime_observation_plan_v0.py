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
    }
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


def _build_states(
    step_by_key: dict[tuple[str, int], dict[str, Any]],
    case_ids: tuple[str, ...],
) -> list[dict[str, Any]]:
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
        consumers=[st("pulse", 11), st("pulse", 50), st("pulse", 51), st("release_grade_recorded_path", 9), st("release_grade_recorded_path", 12), st("release_grade_recorded_path", 17), st("release_grade_recorded_path", 21)],
        authority=True,
    )
    registry = add(
        "gate-registry",
        "gate_registry",
        "gate_registry",
        REGISTRY_PATH,
        producer=None,
        consumers=[st("pulse", 11), st("pulse", 50), st("pulse", 51), st("release_grade_recorded_path", 9), st("release_grade_recorded_path", 12), st("release_grade_recorded_path", 17), st("release_grade_recorded_path", 21)],
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
        "artifact://release-grade-pre-attestation-pulse-artifacts",
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
        "PULSE_safe_pack_v0/artifacts/recorded_release_candidate_index_v0.json",
        producer=st("release_grade_recorded_path", 6),
        consumers=[st("release_grade_recorded_path", 7), st("release_grade_recorded_path", 8), st("release_grade_recorded_path", 9)],
        authority=True,
    )
    evidence_manifest = add(
        "release-evidence-input-manifest",
        "manifest",
        "release_evidence_input_manifest",
        "PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json",
        producer=st("release_grade_recorded_path", 7),
        consumers=[st("release_grade_recorded_path", 8)],
        authority=True,
    )
    evidence_verifier = add(
        "recorded-release-evidence-verifier",
        "verifier_report",
        "recorded_release_evidence_verifier",
        "PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json",
        producer=st("release_grade_recorded_path", 8),
        consumers=[st("release_grade_recorded_path", 9)],
        authority=True,
    )
    materialized = add(
        "materialized-release-required-gate-set",
        "candidate_state",
        "materialized_release_required_gate_set",
        "status://gates/release_required",
        producer=st("release_grade_recorded_path", 9),
        consumers=[st("release_grade_recorded_path", 10), st("release_grade_recorded_path", 11), st("release_grade_recorded_path", 12), st("release_grade_recorded_path", 15), st("release_grade_recorded_path", 17), st("release_grade_recorded_path", 21)],
        authority=True,
        mutation="materialized_gate_set",
    )
    final_status = add(
        "final-status",
        "status",
        "final_release_grade_status",
        "PULSE_safe_pack_v0/artifacts/status.json",
        producer=st("release_grade_recorded_path", 9),
        consumers=[st("release_grade_recorded_path", 10), st("release_grade_recorded_path", 11), st("release_grade_recorded_path", 12), st("release_grade_recorded_path", 13), st("release_grade_recorded_path", 14), st("release_grade_recorded_path", 15), st("release_grade_recorded_path", 17), st("release_grade_recorded_path", 20), st("release_grade_recorded_path", 21), st("release_grade_recorded_path", 23)],
        authority=True,
        mutation="final_status",
    )
    ledger_pre = add(
        "quality-ledger-pre-authority",
        "quality_ledger",
        "release_grade_quality_ledger_before_authority_insertion",
        "PULSE_safe_pack_v0/artifacts/report_card.html#pre-authority-insertion",
        producer=st("release_grade_recorded_path", 13),
        consumers=[st("release_grade_recorded_path", 18)],
        authority=True,
    )
    status_summary = add(
        "final-status-summary",
        "report",
        "final_release_grade_status_summary",
        "PULSE_safe_pack_v0/artifacts/status_summary.json",
        producer=st("release_grade_recorded_path", 14),
        consumers=[st("release_grade_recorded_path", 19)],
        authority=True,
    )
    decision = add(
        "release-decision",
        "release_decision",
        "final_release_decision",
        "PULSE_safe_pack_v0/artifacts/release_decision_v0.json",
        producer=st("release_grade_recorded_path", 15),
        consumers=[st("release_grade_recorded_path", 16), st("release_grade_recorded_path", 19), st("release_grade_recorded_path", 21), st("release_grade_recorded_path", 30)],
        authority=True,
        mutation="release_decision",
    )
    decision_ledger = add(
        "release-decision-ledger-section",
        "report",
        "release_decision_ledger_section",
        "PULSE_safe_pack_v0/artifacts/release_decision_ledger_section_v0.html",
        producer=st("release_grade_recorded_path", 16),
        consumers=[st("release_grade_recorded_path", 19)],
        authority=True,
    )
    authority_manifest = add(
        "release-authority-manifest",
        "release_authority",
        "final_release_authority_manifest",
        "PULSE_safe_pack_v0/artifacts/release_authority_v0.json",
        producer=st("release_grade_recorded_path", 17),
        consumers=[st("release_grade_recorded_path", 18), st("release_grade_recorded_path", 19), st("release_grade_recorded_path", 21), st("release_grade_recorded_path", 27)],
        authority=True,
    )
    ledger_final = add(
        "quality-ledger-final",
        "quality_ledger",
        "final_release_grade_quality_ledger",
        "PULSE_safe_pack_v0/artifacts/report_card.html",
        producer=st("release_grade_recorded_path", 18),
        consumers=[st("release_grade_recorded_path", 19), st("release_grade_recorded_path", 20), st("release_grade_recorded_path", 31)],
        authority=True,
    )
    decision_report = add(
        "release-decision-report",
        "report",
        "composed_release_decision_report",
        "PULSE_safe_pack_v0/artifacts/release_decision_report_v0.html",
        producer=st("release_grade_recorded_path", 19),
        consumers=[st("release_grade_recorded_path", 20), st("release_grade_recorded_path", 31)],
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
        "PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle/",
        producer=st("release_grade_recorded_path", 22),
        consumers=[st("release_grade_recorded_path", 28), st("assemble_release_grade_reference_package", 4)],
        authority=True,
    )
    junit = add(
        "release-grade-junit",
        "junit",
        "final_release_grade_junit",
        "reports/junit.xml",
        producer=st("release_grade_recorded_path", 23),
        consumers=[st("release_grade_recorded_path", 26), st("release_grade_recorded_path", 33)],
        authority=False,
    )
    sarif = add(
        "release-grade-sarif",
        "sarif",
        "final_release_grade_sarif",
        "reports/sarif.json",
        producer=st("release_grade_recorded_path", 23),
        consumers=[st("release_grade_recorded_path", 26), st("release_grade_recorded_path", 33)],
        authority=False,
    )
    advisory_bundle = add(
        "advisory-reference-bundle",
        "package",
        "advisory_release_grade_reference_bundle",
        "PULSE_safe_pack_v0/artifacts/release_grade_reference_bundle/",
        producer=st("release_grade_recorded_path", 25),
        consumers=[st("release_grade_recorded_path", 26), st("release_grade_recorded_path", 32), st("assemble_release_grade_reference_package", 4)],
        authority=False,
    )
    binding_attestation = add(
        "artifact-binding-attestation",
        "attestation",
        "final_release_grade_artifact_binding_attestation",
        "attestation://artifact_provenance_binding_v0.json",
        producer=st("attest_release_grade_artifact_binding", 2),
        consumers=[st("assemble_release_grade_reference_package", 4)],
        authority=True,
    )
    complete_package = add(
        "complete-release-grade-reference-package",
        "package",
        "complete_release_grade_reference_package",
        "artifact://complete-release-grade-reference-package-{workflow_run_id}-1",
        producer=st("assemble_release_grade_reference_package", 5),
        consumers=[st("assemble_release_grade_reference_package", 6), st("verify_release_grade_reference_package", 4)],
        authority=False,
    )
    package_completeness = add(
        "package-completeness-report",
        "verifier_report",
        "release_grade_package_completeness_report",
        "artifact://release-grade-package-completeness-{workflow_run_id}-1",
        producer=st("verify_release_grade_reference_package", 5),
        consumers=[st("verify_release_grade_reference_package", 6)],
        authority=False,
    )
    package_verification = add(
        "package-verification-report",
        "verifier_report",
        "release_grade_reference_package_verification_report",
        "artifact://release-grade-reference-package-verification-{workflow_run_id}-1",
        producer=st("verify_release_grade_reference_package", 7),
        consumers=[st("verify_release_grade_reference_package", 8)],
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
            ("release_grade_recorded_path", 8, candidate_index),
            ("release_grade_recorded_path", 8, evidence_manifest),
            ("release_grade_recorded_path", 8, signer),
            ("release_grade_recorded_path", 9, evidence_verifier),
            ("release_grade_recorded_path", 12, final_status),
            ("release_grade_recorded_path", 12, materialized),
            ("release_grade_recorded_path", 18, ledger_pre),
            ("release_grade_recorded_path", 19, status_summary),
            ("release_grade_recorded_path", 19, decision),
            ("release_grade_recorded_path", 19, decision_ledger),
            ("release_grade_recorded_path", 19, authority_manifest),
            ("release_grade_recorded_path", 20, ledger_final),
            ("release_grade_recorded_path", 20, decision_report),
            ("release_grade_recorded_path", 21, final_status),
            ("release_grade_recorded_path", 21, decision),
            ("release_grade_recorded_path", 21, authority_manifest),
            ("attest_release_grade_artifact_binding", 1, artifact_binding),
            ("assemble_release_grade_reference_package", 4, artifact_binding),
            ("assemble_release_grade_reference_package", 4, audit_bundle),
            ("assemble_release_grade_reference_package", 4, advisory_bundle),
            ("assemble_release_grade_reference_package", 4, binding_attestation),
            ("verify_release_grade_reference_package", 4, complete_package),
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
            ("release_grade_recorded_path", 6, candidate_index),
            ("release_grade_recorded_path", 7, evidence_manifest),
            ("release_grade_recorded_path", 8, evidence_verifier),
            ("release_grade_recorded_path", 9, materialized),
            ("release_grade_recorded_path", 9, final_status),
            ("release_grade_recorded_path", 13, ledger_pre),
            ("release_grade_recorded_path", 14, status_summary),
            ("release_grade_recorded_path", 15, decision),
            ("release_grade_recorded_path", 16, decision_ledger),
            ("release_grade_recorded_path", 17, authority_manifest),
            ("release_grade_recorded_path", 18, ledger_final),
            ("release_grade_recorded_path", 19, decision_report),
            ("release_grade_recorded_path", 21, artifact_binding),
            ("release_grade_recorded_path", 22, audit_bundle),
            ("release_grade_recorded_path", 23, junit),
            ("release_grade_recorded_path", 23, sarif),
            ("release_grade_recorded_path", 25, advisory_bundle),
            ("attest_release_grade_artifact_binding", 2, binding_attestation),
            ("assemble_release_grade_reference_package", 5, complete_package),
            ("verify_release_grade_reference_package", 5, package_completeness),
            ("verify_release_grade_reference_package", 7, package_verification),
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
    state_templates = _build_states(step_by_key, case_ids)

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
