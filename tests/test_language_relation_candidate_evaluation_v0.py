"""LRM-05 preserved candidate import, isolation and diagnostic regressions.

All response builders in this test module are synthetic fixtures. They are not
model outputs or extraction gold labels. Frozen reference representations are
used only to author test inputs; the evaluation runtime must never read them.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.language_relation_v0 import candidates as C
from tools.language_relation_v0.comparator import measure_bundle
from tools.language_relation_v0.io import InputError, canonical_bytes, sha256, strict_json


SELF = "tests/test_language_relation_candidate_evaluation_v0.py"
CLI = ROOT / "tools/evaluate_language_relation_candidates_v0.py"
EXAMPLES = ROOT / "examples/language_relation_adapter_v0"
REFERENCE_CASES = ROOT / "examples/language_relation_measurement_v0/cases.json"
REPORT_SCHEMA = "language_relation_adapter_evaluation_v0.schema.json"
SCHEMAS = (
    "language_relation_adapter_requests_v0.schema.json",
    "language_relation_candidate_records_v0.schema.json",
    REPORT_SCHEMA,
)


def _walk(value):
    pending = [value]
    while pending:
        item = pending.pop()
        yield item
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


def requests():
    return C.load_requests()["requests"]


def request(case_id="LRM_REF_01"):
    return next(row for row in requests() if row["case_id"] == case_id)


def candidate(case_id="LRM_REF_01"):
    """Fixture-only authoring, never a runtime fallback for missing responses."""
    cases = json.loads(REFERENCE_CASES.read_bytes())["cases"]
    value = deepcopy(next(row for row in cases if row["case_id"] == case_id))
    value["impact_model"] = None
    return value


def envelope(records=()):
    inventory = C.load_requests()
    return {
        "schema_version": "language_relation_candidate_records_v0",
        "artifact_kind": "language_relation_candidate_records",
        "record_set_id": "synthetic_regression_capture",
        "request_set_ref": {
            "request_set_id": inventory["request_set_id"],
            "content_sha256": sha256(C.request_bytes()),
        },
        "producer": {
            "adapter_id": "synthetic_fixture_adapter",
            "adapter_version": "0",
            "provider": None,
            "model": None,
            "run_id": "synthetic_run",
            "record_origin": "synthetic_fixture",
            "historical_input_isolation": "not_verified",
        },
        "records": list(records),
        "authority_effect": "none",
        "release_authority_activation": False,
    }


def record(tmp_path, case_id="LRM_REF_01", *, payload=None, raw=None,
           status="completed", reason=None, confidence=None, suffix=""):
    value = {
        "record_id": "record_" + case_id + suffix,
        "case_id": case_id,
        "request_sha256": C.request_digest(request(case_id)),
        "capture_status": status,
        "response": None,
        "reason": reason,
        "confidence": confidence,
        "unresolved_items": [],
    }
    if status == "completed":
        if raw is None:
            raw = canonical_bytes(candidate(case_id) if payload is None else payload)
        relative = "responses/" + case_id + suffix + ".json"
        path = tmp_path / relative
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(raw)
        value["response"] = {"path": relative, "byte_length": len(raw),
                             "content_sha256": sha256(raw)}
    else:
        value["reason"] = reason or "Synthetic capture did not produce a candidate."
    return value


def evaluate(tmp_path, records=(), *, wrapper=None):
    document = envelope(records) if wrapper is None else wrapper
    path = tmp_path / "captures.json"
    path.write_bytes(canonical_bytes(document))
    bundle = C.evaluate_candidates(path, package_root=tmp_path)
    schema = json.loads((ROOT / "schemas" / REPORT_SCHEMA).read_bytes())
    jsonschema.Draft202012Validator(schema).validate(bundle["evaluation"])
    assert len(bundle["evaluation"]["cases"]) == 23
    assert sum(len(row["questions"]) for row in bundle["evaluation"]["cases"]) == 24
    for name, raw in bundle["payloads"].items():
        if name.endswith(".json"):
            strict_json(raw)
    strict_json(canonical_bytes(bundle["evaluation"]))
    return bundle


def case(bundle, case_id="LRM_REF_01"):
    return next(row for row in bundle["evaluation"]["cases"] if row["case_id"] == case_id)


def mapping(row, side):
    return next(check for check in row["mapping_checks"]
                if check["check_id"] == "mapping." + side)


def assert_checked(bundle, case_id="LRM_REF_01", expected=("pass", "pass")):
    row = case(bundle, case_id)
    assert row["import_status"] == "checked", row
    assert tuple(mapping(row, side)["result"] for side in ("before", "after")) == expected
    assert "inputs/" + case_id + ".json" in bundle["payloads"]
    assert "verifications/" + case_id + ".json" in bundle["payloads"]
    return row


def assert_rejected(bundle, case_id="LRM_REF_01"):
    row = case(bundle, case_id)
    assert row["import_status"] == "rejected", row
    assert row["diagnostics"]
    assert "inputs/" + case_id + ".json" not in bundle["payloads"]
    assert row["input_ref"] is None and row["verification_ref"] is None
    return row


def unresolved_item(case_id="LRM_REF_01"):
    return {
        "issue_id": "unresolved_referent",
        "category": "referent_resolution",
        "reason": "Synthetic recorded uncertainty is not a correctness certificate.",
        "source_id": "source_before",
        "start_byte": 0,
        "end_byte": 4,
        "question_ids": [request(case_id)["questions"][0]["target_id"]],
    }


@pytest.mark.parametrize("name", SCHEMAS)
def test_new_schemas_are_valid_and_resolve_only_local_references(name):
    schema = json.loads((ROOT / "schemas" / name).read_bytes())
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    for node in _walk(schema):
        if isinstance(node, dict) and "$ref" in node:
            assert node["$ref"].startswith("#")


@pytest.fixture(scope="module")
def actual_report_and_validator():
    report = C.evaluate_candidates(EXAMPLES / "captures.json", package_root=EXAMPLES)["evaluation"]
    schema = json.loads((ROOT / "schemas" / REPORT_SCHEMA).read_bytes())
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(report)
    return report, validator


@pytest.mark.parametrize("missing", ["response_ref", "input_ref", "verification_ref",
                                     "interpretation_state", "candidate_selection"])
def test_report_schema_rejects_checked_completion_without_required_binding(actual_report_and_validator, missing):
    original, validator = actual_report_and_validator
    report = deepcopy(original)
    row = next(item for item in report["cases"] if item["case_id"] == "LRM_REF_01")
    assert row["import_status"] == "checked"
    if missing == "candidate_selection":
        row["questions"][0]["candidate_selection"] = None
    else:
        row[missing] = None
    assert not validator.is_valid(report), missing


@pytest.mark.parametrize("forged", ["input_ref", "verification_ref", "interpretation_state",
                                    "source_check", "mapping_check", "candidate_selection", "coverage_check"])
def test_report_schema_rejects_success_fields_on_an_unchecked_case(actual_report_and_validator, forged):
    original, validator = actual_report_and_validator
    report = deepcopy(original)
    checked = next(item for item in report["cases"] if item["case_id"] == "LRM_REF_01")
    row = next(item for item in report["cases"] if item["case_id"] == "LRM_REF_04")
    assert row["capture_status"] == "missing" and row["import_status"] == "not_run"
    if forged in {"input_ref", "verification_ref", "interpretation_state"}:
        row[forged] = deepcopy(checked[forged])
    elif forged in {"source_check", "mapping_check"}:
        key = "source_checks" if forged == "source_check" else "mapping_checks"
        row[key][0] = deepcopy(checked[key][0])
        assert row[key][0]["status"] == "completed" and row[key][0]["result"] == "pass"
    elif forged == "candidate_selection":
        row["questions"][0]["candidate_selection"] = deepcopy(checked["questions"][0]["candidate_selection"])
    else:
        row["questions"][0]["coverage_checks"] = deepcopy(checked["questions"][0]["coverage_checks"])
        assert row["questions"][0]["coverage_checks"]
    assert not validator.is_valid(report), forged


@pytest.mark.parametrize("capture_status,record_count", [
    ("missing", 1), ("ambiguous", 0), ("ambiguous", 1),
    ("completed", 0), ("completed", 2), ("failed", 0),
    ("unsupported", 0), ("not_run", 0),
])
def test_report_schema_rejects_capture_state_record_cardinality_mismatch(
        actual_report_and_validator, capture_status, record_count):
    original, validator = actual_report_and_validator
    report = deepcopy(original)
    identifier = {"completed": "LRM_REF_01", "unsupported": "LRM_REF_02",
                  "failed": "LRM_REF_03"}.get(capture_status, "LRM_REF_04")
    row = next(item for item in report["cases"] if item["case_id"] == identifier)
    row["capture_status"] = capture_status
    if capture_status == "ambiguous":
        row["import_status"] = "rejected"
    row["record_ids"] = ["synthetic_record_" + str(index) for index in range(record_count)]
    assert not validator.is_valid(report), (capture_status, record_count)


def test_source_only_inventory_preserves_all_exact_hu_en_requests():
    inventory = C.load_requests()
    schema = json.loads((ROOT / "schemas" / SCHEMAS[0]).read_bytes())
    jsonschema.Draft202012Validator(schema).validate(inventory)
    assert C.request_bytes() == (EXAMPLES / "requests.json").read_bytes()
    assert inventory["request_set_id"] == "lrm_hu_en_source_requests_v0"
    assert len(inventory["requests"]) == 23
    assert sum(len(row["questions"]) for row in inventory["requests"]) == 24
    assert Counter(next(source["language"] for source in row["sources"]
                        if source["role"] == "before") for row in inventory["requests"]) == {"en": 14, "hu": 9}
    forbidden = {"representations", "representation_basis", "source_anchors", "correspondence",
                 "coverage_obligations", "interpretations", "impact_model", "before_ids",
                 "after_ids", "required_obligation_ids", "relation_state", "expectations",
                 "target_expectations", "expected_relation_state", "oracle_label"}
    for node in _walk(inventory):
        if isinstance(node, dict):
            assert forbidden.isdisjoint(node)
    for row in inventory["requests"]:
        assert C.request_digest(row) == sha256(canonical_bytes(row))
        for source in row["sources"]:
            raw = source["content"]["text"].encode("utf-8")
            assert source["content"]["kind"] == "inline_utf8"
            assert source["byte_length"] == len(raw)
            assert source["content_sha256"] == sha256(raw)


def test_loaded_requests_do_not_share_mutable_state():
    first = C.load_requests()
    first["requests"][0]["sources"][0]["content"]["text"] = "poisoned returned object"
    assert C.load_requests()["requests"][0]["sources"][0]["content"]["text"] == "Anna approves."


def test_all_missing_cases_remain_with_fixed_denominators(tmp_path):
    bundle = evaluate(tmp_path)
    report = bundle["evaluation"]
    assert {row["case_id"] for row in report["cases"]} == {row["case_id"] for row in requests()}
    assert all(row["capture_status"] == "missing" and row["import_status"] == "not_run"
               for row in report["cases"])
    assert report["summary"]["selected_cases"] == 23
    assert report["summary"]["selected_questions"] == 24
    assert report["summary"]["missing_cases"] == 23
    assert report["summary"]["checked_cases"] == 0
    assert report["summary"]["mapping_not_run"] == 46
    assert "accuracy" not in report["summary"]
    assert "inputs/LRM_REF_01.json" not in bundle["payloads"]


def test_mixed_capture_retains_success_failure_unsupported_and_missing(tmp_path):
    wrong = candidate("LRM_REF_10")
    root = wrong["representations"]["before"]["relations"][0]
    root["expression"] = root["expression"]["body"]
    entries = [record(tmp_path), record(tmp_path, "LRM_REF_05"),
               record(tmp_path, "LRM_REF_10", payload=wrong),
               record(tmp_path, "LRM_REF_02", status="unsupported"),
               record(tmp_path, "LRM_REF_03", status="failed"),
               record(tmp_path, "LRM_REF_04", status="not_run")]
    bundle = evaluate(tmp_path, entries)
    assert_checked(bundle)
    assert_checked(bundle, "LRM_REF_05")
    assert_checked(bundle, "LRM_REF_10", ("fail", "pass"))
    summary = bundle["evaluation"]["summary"]
    assert summary["checked_cases"] == 3
    assert summary["both_mapping_pass_cases"] == 2
    assert summary["missing_cases"] == 17
    assert summary["capture_failed_cases"] == 1
    assert summary["unsupported_cases"] == 1
    assert summary["not_run_cases"] == 1
    assert summary["mapping_pass"] == 5 and summary["mapping_fail"] == 1


def test_shipped_demo_is_synthetic_and_reports_its_known_diagnostics():
    bundle = C.evaluate_candidates(EXAMPLES / "captures.json", package_root=EXAMPLES)
    report = bundle["evaluation"]
    assert_checked(bundle)
    assert_checked(bundle, "LRM_REF_05")
    assert_checked(bundle, "LRM_REF_10", ("fail", "pass"))
    assert report["summary"]["missing_cases"] == 18
    assert report["summary"]["unsupported_cases"] == 1
    assert report["summary"]["capture_failed_cases"] == 1
    assert report["summary"]["selected_cases"] == 23
    assert report["producer"]["record_origin"] == "synthetic_fixture"
    assert report["producer"]["historical_input_isolation"] == "not_verified"


def test_runtime_does_not_read_reference_annotations_or_expected_labels(tmp_path, monkeypatch):
    entry = record(tmp_path)
    original = os.open

    def no_oracle(path, *args, **kwargs):
        if isinstance(path, (str, bytes, Path)):
            name = os.fsdecode(path)
            assert Path(name).name not in {"cases.json", "expected.json", "contract_examples.json"}
        return original(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", no_oracle)
    bundle = evaluate(tmp_path, [entry])
    assert_checked(bundle)


def test_improved_ref13_candidate_is_not_compared_with_faulty_reference(tmp_path):
    value = candidate()
    value["case_id"] = "LRM_REF_13"
    value["sources"] = deepcopy(request("LRM_REF_13")["sources"])
    for anchor in value["source_anchors"]:
        source = next(row for row in value["sources"] if row["source_id"] == anchor["source_id"])
        anchor.update(end_byte=source["byte_length"], content_sha256=source["content_sha256"])
    assert not candidate("LRM_REF_13")["representations"]["after"]["relations"]
    bundle = evaluate(tmp_path, [record(tmp_path, "LRM_REF_13", payload=value)])
    assert_checked(bundle, "LRM_REF_13")


def test_wrong_identical_extractions_are_checked_against_source_independently(tmp_path):
    value = candidate()
    for side in ("before", "after"):
        relation = value["representations"][side]["relations"][0]
        relation["expression"] = {"op": "NOT", "operand": relation["expression"]}
    bundle = evaluate(tmp_path, [record(tmp_path, payload=value)])
    assert_checked(bundle, expected=("fail", "fail"))
    assert bundle["evaluation"]["summary"]["both_mapping_pass_cases"] == 0


@pytest.mark.parametrize("confidence", [None, 0, 0.5, 1])
def test_confidence_never_grants_acceptance_or_question_scope(tmp_path, confidence):
    bundle = evaluate(tmp_path, [record(tmp_path, confidence=confidence)])
    row = assert_checked(bundle)
    for question in row["questions"]:
        assert question["scope_selection"] == "not_verified"
        assert question["representation_basis"] == "candidate_only"
        assert question["claim_scope"] == "candidate_structures"
        assert "relation_state" not in question
    verification = strict_json(bundle["payloads"]["verifications/LRM_REF_01.json"])
    assert all(item["representation_basis"] == "candidate_only" for item in verification["basis_records"])
    assert verification["authority_effect"] == "none"
    assert verification["release_authority_activation"] is False


@pytest.mark.parametrize("basis", ["accepted_reference", "profile_verified"])
def test_submitted_stronger_basis_is_rejected_without_self_acceptance(tmp_path, basis):
    value = candidate()
    value["representation_basis"]["before"] = {
        "basis": basis,
        "verification_ref": {"artifact_id": "self_check", "content_sha256": "1" * 64},
        "acceptance_ref": {"inventory_id": "self_inventory", "entry_id": "self_entry",
                           "content_sha256": "2" * 64},
    }
    assert_rejected(evaluate(tmp_path, [record(tmp_path, payload=value, confidence=1)]))


@pytest.mark.parametrize("kind", ["correspondence", "coverage", "impact", "processing"])
def test_candidate_cannot_import_its_own_authoritative_premises(tmp_path, kind):
    value = candidate()
    if kind == "correspondence":
        value["correspondence"][0].update(basis="accepted_reference", rule_or_reference_id="self_accepted")
    elif kind == "coverage":
        value["coverage_obligations"][0]["evidence_refs"] = ["self_accepted"]
    elif kind == "impact":
        # candidate() intentionally strips support models for ordinary fixtures.
        original = json.loads(REFERENCE_CASES.read_bytes())["cases"][21]
        value["impact_model"] = deepcopy(original["impact_model"])
    else:
        value["measurement_request"]["processing_claim"] = "processing_change"
        value["processing_binding"] = {"processing_id": "unverified_operation",
                                       "before_source_id": "source_before",
                                       "after_source_id": "source_after",
                                       "context_source_ids": [], "evidence_refs": ["self_accepted"]}
    assert_rejected(evaluate(tmp_path, [record(tmp_path, payload=value)]))


@pytest.mark.parametrize("origin,provenance,accepted", [
    ("synthetic_fixture", "synthetic_reference", True),
    ("synthetic_fixture", "synthetic_contract_example", True),
    ("preserved_model_response", "captured_input", True),
    ("preserved_model_response", "synthetic_reference", False),
    ("synthetic_fixture", "captured_input", False),
])
def test_capture_origin_and_input_provenance_remain_distinct(tmp_path, origin, provenance, accepted):
    value = candidate()
    value["provenance"] = provenance
    wrapper = envelope([record(tmp_path, payload=value)])
    wrapper["producer"].update(record_origin=origin, provider="opaque-provider", model="opaque-model")
    bundle = evaluate(tmp_path, wrapper=wrapper)
    if accepted:
        assert_checked(bundle)
    else:
        assert_rejected(bundle)


def test_raw_response_and_admitted_input_bytes_are_preserved_exactly(tmp_path):
    raw = json.dumps(candidate(), ensure_ascii=False, separators=(",", ":")).encode()
    bundle = evaluate(tmp_path, [record(tmp_path, raw=raw)])
    row = assert_checked(bundle)
    assert bundle["payloads"]["responses/LRM_REF_01.bin"] == raw
    assert bundle["payloads"]["inputs/LRM_REF_01.json"] == raw
    assert row["input_ref"]["content_sha256"] == sha256(raw)
    assert row["response_ref"]["content_sha256"] == sha256(raw)


@pytest.mark.parametrize("raw", [
    b'{"case_id":"first","case_id":"second"}', b'{"value":NaN}',
    b'{"value":Infinity}', b'[]', b'{', b'\xff', b'\xef\xbb\xbf{}',
    b'{"x":' * 90 + b'0' + b'}' * 90,
])
def test_bad_response_is_retained_and_does_not_erase_another_case(tmp_path, raw):
    entries = [record(tmp_path, raw=raw), record(tmp_path, "LRM_REF_05")]
    bundle = evaluate(tmp_path, entries)
    assert_rejected(bundle)
    assert bundle["payloads"]["responses/LRM_REF_01.bin"] == raw
    assert_checked(bundle, "LRM_REF_05")


@pytest.mark.parametrize("kind", ["hash", "length", "request_hash", "missing_file"])
def test_response_or_request_binding_failure_does_not_publish_an_input(tmp_path, kind):
    entry = record(tmp_path)
    if kind == "hash":
        entry["response"]["content_sha256"] = "0" * 64
    elif kind == "length":
        entry["response"]["byte_length"] += 1
    elif kind == "request_hash":
        entry["request_sha256"] = "0" * 64
    else:
        (tmp_path / entry["response"]["path"]).unlink()
    bundle = evaluate(tmp_path, [entry, record(tmp_path, "LRM_REF_05")])
    assert_rejected(bundle)
    assert_checked(bundle, "LRM_REF_05")


def test_mismatched_response_preserves_observed_bytes_separate_from_claimed_pin(tmp_path):
    entry = record(tmp_path)
    claimed = deepcopy(entry["response"])
    actual = b'{"changed_after_capture":true}\n'
    (tmp_path / entry["response"]["path"]).write_bytes(actual)
    bundle = evaluate(tmp_path, [entry])
    row = assert_rejected(bundle)
    assert row["submitted_response"] == claimed
    assert row["response_ref"]["content_sha256"] == sha256(actual)
    assert row["response_ref"]["byte_length"] == len(actual)
    assert bundle["payloads"]["responses/LRM_REF_01.bin"] == actual


@pytest.mark.parametrize("path", ["../escape.json", "/absolute.json", "responses\\candidate.json",
                                   "responses/../candidate.json", "responses/./candidate.json"])
def test_response_paths_cannot_escape_or_change_interpretation(tmp_path, path):
    entry = record(tmp_path)
    entry["response"]["path"] = path
    bundle = evaluate(tmp_path, [entry, record(tmp_path, "LRM_REF_05")])
    assert_rejected(bundle)
    assert_checked(bundle, "LRM_REF_05")


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_special_response_files_are_rejected_without_waiting(tmp_path, kind):
    entry = record(tmp_path)
    path = tmp_path / entry["response"]["path"]
    raw = path.read_bytes()
    path.unlink()
    if kind == "symlink":
        target = tmp_path / "elsewhere.json"
        target.write_bytes(raw)
        path.symlink_to(target)
    else:
        os.mkfifo(path)
    assert_rejected(evaluate(tmp_path, [entry]))


def test_response_limit_is_a_case_diagnostic_with_all_other_cases_retained(tmp_path):
    entry = record(tmp_path, raw=b" " * (C.MAX_RESPONSE_BYTES + 1))
    bundle = evaluate(tmp_path, [entry, record(tmp_path, "LRM_REF_05")])
    row = assert_rejected(bundle)
    assert any(item["code"] == "resource_limit" for item in row["diagnostics"])
    assert_checked(bundle, "LRM_REF_05")


def test_candidate_resource_limit_is_a_case_diagnostic(tmp_path):
    value = candidate()
    anchor = value["source_anchors"][0]
    value["source_anchors"].extend({**deepcopy(anchor), "anchor_id": "extra_" + str(index)}
                                   for index in range(C.MAX_ANCHORS))
    bundle = evaluate(tmp_path, [record(tmp_path, payload=value), record(tmp_path, "LRM_REF_05")])
    row = assert_rejected(bundle)
    assert any(item["code"] == "resource_limit" for item in row["diagnostics"])
    assert_checked(bundle, "LRM_REF_05")


def test_checker_and_published_input_use_the_already_bound_snapshot(tmp_path, monkeypatch):
    entry = record(tmp_path)
    path = tmp_path / entry["response"]["path"]
    preserved = path.read_bytes()
    original = C.safe_read

    def change_original_after_read(root, locator, **kwargs):
        raw = original(root, locator, **kwargs)
        if Path(root) == tmp_path and locator == entry["response"]["path"]:
            path.write_bytes(b'{"changed_after_binding":true}')
        return raw

    monkeypatch.setattr(C, "safe_read", change_original_after_read)
    bundle = evaluate(tmp_path, [entry])
    assert_checked(bundle)
    assert path.read_bytes() != preserved
    assert bundle["payloads"]["inputs/LRM_REF_01.json"] == preserved
    verification = strict_json(bundle["payloads"]["verifications/LRM_REF_01.json"])
    assert verification["input_ref"]["content_sha256"] == sha256(preserved)


def test_checker_cannot_return_an_unbound_verification_as_success(tmp_path, monkeypatch):
    original = C.verify_input

    def wrong_binding(path, **kwargs):
        result = original(path, **kwargs)
        if result["input_ref"]["artifact_id"] == "LRM_REF_01":
            result["input_ref"]["content_sha256"] = "0" * 64
        return result

    monkeypatch.setattr(C, "verify_input", wrong_binding)
    bundle = evaluate(tmp_path, [record(tmp_path), record(tmp_path, "LRM_REF_05")])
    row = case(bundle)
    assert row["import_status"] == "execution_error"
    assert row["input_ref"] is None and row["verification_ref"] is None
    assert "inputs/LRM_REF_01.json" not in bundle["payloads"]
    assert_checked(bundle, "LRM_REF_05")


def test_pinned_request_inventory_cannot_be_replaced_by_runtime_input(monkeypatch):
    original = C.safe_read

    def poisoned_inventory(root, locator, **kwargs):
        raw = original(root, locator, **kwargs)
        return raw + b"\n" if locator == C.REQUEST_PATH else raw

    monkeypatch.setattr(C, "safe_read", poisoned_inventory)
    with pytest.raises(InputError, match="inventory digest"):
        C.load_requests()


def test_all_questions_and_axes_keep_diagnostic_scope_even_when_capture_is_missing(tmp_path):
    bundle = evaluate(tmp_path, [record(tmp_path)])
    report = bundle["evaluation"]
    axes = {"observation_status", "binding_status", "consistency_status",
            "reproduction_status", "causal_status", "authority_status"}
    for row in [report, *report["cases"]]:
        assert set(row["status_axes"]) == axes
        assert row["status_axes"]["authority_status"] == "none"
        assert row["authority_effect"] == "none" and row["release_authority_activation"] is False
    for row in report["cases"]:
        for question in row["questions"]:
            assert question["scope_selection"] == "not_verified"
            assert question["representation_basis"] == "candidate_only"
            assert question["claim_scope"] == "candidate_structures"
    assert report["summary"]["by_language"]["en"]["selected_cases"] == 14
    assert report["summary"]["by_language"]["hu"]["selected_cases"] == 9
    assert report["summary"]["by_language"]["en"]["missing_cases"] == 13
    assert report["summary"]["by_language"]["hu"]["missing_cases"] == 9
    assert report["model_quality"] == "not_evaluated"
    assert report["reference_agreement"] == "not_evaluated"
    assert all("relation_state" not in item for item in _walk(report) if isinstance(item, dict))


@pytest.mark.parametrize("kind", ["case", "profile", "text", "revision", "question", "question_description", "target_id"])
def test_candidate_must_match_exact_request_sources_and_question_metadata(tmp_path, kind):
    value = candidate()
    if kind == "case":
        value["case_id"] = "LRM_REF_04"
    elif kind == "profile":
        value["profile_ref"]["content_sha256"] = "0" * 64
    elif kind == "text":
        source = value["sources"][0]
        source["content"]["text"] += " "
        raw = source["content"]["text"].encode()
        source.update(byte_length=len(raw), content_sha256=sha256(raw))
    elif kind == "revision":
        value["sources"][0]["revision"] = "invented_revision"
    else:
        target = value["measurement_request"]["targets"][0]
        if kind == "question": target["question"] = "condition_impact"
        elif kind == "question_description": target["description"] = "A different question."
        else: target["target_id"] = "unrequested_target"
    assert_rejected(evaluate(tmp_path, [record(tmp_path, payload=value)]))


def test_duplicate_case_records_are_ambiguous_even_if_identical(tmp_path):
    first = record(tmp_path)
    duplicate = deepcopy(first)
    duplicate["record_id"] = "second_capture_of_same_case"
    bundle = evaluate(tmp_path, [first, duplicate, record(tmp_path, "LRM_REF_05")])
    row = case(bundle)
    assert row["capture_status"] == "ambiguous"
    assert row["import_status"] == "rejected"
    assert "inputs/LRM_REF_01.json" not in bundle["payloads"]
    assert bundle["evaluation"]["summary"]["ambiguous_cases"] == 1
    assert_checked(bundle, "LRM_REF_05")


def test_unrequested_extra_record_does_not_get_read_or_change_denominator(tmp_path, monkeypatch):
    entry = record(tmp_path)
    extra = deepcopy(entry)
    extra.update(case_id="UNREQUESTED", record_id="unrequested_record")
    extra["response"]["path"] = "never_read_this.json"
    original = os.open

    def guarded(path, *args, **kwargs):
        assert os.fsdecode(path) != "never_read_this.json"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", guarded)
    bundle = evaluate(tmp_path, [extra, entry])
    assert_checked(bundle)
    assert bundle["evaluation"]["summary"]["selected_cases"] == 23
    assert "UNREQUESTED" not in {row["case_id"] for row in bundle["evaluation"]["cases"]}
    assert "unrequested_record" in json.dumps(bundle["evaluation"])


def test_recorded_unresolved_items_are_preserved_with_question_scope(tmp_path):
    entry = record(tmp_path, confidence=1)
    issue = unresolved_item()
    entry["unresolved_items"] = [issue]
    bundle = evaluate(tmp_path, [entry])
    row = assert_checked(bundle)
    assert row["reported_unresolved_items"] == [issue]
    assert row["questions"][0]["scope_selection"] == "not_verified"


@pytest.mark.parametrize("kind", ["unknown_source", "unknown_question", "empty_span", "outside_span", "split_utf8"])
def test_unresolved_item_locators_are_checked_before_admission(tmp_path, kind):
    entry = record(tmp_path, "LRM_REF_05")
    issue = unresolved_item("LRM_REF_05")
    if kind == "unknown_source": issue["source_id"] = "unknown_source"
    elif kind == "unknown_question": issue["question_ids"] = ["unknown_question"]
    elif kind == "empty_span": issue.update(start_byte=1, end_byte=1)
    elif kind == "outside_span": issue["end_byte"] = 1000
    else:
        raw = request("LRM_REF_05")["sources"][0]["content"]["text"].encode()
        offset = raw.index("ó".encode())
        issue.update(start_byte=offset + 1, end_byte=offset + 2)
    entry["unresolved_items"] = [issue]
    bundle = evaluate(tmp_path, [entry, record(tmp_path)])
    assert_rejected(bundle, "LRM_REF_05")
    assert_checked(bundle)


@pytest.mark.parametrize("case_id,state", [
    ("LRM_REF_19", "unknown"), ("LRM_REF_20", "empty"), ("LRM_REF_21", "truncated"),
])
def test_distinct_interpretation_states_are_not_hidden_by_import(tmp_path, case_id, state):
    bundle = evaluate(tmp_path, [record(tmp_path, case_id)])
    row = case(bundle, case_id)
    assert row["import_status"] == "checked"
    assert row["interpretation_state"] == state
    assert row["questions"][0]["scope_selection"] == "not_verified"


def test_case_runtime_exception_retains_later_case_diagnostics(tmp_path, monkeypatch):
    original = C.verify_input

    def one_failure(path, **kwargs):
        if strict_json(Path(path).read_bytes())["case_id"] == "LRM_REF_01":
            raise RecursionError("synthetic verifier recursion failure")
        return original(path, **kwargs)

    monkeypatch.setattr(C, "verify_input", one_failure)
    bundle = evaluate(tmp_path, [record(tmp_path), record(tmp_path, "LRM_REF_05")])
    assert case(bundle)["import_status"] == "execution_error"
    assert case(bundle)["diagnostics"]
    assert_checked(bundle, "LRM_REF_05")


def test_evaluation_is_deterministic_without_execution_clock(tmp_path):
    entries = [record(tmp_path), record(tmp_path, "LRM_REF_05")]
    first = evaluate(tmp_path, entries)
    second = evaluate(tmp_path, entries)
    assert canonical_bytes(first["evaluation"]) == canonical_bytes(second["evaluation"])
    assert first["payloads"] == second["payloads"]


def test_admitted_input_recomputes_with_existing_comparator_at_candidate_scope(tmp_path):
    bundle = evaluate(tmp_path, [record(tmp_path)])
    output = tmp_path / "published"
    output.mkdir()
    for name, raw in bundle["payloads"].items():
        path = output / name
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(raw)
    measured = measure_bundle(output / "inputs/LRM_REF_01.json", package_root=output)
    target = measured["measurement"]["results"][0]
    assert target["relation_state"] == "PRESERVED"
    assert target["representation_basis"] == "candidate_only"
    assert target["claim_scope"] == "candidate_structures"
    assert measured["measurement"]["authority_effect"] == "none"
    assert measured["measurement"]["release_authority_activation"] is False


@pytest.mark.parametrize("kind", ["set_hash", "extra_field", "authority", "confidence_low", "confidence_high", "confidence_bool"])
def test_invalid_global_capture_is_not_a_successful_diagnostic(tmp_path, kind):
    wrapper = envelope([record(tmp_path)])
    if kind == "set_hash": wrapper["request_set_ref"]["content_sha256"] = "0" * 64
    elif kind == "extra_field": wrapper["expected_label"] = "PRESERVED"
    elif kind == "authority": wrapper["release_authority_activation"] = True
    else:
        wrapper["records"][0]["confidence"] = {"confidence_low": -0.1,
                                                "confidence_high": 1.1,
                                                "confidence_bool": True}[kind]
    path = tmp_path / "captures.json"
    path.write_bytes(canonical_bytes(wrapper))
    with pytest.raises(InputError):
        C.evaluate_candidates(path, package_root=tmp_path)


def _cli(*args):
    return subprocess.run([sys.executable, str(CLI), *map(str, args)],
                          capture_output=True, text=True, timeout=30)


def test_cli_exports_requests_and_evaluation_without_overwriting(tmp_path):
    request_dir = tmp_path / "requests_only"
    result = _cli("requests", "--output-dir", request_dir)
    assert result.returncode == 0, result.stderr
    assert (request_dir / "requests.json").read_bytes() == C.request_bytes()
    sentinel = request_dir / "owner.txt"
    sentinel.write_text("keep")
    result = _cli("requests", "--output-dir", request_dir)
    assert result.returncode == 2 and sentinel.read_text() == "keep"
    entries = [record(tmp_path)]
    captures = tmp_path / "captures.json"
    captures.write_bytes(canonical_bytes(envelope(entries)))
    out = tmp_path / "evaluation"
    result = _cli("evaluate", "--records", captures, "--package-root", tmp_path,
                  "--output-dir", out)
    assert result.returncode == 0, result.stderr
    report = strict_json((out / "evaluation.json").read_bytes())
    assert report["summary"]["checked_cases"] == 1
    assert (out / "inputs/LRM_REF_01.json").read_bytes() == (tmp_path / entries[0]["response"]["path"]).read_bytes()
    assert _cli("evaluate", "--records", captures, "--package-root", tmp_path,
                "--output-dir", out).returncode == 2


def test_cli_global_error_has_no_output_but_case_failure_is_diagnostic(tmp_path):
    captures = tmp_path / "captures.json"
    captures.write_bytes(b'{"duplicate":1,"duplicate":2}')
    invalid_output = tmp_path / "invalid"
    result = _cli("evaluate", "--records", captures, "--package-root", tmp_path,
                  "--output-dir", invalid_output)
    assert result.returncode == 2 and not invalid_output.exists()
    captures.write_bytes(canonical_bytes(envelope([record(tmp_path, raw=b'{') ])))
    case_output = tmp_path / "case_failure"
    result = _cli("evaluate", "--records", captures, "--package-root", tmp_path,
                  "--output-dir", case_output)
    assert result.returncode == 0, result.stderr
    assert strict_json((case_output / "evaluation.json").read_bytes())["summary"]["rejected_cases"] == 1


def test_publisher_rolls_back_only_owned_files_after_partial_failure(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("candidate_evaluation_cli_for_test", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = os.open

    def fail_second(path, flags, *args, **kwargs):
        if os.fsdecode(path) == "second.json" and flags & os.O_WRONLY:
            raise OSError("synthetic second-file write failure")
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", fail_second)
    destination = tmp_path / "new_output"
    unrelated = tmp_path / "owner.txt"
    unrelated.write_bytes(b"owner bytes")
    with pytest.raises(OSError):
        module._publish(destination, {"nested/first.json": b"{}\n", "nested/second.json": b"{}\n"})
    assert not destination.exists()
    assert unrelated.read_bytes() == b"owner bytes"


def test_candidate_evaluation_registered_once_without_losing_prior_lrm_modules():
    previous = ["tests/test_language_relation_" + name + "_v0.py"
                for name in ("contract", "input_verifier", "comparator", "impact")]
    for name, count in (("tools-tests.list", 179), ("pytest-tests.list", 35)):
        entries = [line.split("#", 1)[0].strip() for line in (ROOT / "ci" / name).read_text().splitlines()]
        entries = [line for line in entries if line]
        assert len(entries) == len(set(entries)) == count
        assert entries.count(SELF) == 1
        assert all(entries.count(path) == 1 for path in previous)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
