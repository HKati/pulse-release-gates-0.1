"""LRM-03 relation comparison regressions under explicit finite premises.

The original expected corpus is read only by this test controller. Runtime
comparison receives source-bound input and independently configured evidence,
never expected labels. All examples and independent reviews below are synthetic.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.language_relation_v0.comparator import measure_bundle, measure_input
from tools.language_relation_v0.comparison_evidence import ComparisonTrust
from tools.language_relation_v0.io import InputError
from tools.language_relation_v0.logic import LogicProblem, VariantLogic


SELF = "tests/test_language_relation_comparator_v0.py"
EXAMPLES = ROOT / "examples/language_relation_measurement_v0"
CASES = json.loads((EXAMPLES / "cases.json").read_text(encoding="utf-8"))["cases"]
EXPECTED = json.loads((EXAMPLES / "expected.json").read_text(encoding="utf-8"))["expectations"]
MEASUREMENT_SCHEMA = json.loads(
    (ROOT / "schemas/language_relation_measurement_v0.schema.json").read_text(encoding="utf-8")
)
VERIFICATION_SCHEMA = json.loads(
    (ROOT / "schemas/language_relation_verification_v0.schema.json").read_text(encoding="utf-8")
)
CLI = ROOT / "tools/measure_language_relations_v0.py"
PROFILE = json.loads((ROOT / "contracts/language_relation_profile_v0.json").read_text(encoding="utf-8"))


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def reference_input(number: int = 1) -> dict:
    return deepcopy(next(row for row in CASES if row["case_id"] == f"LRM_REF_{number:02d}"))


def save_input(directory: Path, payload: dict) -> Path:
    path = directory / "input.json"
    path.write_bytes(encoded(payload))
    return path


def result_for(report: dict, target_id: str = "target_main") -> dict:
    rows = [row for row in report["results"] if row["target_id"] == target_id]
    assert len(rows) == 1, (target_id, report["results"])
    return rows[0]


def assert_measurement_integrity(report: dict, payload: dict) -> None:
    jsonschema.Draft202012Validator(MEASUREMENT_SCHEMA).validate(report)
    assert report["provenance"] == "measurement_run"
    assert report["execution"]["status"] == "completed"
    assert report["authority_effect"] == "none"
    assert report["release_authority_activation"] is False
    assert report["status_axes"]["authority_status"] == "none"
    assert report["status_axes"]["causal_status"] == "not_evaluated"
    assert report["status_axes"]["reproduction_status"] == "not_tested"
    assert report["impacts"] == []
    assert report["support"] is None
    targets = {row["target_id"]: row for row in payload["measurement_request"]["targets"]}
    assert {row["target_id"] for row in report["results"]} == set(targets)
    assert len(report["results"]) == len(targets)
    variants = {row["variant_id"] for row in payload["interpretations"]["variants"]}
    witnesses = {row["witness_id"]: row for row in report["witnesses"]}
    assert len(witnesses) == len(report["witnesses"])
    for result in report["results"]:
        target = targets[result["target_id"]]
        assert set(result["coverage_obligation_ids"]) == set(target["required_obligation_ids"])
        assert set(result["closed_obligation_ids"]) <= set(result["coverage_obligation_ids"])
        assert set(result["compatible_variant_ids"]) <= variants
        assert set(result["witness_ids"]) <= witnesses.keys()
        if result["assessment_state"] == "IDENTIFIED":
            assert set(result["closed_obligation_ids"]) == set(result["coverage_obligation_ids"])
            assert result["possible_relation_states"] == [result["relation_state"]]
            assert result["compatible_variant_ids"]
        if result["relation_state"] in {"CHANGED", "BROKEN"}:
            assert result["witness_ids"]
        for identifier in result["witness_ids"]:
            assert witnesses[identifier]["target_id"] == result["target_id"]
    relations = {
        side: {row["relation_id"]: row for row in representation["relations"]}
        for side, representation in payload["representations"].items()
    }
    for witness in witnesses.values():
        assert witness["target_id"] in targets
        assert set(witness["variant_ids"]) <= variants
        for side in ("before", "after"):
            assert set(witness[f"{side}_relation_ids"]) <= relations[side].keys()
        atom_ids = [row["atom_id"] for row in witness["valuation"]]
        assert len(atom_ids) == len(set(atom_ids))
        for atom_id in atom_ids:
            matches = [rows[atom_id] for rows in relations.values() if atom_id in rows]
            assert len(matches) == 1, atom_id
            expression = matches[0]["expression"]
            assert expression["op"] == "ATOM"
            assert all("variable" not in row["value"] for row in expression["arguments"])
    for addition in report["introduced_relations"]:
        assert addition["target_id"] in targets
        assert addition["relation_id"] in relations["after"]
        if addition["novelty"] == "derived_explicitization":
            assert addition["derivation_ref"] in witnesses
            assert witnesses[addition["derivation_ref"]]["kind"] == "derivation"


def measured(tmp_path: Path, payload: dict, **kwargs) -> dict:
    original = deepcopy(payload)
    report = measure_input(save_input(tmp_path, payload), **kwargs)
    assert payload == original
    assert_measurement_integrity(report, payload)
    return report


def replace_source(payload: dict, side: str, text: str, language: str = "en") -> None:
    source = next(row for row in payload["sources"] if row["role"] == side)
    raw = text.encode("utf-8")
    source.update(content={"kind": "inline_utf8", "text": text}, language=language,
                  byte_length=len(raw), content_sha256=digest(raw))
    for anchor in payload["source_anchors"]:
        if anchor["source_id"] == source["source_id"]:
            anchor.update(start_byte=0, end_byte=len(raw), content_sha256=digest(raw))


def atom(side: str, person: str = "anna", predicate: str = "approve") -> dict:
    return {"op": "ATOM", "predicate": predicate,
            "arguments": [{"role": "agent", "value": {"entity_id": side[0] + "_" + person}}]}


def ground_helpers(payload: dict, people: tuple[str, ...] = ("anna", "bela")) -> None:
    for side in ("before", "after"):
        representation = payload["representations"][side]
        template = representation["relations"][0]
        for person in people:
            helper = deepcopy(template)
            helper.update(relation_id=side[0] + "_atom_" + person,
                          expression=atom(side, person), discourse_type="assertion",
                          modality="declarative", speaker_entity_id=None)
            representation["relations"].append(helper)


def semantic_results(report: dict) -> dict:
    return {
        row["target_id"]: {key: row[key] for key in (
            "relation_state", "assessment_state", "representation_basis", "claim_scope",
            "coverage_obligation_ids", "closed_obligation_ids", "compatible_variant_ids",
            "possible_relation_states")}
        for row in report["results"]
    }


def contract_bytes(value: dict) -> bytes:
    """Independent fixture encoding for the preserved profile's semantic sets."""
    record_ids = {
        "sources": "source_id", "source_anchors": "anchor_id", "entities": "entity_id",
        "domains": "domain_id", "relations": "relation_id", "groups": "group_id",
        "variants": "variant_id", "targets": "target_id", "correspondence": "correspondence_id",
        "coverage_obligations": "obligation_id", "claims": "claim_id", "rules": "rule_id",
        "checks": "check_id", "basis_records": "side", "entries": "entry_id", "source_bindings": "source_id",
    }

    def ordered(node, key=""):
        if isinstance(node, dict):
            return {name: ordered(child, name) for name, child in node.items()}
        if isinstance(node, list):
            children = [ordered(child) for child in node]
            if (key.endswith("_ids") or key == "evidence_refs") and all(isinstance(x, str) for x in children):
                return sorted(children)
            if key in record_ids:
                return sorted(children, key=lambda row: row[record_ids[key]])
            return children
        return node

    return encoded(ordered(value))


def evidence_document(schema_version: str, **fields) -> dict:
    return {"schema_version": schema_version, **fields,
            "authority_effect": "none", "release_authority_activation": False}


def completed_check(check_id: str, **fields) -> dict:
    return {"check_id": check_id, **fields, "status": "completed", "result": "pass", "reason": None}


def write_source_acceptance(fixture: dict, *, refresh: bool = True) -> None:
    payload = fixture["payload"]
    if refresh:
        for side in ("before", "after"):
            subject = digest(contract_bytes({
                "projection_version": "language_relation_subject_v0", "side": side,
                "input": {key: value for key, value in payload.items() if key != "representation_basis"}}))
            entry = fixture["entries"][side]
            entry["subject_sha256"] = subject
            payload["representation_basis"][side]["acceptance_ref"]["content_sha256"] = digest(contract_bytes(entry))
            fixture["source_records"][side]["subject_sha256"] = subject
        fixture["input_path"].write_bytes(encoded(payload))
        actual_input = {"artifact_id": payload["case_id"], "content_sha256": digest(fixture["input_path"].read_bytes())}
        for record in fixture["source_records"].values():
            record["input_ref"] = deepcopy(actual_input)
    directory = fixture["source_config"].parent
    inventory = evidence_document("language_relation_acceptance_inventory_v0",
                                  inventory_id="synthetic_source_inventory",
                                  entries=list(fixture["entries"].values()))
    raw = encoded(inventory)
    (directory / "inventory.json").write_bytes(raw)
    config = evidence_document("language_relation_trust_config_v0",
                               inventory_files=[{"path": "inventory.json", "content_sha256": digest(raw)}],
                               verification_files=[], processing_files=[])
    for side, record in fixture["source_records"].items():
        raw = encoded(record)
        filename = side + "_verification.json"
        (directory / filename).write_bytes(raw)
        config["verification_files"].append({"path": filename, "content_sha256": digest(raw)})
    fixture["source_config"].write_bytes(encoded(config))


def write_comparison_reviews(fixture: dict, *, refresh: bool = False) -> None:
    config = evidence_document("language_relation_comparison_trust_config_v0", review_files=[])
    for number, review in enumerate(fixture["reviews"]):
        if refresh:
            review["input_ref"] = {"artifact_id": fixture["payload"]["case_id"],
                                   "content_sha256": digest(fixture["input_path"].read_bytes())}
        raw = encoded(review)
        filename = f"review_{number}.json"
        (fixture["comparison_config"].parent / filename).write_bytes(raw)
        config["review_files"].append({"path": filename, "content_sha256": digest(raw)})
    fixture["comparison_config"].write_bytes(encoded(config))


def accepted_fixture(tmp_path: Path, payload: dict | None = None,
                     source_basis: str = "accepted_reference") -> dict:
    payload = deepcopy(payload) if payload is not None else reference_input()
    package = tmp_path / "package"
    source_trust = tmp_path / "source_trust"
    comparison_trust = tmp_path / "comparison_trust"
    for directory in (package, source_trust, comparison_trust):
        directory.mkdir()
    for row in payload["correspondence"]:
        row.update(basis="accepted_reference", rule_or_reference_id="reference_" + row["correspondence_id"])
    review_ids = {target["target_id"]: "comparison_review_" + target["target_id"]
                  for target in payload["measurement_request"]["targets"]}
    for obligation in payload["coverage_obligations"]:
        obligation["evidence_refs"] = [review_ids[obligation["target_id"]]]
    entries, source_records = {}, {}
    method = "independent_reference_review" if source_basis == "accepted_reference" else "controlled_source_profile_v0"
    scope = "reference_interpretation" if source_basis == "accepted_reference" else "controlled_source_profile"
    for side in ("before", "after"):
        entry = {"entry_id": "accepted_" + side, "basis": source_basis, "subject_sha256": "0" * 64,
                 "side": side, "representation_id": payload["representations"][side]["representation_id"],
                 "verification_id": "source_review_" + side, "method": method, "claim_scope": scope}
        entries[side] = entry
        payload["representation_basis"][side] = {
            "basis": source_basis, "verification_ref": entry["verification_id"],
            "acceptance_ref": {"inventory_id": "synthetic_source_inventory", "entry_id": entry["entry_id"],
                               "content_sha256": "0" * 64}}
        source_records[side] = evidence_document("language_relation_source_verification_v0",
            **{key: value for key, value in entry.items() if key != "entry_id"},
            input_ref={"artifact_id": payload["case_id"], "content_sha256": "0" * 64},
            profile_ref=deepcopy(payload["profile_ref"]),
            checker_ref={"tool_id": "synthetic_source_reviewer", "version": "0",
                         "content_sha256": digest(b"Synthetic independent source reviewer.")},
            checks=[completed_check(side + "_" + kind, kind=kind)
                    for kind in ("source_binding", "subject_binding", "representation_mapping", "coverage")])
    fixture = {"payload": payload, "package": package, "input_path": package / "input.json",
               "source_config": source_trust / "config.json",
               "comparison_config": comparison_trust / "config.json", "entries": entries,
               "source_records": source_records, "reviews": []}
    write_source_acceptance(fixture)
    for target in payload["measurement_request"]["targets"]:
        target_id = target["target_id"]
        obligations = [row for row in payload["coverage_obligations"] if row["target_id"] == target_id]
        required_context = set(target["context_source_ids"])
        context_ids = {row["source_id"] for row in payload["sources"] if row["role"] == "context"}
        for row in obligations:
            required_context.update(context_ids.intersection(row["source_ids"]))
        fixture["reviews"].append(evidence_document("language_relation_comparison_review_v0",
            verification_id=review_ids[target_id],
            input_ref={"artifact_id": payload["case_id"], "content_sha256": digest(fixture["input_path"].read_bytes())},
            profile_ref=deepcopy(payload["profile_ref"]), target_id=target_id,
            basis="accepted_reference", method="independent_comparison_reference_review",
            claim_scope="reference_interpretation",
            checker_ref={"tool_id": "synthetic_comparison_reviewer", "version": "0",
                         "content_sha256": digest(b"Synthetic independent comparison reviewer.")},
            reviewed_variant_ids=[row["variant_id"] for row in payload["interpretations"]["variants"]],
            correspondence_checks=[completed_check("checked_" + row["correspondence_id"],
                correspondence_id=row["correspondence_id"], reference_id=row["rule_or_reference_id"])
                for row in payload["correspondence"]],
            coverage_checks=[completed_check("checked_" + row["obligation_id"],
                obligation_id=row["obligation_id"], source_ids=list(row["source_ids"])) for row in obligations],
            family_check=completed_check("checked_family", family_state=payload["interpretations"]["state"]),
            context_check=completed_check("checked_context", context_source_ids=sorted(required_context)),
            addition_checks=[]))
    write_comparison_reviews(fixture)
    return fixture


def measure_accepted(fixture: dict, **overrides) -> dict:
    options = {"package_root": fixture["package"], "trust_config": fixture["source_config"],
               "comparison_trust_config": fixture["comparison_config"], **overrides}
    report = measure_input(fixture["input_path"], **options)
    assert_measurement_integrity(report, fixture["payload"])
    return report


def review_outcome(fixture: dict, target_id: str = "target_main") -> dict:
    payload = fixture["payload"]
    store = ComparisonTrust.load(fixture["comparison_config"], fixture["package"])
    return store.target_review(payload,
        {"artifact_id": payload["case_id"], "content_sha256": digest(fixture["input_path"].read_bytes())},
        target_id, correspondence_ids=[row["correspondence_id"] for row in payload["correspondence"]],
        variant_ids=[row["variant_id"] for row in payload["interpretations"]["variants"]])


@pytest.mark.parametrize("case", CASES, ids=lambda row: row["case_id"])
def test_reference_relational_controls_execute_with_candidate_scope(tmp_path, case):
    payload = deepcopy(case)
    report = measured(tmp_path, payload)
    expectation = next(row for row in EXPECTED if row["case_id"] == payload["case_id"])
    for expected in expectation["target_expectations"]:
        result = result_for(report, expected["target_id"])
        assert result["relation_state"] == expected["relation_state"], report
        assert result["assessment_state"] == expected["assessment_state"], report
        assert result["representation_basis"] == "candidate_only"
        assert result["claim_scope"] == "candidate_structures"
    for expected in expectation.get("introduced_expectations", []):
        matches = [row for row in report["introduced_relations"]
                   if row["relation_id"] == expected["relation_id"]]
        assert len(matches) == 1, report["introduced_relations"]
        assert matches[0]["novelty"] == expected["novelty"]
        assert matches[0]["evidence_status"] == expected["evidence_status"]


@pytest.mark.parametrize("number", (1, 3, 5, 7, 12, 14, 15, 16, 17, 18, 19, 20, 21))
def test_case_identifier_does_not_select_a_semantic_judgment(tmp_path, number):
    payload = reference_input(number)
    first = measured(tmp_path, payload)
    payload["case_id"] = "Renamed_without_reference_label"
    second = measured(tmp_path, payload)
    assert first["input_ref"] != second["input_ref"]
    assert semantic_results(first) == semantic_results(second)
    assert [(row["relation_id"], row["novelty"], row["evidence_status"])
            for row in first["introduced_relations"]] == [
                (row["relation_id"], row["novelty"], row["evidence_status"])
                for row in second["introduced_relations"]]


def test_runtime_does_not_read_reference_oracle_or_corpus(tmp_path, monkeypatch):
    payload = reference_input()
    read_bytes, read_text = Path.read_bytes, Path.read_text

    def allowed(path):
        assert path.name not in {"expected.json", "cases.json", "contract_examples.json"}

    def guarded_bytes(path):
        allowed(path)
        return read_bytes(path)

    def guarded_text(path, *args, **kwargs):
        allowed(path)
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_bytes)
    monkeypatch.setattr(Path, "read_text", guarded_text)
    assert result_for(measured(tmp_path, payload))["relation_state"] == "PRESERVED"


def test_measurement_bundle_binds_actual_verification_and_exact_input(tmp_path):
    payload = reference_input()
    input_path = save_input(tmp_path, payload)
    first = measure_bundle(input_path)
    second = measure_bundle(input_path)
    assert first == second
    assert set(first) == {"measurement", "verification"}
    verification, report = first["verification"], first["measurement"]
    jsonschema.Draft202012Validator(VERIFICATION_SCHEMA).validate(verification)
    assert_measurement_integrity(report, payload)
    assert report["input_ref"] == verification["input_ref"]
    assert report["input_ref"]["content_sha256"] == digest(input_path.read_bytes())
    assert any(ref["artifact_id"] == verification["verification_id"]
               for ref in report["verification_refs"])
    assert report["verification_refs"] == [{"artifact_id": verification["verification_id"],
                                            "content_sha256": digest(contract_bytes(verification))}]
    assert report == measure_input(input_path)


@pytest.mark.parametrize("side", ("before", "after"))
def test_wrong_source_bytes_leave_target_unbound(tmp_path, side):
    payload = reference_input()
    next(row for row in payload["sources"] if row["role"] == side)["content_sha256"] = "0" * 64
    result = result_for(measured(tmp_path, payload))
    assert result["assessment_state"] == "UNBOUND"
    assert result["relation_state"] == "UNDETERMINED"
    assert result["reason"]


def test_equal_wrong_candidate_mappings_cannot_hide_source_and_or_difference(tmp_path):
    payload = reference_input(5)
    payload["representations"]["after"]["relations"][0]["expression"]["op"] = "AND"
    result = result_for(measured(tmp_path, payload))
    assert result["relation_state"] == "UNDETERMINED"
    assert result["assessment_state"] != "IDENTIFIED"
    assert result["reason"]


@pytest.mark.parametrize("operator,word", (("AND", "and"), ("OR", "or")))
def test_operand_order_change_preserves_the_selected_relation(tmp_path, operator, word):
    payload = reference_input(5)
    for side in ("before", "after"):
        expression = payload["representations"][side]["relations"][0]["expression"]
        expression["op"] = operator
        if side == "after":
            expression["operands"].reverse()
        names = ("Anna", "Béla") if side == "before" else ("Béla", "Anna")
        replace_source(payload, side, f"({names[0]} approves) {word} ({names[1]} approves).")
    payload["measurement_request"]["targets"][0]["question"] = "relation_preservation"
    assert result_for(measured(tmp_path, payload))["relation_state"] == "PRESERVED"


def test_bound_variable_alpha_renaming_preserves_the_finite_relation(tmp_path):
    payload = reference_input(7)
    for side, variable in (("before", "x"), ("after", "y")):
        payload["representations"][side]["relations"][0]["expression"] = {
            "op": "FORALL", "variable": variable, "domain_id": side[0] + "_people",
            "body": {"op": "ATOM", "predicate": "approve",
                     "arguments": [{"role": "agent", "value": {"variable": variable}}]}}
        replace_source(payload, side, f"for every {variable} in {{Anna, Béla}} ({variable} approves).")
    assert result_for(measured(tmp_path, payload))["relation_state"] == "PRESERVED"


def test_boolean_equivalence_is_not_a_general_relation_rewrite(tmp_path):
    payload = reference_input(8)
    assert result_for(measured(tmp_path, payload))["relation_state"] == "PRESERVED"
    payload["measurement_request"]["targets"][0]["question"] = "relation_preservation"
    assert result_for(measured(tmp_path, payload))["relation_state"] != "PRESERVED"


def test_and_or_configuration_witness_uses_declared_atoms_and_one_valuation(tmp_path):
    payload = reference_input(5)
    ground_helpers(payload)
    report = measured(tmp_path, payload)
    result = result_for(report)
    assert result["relation_state"] == "CHANGED"
    configurations = [row for row in report["witnesses"]
                      if row["kind"] == "configuration" and row["witness_id"] in result["witness_ids"]]
    assert configurations, report["witnesses"]
    for witness in configurations:
        values = {}
        for row in witness["valuation"]:
            person = row["atom_id"].removeprefix("b_atom_").removeprefix("a_atom_")
            if person in values:
                assert values[person] == row["value"]
            values[person] = row["value"]
        assert set(values) == {"anna", "bela"}
        before = values["anna"] and values["bela"]
        after = values["anna"] or values["bela"]
        assert before != after


def test_not_all_versus_none_has_a_finite_domain_counterexample(tmp_path):
    payload = reference_input(7)
    payload["measurement_request"]["targets"][0]["question"] = "condition_impact"
    ground_helpers(payload)
    report = measured(tmp_path, payload)
    assert result_for(report)["relation_state"] == "CHANGED"
    configurations = [row for row in report["witnesses"] if row["kind"] == "configuration"]
    assert configurations, report["witnesses"]
    for witness in configurations:
        values = {}
        for row in witness["valuation"]:
            person = row["atom_id"].removeprefix("b_atom_").removeprefix("a_atom_")
            if person in values:
                assert values[person] == row["value"]
            values[person] = row["value"]
        assert set(values) == {"anna", "bela"}
        assert (not all(values.values())) != all(not value for value in values.values())


def test_unbound_equal_labels_do_not_prove_cross_source_identity(tmp_path):
    payload = reference_input()
    payload["correspondence"] = [row for row in payload["correspondence"] if row["kind"] != "entity"]
    allowed = {row["correspondence_id"] for row in payload["correspondence"]}
    for variant in payload["interpretations"]["variants"]:
        variant["correspondence_ids"] = [key for key in variant["correspondence_ids"] if key in allowed]
    assert result_for(measured(tmp_path, payload))["relation_state"] != "PRESERVED"


def test_ternary_difference_survives_equal_pairwise_projections(tmp_path):
    payload = reference_input(17)
    tuples = {}
    for side in ("before", "after"):
        labels = {row["entity_id"]: row["label"] for row in payload["representations"][side]["entities"]}
        tuples[side] = {tuple(labels[arg["value"]["entity_id"]] for arg in row["expression"]["arguments"])
                        for row in payload["representations"][side]["relations"]}
    assert tuples["before"] != tuples["after"]
    for axes in ((0, 1), (0, 2), (1, 2)):
        assert {tuple(row[i] for i in axes) for row in tuples["before"]} == {
            tuple(row[i] for i in axes) for row in tuples["after"]}
    assert result_for(measured(tmp_path, payload))["relation_state"] == "CHANGED"


def test_joint_alternative_loss_preserves_the_unrelated_local_target(tmp_path):
    payload = reference_input(18)
    report = measured(tmp_path, payload)
    assert result_for(report)["relation_state"] == "CHANGED"
    assert result_for(report, "target_stable")["relation_state"] == "PRESERVED"
    assert {row["variant_id"] for row in payload["interpretations"]["variants"]} == {
        "variant_anna", "variant_eva"}
    assert all(set(row["compatible_variant_ids"]) <= {"variant_anna", "variant_eva"}
               for row in report["results"])
    assert any(row["kind"] == "alternative_loss" for row in report["witnesses"])


@pytest.mark.parametrize("number,assessment", ((19, "UNBOUND"), (20, "INCOMPATIBLE"), (21, "UNRESOLVED")))
def test_unknown_empty_and_truncated_families_remain_distinct(tmp_path, number, assessment):
    result = result_for(measured(tmp_path, reference_input(number)))
    assert result["relation_state"] == "UNDETERMINED"
    assert result["assessment_state"] == assessment
    assert result["reason"]


def test_new_content_does_not_inherit_original_assertion_evidence(tmp_path):
    report = measured(tmp_path, reference_input(15))
    addition, = [row for row in report["introduced_relations"] if row["relation_id"] == "a_addition"]
    assert addition["novelty"] == "new_content"
    assert addition["evidence_status"] == "unsupported"
    assert addition["evidence_refs"] == []
    assert addition["derivation_ref"] is None


def test_unasserted_original_helper_cannot_pair_away_an_introduced_assertion(tmp_path):
    payload = reference_input(15)
    before = payload["representations"]["before"]
    entity = deepcopy(payload["representations"]["after"]["entities"][1])
    entity.update(entity_id="b_bela", anchor_ids=["anchor_before"])
    before["entities"].append(entity)
    helper = deepcopy(next(row for row in payload["representations"]["after"]["relations"]
                           if row["relation_id"] == "a_addition"))
    helper.update(relation_id="b_unused_win", expression=atom("before", "bela", "win"),
                  anchor_ids=["anchor_before"])
    before["relations"].append(helper)
    mapping = deepcopy(next(row for row in payload["correspondence"] if row["kind"] == "relation"))
    mapping.update(correspondence_id="map_unasserted", before_ids=["b_unused_win"], after_ids=["a_addition"])
    payload["correspondence"].append(mapping)
    variant = payload["interpretations"]["variants"][0]
    variant["correspondence_ids"].append("map_unasserted")
    assert "b_unused_win" not in variant["before_relation_ids"]
    report = measured(tmp_path, payload)
    assert result_for(report)["relation_state"] == "PRESERVED"
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["novelty"] == "new_content"
    assert addition["evidence_status"] == "unsupported"
    assert addition["derivation_ref"] is None


def test_existing_entailment_is_an_explicitization_with_its_own_derivation(tmp_path):
    report = measured(tmp_path, reference_input(16))
    addition, = [row for row in report["introduced_relations"] if row["relation_id"] == "a_addition"]
    assert addition["novelty"] == "derived_explicitization"
    assert addition["evidence_status"] == "supported"
    witness, = [row for row in report["witnesses"] if row["witness_id"] == addition["derivation_ref"]]
    assert set(witness["premise_refs"]) >= {"b_fact", "b_rule"}
    assert "LOGIC_01" in witness["rule_refs"]


def test_incomplete_original_coverage_cannot_prove_a_new_semantic_addition(tmp_path):
    payload = reference_input(15)
    payload["coverage_obligations"][0].update(state="missing", reason="Original scope is incomplete.")
    report = measured(tmp_path, payload)
    assert result_for(report)["relation_state"] == "UNDETERMINED"
    assert all(row["novelty"] == "unresolved" for row in report["introduced_relations"])


def test_more_than_profile_variant_limit_is_rejected_before_measurement(tmp_path):
    payload = reference_input()
    original = payload["interpretations"]["variants"][0]
    payload["interpretations"]["variants"] = [dict(original, variant_id=f"variant_{i}") for i in range(65)]
    with pytest.raises(InputError):
        measure_input(save_input(tmp_path, payload))


def test_strict_loader_rejects_duplicate_keys_at_measurement_entrypoint(tmp_path):
    raw = encoded(reference_input())
    path = tmp_path / "input.json"
    path.write_bytes(b'{"case_id":"hidden",' + raw[1:])
    with pytest.raises(InputError):
        measure_input(path)


@pytest.mark.parametrize("number", (1, 2, 3, 5, 8, 12, 14, 15, 16, 17, 18))
def test_independent_reference_review_accepts_only_its_explicit_scope(tmp_path, number):
    fixture = accepted_fixture(tmp_path, reference_input(number))
    report = measure_accepted(fixture)
    expectation = next(row for row in EXPECTED if row["case_id"] == fixture["payload"]["case_id"])
    for expected in expectation["target_expectations"]:
        result = result_for(report, expected["target_id"])
        assert result["relation_state"] == expected["relation_state"]
        assert result["assessment_state"] == expected["assessment_state"]
        assert result["representation_basis"] == "accepted_reference", report
        assert result["claim_scope"] == "reference_interpretation"


def test_profile_verified_source_does_not_upgrade_reference_identity_review(tmp_path):
    fixture = accepted_fixture(tmp_path, source_basis="profile_verified")
    result = result_for(measure_accepted(fixture))
    assert result["relation_state"] == "PRESERVED"
    assert result["representation_basis"] == "accepted_reference"
    assert result["claim_scope"] == "reference_interpretation"


@pytest.mark.parametrize("missing", ("trust_config", "comparison_trust_config"))
def test_reference_scope_requires_both_source_and_comparison_evidence(tmp_path, missing):
    fixture = accepted_fixture(tmp_path)
    result = result_for(measure_accepted(fixture, **{missing: None}))
    assert result["representation_basis"] == "candidate_only"
    assert result["claim_scope"] == "candidate_structures"


def test_comparison_review_cannot_promote_a_submitted_candidate_correspondence(tmp_path):
    fixture = accepted_fixture(tmp_path)
    fixture["payload"]["correspondence"][0].update(basis="candidate", rule_or_reference_id=None)
    write_source_acceptance(fixture)
    write_comparison_reviews(fixture, refresh=True)
    assert review_outcome(fixture)["result"] == "unresolved"
    result = result_for(measure_accepted(fixture))
    assert result["representation_basis"] == "candidate_only"
    assert result["claim_scope"] == "candidate_structures"


def test_comparison_evidence_pins_exact_independently_configured_bytes(tmp_path):
    fixture = accepted_fixture(tmp_path)
    result = review_outcome(fixture)
    assert result["result"] == "pass"
    assert result["basis"] == "accepted_reference"
    assert "comparison-trust.sha256:" + digest(fixture["comparison_config"].read_bytes()) in result["evidence_refs"]
    raw = (fixture["comparison_config"].parent / "review_0.json").read_bytes()
    assert "sha256:" + digest(raw) in result["evidence_refs"]
    assert result["family_checked"] and result["context_checked"]
    assert set(result["closed_obligation_ids"]) == set(
        fixture["payload"]["measurement_request"]["targets"][0]["required_obligation_ids"])


@pytest.mark.parametrize("mutation, expected_result", (
    ("input_hash", "fail"), ("input_identity", "fail"), ("profile_hash", "fail"),
    ("reference_identity", "fail"), ("coverage_scope", "fail"),
    ("family_state", "fail"), ("family_members", "fail"),
    ("correspondence_absent", "unresolved"), ("coverage_absent", "unresolved"),
    ("not_run", "unresolved"), ("failed", "fail"), ("unresolved", "unresolved"),
))
def test_incomplete_or_mismatched_comparison_review_never_accepts_scope(tmp_path, mutation, expected_result):
    fixture = accepted_fixture(tmp_path)
    review = fixture["reviews"][0]
    if mutation == "input_hash":
        review["input_ref"]["content_sha256"] = "0" * 64
    elif mutation == "input_identity":
        review["input_ref"]["artifact_id"] = "unrelated_input"
    elif mutation == "profile_hash":
        review["profile_ref"]["content_sha256"] = "0" * 64
    elif mutation == "reference_identity":
        review["correspondence_checks"][0]["reference_id"] = "different_reference"
    elif mutation == "coverage_scope":
        review["coverage_checks"][0]["source_ids"] = ["source_before"]
    elif mutation == "family_state":
        review["family_check"]["family_state"] = "truncated"
    elif mutation == "family_members":
        review["reviewed_variant_ids"] = []
    elif mutation == "correspondence_absent":
        review["correspondence_checks"].pop(0)
    elif mutation == "coverage_absent":
        review["coverage_checks"].pop(0)
    else:
        review["family_check"].update(
            status="not_run" if mutation == "not_run" else "completed",
            result=None if mutation == "not_run" else "fail" if mutation == "failed" else "unresolved",
            reason="Synthetic unfinished or rejected reference review.")
    write_comparison_reviews(fixture)
    assert review_outcome(fixture)["result"] == expected_result
    result = result_for(measure_accepted(fixture))
    assert result["representation_basis"] == "candidate_only"
    assert result["claim_scope"] == "candidate_structures"


@pytest.mark.parametrize("mutation", ("missing", "unnamed_review"))
def test_external_review_does_not_overwrite_submitted_coverage_boundary(tmp_path, mutation):
    fixture = accepted_fixture(tmp_path)
    obligation = fixture["payload"]["coverage_obligations"][0]
    if mutation == "missing":
        obligation.update(state="missing", reason="The submitted scope remains incomplete.")
    else:
        obligation["evidence_refs"] = []
    write_source_acceptance(fixture)
    write_comparison_reviews(fixture, refresh=True)
    assert review_outcome(fixture)["result"] == "unresolved"
    assert result_for(measure_accepted(fixture))["representation_basis"] == "candidate_only"


@pytest.mark.parametrize("rejected", ("correspondence_checks", "coverage_checks", "context_check", "family_check"))
def test_explicit_rejection_of_a_required_comparison_premise_blocks_identification(tmp_path, rejected):
    fixture = accepted_fixture(tmp_path)
    check = fixture["reviews"][0][rejected]
    if isinstance(check, list):
        check = check[0]
    check.update(status="completed", result="fail",
                 reason="Independent reviewer rejected the exact declared premise.")
    write_comparison_reviews(fixture)
    assert review_outcome(fixture)["result"] == "fail"
    result = result_for(measure_accepted(fixture))
    assert result["relation_state"] == "UNDETERMINED"
    assert result["assessment_state"] != "IDENTIFIED"
    if rejected == "coverage_checks":
        assert check["obligation_id"] not in result["closed_obligation_ids"]


@pytest.mark.parametrize("independently_reviewed", (False, True))
def test_context_coverage_needs_an_actual_context_check_not_a_named_certificate(tmp_path, independently_reviewed):
    payload = reference_input(11)
    payload["coverage_obligations"][0].update(kind="context", side="context",
        source_ids=["source_context"], evidence_refs=["never_loaded_context_certificate"])
    if independently_reviewed:
        report = measure_accepted(accepted_fixture(tmp_path, payload))
        result = result_for(report)
        assert result["relation_state"] == "CHANGED"
        assert result["assessment_state"] == "IDENTIFIED"
        assert result["representation_basis"] == "accepted_reference"
        assert result["closed_obligation_ids"] == ["coverage_main"]
    else:
        result = result_for(measured(tmp_path, payload))
        assert result["relation_state"] == "UNDETERMINED"
        assert result["assessment_state"] != "IDENTIFIED"
        assert "coverage_main" not in result["closed_obligation_ids"]


def test_stale_comparison_subject_cannot_follow_rebound_source_evidence(tmp_path):
    fixture = accepted_fixture(tmp_path)
    fixture["payload"]["case_id"] = "a_new_measurement_subject"
    write_source_acceptance(fixture)
    assert review_outcome(fixture)["result"] == "fail"
    assert result_for(measure_accepted(fixture))["representation_basis"] == "candidate_only"


def test_equal_json_value_with_changed_review_bytes_breaks_external_digest(tmp_path):
    fixture = accepted_fixture(tmp_path)
    path = fixture["comparison_config"].parent / "review_0.json"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(InputError):
        measure_accepted(fixture)


@pytest.mark.parametrize("location", ("config_in_package", "symlink_config", "symlink_payload"))
def test_comparison_trust_is_external_and_does_not_follow_links(tmp_path, location):
    fixture = accepted_fixture(tmp_path)
    if location == "config_in_package":
        copied = fixture["package"] / "comparison.json"
        copied.write_bytes(fixture["comparison_config"].read_bytes())
        fixture["comparison_config"] = copied
    elif location == "symlink_config":
        link = fixture["comparison_config"].parent / "linked_config.json"
        link.symlink_to(fixture["comparison_config"])
        fixture["comparison_config"] = link
    else:
        path = fixture["comparison_config"].parent / "review_0.json"
        other = fixture["comparison_config"].parent / "original_review.json"
        path.rename(other)
        path.symlink_to(other)
    with pytest.raises(InputError):
        measure_accepted(fixture)


@pytest.mark.parametrize("mutation", ("duplicate_path", "duplicate_review", "duplicate_subject", "duplicate_check"))
def test_comparison_trust_rejects_ambiguous_duplicate_evidence(tmp_path, mutation):
    fixture = accepted_fixture(tmp_path)
    if mutation == "duplicate_path":
        config = json.loads(fixture["comparison_config"].read_bytes())
        config["review_files"].append(deepcopy(config["review_files"][0]))
        fixture["comparison_config"].write_bytes(encoded(config))
    elif mutation in {"duplicate_review", "duplicate_subject"}:
        repeated = deepcopy(fixture["reviews"][0])
        if mutation == "duplicate_subject":
            repeated["verification_id"] = "second_review_of_same_subject"
        fixture["reviews"].append(repeated)
        write_comparison_reviews(fixture)
    else:
        fixture["reviews"][0]["context_check"]["check_id"] = fixture["reviews"][0]["family_check"]["check_id"]
        write_comparison_reviews(fixture)
    with pytest.raises(InputError):
        measure_accepted(fixture)


def add_entity_context(payload: dict) -> str:
    raw = b"Synthetic context used only through a selected entity anchor."
    payload["sources"].append({"source_id": "context_entity", "role": "context", "language": "en",
        "encoding": "utf-8", "revision": None,
        "content": {"kind": "inline_utf8", "text": raw.decode()},
        "byte_length": len(raw), "content_sha256": digest(raw)})
    payload["source_anchors"].append({"anchor_id": "context_entity_anchor", "source_id": "context_entity",
        "start_byte": 0, "end_byte": len(raw), "content_sha256": digest(raw)})
    payload["representations"]["before"]["entities"][0]["anchor_ids"].append("context_entity_anchor")
    return "context_entity"


def test_used_entity_context_requires_its_own_review_even_without_target_or_obligation_context(tmp_path):
    payload = reference_input()
    context_id = add_entity_context(payload)
    fixture = accepted_fixture(tmp_path, payload)
    review = fixture["reviews"][0]
    assert not review["context_check"]["context_source_ids"]
    assert review_outcome(fixture)["result"] == "fail"
    assert not review_outcome(fixture)["context_checked"]
    assert result_for(measure_accepted(fixture))["representation_basis"] == "candidate_only"
    review["context_check"]["context_source_ids"] = [context_id]
    write_comparison_reviews(fixture)
    assert review_outcome(fixture)["result"] == "pass"
    assert result_for(measure_accepted(fixture))["representation_basis"] == "accepted_reference"


def test_joint_family_review_cannot_be_reduced_to_one_favorable_variant(tmp_path):
    fixture = accepted_fixture(tmp_path, reference_input(18))
    store = ComparisonTrust.load(fixture["comparison_config"], fixture["package"])
    with pytest.raises(InputError):
        store.target_review(fixture["payload"], fixture["reviews"][0]["input_ref"], "target_main",
            correspondence_ids=[row["correspondence_id"] for row in fixture["payload"]["correspondence"]],
            variant_ids=[fixture["payload"]["interpretations"]["variants"][0]["variant_id"]])


@pytest.mark.parametrize("support", ("absent", "empty", "named"))
def test_addition_support_requires_a_separate_named_independent_check(tmp_path, support):
    fixture = accepted_fixture(tmp_path, reference_input(15))
    if support != "absent":
        fixture["reviews"][0]["addition_checks"] = [completed_check("checked_new_assertion",
            relation_id="a_addition", evidence_refs=[] if support == "empty" else ["synthetic_new_assertion_evidence"])]
        write_comparison_reviews(fixture)
    if support == "empty":
        with pytest.raises(InputError):
            measure_accepted(fixture)
        return
    report = measure_accepted(fixture)
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    if support == "named":
        assert addition["novelty"] == "externally_supported"
        assert addition["evidence_status"] == "supported"
        assert "synthetic_new_assertion_evidence" in addition["evidence_refs"]
    else:
        assert addition["novelty"] == "new_content"
        assert addition["evidence_status"] == "unsupported"


@pytest.mark.parametrize("context_reviewed", (False, True))
def test_added_fact_context_must_be_reviewed_separately_from_unchanged_target(tmp_path, context_reviewed):
    payload = reference_input(15)
    raw = b"Synthetic qualification used only by the added assertion."
    payload["sources"].append({"source_id": "addition_context", "role": "context", "language": "en",
        "encoding": "utf-8", "revision": None, "content": {"kind": "inline_utf8", "text": raw.decode()},
        "byte_length": len(raw), "content_sha256": digest(raw)})
    payload["source_anchors"].append({"anchor_id": "addition_context_anchor", "source_id": "addition_context",
        "start_byte": 0, "end_byte": len(raw), "content_sha256": digest(raw)})
    addition = next(row for row in payload["representations"]["after"]["relations"]
                    if row["relation_id"] == "a_addition")
    addition["anchor_ids"].append("addition_context_anchor")
    fixture = accepted_fixture(tmp_path, payload)
    review = fixture["reviews"][0]
    assert review["context_check"]["context_source_ids"] == []
    review["addition_checks"] = [completed_check("checked_new_assertion", relation_id="a_addition",
        evidence_refs=["synthetic_new_assertion_evidence"])]
    if context_reviewed:
        review["context_check"]["context_source_ids"] = ["addition_context"]
    write_comparison_reviews(fixture)
    report = measure_accepted(fixture)
    target = result_for(report)
    assert target["relation_state"] == "PRESERVED"
    assert target["assessment_state"] == "IDENTIFIED"
    assert target["representation_basis"] == "accepted_reference"
    result = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    if context_reviewed:
        assert result["novelty"] == "externally_supported"
        assert result["evidence_status"] == "supported"
        assert "synthetic_new_assertion_evidence" in result["evidence_refs"]
    else:
        assert result["novelty"] == "unresolved"
        assert result["evidence_status"] == "unresolved"
        assert result["derivation_ref"] is None


def test_input_replaced_during_source_verification_cannot_receive_old_evidence(tmp_path, monkeypatch):
    import tools.language_relation_v0.comparator as comparator

    payload = reference_input()
    path = save_input(tmp_path, payload)
    actual_verify = comparator.verify_input

    def replace_after_verifying(*args, **kwargs):
        verified = actual_verify(*args, **kwargs)
        changed = deepcopy(payload)
        changed["case_id"] = "changed_after_verifier_read"
        path.write_bytes(encoded(changed))
        return verified

    monkeypatch.setattr(comparator, "verify_input", replace_after_verifying)
    with pytest.raises(InputError):
        comparator.measure_input(path)


@pytest.mark.parametrize("wrapper", ("NOT", "OR", "IMPLIES", "quotation"))
def test_embedded_only_relation_cannot_lose_its_enclosing_condition(tmp_path, wrapper):
    payload = reference_input()
    representation = payload["representations"]["before"]
    container = deepcopy(representation["relations"][0])
    container["relation_id"] = "b_container"
    reference = {"op": "REF", "relation_id": "b_main"}
    if wrapper == "NOT":
        container["expression"] = {"op": "NOT", "operand": reference}
    elif wrapper == "OR":
        container["expression"] = {"op": "OR", "operands": [reference, atom("before")]}
    elif wrapper == "IMPLIES":
        container["expression"] = {"op": "IMPLIES", "antecedent": reference, "consequent": atom("before")}
    else:
        container.update(expression=reference, discourse_type="quotation", speaker_entity_id="b_anna")
    representation["relations"].append(container)
    payload["interpretations"]["variants"][0]["before_relation_ids"] = ["b_container"]
    replace_source(payload, "before", "A synthetic reference supplies an explicitly qualified assertion.")
    fixture = accepted_fixture(tmp_path, payload)
    result = result_for(measure_accepted(fixture))
    assert result["relation_state"] == "UNDETERMINED"
    assert result["assessment_state"] != "IDENTIFIED"


def test_unrelated_target_incompleteness_does_not_leak_into_closed_target(tmp_path):
    payload = reference_input()
    target = deepcopy(payload["measurement_request"]["targets"][0])
    target.update(target_id="target_auxiliary", before_ids=["b_auxiliary"], after_ids=["a_auxiliary"],
                  required_obligation_ids=["coverage_auxiliary"])
    payload["measurement_request"]["targets"].append(target)
    obligation = deepcopy(payload["coverage_obligations"][0])
    obligation.update(obligation_id="coverage_auxiliary", target_id="target_auxiliary")
    payload["coverage_obligations"].append(obligation)
    for side in ("before", "after"):
        relation = deepcopy(payload["representations"][side]["relations"][0])
        relation["relation_id"] = side[0] + "_auxiliary"
        payload["representations"][side]["relations"].append(relation)
    fixture = accepted_fixture(tmp_path, payload)
    report = measure_accepted(fixture)
    main = result_for(report)
    assert main["relation_state"] == "PRESERVED"
    assert main["assessment_state"] == "IDENTIFIED"
    assert main["representation_basis"] == "accepted_reference"
    assert result_for(report, "target_auxiliary")["relation_state"] == "UNDETERMINED"
    assert result_for(report, "target_auxiliary")["assessment_state"] != "IDENTIFIED"


@pytest.mark.parametrize("proposition_identity_bound", (False, True))
def test_proposition_valued_arguments_need_explicit_proposition_identity(tmp_path, proposition_identity_bound):
    payload = reference_input()
    for side in ("before", "after"):
        prefix = side[0]
        representation = payload["representations"][side]
        proposition = deepcopy(representation["relations"][0])
        proposition["relation_id"] = prefix + "_proposition"
        representation["relations"].append(proposition)
        representation["relations"][0]["expression"] = {
            "op": "ATOM", "predicate": "notify", "arguments": [
                {"role": "sender", "value": {"entity_id": prefix + "_anna"}},
                {"role": "recipient", "value": {"entity_id": prefix + "_anna"}},
                {"role": "content", "value": {"relation_id": prefix + "_proposition"}}]}
        replace_source(payload, side, "Anna notifies herself of the explicitly referenced proposition.")
    if proposition_identity_bound:
        mapping = deepcopy(payload["correspondence"][1])
        mapping.update(correspondence_id="map_proposition", before_ids=["b_proposition"], after_ids=["a_proposition"])
        payload["correspondence"].append(mapping)
        payload["interpretations"]["variants"][0]["correspondence_ids"].append("map_proposition")
    logic = VariantLogic(payload, PROFILE, payload["interpretations"]["variants"][0])
    missing = logic.missing_identity(["b_main"], ["a_main"])
    if proposition_identity_bound:
        assert missing == []
    else:
        assert {row["relation_id"] for row in missing} == {"b_proposition", "a_proposition"}
    result = result_for(measure_accepted(accepted_fixture(tmp_path, payload)))
    if proposition_identity_bound:
        assert result["relation_state"] == "PRESERVED"
        assert result["assessment_state"] == "IDENTIFIED"
        assert result["representation_basis"] == "accepted_reference"
    else:
        assert result["relation_state"] == "UNDETERMINED"
        assert result["assessment_state"] != "IDENTIFIED"


def test_common_context_does_not_activate_an_unrelated_ambiguous_mapping(tmp_path):
    payload = reference_input()
    variant = payload["interpretations"]["variants"][0]
    variant["context_constraints"] = [{"op": "REF", "relation_id": "b_main"}]
    for side, people in (("before", ("bela",)), ("after", ("bela", "eva"))):
        for person in people:
            entity = deepcopy(payload["representations"][side]["entities"][0])
            entity.update(entity_id=side[0] + "_" + person, label=person)
            payload["representations"][side]["entities"].append(entity)
    mapping = deepcopy(payload["correspondence"][0])
    mapping.update(correspondence_id="map_irrelevant", before_ids=["b_bela"], after_ids=["a_bela", "a_eva"])
    payload["correspondence"].append(mapping)
    variant["correspondence_ids"].append("map_irrelevant")
    result = result_for(measure_accepted(accepted_fixture(tmp_path, payload)))
    assert result["relation_state"] == "PRESERVED"
    assert result["assessment_state"] == "IDENTIFIED"
    assert result["representation_basis"] == "accepted_reference"


def test_missing_identity_cannot_prove_relation_loss_or_new_content(tmp_path):
    payload = reference_input()
    payload["measurement_request"]["targets"][0]["after_ids"] = []
    payload["correspondence"] = []
    payload["interpretations"]["variants"][0]["correspondence_ids"] = []
    report = measured(tmp_path, payload)
    assert result_for(report)["relation_state"] == "UNDETERMINED"
    assert result_for(report)["assessment_state"] != "IDENTIFIED"
    assert report["introduced_relations"]
    assert all(row["novelty"] == "unresolved" for row in report["introduced_relations"])


def test_absence_search_cannot_lose_joint_continuation_when_sentence_split(tmp_path):
    payload = reference_input(12)
    payload["measurement_request"]["targets"][0]["after_ids"] = []
    result = result_for(measured(tmp_path, payload))
    assert result["relation_state"] != "BROKEN"
    assert result["relation_state"] in {"PRESERVED", "UNDETERMINED"}


def test_absence_search_respects_boolean_equivalence_for_condition_target(tmp_path):
    payload = reference_input(8)
    payload["measurement_request"]["targets"][0]["after_ids"] = []
    payload["correspondence"] = [row for row in payload["correspondence"] if row["kind"] == "entity"]
    retained = {row["correspondence_id"] for row in payload["correspondence"]}
    for variant in payload["interpretations"]["variants"]:
        variant["correspondence_ids"] = [identifier for identifier in variant["correspondence_ids"] if identifier in retained]
    result = result_for(measured(tmp_path, payload))
    assert result["relation_state"] != "BROKEN"
    assert result["relation_state"] in {"PRESERVED", "UNDETERMINED"}


def test_partial_mapping_does_not_accept_a_complete_selected_relation_group(tmp_path):
    payload = reference_input(12)
    group_map = next(row for row in payload["correspondence"] if row["correspondence_id"] == "map_group")
    group_map.update(kind="relation", before_ids=["b_joint"], after_ids=["a_anna"])
    result = result_for(measured(tmp_path, payload))
    assert result["relation_state"] == "UNDETERMINED"
    assert result["assessment_state"] != "IDENTIFIED"


def test_accepted_target_does_not_accept_unreviewed_identity_used_only_by_added_fact(tmp_path):
    payload = reference_input(16)
    payload["measurement_request"]["targets"][0].update(before_ids=["b_fact"], after_ids=["a_fact"])
    fixture = accepted_fixture(tmp_path, payload)
    identity = next(row for row in fixture["payload"]["correspondence"]
                    if row["correspondence_id"] == "map_entity_bela")
    identity.update(basis="candidate", rule_or_reference_id=None)
    write_source_acceptance(fixture)
    write_comparison_reviews(fixture, refresh=True)
    report = measure_accepted(fixture)
    target = result_for(report)
    assert target["relation_state"] == "PRESERVED"
    assert target["assessment_state"] == "IDENTIFIED"
    assert target["representation_basis"] == "accepted_reference"
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["novelty"] == "unresolved"
    assert addition["evidence_status"] == "unresolved"
    assert addition["derivation_ref"] is None


@pytest.mark.parametrize("identity_basis", ("absent", "candidate", "accepted_reference"))
def test_added_expression_needs_its_own_cross_source_identity(tmp_path, identity_basis):
    payload = reference_input(15)
    before = payload["representations"]["before"]
    entity = deepcopy(payload["representations"]["after"]["entities"][1])
    entity.update(entity_id="b_bela", anchor_ids=["anchor_before"])
    before["entities"].append(entity)
    existing = deepcopy(before["relations"][0])
    existing.update(relation_id="b_existing_win", expression=atom("before", "bela", "win"))
    before["relations"].append(existing)
    payload["interpretations"]["variants"][0]["before_relation_ids"].append("b_existing_win")
    for side in ("before", "after"):
        replace_source(payload, side, "Anna approves. Béla wins.")
    if identity_basis != "absent":
        identity = deepcopy(payload["correspondence"][0])
        identity.update(correspondence_id="map_entity_bela", before_ids=["b_bela"], after_ids=["a_bela"])
        payload["correspondence"].append(identity)
        payload["interpretations"]["variants"][0]["correspondence_ids"].append("map_entity_bela")
    fixture = accepted_fixture(tmp_path, payload)
    if identity_basis == "candidate":
        identity = next(row for row in fixture["payload"]["correspondence"]
                        if row["correspondence_id"] == "map_entity_bela")
        identity.update(basis="candidate", rule_or_reference_id=None)
        write_source_acceptance(fixture)
        write_comparison_reviews(fixture, refresh=True)
    report = measure_accepted(fixture)
    target = result_for(report)
    assert target["relation_state"] == "PRESERVED"
    assert target["representation_basis"] == "accepted_reference"
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    if identity_basis == "accepted_reference":
        assert addition["novelty"] == "new_expression"
        assert addition["evidence_status"] == "supported"
    else:
        assert addition["novelty"] == "unresolved"
        assert addition["evidence_status"] == "unresolved"
        assert addition["derivation_ref"] is None


def test_inconsistent_original_premises_do_not_prove_arbitrary_additions(tmp_path):
    payload = reference_input(16)
    representation = payload["representations"]["before"]
    contradiction = deepcopy(representation["relations"][0])
    contradiction.update(relation_id="b_contradiction", expression={"op": "NOT",
        "operand": {"op": "REF", "relation_id": "b_fact"}})
    representation["relations"].append(contradiction)
    payload["interpretations"]["variants"][0]["before_relation_ids"].append("b_contradiction")
    report = measured(tmp_path, payload)
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["novelty"] == "unresolved"
    assert addition["evidence_status"] == "unresolved"
    assert addition["derivation_ref"] is None


@pytest.mark.parametrize("mutation", ("unknown", "incomplete", "duplicate", "contradictory_alias", "non_boolean"))
def test_serialized_counterexample_is_rechecked_against_ground_aliases(mutation):
    payload = reference_input(5)
    ground_helpers(payload)
    logic = VariantLogic(payload, PROFILE, payload["interpretations"]["variants"][0])
    target = payload["measurement_request"]["targets"][0]
    valuation = [{"atom_id": "b_atom_anna", "value": True},
                 {"atom_id": "b_atom_bela", "value": False}]
    valid = logic.check_valuation(target["before_ids"], target["after_ids"], valuation)
    assert valid == {"before_value": False, "after_value": True, "different": True}
    if mutation == "unknown":
        valuation[0]["atom_id"] = "invented_atom"
    elif mutation == "incomplete":
        valuation.pop()
    elif mutation == "duplicate":
        valuation.append(deepcopy(valuation[0]))
    elif mutation == "contradictory_alias":
        valuation.append({"atom_id": "a_atom_anna", "value": False})
    else:
        valuation[0]["value"] = 1
    with pytest.raises(LogicProblem):
        logic.check_valuation(target["before_ids"], target["after_ids"], valuation)


def invoke_cli(input_path: Path, output_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), "--input", str(input_path),
        "--output-dir", str(output_dir), *extra], cwd=ROOT, text=True, capture_output=True, check=False)


def test_cli_publishes_schema_valid_pair_with_exact_verification_digest(tmp_path):
    payload = reference_input(5)
    output = tmp_path / "measurement"
    completed = invoke_cli(save_input(tmp_path, payload), output)
    assert completed.returncode == 0, completed.stderr
    assert {path.name for path in output.iterdir()} == {"measurement.json", "verification.json"}
    report = json.loads((output / "measurement.json").read_bytes())
    verification_raw = (output / "verification.json").read_bytes()
    verification = json.loads(verification_raw)
    assert_measurement_integrity(report, payload)
    jsonschema.Draft202012Validator(VERIFICATION_SCHEMA).validate(verification)
    assert report["verification_refs"] == [{"artifact_id": verification["verification_id"],
                                            "content_sha256": digest(verification_raw)}]
    assert "authority_effect=none" in completed.stdout


@pytest.mark.parametrize("number", (13, 19, 20, 21))
def test_cli_diagnostic_completion_does_not_mean_resolved_target(tmp_path, number):
    payload = reference_input(number)
    output = tmp_path / "unresolved"
    completed = invoke_cli(save_input(tmp_path, payload), output)
    assert completed.returncode == 0, completed.stderr
    report = json.loads((output / "measurement.json").read_bytes())
    assert result_for(report)["assessment_state"] != "IDENTIFIED"
    assert result_for(report)["relation_state"] == "UNDETERMINED"


def test_cli_does_not_overwrite_an_existing_output_directory(tmp_path):
    path = save_input(tmp_path, reference_input())
    output = tmp_path / "already_exists"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("preserve exact owner file", encoding="utf-8")
    completed = invoke_cli(path, output)
    assert completed.returncode == 2
    assert {row.name for row in output.iterdir()} == {"keep.txt"}
    assert sentinel.read_text(encoding="utf-8") == "preserve exact owner file"


def test_cli_invalid_input_publishes_no_partial_artifact(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text('{"case_id": "x", "case_id": "y"}', encoding="utf-8")
    output = tmp_path / "must_not_exist"
    assert invoke_cli(path, output).returncode == 2
    assert not output.exists()


def test_comparator_module_is_registered_once_and_keeps_existing_tests():
    for name, expected_count in (("tools-tests.list", 177), ("pytest-tests.list", 33)):
        entries = [line for raw in (ROOT / "ci" / name).read_text().splitlines()
                   if (line := raw.split("#", 1)[0].strip())]
        assert len(entries) == len(set(entries)) == expected_count
        assert entries.count(SELF) == 1
        for existing in ("tests/test_language_relation_contract_v0.py",
                         "tests/test_language_relation_input_verifier_v0.py",
                         "tests/test_anchor_integrity_v0_1_contract.py",
                         "tests/test_paradox_w1_records_v0.py", "tests/test_paradox_w1_native_v0.py"):
            assert entries.count(existing) == 1


@pytest.mark.parametrize("premise_kind", ("correspondence", "coverage"))
def test_pr2995_exact_rejection_survives_candidate_scope_fallback(tmp_path, premise_kind):
    fixture = accepted_fixture(tmp_path)
    if premise_kind == "correspondence":
        item = next(row for row in fixture["payload"]["correspondence"] if row["kind"] == "entity")
        item.update(basis="candidate", rule_or_reference_id=None)
        check = next(row for row in fixture["reviews"][0]["correspondence_checks"]
                     if row["correspondence_id"] == item["correspondence_id"])
    else:
        check = fixture["reviews"][0]["coverage_checks"][0]
    for obligation in fixture["payload"]["coverage_obligations"]:
        obligation["evidence_refs"] = []
    check.update(status="completed", result="fail",
                 reason="Independent review rejected this exact required premise.")
    write_source_acceptance(fixture)
    write_comparison_reviews(fixture, refresh=True)

    outcome = review_outcome(fixture)
    assert outcome["result"] == "fail"
    assert check["check_id"] in outcome["evidence_refs"]
    report = measure_accepted(fixture)
    target = result_for(report)
    assert target["relation_state"] == "UNDETERMINED"
    assert target["assessment_state"] == "UNRESOLVED"
    assert target["closed_obligation_ids"] == []
    assert report["status_axes"]["consistency_status"] == "conflicting"


@pytest.mark.parametrize("premise_kind", ("correspondence", "coverage"))
@pytest.mark.parametrize("check_state", ("absent", "not_run"))
def test_pr2995_unperformed_review_keeps_conditional_candidate_scope(tmp_path, premise_kind, check_state):
    fixture = accepted_fixture(tmp_path)
    if premise_kind == "correspondence":
        item = next(row for row in fixture["payload"]["correspondence"] if row["kind"] == "entity")
        item.update(basis="candidate", rule_or_reference_id=None)
        checks = fixture["reviews"][0]["correspondence_checks"]
        check = next(row for row in checks if row["correspondence_id"] == item["correspondence_id"])
    else:
        checks = fixture["reviews"][0]["coverage_checks"]
        check = checks[0]
    for obligation in fixture["payload"]["coverage_obligations"]:
        obligation["evidence_refs"] = []
    if check_state == "absent":
        checks.remove(check)
    else:
        check.update(status="not_run", result=None, reason="This independent check was not performed.")
    write_source_acceptance(fixture)
    write_comparison_reviews(fixture, refresh=True)

    assert review_outcome(fixture)["result"] == "unresolved"
    report = measure_accepted(fixture)
    target = result_for(report)
    assert target["relation_state"] == "PRESERVED"
    assert target["assessment_state"] == "IDENTIFIED"
    assert target["representation_basis"] == "candidate_only"
    assert target["claim_scope"] == "candidate_structures"
    assert target["closed_obligation_ids"] == ["coverage_main"]


def test_pr2995_rejected_unused_identity_does_not_poison_an_independent_target(tmp_path):
    payload = reference_input(16)
    payload["measurement_request"]["targets"][0].update(before_ids=["b_fact"], after_ids=["a_fact"])
    fixture = accepted_fixture(tmp_path, payload)
    item = next(row for row in fixture["payload"]["correspondence"]
                if row["correspondence_id"] == "map_entity_bela")
    item.update(basis="candidate", rule_or_reference_id=None)
    check = next(row for row in fixture["reviews"][0]["correspondence_checks"]
                 if row["correspondence_id"] == item["correspondence_id"])
    check.update(status="completed", result="fail", reason="This separate identity was rejected.")
    write_source_acceptance(fixture)
    write_comparison_reviews(fixture, refresh=True)

    report = measure_accepted(fixture)
    target = result_for(report)
    assert target["relation_state"] == "PRESERVED"
    assert target["assessment_state"] == "IDENTIFIED"
    assert target["representation_basis"] == "accepted_reference"
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["novelty"] == "unresolved"
    assert addition["derivation_ref"] is None


def test_pr2995_rejected_coverage_is_local_to_its_exact_target(tmp_path):
    payload = reference_input()
    auxiliary = deepcopy(payload["measurement_request"]["targets"][0])
    auxiliary.update(target_id="target_auxiliary", required_obligation_ids=["coverage_auxiliary"])
    payload["measurement_request"]["targets"].append(auxiliary)
    obligation = deepcopy(payload["coverage_obligations"][0])
    obligation.update(obligation_id="coverage_auxiliary", target_id="target_auxiliary")
    payload["coverage_obligations"].append(obligation)
    fixture = accepted_fixture(tmp_path, payload)
    required = next(row for row in fixture["payload"]["coverage_obligations"]
                    if row["obligation_id"] == "coverage_auxiliary")
    required["evidence_refs"] = []
    review = next(row for row in fixture["reviews"] if row["target_id"] == "target_auxiliary")
    review["coverage_checks"][0].update(status="completed", result="fail",
        reason="Only the auxiliary target's exact coverage was rejected.")
    write_source_acceptance(fixture)
    write_comparison_reviews(fixture, refresh=True)

    report = measure_accepted(fixture)
    target = result_for(report)
    assert target["relation_state"] == "PRESERVED"
    assert target["assessment_state"] == "IDENTIFIED"
    assert target["representation_basis"] == "accepted_reference"
    auxiliary_result = result_for(report, "target_auxiliary")
    assert auxiliary_result["relation_state"] == "UNDETERMINED"
    assert auxiliary_result["assessment_state"] == "UNRESOLVED"
    assert auxiliary_result["closed_obligation_ids"] == []

def _pr2995_typed_addition_fixture(tmp_path, discourse="assertion", modality="permission", *, named_support=True):
    payload = reference_input(15)
    addition = next(row for row in payload["representations"]["after"]["relations"]
                    if row["relation_id"] == "a_addition")
    addition.update(discourse_type=discourse, modality=modality)
    fixture = accepted_fixture(tmp_path, payload)
    if named_support:
        fixture["reviews"][0]["addition_checks"] = [completed_check(
            "checked_typed_addition", relation_id="a_addition",
            evidence_refs=["synthetic_typed_addition_support"])]
        write_comparison_reviews(fixture)
    return fixture


@pytest.mark.parametrize("discourse,modality", (
    ("assertion", "permission"), ("assertion", "obligation"),
    ("quotation", "declarative"), ("supposition", "declarative"),
    ("assertion", "observed_event")))
@pytest.mark.parametrize("named_support", (False, True))
def test_typed_addition_resolves_own_support_without_boolean_derivation(
        tmp_path, discourse, modality, named_support):
    fixture = _pr2995_typed_addition_fixture(tmp_path, discourse, modality,
                                            named_support=named_support)
    report = measure_accepted(fixture)
    target = result_for(report)
    assert target["relation_state"] == "PRESERVED"
    assert target["assessment_state"] == "IDENTIFIED"
    assert target["representation_basis"] == "accepted_reference"
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["derivation_ref"] is None
    assert not any(row["kind"] == "derivation" for row in report["witnesses"])
    if named_support:
        assert addition["novelty"] == "externally_supported"
        assert addition["evidence_status"] == "supported"
        assert "synthetic_typed_addition_support" in addition["evidence_refs"]
        assert "checked_typed_addition" in addition["evidence_refs"]
    else:
        assert addition["novelty"] == "unresolved"
        assert addition["evidence_status"] == "unresolved"
        assert "Boolean derivation is unsupported" in addition["reason"]
    assert report["status_axes"]["causal_status"] == "not_evaluated"
    assert report["authority_effect"] == "none"
    assert report["release_authority_activation"] is False


@pytest.mark.parametrize("state", ("not_run", "fail"))
def test_typed_addition_requires_a_completed_passing_own_support_check(tmp_path, state):
    fixture = _pr2995_typed_addition_fixture(tmp_path)
    check = fixture["reviews"][0]["addition_checks"][0]
    check.update(status="not_run" if state == "not_run" else "completed",
                 result=None if state == "not_run" else "fail",
                 reason="Synthetic independent addition support was not established.")
    write_comparison_reviews(fixture)
    report = measure_accepted(fixture)
    assert result_for(report)["assessment_state"] == "IDENTIFIED"
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["novelty"] == "unresolved"
    assert addition["evidence_status"] == "unresolved"
    assert addition["derivation_ref"] is None


def test_typed_addition_support_does_not_promote_candidate_source_scope(tmp_path):
    fixture = _pr2995_typed_addition_fixture(tmp_path)
    report = measure_accepted(fixture, trust_config=None)
    target = result_for(report)
    assert target["representation_basis"] == "candidate_only"
    assert target["assessment_state"] == "IDENTIFIED"
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["novelty"] == "unresolved"
    assert addition["evidence_status"] == "unresolved"
    assert addition["derivation_ref"] is None


def test_typed_addition_support_cannot_bypass_its_own_context_review(tmp_path):
    fixture = _pr2995_typed_addition_fixture(tmp_path)
    payload = fixture["payload"]
    raw = b"Synthetic qualification used only by the added permission."
    payload["sources"].append({"source_id": "typed_addition_context", "role": "context", "language": "en",
        "encoding": "utf-8", "revision": None, "content": {"kind": "inline_utf8", "text": raw.decode()},
        "byte_length": len(raw), "content_sha256": digest(raw)})
    payload["source_anchors"].append({"anchor_id": "typed_addition_context_anchor",
        "source_id": "typed_addition_context", "start_byte": 0,
        "end_byte": len(raw), "content_sha256": digest(raw)})
    addition = next(row for row in payload["representations"]["after"]["relations"]
                    if row["relation_id"] == "a_addition")
    addition["anchor_ids"].append("typed_addition_context_anchor")
    write_source_acceptance(fixture)
    write_comparison_reviews(fixture, refresh=True)
    assert fixture["reviews"][0]["context_check"]["context_source_ids"] == []
    report = measure_accepted(fixture)
    assert result_for(report)["representation_basis"] == "accepted_reference"
    assert result_for(report)["assessment_state"] == "IDENTIFIED"
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["novelty"] == "unresolved"
    assert addition["evidence_status"] == "unresolved"
    assert addition["derivation_ref"] is None


def test_non_context_logic_failure_does_not_unlock_independent_addition_support(tmp_path, monkeypatch):
    fixture = _pr2995_typed_addition_fixture(tmp_path)

    def exhausted_scope(self, premise_ids, after_id):
        raise LogicProblem("expanded_atom_limit", "Synthetic finite derivation resource exhaustion.")

    monkeypatch.setattr(VariantLogic, "entailment", exhausted_scope)
    report = measure_accepted(fixture)
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["novelty"] == "unresolved"
    assert addition["evidence_status"] == "unresolved"
    assert addition["derivation_ref"] is None


def test_exact_typed_duplicate_does_not_claim_a_boolean_derivation_without_own_support(tmp_path):
    payload = reference_input()
    for side in ("before", "after"):
        payload["representations"][side]["relations"][0]["modality"] = "permission"
        replace_source(payload, side, "The synthetic reference records Anna's permission to approve.")
    addition = deepcopy(payload["representations"]["after"]["relations"][0])
    addition["relation_id"] = "a_addition"
    payload["representations"]["after"]["relations"].append(addition)
    payload["interpretations"]["variants"][0]["after_relation_ids"].append("a_addition")
    fixture = accepted_fixture(tmp_path, payload)
    report = measure_accepted(fixture)
    assert result_for(report)["relation_state"] == "PRESERVED"
    addition = next(row for row in report["introduced_relations"] if row["relation_id"] == "a_addition")
    assert addition["novelty"] == "unresolved"
    assert addition["evidence_status"] == "unresolved"
    assert addition["derivation_ref"] is None
    assert not any(row["kind"] == "derivation" for row in report["witnesses"])

def nested_relation_chain_payload(length: int, wrappers: int, *,
                                  reference_kind: str = "REF", mirror: bool = False) -> dict:
    """Keep each raw expression shallow while expanding a longer joint path."""
    payload = reference_input()
    for side in ("before", "after"):
        replace_source(payload, side, "Opaque nested relation fixture.")
    for side in ("before", "after") if mirror else ("before",):
        representation = payload["representations"][side]
        template = deepcopy(representation["relations"][0])
        prefix = side[0]
        relations = []
        for index in range(length):
            if index == length - 1:
                expression = deepcopy(template["expression"])
            elif reference_kind == "proposition":
                expression = {"op": "ATOM", "predicate": "notify", "arguments": [
                    {"role": "sender", "value": {"entity_id": prefix + "_anna"}},
                    {"role": "recipient", "value": {"entity_id": prefix + "_anna"}},
                    {"role": "content", "value": {"relation_id": f"{prefix}_chain_{index + 1}"}}]}
            else:
                expression = {"op": "REF", "relation_id": f"{prefix}_chain_{index + 1}"}
            for _ in range(wrappers):
                expression = {"op": "NOT", "operand": expression}
            relation = deepcopy(template)
            relation.update(relation_id=prefix + "_main" if index == 0 else f"{prefix}_chain_{index}",
                            expression=expression)
            relations.append(relation)
        representation["relations"] = relations
    return payload


@pytest.mark.parametrize("reference_kind", ("REF", "proposition"))
def test_cumulative_reference_expansion_becomes_unresolved_before_stack_exhaustion(tmp_path, reference_kind):
    from tools.language_relation_v0.verifier import verify_input

    payload = nested_relation_chain_payload(25, 45, reference_kind=reference_kind)
    path = save_input(tmp_path, payload)
    verification = verify_input(path)
    assert all(row["result"] == "pass" for row in verification["checks"]
               if row["kind"] == "source_binding")
    assert all(row["result"] == "unresolved" for row in verification["checks"]
               if row["kind"] == "representation_mapping")
    report = measure_input(path)
    assert_measurement_integrity(report, payload)
    target = result_for(report)
    assert target["relation_state"] == "UNDETERMINED"
    assert target["assessment_state"] == "UNRESOLVED"
    assert target["closed_obligation_ids"] == []
    assert "bound" in target["reason"]


@pytest.mark.parametrize("length, wrappers, reference_kind, mirror, expected", (
    (3, 30, "REF", True, "PRESERVED"),
    (254, 0, "REF", False, "PRESERVED"),
    (254, 0, "proposition", False, "CHANGED"),
))
def test_supported_cumulative_reference_expansions_still_complete(
        tmp_path, length, wrappers, reference_kind, mirror, expected):
    payload = nested_relation_chain_payload(length, wrappers,
                                           reference_kind=reference_kind, mirror=mirror)
    report = measured(tmp_path, payload)
    target = result_for(report)
    assert target["relation_state"] == expected
    assert target["assessment_state"] == "IDENTIFIED"
    assert target["representation_basis"] == "candidate_only"


@pytest.mark.parametrize("operator", ("AND", "OR"))
def test_deep_proposition_composition_preserves_operand_order_independence(tmp_path, operator):
    payload = nested_relation_chain_payload(252, 0, reference_kind="proposition")
    root = payload["representations"]["before"]["relations"][0]
    root["expression"] = {"op": operator, "operands": [root["expression"], atom("before")]}
    report = measured(tmp_path, payload)
    target = result_for(report)
    assert target["relation_state"] == "CHANGED"
    assert target["assessment_state"] == "IDENTIFIED"
    assert target["representation_basis"] == "candidate_only"
    root["expression"]["operands"].reverse()
    reordered = measured(tmp_path, payload)
    reordered_target = result_for(reordered)
    assert {key: value for key, value in reordered_target.items() if key != "verification_ids"} == {
        key: value for key, value in target.items() if key != "verification_ids"}
    assert reordered_target["verification_ids"] != target["verification_ids"]
    assert reordered["witnesses"] == report["witnesses"]


def test_deep_duplicate_interpretation_alternatives_remain_comparable(tmp_path):
    payload = nested_relation_chain_payload(254, 0, reference_kind="proposition")
    payload["measurement_request"]["targets"][0]["question"] = "interpretation_preservation"
    variants = payload["interpretations"]["variants"]
    duplicate = deepcopy(variants[0])
    duplicate["variant_id"] = "variant_duplicate"
    variants.append(duplicate)
    report = measured(tmp_path, payload)
    target = result_for(report)
    assert target["relation_state"] == "CHANGED"
    assert target["assessment_state"] == "IDENTIFIED"
    assert target["representation_basis"] == "candidate_only"
    assert target["compatible_variant_ids"] == sorted(row["variant_id"] for row in variants)
    assert any(row["kind"] == "alternative_loss" for row in report["witnesses"])


def test_structural_order_keeps_the_existing_tuple_representation():
    from tools.language_relation_v0.logic import _tuple_key

    values = [(), ("CONST", True), ("CONST", False), ("VAR", 0),
              ("singleton",), ("nested", ((), (None,), ("quote'", 'double"', "\\", "\n", "árvíz"))),
              ("CONTEXT", "quotation", "permission", None, ("CONST", False))]
    assert [_tuple_key(value) for value in values] == [repr(value) for value in values]
    assert sorted(values, key=_tuple_key) == sorted(values, key=repr)


def test_cli_publishes_all_target_diagnostics_for_oversized_reference_expansion(tmp_path):
    payload = nested_relation_chain_payload(25, 45)
    another_target = deepcopy(payload["measurement_request"]["targets"][0])
    another_target.update(target_id="target_other", required_obligation_ids=["coverage_other"])
    payload["measurement_request"]["targets"].append(another_target)
    another_obligation = deepcopy(payload["coverage_obligations"][0])
    another_obligation.update(target_id="target_other", obligation_id="coverage_other")
    payload["coverage_obligations"].append(another_obligation)
    output = tmp_path / "bounded-diagnostics"
    completed = invoke_cli(save_input(tmp_path, payload), output)
    assert completed.returncode == 0, completed.stderr
    assert {path.name for path in output.iterdir()} == {"measurement.json", "verification.json"}
    report = json.loads((output / "measurement.json").read_bytes())
    verification_raw = (output / "verification.json").read_bytes()
    verification = json.loads(verification_raw)
    assert_measurement_integrity(report, payload)
    jsonschema.Draft202012Validator(VERIFICATION_SCHEMA).validate(verification)
    assert report["verification_refs"] == [{"artifact_id": verification["verification_id"],
                                            "content_sha256": digest(verification_raw)}]
    assert {row["target_id"] for row in report["results"]} == {"target_main", "target_other"}
    assert all(row["assessment_state"] == "UNRESOLVED" for row in report["results"])
    assert all(row["relation_state"] == "UNDETERMINED" for row in report["results"])

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
