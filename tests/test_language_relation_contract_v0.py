"""Offline LRM-01 contract regressions, not a language measurement runtime.

The helpers below inspect the shipped synthetic fixtures and contract records.
They do not verify arbitrary natural-language meaning, execute a comparator,
establish observed consequences, or produce release-authority evidence.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
EXAMPLE_DIR = ROOT / "examples" / "language_relation_measurement_v0"
BASELINE = ROOT / "contracts" / "language_relation_measurement_v0_baseline.json"
PROFILE = ROOT / "contracts" / "language_relation_profile_v0.json"
TEST_PATH = "tests/test_language_relation_contract_v0.py"
SOURCE_COMMIT = "47a3add6667542df6ef176285ed02bb1a741d9cf"
SOURCE_TREE = "6d425c83e16fdc95cb2cfe1645a8060f3336dfaf"
SCHEMA_FILES = (
    "language_relation_input_v0.schema.json",
    "language_relation_verification_v0.schema.json",
    "language_relation_measurement_v0.schema.json",
    "language_relation_manifest_v0.schema.json",
)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _strict_json(text: str) -> object:
    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_nonfinite,
    )


def load_json(path: Path) -> dict:
    value = _strict_json(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value


def _walk(value: object):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


@lru_cache(maxsize=4)
def validator(schema_file: str) -> jsonschema.Draft202012Validator:
    assert schema_file in SCHEMA_FILES
    schema = load_json(SCHEMA_DIR / schema_file)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def assert_valid(schema_file: str, payload: dict) -> None:
    errors = list(validator(schema_file).iter_errors(payload))
    assert not errors, [
        {"path": list(error.absolute_path), "message": error.message}
        for error in errors
    ]


def assert_invalid(schema_file: str, payload: dict) -> None:
    assert list(validator(schema_file).iter_errors(payload)), (
        f"prohibited contract instance accepted by {schema_file}"
    )


def contract_examples() -> list[dict]:
    return load_json(EXAMPLE_DIR / "contract_examples.json")["examples"]


def example_for(schema_file: str) -> dict:
    matches = [row["artifact"] for row in contract_examples()
               if row["schema_file"] == schema_file]
    assert matches, schema_file
    return deepcopy(matches[0])


def _manifest_entries(path: Path) -> list[str]:
    return [entry for raw in path.read_text(encoding="utf-8").splitlines()
            if (entry := raw.split("#", 1)[0].strip())]


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
def test_schema_is_draft_2020_12_and_offline(schema_file: str) -> None:
    schema = load_json(SCHEMA_DIR / schema_file)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    jsonschema.Draft202012Validator.check_schema(schema)
    # $schema/$id are identifiers; instance validation must not fetch resources.
    for node in _walk(schema):
        if isinstance(node, dict) and "$ref" in node:
            assert node["$ref"].startswith("#"), node["$ref"]


def test_all_shipped_json_uses_strict_json_loading() -> None:
    paths = [BASELINE, PROFILE]
    paths.extend(SCHEMA_DIR / name for name in SCHEMA_FILES)
    paths.extend(EXAMPLE_DIR / name for name in (
        "cases.json", "expected.json", "contract_examples.json"))
    for path in paths:
        load_json(path)


@pytest.mark.parametrize("text", (
    '{"id": "first", "id": "second"}',
    '{"nested": {"result": null, "result": "PRESERVED"}}',
    '{"value": NaN}',
    '{"value": Infinity}',
    '{"value": -Infinity}',
))
def test_fixture_loader_rejects_duplicate_keys_and_nonfinite_numbers(text: str) -> None:
    with pytest.raises(ValueError):
        _strict_json(text)


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
def test_each_schema_has_valid_synthetic_examples(schema_file: str) -> None:
    rows = [row for row in contract_examples() if row["schema_file"] == schema_file]
    assert rows, schema_file
    for row in rows:
        assert_valid(schema_file, row["artifact"])


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
def test_unknown_top_level_property_is_rejected(schema_file: str) -> None:
    payload = example_for(schema_file)
    payload["undeclared_authority_shortcut"] = True
    assert_invalid(schema_file, payload)


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
def test_schema_version_is_required(schema_file: str) -> None:
    payload = example_for(schema_file)
    del payload["schema_version"]
    assert_invalid(schema_file, payload)


def test_fixture_wrappers_preserve_synthetic_provenance() -> None:
    examples = load_json(EXAMPLE_DIR / "contract_examples.json")
    assert examples["schema_version"] == "language_relation_contract_examples_v0"
    assert examples["provenance"] == "synthetic_contract_example"
    ids = [row["example_id"] for row in examples["examples"]]
    assert len(ids) == len(set(ids))
    assert {row["schema_file"] for row in examples["examples"]} == set(SCHEMA_FILES)
    cases = load_json(EXAMPLE_DIR / "cases.json")
    expected = load_json(EXAMPLE_DIR / "expected.json")
    assert cases["schema_version"] == "language_relation_reference_cases_v0"
    assert expected["schema_version"] == "language_relation_expected_v0"
    for wrapper in (cases, expected):
        assert wrapper["provenance"] == "synthetic_reference"
        assert wrapper["reference_status"] == "draft_synthetic_references"
    assert expected["execution_status"] == "not_run"


def test_expected_oracle_is_separate_from_reference_inputs() -> None:
    cases_path = EXAMPLE_DIR / "cases.json"
    expected_path = EXAMPLE_DIR / "expected.json"
    assert cases_path.resolve() != expected_path.resolve()
    forbidden = {"expectations", "target_expectations", "expected_result",
                 "expected_relation_state", "expected_state", "oracle_label"}
    for node in _walk(load_json(cases_path)):
        if isinstance(node, dict):
            assert forbidden.isdisjoint(node), forbidden.intersection(node)


def test_expected_records_bind_cases_targets_and_conditional_scopes() -> None:
    cases = _unique_index(load_json(EXAMPLE_DIR / "cases.json")["cases"], "case_id")
    expected = _unique_index(load_json(EXAMPLE_DIR / "expected.json")["expectations"], "case_id")
    assert set(cases) == set(expected)
    permitted_states = {"PRESERVED", "CHANGED", "BROKEN", "UNDETERMINED"}
    observed_states = set()
    obligations = set(load_json(BASELINE)["acceptance_obligations"])
    for case_id, row in expected.items():
        assert row["assumptions"] and all(isinstance(item, str) and item for item in row["assumptions"])
        assert row["rationale"]
        assert row["acceptance_ids"] and set(row["acceptance_ids"]) <= obligations
        inputs = _unique_index(cases[case_id]["measurement_request"]["targets"], "target_id")
        outputs = _unique_index(row["target_expectations"], "target_id")
        assert set(inputs) == set(outputs)
        for target in outputs.values():
            assert target["relation_state"] in permitted_states
            observed_states.add(target["relation_state"])
            assert target["claim_scope"] == "reference_interpretation"
            if target["assessment_state"] == "IDENTIFIED":
                assert target["relation_state"] != "UNDETERMINED"
            else:
                assert target["assessment_state"] in {"UNBOUND", "INCOMPATIBLE", "UNRESOLVED"}
                assert target["relation_state"] == "UNDETERMINED"
        # Expected conditional judgments do not upgrade the supplied candidates.
        assert all(basis["basis"] == "candidate_only"
                   for basis in cases[case_id]["representation_basis"].values())
    assert observed_states == permitted_states


def _encoded_fixture(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def test_synthetic_artifact_references_bind_exact_fixture_inputs() -> None:
    # A schema example is a distinct input artifact, including its provenance.
    # Resolve the actual referenced object; do not substitute a reference-corpus
    # case that happens to carry the same source text.
    inputs = list(load_json(EXAMPLE_DIR / "cases.json")["cases"])
    inputs.extend(row["artifact"] for row in contract_examples()
                  if row["schema_file"] == "language_relation_input_v0.schema.json")
    cases = _unique_index(inputs, "case_id")
    for row in contract_examples():
        artifact = row["artifact"]
        assert artifact["profile_ref"]["content_sha256"] == hashlib.sha256(PROFILE.read_bytes()).hexdigest()
        if "input_ref" not in artifact:
            continue
        reference = artifact["input_ref"]
        assert reference["artifact_id"] in cases
        source_input = cases[reference["artifact_id"]]
        assert reference["content_sha256"] == hashlib.sha256(_encoded_fixture(source_input)).hexdigest()
        targets = _unique_index(source_input["measurement_request"]["targets"], "target_id")
        if artifact["artifact_kind"] == "language_relation_verification":
            checks = _unique_index(artifact["checks"], "check_id")
            assert {item["side"] for item in artifact["basis_records"]} == {"before", "after"}
            for check in checks.values():
                assert set(check["target_ids"]) <= set(targets)
            for basis in artifact["basis_records"]:
                assert set(basis["check_ids"]) <= set(checks)
        else:
            results = _unique_index(artifact["results"] or [], "target_id")
            assert set(results) <= set(targets)
            witnesses = _unique_index(artifact["witnesses"], "witness_id")
            variants = _unique_index(source_input["interpretations"]["variants"], "variant_id")
            coverage = _unique_index(source_input["coverage_obligations"], "obligation_id")
            for result in results.values():
                assert set(result["witness_ids"]) <= set(witnesses)
                assert set(result["compatible_variant_ids"]) <= set(variants)
                assert set(result["coverage_obligation_ids"]) <= set(coverage)
                assert set(result["closed_obligation_ids"]) <= set(result["coverage_obligation_ids"])
            for witness in witnesses.values():
                assert witness["target_id"] in targets
                assert set(witness["variant_ids"]) <= set(variants)
                for side in ("before", "after"):
                    relations = {item["relation_id"] for item in source_input["representations"][side]["relations"]}
                    assert set(witness[f"{side}_relation_ids"]) <= relations


def test_manifest_example_payload_digests_are_real_fixture_bytes() -> None:
    examples = {row["example_id"]: row["artifact"] for row in contract_examples()}
    payload_bytes = {
        "input.json": _encoded_fixture(examples["input_candidate"]),
        "verification.json": _encoded_fixture(examples["verification_not_run"]),
        "measurement.json": _encoded_fixture(examples["measurement_not_run"]),
        "profile.json": PROFILE.read_bytes(),
    }
    manifest = examples["manifest_shape"]
    assert {row["path"] for row in manifest["payloads"]} == set(payload_bytes)
    assert len(manifest["payloads"]) == len(payload_bytes)
    for payload in manifest["payloads"]:
        data = payload_bytes[payload["path"]]
        assert payload["size_bytes"] == len(data)
        assert payload["content_sha256"] == hashlib.sha256(data).hexdigest()
    assert set(manifest["replay"]["deterministic_payload_paths"]) <= set(payload_bytes)
    assert "replay_receipt.json" not in payload_bytes
    assert "manifest.json" not in payload_bytes


def test_ternary_fixture_has_equal_pairwise_projections_but_different_tuples() -> None:
    cases = _unique_index(load_json(EXAMPLE_DIR / "cases.json")["cases"], "case_id")
    controls = [row for row in load_json(EXAMPLE_DIR / "expected.json")["expectations"]
                if "ternary_control" in row]
    assert controls
    for row in controls:
        control = row["ternary_control"]
        tuples = {}
        for side in ("before", "after"):
            representation = cases[row["case_id"]]["representations"][side]
            entities = _unique_index(representation["entities"], "entity_id")
            actual = set()
            for relation in representation["relations"]:
                expression = relation["expression"]
                assert expression["op"] == "ATOM" and expression["predicate"] == "tuple"
                arguments = {argument["role"]: argument["value"]["entity_id"]
                             for argument in expression["arguments"]}
                actual.add(tuple(int(entities[arguments[role]]["label"])
                                 for role in ("first", "second", "third")))
            tuples[side] = {tuple(item) for item in control[f"{side}_tuples"]}
            assert actual == tuples[side]
        assert tuples["before"] != tuples["after"]
        for axes in control["pairwise_projection_axes"]:
            assert len(axes) == 2
            assert {tuple(item[index] for index in axes) for item in tuples["before"]} == {
                tuple(item[index] for index in axes) for item in tuples["after"]}


def test_contract_test_registered_once_in_both_manifests() -> None:
    for relative in ("ci/pytest-tests.list", "ci/tools-tests.list"):
        entries = _manifest_entries(ROOT / relative)
        assert entries.count(TEST_PATH) == 1, relative
        assert len(entries) == len(set(entries)), relative
        assert all(not any(char.isspace() for char in item) for item in entries)


def test_historical_baseline_identity_is_preserved() -> None:
    baseline = load_json(BASELINE)
    assert baseline["schema_version"] == "language_relation_measurement_v0_baseline"
    assert baseline["artifact_role"] == "historical_source_inventory"
    assert baseline["stage"] == "LRM-01"
    assert baseline["repository"] == "HKati/pulse-release-gates-0.1"
    assert baseline["source_baseline"]["commit"] == SOURCE_COMMIT
    assert baseline["source_baseline"]["tree"] == SOURCE_TREE
    assert baseline["authority_effect"] == "none"
    assert baseline["release_authority_activation"] is False
    for field in ("commit", "tree"):
        assert re.fullmatch(r"[0-9a-f]{40}", baseline["implementation_base"][field])
    assert baseline["implementation_base"]["branch"] == "main"
    ids = [row["id"] for row in baseline["sources"]]
    paths = [row["path"] for row in baseline["sources"]]
    assert len(ids) == len(set(ids)) == 15
    assert len(paths) == len(set(paths))
    for source in baseline["sources"]:
        assert re.fullmatch(r"[0-9a-f]{40}", source["git_blob_sha"])
        assert source["url"] == (
            "https://github.com/HKati/pulse-release-gates-0.1/blob/"
            + SOURCE_COMMIT + "/" + source["path"]
        )
        assert source["reuse_obligations"], source["path"]


def test_lrm01_file_scope_and_followup_obligations_are_explicit() -> None:
    baseline = load_json(BASELINE)
    assert len(baseline["new_files"]) == len(set(baseline["new_files"])) == 13
    for relative in baseline["new_files"]:
        assert not Path(relative).is_absolute()
        assert ".." not in Path(relative).parts
        assert (ROOT / relative).is_file(), relative
    assert {row["path"] for row in baseline["amended_files"]} == {
        "ci/pytest-tests.list", "ci/tools-tests.list"
    }
    for amended in baseline["amended_files"]:
        assert amended["change"] == "append_test_registration"
        assert amended["entry"] == TEST_PATH
        assert re.fullmatch(r"[0-9a-f]{64}", amended["base_content_sha256"])
        assert re.fullmatch(r"[0-9a-f]{40}", amended["base_git_blob_sha1"])
        assert type(amended["base_size_bytes"]) is int
        assert amended["base_size_bytes"] > 0
    assert set(baseline["acceptance_obligations"]) == {
        f"A{index:02d}" for index in range(1, 25)
    }


def _unique_index(rows: list[dict], key: str) -> dict[str, dict]:
    identifiers = [row[key] for row in rows]
    assert len(identifiers) == len(set(identifiers)), f"duplicate {key}"
    return {row[key]: row for row in rows}


def _assert_fixture_input_integrity(payload: dict) -> None:
    """Check shipped annotations and bytes; do not infer source meaning."""
    assert_valid("language_relation_input_v0.schema.json", payload)
    profile = load_json(PROFILE)
    assert payload["profile_ref"]["profile_id"] == profile["profile_id"]
    assert payload["profile_ref"]["content_sha256"] == hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    sources = _unique_index(payload["sources"], "source_id")
    source_bytes = {}
    for source_id, source in sources.items():
        # The initial reference set preserves source text inline. Resolving
        # arbitrary package paths belongs to the future input runtime.
        assert source["content"]["kind"] == "inline_utf8"
        data = source["content"]["text"].encode("utf-8")
        assert len(data) == source["byte_length"], source_id
        assert hashlib.sha256(data).hexdigest() == source["content_sha256"], source_id
        source_bytes[source_id] = data
    for side in ("before", "after"):
        assert sum(source["role"] == side for source in sources.values()) == 1
    anchors = _unique_index(payload["source_anchors"], "anchor_id")
    for anchor_id, anchor in anchors.items():
        assert anchor["source_id"] in sources, anchor_id
        data = source_bytes[anchor["source_id"]]
        start, end = anchor["start_byte"], anchor["end_byte"]
        assert 0 <= start < end <= len(data), anchor_id
        # Check both half-open boundaries; a valid digest of cut UTF-8 bytes
        # does not make the source locator valid.
        data[:start].decode("utf-8")
        data[:end].decode("utf-8")
        assert hashlib.sha256(data[start:end]).hexdigest() == anchor["content_sha256"], anchor_id
    representations = payload["representations"]
    assert representations["before"]["representation_id"] != representations["after"]["representation_id"]
    indices = {}
    for side, representation in representations.items():
        source_id = representation["source_id"]
        assert source_id in sources
        assert sources[source_id]["role"] == side
        entities = _unique_index(representation["entities"], "entity_id")
        domains = _unique_index(representation["domains"], "domain_id")
        relations = _unique_index(representation["relations"], "relation_id")
        groups = _unique_index(representation["groups"], "group_id")
        indices[side] = {"entity": entities, "event": entities,
                         "relation": relations, "relation_group": {**relations, **groups}}
        for domain in domains.values():
            assert set(domain["entity_ids"]) <= set(entities)
        for group in groups.values():
            assert set(group["relation_ids"]) <= set(relations)
        for record in [*entities.values(), *relations.values()]:
            assert set(record["anchor_ids"]) <= set(anchors)
            for anchor_id in record["anchor_ids"]:
                anchor_source = anchors[anchor_id]["source_id"]
                assert anchor_source == source_id or sources[anchor_source]["role"] == "context"
        for relation in relations.values():
            speaker = relation["speaker_entity_id"]
            assert speaker is None or speaker in entities
            _assert_expression_references(relation["expression"], entities, domains, relations, {})
    correspondences = _unique_index(payload["correspondence"], "correspondence_id")
    for correspondence in correspondences.values():
        kind = correspondence["kind"]
        for side in ("before", "after"):
            assert set(correspondence[f"{side}_ids"]) <= set(indices[side][kind])
        assert set(correspondence["anchor_ids"]) <= set(anchors)
    variants = _unique_index(payload["interpretations"]["variants"], "variant_id")
    for variant in variants.values():
        for side in ("before", "after"):
            assert set(variant[f"{side}_relation_ids"]) <= set(indices[side]["relation"])
        assert set(variant["correspondence_ids"]) <= set(correspondences)
    targets = _unique_index(payload["measurement_request"]["targets"], "target_id")
    obligations = _unique_index(payload["coverage_obligations"], "obligation_id")
    for obligation in obligations.values():
        assert obligation["target_id"] in targets
        assert set(obligation["source_ids"]) <= set(sources)
    for target in targets.values():
        for side in ("before", "after"):
            assert set(target[f"{side}_ids"]) <= set(indices[side]["relation_group"])
        assert set(target["required_obligation_ids"]) <= set(obligations)
        assert set(target["context_source_ids"]) <= set(sources)
        for obligation_id in target["required_obligation_ids"]:
            assert obligations[obligation_id]["target_id"] == target["target_id"]
        for source_id in target["context_source_ids"]:
            assert sources[source_id]["role"] == "context"
    if payload["processing_binding"] is not None:
        binding = payload["processing_binding"]
        for side in ("before", "after"):
            assert binding[f"{side}_source_id"] == representations[side]["source_id"]
        assert set(binding["context_source_ids"]) <= set(sources)
    model = payload["impact_model"]
    if model is not None:
        claims = _unique_index(model["claims"], "claim_id")
        _unique_index(model["rules"], "rule_id")
        assert set(model["withdrawn_claim_ids"]) <= set(claims)
        assert set(model["target_claim_ids"]) <= set(claims)
        for claim in claims.values():
            assert set(claim["source_anchor_ids"]) <= set(anchors)
        for rule in model["rules"]:
            assert set(rule["premise_claim_ids"]) <= set(claims)
            assert rule["conclusion_claim_id"] in claims


def _assert_expression_references(
    expression: dict, entities: dict, domains: dict, relations: dict, variables: dict
) -> None:
    """Resolve annotation references and roles without evaluating expressions."""
    op = expression["op"]
    if op == "ATOM":
        signatures = {row["predicate"]: row["roles"]
                      for row in load_json(PROFILE)["predicate_signatures"]}
        assert expression["predicate"] in signatures
        signature = {row["role"]: set(row["types"])
                     for row in signatures[expression["predicate"]]}
        arguments = _unique_index(expression["arguments"], "role")
        assert set(arguments) == set(signature)
        for role, argument in arguments.items():
            value = argument["value"]
            if "entity_id" in value:
                assert value["entity_id"] in entities
                assert entities[value["entity_id"]]["entity_type"] in signature[role]
            elif "relation_id" in value:
                assert value["relation_id"] in relations
                assert "proposition" in signature[role]
            else:
                assert value["variable"] in variables
                assert variables[value["variable"]] <= signature[role]
    elif op == "REF":
        assert expression["relation_id"] in relations
    elif op in ("FORALL", "EXISTS"):
        assert expression["domain_id"] in domains
        members = domains[expression["domain_id"]]["entity_ids"]
        nested = dict(variables)
        nested[expression["variable"]] = {entities[member]["entity_type"] for member in members}
        _assert_expression_references(expression["body"], entities, domains, relations, nested)
    elif op in ("AND", "OR"):
        for child in expression["operands"]:
            _assert_expression_references(child, entities, domains, relations, variables)
    elif op == "NOT":
        _assert_expression_references(expression["operand"], entities, domains, relations, variables)
    elif op == "IMPLIES":
        for key in ("antecedent", "consequent"):
            _assert_expression_references(expression[key], entities, domains, relations, variables)
    elif op == "CONTEXT":
        speaker = expression["speaker_entity_id"]
        assert speaker is None or speaker in entities
        _assert_expression_references(expression["body"], entities, domains, relations, variables)
    else:
        raise AssertionError(f"unsupported expression node in fixture: {op}")


def test_reference_inputs_have_bound_bytes_and_resolvable_annotations() -> None:
    cases = load_json(EXAMPLE_DIR / "cases.json")["cases"]
    _unique_index(cases, "case_id")
    assert cases
    languages = set()
    for case in cases:
        _assert_fixture_input_integrity(case)
        languages.update(source["language"] for source in case["sources"])
    assert {"hu", "en"} <= languages


def test_contract_input_examples_have_bound_bytes_and_resolvable_annotations() -> None:
    for row in contract_examples():
        if row["schema_file"] == "language_relation_input_v0.schema.json":
            _assert_fixture_input_integrity(row["artifact"])


@pytest.mark.parametrize("mutation", ("source_bytes", "source_digest", "profile_digest",
                                      "dangling_anchor", "duplicate_entity", "dangling_entity"))
def test_fixture_integrity_rejects_corrupted_bindings(mutation: str) -> None:
    payload = example_for("language_relation_input_v0.schema.json")
    if mutation == "source_bytes":
        payload["sources"][0]["content"]["text"] += "!"
    elif mutation == "source_digest":
        payload["sources"][0]["content_sha256"] = "0" * 64
    elif mutation == "profile_digest":
        payload["profile_ref"]["content_sha256"] = "0" * 64
    elif mutation == "dangling_anchor":
        payload["source_anchors"][0]["source_id"] = "missing_source"
    elif mutation == "duplicate_entity":
        entities = payload["representations"]["before"]["entities"]
        assert entities
        entities.append(deepcopy(entities[0]))
    else:
        expression = payload["representations"]["before"]["relations"][0]["expression"]
        atom = next(node for node in _walk(expression)
                    if isinstance(node, dict) and node.get("op") == "ATOM")
        atom["arguments"][0]["value"] = {"entity_id": "missing_entity"}
    with pytest.raises(AssertionError):
        _assert_fixture_input_integrity(payload)


def test_a_digest_of_cut_unicode_bytes_does_not_validate_an_anchor() -> None:
    cases = load_json(EXAMPLE_DIR / "cases.json")["cases"]
    payload = deepcopy(next(case for case in cases
                            if any(any(ord(char) > 127 for char in source["content"]["text"])
                                   for source in case["sources"])))
    source = next(source for source in payload["sources"]
                  if any(ord(char) > 127 for char in source["content"]["text"]))
    data = source["content"]["text"].encode("utf-8")
    cut = next(index + 1 for index, byte in enumerate(data) if byte >= 0xC0)
    anchor = next(anchor for anchor in payload["source_anchors"]
                  if anchor["source_id"] == source["source_id"])
    anchor.update(start_byte=0, end_byte=cut, content_sha256=hashlib.sha256(data[:cut]).hexdigest())
    with pytest.raises(UnicodeDecodeError):
        _assert_fixture_input_integrity(payload)


def test_profile_and_baseline_keep_runtime_completion_explicit() -> None:
    profile = load_json(PROFILE)
    assert profile["profile_id"] == "lrm_finite_reference_profile_v0"
    assert profile["stage"] == "contract_only"
    assert profile["authority_effect"] == "none"
    assert profile["release_authority_activation"] is False
    assert profile["or_semantics"] == "inclusive"
    assert profile["quantification"] == "explicit_finite_domain"
    assert profile["limits"]["max_expanded_boolean_atoms"] == 12
    assert profile["limits"]["max_joint_variants"] == 64
    assert profile["limits"]["max_ast_nodes_per_variant"] == 256
    assert profile["limits"]["limit_status"] == "planned_resource_bounds_not_benchmark"
    assert {"source_mapping_checker", "reference_acceptance_resolver",
            "relation_comparator", "impact_evaluator", "automatic_extractor",
            "offline_replay_runner"} <= set(profile["unimplemented"])
    states = load_json(BASELINE)["implementation_state"]
    for key in ("source_binding_runtime", "independent_representation_checker",
                "relation_comparator", "impact_measurement", "automatic_extractor",
                "offline_replay_runtime"):
        assert states[key] == "not_implemented"


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
@pytest.mark.parametrize(("field", "value"), (
    ("authority_effect", "release_allow"),
    ("release_authority_activation", True),
))
def test_diagnostic_contract_cannot_activate_authority(
    schema_file: str, field: str, value: object
) -> None:
    payload = example_for(schema_file)
    payload[field] = value
    assert_invalid(schema_file, payload)


@pytest.mark.parametrize("schema_file", (
    "language_relation_verification_v0.schema.json",
    "language_relation_measurement_v0.schema.json",
))
def test_all_six_status_axes_are_required(schema_file: str) -> None:
    payload = example_for(schema_file)
    axes = {"observation_status", "binding_status", "consistency_status",
            "reproduction_status", "causal_status", "authority_status"}
    assert set(payload["status_axes"]) == axes
    for axis in sorted(axes):
        changed = deepcopy(payload)
        del changed["status_axes"][axis]
        assert_invalid(schema_file, changed)
    payload["status_axes"]["authority_status"] = "authority_bearing"
    assert_invalid(schema_file, payload)


@pytest.mark.parametrize("status", ("not_run", "error"))
@pytest.mark.parametrize("result", ("pass", "fail", "unresolved"))
def test_unfinished_verification_check_has_no_result(status: str, result: str) -> None:
    schema = "language_relation_verification_v0.schema.json"
    payload = example_for(schema)
    payload["checks"][0].update(status=status, result=result, reason="Not completed.")
    assert_invalid(schema, payload)


@pytest.mark.parametrize("status", ("not_run", "error"))
def test_unfinished_verification_check_requires_reason(status: str) -> None:
    schema = "language_relation_verification_v0.schema.json"
    payload = example_for(schema)
    payload["checks"][0].update(status=status, result=None, reason=None)
    assert_invalid(schema, payload)


def test_completed_verification_check_requires_a_result() -> None:
    schema = "language_relation_verification_v0.schema.json"
    payload = example_for(schema)
    payload["checks"][0].update(status="completed", result=None)
    assert_invalid(schema, payload)


@pytest.mark.parametrize("result", ("fail", "unresolved"))
def test_completed_nonpass_verification_requires_reason(result: str) -> None:
    schema = "language_relation_verification_v0.schema.json"
    payload = example_for(schema)
    payload["checks"][0].update(status="completed", result=result, reason=None)
    assert_invalid(schema, payload)


@pytest.mark.parametrize("scope", ("reference_interpretation", "controlled_source_profile"))
def test_candidate_verification_cannot_promote_its_claim_scope(scope: str) -> None:
    schema = "language_relation_verification_v0.schema.json"
    payload = example_for(schema)
    payload["basis_records"][0].update(
        representation_basis="candidate_only", claim_scope=scope, acceptance_ref=None)
    assert_invalid(schema, payload)


@pytest.mark.parametrize("basis", ("accepted_reference", "profile_verified"))
def test_input_non_candidate_basis_requires_bound_acceptance(basis: str) -> None:
    schema = "language_relation_input_v0.schema.json"
    payload = example_for(schema)
    payload["representation_basis"]["before"].update(
        basis=basis, verification_ref=None, acceptance_ref=None)
    assert_invalid(schema, payload)


def test_candidate_input_cannot_include_self_acceptance() -> None:
    schema = "language_relation_input_v0.schema.json"
    payload = example_for(schema)
    payload["representation_basis"]["before"].update(
        basis="candidate_only", acceptance_ref={
            "inventory_id": "self_inventory", "entry_id": "self_entry",
            "content_sha256": "0" * 64})
    assert_invalid(schema, payload)


def test_processing_change_claim_requires_processing_binding() -> None:
    schema = "language_relation_input_v0.schema.json"
    payload = example_for(schema)
    payload["measurement_request"]["processing_claim"] = "processing_change"
    payload["processing_binding"] = None
    assert_invalid(schema, payload)


@pytest.mark.parametrize("state", ("unknown", "empty"))
def test_unknown_or_empty_family_cannot_contain_variants(state: str) -> None:
    schema = "language_relation_input_v0.schema.json"
    payload = example_for(schema)
    assert payload["interpretations"]["variants"]
    payload["interpretations"].update(state=state, reason="Explicit family state.")
    assert_invalid(schema, payload)
    payload["interpretations"]["variants"] = []
    assert_valid(schema, payload)


def test_complete_family_must_not_be_empty() -> None:
    schema = "language_relation_input_v0.schema.json"
    payload = example_for(schema)
    payload["interpretations"] = {"state": "complete", "variants": [], "reason": None}
    assert_invalid(schema, payload)


def test_truncated_family_preserves_known_variants_and_requires_reason() -> None:
    schema = "language_relation_input_v0.schema.json"
    payload = example_for(schema)
    known_variants = deepcopy(payload["interpretations"]["variants"])
    payload["interpretations"].update(state="truncated", reason="Declared bound reached.")
    assert_valid(schema, payload)
    assert payload["interpretations"]["variants"] == known_variants
    payload["interpretations"]["reason"] = None
    assert_invalid(schema, payload)


def _completed_candidate_measurement() -> dict:
    """Construct an illustrative shape, without claiming that a run occurred."""
    payload = example_for("language_relation_measurement_v0.schema.json")
    payload["execution"] = {"status": "completed", "reason": None}
    payload["results"] = [{
        "target_id": "synthetic_target",
        "relation_state": "PRESERVED",
        "assessment_state": "IDENTIFIED",
        "representation_basis": "candidate_only",
        "claim_scope": "candidate_structures",
        "verification_ids": [],
        "coverage_obligation_ids": ["synthetic_coverage"],
        "closed_obligation_ids": ["synthetic_coverage"],
        "compatible_variant_ids": ["synthetic_variant"],
        "possible_relation_states": ["PRESERVED"],
        "witness_ids": [],
        "reason": None,
    }]
    return payload


def test_candidate_structural_result_is_representable_without_source_promotion() -> None:
    payload = _completed_candidate_measurement()
    assert_valid("language_relation_measurement_v0.schema.json", payload)
    assert payload["results"][0]["claim_scope"] == "candidate_structures"


@pytest.mark.parametrize("scope", ("reference_interpretation", "controlled_source_profile"))
def test_candidate_measurement_cannot_promote_claim_scope(scope: str) -> None:
    payload = _completed_candidate_measurement()
    payload["results"][0]["claim_scope"] = scope
    assert_invalid("language_relation_measurement_v0.schema.json", payload)


@pytest.mark.parametrize("status", ("not_run", "error"))
def test_unfinished_measurement_cannot_publish_target_results(status: str) -> None:
    payload = _completed_candidate_measurement()
    payload["execution"] = {"status": status, "reason": "Not completed."}
    assert_invalid("language_relation_measurement_v0.schema.json", payload)


@pytest.mark.parametrize("field", ("compatible_variant_ids", "closed_obligation_ids"))
def test_identified_result_needs_variants_and_closed_obligations(field: str) -> None:
    payload = _completed_candidate_measurement()
    payload["results"][0][field] = []
    assert_invalid("language_relation_measurement_v0.schema.json", payload)


@pytest.mark.parametrize("possible", (["CHANGED"], ["PRESERVED", "CHANGED"], []))
def test_identified_result_has_one_matching_possible_state(possible: list[str]) -> None:
    payload = _completed_candidate_measurement()
    payload["results"][0]["possible_relation_states"] = possible
    assert_invalid("language_relation_measurement_v0.schema.json", payload)


@pytest.mark.parametrize("assessment", ("UNBOUND", "INCOMPATIBLE", "UNRESOLVED"))
def test_unresolved_assessment_cannot_be_preserved(assessment: str) -> None:
    payload = _completed_candidate_measurement()
    payload["results"][0].update(assessment_state=assessment, reason="Open obligation.")
    assert_invalid("language_relation_measurement_v0.schema.json", payload)


@pytest.mark.parametrize("state", ("CHANGED", "BROKEN"))
def test_changed_or_broken_result_requires_witness(state: str) -> None:
    payload = _completed_candidate_measurement()
    payload["results"][0].update(relation_state=state, possible_relation_states=[state])
    assert_invalid("language_relation_measurement_v0.schema.json", payload)


def test_new_relation_cannot_inherit_support_without_its_own_record() -> None:
    payload = _completed_candidate_measurement()
    payload["introduced_relations"] = [{
        "relation_id": "synthetic_added", "target_id": "synthetic_target",
        "novelty": "new_content", "evidence_status": "supported",
        "evidence_refs": [], "derivation_ref": None,
        "source_coverage_obligation_ids": ["synthetic_coverage"], "reason": None,
    }]
    assert_invalid("language_relation_measurement_v0.schema.json", payload)


def test_modeled_impact_requires_a_witness() -> None:
    payload = _completed_candidate_measurement()
    payload["impacts"] = [{
        "impact_id": "synthetic_impact", "target_id": "synthetic_target",
        "kind": "condition_satisfaction_change", "conclusion": "changed",
        "representation_basis": "candidate_only", "claim_scope": "candidate_structures",
        "witness_ids": [], "evidence_refs": [], "reason": None,
    }]
    assert_invalid("language_relation_measurement_v0.schema.json", payload)


def test_candidate_structures_cannot_claim_an_observed_consequence() -> None:
    payload = _completed_candidate_measurement()
    payload["impacts"] = [{
        "impact_id": "synthetic_impact", "target_id": "synthetic_target",
        "kind": "observed_consequence", "conclusion": "changed",
        "representation_basis": "candidate_only", "claim_scope": "candidate_structures",
        "witness_ids": ["synthetic_witness"], "evidence_refs": ["synthetic_evidence"],
        "reason": None,
    }]
    assert_invalid("language_relation_measurement_v0.schema.json", payload)


@pytest.mark.parametrize("path", ("../input.json", "/input.json", "a/../../input.json",
                                  "a\\input.json", "C:/input.json"))
def test_manifest_rejects_paths_outside_the_package(path: str) -> None:
    schema = "language_relation_manifest_v0.schema.json"
    payload = example_for(schema)
    payload["payloads"][0]["path"] = path
    assert_invalid(schema, payload)


def test_manifest_does_not_hash_itself() -> None:
    schema = "language_relation_manifest_v0.schema.json"
    payload = example_for(schema)
    payload["payloads"][0]["path"] = "manifest.json"
    assert_invalid(schema, payload)


def test_replay_receipt_is_outside_the_deterministic_measurement_digest() -> None:
    schema = "language_relation_manifest_v0.schema.json"
    payload = example_for(schema)
    payload["replay"]["deterministic_payload_paths"].append("replay_receipt.json")
    assert_invalid(schema, payload)


def test_deterministic_replay_does_not_allow_model_calls() -> None:
    schema = "language_relation_manifest_v0.schema.json"
    payload = example_for(schema)
    payload["replay"]["model_calls"] = True
    assert_invalid(schema, payload)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
