```python
#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pytest


ROOT = Path(__file__).resolve().parents[1]

ARCHIVE = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
PRESERVATION_DIR = ROOT / "preservation" / "pulse_ci_6066"
PRESERVATION_MANIFEST = PRESERVATION_DIR / "PRESERVATION_MANIFEST_v0.json"
PRESERVATION_README = PRESERVATION_DIR / "README.md"
PRESERVATION_SHA256SUMS = PRESERVATION_DIR / "SHA256SUMS"

REPORT_BUILDER = ROOT / "tools" / "build_pulsemech_compute_binding_report_v0.py"
REPORT_SCHEMA = ROOT / "schemas" / "pulsemech_compute_binding_report_v0.schema.json"
REPORT_VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_binding_report_v0.py"

COMPONENT_MANIFEST = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_fixed_source_6066_component_manifest_v0.json"
)
INTEGRATION_PLAN = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_fixed_source_6066_integration_plan_v0.json"
)
EXPECTATIONS = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_run_expectations_6066_v0.json"
)
PLAN_SCHEMA = ROOT / "schemas" / "pulsemech_integration_plan_v0.schema.json"

RELATION_BUILDER = (
    ROOT / "tools" / "build_pulsemech_compute_planned_observed_relation_v0.py"
)
RELATION_SCHEMA = (
    ROOT / "schemas" / "pulsemech_compute_planned_observed_relation_v0.schema.json"
)
RELATION_VALIDATOR = (
    ROOT / "tools" / "check_pulsemech_compute_planned_observed_relation_v0.py"
)
RUNTIME_PACKET_SCHEMA = (
    ROOT / "schemas" / "pulsemech_compute_runtime_observation_packet_v0.schema.json"
)
RUNTIME_PACKET_VALIDATOR = (
    ROOT / "tools" / "check_pulsemech_compute_runtime_observation_packet_v0.py"
)

MATERIALIZER = (
    ROOT
    / "tools"
    / "fold_pulsemech_compute_planned_observed_relation_into_status_v0.py"
)
POLICY = ROOT / "pulse_gate_policy_v0.yml"
REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"
POLICY_TO_REQUIRE_ARGS = ROOT / "tools" / "policy_to_require_args.py"
CHECK_GATES = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"

EXPECTED_ARCHIVE_SHA256 = (
    "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
)
EXPECTED_ARCHIVE_SIZE = 44660
EXPECTED_COMPONENT_MANIFEST_SHA256 = (
    "6c2fdf3b01388b82f19f20e3da4a2985b8802fa3a4c9957441969ca025af7b50"
)
EXPECTED_PLAN_SHA256 = (
    "28f254edd341f2d98aea1b8c297019fd664d4a97bb17347be902f93b8bb99127"
)
EXPECTED_EXPECTATIONS_SHA256 = (
    "a48cb7831c623afc53fbb082adb08edd56cdfee26a5ec399bc2c27dfb2b68736"
)
EXPECTED_CHECK_GATES_SHA256 = (
    "3a85ed757d5569e87364bd5de511dc1985c60d97e29ee3f782e08197fa4f5c8f"
)
EXPECTED_CHECK_GATES_SIZE = 2535
EXPECTED_OPERATION_SHA256 = (
    "8226cc8235ed3f7a4262326232cf5a374b2d57b90f4e48538b164d6a116a762e"
)
EXPECTED_SOURCE_COMMIT = "46b639706e23f80fe296a8893be18e2b5ab21f7e"
EXPECTED_HISTORICAL_POLICY_SHA256 = (
    "7160c37e5e04099c1b6960229d944076503380ae7d2a712c00da459a275d3c31"
)
EXPECTED_HISTORICAL_WORKFLOW_SHA256 = (
    "0d74133efdbe7c06672cc691d17ed5cdeec3c04df3e0ba465accfd187fd3c649"
)
EXPECTED_ARTIFACT_BINDING_PATH = (
    "PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json"
)
EXPECTED_ARTIFACT_BINDING_SHA256 = (
    "eeedae701541f34841d74d0ad12a37e4c6ebdf2f24260616c9cc356e241d87ff"
)
EXPECTED_SUBJECT_RUN_KEY = (
    "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|"
    "GITHUB_WORKFLOW=PULSE CI"
)
EXPECTED_ANALYSIS_RUN_KEY = (
    "OFFLINE_ANALYSIS=pulsemech-compute-fixed-source-candidate-chain-6066-v0"
)
EXPECTED_RELEASE_CANDIDATE = "main"

CANDIDATE_SET = "compute_planned_observed_relation_candidate"
CANDIDATE_GATES = [
    "compute_transition_path_complete",
    "compute_transition_authority_binding_ok",
    "compute_transition_unbound_mutation_absent",
]
EXPECTED_CANDIDATE_VALUES = {
    "compute_transition_path_complete": False,
    "compute_transition_authority_binding_ok": False,
    "compute_transition_unbound_mutation_absent": True,
}

RELATION_ID = "planned-observed:fixed-source-6066-candidate-boundary-v0"

PROTECTED_INPUTS = (
    ARCHIVE,
    PRESERVATION_MANIFEST,
    PRESERVATION_README,
    PRESERVATION_SHA256SUMS,
    REPORT_BUILDER,
    REPORT_SCHEMA,
    REPORT_VALIDATOR,
    COMPONENT_MANIFEST,
    INTEGRATION_PLAN,
    EXPECTATIONS,
    PLAN_SCHEMA,
    RELATION_BUILDER,
    RELATION_SCHEMA,
    RELATION_VALIDATOR,
    RUNTIME_PACKET_SCHEMA,
    RUNTIME_PACKET_VALIDATOR,
    MATERIALIZER,
    POLICY,
    REGISTRY,
    PULSE_WORKFLOW,
    POLICY_TO_REQUIRE_ARGS,
    CHECK_GATES,
)

OPERATION_DIGEST_FIELDS = (
    "action",
    "component_id",
    "reason",
    "source_path",
    "source_sha256",
    "source_size_bytes",
    "target_path",
    "target_state",
)


@dataclass(frozen=True)
class ChainBuild:
    workdir: Path
    report_path: Path
    report_text: str
    report: dict[str, Any]
    relation_path: Path
    relation_text: str
    relation: dict[str, Any]
    base_status_path: Path
    base_status_before: bytes
    materializer_report: dict[str, Any]
    folded_status_path: Path
    folded_status: dict[str, Any]
    required_gates: list[str]
    candidate_check: subprocess.CompletedProcess[str]
    protected_before: dict[str, tuple[int, str]]
    protected_after: dict[str, tuple[int, str]]


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise AssertionError(f"non-finite JSON value: {value}")


def strict_json_text(text: str, *, label: str) -> dict[str, Any]:
    value = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    assert isinstance(value, dict), f"{label}: expected JSON object"
    return value


def strict_json_file(path: Path, *, label: str) -> dict[str, Any]:
    return strict_json_text(path.read_text(encoding="utf-8"), label=label)


def render_json(value: dict[str, Any]) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(value), encoding="utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(encoded)


def canonical_operation_ref(operation: dict[str, Any]) -> dict[str, Any]:
    payload = {
        field: operation.get(field)
        for field in OPERATION_DIGEST_FIELDS
    }
    return {
        "action": operation.get("action"),
        "component_id": operation.get("component_id"),
        "operation_canonicalization": "json-sort-keys-utf8-no-whitespace",
        "operation_digest_scope": "pulsemech_integration_plan_operation_v0",
        "operation_sha256": canonical_digest(payload),
        "reason": operation.get("reason"),
        "source_path": operation.get("source_path"),
        "source_sha256": operation.get("source_sha256"),
        "source_size_bytes": operation.get("source_size_bytes"),
        "target_path": operation.get("target_path"),
        "target_state": operation.get("target_state"),
    }


def snapshot(paths: Iterable[Path]) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in paths:
        assert path.is_file(), path
        assert not path.is_symlink(), path
        result[str(path)] = (path.stat().st_size, sha256_file(path))
    return result


def run_command(
    command: list[str],
    *,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def run_report_builder(
    *,
    output: Path,
    archive: Path = ARCHIVE,
    manifest: Path = PRESERVATION_MANIFEST,
    readme: Path = PRESERVATION_README,
    sha256sums: Path = PRESERVATION_SHA256SUMS,
) -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            sys.executable,
            str(REPORT_BUILDER),
            "--archive",
            str(archive),
            "--manifest",
            str(manifest),
            "--readme",
            str(readme),
            "--sha256sums",
            str(sha256sums),
            "--schema",
            str(REPORT_SCHEMA),
            "--validator",
            str(REPORT_VALIDATOR),
            "--analysis-run-key",
            EXPECTED_ANALYSIS_RUN_KEY,
            "--output",
            str(output),
        ]
    )


def run_relation_builder(
    *,
    report: Path,
    output: Path,
    plan: Path = INTEGRATION_PLAN,
    expectations: Path = EXPECTATIONS,
) -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            sys.executable,
            str(RELATION_BUILDER),
            "--plan",
            str(plan),
            "--compute-report",
            str(report),
            "--expectations",
            str(expectations),
            "--relation-id",
            RELATION_ID,
            "--plan-schema",
            str(PLAN_SCHEMA),
            "--report-schema",
            str(REPORT_SCHEMA),
            "--runtime-packet-schema",
            str(RUNTIME_PACKET_SCHEMA),
            "--relation-schema",
            str(RELATION_SCHEMA),
            "--report-validator",
            str(REPORT_VALIDATOR),
            "--runtime-packet-validator",
            str(RUNTIME_PACKET_VALIDATOR),
            "--relation-validator",
            str(RELATION_VALIDATOR),
            "--subject-root",
            str(ROOT),
            "--output",
            str(output),
        ]
    )


def run_materializer(
    *,
    status: Path,
    relation: Path,
    output: Path,
) -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            sys.executable,
            str(MATERIALIZER),
            "--status",
            str(status),
            "--relation",
            str(relation),
            "--schema",
            str(RELATION_SCHEMA),
            "--validator",
            str(RELATION_VALIDATOR),
            "--output",
            str(output),
        ]
    )


def run_policy_to_require_args() -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            sys.executable,
            str(POLICY_TO_REQUIRE_ARGS),
            "--policy",
            str(POLICY),
            "--set",
            CANDIDATE_SET,
            "--format",
            "newline",
        ]
    )


def run_check_gates(
    *,
    status: Path,
    required_gates: list[str],
) -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            sys.executable,
            str(CHECK_GATES),
            "--status",
            str(status),
            "--require",
            *required_gates,
        ]
    )


def diagnostic_errors(result: subprocess.CompletedProcess[str]) -> list[str]:
    diagnostic = strict_json_text(result.stderr, label="tool diagnostic")
    errors = diagnostic.get("errors")
    assert isinstance(errors, list)
    return [str(error) for error in errors]


@pytest.fixture(scope="module")
def chain_build(tmp_path_factory: pytest.TempPathFactory) -> ChainBuild:
    workdir = tmp_path_factory.mktemp(
        "pulsemech-fixed-source-candidate-chain-6066-v0"
    )
    report_path = workdir / "generated_compute_binding_report_v0.json"
    relation_path = workdir / "generated_planned_observed_relation_v0.json"
    base_status_path = workdir / "base_candidate_status.json"
    folded_status_path = workdir / "folded_candidate_status.json"

    protected_before = snapshot(PROTECTED_INPUTS)

    report_result = run_report_builder(output=report_path)
    assert report_result.returncode == 0, report_result.stdout + report_result.stderr
    assert report_result.stderr == ""
    assert report_result.stdout.endswith("\n")
    assert report_path.read_text(encoding="utf-8") == report_result.stdout
    report = strict_json_text(report_result.stdout, label="generated report")

    relation_result = run_relation_builder(
        report=report_path,
        output=relation_path,
    )
    assert relation_result.returncode == 0, (
        relation_result.stdout + relation_result.stderr
    )
    assert relation_result.stderr == ""
    assert relation_result.stdout.endswith("\n")
    assert relation_path.read_text(encoding="utf-8") == relation_result.stdout
    relation = strict_json_text(
        relation_result.stdout,
        label="generated relation",
    )

    write_json(
        base_status_path,
        {
            "gates": {
                "existing_gate": True,
            },
            "run_id": "PULSE-CI-6066-fixed-source-candidate-boundary",
            "schema_version": "fixed_source_candidate_chain_test_v0",
        },
    )
    base_status_before = base_status_path.read_bytes()

    materializer_result = run_materializer(
        status=base_status_path,
        relation=relation_path,
        output=folded_status_path,
    )
    assert materializer_result.returncode == 0, (
        materializer_result.stdout + materializer_result.stderr
    )
    assert materializer_result.stderr == ""
    assert materializer_result.stdout.endswith("\n")
    materializer_report = strict_json_text(
        materializer_result.stdout,
        label="materializer report",
    )
    folded_status = strict_json_file(
        folded_status_path,
        label="folded status",
    )

    require_result = run_policy_to_require_args()
    assert require_result.returncode == 0, require_result.stdout + require_result.stderr
    assert require_result.stderr == ""
    required_gates = [
        line.strip()
        for line in require_result.stdout.splitlines()
        if line.strip()
    ]

    candidate_check = run_check_gates(
        status=folded_status_path,
        required_gates=required_gates,
    )

    protected_after = snapshot(PROTECTED_INPUTS)

    return ChainBuild(
        workdir=workdir,
        report_path=report_path,
        report_text=report_result.stdout,
        report=report,
        relation_path=relation_path,
        relation_text=relation_result.stdout,
        relation=relation,
        base_status_path=base_status_path,
        base_status_before=base_status_before,
        materializer_report=materializer_report,
        folded_status_path=folded_status_path,
        folded_status=folded_status,
        required_gates=required_gates,
        candidate_check=candidate_check,
        protected_before=protected_before,
        protected_after=protected_after,
    )


def test_fixed_source_chain_inputs_are_exactly_bound() -> None:
    assert ARCHIVE.stat().st_size == EXPECTED_ARCHIVE_SIZE
    assert sha256_file(ARCHIVE) == EXPECTED_ARCHIVE_SHA256
    assert sha256_file(COMPONENT_MANIFEST) == EXPECTED_COMPONENT_MANIFEST_SHA256
    assert sha256_file(INTEGRATION_PLAN) == EXPECTED_PLAN_SHA256
    assert sha256_file(EXPECTATIONS) == EXPECTED_EXPECTATIONS_SHA256
    assert CHECK_GATES.stat().st_size == EXPECTED_CHECK_GATES_SIZE
    assert sha256_file(CHECK_GATES) == EXPECTED_CHECK_GATES_SHA256

    manifest = strict_json_file(COMPONENT_MANIFEST, label="component manifest")
    plan = strict_json_file(INTEGRATION_PLAN, label="integration plan")
    expectations = strict_json_file(EXPECTATIONS, label="expectations")

    assert manifest["components"] == [
        {
            "id": "pulse_check_gates_v0",
            "kind": "file",
            "requires": [],
            "source_path": "PULSE_safe_pack_v0/tools/check_gates.py",
            "target_path": "PULSE_safe_pack_v0/tools/check_gates.py",
        }
    ]
    assert manifest["component_sets"][0]["root_components"] == [
        "pulse_check_gates_v0"
    ]
    assert manifest["component_sets"][0]["declared_gate_sets"] == [
        "required",
        "release_required",
    ]

    assert plan["source"] == {
        "component_manifest_path": (
            "pulsemech_compute_fixed_source_6066_component_manifest_v0.json"
        ),
        "component_manifest_sha256": EXPECTED_COMPONENT_MANIFEST_SHA256,
        "policy_path": "pulse_gate_policy_v0.yml",
        "policy_sha256": EXPECTED_HISTORICAL_POLICY_SHA256,
        "repository": "HKati/pulse-release-gates-0.1",
        "revision": EXPECTED_SOURCE_COMMIT,
    }
    assert plan["selection"]["resolved_components"] == ["pulse_check_gates_v0"]
    assert plan["summary"] == {
        "conflict": 0,
        "create": 0,
        "files_total": 1,
        "preserve": 1,
        "source_missing": 0,
        "unresolved": 0,
    }
    assert plan["apply_eligible"] is True
    assert plan["conflicts"] == []
    assert plan["unresolved"] == []

    operation = plan["operations"][0]
    canonical_ref = canonical_operation_ref(operation)
    assert canonical_ref["operation_sha256"] == EXPECTED_OPERATION_SHA256

    assert list(expectations) == [
        "expectation:execute-check-gates-consumed"
    ]
    expectation = expectations["expectation:execute-check-gates-consumed"]
    assert expectation["plan_operation_refs"] == [canonical_ref]
    assert expectation["expectation_scope"] == {
        "release_candidate_id": EXPECTED_RELEASE_CANDIDATE,
        "scope_kind": "subject_run",
        "subject_run_key": EXPECTED_SUBJECT_RUN_KEY,
        "subject_source_commit": EXPECTED_SOURCE_COMMIT,
    }
    assert expectation["expected_compute"] == {
        "downstream_consumption_required": True,
        "execution_required": True,
        "selector": {
            "command_sha256": None,
            "job_name": None,
            "node_type": "local_tool_execution",
            "step_name": None,
            "tool_id": "PULSE_safe_pack_v0/tools/check_gates.py",
            "workflow_name": "PULSE CI",
        },
    }
    assert expectation["expected_declared_role"] == "transition"
    assert expectation["expected_mutation_authority"] == "release_decision"
    assert expectation["expected_source_identity"] == {
        "action_commit_sha": None,
        "action_ref": None,
        "action_repository": None,
        "container_image_digest": None,
        "identity_status": "exact",
        "source_kind": "repository_file",
        "source_path_or_uri": "PULSE_safe_pack_v0/tools/check_gates.py",
        "source_revision": EXPECTED_SOURCE_COMMIT,
        "source_sha256": EXPECTED_CHECK_GATES_SHA256,
    }


    basis_by_id = {
        basis["basis_id"]: basis
        for basis in expectation["basis_records"]
    }
    assert set(basis_by_id) == {
        "basis:plan-check-gates-v0",
        "basis:recorded-artifact-binding-consumption",
        "basis:workflow-check-gates-transition",
    }
    assert basis_by_id["basis:plan-check-gates-v0"] == {
        "basis_id": "basis:plan-check-gates-v0",
        "basis_kind": "integration_plan_operation",
        "evidence_refs": [
            "plan-operation:pulse_check_gates_v0",
            f"sha256:{EXPECTED_OPERATION_SHA256}",
        ],
        "source_path_or_uri": (
            "examples/compute/"
            "pulsemech_compute_fixed_source_6066_integration_plan_v0.json"
            f"#operation/{EXPECTED_OPERATION_SHA256}"
        ),
        "source_revision": None,
        "source_sha256": EXPECTED_OPERATION_SHA256,
        "subject_run_key": None,
        "supports": [
            "component_presence",
            "source_identity",
        ],
    }
    assert basis_by_id[
        "basis:workflow-check-gates-transition"
    ] == {
        "basis_id": "basis:workflow-check-gates-transition",
        "basis_kind": "workflow_execution_declaration",
        "evidence_refs": [
            "workflow-tool:PULSE_safe_pack_v0/tools/check_gates.py",
            "workflow:PULSE-CI",
        ],
        "source_path_or_uri": ".github/workflows/pulse_ci.yml",
        "source_revision": EXPECTED_SOURCE_COMMIT,
        "source_sha256": EXPECTED_HISTORICAL_WORKFLOW_SHA256,
        "subject_run_key": EXPECTED_SUBJECT_RUN_KEY,
        "supports": [
            "declared_role",
            "execution_expectation",
            "mutation_authority",
        ],
    }
    assert basis_by_id[
        "basis:recorded-artifact-binding-consumption"
    ] == {
        "basis_id": "basis:recorded-artifact-binding-consumption",
        "basis_kind": "recorded_manifest",
        "evidence_refs": [
            f"artifact:{EXPECTED_ARTIFACT_BINDING_PATH}",
            "binding:strict-check-gates-to-release-decision",
            f"sha256:{EXPECTED_ARTIFACT_BINDING_SHA256}",
        ],
        "source_path_or_uri": EXPECTED_ARTIFACT_BINDING_PATH,
        "source_revision": None,
        "source_sha256": EXPECTED_ARTIFACT_BINDING_SHA256,
        "subject_run_key": EXPECTED_SUBJECT_RUN_KEY,
        "supports": [
            "downstream_consumption_expectation",
        ],
    }
    assert expectation["evidence_refs"] == [
        f"artifact:{EXPECTED_ARTIFACT_BINDING_PATH}",
        "binding:strict-check-gates-to-release-decision",
        "component:pulse_check_gates_v0",
        "workflow-tool:PULSE_safe_pack_v0/tools/check_gates.py",
    ]


def test_generated_chain_preserves_the_artifact_observed_boundary(
    chain_build: ChainBuild,
) -> None:
    report = chain_build.report
    assert report["schema_version"] == "pulsemech_compute_binding_report_v0"
    assert report["report_type"] == "pulsemech_compute_binding_report"
    assert report["record_status"] == "observed"
    assert report["ok"] is True
    assert report["errors"] == []
    assert report["analysis_boundary"] == {
        "analysis_level": "artifact_observed",
        "analysis_run_key": EXPECTED_ANALYSIS_RUN_KEY,
        "observer_in_subject_totals": False,
        "subject_run_key": EXPECTED_SUBJECT_RUN_KEY,
    }
    assert report["subject"]["repository"] == "HKati/pulse-release-gates-0.1"
    assert report["subject"]["workflow_run_id"] == 29249887581
    assert report["subject"]["workflow_run_number"] == 6066
    assert report["subject"]["workflow_run_attempt"] == 1
    assert report["subject"]["source_commit"] == EXPECTED_SOURCE_COMMIT
    assert report["subject"]["release_candidate_id"] == EXPECTED_RELEASE_CANDIDATE
    assert report["subject"]["decision"] == "ALLOW"
    assert report["summary"] == {
        "advisory_bound_nodes": 0,
        "authority_binding_complete": False,
        "decision_closure_complete": False,
        "evidence_bound_nodes": 4,
        "observer_nodes": 1,
        "preservation_bound_nodes": 0,
        "resource_measurement_status": "none",
        "subject_compute_nodes": 18,
        "transition_bound_nodes": 2,
        "unbound_authoritative_mutation_count": 0,
        "unbound_nodes": 0,
        "unknown_nodes": 12,
    }

    relation = chain_build.relation
    assert relation["schema_version"] == (
        "pulsemech_compute_planned_observed_relation_v0"
    )
    assert relation["relation_type"] == (
        "pulsemech_compute_planned_observed_relation"
    )
    assert relation["record_status"] == "observed"
    assert relation["ok"] is True
    assert relation["errors"] == []
    assert relation["comparison_identity"] == {
        "canonicalization": "json-sort-keys-utf8-newline",
        "comparison_scope": "subject_run",
        "relation_record_id": RELATION_ID,
        "release_candidate_id": EXPECTED_RELEASE_CANDIDATE,
        "subject_repository": "HKati/pulse-release-gates-0.1",
        "subject_run_key": EXPECTED_SUBJECT_RUN_KEY,
        "subject_source_commit": EXPECTED_SOURCE_COMMIT,
    }
    assert relation["authority_boundary"] == {
        "activates_compute_gate": False,
        "changes_gate_policy": False,
        "changes_gate_semantics": False,
        "changes_release_authority": False,
        "creates_compute_budget": False,
        "creates_gate_result": False,
        "creates_release_decision": False,
        "mutates_subject_run": False,
        "relation_record_is_release_authority": False,
        "write_mode": "relation_only",
        "writes_target_repository": False,
    }

    assert len(relation["expectations"]) == 1
    assert len(relation["observations"]) == 19
    assert len(relation["relations"]) == 19

    expected_relation_records = [
        item
        for item in relation["relations"].values()
        if item.get("expectation_id")
        == "expectation:execute-check-gates-consumed"
    ]
    assert len(expected_relation_records) == 1
    checked_relation = expected_relation_records[0]
    assert checked_relation["relation_status"] == "planned_and_observed"
    assert checked_relation["evaluation"] == {
        "authority_class": "match",
        "coverage": "complete",
        "decisive": True,
        "declared_role": "match",
        "downstream_consumption": "observed",
        "execution_identity": "match",
        "execution_observation": "observed",
        "run_binding": "match",
        "source_identity": "match",
    }
    assert len(checked_relation["observation_ids"]) == 1
    selected_observation = relation["observations"][
        checked_relation["observation_ids"][0]
    ]
    assert selected_observation["source_record_id"] == "compute:check-gates"
    assert selected_observation["source_record_kind"] == (
        "compute_binding_report"
    )
    assert selected_observation["binding_status"] == "complete"
    assert selected_observation["binding_class"] == "transition_bound"
    assert selected_observation["declared_role"] == "transition"
    assert selected_observation["mutation_authority"] == "release_decision"
    assert selected_observation["source_identity"]["source_sha256"] == (
        EXPECTED_CHECK_GATES_SHA256
    )
    assert selected_observation["downstream_consumption"]["status"] == (
        "observed"
    )

    relation_status_counts = Counter(
        item["relation_status"]
        for item in relation["relations"].values()
    )
    assert relation_status_counts == Counter(
        {
            "planned_and_observed": 1,
            "observed_but_not_planned": 5,
            "unresolved_due_to_coverage": 13,
        }
    )

    assert relation["coverage"] == {
        "authority_coverage_status": "complete",
        "comparison_status": "unknown",
        "declared_role_coverage_status": "complete",
        "downstream_consumption_coverage_status": "complete",
        "execution_coverage_status": "partial",
        "expectations_classified": 1,
        "expectations_total": 1,
        "identity_coverage_status": "unknown",
        "missing_plan_operation_refs": [],
        "observations_classified": 19,
        "observations_total": 19,
        "plan_operations_referenced": 1,
        "plan_operations_total": 1,
        "relations_total": 19,
        "runtime_observation_status": "none",
        "unclassified_expectation_ids": [],
        "unclassified_observation_ids": [],
        "unresolved_reasons": [
            "artifact_coverage_partial",
            "source_identity_unavailable",
        ],
    }

    summary = relation["summary"]
    assert summary["authority_integrity_candidate_count"] == 0
    assert summary["comparison_complete"] is False
    assert summary["decisive_relations"] == 6
    assert summary["expectations"] == 1
    assert summary["observations"] == 19
    assert summary["plan_operations"] == 1
    assert summary["relations"] == 19
    assert summary["unresolved_relations"] == 13
    assert summary["planned_execution_and_consumption_expected"] == 1
    assert summary["planned_execution_expected"] == 0
    assert summary["planned_presence_only"] == 0
    assert summary["planned_and_observed"] == 1
    assert summary["observed_but_not_planned"] == 5
    assert summary["unresolved_due_to_coverage"] == 13
    for status in (
        "planned_but_not_observed",
        "execution_identity_mismatch",
        "source_digest_mismatch",
        "run_binding_mismatch",
        "declared_role_mismatch",
        "authority_class_mismatch",
        "downstream_consumption_missing",
        "ambiguous_observation_match",
    ):
        assert summary[status] == 0

    finding_counts = Counter(
        item["finding_type"]
        for item in relation["findings"].values()
    )
    assert finding_counts == Counter(
        {
            "comparison_coverage_partial": 13,
            "observed_execution_not_planned": 5,
        }
    )
    assert all(
        item["severity"] != "authority_integrity_candidate"
        for item in relation["findings"].values()
    )


def test_materialization_succeeds_while_candidate_check_fails_closed(
    chain_build: ChainBuild,
) -> None:
    materializer_report = chain_build.materializer_report
    assert materializer_report["tool"] == (
        "fold_pulsemech_compute_planned_observed_relation_into_status_v0"
    )
    assert materializer_report["ok"] is True
    assert materializer_report["relation_validated"] is True
    assert materializer_report["output_status_written"] is True
    assert materializer_report["record_status"] == "observed"
    assert materializer_report["relation_record_id"] == RELATION_ID
    assert materializer_report["candidate_gate_set"] == CANDIDATE_SET
    assert materializer_report["candidate_gates"] == (
        EXPECTED_CANDIDATE_VALUES
    )
    assert materializer_report["candidate_all_true"] is False
    assert materializer_report["folded_gates"] == CANDIDATE_GATES
    assert materializer_report["errors"] == []

    assert chain_build.base_status_path.read_bytes() == (
        chain_build.base_status_before
    )
    assert chain_build.folded_status["gates"] == {
        "existing_gate": True,
        **EXPECTED_CANDIDATE_VALUES,
    }

    assert chain_build.required_gates == CANDIDATE_GATES
    assert chain_build.candidate_check.returncode == 1
    assert chain_build.candidate_check.stderr == ""
    assert "[X] FAIL gates:" in chain_build.candidate_check.stdout
    assert "compute_transition_path_complete" in (
        chain_build.candidate_check.stdout
    )
    assert "compute_transition_authority_binding_ok" in (
        chain_build.candidate_check.stdout
    )
    assert "compute_transition_unbound_mutation_absent" not in (
        chain_build.candidate_check.stdout.splitlines()[0]
    )


def test_connected_chain_is_deterministic_and_read_only(
    chain_build: ChainBuild,
    tmp_path: Path,
) -> None:
    assert chain_build.protected_before == chain_build.protected_after

    second_relation_path = tmp_path / "second_generated_relation.json"
    second_relation = run_relation_builder(
        report=chain_build.report_path,
        output=second_relation_path,
    )
    assert second_relation.returncode == 0, (
        second_relation.stdout + second_relation.stderr
    )
    assert second_relation.stderr == ""
    assert second_relation.stdout == chain_build.relation_text
    assert second_relation_path.read_text(encoding="utf-8") == (
        chain_build.relation_text
    )

    second_folded_path = tmp_path / "second_folded_candidate_status.json"
    second_materializer = run_materializer(
        status=chain_build.base_status_path,
        relation=chain_build.relation_path,
        output=second_folded_path,
    )
    assert second_materializer.returncode == 0, (
        second_materializer.stdout + second_materializer.stderr
    )
    assert second_materializer.stderr == ""
    assert second_folded_path.read_bytes() == (
        chain_build.folded_status_path.read_bytes()
    )
    second_report = strict_json_text(
        second_materializer.stdout,
        label="second materializer report",
    )
    assert second_report["candidate_gates"] == EXPECTED_CANDIDATE_VALUES
    assert second_report["output_status_sha256"] == (
        chain_build.materializer_report["output_status_sha256"]
    )

    assert snapshot(PROTECTED_INPUTS) == chain_build.protected_before


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        (
            "subject_run_key",
            "GITHUB_RUN_ID=1|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
        ),
        ("subject_source_commit", "0" * 40),
        ("release_candidate_id", "other-candidate"),
    ],
)
def test_subject_binding_mismatch_is_rejected(
    chain_build: ChainBuild,
    tmp_path: Path,
    field: str,
    replacement: str,
) -> None:
    expectations = strict_json_file(EXPECTATIONS, label="expectations")
    record = expectations["expectation:execute-check-gates-consumed"]
    record["expectation_scope"][field] = replacement

    bad_expectations = tmp_path / f"bad_expectations_{field}.json"
    output = tmp_path / f"relation_{field}.json"
    write_json(bad_expectations, expectations)

    result = run_relation_builder(
        report=chain_build.report_path,
        expectations=bad_expectations,
        output=output,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert not output.exists()
    assert any(
        "expectation_subject_binding_mismatch" in error
        for error in diagnostic_errors(result)
    )


def test_plan_operation_identity_mismatch_is_rejected(
    chain_build: ChainBuild,
    tmp_path: Path,
) -> None:
    expectations = strict_json_file(EXPECTATIONS, label="expectations")
    operation = expectations[
        "expectation:execute-check-gates-consumed"
    ]["plan_operation_refs"][0]
    operation["source_size_bytes"] += 1

    bad_expectations = tmp_path / "bad_operation_expectations.json"
    output = tmp_path / "relation_bad_operation.json"
    write_json(bad_expectations, expectations)

    result = run_relation_builder(
        report=chain_build.report_path,
        expectations=bad_expectations,
        output=output,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert not output.exists()
    assert any(
        "expectation_operation_identity_mismatch" in error
        for error in diagnostic_errors(result)
    )


def test_corrupted_preservation_archive_stops_the_chain(
    tmp_path: Path,
) -> None:
    subject_root = tmp_path / "corrupted_subject"
    preservation_dir = subject_root / "preservation" / "pulse_ci_6066"
    preservation_dir.mkdir(parents=True)

    archive = subject_root / ARCHIVE.name
    manifest = preservation_dir / PRESERVATION_MANIFEST.name
    readme = preservation_dir / PRESERVATION_README.name
    sha256sums = preservation_dir / PRESERVATION_SHA256SUMS.name

    shutil.copy2(ARCHIVE, archive)
    shutil.copy2(PRESERVATION_MANIFEST, manifest)
    shutil.copy2(PRESERVATION_README, readme)
    shutil.copy2(PRESERVATION_SHA256SUMS, sha256sums)

    payload = bytearray(archive.read_bytes())
    payload[len(payload) // 2] ^= 0x01
    archive.write_bytes(payload)
    assert archive.stat().st_size == EXPECTED_ARCHIVE_SIZE

    output = tmp_path / "corrupted_report.json"
    result = run_report_builder(
        output=output,
        archive=archive,
        manifest=manifest,
        readme=readme,
        sha256sums=sha256sums,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert not output.exists()
    assert any(
        "preservation_archive_sha256_mismatch" in error
        for error in diagnostic_errors(result)
    )


def test_preserved_subject_overwrite_is_refused() -> None:
    before = (ARCHIVE.stat().st_size, sha256_file(ARCHIVE))
    result = run_report_builder(output=ARCHIVE)

    assert result.returncode == 1
    assert result.stdout == ""
    assert any(
        "refusing_to_overwrite_input" in error
        for error in diagnostic_errors(result)
    )
    assert (ARCHIVE.stat().st_size, sha256_file(ARCHIVE)) == before


def test_invalid_generated_relation_writes_no_candidate_status(
    chain_build: ChainBuild,
    tmp_path: Path,
) -> None:
    invalid_relation = copy.deepcopy(chain_build.relation)
    invalid_relation["ok"] = False
    invalid_relation["errors"] = ["synthetic_generated_relation_error"]

    invalid_relation_path = tmp_path / "invalid_generated_relation.json"
    output = tmp_path / "invalid_relation_folded_status.json"
    write_json(invalid_relation_path, invalid_relation)

    base_before = chain_build.base_status_path.read_bytes()
    result = run_materializer(
        status=chain_build.base_status_path,
        relation=invalid_relation_path,
        output=output,
    )

    assert result.returncode == 1
    assert result.stderr == ""
    report = strict_json_text(
        result.stdout,
        label="invalid relation materializer report",
    )
    assert report["ok"] is False
    assert report["output_status_written"] is False
    assert not output.exists()
    assert chain_build.base_status_path.read_bytes() == base_before
    assert any(
        "relation_strict_validation_failed" in error
        or "relation_not_ok" in error
        for error in report["errors"]
    )


def test_missing_candidate_gate_returns_exit_two(
    chain_build: ChainBuild,
    tmp_path: Path,
) -> None:
    missing = copy.deepcopy(chain_build.folded_status)
    missing_gate = "compute_transition_unbound_mutation_absent"
    del missing["gates"][missing_gate]

    missing_path = tmp_path / "missing_candidate_gate_status.json"
    write_json(missing_path, missing)

    result = run_check_gates(
        status=missing_path,
        required_gates=chain_build.required_gates,
    )
    assert result.returncode == 2
    assert result.stderr == ""
    assert "[X] Missing required gates:" in result.stdout
    assert missing_gate in result.stdout


def check_pulsemech_compute_fixed_source_candidate_chain_v0() -> None:
    raise SystemExit(pytest.main([__file__, "-q"]))


if __name__ == "__main__":
    check_pulsemech_compute_fixed_source_candidate_chain_v0()
```
