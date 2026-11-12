"""LRM-04 support, impact and evidence-boundary regressions.

All evidence fixtures are synthetic and independently configured by this test
controller. Reference examples are test data, never runtime judgment inputs.
"""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import subprocess
from pathlib import Path
import sys

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.language_relation_v0.logic import LogicProblem
from tools.language_relation_v0 import support
from tools.language_relation_v0.io import InputError, canonical_bytes, sha256


SELF = "tests/test_language_relation_impact_v0.py"
CLI = ROOT / "tools/measure_language_relations_v0.py"
_fixture_spec = importlib.util.spec_from_file_location(
    "lrm04_comparison_fixtures", ROOT / "tests/test_language_relation_comparator_v0.py")
assert _fixture_spec is not None and _fixture_spec.loader is not None
fixtures = importlib.util.module_from_spec(_fixture_spec)
sys.modules[_fixture_spec.name] = fixtures
_fixture_spec.loader.exec_module(fixtures)


def claim(identifier, base=False, expression=None):
    return {'claim_id': identifier, 'is_base': base, 'evidence_refs': ['declared_evidence'],
            'source_anchor_ids': ['declared_anchor'],
            'expression': expression or {'op': 'ATOM', 'predicate': 'approve',
                'arguments': [{'role': 'agent', 'value': {'entity_id': identifier}}]}}


def rule(identifier, premises, conclusion):
    return {'rule_id': identifier, 'premise_claim_ids': list(premises),
            'conclusion_claim_id': conclusion, 'rule_basis_ref': 'SUPPORT_01'}


def model(claims, rules=(), withdrawn=()):
    return {'model_id': 'synthetic_model', 'claims': list(claims), 'rules': list(rules),
            'withdrawn_claim_ids': list(withdrawn), 'target_claim_ids': []}


def admitted(payload, bases=()):
    return support.support_transition(payload, admitted_base_claim_ids=bases,
        admitted_rule_ids=[row['rule_id'] for row in payload['rules']])


def test_declared_flags_and_evidence_strings_do_not_seed_without_admission():
    payload = model([claim('a', True), claim('b')], [rule('ab', ['a'], 'b')])
    result = admitted(payload)
    assert result['before']['grounded_claim_ids'] == []
    assert result['before']['support_paths'] == []


def test_rule_requires_separate_admission():
    payload = model([claim('a', True), claim('b')], [rule('ab', ['a'], 'b')])
    result = support.grounded_closure(payload, admitted_base_claim_ids=['a'], admitted_rule_ids=[])
    assert result['grounded_claim_ids'] == ['a']


@pytest.mark.parametrize('bases,expected', [(['a'], ['a']), (['b'], ['b']), (['a', 'b'], ['a', 'b', 'c'])])
def test_conjunctive_support_requires_all_admitted_premises(bases, expected):
    payload = model([claim('a', True), claim('b', True), claim('c')],
                    [rule('abc', ['a', 'b'], 'c')])
    assert admitted(payload, bases)['after']['grounded_claim_ids'] == expected


def test_alternative_paths_survive_one_withdrawal_and_retain_their_own_bases():
    payload = model([claim('a', True), claim('b', True), claim('c')],
                    [rule('ac', ['a'], 'c'), rule('bc', ['b'], 'c')], ['a'])
    result = admitted(payload, ['a', 'b'])
    paths = lambda side: [row for row in result[side]['support_paths'] if row['claim_id'] == 'c']
    assert paths('before') == [
        {'claim_id': 'c', 'base_claim_ids': ['a'], 'rule_ids': ['ac']},
        {'claim_id': 'c', 'base_claim_ids': ['b'], 'rule_ids': ['bc']}]
    assert paths('after') == [{'claim_id': 'c', 'base_claim_ids': ['b'], 'rule_ids': ['bc']}]
    assert result['lost_claim_ids'] == ['a']
    assert result['retained_claim_ids'] == ['b', 'c']
    assert result['after']['recomputed_after_withdrawal'] is True


def test_withdrawal_does_not_seed_the_previous_derived_cycle():
    payload = model([claim('base', True), claim('a'), claim('b')],
                    [rule('seed', ['base'], 'a'), rule('ab', ['a'], 'b'), rule('ba', ['b'], 'a')], ['base'])
    result = admitted(payload, ['base'])
    assert result['before']['grounded_claim_ids'] == ['a', 'b', 'base']
    assert result['after']['grounded_claim_ids'] == []
    assert result['after']['support_paths'] == []
    assert result['after']['unsupported_cycle_claim_ids'] == ['a', 'b']


def test_withdrawn_base_claim_can_be_derived_from_an_independent_base():
    payload = model([claim('a', True), claim('b', True)], [rule('ba', ['b'], 'a')], ['a'])
    result = admitted(payload, ['a', 'b'])
    assert result['lost_claim_ids'] == []
    assert result['after']['support_paths'] == [
        {'claim_id': 'a', 'base_claim_ids': ['b'], 'rule_ids': ['ba']},
        {'claim_id': 'b', 'base_claim_ids': ['b'], 'rule_ids': []}]


def test_unsupported_scc_members_exclude_downstream_tails():
    payload = model([claim('a'), claim('b'), claim('tail'), claim('self')],
                    [rule('ab', ['a'], 'b'), rule('ba', ['b'], 'a'),
                     rule('bt', ['b'], 'tail'), rule('ss', ['self'], 'self')])
    result = admitted(payload)['after']
    assert result['grounded_claim_ids'] == []
    assert result['unsupported_cycle_claim_ids'] == ['a', 'b', 'self']


def test_exact_grounded_conflict_does_not_derive_unrelated_claims():
    positive = claim('positive', True)
    negative = claim('negative', True, {'op': 'NOT', 'operand': positive['expression']})
    payload = model([positive, negative, claim('unrelated')])
    result = admitted(payload, ['positive', 'negative'])['after']
    assert result['grounded_claim_ids'] == ['negative', 'positive']
    assert result['conflicts'] == [{'claim_id': 'negative', 'opposes_claim_id': 'positive'}]


def test_unadmitted_negation_and_typed_quotation_do_not_manufacture_a_conflict():
    positive = claim('positive', True)
    negative = claim('negative', True, {'op': 'NOT', 'operand': positive['expression']})
    quoted = claim('quoted', True, {'op': 'CONTEXT', 'discourse_type': 'quotation',
        'modality': 'declarative', 'speaker_entity_id': None, 'body': negative['expression']})
    payload = model([positive, negative, quoted])
    result = admitted(payload, ['positive', 'quoted'])['after']
    assert result['conflicts'] == []
    assert result['grounded_claim_ids'] == ['positive', 'quoted']


def test_equal_claim_expressions_do_not_alias_claim_identity():
    a = claim('a', True)
    b = claim('b', False, deepcopy(a['expression']))
    assert admitted(model([a, b]), ['a'])['after']['grounded_claim_ids'] == ['a']


def test_support_output_is_order_independent_and_schema_compatible():
    payload = model([claim('a', True), claim('b', True), claim('c'), claim('d')],
        [rule('abc', ['b', 'a'], 'c'), rule('ad', ['a'], 'd'), rule('cd', ['c'], 'd')], ['b'])
    original = deepcopy(payload)
    first = admitted(payload, ['a', 'b'])
    assert payload == original
    payload['claims'].reverse()
    payload['rules'].reverse()
    for row in payload['rules']:
        row['premise_claim_ids'].reverse()
    assert admitted(payload, ['b', 'a']) == first
    schema = json.loads((ROOT/'schemas/language_relation_measurement_v0.schema.json').read_text())['properties']['support']
    for side in ['before', 'after']:
        jsonschema.Draft202012Validator(schema).validate(first[side])


def test_maximum_support_chain_uses_iterative_closure():
    claims = [claim('c' + str(i), i == 0) for i in range(256)]
    rules = [rule('r' + str(i), ['c' + str(i)], 'c' + str(i + 1)) for i in range(255)]
    result = admitted(model(claims, rules), ['c0'])['after']
    assert len(result['grounded_claim_ids']) == 256
    last = next(row for row in result['support_paths'] if row['claim_id'] == 'c255')
    assert last['base_claim_ids'] == ['c0']
    assert set(last['rule_ids']) == {row['rule_id'] for row in rules}


def test_model_record_exhaustion_is_explicit():
    payload = model([claim('c' + str(i), True) for i in range(257)])
    with pytest.raises(LogicProblem) as error:
        admitted(payload)
    assert error.value.code == 'support_model_limit'


def test_alternative_path_exhaustion_does_not_return_partial_success():
    claims = [claim('c' + str(i), i == 0) for i in range(13)]
    rules = [rule('r' + str(i) + suffix, ['c' + str(i)], 'c' + str(i + 1))
             for i in range(12) for suffix in ['a', 'b']]
    with pytest.raises(LogicProblem) as error:
        admitted(model(claims, rules), ['c0'])
    assert error.value.code == 'support_path_limit'


def test_combination_exhaustion_is_incomplete_not_a_grounded_prefix(monkeypatch):
    payload = model([claim('a', True), claim('b'), claim('c')],
        [rule('ab', ['a'], 'b'), rule('bc', ['b'], 'c')])
    monkeypatch.setattr(support, 'MAX_SUPPORT_COMBINATIONS', 1)
    with pytest.raises(LogicProblem) as error:
        admitted(payload, ['a'])
    assert error.value.code == 'support_combination_limit'


@pytest.mark.parametrize('bases,rules,code', [(['missing'], [], 'support_unknown_identifier'),
    (['a'], ['missing'], 'support_unknown_identifier'), (['b'], [], 'support_base_mismatch')])
def test_invalid_admission_subjects_fail_explicitly(bases, rules, code):
    payload = model([claim('a', True), claim('b')])
    with pytest.raises(LogicProblem) as error:
        support.grounded_closure(payload, admitted_base_claim_ids=bases, admitted_rule_ids=rules)
    assert error.value.code == code


def test_unknown_withdrawal_is_not_silently_ignored():
    payload = model([claim('a', True)], withdrawn=['missing'])
    with pytest.raises(LogicProblem) as error:
        admitted(payload, ['a'])
    assert error.value.code == 'support_unknown_identifier'


def impact_bundle(fixture: dict, **overrides) -> dict:
    from tools.language_relation_v0.impact import measure_impact_bundle

    options = {"package_root": fixture["package"],
               "trust_config": fixture["source_config"],
               "comparison_trust_config": fixture["comparison_config"], **overrides}
    if "impact_config" in fixture and "impact_trust_config" not in overrides:
        options["impact_trust_config"] = fixture["impact_config"]
    return measure_impact_bundle(fixture["input_path"], **options)


def candidate_bundle(tmp_path: Path, payload: dict) -> dict:
    from tools.language_relation_v0.impact import measure_impact_bundle

    return measure_impact_bundle(fixtures.save_input(tmp_path, payload), package_root=tmp_path)


def invoke_impact_cli(input_path: Path, output_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), "--input", str(input_path),
        "--output-dir", str(output_dir), "--with-impact", *map(str, extra)],
        cwd=ROOT, text=True, capture_output=True, check=False, timeout=30)


def assert_authority_boundary(bundle: dict) -> None:
    for artifact in bundle.values():
        assert artifact["authority_effect"] == "none"
        assert artifact["release_authority_activation"] is False
    report = bundle["measurement"]
    assert report["status_axes"]["authority_status"] == "none"
    assert report["status_axes"]["causal_status"] == "not_evaluated"
    jsonschema.Draft202012Validator(fixtures.MEASUREMENT_SCHEMA).validate(report)
    jsonschema.Draft202012Validator(fixtures.VERIFICATION_SCHEMA).validate(bundle["verification"])


def test_legacy_invocation_keeps_its_semantics_and_two_artifact_bundle(tmp_path):
    fixture = fixtures.accepted_fixture(tmp_path, fixtures.reference_input(23))
    bundle = fixtures.measure_bundle(fixture["input_path"], package_root=fixture["package"],
        trust_config=fixture["source_config"], comparison_trust_config=fixture["comparison_config"])
    assert set(bundle) == {"measurement", "verification"}
    fixtures.assert_measurement_integrity(bundle["measurement"], fixture["payload"])
    assert fixtures.result_for(bundle["measurement"])["relation_state"] == "CHANGED"
    assert any(row["reason_code"] == "impact_not_evaluated" for row in bundle["measurement"]["unresolved"])


def test_candidate_support_declarations_cannot_admit_their_own_evidence(tmp_path):
    bundle = candidate_bundle(tmp_path, fixtures.reference_input(23))
    report = bundle["measurement"]
    assert_authority_boundary(bundle)
    assert set(bundle) == {"measurement", "verification", "impact"}
    if report["support"] is not None:
        assert report["support"]["grounded_claim_ids"] == []
        assert report["support"]["support_paths"] == []
    assert not any(row["kind"] == "observed_consequence" for row in report["impacts"])


def test_impact_runtime_does_not_read_reference_corpus_or_oracle(tmp_path, monkeypatch):
    payload = fixtures.reference_input(23)
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
    bundle = candidate_bundle(tmp_path, payload)
    assert_authority_boundary(bundle)
    assert fixtures.result_for(bundle["measurement"])["relation_state"] == "CHANGED"


def test_impact_cli_does_not_overwrite_existing_output(tmp_path):
    input_path = fixtures.save_input(tmp_path, fixtures.reference_input(23))
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "owner.txt"
    sentinel.write_bytes(b"preserve the exact owner's bytes\n")
    completed = invoke_impact_cli(input_path, output)
    assert completed.returncode == 2, completed.stderr
    assert {path.name for path in output.iterdir()} == {"owner.txt"}
    assert sentinel.read_bytes() == b"preserve the exact owner's bytes\n"


def test_impact_cli_rejects_symlink_output_without_touching_destination(tmp_path):
    input_path = fixtures.save_input(tmp_path, fixtures.reference_input(23))
    destination = tmp_path / "owner_directory"
    destination.mkdir()
    sentinel = destination / "owner.txt"
    sentinel.write_bytes(b"owner data")
    output = tmp_path / "output_link"
    output.symlink_to(destination, target_is_directory=True)
    completed = invoke_impact_cli(input_path, output)
    assert completed.returncode == 2, completed.stderr
    assert output.is_symlink()
    assert {path.name for path in destination.iterdir()} == {"owner.txt"}
    assert sentinel.read_bytes() == b"owner data"


def test_impact_cli_invalid_input_publishes_no_partial_artifacts(tmp_path):
    input_path = tmp_path / "invalid.json"
    input_path.write_bytes(b'{"case_id":"a","case_id":"b"}')
    output = tmp_path / "must_not_exist"
    assert invoke_impact_cli(input_path, output).returncode == 2
    assert not output.exists()


def test_impact_module_registered_once_with_all_existing_lrm_modules():
    for name, expected in (("tools-tests.list", 181), ("pytest-tests.list", 39)):
        entries = [line for raw in (ROOT / "ci" / name).read_text().splitlines()
                   if (line := raw.split("#", 1)[0].strip())]
        assert len(entries) == len(set(entries)) == expected
        assert entries.count(SELF) == 1
        for prior in ("contract", "input_verifier", "comparator"):
            assert entries.count(f"tests/test_language_relation_{prior}_v0.py") == 1
        assert entries.index(SELF) == entries.index("tests/test_language_relation_comparator_v0.py") + 1


def impact_check(identifier: str, **fields) -> dict:
    return {"check_id": identifier, "status": "completed", "result": "pass", "reason": None,
            "evidence_refs": ["independent_" + identifier], **fields}


def write_impact_reviews(fixture: dict) -> None:
    directory = fixture["impact_config"].parent
    config = {"schema_version": "language_relation_impact_trust_config_v0",
              "review_files": [], "observation_files": []}
    for kind, key in (("review", "impact_reviews"), ("observation", "observations")):
        for index, value in enumerate(fixture.get(key, [])):
            raw = fixtures.encoded(value)
            filename = f"{kind}_{index}.json"
            (directory / filename).write_bytes(raw)
            config[kind + "_files"].append({"path": filename, "content_sha256": fixtures.digest(raw)})
    fixture["impact_config"].write_bytes(fixtures.encoded(config))


def refresh_all_subjects(fixture: dict) -> None:
    fixtures.write_source_acceptance(fixture)
    fixtures.write_comparison_reviews(fixture, refresh=True)
    input_ref = {"artifact_id": fixture["payload"]["case_id"],
                 "content_sha256": fixtures.digest(fixture["input_path"].read_bytes())}
    for review in fixture["impact_reviews"]:
        review["input_ref"] = deepcopy(input_ref)
        review["profile_ref"] = deepcopy(fixture["payload"]["profile_ref"])
        if review["model_ref"] is not None:
            review["model_ref"] = {"model_id": fixture["payload"]["impact_model"]["model_id"],
                "content_sha256": fixtures.digest(fixtures.contract_bytes(fixture["payload"]["impact_model"]))}
    for observation in fixture.get("observations", []):
        observation["input_ref"] = deepcopy(input_ref)
        observation["profile_ref"] = deepcopy(fixture["payload"]["profile_ref"])
    write_impact_reviews(fixture)


def support_review(fixture: dict, target_id: str = "target_main", claim_ids=None) -> dict:
    payload = fixture["payload"]
    target = next(row for row in payload["measurement_request"]["targets"] if row["target_id"] == target_id)
    model = payload["impact_model"]
    return {"schema_version": "language_relation_impact_review_v0",
        "verification_id": "impact_review_" + target_id,
        "input_ref": {"artifact_id": payload["case_id"],
                      "content_sha256": fixtures.digest(fixture["input_path"].read_bytes())},
        "profile_ref": deepcopy(payload["profile_ref"]), "target_id": target_id, "mode": "support",
        "model_ref": {"model_id": model["model_id"],
                      "content_sha256": fixtures.digest(fixtures.contract_bytes(model))},
        "claim_ids": list(model["target_claim_ids"] if claim_ids is None else claim_ids),
        "reviewed_variant_ids": [row["variant_id"] for row in payload["interpretations"]["variants"]],
        "scope_check": impact_check("scope_" + target_id,
            context_source_ids=list(target["context_source_ids"]),
            correspondence_ids=sorted({key for row in payload["interpretations"]["variants"]
                                       for key in row["correspondence_ids"]}),
            withdrawal_semantics="remove_base_evidence"),
        "base_checks": [impact_check(target_id + "_" + row["claim_id"], claim_id=row["claim_id"])
                        for row in model["claims"] if row["is_base"]],
        "rule_checks": [impact_check(target_id + "_" + row["rule_id"], rule_id=row["rule_id"],
                                     rule_basis_ref=row["rule_basis_ref"]) for row in model["rules"]],
        "observation_ref": None}


def support_fixture(tmp_path: Path, number: int = 23, payload=None) -> dict:
    fixture = fixtures.accepted_fixture(tmp_path, fixtures.reference_input(number) if payload is None else payload)
    directory = tmp_path / "impact_trust"
    directory.mkdir()
    fixture.update(impact_config=directory / "config.json", observations=[], impact_reviews=[])
    fixture["impact_reviews"] = [support_review(fixture)]
    write_impact_reviews(fixture)
    return fixture


def impact_review_outcome(fixture: dict, target_id="target_main") -> dict:
    from tools.language_relation_v0.impact_evidence import ImpactTrust

    return ImpactTrust.load(fixture["impact_config"], fixture["package"]).target_review(
        fixture["payload"], {"artifact_id": fixture["payload"]["case_id"],
                            "content_sha256": fixtures.digest(fixture["input_path"].read_bytes())},
        target_id, variant_ids=[row["variant_id"] for row in fixture["payload"]["interpretations"]["variants"]])


def impacts_for(bundle: dict, target_id="target_main", kind=None) -> list[dict]:
    return [row for row in bundle["measurement"]["impacts"]
            if row["target_id"] == target_id and (kind is None or row["kind"] == kind)]


def test_independent_support_review_admits_exact_base_and_rule_records(tmp_path):
    fixture = support_fixture(tmp_path)
    outcome = impact_review_outcome(fixture)
    assert outcome["result"] == "pass", outcome
    assert set(outcome["admitted_base_claim_ids"]) == {"claim_anna", "claim_eva"}
    assert set(outcome["admitted_rule_ids"]) == {"rule_ab", "rule_eb"}
    assert outcome["claim_ids"] == ["claim_bela"]
    assert outcome["evidence_refs"]


@pytest.mark.parametrize("field", ["input", "profile", "model_digest", "model_id", "variants", "context", "correspondence"])
def test_impact_review_rejects_an_exact_subject_or_scope_mismatch(tmp_path, field):
    fixture = support_fixture(tmp_path)
    review = fixture["impact_reviews"][0]
    if field in {"input", "profile"}:
        review[field + "_ref"]["content_sha256"] = "0" * 64
    elif field == "model_digest":
        review["model_ref"]["content_sha256"] = "0" * 64
    elif field == "model_id":
        review["model_ref"]["model_id"] = "foreign_model"
    elif field == "variants":
        review["reviewed_variant_ids"] = ["foreign_variant"]
    elif field == "context":
        review["scope_check"]["context_source_ids"] = ["foreign_context"]
    else:
        review["scope_check"]["correspondence_ids"] = ["foreign_correspondence"]
    write_impact_reviews(fixture)
    outcome = impact_review_outcome(fixture)
    assert outcome["result"] == "fail", outcome
    assert outcome["reason"]


@pytest.mark.parametrize("check_name", ["scope_check", "base_checks", "rule_checks"])
def test_explicit_impact_rejection_wins_over_missing_evidence_refs(tmp_path, check_name):
    fixture = support_fixture(tmp_path)
    review = fixture["impact_reviews"][0]
    check = review[check_name] if check_name == "scope_check" else review[check_name][0]
    check.update(result="fail", reason="Independent reviewer rejected this exact premise.", evidence_refs=[])
    write_impact_reviews(fixture)
    outcome = impact_review_outcome(fixture)
    assert outcome["result"] == "fail", outcome
    assert outcome["reason"]
    bundle = impact_bundle(fixture)
    assert not any(row["conclusion"] in {"changed", "preserved"} for row in impacts_for(bundle))


@pytest.mark.parametrize("state", ["missing", "not_run", "error", "unresolved", "no_evidence"])
def test_required_impact_premise_cannot_be_silently_omitted(tmp_path, state):
    fixture = support_fixture(tmp_path)
    review = fixture["impact_reviews"][0]
    if state == "missing":
        review["base_checks"].pop()
    else:
        check = review["base_checks"][0]
        if state in {"not_run", "error"}:
            check.update(status=state, result=None, reason="The independent check did not complete.")
        elif state == "unresolved":
            check.update(result="unresolved", reason="The independent evidence remains unresolved.")
        else:
            check["evidence_refs"] = []
    write_impact_reviews(fixture)
    outcome = impact_review_outcome(fixture)
    assert outcome["result"] == ("fail" if state == "no_evidence" else "unresolved"), outcome
    assert outcome["reason"]


def test_impact_evidence_digest_pins_the_actual_review_bytes(tmp_path):
    fixture = support_fixture(tmp_path)
    path = fixture["impact_config"].parent / "review_0.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(InputError):
        impact_review_outcome(fixture)


def test_impact_package_cannot_configure_its_own_trust(tmp_path):
    from tools.language_relation_v0.impact_evidence import ImpactTrust

    fixture = support_fixture(tmp_path)
    internal_config = fixture["package"] / "impact-trust.json"
    internal_config.write_bytes(fixture["impact_config"].read_bytes())
    with pytest.raises(InputError):
        ImpactTrust.load(internal_config, fixture["package"])


def test_impact_trust_config_symlink_is_not_an_independent_path(tmp_path):
    from tools.language_relation_v0.impact_evidence import ImpactTrust

    fixture = support_fixture(tmp_path)
    symlink = tmp_path / "trust_link.json"
    symlink.symlink_to(fixture["impact_config"])
    with pytest.raises(InputError):
        ImpactTrust.load(symlink, fixture["package"])


def test_duplicate_impact_review_subject_is_rejected(tmp_path):
    fixture = support_fixture(tmp_path)
    duplicate = deepcopy(fixture["impact_reviews"][0])
    duplicate["verification_id"] = "second_review_same_subject"
    fixture["impact_reviews"].append(duplicate)
    write_impact_reviews(fixture)
    with pytest.raises(InputError):
        impact_review_outcome(fixture)


def source_bindings_for(payload: dict) -> list[dict]:
    binding = payload["processing_binding"]
    selected = {binding["before_source_id"], binding["after_source_id"], *binding["context_source_ids"]}
    fields = ("source_id", "role", "language", "revision", "content_sha256", "byte_length")
    return sorted([{key: row[key] for key in fields} for row in payload["sources"]
                   if row["source_id"] in selected], key=lambda row: row["source_id"])


def write_processing_record(fixture: dict) -> None:
    raw = fixtures.encoded(fixture["processing_record"])
    name = "processing.json"
    (fixture["source_config"].parent / name).write_bytes(raw)
    config = json.loads(fixture["source_config"].read_bytes())
    config["processing_files"] = [{"path": name, "content_sha256": fixtures.digest(raw)}]
    fixture["source_config"].write_bytes(fixtures.encoded(config))


def observation_fixture(tmp_path: Path, before_value=False, after_value=True) -> dict:
    payload = fixtures.reference_input()
    payload["measurement_request"]["processing_claim"] = "processing_change"
    payload["measurement_request"]["targets"][0]["question"] = "observed_effect"
    payload["processing_binding"] = {"processing_id": "processing_1",
        "before_source_id": "source_before", "after_source_id": "source_after",
        "context_source_ids": [], "evidence_refs": ["processing_evidence_1"]}
    fixture = fixtures.accepted_fixture(tmp_path, payload)
    input_ref = {"artifact_id": fixture["payload"]["case_id"],
                 "content_sha256": fixtures.digest(fixture["input_path"].read_bytes())}
    fixture["processing_record"] = fixtures.evidence_document("language_relation_processing_record_v0",
        evidence_id="processing_evidence_1", processing_id="processing_1", operation="synthetic_language_rewrite",
        input_ref=deepcopy(input_ref), profile_ref=deepcopy(payload["profile_ref"]),
        source_bindings=source_bindings_for(payload),
        execution={"status": "completed", "result": "pass", "reason": None})
    write_processing_record(fixture)
    directory = tmp_path / "impact_trust"
    directory.mkdir()
    observation_ref = {"observation_id": "observed_event_1", "subject_id": "synthetic_subject_1",
                       "run_id": "synthetic_run_1", "event_id": "synthetic_event_1"}
    review = {"schema_version": "language_relation_impact_review_v0",
        "verification_id": "impact_review_target_main", "input_ref": deepcopy(input_ref),
        "profile_ref": deepcopy(payload["profile_ref"]), "target_id": "target_main", "mode": "observed",
        "model_ref": None, "claim_ids": [],
        "reviewed_variant_ids": [row["variant_id"] for row in payload["interpretations"]["variants"]],
        "scope_check": impact_check("scope_target_main", context_source_ids=[],
            correspondence_ids=sorted({key for row in payload["interpretations"]["variants"]
                                       for key in row["correspondence_ids"]}), withdrawal_semantics=None),
        "base_checks": [], "rule_checks": [], "observation_ref": observation_ref}
    observation = {"schema_version": "language_relation_impact_observation_v0", **observation_ref,
        "input_ref": deepcopy(input_ref), "profile_ref": deepcopy(payload["profile_ref"]),
        "target_id": "target_main", "reviewed_variant_ids": list(review["reviewed_variant_ids"]),
        "processing_id": "processing_1", "before_value": before_value, "after_value": after_value,
        "source_bindings": source_bindings_for(payload),
        "check": impact_check("observation_check", method="independent_event_observation")}
    fixture.update(impact_config=directory / "config.json", impact_reviews=[review], observations=[observation])
    write_impact_reviews(fixture)
    return fixture


@pytest.mark.parametrize("before_value,after_value,expected", [(False, True, "changed"),
                                                              (True, True, "preserved")])
def test_observed_before_after_outcome_keeps_observation_separate_from_causation(
        tmp_path, before_value, after_value, expected):
    fixture = observation_fixture(tmp_path, before_value, after_value)
    assert impact_review_outcome(fixture)["result"] == "pass"
    bundle = impact_bundle(fixture)
    assert_authority_boundary(bundle)
    rows = impacts_for(bundle, kind="observed_consequence")
    assert len(rows) == 1, bundle["measurement"]["impacts"]
    assert rows[0]["conclusion"] == expected
    assert rows[0]["representation_basis"] == "accepted_reference"
    assert rows[0]["witness_ids"] and rows[0]["evidence_refs"]
    assert bundle["measurement"]["status_axes"]["causal_status"] == "not_evaluated"


@pytest.mark.parametrize("field", ["subject_id", "run_id", "event_id", "processing_id", "input_ref",
                                   "source_revision", "source_digest"])
def test_observation_cannot_splice_a_different_event_or_processing_instance(tmp_path, field):
    fixture = observation_fixture(tmp_path)
    record = fixture["observations"][0]
    if field in {"subject_id", "run_id", "event_id", "processing_id"}:
        record[field] = "another_instance"
    elif field == "input_ref":
        record[field]["content_sha256"] = "0" * 64
    elif field == "source_revision":
        record["source_bindings"][0]["revision"] = "another_revision"
    else:
        record["source_bindings"][0]["content_sha256"] = "0" * 64
    write_impact_reviews(fixture)
    assert impact_review_outcome(fixture)["result"] == "fail"
    bundle = impact_bundle(fixture)
    assert not impacts_for(bundle, kind="observed_consequence")
    assert all(row["conclusion"] == "unresolved" for row in impacts_for(bundle))


@pytest.mark.parametrize("missing", ["before_value", "after_value"])
def test_single_observation_does_not_supply_a_before_after_change(tmp_path, missing):
    fixture = observation_fixture(tmp_path)
    del fixture["observations"][0][missing]
    write_impact_reviews(fixture)
    with pytest.raises(InputError):
        impact_review_outcome(fixture)


@pytest.mark.parametrize("check_state", ["missing_record", "not_run", "fail", "unresolved", "no_evidence"])
def test_observed_result_requires_its_own_completed_independent_evidence(tmp_path, check_state):
    fixture = observation_fixture(tmp_path)
    if check_state == "missing_record":
        fixture["observations"] = []
    else:
        check = fixture["observations"][0]["check"]
        if check_state == "not_run":
            check.update(status="not_run", result=None, reason="This event has not been independently checked.")
        elif check_state == "no_evidence":
            check["evidence_refs"] = []
        else:
            check.update(result=check_state, reason="This exact event is not accepted.")
    write_impact_reviews(fixture)
    assert impact_review_outcome(fixture)["result"] != "pass"
    bundle = impact_bundle(fixture)
    assert not impacts_for(bundle, kind="observed_consequence")
    assert_authority_boundary(bundle)


def test_observation_cannot_replace_independent_processing_evidence(tmp_path):
    fixture = observation_fixture(tmp_path)
    source_config = json.loads(fixture["source_config"].read_bytes())
    source_config["processing_files"] = []
    fixture["source_config"].write_bytes(fixtures.encoded(source_config))
    bundle = impact_bundle(fixture)
    assert not impacts_for(bundle, kind="observed_consequence")
    assert all(row["conclusion"] == "unresolved" for row in impacts_for(bundle))


def detail_for(bundle: dict, target_id="target_main") -> dict:
    rows = [row for row in bundle["impact"]["targets"] if row["target_id"] == target_id]
    assert len(rows) == 1, bundle["impact"]["targets"]
    return rows[0]


def duplicate_target(payload: dict, target_id="target_aux") -> None:
    target = deepcopy(payload["measurement_request"]["targets"][0])
    original_id = target["target_id"]
    original_obligations = set(target["required_obligation_ids"])
    target["target_id"] = target_id
    mapping = {key: key + "_" + target_id for key in original_obligations}
    target["required_obligation_ids"] = [mapping[key] for key in target["required_obligation_ids"]]
    payload["measurement_request"]["targets"].append(target)
    for obligation in list(payload["coverage_obligations"]):
        if obligation["target_id"] == original_id and obligation["obligation_id"] in original_obligations:
            copy = deepcopy(obligation)
            copy.update(target_id=target_id, obligation_id=mapping[obligation["obligation_id"]])
            payload["coverage_obligations"].append(copy)


def test_relation_change_and_preserved_backup_support_are_separate_results(tmp_path):
    fixture = support_fixture(tmp_path)
    bundle = impact_bundle(fixture)
    assert_authority_boundary(bundle)
    assert fixtures.result_for(bundle["measurement"])["relation_state"] == "CHANGED"
    detail = detail_for(bundle)
    assert detail["assessment_state"] == "IDENTIFIED", detail
    assert detail["kind"] == "support"
    assert detail["conclusion"] == "preserved"
    transition = detail["support"]
    assert transition["after"]["grounded_claim_ids"] == ["claim_bela", "claim_eva"]
    paths = [row for row in transition["after"]["support_paths"] if row["claim_id"] == "claim_bela"]
    assert paths == [{"claim_id": "claim_bela", "base_claim_ids": ["claim_eva"], "rule_ids": ["rule_eb"]}]
    assert transition["lost_claim_ids"] == ["claim_anna"]
    assert bundle["measurement"]["support"] == transition["after"]
    projection = impacts_for(bundle, kind="support_change")
    assert len(projection) == 1 and projection[0]["conclusion"] == "preserved"
    assert projection[0]["witness_ids"] and projection[0]["evidence_refs"]


def test_withdrawal_of_only_admitted_foundation_changes_support(tmp_path):
    payload = fixtures.reference_input(23)
    model = payload["impact_model"]
    model["claims"] = [row for row in model["claims"] if row["claim_id"] != "claim_eva"]
    model["rules"] = [row for row in model["rules"] if row["rule_id"] != "rule_eb"]
    fixture = support_fixture(tmp_path, payload=payload)
    detail = detail_for(impact_bundle(fixture))
    assert detail["assessment_state"] == "IDENTIFIED", detail
    assert detail["conclusion"] == "changed"
    assert detail["support"]["before"]["grounded_claim_ids"] == ["claim_anna", "claim_bela"]
    assert detail["support"]["after"]["grounded_claim_ids"] == []
    assert detail["support"]["after"]["support_paths"] == []


def test_preserved_relation_does_not_create_a_foundation_for_a_support_cycle(tmp_path):
    fixture = support_fixture(tmp_path, number=22)
    bundle = impact_bundle(fixture)
    assert fixtures.result_for(bundle["measurement"])["relation_state"] == "PRESERVED"
    transition = detail_for(bundle)["support"]
    assert transition is not None
    for side in ("before", "after"):
        assert transition[side]["grounded_claim_ids"] == []
        assert transition[side]["support_paths"] == []
        assert transition[side]["unsupported_cycle_claim_ids"] == ["claim_anna", "claim_bela"]
    assert_authority_boundary(bundle)


def test_rejected_other_target_does_not_poison_closed_support_scope(tmp_path):
    payload = fixtures.reference_input(23)
    duplicate_target(payload)
    fixture = support_fixture(tmp_path, payload=payload)
    other = support_review(fixture, "target_aux")
    other["scope_check"].update(result="fail", reason="The independent scope review rejects this target.")
    fixture["impact_reviews"].append(other)
    write_impact_reviews(fixture)
    bundle = impact_bundle(fixture)
    assert detail_for(bundle)["assessment_state"] == "IDENTIFIED"
    assert detail_for(bundle)["conclusion"] == "preserved"
    assert detail_for(bundle, "target_aux")["assessment_state"] != "IDENTIFIED"
    assert detail_for(bundle, "target_aux")["conclusion"] == "unresolved"
    assert all(row["conclusion"] == "unresolved" for row in impacts_for(bundle, "target_aux"))
    assert fixtures.result_for(bundle["measurement"])["assessment_state"] == "IDENTIFIED"
    assert fixtures.result_for(bundle["measurement"], "target_aux")["assessment_state"] == "IDENTIFIED"


def test_incomplete_interpretation_family_cannot_establish_support_preservation(tmp_path):
    payload = fixtures.reference_input(23)
    payload["interpretations"]["state"] = "truncated"
    payload["interpretations"]["reason"] = "Only one interpretation was evaluated."
    fixture = support_fixture(tmp_path, payload=payload)
    bundle = impact_bundle(fixture)
    detail = detail_for(bundle)
    assert detail["assessment_state"] != "IDENTIFIED", detail
    assert detail["conclusion"] == "unresolved"
    assert detail["reason"]


def test_support_resource_exhaustion_preserves_other_target_diagnostics(tmp_path, monkeypatch):
    payload = fixtures.reference_input(23)
    duplicate_target(payload)
    fixture = support_fixture(tmp_path, payload=payload)
    monkeypatch.setattr(support, "MAX_SUPPORT_PATHS", 1)
    bundle = impact_bundle(fixture)
    assert detail_for(bundle)["assessment_state"] != "IDENTIFIED"
    assert detail_for(bundle)["conclusion"] == "unresolved"
    assert detail_for(bundle)["support"] is None
    assert fixtures.result_for(bundle["measurement"], "target_aux")["assessment_state"] == "IDENTIFIED"
    assert {row["target_id"] for row in bundle["impact"]["targets"]} == {"target_main", "target_aux"}


def joint_condition_payload() -> dict:
    payload = fixtures.reference_input()
    duplicate_target(payload, "target_second")
    for side in ("before", "after"):
        prefix = side[0]
        relations = payload["representations"][side]["relations"]
        second = deepcopy(relations[0])
        second["relation_id"] = prefix + "_second"
        if side == "after":
            second["expression"] = {"op": "NOT", "operand": second["expression"]}
        relations.append(second)
        payload["interpretations"]["variants"][0][side + "_relation_ids"].append(prefix + "_second")
        # This independently reviewed two-condition text deliberately exceeds the
        # controlled one-sentence grammar; it is not a false successful parse.
        text = ("Reviewed condition one: Anna approves. Reviewed condition two: Anna approves."
                if side == "before" else
                "Reviewed condition one: Anna approves. Reviewed condition two: Anna does not approve.")
        fixtures.replace_source(payload, side, text)
    target = payload["measurement_request"]["targets"][1]
    target.update(before_ids=["b_second"], after_ids=["a_second"])
    for target in payload["measurement_request"]["targets"]:
        target["question"] = "condition_impact"
    relation_mapping = deepcopy(next(row for row in payload["correspondence"] if row["kind"] == "relation"))
    relation_mapping.update(correspondence_id="map_second", before_ids=["b_second"], after_ids=["a_second"])
    payload["correspondence"].append(relation_mapping)
    payload["interpretations"]["variants"][0]["correspondence_ids"].append("map_second")
    return payload


def condition_group(payload: dict, target_ids=None) -> dict:
    from tools.language_relation_v0.impact_logic import evaluate_condition_group

    targets = payload["measurement_request"]["targets"]
    if target_ids is not None:
        targets = [row for row in targets if row["target_id"] in target_ids]
    return evaluate_condition_group(payload, fixtures.PROFILE, targets)


def test_joint_possibility_change_survives_identical_marginal_value_sets():
    payload = joint_condition_payload()
    outcome = condition_group(payload)
    assert outcome["state"] == "identified", outcome
    assert outcome["joint_conclusion"] == "changed"
    assert outcome["per_target"]["target_main"]["conclusion"] == "preserved"
    assert outcome["per_target"]["target_second"]["conclusion"] == "changed"
    variant, = outcome["variants"]
    assert variant["before_vectors"] == [[False, False], [True, True]]
    assert variant["after_vectors"] == [[False, True], [True, False]]
    for index in (0, 1):
        assert {row[index] for row in variant["before_vectors"]} == {False, True}
        assert {row[index] for row in variant["after_vectors"]} == {False, True}
    witness = variant["joint_witness"]
    assert witness["valuation"]
    other = "after" if witness["side"] == "before" else "before"
    assert witness["vector"] in variant[witness["side"] + "_vectors"]
    assert witness["vector"] not in variant[other + "_vectors"]


def test_condition_satisfaction_change_does_not_imply_changed_possibility_set():
    outcome = condition_group(joint_condition_payload(), ["target_second"])
    assert outcome["state"] == "identified", outcome
    assert outcome["per_target"]["target_second"]["conclusion"] == "changed"
    assert outcome["joint_conclusion"] == "preserved"
    variant, = outcome["variants"]
    assert variant["before_vectors"] == variant["after_vectors"] == [[False], [True]]
    assert variant["counterexamples"]["target_second"]


def test_condition_counterexample_is_rechecked_in_one_shared_configuration():
    from tools.language_relation_v0.logic import VariantLogic

    payload = joint_condition_payload()
    outcome = condition_group(payload)
    variant = payload["interpretations"]["variants"][0]
    logic = VariantLogic(payload, fixtures.PROFILE, variant)
    valuation = outcome["variants"][0]["joint_witness"]["valuation"]
    values = {row["atom_id"]: row["value"] for row in valuation}
    assert values and len(set(values.values())) == 1
    vector = []
    for target in sorted(payload["measurement_request"]["targets"], key=lambda row: row["target_id"]):
        # Projection is still the same common configuration, not a separately
        # chosen convenient valuation for each target.
        checked = logic.check_valuation(target["before_ids"], target["after_ids"], valuation)
        vector.append(checked[outcome["variants"][0]["joint_witness"]["side"] + "_value"])
    assert vector == outcome["variants"][0]["joint_witness"]["vector"]


def test_unnamed_ground_atoms_cannot_publish_an_uncheckable_condition_witness():
    outcome = condition_group(fixtures.reference_input(5))
    assert outcome["state"] == "unresolved", outcome
    assert outcome["per_target"]["target_main"]["conclusion"] == "unresolved"
    assert not any(row["counterexamples"] for row in outcome["variants"])


@pytest.mark.parametrize("family_state", ["truncated", "unknown", "empty"])
def test_incomplete_or_empty_condition_family_is_never_vacuously_preserved(family_state):
    payload = joint_condition_payload()
    payload["interpretations"].update(state=family_state, reason="The complete family is not available.")
    if family_state in {"unknown", "empty"}:
        payload["interpretations"]["variants"] = []
    outcome = condition_group(payload)
    assert outcome["state"] != "identified"
    assert outcome["joint_conclusion"] == "unresolved"
    assert outcome["enumeration_complete"] is False
    assert all(row["conclusion"] == "unresolved" for row in outcome["per_target"].values())


def test_unsupported_typed_condition_does_not_become_plain_boolean_truth():
    payload = joint_condition_payload()
    next(row for row in payload["representations"]["after"]["relations"]
         if row["relation_id"] == "a_second")["modality"] = "permission"
    outcome = condition_group(payload)
    assert outcome["state"] == "unresolved"
    assert outcome["joint_conclusion"] == "unresolved"
    assert outcome["failures"]
    assert condition_group(payload, ["target_main"])["state"] == "identified"


def test_common_configuration_budget_exhaustion_does_not_publish_a_prefix(monkeypatch):
    from tools.language_relation_v0 import impact_logic

    monkeypatch.setattr(impact_logic, "MAX_CONDITION_CONFIGURATIONS", 1)
    outcome = condition_group(joint_condition_payload())
    assert outcome["state"] == "unresolved"
    assert outcome["enumeration_complete"] is False
    assert any(row["code"] == "condition_configuration_limit" for row in outcome["failures"])
    assert all(row["conclusion"] == "unresolved" for row in outcome["per_target"].values())


def test_independent_target_conditions_and_joint_structure_are_both_measured(tmp_path):
    fixture = fixtures.accepted_fixture(tmp_path, joint_condition_payload())
    bundle = impact_bundle(fixture)
    assert_authority_boundary(bundle)
    assert detail_for(bundle)["conclusion"] == "preserved", bundle["impact"]
    assert detail_for(bundle, "target_second")["conclusion"] == "changed", bundle["impact"]
    assert bundle["impact"]["joint_conditions"]["joint_conclusion"] == "changed"
    assert impacts_for(bundle, "target_second", "condition_satisfaction_change")
    assert any(row["kind"] == "model_possibility_change" for row in bundle["measurement"]["impacts"])
    assert not any(row["kind"] == "observed_consequence" for row in bundle["measurement"]["impacts"])


def test_unsupported_other_condition_leaves_independent_target_identified(tmp_path):
    payload = joint_condition_payload()
    next(row for row in payload["representations"]["after"]["relations"]
         if row["relation_id"] == "a_second")["modality"] = "permission"
    fixture = fixtures.accepted_fixture(tmp_path, payload)
    bundle = impact_bundle(fixture)
    assert detail_for(bundle)["assessment_state"] == "IDENTIFIED", bundle["impact"]
    assert detail_for(bundle)["conclusion"] == "preserved"
    assert detail_for(bundle, "target_second")["assessment_state"] != "IDENTIFIED"
    assert detail_for(bundle, "target_second")["conclusion"] == "unresolved"
    assert bundle["impact"]["joint_conditions"]["joint_conclusion"] == "unresolved"


def opposing_claim_payload(*, grounded_opponent=True, unrelated_conflict=True) -> dict:
    payload = fixtures.reference_input(23)
    original = payload["impact_model"]
    anna = deepcopy(next(row for row in original["claims"] if row["claim_id"] == "claim_anna"))
    not_anna = deepcopy(anna)
    not_anna.update(claim_id="claim_not_anna", is_base=grounded_opponent,
                    expression={"op": "NOT", "operand": deepcopy(anna["expression"])})
    claims = [anna, not_anna]
    if unrelated_conflict:
        eva = deepcopy(next(row for row in original["claims"] if row["claim_id"] == "claim_eva"))
        not_eva = deepcopy(eva)
        not_eva.update(claim_id="claim_not_eva", expression={"op": "NOT", "operand": deepcopy(eva["expression"])})
        claims.extend([eva, not_eva])
    original.update(claims=claims, rules=[], target_claim_ids=["claim_anna"], withdrawn_claim_ids=[])
    return payload


def test_independently_grounded_opponent_outside_ancestry_is_in_scope(tmp_path):
    fixture = support_fixture(tmp_path, payload=opposing_claim_payload())
    outcome = impact_review_outcome(fixture)
    assert outcome["result"] == "pass", outcome
    assert {row["claim_id"] for row in outcome["model"]["claims"]} == {"claim_anna", "claim_not_anna"}
    bundle = impact_bundle(fixture)
    detail = detail_for(bundle)
    assert detail["assessment_state"] != "IDENTIFIED", detail
    assert detail["conclusion"] == "unresolved"
    assert detail["support"]["after"]["conflicts"] == [
        {"claim_id": "claim_anna", "opposes_claim_id": "claim_not_anna"}]
    assert all(row["conclusion"] == "unresolved" for row in impacts_for(bundle))


def test_ungrounded_opponent_is_retained_without_fabricating_a_conflict(tmp_path):
    fixture = support_fixture(tmp_path, payload=opposing_claim_payload(grounded_opponent=False))
    outcome = impact_review_outcome(fixture)
    assert outcome["result"] == "pass", outcome
    assert {row["claim_id"] for row in outcome["model"]["claims"]} == {"claim_anna", "claim_not_anna"}
    detail = detail_for(impact_bundle(fixture))
    assert detail["assessment_state"] == "IDENTIFIED", detail
    assert detail["support"]["after"]["grounded_claim_ids"] == ["claim_anna"]
    assert detail["support"]["after"]["conflicts"] == []


def test_unrelated_conflicting_component_is_not_a_target_premise(tmp_path):
    payload = opposing_claim_payload()
    payload["impact_model"]["claims"] = [row for row in payload["impact_model"]["claims"]
                                          if row["claim_id"] != "claim_not_anna"]
    fixture = support_fixture(tmp_path, payload=payload)
    outcome = impact_review_outcome(fixture)
    assert {row["claim_id"] for row in outcome["model"]["claims"]} == {"claim_anna"}
    detail = detail_for(impact_bundle(fixture))
    assert detail["assessment_state"] == "IDENTIFIED", detail
    assert detail["support"]["after"]["conflicts"] == []


def test_context_and_selected_conditions_use_the_same_configuration():
    payload = fixtures.reference_input(5)
    fixtures.ground_helpers(payload)
    payload["interpretations"]["variants"][0]["context_constraints"] = [
        {"op": "REF", "relation_id": "b_atom_anna"}, {"op": "REF", "relation_id": "b_atom_bela"}]
    outcome = condition_group(payload)
    assert outcome["state"] == "identified", outcome
    assert outcome["per_target"]["target_main"]["conclusion"] == "preserved"
    assert outcome["variants"][0]["configuration_count"] == 1


def test_contradictory_context_is_incompatible_not_vacuously_preserved():
    payload = joint_condition_payload()
    reference = {"op": "REF", "relation_id": "b_main"}
    payload["interpretations"]["variants"][0]["context_constraints"] = [
        reference, {"op": "NOT", "operand": deepcopy(reference)}]
    outcome = condition_group(payload)
    assert outcome["state"] == "incompatible"
    assert outcome["joint_conclusion"] == "unresolved"
    assert any(row["code"] == "incompatible_context" for row in outcome["failures"])


def test_different_variant_conclusions_are_not_combined_into_one_joint_result():
    payload = fixtures.reference_input(5)
    fixtures.ground_helpers(payload)
    second = deepcopy(payload["interpretations"]["variants"][0])
    second.update(variant_id="variant_2", context_constraints=[
        {"op": "REF", "relation_id": "b_atom_anna"}, {"op": "REF", "relation_id": "b_atom_bela"}])
    payload["interpretations"]["variants"].append(second)
    outcome = condition_group(payload)
    assert outcome["enumeration_complete"] is True
    assert outcome["state"] == "unresolved"
    assert outcome["per_target"]["target_main"]["conclusion"] == "unresolved"
    assert [row["per_target"]["target_main"]["conclusion"] for row in outcome["variants"]] == ["changed", "preserved"]
    assert [row["configuration_count"] for row in outcome["variants"]] == [4, 1]


def test_cumulative_condition_work_budget_is_a_diagnostic_boundary(monkeypatch):
    from tools.language_relation_v0 import impact_logic

    monkeypatch.setattr(impact_logic, "MAX_CONDITION_EVALUATIONS", 2)
    outcome = condition_group(joint_condition_payload())
    assert outcome["state"] == "unresolved"
    assert outcome["enumeration_complete"] is False
    assert any(row["code"] == "condition_evaluation_limit" for row in outcome["failures"])


def test_condition_recursion_exhaustion_becomes_an_unresolved_variant(monkeypatch):
    from tools.language_relation_v0 import impact_logic

    def exhausted(*args, **kwargs):
        raise RecursionError("synthetic execution-budget exhaustion")

    monkeypatch.setattr(impact_logic, "VariantLogic", exhausted)
    outcome = condition_group(joint_condition_payload())
    assert outcome["state"] == "unresolved"
    assert any(row["code"] == "condition_recursion_limit" for row in outcome["failures"])


def assert_bundle_identity(bundle: dict) -> None:
    assert set(bundle) == {"measurement", "verification", "impact"}
    report, verification, impact = (bundle[key] for key in ("measurement", "verification", "impact"))
    assert report["input_ref"] == verification["input_ref"] == impact["input_ref"]
    assert report["profile_ref"] == verification["profile_ref"] == impact["profile_ref"]
    assert report["verification_refs"] == [{"artifact_id": verification["verification_id"],
                                            "content_sha256": sha256(canonical_bytes(verification))}]
    for artifact, id_field in ((report, "measurement_id"), (verification, "verification_id"), (impact, "impact_id")):
        unhashed = {key: value for key, value in artifact.items() if key != id_field}
        assert artifact[id_field].endswith(sha256(canonical_bytes(unhashed))[:48]), (id_field, artifact[id_field])
    evidence = {ref for check in verification["checks"] for ref in check["evidence_refs"]}
    assert impact["impact_id"] in evidence
    assert any(sha256(canonical_bytes(impact)) in ref for ref in evidence)
    witnesses = {row["witness_id"]: row for row in report["witnesses"]}
    for detail in impact["targets"]:
        assert detail["causal_status"] == "not_evaluated"
        assert set(detail["witness_ids"]) <= witnesses.keys()
        assert all(witnesses[key]["target_id"] == detail["target_id"] for key in detail["witness_ids"])
    for projection in report["impacts"]:
        assert set(projection["witness_ids"]) <= witnesses.keys()
        assert all(witnesses[key]["target_id"] == projection["target_id"] for key in projection["witness_ids"])
    assert_authority_boundary(bundle)


def test_full_impact_bundle_has_exact_acyclic_hashes_and_reproducible_bytes(tmp_path):
    fixture = support_fixture(tmp_path)
    original = deepcopy(fixture["payload"])
    first = impact_bundle(fixture)
    second = impact_bundle(fixture)
    assert first == second
    assert fixture["payload"] == original
    assert_bundle_identity(first)
    assert first["impact"]["input_ref"]["content_sha256"] == fixtures.digest(fixture["input_path"].read_bytes())
    assert "measurement_ref" not in first["impact"] and "verification_ref" not in first["impact"]
    schema = json.loads((ROOT / "schemas/language_relation_impact_v0.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(first["impact"])


def test_equivalent_trusted_json_bytes_still_change_the_bound_evidence_identity(tmp_path):
    fixture = support_fixture(tmp_path)
    first = impact_bundle(fixture)
    review_path = fixture["impact_config"].parent / "review_0.json"
    raw = review_path.read_bytes() + b" "
    review_path.write_bytes(raw)
    config = json.loads(fixture["impact_config"].read_bytes())
    config["review_files"][0]["content_sha256"] = fixtures.digest(raw)
    fixture["impact_config"].write_bytes(fixtures.encoded(config))
    second = impact_bundle(fixture)
    assert detail_for(first)["conclusion"] == detail_for(second)["conclusion"] == "preserved"
    assert first["impact"]["impact_id"] != second["impact"]["impact_id"]
    assert first["measurement"]["measurement_id"] != second["measurement"]["measurement_id"]
    assert_bundle_identity(second)


@pytest.mark.parametrize("explicit_with_impact", [True, False])
def test_cli_publishes_three_artifacts_with_exact_written_byte_bindings(tmp_path, explicit_with_impact):
    fixture = support_fixture(tmp_path)
    output = tmp_path / "published"
    args = ["--package-root", fixture["package"], "--trust-config", fixture["source_config"],
            "--comparison-trust-config", fixture["comparison_config"],
            "--impact-trust-config", fixture["impact_config"]]
    if explicit_with_impact:
        completed = invoke_impact_cli(fixture["input_path"], output, *args)
    else:
        completed = fixtures.invoke_cli(fixture["input_path"], output, *map(str, args))
    assert completed.returncode == 0, completed.stderr
    assert {path.name for path in output.iterdir()} == {"measurement.json", "verification.json", "impact.json"}
    raw = {key: (output / (key + ".json")).read_bytes() for key in ("measurement", "verification", "impact")}
    bundle = {key: json.loads(value) for key, value in raw.items()}
    assert_bundle_identity(bundle)
    assert bundle["measurement"]["verification_refs"][0]["content_sha256"] == fixtures.digest(raw["verification"])
    evidence = {ref for check in bundle["verification"]["checks"] for ref in check["evidence_refs"]}
    assert any(fixtures.digest(raw["impact"]) in ref for ref in evidence)
    assert all(raw[key] == canonical_bytes(value) for key, value in bundle.items())
    assert "authority_effect=none" in completed.stdout


def test_third_artifact_publication_failure_rolls_back_owned_partial_output(tmp_path, monkeypatch):
    fixture = support_fixture(tmp_path)
    bundle = impact_bundle(fixture)
    spec = importlib.util.spec_from_file_location("lrm04_cli_publication", CLI)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    actual_encoder = cli.canonical_bytes

    def fail_impact(artifact):
        if artifact.get("schema_version") == "language_relation_impact_v0":
            raise RuntimeError("synthetic third artifact write failure")
        return actual_encoder(artifact)

    monkeypatch.setattr(cli, "canonical_bytes", fail_impact)
    output = tmp_path / "must_be_rolled_back"
    with pytest.raises(RuntimeError, match="third artifact"):
        cli._publish(output, bundle)
    assert not output.exists()


def test_observation_retains_raw_subject_and_run_identities_outside_identifier_refs(tmp_path):
    fixture = observation_fixture(tmp_path)
    subject_id = "2026 reviewed subject A"
    run_id = "2026-11-08 17:25 UTC run with spaces"
    fixture["observations"][0].update(subject_id=subject_id, run_id=run_id)
    fixture["impact_reviews"][0]["observation_ref"].update(subject_id=subject_id, run_id=run_id)
    write_impact_reviews(fixture)
    bundle = impact_bundle(fixture)
    detail = detail_for(bundle)
    assert detail["assessment_state"] == "IDENTIFIED", detail
    assert detail["observation"]["subject_id"] == subject_id
    assert detail["observation"]["run_id"] == run_id
    for witness in bundle["measurement"]["witnesses"]:
        assert subject_id not in witness["premise_refs"]
        assert run_id not in witness["premise_refs"]
    assert_bundle_identity(bundle)


@pytest.mark.parametrize("incomplete", ["target_source_scope", "incompatible_variant"])
def test_accepted_impact_review_cannot_bypass_unclosed_measurement_premises(tmp_path, incomplete):
    payload = fixtures.reference_input(23)
    if incomplete == "target_source_scope":
        payload["coverage_obligations"][0]["source_ids"] = ["source_before"]
    else:
        variant = deepcopy(payload["interpretations"]["variants"][0])
        reference = {"op": "REF", "relation_id": "b_fact_anna"}
        variant.update(variant_id="variant_incompatible", context_constraints=[
            reference, {"op": "NOT", "operand": deepcopy(reference)}])
        payload["interpretations"]["variants"].append(variant)
    fixture = support_fixture(tmp_path, payload=payload)
    assert impact_review_outcome(fixture)["result"] == "pass"
    bundle = impact_bundle(fixture)
    detail = detail_for(bundle)
    assert detail["assessment_state"] != "IDENTIFIED", detail
    assert detail["conclusion"] == "unresolved"
    assert detail["reason"]
    assert bundle["measurement"]["support"] is None
    assert all(row["conclusion"] == "unresolved" for row in impacts_for(bundle))


def test_empty_optional_impact_artifact_is_still_bound_to_published_measurement(tmp_path):
    bundle = candidate_bundle(tmp_path, fixtures.reference_input())
    assert bundle["impact"]["targets"] == []
    assert bundle["impact"]["joint_conditions"] is None
    assert bundle["measurement"]["impacts"] == []
    assert bundle["measurement"]["support"] is None
    assert_bundle_identity(bundle)


def long_support_fixture(tmp_path: Path, length: int, *, large_target_count=1) -> dict:
    payload = fixtures.reference_input()
    claim_ids = [f"c{index:03d}_" + "c" * 123 for index in range(length)]
    rule_ids = [f"r{index:03d}_" + "r" * 123 for index in range(length - 1)]
    expression = payload["representations"]["before"]["relations"][0]["expression"]
    payload["impact_model"] = {"model_id": "long_identified_support_chain",
        "claims": [{"claim_id": identifier, "expression": deepcopy(expression), "is_base": index == 0,
                    "evidence_refs": [], "source_anchor_ids": ["anchor_before"]}
                   for index, identifier in enumerate(claim_ids)],
        "rules": [{"rule_id": identifier, "premise_claim_ids": [claim_ids[index]],
                   "conclusion_claim_id": claim_ids[index + 1], "rule_basis_ref": "SUPPORT_01"}
                  for index, identifier in enumerate(rule_ids)],
        "withdrawn_claim_ids": [], "target_claim_ids": [claim_ids[-1], claim_ids[0]]}
    if large_target_count == 2:
        duplicate_target(payload, "target_secondary")
    duplicate_target(payload, "target_z_stable")
    fixture = support_fixture(tmp_path, payload=payload)
    fixture["impact_reviews"] = []
    for target in fixture["payload"]["measurement_request"]["targets"]:
        selected = claim_ids[0] if target["target_id"] == "target_z_stable" else claim_ids[-1]
        fixture["impact_reviews"].append(support_review(fixture, target["target_id"], [selected]))
    # The modeled IDs intentionally fill the schema's128-character allowance.
    # Check/evidence IDs are separate short identities, not concatenated claims.
    for index, review in enumerate(fixture["impact_reviews"]):
        for number, check in enumerate([review["scope_check"], *review["base_checks"], *review["rule_checks"]]):
            check["check_id"] = f"long_review_{index}_check_{number}"
            check["evidence_refs"] = [f"independent_long_review_{index}_check_{number}"]
    write_impact_reviews(fixture)
    return fixture


def full_chain_transition(fixture: dict) -> dict:
    model = fixture["payload"]["impact_model"]
    return support.support_transition(model,
        admitted_base_claim_ids=[row["claim_id"] for row in model["claims"] if row["is_base"]],
        admitted_rule_ids=[row["rule_id"] for row in model["rules"]])


def json_node_count(value) -> int:
    pending = [value]
    total = 0
    while pending:
        current = pending.pop()
        total += 1
        if isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return total


def assert_readable_publication(bundle: dict) -> None:
    from tools.language_relation_v0.io import strict_json

    for artifact in bundle.values():
        assert strict_json(canonical_bytes(artifact)) == artifact
    assert_bundle_identity(bundle)


def assert_publication_bound_detail(bundle: dict, target_id="target_main") -> None:
    detail = detail_for(bundle, target_id)
    assert detail["assessment_state"] == "UNRESOLVED", detail
    assert detail["conclusion"] == "unresolved"
    assert "publication resource bound" in detail["reason"]
    assert detail["support"] is None and detail["condition"] is None and detail["observation"] is None
    assert detail["witness_ids"] == []
    coverage = [row for row in bundle["verification"]["checks"]
                if row["kind"] == "coverage" and target_id in row["target_ids"]]
    assert any(row["result"] == "unresolved" for row in coverage)
    assert not any(row["conclusion"] != "unresolved" for row in impacts_for(bundle, target_id))


def test_actual_oversized_support_output_becomes_readable_diagnostics_for_every_target(tmp_path):
    from tools.language_relation_v0.io import MAX_JSON_BYTES

    fixture = long_support_fixture(tmp_path, 256)
    assert len(fixture["input_path"].read_bytes()) < MAX_JSON_BYTES
    assert len(canonical_bytes(full_chain_transition(fixture))) > MAX_JSON_BYTES
    assert impact_review_outcome(fixture)["result"] == "pass"
    bundle = impact_bundle(fixture)
    assert_publication_bound_detail(bundle)
    independent = detail_for(bundle, "target_z_stable")
    assert independent["assessment_state"] == "IDENTIFIED", independent
    assert independent["conclusion"] == "preserved"
    assert independent["support"]["after"]["grounded_claim_ids"]
    review_id = fixture["impact_reviews"][0]["verification_id"]
    assert any(row["result"] == "pass" and review_id in row["evidence_refs"]
               for row in bundle["verification"]["checks"])
    assert all(row["relation_state"] == "PRESERVED" for row in bundle["measurement"]["results"])
    assert_readable_publication(bundle)


def test_publication_node_budget_rejects_large_detail_below_byte_limit(tmp_path, monkeypatch):
    from tools.language_relation_v0 import impact

    fixture = long_support_fixture(tmp_path, 64)
    transition = full_chain_transition(fixture)
    assert len(canonical_bytes(transition)) < impact.MAX_IMPACT_PAYLOAD_BYTES
    assert json_node_count(transition) > 1000
    monkeypatch.setattr(impact, "MAX_IMPACT_PAYLOAD_NODES", 1000)
    bundle = impact_bundle(fixture)
    assert_publication_bound_detail(bundle)
    assert detail_for(bundle, "target_z_stable")["assessment_state"] == "IDENTIFIED"
    assert_readable_publication(bundle)


def test_publication_budget_is_shared_across_separately_admissible_target_details(tmp_path):
    from tools.language_relation_v0 import impact

    fixture = long_support_fixture(tmp_path, 96, large_target_count=2)
    size = len(canonical_bytes(full_chain_transition(fixture)))
    assert size < impact.MAX_IMPACT_PAYLOAD_BYTES < 2 * size
    bundle = impact_bundle(fixture)
    assert detail_for(bundle)["assessment_state"] == "IDENTIFIED", detail_for(bundle)
    assert_publication_bound_detail(bundle, "target_secondary")
    assert detail_for(bundle, "target_z_stable")["assessment_state"] == "IDENTIFIED"
    assert_readable_publication(bundle)


@pytest.mark.parametrize("limit,second_state", [(8, "IDENTIFIED"), (6, "UNRESOLVED")])
def test_wrapper_condition_budget_is_shared_by_individual_and_joint_evaluations(tmp_path, monkeypatch, limit, second_state):
    from tools.language_relation_v0 import impact, impact_logic

    fixture = fixtures.accepted_fixture(tmp_path, joint_condition_payload())
    evaluate = impact.evaluate_condition_group
    seeded = False

    def with_remaining_budget(*args, **kwargs):
        nonlocal seeded
        counter = kwargs.get("_evaluation_budget")
        if counter is not None and not seeded:
            # Preserve the schema's normative limit while simulating prior
            # work in this measurement. Later calls must retain this counter.
            counter[0] = impact_logic.MAX_CONDITION_EVALUATIONS - limit
            seeded = True
        return evaluate(*args, **kwargs)

    monkeypatch.setattr(impact, "evaluate_condition_group", with_remaining_budget)
    bundle = impact_bundle(fixture)
    first = detail_for(bundle)
    second = detail_for(bundle, "target_second")
    assert first["assessment_state"] == "IDENTIFIED", first
    assert second["assessment_state"] == second_state, second
    joint = bundle["impact"]["joint_conditions"]
    assert joint["joint_conclusion"] == "unresolved", joint
    assert joint["target_value_evaluations"] == 0
    assert sum(row["condition"]["target_value_evaluations"] for row in (first, second)) == limit
    assert_readable_publication(bundle)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
