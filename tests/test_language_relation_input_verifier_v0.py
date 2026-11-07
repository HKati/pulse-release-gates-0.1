"""LRM-02 source-bound input verification and independent mapping regressions.

All examples are synthetic. Successful source mapping is conditional on the
finite controlled grammar; it neither proves an observed event nor grants
release authority. Expected trees below are hand-authored independently of the
runtime parser and no comparison/impact oracle is imported.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unicodedata

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.language_relation_v0.io import InputError
from tools.language_relation_v0.profile import check_profile_mapping
from tools.language_relation_v0.verifier import verify_input


SELF = "tests/test_language_relation_input_verifier_v0.py"
PROFILE_PATH = ROOT / "contracts/language_relation_profile_v0.json"
EXAMPLES = ROOT / "examples/language_relation_measurement_v0"
CLI = ROOT / "tools/check_language_relation_input_v0.py"
PROFILE = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
CASES = json.loads((EXAMPLES / "cases.json").read_text(encoding="utf-8"))["cases"]
VERIFICATION_SCHEMA = json.loads(
    (ROOT / "schemas/language_relation_verification_v0.schema.json").read_text(encoding="utf-8")
)
EVIDENCE_SCHEMA = json.loads(
    (ROOT / "schemas/language_relation_evidence_v0.schema.json").read_text(encoding="utf-8")
)


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def base_input() -> dict:
    return deepcopy(CASES[0])


def save_input(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "input.json"
    path.write_bytes(encoded(payload))
    return path


def verified(tmp_path: Path, payload: dict, **kwargs) -> dict:
    result = verify_input(save_input(tmp_path, payload), **kwargs)
    jsonschema.Draft202012Validator(VERIFICATION_SCHEMA).validate(result)
    return result


def check(result: dict, check_id: str) -> dict:
    rows = [row for row in result["checks"] if row["check_id"] == check_id]
    assert len(rows) == 1, (check_id, result["checks"])
    return rows[0]


def basis(result: dict, side: str) -> dict:
    rows = [row for row in result["basis_records"] if row["side"] == side]
    assert len(rows) == 1
    return rows[0]


def replace_source(payload: dict, side: str, text: str, language: str = "en") -> None:
    source = next(row for row in payload["sources"] if row["role"] == side)
    data = text.encode("utf-8")
    source.update(content={"kind": "inline_utf8", "text": text},
                  byte_length=len(data), content_sha256=digest(data), language=language)
    for anchor in payload["source_anchors"]:
        if anchor["source_id"] == source["source_id"]:
            anchor.update(start_byte=0, end_byte=len(data), content_sha256=digest(data))


def atom(side: str, person: str = "anna", predicate: str = "approve", *, variable: str | None = None) -> dict:
    value = {"variable": variable} if variable is not None else {"entity_id": side[0] + "_" + person}
    return {"op": "ATOM", "predicate": predicate, "arguments": [{"role": "agent", "value": value}]}


def context(body: dict, *, discourse: str = "assertion", modality: str = "declarative",
            speaker: str | None = None) -> dict:
    return {"op": "CONTEXT", "discourse_type": discourse, "modality": modality,
            "speaker_entity_id": speaker, "body": body}


def controlled_input(text: str, expression: dict, *, side: str = "before", language: str = "en") -> dict:
    payload = base_input()
    replace_source(payload, side, text, language)
    prefix = side[0] + "_"
    representation = payload["representations"][side]
    representation["entities"] = [
        {"entity_id": prefix + identifier, "label": label, "entity_type": "person",
         "anchor_ids": ["anchor_" + side]}
        for identifier, label in (("anna", "Anna"), ("bela", "Béla"), ("eva", "Éva"), ("daniel", "Dániel"))
    ]
    representation["domains"] = [
        {"domain_id": prefix + "people", "entity_ids": [prefix + "anna", prefix + "bela"]}
    ]
    representation["relations"][0]["expression"] = deepcopy(expression)
    return payload


def mapped(payload: dict, side: str = "before") -> dict:
    source_texts = {source["source_id"]: source["content"]["text"] for source in payload["sources"]}
    return check_profile_mapping(payload, PROFILE, source_texts, side)


def grammar_example(production: str, language: str, side: str) -> tuple[str, dict]:
    """Independent fixed expected trees, not a second call to the runtime parser."""
    first, second = atom(side), atom(side, "bela", "win")
    approve = "Anna approves" if language == "en" else "Anna jóváhagy"
    win = "Béla wins" if language == "en" else "Béla nyer"
    if production == "APPROVE":
        return approve + ".", first
    if production == "WIN":
        return win + ".", second
    if production == "NOT":
        return ("not" if language == "en" else "nem") + f" ({approve}).", {"op": "NOT", "operand": first}
    if production in {"AND", "OR"}:
        word = {("AND", "en"): "and", ("AND", "hu"): "és", ("OR", "en"): "or", ("OR", "hu"): "vagy"}[(production, language)]
        return f"({approve}) {word} ({win}).", {"op": production, "operands": [first, second]}
    if production == "IMPLIES":
        text = f"if ({approve}) then ({win})." if language == "en" else f"ha ({approve}), akkor ({win})."
        return text, {"op": "IMPLIES", "antecedent": first, "consequent": second}
    if production in {"FORALL", "EXISTS"}:
        if language == "en":
            word = "every" if production == "FORALL" else "some"
            text = f"for {word} x in {{Anna, Béla}} (x approves)."
        else:
            word = "minden" if production == "FORALL" else "van olyan"
            text = f"{word} x a {{Anna, Béla}} halmazból (x jóváhagy)."
        return text, {"op": production, "variable": "x", "domain_id": side[0] + "_people",
                      "body": atom(side, variable="x")}
    if production == "QUOTE":
        text = f"Béla says: ({approve})." if language == "en" else f"Béla mondja: ({approve})."
        return text, context(first, discourse="quotation", speaker=side[0] + "_bela")
    if production in {"PERMISSION", "OBLIGATION"}:
        if language == "en":
            word = "permitted" if production == "PERMISSION" else "required"
            text = f"it is {word} that ({approve})."
        else:
            word = "megengedett" if production == "PERMISSION" else "kötelező"
            text = f"{word}, hogy ({approve})."
        return text, context(first, modality=production.lower())
    raise AssertionError(production)


PRODUCTIONS = ("APPROVE", "WIN", "NOT", "AND", "OR", "IMPLIES", "FORALL", "EXISTS",
               "QUOTE", "PERMISSION", "OBLIGATION")


@pytest.mark.parametrize("side", ("before", "after"))
@pytest.mark.parametrize("language", ("hu", "en"))
@pytest.mark.parametrize("production", PRODUCTIONS)
def test_each_controlled_production_is_checked_from_source(production, language, side):
    text, expression = grammar_example(production, language, side)
    result = mapped(controlled_input(text, expression, side=side, language=language), side)
    assert result["result"] == "pass", result


@pytest.mark.parametrize("case", CASES, ids=lambda row: row["case_id"])
def test_original_reference_inputs_remain_structurally_loadable(tmp_path, case):
    result = verified(tmp_path, deepcopy(case))
    for side in ("before", "after"):
        assert check(result, "source." + side)["result"] == "pass"
        assert basis(result, side)["representation_basis"] == "candidate_only"
        assert basis(result, side)["claim_scope"] == "candidate_structures"


def test_completed_diagnostic_binds_exact_input_and_does_not_promote_candidates(tmp_path):
    payload = base_input()
    result = verified(tmp_path, payload)
    assert result["provenance"] == "verification_run"
    assert result["input_ref"]["content_sha256"] == digest((tmp_path / "input.json").read_bytes())
    assert result["profile_ref"]["content_sha256"] == digest(PROFILE_PATH.read_bytes())
    assert result["authority_effect"] == "none"
    assert result["release_authority_activation"] is False
    assert result["status_axes"]["authority_status"] == "none"
    assert result["status_axes"]["causal_status"] == "not_evaluated"
    assert result["status_axes"]["reproduction_status"] not in {"reproduced", "bounded_replay_only"}
    assert not {"results", "introduced_relations", "impacts"} & result.keys()
    check_ids = [row["check_id"] for row in result["checks"]]
    assert len(check_ids) == len(set(check_ids))
    for side in ("before", "after"):
        assert check(result, "mapping." + side)["result"] == "pass"
        assert basis(result, side)["representation_basis"] == "candidate_only"
        assert basis(result, side)["acceptance_ref"] is None
        assert set(basis(result, side)["check_ids"]) <= set(check_ids)


@pytest.mark.parametrize("mutation", ("source_text", "source_digest", "source_length", "anchor_digest", "anchor_offset"))
def test_source_binding_failures_do_not_run_mapping(tmp_path, mutation):
    payload = base_input()
    source, anchor = payload["sources"][0], payload["source_anchors"][0]
    if mutation == "source_text":
        source["content"]["text"] = "Anna approves!"
    elif mutation == "source_digest":
        source["content_sha256"] = "0" * 64
    elif mutation == "source_length":
        source["byte_length"] += 1
    elif mutation == "anchor_digest":
        anchor["content_sha256"] = "0" * 64
    else:
        anchor["start_byte"] = 1
    result = verified(tmp_path, payload)
    assert check(result, "source.before")["result"] == "fail"
    assert check(result, "source.after")["result"] == "pass"
    mapping = check(result, "mapping.before")
    assert mapping["status"] != "completed" and mapping["result"] is None and mapping["reason"]
    assert basis(result, "before")["representation_basis"] == "candidate_only"


@pytest.mark.parametrize("boundary", ("start", "end"))
def test_hash_of_split_utf8_character_does_not_validate_locator(tmp_path, boundary):
    payload = controlled_input("Éva wins.", atom("before", "eva", "win"))
    anchor = payload["source_anchors"][0]
    data = payload["sources"][0]["content"]["text"].encode("utf-8")
    if boundary == "start":
        anchor["start_byte"] = 1
    else:
        anchor["end_byte"] = 1
    anchor["content_sha256"] = digest(data[anchor["start_byte"]:anchor["end_byte"]])
    result = verified(tmp_path, payload)
    assert check(result, "source.before")["result"] == "fail"
    assert check(result, "mapping.before")["result"] is None


@pytest.mark.parametrize("mutation", ("duplicate_top", "duplicate_nested", "nan", "infinity", "negative_infinity", "overflow", "integer_digit_limit", "surrogate", "bom", "bad_utf8"))
def test_strict_json_rejects_duplicates_nonfinite_values_and_invalid_encoding(tmp_path, mutation):
    raw = encoded(base_input())
    if mutation == "duplicate_top":
        raw = b'{"schema_version": "wrong",' + raw[1:]
    elif mutation == "duplicate_nested":
        raw = raw.replace(b'"text": "Anna approves."', b'"text": "wrong", "text": "Anna approves."', 1)
    elif mutation in {"nan", "infinity", "negative_infinity", "overflow"}:
        token = {"nan": b"NaN", "infinity": b"Infinity", "negative_infinity": b"-Infinity", "overflow": b"1e999"}[mutation]
        raw = raw.replace(b'"byte_length": 14', b'"byte_length": ' + token, 1)
    elif mutation == "integer_digit_limit":
        raw = raw.replace(b'"byte_length": 14', b'"byte_length": ' + b"9" * 5000, 1)
    elif mutation == "surrogate":
        raw = raw.replace(b"Anna approves.", b"Anna \\ud800 approves.", 1)
    elif mutation == "bom":
        raw = b"\xef\xbb\xbf" + raw
    else:
        raw = raw.replace(b"Anna approves.", b"Anna approv\xffs.", 1)
    path = tmp_path / "input.json"
    path.write_bytes(raw)
    with pytest.raises(InputError):
        verify_input(path)


@pytest.mark.parametrize("collection", ("sources", "source_anchors", "correspondence", "coverage_obligations", "entities", "relations", "variants", "targets"))
def test_duplicate_ids_fail_before_diagnostic_result(tmp_path, collection):
    payload = base_input()
    if collection in {"entities", "relations"}:
        rows = payload["representations"]["before"][collection]
    elif collection == "variants":
        rows = payload["interpretations"]["variants"]
    elif collection == "targets":
        rows = payload["measurement_request"]["targets"]
    else:
        rows = payload[collection]
    rows.append(deepcopy(rows[0]))
    with pytest.raises(InputError):
        verify_input(save_input(tmp_path, payload))


@pytest.mark.parametrize("mutation", ("extra_field", "wrong_type", "representation_identity", "source_role", "anchor_source", "anchor_side", "entity_ref", "variant_ref", "target_ref", "obligation_target", "correspondence_side", "role", "predicate", "argument_type", "variable", "self_ref", "indirect_ref"))
def test_cross_record_identity_types_and_reference_cycles_are_rejected(tmp_path, mutation):
    payload = base_input()
    rep = payload["representations"]["before"]
    relation = rep["relations"][0]
    expression = relation["expression"]
    if mutation == "extra_field":
        payload["trusted"] = True
    elif mutation == "wrong_type":
        payload["sources"][0]["byte_length"] = True
    elif mutation == "representation_identity":
        rep["representation_id"] = payload["representations"]["after"]["representation_id"]
    elif mutation == "source_role":
        rep["source_id"] = "source_after"
    elif mutation == "anchor_source":
        payload["source_anchors"][0]["source_id"] = "missing_source"
    elif mutation == "anchor_side":
        relation["anchor_ids"] = ["anchor_after"]
    elif mutation == "entity_ref":
        expression["arguments"][0]["value"] = {"entity_id": "missing_entity"}
    elif mutation == "variant_ref":
        payload["interpretations"]["variants"][0]["before_relation_ids"] = ["missing_relation"]
    elif mutation == "target_ref":
        payload["measurement_request"]["targets"][0]["before_ids"] = ["missing_relation"]
    elif mutation == "obligation_target":
        payload["coverage_obligations"][0]["target_id"] = "missing_target"
    elif mutation == "correspondence_side":
        payload["correspondence"][0]["before_ids"] = ["a_anna"]
    elif mutation == "role":
        expression["arguments"][0]["role"] = "recipient"
    elif mutation == "predicate":
        expression["predicate"] = "invented_predicate"
    elif mutation == "argument_type":
        rep["entities"][0]["entity_type"] = "object"
    elif mutation == "variable":
        expression["arguments"][0]["value"] = {"variable": "x"}
    elif mutation == "self_ref":
        relation["expression"] = {"op": "REF", "relation_id": "b_main"}
    else:
        helper = deepcopy(relation)
        helper.update(relation_id="b_helper", expression={"op": "REF", "relation_id": "b_main"})
        relation["expression"] = {"op": "REF", "relation_id": "b_helper"}
        rep["relations"].append(helper)
    with pytest.raises(InputError):
        verify_input(save_input(tmp_path, payload))


@pytest.mark.parametrize("case_id", ("LRM_REF_11", "LRM_REF_17"))
@pytest.mark.parametrize("mutation", ("dropped_role", "duplicate_role"))
def test_nary_relations_require_every_distinct_role(tmp_path, case_id, mutation):
    payload = deepcopy(next(case for case in CASES if case["case_id"] == case_id))
    arguments = payload["representations"]["before"]["relations"][0]["expression"]["arguments"]
    assert len(arguments) == 3
    if mutation == "dropped_role":
        arguments.pop()
    else:
        arguments[-1]["role"] = arguments[0]["role"]
    with pytest.raises(InputError):
        verify_input(save_input(tmp_path, payload))


@pytest.mark.parametrize("case_id", ("LRM_REF_11", "LRM_REF_17"))
def test_valid_nary_annotations_do_not_expand_the_controlled_surface_grammar(tmp_path, case_id):
    payload = deepcopy(next(case for case in CASES if case["case_id"] == case_id))
    result = verified(tmp_path, payload)
    for side in ("before", "after"):
        assert check(result, "mapping." + side)["result"] == "unresolved"
        assert basis(result, side)["representation_basis"] == "candidate_only"


@pytest.mark.parametrize("production", ("NOT", "AND", "OR", "IMPLIES", "FORALL", "EXISTS", "QUOTE", "PERMISSION", "OBLIGATION"))
def test_correct_bytes_do_not_certify_changed_conveyed_structure(tmp_path, production):
    text, expression = grammar_example(production, "en", "before")
    payload = controlled_input(text, expression)
    root = payload["representations"]["before"]["relations"][0]
    if production == "NOT":
        root["expression"] = root["expression"]["operand"]
    elif production in {"AND", "OR"}:
        root["expression"]["op"] = "OR" if production == "AND" else "AND"
    elif production == "IMPLIES":
        expr = root["expression"]
        expr["antecedent"], expr["consequent"] = expr["consequent"], expr["antecedent"]
    elif production in {"FORALL", "EXISTS"}:
        root["expression"]["op"] = "EXISTS" if production == "FORALL" else "FORALL"
    elif production == "QUOTE":
        root["expression"]["speaker_entity_id"] = "b_anna"
    else:
        root["expression"]["modality"] = "obligation" if production == "PERMISSION" else "permission"
    result = verified(tmp_path, payload)
    assert check(result, "source.before")["result"] == "pass"
    assert check(result, "mapping.before")["result"] == "fail"
    assert basis(result, "before")["representation_basis"] == "candidate_only"


def test_identical_and_or_distortion_on_both_sides_is_detected_independently(tmp_path):
    payload = base_input()
    for side in ("before", "after"):
        text, expression = grammar_example("AND", "en", side)
        side_input = controlled_input(text, expression, side=side)
        payload["representations"][side] = side_input["representations"][side]
        replace_source(payload, side, text)
        payload["representations"][side]["relations"][0]["expression"]["op"] = "OR"
    result = verified(tmp_path, payload)
    for side in ("before", "after"):
        assert check(result, "source." + side)["result"] == "pass"
        assert check(result, "mapping." + side)["result"] == "fail"


@pytest.mark.parametrize("text,language", (
    ("Anna approves", "en"), ("Anna approves..", "en"), ("Anna  approves.", "en"),
    ("anna approves.", "en"), ("Anna approves.\n", "en"), ("Anna approves. Béla wins.", "en"),
    ("She approves.", "en"), ("Anna approves and Béla wins.", "en"),
    ("Anna gives Béla a book.", "en"), ("Anna approves.", "und"),
    (unicodedata.normalize("NFD", "Éva wins."), "en"),
))
def test_unsupported_surface_remains_explicitly_unresolved(tmp_path, text, language):
    payload = controlled_input(text, atom("before"), language=language)
    result = verified(tmp_path, payload)
    assert check(result, "source.before")["result"] == "pass"
    mapping = check(result, "mapping.before")
    assert mapping["status"] == "completed" and mapping["result"] == "unresolved" and mapping["reason"]
    assert basis(result, "before")["claim_scope"] == "candidate_structures"


@pytest.mark.parametrize("family", ("unknown", "empty", "truncated"))
def test_incomplete_interpretation_family_cannot_produce_mapping_success(tmp_path, family):
    payload = base_input()
    payload["interpretations"]["state"] = family
    payload["interpretations"]["reason"] = "Synthetic unresolved interpretation family."
    if family != "truncated":
        payload["interpretations"]["variants"] = []
    result = verified(tmp_path, payload)
    for side in ("before", "after"):
        assert check(result, "mapping." + side)["result"] == "unresolved"
        assert basis(result, side)["representation_basis"] == "candidate_only"


def test_all_variants_are_checked_not_only_the_first():
    payload = base_input()
    representation = payload["representations"]["before"]
    different = deepcopy(representation["relations"][0])
    different["relation_id"] = "b_different"
    different["expression"]["predicate"] = "win"
    representation["relations"].append(different)
    second = deepcopy(payload["interpretations"]["variants"][0])
    second.update(variant_id="variant_2", before_relation_ids=["b_different"])
    payload["interpretations"]["variants"].append(second)
    assert mapped(payload)["result"] != "pass"


def test_alpha_renaming_is_capture_avoiding():
    text = "for every x in {Anna, Béla} (for some y in {Anna, Béla} ((x approves) and (y wins)))."
    expression = {"op": "FORALL", "variable": "y", "domain_id": "b_people", "body": {
        "op": "EXISTS", "variable": "x", "domain_id": "b_people", "body": {
            "op": "AND", "operands": [atom("before", variable="y"), atom("before", predicate="win", variable="x")]}}}
    payload = controlled_input(text, expression)
    assert mapped(payload)["result"] == "pass"
    payload["representations"]["before"]["relations"][0]["expression"]["body"]["body"]["operands"][0]["arguments"][0]["value"] = {"variable": "x"}
    assert mapped(payload)["result"] == "fail"


def test_and_permutation_association_preserve_context_boundaries():
    expression = {"op": "AND", "operands": [atom("before", "eva"), atom("before", "bela", "win"), atom("before")]}
    payload = controlled_input("(Anna approves) and ((Béla wins) and (Éva approves)).", expression)
    assert mapped(payload)["result"] == "pass"
    payload["representations"]["before"]["relations"][0]["expression"]["operands"][0] = context(atom("before", "eva"), modality="permission")
    assert mapped(payload)["result"] == "fail"


def test_ref_resolution_does_not_erase_relation_context():
    payload = base_input()
    relation = payload["representations"]["before"]["relations"][0]
    helper = deepcopy(relation)
    helper["relation_id"] = "b_helper"
    relation["expression"] = {"op": "REF", "relation_id": "b_helper"}
    payload["representations"]["before"]["relations"].append(helper)
    assert mapped(payload)["result"] == "pass"
    helper["modality"] = "permission"
    assert mapped(payload)["result"] == "fail"


@pytest.mark.parametrize("own_anchor", (True, False))
def test_context_anchors_do_not_substitute_for_checked_source_coverage(own_anchor):
    payload = base_input()
    source = deepcopy(payload["sources"][0])
    source.update(source_id="context_source", role="context")
    payload["sources"].append(source)
    anchor = deepcopy(payload["source_anchors"][0])
    anchor.update(anchor_id="context_anchor", source_id="context_source")
    payload["source_anchors"].append(anchor)
    representation = payload["representations"]["before"]
    for record in representation["entities"] + representation["relations"]:
        record["anchor_ids"] = (["anchor_before"] if own_anchor else []) + ["context_anchor"]
    result = mapped(payload)
    assert result["result"] == ("pass" if own_anchor else "fail")
    if own_anchor:
        assert "context_anchor" not in result["details"]["checked_anchor_ids"]
        assert result["details"]["external_context_checked"] is False


def test_source_quantifier_domain_cannot_be_silently_expanded():
    text, expression = grammar_example("FORALL", "en", "before")
    payload = controlled_input(text, expression)
    payload["representations"]["before"]["domains"][0]["entity_ids"].append("b_eva")
    assert mapped(payload)["result"] == "fail"


def thirteen_distinct_ground_atoms() -> str:
    people = ("Anna", "Béla", "Éva", "Dániel")
    clauses = [f"{person} {predicate}" for person in people for predicate in ("approves", "wins")]
    clauses += [f"it is permitted that ({person} approves)" for person in people]
    clauses.append("it is required that (Anna approves)")
    text = clauses[0]
    for clause in clauses[1:]:
        text = f"({text}) and ({clause})"
    return text + "."


def thirteen_quoted_context_occurrences() -> str:
    def join(clauses):
        if len(clauses) == 1:
            return clauses[0]
        split = len(clauses) // 2
        return f"({join(clauses[:split])}) and ({join(clauses[split:])})"

    return join(["Éva says: (Anna approves)"] * 13) + "."


@pytest.mark.parametrize("text,reason_code", (
    ("not (" * 256 + "Anna approves" + ")" * 256 + ".", "source_ast_limit"),
    (thirteen_distinct_ground_atoms(), "expanded_atom_limit"),
    (thirteen_quoted_context_occurrences(), "expanded_atom_limit"),
), ids=("ast_node_limit", "expanded_atom_limit", "distinct_context_occurrences"))
def test_controlled_profile_resource_limits_remain_unresolved(text, reason_code):
    payload = controlled_input(text, atom("before"))
    result = mapped(payload)
    assert result["result"] == "unresolved" and result["reason"]
    assert result["details"]["reason_code"] == reason_code


def test_ref_cannot_capture_a_variable_from_another_relation(tmp_path):
    text, expression = grammar_example("FORALL", "en", "before")
    payload = controlled_input(text, expression)
    representation = payload["representations"]["before"]
    helper = deepcopy(representation["relations"][0])
    helper.update(relation_id="b_helper", expression=atom("before", variable="x"))
    representation["relations"].append(helper)
    representation["relations"][0]["expression"]["body"] = {"op": "REF", "relation_id": "b_helper"}
    with pytest.raises(InputError):
        verify_input(save_input(tmp_path, payload))


def test_submission_claim_of_fulfilled_coverage_is_not_its_own_evidence(tmp_path):
    payload = base_input()
    replace_source(payload, "before", "She approves.")
    result = verified(tmp_path, payload)
    assert payload["coverage_obligations"][0]["state"] == "fulfilled"
    assert check(result, "coverage.coverage_main")["result"] != "pass"


def test_same_labels_do_not_independently_establish_cross_source_identity(tmp_path):
    result = verified(tmp_path, base_input())
    assert check(result, "correspondence.map_entity_anna")["result"] != "pass"


def subject_digest(payload: dict, side: str) -> str:
    """Apply the documented subject projection independently of runtime helpers."""
    record_ids = {
        "sources": "source_id", "source_anchors": "anchor_id", "entities": "entity_id",
        "domains": "domain_id", "relations": "relation_id", "groups": "group_id",
        "variants": "variant_id", "targets": "target_id", "correspondence": "correspondence_id",
        "coverage_obligations": "obligation_id", "claims": "claim_id", "rules": "rule_id",
    }

    def ordered(value, key=""):
        if isinstance(value, dict):
            return {name: ordered(child, name) for name, child in value.items()}
        if isinstance(value, list):
            children = [ordered(child) for child in value]
            if (key.endswith("_ids") or key == "evidence_refs") and all(isinstance(child, str) for child in children):
                return sorted(children)
            if key in record_ids:
                return sorted(children, key=lambda child: child[record_ids[key]])
            return children
        return value

    projection = {"projection_version": "language_relation_subject_v0", "side": side,
                  "input": {key: value for key, value in payload.items() if key != "representation_basis"}}
    return digest(encoded(ordered(projection)))


def evidence_document(schema_version: str, **fields) -> dict:
    return {"schema_version": schema_version, **fields,
            "authority_effect": "none", "release_authority_activation": False}


def write_trust(fixture: dict) -> None:
    directory = fixture["config_path"].parent
    config = evidence_document("language_relation_trust_config_v0", inventory_files=[],
                               verification_files=[], processing_files=[])
    for key, name, field in (("inventory", "inventory.json", "inventory_files"),
                             ("record", "verification.json", "verification_files"),
                             ("processing", "processing.json", "processing_files")):
        if key not in fixture:
            continue
        record = fixture[key]
        jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(record)
        raw = encoded(record)
        (directory / name).write_bytes(raw)
        config[field].append({"path": name, "content_sha256": digest(raw)})
    jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(config)
    fixture["config_path"].write_bytes(encoded(config))


def trusted_fixture(tmp_path: Path, accepted_basis: str = "accepted_reference") -> dict:
    package = tmp_path / "package"
    package.mkdir()
    trust = tmp_path / "trust"
    trust.mkdir()
    payload = base_input()
    method = "independent_reference_review" if accepted_basis == "accepted_reference" else "controlled_source_profile_v0"
    scope = "reference_interpretation" if accepted_basis == "accepted_reference" else "controlled_source_profile"
    subject = subject_digest(payload, "before")
    entry = {"entry_id": "accepted_before", "basis": accepted_basis, "subject_sha256": subject,
             "side": "before", "representation_id": "b_representation", "verification_id": "review_before",
             "method": method, "claim_scope": scope}
    payload["representation_basis"]["before"] = {
        "basis": accepted_basis, "verification_ref": "review_before",
        "acceptance_ref": {"inventory_id": "synthetic_inventory", "entry_id": entry["entry_id"],
                           "content_sha256": digest(encoded(entry))}}
    input_path = save_input(package, payload)
    record = evidence_document(
        "language_relation_source_verification_v0", verification_id="review_before",
        input_ref={"artifact_id": payload["case_id"], "content_sha256": digest(input_path.read_bytes())},
        profile_ref=deepcopy(payload["profile_ref"]), subject_sha256=subject, side="before",
        representation_id="b_representation", basis=accepted_basis, method=method, claim_scope=scope,
        checker_ref={"tool_id": "synthetic_independent_checker", "version": "0",
                     "content_sha256": digest(b"Synthetic independently selected checker identity.")},
        checks=[{"check_id": "review_" + kind, "kind": kind, "status": "completed",
                 "result": "pass", "reason": None}
                for kind in ("source_binding", "subject_binding", "representation_mapping", "coverage")])
    fixture = {"payload": payload, "input_path": input_path, "package": package,
               "config_path": trust / "config.json", "record": record,
               "inventory": evidence_document("language_relation_acceptance_inventory_v0",
                                              inventory_id="synthetic_inventory", entries=[entry])}
    write_trust(fixture)
    return fixture


def verify_trusted(fixture: dict) -> dict:
    result = verify_input(fixture["input_path"], package_root=fixture["package"], trust_config=fixture["config_path"])
    jsonschema.Draft202012Validator(VERIFICATION_SCHEMA).validate(result)
    return result


def rebind_review_to_payload(fixture: dict) -> None:
    payload = fixture["payload"]
    subject = subject_digest(payload, "before")
    entry = fixture["inventory"]["entries"][0]
    entry["subject_sha256"] = subject
    payload["representation_basis"]["before"]["acceptance_ref"]["content_sha256"] = digest(encoded(entry))
    fixture["input_path"].write_bytes(encoded(payload))
    fixture["record"]["subject_sha256"] = subject
    fixture["record"]["input_ref"]["content_sha256"] = digest(fixture["input_path"].read_bytes())
    write_trust(fixture)


@pytest.mark.parametrize("accepted_basis,scope", (("accepted_reference", "reference_interpretation"),
                                                ("profile_verified", "controlled_source_profile")))
def test_independently_configured_exact_acceptance_preserves_its_scope(tmp_path, accepted_basis, scope):
    fixture = trusted_fixture(tmp_path, accepted_basis)
    result = verify_trusted(fixture)
    assert check(result, "acceptance.before")["result"] == "pass"
    assert basis(result, "before")["representation_basis"] == accepted_basis
    assert basis(result, "before")["claim_scope"] == scope
    assert basis(result, "after")["representation_basis"] == "candidate_only"
    assert result["status_axes"]["authority_status"] == "none"
    pins = {"sha256:" + digest(path.read_bytes()) for path in (
        fixture["config_path"].parent / "inventory.json",
        fixture["config_path"].parent / "verification.json")}
    pins.add("trust-config.sha256:" + digest(fixture["config_path"].read_bytes()))
    assert pins <= set(check(result, "acceptance.before")["evidence_refs"])


def test_a_bundled_inventory_cannot_select_its_own_trust_root(tmp_path):
    fixture = trusted_fixture(tmp_path)
    (fixture["package"] / "inventory.json").write_bytes(encoded(fixture["inventory"]))
    (fixture["package"] / "verification.json").write_bytes(encoded(fixture["record"]))
    result = verify_input(fixture["input_path"], package_root=fixture["package"])
    assert check(result, "acceptance.before")["result"] != "pass"
    assert basis(result, "before")["representation_basis"] == "candidate_only"


def test_explicit_trust_config_inside_submitted_package_is_rejected(tmp_path):
    fixture = trusted_fixture(tmp_path)
    path = fixture["package"] / "trust.json"
    path.write_bytes(fixture["config_path"].read_bytes())
    with pytest.raises(InputError):
        verify_input(fixture["input_path"], package_root=fixture["package"], trust_config=path)


def test_trusted_payload_symlink_cannot_point_into_package(tmp_path):
    fixture = trusted_fixture(tmp_path)
    target = fixture["package"] / "verification.json"
    target.write_bytes(encoded(fixture["record"]))
    path = fixture["config_path"].parent / "verification.json"
    path.unlink()
    path.symlink_to(target)
    with pytest.raises(InputError):
        verify_trusted(fixture)


def test_trust_configuration_parent_symlink_is_rejected(tmp_path):
    fixture = trusted_fixture(tmp_path)
    alias = tmp_path / "linked_trust"
    alias.symlink_to(fixture["config_path"].parent, target_is_directory=True)
    with pytest.raises(InputError):
        verify_input(fixture["input_path"], package_root=fixture["package"], trust_config=alias / "config.json")


@pytest.mark.parametrize("mutation", ("input_hash", "profile_hash", "subject", "side", "representation",
                                      "method", "scope", "basis", "missing_kind", "not_run", "failed", "unresolved"))
def test_named_record_must_prove_the_requested_subject_and_completed_method(tmp_path, mutation):
    fixture = trusted_fixture(tmp_path)
    record = fixture["record"]
    if mutation == "input_hash":
        record["input_ref"]["content_sha256"] = "0" * 64
    elif mutation == "profile_hash":
        record["profile_ref"]["content_sha256"] = "0" * 64
    elif mutation == "subject":
        record["subject_sha256"] = "0" * 64
    elif mutation == "side":
        record["side"] = "after"
    elif mutation == "representation":
        record["representation_id"] = "a_representation"
    elif mutation == "method":
        record["method"] = "controlled_source_profile_v0"
    elif mutation == "scope":
        record["claim_scope"] = "controlled_source_profile"
    elif mutation == "basis":
        record["basis"] = "profile_verified"
    elif mutation == "missing_kind":
        record["checks"] = [row for row in record["checks"] if row["kind"] != "representation_mapping"]
    elif mutation == "not_run":
        record["checks"][0].update(status="not_run", result=None, reason="Never performed.")
    else:
        record["checks"][0].update(result="fail" if mutation == "failed" else "unresolved", reason="Unclosed check.")
    write_trust(fixture)
    result = verify_trusted(fixture)
    assert check(result, "acceptance.before")["result"] != "pass"
    assert basis(result, "before")["representation_basis"] == "candidate_only"


@pytest.mark.parametrize("mutation", ("source", "revision", "roots", "request"))
def test_acceptance_subject_binds_more_than_representation_bytes(tmp_path, mutation):
    fixture = trusted_fixture(tmp_path)
    payload = fixture["payload"]
    if mutation == "source":
        replace_source(payload, "before", "Anna wins.")
        payload["representations"]["before"]["relations"][0]["expression"]["predicate"] = "win"
    elif mutation == "revision":
        payload["sources"][0]["revision"] = "another_utterance_instance"
    elif mutation == "roots":
        helper = deepcopy(payload["representations"]["before"]["relations"][0])
        helper["relation_id"] = "b_other_root"
        payload["representations"]["before"]["relations"].append(helper)
        payload["interpretations"]["variants"][0]["before_relation_ids"] = ["b_other_root"]
    else:
        payload["measurement_request"]["targets"][0]["description"] = "A different requested subject."
    fixture["input_path"].write_bytes(encoded(payload))
    # Rebind the raw input deliberately: the old semantic subject must still fail.
    fixture["record"]["input_ref"]["content_sha256"] = digest(fixture["input_path"].read_bytes())
    write_trust(fixture)
    result = verify_trusted(fixture)
    assert check(result, "source.before")["result"] == "pass"
    assert check(result, "acceptance.before")["result"] == "fail"
    assert basis(result, "before")["representation_basis"] == "candidate_only"


@pytest.mark.parametrize("accepted_basis", ("accepted_reference", "profile_verified"))
def test_trusted_record_cannot_override_a_current_controlled_mapping_mismatch(tmp_path, accepted_basis):
    fixture = trusted_fixture(tmp_path, accepted_basis)
    payload = fixture["payload"]
    payload["representations"]["before"]["relations"][0]["expression"]["predicate"] = "win"
    rebind_review_to_payload(fixture)
    result = verify_trusted(fixture)
    assert check(result, "mapping.before")["result"] == "fail"
    assert basis(result, "before")["representation_basis"] == "candidate_only"


@pytest.mark.parametrize("accepted_basis,expected", (("accepted_reference", "accepted_reference"),
                                                    ("profile_verified", "candidate_only")))
def test_reference_review_and_controlled_profile_have_distinct_supported_scopes(tmp_path, accepted_basis, expected):
    fixture = trusted_fixture(tmp_path, accepted_basis)
    payload = fixture["payload"]
    replace_source(payload, "before", "She approves.")
    rebind_review_to_payload(fixture)
    result = verify_trusted(fixture)
    assert check(result, "mapping.before")["result"] == "unresolved"
    assert basis(result, "before")["representation_basis"] == expected


@pytest.mark.parametrize("mutation", ("unselected_helper", "joint_context_constraint", "target_context",
                                      "variant_without_target", "used_context_anchor"))
def test_profile_acceptance_cannot_exceed_the_checked_closure(tmp_path, mutation):
    fixture = trusted_fixture(tmp_path, "profile_verified")
    payload = fixture["payload"]
    if mutation == "unselected_helper":
        relation = deepcopy(payload["representations"]["before"]["relations"][0])
        relation["relation_id"] = "b_unselected_helper"
        payload["representations"]["before"]["relations"].append(relation)
        payload["measurement_request"]["targets"][0]["before_ids"] = [relation["relation_id"]]
    elif mutation == "joint_context_constraint":
        payload["interpretations"]["variants"][0]["context_constraints"] = [atom("before")]
    elif mutation == "variant_without_target":
        relation = deepcopy(payload["representations"]["before"]["relations"][0])
        relation["relation_id"] = "b_another_variant_root"
        payload["representations"]["before"]["relations"].append(relation)
        variant = deepcopy(payload["interpretations"]["variants"][0])
        variant.update(variant_id="variant_2", before_relation_ids=[relation["relation_id"]])
        payload["interpretations"]["variants"].append(variant)
    else:
        source = deepcopy(payload["sources"][0])
        source.update(source_id="external_context", role="context")
        payload["sources"].append(source)
        if mutation == "target_context":
            payload["measurement_request"]["targets"][0]["context_source_ids"] = [source["source_id"]]
        else:
            anchor = deepcopy(payload["source_anchors"][0])
            anchor.update(anchor_id="external_context_anchor", source_id=source["source_id"])
            payload["source_anchors"].append(anchor)
            representation = payload["representations"]["before"]
            for row in representation["relations"] + representation["entities"]:
                row["anchor_ids"].append(anchor["anchor_id"])
    rebind_review_to_payload(fixture)
    result = verify_trusted(fixture)
    assert basis(result, "before")["representation_basis"] == "candidate_only"
    if mutation in {"variant_without_target", "used_context_anchor"}:
        assert check(result, "mapping.before")["result"] == "pass"
        assert check(result, "coverage.coverage_main")["result"] != "pass"


def add_unchecked_auxiliary_target(payload: dict, side: str, granularity: str) -> None:
    main = payload["measurement_request"]["targets"][0]
    auxiliary = deepcopy(main)
    auxiliary.update(target_id="target_aux", required_obligation_ids=["coverage_aux"],
                     granularity=granularity)
    main["granularity"] = granularity
    for selected in ("before", "after"):
        representation = payload["representations"][selected]
        main_ids = list(main[f"{selected}_ids"])
        auxiliary_ids = list(main_ids)
        if side in (selected, "both"):
            helper = deepcopy(representation["relations"][0])
            helper["relation_id"] = selected[0] + "_unchecked_helper"
            representation["relations"].append(helper)
            auxiliary_ids.append(helper["relation_id"])
        if granularity == "relation_group":
            for name, relation_ids, target in (("main", main_ids, main),
                                                ("aux", auxiliary_ids, auxiliary)):
                group_id = selected[0] + "_" + name + "_group"
                representation["groups"].append({"group_id": group_id, "relation_ids": relation_ids})
                target[f"{selected}_ids"] = [group_id]
        else:
            auxiliary[f"{selected}_ids"] = auxiliary_ids
    payload["measurement_request"]["targets"].append(auxiliary)
    obligation = payload["coverage_obligations"][0]
    obligation.update(side=side, source_ids=["source_" + selected for selected in ("before", "after")
                                            if side in (selected, "both")])
    payload["coverage_obligations"].append(
        dict(obligation, obligation_id="coverage_aux", target_id="target_aux"))


@pytest.mark.parametrize("side", ("before", "after", "both"))
@pytest.mark.parametrize("granularity", ("relation", "relation_group"))
@pytest.mark.parametrize("auxiliary_first", (False, True))
def test_coverage_closure_is_local_to_obligation_target(tmp_path, side, granularity, auxiliary_first):
    payload = base_input()
    payload["coverage_obligations"][0].update(
        side=side, source_ids=["source_" + selected for selected in ("before", "after")
                               if side in (selected, "both")])
    original = check(verified(tmp_path, payload), "coverage.coverage_main")
    assert original["result"] == "pass"
    add_unchecked_auxiliary_target(payload, side, granularity)
    if auxiliary_first:
        payload["measurement_request"]["targets"].reverse()
        payload["coverage_obligations"].reverse()
    result = verified(tmp_path, payload)
    for selected in ("before", "after"):
        assert check(result, "mapping." + selected)["result"] == "pass"
    assert check(result, "coverage.coverage_main") == original
    auxiliary = check(result, "coverage.coverage_aux")
    assert auxiliary["target_ids"] == ["target_aux"]
    assert auxiliary["result"] == "unresolved"
    assert auxiliary["evidence_refs"] == []


@pytest.mark.parametrize("granularity", ("relation", "relation_group"))
def test_profile_basis_still_requires_every_selected_target(tmp_path, granularity):
    fixture = trusted_fixture(tmp_path, "profile_verified")
    add_unchecked_auxiliary_target(fixture["payload"], "before", granularity)
    rebind_review_to_payload(fixture)
    result = verify_trusted(fixture)
    assert check(result, "acceptance.before")["result"] == "pass"
    assert check(result, "mapping.before")["result"] == "pass"
    assert check(result, "coverage.coverage_main")["result"] == "pass"
    assert check(result, "coverage.coverage_aux")["result"] == "unresolved"
    assert basis(result, "before")["representation_basis"] == "candidate_only"


@pytest.mark.parametrize("family", ("unknown", "empty", "truncated"))
def test_independent_review_does_not_close_an_incomplete_interpretation_family(tmp_path, family):
    fixture = trusted_fixture(tmp_path)
    payload = fixture["payload"]
    payload["interpretations"].update(state=family, reason="Exhaustiveness not established.")
    if family != "truncated":
        payload["interpretations"]["variants"] = []
    rebind_review_to_payload(fixture)
    result = verify_trusted(fixture)
    assert check(result, "source.before")["result"] == "pass"
    assert check(result, "mapping.before")["result"] == "unresolved"
    assert check(result, "coverage.coverage_main")["result"] != "pass"


def test_trust_file_pin_binds_raw_bytes_not_equivalent_json(tmp_path):
    fixture = trusted_fixture(tmp_path)
    path = fixture["config_path"].parent / "verification.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(InputError):
        verify_trusted(fixture)


def processing_fixture(tmp_path: Path) -> dict:
    package = tmp_path / "package"
    package.mkdir()
    trust = tmp_path / "trust"
    trust.mkdir()
    payload = base_input()
    context_data = b"Synthetic context."
    payload["sources"].append({"source_id": "context_1", "role": "context", "language": "en",
                               "revision": "context_revision_1", "encoding": "utf-8",
                               "content": {"kind": "inline_utf8", "text": context_data.decode()},
                               "byte_length": len(context_data), "content_sha256": digest(context_data)})
    payload["measurement_request"]["processing_claim"] = "processing_change"
    payload["measurement_request"]["targets"][0]["context_source_ids"] = ["context_1"]
    payload["processing_binding"] = {"processing_id": "processing_1", "before_source_id": "source_before",
                                      "after_source_id": "source_after", "context_source_ids": ["context_1"],
                                      "evidence_refs": ["processing_evidence_1"]}
    input_path = save_input(package, payload)
    record = evidence_document("language_relation_processing_record_v0", evidence_id="processing_evidence_1",
        processing_id="processing_1", operation="synthetic_language_rewrite",
        input_ref={"artifact_id": payload["case_id"], "content_sha256": digest(input_path.read_bytes())},
        profile_ref=deepcopy(payload["profile_ref"]),
        source_bindings=[{key: source[key] for key in ("source_id", "role", "language", "revision", "content_sha256", "byte_length")}
                         for source in payload["sources"]],
        execution={"status": "completed", "result": "pass", "reason": None})
    fixture = {"payload": payload, "input_path": input_path, "package": package,
               "config_path": trust / "config.json", "processing": record}
    write_trust(fixture)
    return fixture


def test_processing_evidence_binds_actual_operation_sources_and_context(tmp_path):
    fixture = processing_fixture(tmp_path)
    result = verify_trusted(fixture)
    assert check(result, "processing")["result"] == "pass"
    assert check(result, "source.context")["result"] == "pass"
    assert result["status_axes"]["causal_status"] == "not_evaluated"


@pytest.mark.parametrize("side", ("before", "after", "both", "context"))
@pytest.mark.parametrize("binding_state", ("bound", "record_missing", "both_missing"))
def test_processing_covers_context_required_by_any_obligation_side(tmp_path, side, binding_state):
    fixture = processing_fixture(tmp_path)
    payload = fixture["payload"]
    payload["measurement_request"]["targets"][0]["context_source_ids"] = []
    obligation = payload["coverage_obligations"][0]
    obligation.update(side=side, source_ids=["source_" + selected for selected in ("before", "after")
                                            if side in (selected, "both")] + ["context_1"])
    if binding_state != "bound":
        fixture["processing"]["source_bindings"] = [
            row for row in fixture["processing"]["source_bindings"] if row["role"] != "context"]
    if binding_state == "both_missing":
        payload["processing_binding"]["context_source_ids"] = []
    fixture["input_path"].write_bytes(encoded(payload))
    fixture["processing"]["input_ref"]["content_sha256"] = digest(fixture["input_path"].read_bytes())
    write_trust(fixture)
    if binding_state == "both_missing":
        with pytest.raises(InputError, match="processing binding omits a required context source"):
            verify_trusted(fixture)
    else:
        result = verify_trusted(fixture)
        assert check(result, "source.context")["result"] == "pass"
        processing = check(result, "processing")
        assert processing["status"] == "completed"
        assert processing["result"] == ("pass" if binding_state == "bound" else "fail")


def test_unreferenced_context_is_not_added_to_processing_requirements(tmp_path):
    fixture = processing_fixture(tmp_path)
    payload = fixture["payload"]
    payload["measurement_request"]["targets"][0]["context_source_ids"] = []
    payload["processing_binding"]["context_source_ids"] = []
    fixture["processing"]["source_bindings"] = [
        row for row in fixture["processing"]["source_bindings"] if row["role"] != "context"]
    fixture["input_path"].write_bytes(encoded(payload))
    fixture["processing"]["input_ref"]["content_sha256"] = digest(fixture["input_path"].read_bytes())
    write_trust(fixture)
    assert check(verify_trusted(fixture), "processing")["result"] == "pass"


@pytest.mark.parametrize("mutation", ("processing_id", "input", "profile", "source_hash", "source_revision",
                                      "source_id", "role", "omit_context", "not_run", "failed", "unresolved"))
def test_processing_record_of_another_subject_cannot_substitute(tmp_path, mutation):
    fixture = processing_fixture(tmp_path)
    record = fixture["processing"]
    if mutation == "processing_id":
        record["processing_id"] = "another_processing_instance"
    elif mutation in {"input", "profile"}:
        record[mutation + "_ref"]["content_sha256"] = "0" * 64
    elif mutation == "source_hash":
        record["source_bindings"][0]["content_sha256"] = "0" * 64
    elif mutation == "source_revision":
        record["source_bindings"][0]["revision"] = "another_source_instance"
    elif mutation == "source_id":
        record["source_bindings"][0]["source_id"] = "another_source_id"
    elif mutation == "role":
        record["source_bindings"][0]["role"] = "after"
    elif mutation == "omit_context":
        record["source_bindings"] = [row for row in record["source_bindings"] if row["role"] != "context"]
    elif mutation == "not_run":
        record["execution"].update(status="not_run", result=None, reason="No execution took place.")
    else:
        record["execution"].update(result="fail" if mutation == "failed" else "unresolved", reason="Execution not established.")
    write_trust(fixture)
    result = verify_trusted(fixture)
    assert check(result, "processing")["result"] != "pass"
    assert result["status_axes"]["causal_status"] == "not_evaluated"


def test_named_processing_evidence_without_independent_resolution_is_unresolved(tmp_path):
    fixture = processing_fixture(tmp_path)
    result = verify_input(fixture["input_path"], package_root=fixture["package"])
    assert check(result, "processing")["result"] == "unresolved"


def test_package_source_bytes_are_bound_without_text_normalization(tmp_path):
    payload = base_input()
    package = tmp_path / "package"
    package.mkdir()
    source_path = package / "source.txt"
    original = b"Anna approves."
    source_path.write_bytes(original)
    payload["sources"][0]["content"] = {"kind": "package_path", "path": "source.txt"}
    input_path = package / "input.json"
    input_path.write_bytes(encoded(payload))
    result = verify_input(input_path, package_root=package)
    assert check(result, "source.before")["result"] == "pass"
    source_path.write_bytes(original + b"\n")
    result = verify_input(input_path, package_root=package)
    assert check(result, "source.before")["result"] == "fail"
    assert check(result, "mapping.before")["result"] is None


@pytest.mark.parametrize("path", ("../source.txt", "/source.txt", "a/../../source.txt",
                                  "a\\source.txt", "C:/source.txt", "a//source.txt"))
def test_package_source_paths_cannot_escape_or_change_interpretation(tmp_path, path):
    payload = base_input()
    payload["sources"][0]["content"] = {"kind": "package_path", "path": path}
    with pytest.raises(InputError):
        verify_input(save_input(tmp_path, payload), package_root=tmp_path)


@pytest.mark.parametrize("kind", ("file", "parent"))
def test_package_source_symlinks_are_not_followed(tmp_path, kind):
    package = tmp_path / "package"
    package.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "source.txt").write_bytes(b"Anna approves.")
    if kind == "file":
        (package / "source.txt").symlink_to(outside / "source.txt")
        relative = "source.txt"
    else:
        (package / "linked").symlink_to(outside, target_is_directory=True)
        relative = "linked/source.txt"
    payload = base_input()
    payload["sources"][0]["content"] = {"kind": "package_path", "path": relative}
    input_path = package / "input.json"
    input_path.write_bytes(encoded(payload))
    with pytest.raises(InputError):
        verify_input(input_path, package_root=package)


@pytest.mark.parametrize("outcome", ("pass", "fail", "unresolved"))
def test_cli_distinguishes_completed_diagnosis_from_invalid_input(tmp_path, outcome):
    payload = base_input()
    if outcome == "fail":
        payload["sources"][0]["content_sha256"] = "0" * 64
    elif outcome == "unresolved":
        replace_source(payload, "before", "She approves.")
    input_path = save_input(tmp_path, payload)
    output = tmp_path / "verification.json"
    run = subprocess.run([sys.executable, str(CLI), "--input", str(input_path), "--output", str(output)],
                         cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 0, (run.stdout, run.stderr)
    result = json.loads(output.read_text())
    jsonschema.Draft202012Validator(VERIFICATION_SCHEMA).validate(result)
    selected = "source.before" if outcome == "fail" else "mapping.before"
    assert check(result, selected)["result"] == outcome
    assert result["authority_effect"] == "none"


def test_cli_invalid_input_has_distinct_exit_and_no_success_artifact(tmp_path):
    input_path = tmp_path / "input.json"
    input_path.write_text('{"duplicate": 1, "duplicate": 2}')
    output = tmp_path / "verification.json"
    run = subprocess.run([sys.executable, str(CLI), "--input", str(input_path), "--output", str(output)],
                         cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 2
    assert not output.exists()


def test_cli_missing_input_reports_execution_failure(tmp_path):
    output = tmp_path / "verification.json"
    run = subprocess.run([sys.executable, str(CLI), "--input", str(tmp_path / "missing.json"),
                          "--output", str(output)], cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 3
    assert not output.exists()


def test_cli_output_cannot_overwrite_a_source_carrier(tmp_path):
    payload = base_input()
    source_path = tmp_path / "source.txt"
    source_bytes = b"Anna approves."
    source_path.write_bytes(source_bytes)
    payload["sources"][0]["content"] = {"kind": "package_path", "path": source_path.name}
    input_path = save_input(tmp_path, payload)
    run = subprocess.run([sys.executable, str(CLI), "--input", str(input_path), "--package-root", str(tmp_path),
                          "--output", str(source_path)], cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 2
    assert source_path.read_bytes() == source_bytes
    assert input_path.read_bytes() == encoded(payload)


def test_cli_output_cannot_overwrite_independent_evidence(tmp_path):
    fixture = trusted_fixture(tmp_path)
    evidence_path = fixture["config_path"].parent / "verification.json"
    original = evidence_path.read_bytes()
    run = subprocess.run([sys.executable, str(CLI), "--input", str(fixture["input_path"]),
                          "--package-root", str(fixture["package"]), "--trust-config", str(fixture["config_path"]),
                          "--output", str(evidence_path)], cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 2
    assert evidence_path.read_bytes() == original


def test_repeated_verification_is_deterministic_without_replay_claim(tmp_path):
    path = save_input(tmp_path, base_input())
    first, second = verify_input(path), verify_input(path)
    assert encoded(first) == encoded(second)
    assert first["status_axes"]["reproduction_status"] not in {"reproduced", "bounded_replay_only"}


def test_generated_check_ids_do_not_collide_with_hash_shaped_input_ids(tmp_path):
    payload = base_input()
    for number in range(100):
        long_id = "A" * 120 + str(number)
        digest_id = digest(long_id.encode("ascii"))
        if digest_id[0] in "abcdef":
            break
    else:
        raise AssertionError("Synthetic ID search exhausted.")
    original = payload["coverage_obligations"][0]
    payload["coverage_obligations"] = [dict(original, obligation_id=identifier) for identifier in (long_id, digest_id)]
    payload["measurement_request"]["targets"][0]["required_obligation_ids"] = [long_id, digest_id]
    with pytest.raises(InputError):
        verify_input(save_input(tmp_path, payload))


def test_new_test_registered_once_and_keeps_existing_manifest_members():
    for name in ("tools-tests.list", "pytest-tests.list"):
        entries = [entry for raw in (ROOT / "ci" / name).read_text().splitlines()
                   if (entry := raw.split("#", 1)[0].strip())]
        assert len(entries) == len(set(entries))
        assert entries.count(SELF) == 1
        for existing in ("tests/test_language_relation_contract_v0.py", "tests/test_anchor_integrity_v0_1_contract.py",
                         "tests/test_paradox_w1_records_v0.py", "tests/test_paradox_w1_native_v0.py"):
            assert entries.count(existing) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
