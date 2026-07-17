#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]

TOOL = (
    ROOT
    / "tools"
    / "check_pulsemech_compute_planned_observed_relation_v0.py"
)
SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_compute_planned_observed_relation_v0.schema.json"
)
EXAMPLE = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_planned_observed_relation_example_v0.json"
)
GATE_POLICY = ROOT / "pulse_gate_policy_v0.yml"
GATE_REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"

EXPECTED_CHECKS = {
    "analysis_level_and_runtime_admission_ok",
    "basis_identifiers_unique_within_expectation",
    "canonical_json_key_ordering_ok",
    "canonical_json_newline_termination_ok",
    "comparison_complete_semantics_ok",
    "compute_report_subject_binding_ok",
    "coverage_counts_recompute",
    "coverage_status_semantics_ok",
    "deterministic_string_list_ordering_ok",
    "expectation_basis_run_bindings_ok",
    "expectation_relation_multiplicity_ok",
    "expectation_subject_scope_bindings_ok",
    "finding_fingerprints_unique",
    "finding_references_resolve",
    "identifier_keyed_record_maps_ok",
    "nested_record_ordering_ok",
    "observation_relation_multiplicity_ok",
    "observer_boundary_ok",
    "plan_operation_digests_recompute",
    "plan_operation_identity_consistent",
    "plan_target_subject_binding_ok",
    "record_map_ordering_ok",
    "record_ok_errors_semantics_ok",
    "relation_candidates_unique",
    "relation_evaluations_recompute",
    "relation_expectation_kind_compatibility_ok",
    "relation_references_resolve",
    "relation_type_ok",
    "runtime_packet_subject_bindings_ok",
    "schema_version_ok",
    "summary_counts_recompute",
    "unbound_authority_findings_present",
    "unbound_authority_flags_derived_ok",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


_BASE_RELATION = load_json(EXAMPLE)


def relation_record() -> dict[str, Any]:
    return copy.deepcopy(_BASE_RELATION)


def write_relation(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def import_tool_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pulsemech_planned_observed_relation_validator_v0_under_test",
        TOOL,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL_MODULE = import_tool_module()


def run_tool(
    *,
    relation_path: Path = EXAMPLE,
    schema_path: Path = SCHEMA,
    output: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(TOOL),
        "--schema",
        str(schema_path),
        "--relation",
        str(relation_path),
    ]
    if output is not None:
        command.extend(["--output", str(output)])

    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_json_text(text: str) -> dict[str, Any]:
    loaded = json.loads(text)
    assert isinstance(loaded, dict)
    return loaded


def assert_cli_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
    *,
    expected_returncode: int | None = None,
    stream: str = "stdout",
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    if expected_returncode is not None:
        assert result.returncode == expected_returncode
    assert "Traceback" not in result.stderr

    text = result.stdout if stream == "stdout" else result.stderr
    assert text, result.stdout + result.stderr
    diagnostic = parse_json_text(text)
    assert diagnostic["ok"] is False
    assert any(
        expected_fragment in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def diagnostic_for(
    value: dict[str, Any],
    tmp_path: Path,
    *,
    raw_text: str | None = None,
) -> tuple[dict[str, Any], int]:
    relation_path = tmp_path / "relation.json"
    if raw_text is None:
        write_relation(relation_path, value)
    else:
        relation_path.write_text(raw_text, encoding="utf-8")
    return TOOL_MODULE.build_diagnostic(
        schema_path=SCHEMA,
        relation_path=relation_path,
    )


def assert_semantic_failure(
    value: dict[str, Any],
    tmp_path: Path,
    check_name: str,
    *,
    raw_text: str | None = None,
) -> dict[str, Any]:
    diagnostic, exit_code = diagnostic_for(
        value,
        tmp_path,
        raw_text=raw_text,
    )

    assert exit_code == 1, diagnostic
    assert diagnostic["schema_valid"] is True, diagnostic
    assert diagnostic["checks"][check_name] is False, diagnostic
    assert any(
        f"check_failed: {check_name}" in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def assert_schema_failure(
    value: dict[str, Any],
    tmp_path: Path,
    expected_fragment: str = "schema_error",
) -> dict[str, Any]:
    diagnostic, exit_code = diagnostic_for(value, tmp_path)

    assert exit_code == 1, diagnostic
    assert diagnostic["schema_valid"] is False, diagnostic
    assert any(
        expected_fragment in str(error)
        for error in diagnostic["errors"]
    ), diagnostic
    return diagnostic


def expectation(value: dict[str, Any], identifier: str) -> dict[str, Any]:
    selected = value["expectations"][identifier]
    assert isinstance(selected, dict)
    return selected


def observation(value: dict[str, Any], identifier: str) -> dict[str, Any]:
    selected = value["observations"][identifier]
    assert isinstance(selected, dict)
    return selected


def relation(value: dict[str, Any], identifier: str) -> dict[str, Any]:
    selected = value["relations"][identifier]
    assert isinstance(selected, dict)
    return selected


def snapshot(path: Path) -> tuple[int, str]:
    return path.stat().st_size, sha256_file(path)


def add_runtime_packet(value: dict[str, Any]) -> None:
    identity = value["comparison_identity"]
    value["observation_bindings"]["compute_binding_report"][
        "analysis_level"
    ] = "runtime_observed"
    value["comparison_boundary"]["observed_analysis_level"] = (
        "runtime_observed"
    )
    value["observation_bindings"]["runtime_observation_status"] = "partial"
    value["coverage"]["runtime_observation_status"] = "partial"
    value["observation_bindings"]["runtime_observation_packets"] = [
        {
            "schema_version": (
                "pulsemech_compute_runtime_observation_packet_v0"
            ),
            "packet_type": "pulsemech_compute_runtime_observation_packet",
            "record_status": "example",
            "path_or_uri": "example://runtime-observation-v0.json",
            "sha256": "a" * 64,
            "packet_id": "runtime-observation:planned-observed-example-v0",
            "packet_sequence": 0,
            "packet_scope": "example",
            "subject_repository": identity["subject_repository"],
            "subject_run_key": identity["subject_run_key"],
            "subject_source_commit": identity["subject_source_commit"],
            "release_candidate_id": identity["release_candidate_id"],
            "ok": True,
        }
    ]


def add_authority_finding(
    value: dict[str, Any],
    *,
    finding_id: str = "finding:unbound-authority",
    observation_id: str = "observation:policy-materializer",
) -> None:
    value["findings"][finding_id] = {
        "finding_type": "authority_class_mismatch",
        "severity": "authority_integrity_candidate",
        "expectation_id": "expectation:execute-policy-materializer",
        "observation_ids": [observation_id],
        "relation_id": "relation:execute-policy-materializer",
        "message": "Unbound authoritative mutation observed.",
        "evidence_refs": [observation_id],
    }
    value["summary"]["authority_integrity_candidate_count"] += 1


# ---------------------------------------------------------------------------
# Positive path and deterministic diagnostics
# ---------------------------------------------------------------------------


def test_contract_files_exist() -> None:
    for path in (TOOL, SCHEMA, EXAMPLE):
        assert path.is_file(), path
        assert not path.is_symlink(), path


def test_valid_example_passes_all_semantic_checks() -> None:
    result = run_tool()

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.endswith("\n")

    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["tool"] == (
        "check_pulsemech_compute_planned_observed_relation_v0"
    )
    assert diagnostic["schema_version"] == (
        "pulsemech_compute_planned_observed_relation_v0"
    )
    assert diagnostic["relation_type"] == (
        "pulsemech_compute_planned_observed_relation"
    )
    assert diagnostic["schema_valid"] is True
    assert diagnostic["ok"] is True
    assert diagnostic["errors"] == []
    assert set(diagnostic["checks"]) == EXPECTED_CHECKS
    assert all(diagnostic["checks"].values())


def test_diagnostic_output_matches_stdout(tmp_path: Path) -> None:
    output = tmp_path / "diagnostic.json"
    result = run_tool(output=output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert output.is_file()
    assert output.read_text(encoding="utf-8") == result.stdout


def test_identical_inputs_emit_byte_identical_diagnostics(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    first_result = run_tool(output=first)
    second_result = run_tool(output=second)

    assert first_result.returncode == 0
    assert second_result.returncode == 0
    assert first_result.stdout == second_result.stdout
    assert first.read_bytes() == second.read_bytes()


def test_relation_error_state_is_independent_from_validator_success(
    tmp_path: Path,
) -> None:
    value = relation_record()
    value["ok"] = False
    value["errors"] = ["synthetic_relation_error"]
    value["coverage"]["comparison_status"] = "partial"
    value["coverage"]["identity_coverage_status"] = "partial"
    value["coverage"]["unresolved_reasons"] = [
        "artifact_coverage_partial"
    ]
    value["summary"]["comparison_complete"] = False

    diagnostic, exit_code = diagnostic_for(value, tmp_path)

    assert exit_code == 0, diagnostic
    assert diagnostic["ok"] is True
    assert diagnostic["schema_valid"] is True
    assert diagnostic["checks"]["record_ok_errors_semantics_ok"] is True


# ---------------------------------------------------------------------------
# Strict parsing, schema validation, and canonical serialization
# ---------------------------------------------------------------------------


def test_duplicate_json_keys_fail_closed(tmp_path: Path) -> None:
    relation_path = tmp_path / "duplicate.json"
    relation_path.write_text(
        '{"schema_version": '
        '"pulsemech_compute_planned_observed_relation_v0", '
        '"schema_version": "duplicate"}\n',
        encoding="utf-8",
    )

    result = run_tool(relation_path=relation_path)
    diagnostic = assert_cli_failure(
        result,
        "duplicate JSON key",
        expected_returncode=2,
    )
    assert diagnostic["schema_valid"] is False


def test_non_finite_json_values_fail_closed(tmp_path: Path) -> None:
    relation_path = tmp_path / "non-finite.json"
    relation_path.write_text('{"value": NaN}\n', encoding="utf-8")

    result = run_tool(relation_path=relation_path)
    diagnostic = assert_cli_failure(
        result,
        "non-finite JSON value",
        expected_returncode=2,
    )
    assert diagnostic["schema_valid"] is False


def test_schema_invalid_relation_skips_semantic_checks(tmp_path: Path) -> None:
    value = relation_record()
    value["authority_boundary"]["creates_gate_result"] = True

    diagnostic = assert_schema_failure(value, tmp_path)
    assert diagnostic["checks"] == {
        "semantic_checks_skipped_due_to_schema_errors": False
    }


def test_non_canonical_object_key_order_is_rejected(tmp_path: Path) -> None:
    value = relation_record()
    value = dict(reversed(list(value.items())))
    raw_text = json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
        allow_nan=False,
    ) + "\n"

    assert_semantic_failure(
        value,
        tmp_path,
        "canonical_json_key_ordering_ok",
        raw_text=raw_text,
    )


def test_missing_or_duplicate_trailing_newline_is_rejected(
    tmp_path: Path,
) -> None:
    value = relation_record()
    canonical = json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    )

    assert_semantic_failure(
        value,
        tmp_path,
        "canonical_json_newline_termination_ok",
        raw_text=canonical,
    )
    assert_semantic_failure(
        value,
        tmp_path,
        "canonical_json_newline_termination_ok",
        raw_text=canonical + "\n\n",
    )


# ---------------------------------------------------------------------------
# Deterministic record identity and plan-operation semantics
# ---------------------------------------------------------------------------


def test_record_map_order_is_rejected_when_not_sorted(tmp_path: Path) -> None:
    value = relation_record()
    value["expectations"] = dict(reversed(list(value["expectations"].items())))

    raw_text = json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
        allow_nan=False,
    ) + "\n"
    diagnostic = assert_semantic_failure(
        value,
        tmp_path,
        "record_map_ordering_ok",
        raw_text=raw_text,
    )
    assert diagnostic["checks"]["canonical_json_key_ordering_ok"] is False


def test_unsorted_string_reference_list_is_rejected(tmp_path: Path) -> None:
    value = relation_record()
    target = relation(value, "relation:execute-policy-materializer")
    target["evidence_refs"] = list(reversed(target["evidence_refs"]))

    assert_semantic_failure(
        value,
        tmp_path,
        "deterministic_string_list_ordering_ok",
    )


def test_duplicate_or_unsorted_basis_identifiers_are_rejected(
    tmp_path: Path,
) -> None:
    value = relation_record()
    target = expectation(value, "expectation:execute-policy-materializer")
    target["basis_records"] = list(reversed(target["basis_records"]))

    assert_semantic_failure(value, tmp_path, "nested_record_ordering_ok")

    value = relation_record()
    target = expectation(value, "expectation:execute-policy-materializer")
    duplicate = copy.deepcopy(target["basis_records"][0])
    duplicate["evidence_refs"] = sorted(
        duplicate["evidence_refs"] + ["duplicate-basis-variant"]
    )
    target["basis_records"].append(duplicate)
    target["basis_records"].sort(key=lambda item: item["basis_id"])

    assert_semantic_failure(
        value,
        tmp_path,
        "basis_identifiers_unique_within_expectation",
    )


def test_plan_operation_digest_is_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    operation = expectation(
        value,
        "expectation:execute-policy-materializer",
    )["plan_operation_refs"][0]
    operation["reason"] = "changed but digest left stale"

    assert_semantic_failure(
        value,
        tmp_path,
        "plan_operation_digests_recompute",
    )


def test_plan_operation_component_and_basis_identity_are_recomputed(
    tmp_path: Path,
) -> None:
    value = relation_record()
    target = expectation(value, "expectation:execute-policy-materializer")
    target["component_id"] = "other-component"

    assert_semantic_failure(
        value,
        tmp_path,
        "plan_operation_identity_consistent",
    )

    value = relation_record()
    target = expectation(value, "expectation:execute-policy-materializer")
    integration_basis = next(
        basis
        for basis in target["basis_records"]
        if basis["basis_kind"] == "integration_plan_operation"
    )
    integration_basis["source_sha256"] = "f" * 64

    assert_semantic_failure(
        value,
        tmp_path,
        "plan_operation_identity_consistent",
    )


# ---------------------------------------------------------------------------
# Subject, runtime, expectation, and observer boundaries
# ---------------------------------------------------------------------------


def test_compute_report_subject_or_candidate_drift_is_rejected(
    tmp_path: Path,
) -> None:
    value = relation_record()
    value["observation_bindings"]["compute_binding_report"][
        "release_candidate_id"
    ] = "other"

    assert_semantic_failure(
        value,
        tmp_path,
        "compute_report_subject_binding_ok",
    )


def test_runtime_packet_subject_or_candidate_drift_is_rejected(
    tmp_path: Path,
) -> None:
    value = relation_record()
    add_runtime_packet(value)
    packet = value["observation_bindings"]["runtime_observation_packets"][0]
    packet["release_candidate_id"] = "other"

    assert_semantic_failure(
        value,
        tmp_path,
        "runtime_packet_subject_bindings_ok",
    )


def test_duplicate_runtime_packet_identity_is_rejected(tmp_path: Path) -> None:
    value = relation_record()
    add_runtime_packet(value)
    packets = value["observation_bindings"]["runtime_observation_packets"]
    packets.append(copy.deepcopy(packets[0]))

    assert_semantic_failure(
        value,
        tmp_path,
        "runtime_packet_subject_bindings_ok",
    )


def test_plan_target_and_subject_binding_are_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    value["plan_binding"]["target_repository_id"] = "other/repository"
    value["comparison_boundary"][
        "plan_target_matches_subject_repository"
    ] = False
    value["ok"] = False
    value["errors"] = ["plan target mismatch"]
    value["summary"]["comparison_complete"] = False

    assert_semantic_failure(
        value,
        tmp_path,
        "plan_target_subject_binding_ok",
    )


def test_analysis_level_runtime_admission_is_fail_closed(tmp_path: Path) -> None:
    value = relation_record()
    value["coverage"]["runtime_observation_status"] = "partial"

    assert_schema_failure(
        value,
        tmp_path,
        "runtime_observation_status",
    )


def test_subject_scoped_expectation_drift_is_rejected(tmp_path: Path) -> None:
    value = relation_record()
    expectation(
        value,
        "expectation:execute-policy-materializer",
    )["expectation_scope"]["release_candidate_id"] = "other"

    assert_semantic_failure(
        value,
        tmp_path,
        "expectation_subject_scope_bindings_ok",
    )


def test_expectation_basis_run_binding_drift_is_rejected(
    tmp_path: Path,
) -> None:
    value = relation_record()
    target = expectation(value, "expectation:execute-policy-materializer")
    target["basis_records"][0]["subject_run_key"] = "OTHER_RUN"

    assert_semantic_failure(
        value,
        tmp_path,
        "expectation_basis_run_bindings_ok",
    )


def test_observer_scope_cannot_claim_subject_authority(tmp_path: Path) -> None:
    value = relation_record()
    target = observation(value, "observation:policy-materializer")
    target["execution_scope"] = "analysis_observer"

    assert_semantic_failure(value, tmp_path, "observer_boundary_ok")


def test_unbound_authority_flag_is_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    target = observation(value, "observation:policy-materializer")
    target["binding_status"] = "none"
    target["binding_class"] = "unbound"
    target["observed_mutation_classes"] = ["final_status"]
    target["unbound_authoritative_mutation"] = True
    add_authority_finding(value)

    diagnostic, exit_code = diagnostic_for(value, tmp_path)
    assert exit_code == 0, diagnostic
    assert diagnostic["schema_valid"] is True
    assert diagnostic["checks"]["unbound_authority_flags_derived_ok"] is True
    assert diagnostic["checks"]["unbound_authority_findings_present"] is True

    target["unbound_authoritative_mutation"] = False
    assert_schema_failure(value, tmp_path, "unbound_authoritative_mutation")


# ---------------------------------------------------------------------------
# Relation references, classification, and evaluation
# ---------------------------------------------------------------------------


def test_dangling_relation_reference_is_rejected(tmp_path: Path) -> None:
    value = relation_record()
    relation(value, "relation:execute-policy-materializer")[
        "expectation_id"
    ] = "expectation:missing"

    assert_semantic_failure(
        value,
        tmp_path,
        "relation_references_resolve",
    )


def test_duplicate_relation_candidate_is_rejected(tmp_path: Path) -> None:
    value = relation_record()
    value["relations"]["relation:duplicate-candidate"] = copy.deepcopy(
        relation(value, "relation:execute-policy-materializer")
    )
    value["coverage"]["relations_total"] += 1
    value["summary"]["relations"] += 1
    value["summary"]["planned_and_observed"] += 1
    value["summary"]["decisive_relations"] += 1

    assert_semantic_failure(value, tmp_path, "relation_candidates_unique")


def test_presence_expectation_cannot_use_execution_relation_status(
    tmp_path: Path,
) -> None:
    value = relation_record()
    target = relation(value, "relation:presence-status-schema")
    target["relation_status"] = "planned_but_not_observed"
    target["evaluation"] = {
        "execution_observation": "not_observed",
        "execution_identity": "not_required",
        "source_identity": "not_required",
        "run_binding": "not_required",
        "declared_role": "not_required",
        "authority_class": "not_required",
        "downstream_consumption": "not_required",
        "coverage": "complete",
        "decisive": True,
    }
    value["summary"]["planned_presence_only"] -= 1
    value["summary"]["planned_but_not_observed"] += 1

    assert_semantic_failure(
        value,
        tmp_path,
        "relation_expectation_kind_compatibility_ok",
    )


def test_relation_evaluation_is_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    relation(value, "relation:execute-policy-materializer")["evaluation"][
        "source_identity"
    ] = "not_required"

    assert_semantic_failure(
        value,
        tmp_path,
        "relation_evaluations_recompute",
    )


def test_expectation_cannot_be_classified_by_multiple_relations(
    tmp_path: Path,
) -> None:
    value = relation_record()
    duplicate = copy.deepcopy(
        relation(value, "relation:execute-policy-materializer")
    )
    duplicate["observation_ids"] = ["observation:status-validator"]
    value["relations"]["relation:second-expectation-use"] = duplicate
    value["coverage"]["relations_total"] += 1
    value["summary"]["relations"] += 1
    value["summary"]["planned_and_observed"] += 1
    value["summary"]["decisive_relations"] += 1

    assert_semantic_failure(
        value,
        tmp_path,
        "expectation_relation_multiplicity_ok",
    )


def test_observation_cannot_be_consumed_by_multiple_relations(
    tmp_path: Path,
) -> None:
    value = relation_record()
    second = relation(value, "relation:execute-status-validator-consumed")
    second["observation_ids"] = ["observation:policy-materializer"]

    assert_semantic_failure(
        value,
        tmp_path,
        "observation_relation_multiplicity_ok",
    )


# ---------------------------------------------------------------------------
# Coverage, summary, findings, and terminal state semantics
# ---------------------------------------------------------------------------


def test_coverage_counts_are_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    value["coverage"]["expectations_total"] += 1

    assert_semantic_failure(value, tmp_path, "coverage_counts_recompute")


def test_unclassified_record_lists_are_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    removed = value["relations"].pop("relation:presence-status-schema")
    assert removed
    value["coverage"]["relations_total"] -= 1
    value["summary"]["relations"] -= 1
    value["summary"]["planned_presence_only"] -= 1
    value["summary"]["decisive_relations"] -= 1

    assert_semantic_failure(value, tmp_path, "coverage_counts_recompute")


def test_summary_counts_are_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    value["summary"]["planned_and_observed"] += 1

    assert_semantic_failure(value, tmp_path, "summary_counts_recompute")


def test_finding_references_must_resolve(tmp_path: Path) -> None:
    value = relation_record()
    add_authority_finding(value, observation_id="observation:missing")

    assert_semantic_failure(value, tmp_path, "finding_references_resolve")


def test_duplicate_finding_fingerprint_is_rejected(tmp_path: Path) -> None:
    value = relation_record()
    add_authority_finding(value, finding_id="finding:first")
    add_authority_finding(value, finding_id="finding:second")

    assert_semantic_failure(value, tmp_path, "finding_fingerprints_unique")


def test_unbound_authoritative_mutation_requires_authority_finding(
    tmp_path: Path,
) -> None:
    value = relation_record()
    target = observation(value, "observation:policy-materializer")
    target["binding_status"] = "none"
    target["binding_class"] = "unbound"
    target["observed_mutation_classes"] = ["final_status"]
    target["unbound_authoritative_mutation"] = True

    assert_semantic_failure(
        value,
        tmp_path,
        "unbound_authority_findings_present",
    )


def test_comparison_complete_is_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    value["summary"]["comparison_complete"] = False

    assert_semantic_failure(
        value,
        tmp_path,
        "comparison_complete_semantics_ok",
    )


def test_coverage_status_is_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    value["coverage"]["comparison_status"] = "partial"
    value["summary"]["comparison_complete"] = False

    assert_semantic_failure(value, tmp_path, "coverage_status_semantics_ok")


def test_record_ok_and_errors_semantics_are_recomputed(tmp_path: Path) -> None:
    value = relation_record()
    value["ok"] = False
    value["errors"] = ["synthetic_relation_error"]
    value["coverage"]["comparison_status"] = "partial"
    value["coverage"]["identity_coverage_status"] = "partial"
    value["coverage"]["unresolved_reasons"] = [
        "artifact_coverage_partial"
    ]
    value["summary"]["comparison_complete"] = False

    diagnostic, exit_code = diagnostic_for(value, tmp_path)
    assert exit_code == 0, diagnostic

    value["ok"] = True
    assert_schema_failure(value, tmp_path, "errors")


# ---------------------------------------------------------------------------
# Read-only diagnostic output boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "output_name",
    [
        "status.json",
        "release_decision_v0.json",
        "pulsemech_compute_planned_observed_relation_v0.json",
    ],
)
def test_authority_or_contract_surface_output_names_are_rejected(
    tmp_path: Path,
    output_name: str,
) -> None:
    output = tmp_path / output_name
    result = run_tool(output=output)

    diagnostic = assert_cli_failure(
        result,
        "refusing_authority_or_contract_surface_output",
        expected_returncode=2,
        stream="stderr",
    )
    assert result.stdout == ""
    assert diagnostic["schema_valid"] is False
    assert not output.exists()


@pytest.mark.parametrize(
    "protected_path",
    [SCHEMA, EXAMPLE, TOOL, GATE_POLICY, GATE_REGISTRY, PULSE_WORKFLOW],
    ids=lambda value: value.name,
)
def test_input_and_authority_source_overwrite_is_rejected(
    protected_path: Path,
) -> None:
    before = snapshot(protected_path)

    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="refusing_to_overwrite_input",
    ):
        TOOL_MODULE.reject_unsafe_output(
            protected_path,
            schema_path=SCHEMA,
            relation_path=EXAMPLE,
        )

    assert snapshot(protected_path) == before


def test_existing_and_dangling_output_symlinks_are_rejected(
    tmp_path: Path,
) -> None:
    existing_target = tmp_path / "existing-target.json"
    existing_target.write_text("{}\n", encoding="utf-8")
    existing_link = tmp_path / "existing-link.json"

    try:
        existing_link.symlink_to(existing_target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unsupported: {exc}")

    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="refusing_symlink_output_path",
    ):
        TOOL_MODULE.reject_unsafe_output(
            existing_link,
            schema_path=SCHEMA,
            relation_path=EXAMPLE,
        )
    assert existing_target.read_text(encoding="utf-8") == "{}\n"

    missing_target = tmp_path / "missing-target.json"
    dangling_link = tmp_path / "dangling-link.json"
    dangling_link.symlink_to(missing_target)

    assert dangling_link.is_symlink()
    assert not dangling_link.exists()
    assert not missing_target.exists()

    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="refusing_symlink_output_path",
    ):
        TOOL_MODULE.reject_unsafe_output(
            dangling_link,
            schema_path=SCHEMA,
            relation_path=EXAMPLE,
        )

    assert dangling_link.is_symlink()
    assert not dangling_link.exists()
    assert not missing_target.exists()


def test_output_through_symlink_parent_is_rejected(tmp_path: Path) -> None:
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    linked_directory = tmp_path / "linked"

    try:
        linked_directory.symlink_to(real_directory, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlink unsupported: {exc}")

    output = linked_directory / "diagnostic.json"
    with pytest.raises(
        TOOL_MODULE.SemanticError,
        match="refusing_symlink_output_path",
    ):
        TOOL_MODULE.reject_unsafe_output(
            output,
            schema_path=SCHEMA,
            relation_path=EXAMPLE,
        )

    assert not (real_directory / "diagnostic.json").exists()


# ---------------------------------------------------------------------------
# Direct tools-tests execution entrypoint
# ---------------------------------------------------------------------------


def check_pulsemech_compute_planned_observed_relation_validator_v0() -> None:
    raise SystemExit(pytest.main([__file__, "-q"]))


if __name__ == "__main__":
    check_pulsemech_compute_planned_observed_relation_validator_v0()
