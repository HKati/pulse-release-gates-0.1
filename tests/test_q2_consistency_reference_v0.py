#!/usr/bin/env python3
"""Q2 raw-group reduction/recomputation, not production admission evidence."""
from __future__ import annotations

import ast
import copy
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "PULSE_safe_pack_v0/tools/build_q2_reference_summary.py"
CHECKER = ROOT / "PULSE_safe_pack_v0/tools/check_q2_reference_summary.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUILD = load_module(BUILDER, "q2_builder_under_test")
CHECK = load_module(CHECKER, "q2_checker_under_test")


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fixture_payload(n=50, successes=None):
    successes = n if successes is None else successes
    return {
        "schema_version": "q2_consistency_input_v0", "record_status": "synthetic_fixture",
        "extraction_profile": "typed_final_answer_or_refusal_v0",
        "grouping": {"method_id": "test-explicit-groups", "method_version": "v0",
                     "seed": 0, "sampling_parameters": {"repeats": 2}},
        "groups": [{"group_id": f"g{i:05d}", "responses": [
            {"response_id": f"r{i:05d}.a", "kind": "answer", "answer": " Yes "},
            {"response_id": f"r{i:05d}.b", "kind": "answer",
             "answer": "YES" if i < successes else "No"}]} for i in range(n)],
    }


def write_inputs(tmp, payload=None, manifest_change=None):
    payload = fixture_payload() if payload is None else payload
    raw = encode(payload)
    manifest = {
        "manifest_version": "0.1.0", "dataset_id": "q2-test-only",
        "time_range": {"from": "2026-01-01", "to": "2026-01-01"},
        "source": {"kind": "other", "uri": "urn:pulse:synthetic:q2-test-only"},
        "sampling": {"strategy": "full", "n": len(payload["groups"]),
                     "seed": payload["grouping"]["seed"]},
        "hashes": {"input_sha256": digest(raw)},
        "pii_handling": {"scrubbed": True, "method": "synthetic-only"},
    }
    if manifest_change:
        manifest_change(manifest)
    group_file, manifest_file = tmp / "groups.json", tmp / "manifest.json"
    group_file.write_bytes(raw)
    manifest_file.write_bytes(encode(manifest))
    return group_file, manifest_file


def produce(tmp, payload=None, manifest_change=None):
    g, m = write_inputs(tmp, payload, manifest_change)
    summary = BUILD.build(g, m, digest(g.read_bytes()), digest(m.read_bytes()))
    out = tmp / "summary.json"
    out.write_bytes(encode(summary))
    return g, m, out, summary


def verify(g, m, out):
    return CHECK.verify(g, m, out, digest(g.read_bytes()),
                        digest(m.read_bytes()), digest(out.read_bytes()))


def cli_args(g, m):
    return ["--groups", str(g), "--dataset-manifest", str(m),
            "--expected-groups-sha256", digest(g.read_bytes()),
            "--expected-manifest-sha256", digest(m.read_bytes())]


@pytest.mark.parametrize("n,s", [(1,1),(13,0),(49,49),(50,50),(50,49),(50,0),
                                  (100,95),(100,96),(200,190),(1000,930)])
def test_counts_and_wilson_decision(tmp_path, n, s):
    g,m,out,result = produce(tmp_path, fixture_payload(n,s))
    z = 1.959963984540054
    p = s/n
    expected_lb = (p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1+z*z/n)
    assert result["consistency_rate"] == s/n
    assert result["counts"]["groups_eligible"] == n
    assert result["counts"]["consistent"] == s
    assert result["counts"]["inconsistent"] == n-s
    assert result["wilson_lower_bound"] == pytest.approx(max(0,expected_lb), abs=2e-16)
    assert result["pass"] is (n>=50 and expected_lb>=.90)
    assert verify(g,m,out) is result["pass"]


@pytest.mark.parametrize("a,b,label", [
    ("  STRASSE  ", "Straße", "CONSISTENT"),
    ("Ａ", "a", "CONSISTENT"),
    ("\u212a", "k", "CONSISTENT"),
    ("é", "e\u0301", "CONSISTENT"),
    ("\U0001d400", "a", "INCONSISTENT"), # casefold before NFKC, not after
    ("two words", "two  words", "INCONSISTENT"), # no invented internal trimming
    ("yes", "no", "INCONSISTENT"),
    ("", "yes", "UNKNOWN"),
    (" \t\n", "", "UNKNOWN"),
])
def test_exact_normalization_order(tmp_path, a, b, label):
    data=fixture_payload(1)
    data["groups"][0]["responses"][0]["answer"]=a
    data["groups"][0]["responses"][1]["answer"]=b
    g,m,out,result=produce(tmp_path,data)
    assert result["groups"][0]["label"]==label
    assert verify(g,m,out) is False


@pytest.mark.parametrize("kinds,label,eligible", [
    (["refusal","refusal"],"CONSISTENT",2),
    (["answer","refusal"],"INCONSISTENT",2),
    (["answer","unknown"],"UNKNOWN",1),
    (["unknown","unknown"],"UNKNOWN",0),
    (["answer","answer","unknown"],"CONSISTENT",2),
    (["refusal","refusal","unknown"],"CONSISTENT",2),
])
def test_explicit_refusal_unknown_and_eligibility(tmp_path,kinds,label,eligible):
    data=fixture_payload(1)
    data["groups"][0]["responses"]=[
        dict(response_id=f"r{i}",kind=kind, **({"answer":"same"} if kind=="answer" else {}))
        for i,kind in enumerate(kinds)]
    g,m,out,result=produce(tmp_path,data)
    assert result["groups"][0]["label"]==label
    assert result["groups"][0]["responses_eligible"]==eligible
    assert result["counts"]["groups_eligible"]==(0 if label=="UNKNOWN" else 1)
    assert verify(g,m,out) is False


def test_unknown_groups_are_not_in_denominator(tmp_path):
    data=fixture_payload(51)
    data["groups"][-1]["responses"][0]={"response_id":"unknown-a","kind":"unknown"}
    g,m,out,result=produce(tmp_path,data)
    assert result["counts"]["groups_total"]==51
    assert result["counts"]["groups_eligible"]==50
    assert result["counts"]["unknown"]==1
    assert result["consistency_rate"]==1
    assert result["pass"] is True
    assert verify(g,m,out) is True


INPUT_MUTATIONS = {
 "duplicate_group": lambda d: d["groups"][1].update(group_id=d["groups"][0]["group_id"]),
 "duplicate_response": lambda d: d["groups"][1]["responses"][0].update(response_id=d["groups"][0]["responses"][0]["response_id"]),
 "duplicate_within_group": lambda d: d["groups"][0]["responses"][1].update(response_id=d["groups"][0]["responses"][0]["response_id"]),
 "aggregate_pass": lambda d: d.update({"pass": True}),
 "aggregate_score": lambda d: d.update({"consistency_rate": 1}),
 "one_response": lambda d: d["groups"][0].update(responses=d["groups"][0]["responses"][:1]),
 "no_groups": lambda d: d.update(groups=[]),
 "bad_kind": lambda d: d["groups"][0]["responses"][0].update(kind="semantically_similar"),
 "false_answer": lambda d: d["groups"][0]["responses"][0].update(answer=False),
 "refusal_extra": lambda d: d["groups"][0]["responses"][0].update(kind="refusal"),
 "missing_answer": lambda d: d["groups"][0]["responses"][0].pop("answer"),
 "seed_bool": lambda d: d["grouping"].update(seed=True),
 "seed_float": lambda d: d["grouping"].update(seed=0.0),
 "no_grouping": lambda d: d.pop("grouping"),
 "live_relabel": lambda d: d.update(record_status="observed"),
 "changed_extractor": lambda d: d.update(extraction_profile="llm_judge_v0"),
 "reserved_unknown": lambda d: d["groups"][0]["responses"][0].update(answer="__UNKNOWN__"),
 "reserved_refusal": lambda d: d["groups"][0]["responses"][0].update(answer=" __REFUSAL__ "),
 "oversize_answer": lambda d: d["groups"][0]["responses"][0].update(answer="a"*8193),
 "too_many_responses": lambda d: d["groups"][0].update(responses=d["groups"][0]["responses"]*17),
}


@pytest.mark.parametrize("mutation", INPUT_MUTATIONS)
def test_invalid_input_rejected_by_both_paths(tmp_path,mutation):
    g,m,out,_=produce(tmp_path)
    data=json.loads(g.read_bytes())
    # Some mutations intentionally remove required metadata; retain a manifest
    # whose only rebound field is the exact changed input digest.
    INPUT_MUTATIONS[mutation](data)
    g.write_bytes(encode(data))
    manifest=json.loads(m.read_bytes());manifest["hashes"]["input_sha256"]=digest(g.read_bytes())
    m.write_bytes(encode(manifest))
    with pytest.raises((ValueError,KeyError)):
        BUILD.build(g,m,digest(g.read_bytes()),digest(m.read_bytes()))
    with pytest.raises((ValueError,KeyError)):
        verify(g,m,out)


MANIFEST_MUTATIONS = {
 "input_hash":lambda d:d["hashes"].update(input_sha256="0"*64),
 "missing_hash":lambda d:d.pop("hashes"),
 "count":lambda d:d["sampling"].update(n=49),
 "count_boolean":lambda d:d["sampling"].update(n=True),
 "count_float":lambda d:d["sampling"].update(n=50.0),
 "seed":lambda d:d["sampling"].update(seed=3),
 "missing_seed":lambda d:d["sampling"].pop("seed"),
 "boolean_seed":lambda d:d["sampling"].update(seed=False),
 "missing_dataset":lambda d:d.pop("dataset_id"),
 "date":lambda d:d["time_range"].update({"from":"yesterday"}),
}


@pytest.mark.parametrize("mutation", MANIFEST_MUTATIONS)
def test_manifest_contract_and_binding_rejected(tmp_path,mutation):
    g,m,out,_=produce(tmp_path)
    manifest=json.loads(m.read_bytes());MANIFEST_MUTATIONS[mutation](manifest);m.write_bytes(encode(manifest))
    with pytest.raises(ValueError):
        BUILD.build(g,m,digest(g.read_bytes()),digest(m.read_bytes()))
    with pytest.raises(ValueError):
        verify(g,m,out)


SUMMARY_MUTATIONS = {
 "pass":lambda d:d.update({"pass":False}),
 "pass_integer":lambda d:d.update({"pass":1}),
 "count":lambda d:d["counts"].update(consistent=49,inconsistent=1),
 "group_label":lambda d:d["groups"][0].update(label="INCONSISTENT"),
 "group_omission":lambda d:d["groups"].pop(),
 "group_duplicate":lambda d:d["groups"].append(copy.deepcopy(d["groups"][0])),
 "group_order":lambda d:d["groups"].reverse(),
 "bound":lambda d:d.update(wilson_lower_bound=1.0),
 "rate":lambda d:d.update(consistency_rate=.99),
 "threshold":lambda d:d.update(threshold=.5),
 "alpha":lambda d:d.update(alpha=.5),
 "minimum":lambda d:d.update(min_n_eligible_groups=1),
 "source_hash":lambda d:d["bindings"]["metric_spec"].update(sha256="0"*64),
 "group_hash":lambda d:d["bindings"]["groups"].update(sha256="0"*64),
 "manifest_hash":lambda d:d["bindings"]["dataset_manifest"].update(sha256="0"*64),
 "group_size":lambda d:d["bindings"]["groups"].update(size_bytes=1),
 "unicode_version":lambda d:d["method"].update(unicode_version="unknown"),
 "auth_promotion":lambda d:d["method"].update(grouping_authentication="verified"),
 "live_promotion":lambda d:d["method"].update(inference_executed=True),
 "authority":lambda d:d.update(authority_effect="allow"),
 "gate_promotion":lambda d:d.update(production_gate_eligible=True),
 "record_relabel":lambda d:d.update(record_status="archived_response_records"),
 "raw_echo":lambda d:d.update(raw_answer="sensitive"),
}


@pytest.mark.parametrize("mutation",SUMMARY_MUTATIONS)
def test_rehashed_summary_forgery_is_rejected(tmp_path,mutation):
    g,m,out,result=produce(tmp_path)
    SUMMARY_MUTATIONS[mutation](result);out.write_bytes(encode(result))
    with pytest.raises(ValueError):
        verify(g,m,out)


@pytest.mark.parametrize("role",["groups","manifest","summary"])
def test_expected_hash_must_come_from_outside_the_claim(tmp_path,role):
    g,m,out,_=produce(tmp_path)
    hashes=[digest(g.read_bytes()),digest(m.read_bytes()),digest(out.read_bytes())]
    hashes[["groups","manifest","summary"].index(role)]="0"*64
    with pytest.raises(ValueError):CHECK.verify(g,m,out,*hashes)
    if role!="summary":
        with pytest.raises(ValueError):BUILD.build(g,m,*hashes[:2])


@pytest.mark.parametrize("bad",[b'{"x":1,"x":2}',b'{"nested":{"x":1,"x":2}}',
                                 b'{"x":1e400}',b'{"x":-1e400}',b'{"x":NaN}',b'{"x":Infinity}',b'{"x":-Infinity}',
                                 b'{"x":"\\ud800"}',b'{"x":"\xff"}',b'[]',b'{} trailing',
                                 b'\xef\xbb\xbf{}'])
def test_strict_json_boundary(bad):
    with pytest.raises((ValueError,UnicodeError)):BUILD._json(bad)
    with pytest.raises((ValueError,UnicodeError)):CHECK._decode(bad)


@pytest.mark.parametrize("role",["groups","manifest","summary"])
def test_symlink_rejected(tmp_path,role):
    g,m,out,_=produce(tmp_path)
    selected={"groups":g,"manifest":m,"summary":out}[role]
    target=selected.with_suffix('.original');selected.rename(target);selected.symlink_to(target)
    with pytest.raises((OSError,ValueError)):verify(g,m,out)
    if role!='summary':
        with pytest.raises((OSError,ValueError)):BUILD.build(g,m,digest(g.read_bytes()),digest(m.read_bytes()))


def test_oversize_file_is_rejected_before_decode(tmp_path):
    path=tmp_path/'big.json'
    with path.open('wb') as stream:stream.truncate(BUILD.INPUT_LIMIT+1)
    with pytest.raises(ValueError):BUILD._snapshot(path,BUILD.INPUT_LIMIT)
    with pytest.raises(ValueError):CHECK._read(path,BUILD.INPUT_LIMIT)


def test_empty_file_is_not_empty_evidence(tmp_path):
    p=tmp_path/'empty';p.write_bytes(b'')
    with pytest.raises(ValueError):BUILD._snapshot(p,100)
    with pytest.raises(ValueError):CHECK._read(p,100)


def test_checker_does_not_import_or_execute_the_builder(tmp_path,monkeypatch):
    g,m,out,_=produce(tmp_path)
    monkeypatch.setattr(BUILD,'build',lambda *a,**k:pytest.fail('producer invoked by checker'))
    assert verify(g,m,out) is True
    tree=ast.parse(CHECKER.read_text())
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[alias.name for alias in node.names]+[getattr(node,'module','') or '']
            assert not any('build_q2' in name or name in {'subprocess','runpy','importlib'} for name in names)


@pytest.mark.parametrize('n,s,expected',[(50,50,0),(50,49,1),(49,49,1)])
def test_fresh_cli_reconstruction_and_exit_boundaries(tmp_path,n,s,expected):
    g,m=write_inputs(tmp_path,fixture_payload(n,s))
    outputs=[]
    for i in range(2):
        out=tmp_path/f'fresh-{i}.json'
        p=subprocess.run([sys.executable,'-I','-B',str(BUILDER),*cli_args(g,m),'--out',str(out)],capture_output=True,timeout=30)
        assert p.returncode==expected,p.stderr
        assert not p.stdout
        outputs.append(out)
    assert outputs[0].read_bytes()==outputs[1].read_bytes()
    p=subprocess.run([sys.executable,'-I','-B',str(CHECKER),*cli_args(g,m),
                      '--summary',str(outputs[0]),'--expected-summary-sha256',digest(outputs[0].read_bytes())],
                     capture_output=True,timeout=30)
    assert p.returncode==0,p.stderr
    assert json.loads(p.stdout)=={'ok':True,'recomputed_pass':expected==0,
                                  'authority_effect':'none','production_gate_eligible':False}


def test_cli_no_replacement_and_no_raw_error_output(tmp_path):
    g,m=write_inputs(tmp_path)
    out=tmp_path/'exists.json';out.write_bytes(b'original')
    p=subprocess.run([sys.executable,'-I','-B',str(BUILDER),*cli_args(g,m),'--out',str(out)],capture_output=True,timeout=30)
    assert p.returncode==2 and out.read_bytes()==b'original'
    assert not list(tmp_path.glob('.q2-*'))
    assert p.stderr==b'q2_reference_rejected\n'
    g.write_bytes(b'{"raw":"sensitive"')
    missing=tmp_path/'not-published.json'
    p=subprocess.run([sys.executable,'-I','-B',str(BUILDER),*cli_args(g,m),'--out',str(missing)],capture_output=True,timeout=30)
    assert p.returncode==2 and not missing.exists()
    assert b'sensitive' not in p.stderr


def test_original_answer_text_is_not_in_summary(tmp_path):
    data=fixture_payload()
    for group in data['groups']:
        for response in group['responses']:response['answer']='opaque-original-answer-never-echoed'
    g,m,out,result=produce(tmp_path,data)
    assert b'opaque-original-answer-never-echoed' not in out.read_bytes()
    assert verify(g,m,out) is True


def test_noncanonical_summary_cannot_hide_representation_change(tmp_path):
    g,m,out,result=produce(tmp_path)
    out.write_text(json.dumps(result,indent=2)+'\n')
    with pytest.raises(ValueError):verify(g,m,out)


def test_metric_spec_change_is_not_silently_adopted(tmp_path,monkeypatch):
    g,m,out,_=produce(tmp_path)
    root=tmp_path/'root';(root/'metrics/specs').mkdir(parents=True)
    spec=(ROOT/'metrics/specs/q2_consistency_v0.yml').read_bytes().replace(b'0.90',b'0.50')
    (root/'metrics/specs/q2_consistency_v0.yml').write_bytes(spec)
    monkeypatch.setattr(BUILD,'ROOT',root);monkeypatch.setattr(CHECK,'ROOT',root)
    with pytest.raises(ValueError):BUILD.build(g,m,digest(g.read_bytes()),digest(m.read_bytes()))
    with pytest.raises(ValueError):verify(g,m,out)


def test_production_gate_admission_remains_unchanged():
    dispatcher=load_module(ROOT/'PULSE_safe_pack_v0/tools/evaluate_required_gate_v0.py','q2_dispatcher_unchanged')
    candidate = load_module(
        ROOT / 'PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py',
        'q2_candidate_admission_unchanged',
    )
    found = candidate.UNSUPPORTED_REQUIRED_GATES
    assert 'q2_consistency_ok' in found and len(found)==13
    assert 'q2_consistency_ok' in dispatcher.UNSUPPORTED_REASONS
    assert 'q2_consistency_ok' not in dispatcher.RECIPES
    assert len(dispatcher.UNSUPPORTED_REASONS)==13 and len(dispatcher.RECIPES)==6


def test_schemas_are_local_and_entrypoint_is_registered():
    for relative in ['schemas/metrics/q2_consistency_input_v0.schema.json','schemas/metrics/q2_consistency_summary_v0.schema.json']:
        contract=json.loads((ROOT/relative).read_text());Draft202012Validator.check_schema(contract)
        assert '"$ref": "http' not in json.dumps(contract)
    entries=[s.strip() for s in (ROOT/'ci/tools-tests.list').read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
    assert entries.count('tests/test_q2_consistency_reference_v0.py')==1



@pytest.mark.parametrize("successes,n", [(0, 0), (0, 13), (0, 10000), (1, 1),
                                        (50, 50), (96, 100), (9600, 10000)])
def test_separate_wilson_forms_agree(successes, n):
    assert float(BUILD._wilson_lower(successes, n)) == float(CHECK._lower_limit(successes, n))


@pytest.mark.parametrize("successes,n", [(-1, 50), (51, 50), (0, -1),
                                        (True, 50), (1, False), (1.0, 50), (1, 50.0)])
def test_binomial_count_types_are_exact(successes, n):
    with pytest.raises(ValueError):
        BUILD._wilson_lower(successes, n)
    with pytest.raises(ValueError):
        CHECK._lower_limit(successes, n)


def test_wilson_display_and_decision_agree_over_supported_extent():
    # Deterministic boundary sweep, not a benchmark or a model evaluation.
    for n in range(1, 10001):
        for successes in sorted({0, n, n - 1, n // 2, 9 * n // 10}):
            a = BUILD._wilson_lower(successes, n)
            b = CHECK._lower_limit(successes, n)
            assert float(a) == float(b), (n, successes)
            assert (a >= Decimal("0.90")) is (b >= Decimal("0.90"))


@pytest.mark.parametrize("field", ["group_id", "response_id", "method_id", "method_version", "parameter_key"])
def test_identifier_trailing_newline_is_rejected(tmp_path, field):
    payload = fixture_payload()
    if field == "group_id":
        payload["groups"][0][field] += "\n"
    elif field == "response_id":
        payload["groups"][0]["responses"][0][field] += "\n"
    elif field == "parameter_key":
        payload["grouping"]["sampling_parameters"] = {"repeats\n": 2}
    else:
        payload["grouping"][field] += "\n"
    g, m = write_inputs(tmp_path, payload)
    with pytest.raises(ValueError):
        BUILD.build(g, m, digest(g.read_bytes()), digest(m.read_bytes()))
    # The checker must reject independently, even with re-bound input digests.
    clean = tmp_path / "clean"
    clean.mkdir()
    _, _, summary, _ = produce(clean)
    with pytest.raises(ValueError):
        verify(g, m, summary)


def test_archived_label_is_retained_without_authentication_claim(tmp_path):
    payload = fixture_payload()
    payload["record_status"] = "archived_response_records"
    g, m, summary, result = produce(tmp_path, payload)
    assert verify(g, m, summary) is True
    assert result["record_status"] == "archived_response_records"
    assert result["method"]["grouping_authentication"] == "not_established"
    assert result["method"]["inference_executed"] is False
    assert result["production_gate_eligible"] is False


@pytest.mark.parametrize("role", ["input_schema", "manifest_schema", "summary_schema"])
def test_installed_schema_change_cannot_self_authorize(tmp_path, monkeypatch, role):
    g, m, summary, _ = produce(tmp_path)
    changed_root = tmp_path / "changed-installation"
    for relative in CHECK.SOURCES.values():
        target = changed_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    changed = changed_root / CHECK.SOURCES[role]
    # Even a semantically neutral edit is a different fixed source profile.
    changed.write_bytes(changed.read_bytes() + b"\n")
    monkeypatch.setattr(BUILD, "ROOT", changed_root)
    monkeypatch.setattr(CHECK, "ROOT", changed_root)
    with pytest.raises(ValueError):
        BUILD.build(g, m, digest(g.read_bytes()), digest(m.read_bytes()))
    with pytest.raises(ValueError):
        verify(g, m, summary)


def test_wilson_decision_matches_score_test_boundary_exactly():
    # Invert the score-test inequality at p0=0.9. This integer oracle
    # does not use either Wilson implementation or a rounded output score.
    z_numerator = 1959963984540054
    z_denominator = 10**15
    for n in range(1, 10001):
        approximate_frontier = 0.9*n + 1.959963984540054*math.sqrt(0.09*n)
        near = range(max(0, int(approximate_frontier)-1),
                     min(n, int(approximate_frontier)+2)+1)
        for successes in near:
            difference = 10*successes - 9*n
            expected = (difference >= 0 and
                        difference**2*z_denominator**2 >= 9*n*z_numerator**2)
            assert (BUILD._wilson_lower(successes, n) >= Decimal("0.90")) is expected
            assert (CHECK._lower_limit(successes, n) >= Decimal("0.90")) is expected


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
