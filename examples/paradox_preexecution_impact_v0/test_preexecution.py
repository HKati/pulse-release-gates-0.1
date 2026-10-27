from __future__ import annotations

import ast
import copy
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import check_impact
import run_local
import source_model


ROOT = Path(__file__).resolve().parent
PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
FIXTURES = json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8"))
CASES = {row["case_id"]: row for row in FIXTURES["cases"]}


def build(case: dict) -> tuple[bytes, dict]:
    source = case["candidate_source"].encode("utf-8")
    model, _code = source_model.build_model_record(source, PROFILE)
    mutation = case.get("model_mutation")
    if mutation:
        model = copy.deepcopy(model)
        if mutation["kind"] == "remove_direct_effect_route":
            model["relations"]["effect_occurrences"] = []
            model["relations"]["effect_route_count"] = 0
        elif mutation["kind"] == "empty_configuration_domain":
            domain = model["relations"]["configuration_domain"]
            domain["environment_scenarios"] = []
            domain["scenario_count"] = 0
            domain["model_nonempty_status"] = "EMPTY"
        else:  # pragma: no cover - fixture contract guard
            raise AssertionError(mutation)
    return source, model


def observed(case: dict) -> tuple[str, dict]:
    source, model = build(case)
    if case["test_lane"] == "launch_binding":
        report = check_impact.assess(source, PROFILE, model, case["context"])
        mutation = case["launch_mutation"]
        if mutation["kind"] == "replace_candidate_source":
            candidate = mutation["replacement_source"].encode("utf-8")
            result = run_local.preflight(PROFILE, candidate, report, case["context"])
        elif mutation["kind"] == "replace_context_environment":
            context = copy.deepcopy(case["context"])
            context["environment_identity"] = mutation["replacement_environment_identity"]
            result = run_local.preflight(PROFILE, source, report, context)
        else:  # pragma: no cover - fixture contract guard
            raise AssertionError(mutation)
        return result["status"], result
    report = check_impact.assess(source, PROFILE, model, case["context"])
    return report["assessment"], report


@pytest.mark.parametrize("case", FIXTURES["cases"], ids=lambda row: row["case_id"])
def test_all_24_planned_obligations(case):
    value, _record = observed(case)
    assert value == case["expected_assessment"]


@pytest.mark.parametrize("case", FIXTURES["cases"], ids=lambda row: row["case_id"])
def test_case_metadata_never_enters_candidate_or_checker_context(case):
    assert case["case_id"] not in case["candidate_source"]
    assert "expected_assessment" not in case["context"]
    assert "case_id" not in case["context"]
    assert case["pilot_execution_status"] == "NOT_RUN"
    assert case["observed_result"] is None


def test_fixture_inventory_and_profile_source_map_are_exact():
    assert FIXTURES["case_count"] == 24 == len(FIXTURES["cases"])
    assert len({row["case_id"] for row in FIXTURES["cases"]}) == 24
    bindings = PROFILE["source_basis"]["source_region_bindings"]
    assert len(bindings) == 13
    assert [row[0] for row in bindings] == [f"S{i:02d}" for i in range(1, 14)]
    assert PROFILE["pilot_execution_status"] == "NOT_RUN"
    assert PROFILE["authority_effect"] == "none"


def test_mapper_and_checker_have_no_candidate_import_path():
    for module_path in (ROOT / "source_model.py", ROOT / "check_impact.py"):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert "enforcement_probe" not in imported
        assert "candidate" not in imported


def test_mapper_has_no_exec_or_eval_of_candidate_source():
    tree = ast.parse((ROOT / "source_model.py").read_text(encoding="utf-8"))
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "exec" not in called
    assert "eval" not in called


def test_private_renaming_changes_bytes_but_not_normalized_operations():
    source0, model0 = build(CASES["P00"])
    source1, model1 = build(CASES["P01"])
    assert source0 != source1
    assert model0["candidate_sha256"] != model1["candidate_sha256"]
    normalized0 = [(row["primitive"], row["args"]) for row in model0["operations"]]
    normalized1 = [(row["primitive"], row["args"]) for row in model1["operations"]]
    assert normalized0 == normalized1


def test_safe_delegate_is_a_new_role_without_direct_sink_route():
    _source, model = build(CASES["P02"])
    assert "delegate" in model["relations"]["roles"]
    assert all(row["route"] == "broker_append" for row in model["relations"]["effect_occurrences"])


def test_redundant_check_case_uses_monitor_lifetime_and_has_one_effect():
    value, report = observed(CASES["P03"])
    assert value == "PROPERTY_DEPENDENT"
    replay = next(row for row in report["finite_scenarios"] if row["scenario"] == "replay_two_attempts")
    assert len(replay["effects"]) == 1
    assert report["invariant_assessment"] == "SATISFIED"
    assert report["useful_operation_assessment"] == "SATISFIED"


def test_alternative_grounded_support_prevents_false_block():
    value, report = observed(CASES["P04"])
    assert value == "ESTABLISHED_CONDITIONAL"
    assert "evidence.secondary" in report["evidence_closure"]
    assert "source.justified" in report["evidence_closure"]


@pytest.mark.parametrize("case_id", ["N01", "N02", "N03", "N04", "N05", "N06", "N07", "N08", "N11"])
def test_negative_cases_preserve_source_located_model_witnesses(case_id):
    value, report = observed(CASES[case_id])
    assert value == "REFUTED_IN_MODEL"
    assert report["counterexamples"]
    assert report["counterexample_realizability_status"] == "MODEL_WITNESS_ONLY"
    assert report["execution_observation_status"] == "NOT_RUN"


def test_endpoint_equivalence_does_not_erase_unsafe_prefix():
    value, report = observed(CASES["N08"])
    assert value == "REFUTED_IN_MODEL"
    healthy = next(row for row in report["finite_scenarios"] if row["scenario"] == "healthy")
    assert len(healthy["effects"]) == 1
    witness = healthy["effects"][0]
    assert witness["support"]["intent"] is False
    assert witness["support"]["ack"] is False
    assert witness["support"]["audit"] is False


def test_useful_operation_is_separate_from_safety():
    value, report = observed(CASES["N09"])
    assert value == "SAFETY_ONLY_NOT_ACCEPTABLE"
    assert report["invariant_assessment"] == "SATISFIED"
    assert report["useful_operation_assessment"] == "NOT_SATISFIED"


def test_ungrounded_positive_cycle_does_not_create_support():
    value, report = observed(CASES["N10"])
    assert value == "UNRESOLVED"
    assert report["source_justification_status"] == "UNRESOLVED_CYCLE"
    assert "source.justified" not in report["evidence_closure"]


def test_joint_support_cannot_be_replaced_by_true_marginals():
    value, report = observed(CASES["N11"])
    assert value == "REFUTED_IN_MODEL"
    mismatch = next(row for row in report["counterexamples"] if row["scenario"] == "joint_mismatch")
    assert mismatch["support"]["ack"] is True
    assert mismatch["support"]["audit"] is False


def test_unsupported_source_is_unresolved_and_never_executed():
    source, model = build(CASES["U01"])
    assert model["source_language_status"] == "UNSUPPORTED"
    report = check_impact.assess(source, PROFILE, model, CASES["U01"]["context"])
    assert report["assessment"] == "UNRESOLVED"
    assert report["candidate_imported_or_executed"] is False


def test_omitted_source_visible_effect_route_invalidates_mapping():
    value, report = observed(CASES["U02"])
    assert value == "INVALID_MAPPING"
    assert report["source_model_mapping_status"] == "INVALID"


def test_empty_model_cannot_pass_vacuously():
    value, report = observed(CASES["U03"])
    assert value == "INCONSISTENT_OR_INVALID"
    assert report["model_nonempty_status"] == "FAILED"


def test_post_assessment_source_replacement_is_rejected():
    value, result = observed(CASES["B01"])
    assert value == "BINDING_REJECTED"
    assert result["reason"] == "candidate_sha256"
    assert result["execution_started"] is False


def test_environment_change_invalidates_old_assessment():
    value, result = observed(CASES["B02"])
    assert value == "UNRESOLVED_OR_BINDING_REJECTED"
    assert result["reason"] == "environment_identity"


def test_cross_target_proof_reuse_is_rejected():
    value, report = observed(CASES["B03"])
    assert value == "BINDING_REJECTED"
    assert report["proof_applicability_status"] == "BINDING_REJECTED"


def test_missing_observer_is_not_zero_effect_evidence():
    value, report = observed(CASES["O01"])
    assert value == "OBSERVATION_INCOMPLETE"
    assert report["execution_observation_status"] == "NOT_RUN"


def test_preexecution_boundary_prevents_unchecked_launch():
    value, report = observed(CASES["O02"])
    assert value == "NO_UNCHECKED_LAUNCH"
    assert report["candidate_imported_or_executed"] is False


def test_baseline_assessment_is_eligible_for_preflight_only():
    source, model = build(CASES["P00"])
    report = check_impact.assess(source, PROFILE, model, CASES["P00"]["context"])
    result = run_local.preflight(PROFILE, source, report, CASES["P00"]["context"])
    assert result["status"] == "ELIGIBLE_FOR_EXPLICIT_SCRATCH_LAUNCH"
    assert result["execution_started"] is False


def test_property_dependent_result_is_not_launch_eligible():
    source, model = build(CASES["P03"])
    report = check_impact.assess(source, PROFILE, model, CASES["P03"]["context"])
    result = run_local.preflight(PROFILE, source, report, CASES["P03"]["context"])
    assert result["status"] == "NO_UNCHECKED_LAUNCH"
    assert result["reason"] == "assessment_not_eligible"


def test_runtime_ast_validator_accepts_baseline_and_rejects_unknown_code():
    run_local._validate_runtime_ast(CASES["P00"]["candidate_source"].encode(), PROFILE)
    with pytest.raises(run_local.LaunchError):
        run_local._validate_runtime_ast(CASES["U01"]["candidate_source"].encode(), PROFILE)


def test_sealed_source_readback_preserves_exact_bytes():
    source = CASES["P00"]["candidate_source"].encode()
    fd, digest = run_local._seal_source(source)
    try:
        assert digest == source_model.sha256(source)
        assert Path(f"/proc/self/fd/{fd}").read_bytes() == source
    finally:
        import os
        os.close(fd)


def test_cli_roundtrip_is_preflight_only(tmp_path):
    case = CASES["P00"]
    candidate = tmp_path / "candidate.py"
    context = tmp_path / "context.json"
    model = tmp_path / "model.json"
    report = tmp_path / "report.json"
    preflight = tmp_path / "preflight.json"
    candidate.write_text(case["candidate_source"], encoding="utf-8")
    context.write_text(json.dumps(case["context"]), encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "source_model.py"), "--profile", str(ROOT / "profile.json"),
         "--candidate", str(candidate), "--output", str(model)], check=True
    )
    subprocess.run(
        [sys.executable, str(ROOT / "check_impact.py"), "--profile", str(ROOT / "profile.json"),
         "--candidate", str(candidate), "--model", str(model), "--context", str(context),
         "--output", str(report)], check=True
    )
    subprocess.run(
        [sys.executable, str(ROOT / "run_local.py"), "--profile", str(ROOT / "profile.json"),
         "--candidate", str(candidate), "--assessment", str(report), "--context", str(context),
         "--output", str(preflight), "--preflight-only"], check=True
    )
    record = json.loads(preflight.read_text())
    assert record["status"] == "ELIGIBLE_FOR_EXPLICIT_SCRATCH_LAUNCH"
    assert record["execution_started"] is False


def test_no_pilot_result_or_production_authority_is_claimed():
    assert FIXTURES["pilot_execution_status"] == "NOT_RUN"
    assert PROFILE["report_contract"]["execution_observation_status"] == "NOT_RUN"
    assert PROFILE["production_gate_eligible"] is False
    assert PROFILE["authority_effect"] == "none"
