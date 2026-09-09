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
POLICY = ROOT / "pulse_gate_policy_v0.yml"
REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
POLICY_TO_REQUIRE_ARGS = ROOT / "tools" / "policy_to_require_args.py"
MATERIALIZER = (
    ROOT
    / "tools"
    / "fold_pulsemech_compute_planned_observed_relation_into_status_v0.py"
)
RELATION_SCHEMA = (
    ROOT / "schemas" / "pulsemech_compute_planned_observed_relation_v0.schema.json"
)
RELATION_VALIDATOR = (
    ROOT / "tools" / "check_pulsemech_compute_planned_observed_relation_v0.py"
)
RELATION_EXAMPLE = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_planned_observed_relation_example_v0.json"
)
CHECK_GATES = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_gates.py"
PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"

CANDIDATE_SET = "compute_planned_observed_relation_candidate"
CANDIDATE_GATES = [
    "compute_transition_path_complete",
    "compute_transition_authority_binding_ok",
    "compute_transition_unbound_mutation_absent",
]
ACTIVE_OR_BASELINE_SETS = [
    "required",
    "core_required",
    "release_required",
    "advisory",
]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_materializer_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "fold_pulsemech_compute_planned_observed_relation_into_status_v0_under_test",
        MATERIALIZER,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MATERIALIZER_MODULE = import_materializer_module()


def run_policy_to_require_args(gate_set: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(POLICY_TO_REQUIRE_ARGS),
            "--policy",
            str(POLICY),
            "--set",
            gate_set,
            "--format",
            "newline",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def materialize_gate_set(gate_set: str) -> list[str]:
    result = run_policy_to_require_args(gate_set)
    assert result.returncode == 0, result.stdout + result.stderr
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def run_materializer(
    *,
    status: Path,
    relation: Path,
    output: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_check_gates(
    status: Path,
    required_gates: list[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECK_GATES),
            "--status",
            str(status),
            "--require",
            *required_gates,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def make_base_status(path: Path, *, existing_gates: dict[str, Any] | None = None) -> None:
    gates: dict[str, Any] = {"existing_gate": True}
    if existing_gates:
        gates.update(existing_gates)
    write_json(
        path,
        {
            "schema_version": "test_status_v0",
            "run_id": "compute-planned-observed-candidate-proof",
            "gates": gates,
        },
    )


def extract_registry_gate_block(text: str, gate_id: str) -> str:
    lines = text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line == f"  {gate_id}:":
            start = index
            break
    assert start is not None, gate_id

    out = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            break
        out.append(line)
    return "\n".join(out)


def test_candidate_contract_files_exist() -> None:
    for path in (
        POLICY,
        REGISTRY,
        POLICY_TO_REQUIRE_ARGS,
        MATERIALIZER,
        RELATION_SCHEMA,
        RELATION_VALIDATOR,
        RELATION_EXAMPLE,
        CHECK_GATES,
        PULSE_WORKFLOW,
    ):
        assert path.is_file(), path
        assert not path.is_symlink(), path


def test_candidate_gate_identities_and_non_activation() -> None:
    assert materialize_gate_set(CANDIDATE_SET) == CANDIDATE_GATES

    for gate_set in ACTIVE_OR_BASELINE_SETS:
        materialized = materialize_gate_set(gate_set)
        leaked = [gate for gate in CANDIDATE_GATES if gate in materialized]
        assert not leaked, f"compute candidate gates leaked into {gate_set}: {leaked}"

    policy_text = POLICY.read_text(encoding="utf-8")
    assert 'version: "0.1.7"' in policy_text

    registry_text = REGISTRY.read_text(encoding="utf-8")
    for gate_id in CANDIDATE_GATES:
        assert registry_text.count(f"  {gate_id}:") == 1
        block = extract_registry_gate_block(registry_text, gate_id)
        assert "category: compute" in block
        assert "stability: experimental" in block
        assert "default_normative: false" in block

    generic_checker_source = CHECK_GATES.read_text(encoding="utf-8")
    assert CANDIDATE_SET not in generic_checker_source
    for gate_id in CANDIDATE_GATES:
        assert gate_id not in generic_checker_source


def test_materialized_candidate_passes_and_false_or_missing_fails_closed(
    tmp_path: Path,
) -> None:
    input_status = tmp_path / "status_input.json"
    output = tmp_path / "status_compute_candidate_folded.json"
    make_base_status(input_status)

    status_before = input_status.read_bytes()
    relation_before = RELATION_EXAMPLE.read_bytes()
    schema_before = RELATION_SCHEMA.read_bytes()
    validator_before = RELATION_VALIDATOR.read_bytes()

    result = run_materializer(
        status=input_status,
        relation=RELATION_EXAMPLE,
        output=output,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert result.stdout.endswith("\n")
    report = json.loads(result.stdout)
    assert report["tool"] == (
        "fold_pulsemech_compute_planned_observed_relation_into_status_v0"
    )
    assert report["version"] == "0.1.0"
    assert report["ok"] is True
    assert report["relation_validated"] is True
    assert report["output_status_written"] is True
    assert report["candidate_gate_set"] == CANDIDATE_SET
    assert report["candidate_gates"] == {
        gate_id: True for gate_id in CANDIDATE_GATES
    }
    assert report["candidate_all_true"] is True
    assert report["folded_gates"] == CANDIDATE_GATES
    assert report["errors"] == []

    folded = load_json(output)
    assert folded["gates"]["existing_gate"] is True
    for gate_id in CANDIDATE_GATES:
        assert folded["gates"][gate_id] is True

    assert report["output_status_sha256"] == sha256_file(output)
    assert input_status.read_bytes() == status_before
    assert RELATION_EXAMPLE.read_bytes() == relation_before
    assert RELATION_SCHEMA.read_bytes() == schema_before
    assert RELATION_VALIDATOR.read_bytes() == validator_before

    required_gates = materialize_gate_set(CANDIDATE_SET)
    checked = run_check_gates(output, required_gates)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "[OK] All required gates PASS" in checked.stdout

    false_status = copy.deepcopy(folded)
    false_gate = required_gates[0]
    false_status["gates"][false_gate] = False
    false_path = tmp_path / "status_candidate_false.json"
    write_json(false_path, false_status)
    false_result = run_check_gates(false_path, required_gates)
    assert false_result.returncode == 1
    assert "[X] FAIL gates:" in false_result.stdout
    assert false_gate in false_result.stdout

    missing_status = copy.deepcopy(folded)
    missing_gate = required_gates[1]
    del missing_status["gates"][missing_gate]
    missing_path = tmp_path / "status_candidate_missing.json"
    write_json(missing_path, missing_status)
    missing_result = run_check_gates(missing_path, required_gates)
    assert missing_result.returncode == 2
    assert "[X] Missing required gates:" in missing_result.stdout
    assert missing_gate in missing_result.stdout


def test_candidate_derivation_preserves_independent_failure_classes() -> None:
    base = load_json(RELATION_EXAMPLE)
    assert MATERIALIZER_MODULE.derive_candidate_gates(base) == {
        gate_id: True for gate_id in CANDIDATE_GATES
    }

    source_mismatch = copy.deepcopy(base)
    target_relation = source_mismatch["relations"][
        "relation:execute-policy-materializer"
    ]
    target_relation["relation_status"] = "source_digest_mismatch"
    target_relation["evaluation"]["source_identity"] = "mismatch"
    assert MATERIALIZER_MODULE.derive_candidate_gates(source_mismatch) == {
        "compute_transition_path_complete": True,
        "compute_transition_authority_binding_ok": False,
        "compute_transition_unbound_mutation_absent": True,
    }

    missing_execution = copy.deepcopy(base)
    missing_execution["relations"]["relation:execute-policy-materializer"][
        "relation_status"
    ] = "planned_but_not_observed"
    assert MATERIALIZER_MODULE.derive_candidate_gates(missing_execution)[
        "compute_transition_path_complete"
    ] is False

    unbound_mutation = copy.deepcopy(base)
    unbound_mutation["observations"]["observation:policy-materializer"][
        "unbound_authoritative_mutation"
    ] = True
    assert MATERIALIZER_MODULE.derive_candidate_gates(unbound_mutation)[
        "compute_transition_unbound_mutation_absent"
    ] is False


def test_invalid_relation_boundary_and_existing_gate_conflicts_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_relation = load_json(RELATION_EXAMPLE)
    invalid_relation["ok"] = False
    invalid_relation["errors"] = ["synthetic_relation_error"]
    invalid_relation["coverage"]["comparison_status"] = "partial"
    invalid_relation["coverage"]["identity_coverage_status"] = "partial"
    invalid_relation["coverage"]["unresolved_reasons"] = [
        "artifact_coverage_partial"
    ]
    invalid_relation["summary"]["comparison_complete"] = False

    with pytest.raises(MATERIALIZER_MODULE.MaterializerError) as exc_info:
        MATERIALIZER_MODULE.validate_relation_materialization_boundary(
            invalid_relation
        )
    assert "relation_not_ok" in str(exc_info.value)
    assert "relation_errors_not_empty" in str(exc_info.value)

    all_true = {gate_id: True for gate_id in CANDIDATE_GATES}
    idempotent_status = {"gates": {"existing_gate": True, **all_true}}
    MATERIALIZER_MODULE.validate_existing_gate_conflicts(
        idempotent_status,
        all_true,
    )
    folded = MATERIALIZER_MODULE.fold_candidate_gates(
        idempotent_status,
        all_true,
    )
    assert {gate_id: folded["gates"][gate_id] for gate_id in CANDIDATE_GATES} == all_true

    conflicting_status = {
        "gates": {
            "existing_gate": True,
            CANDIDATE_GATES[0]: False,
        }
    }
    with pytest.raises(
        MATERIALIZER_MODULE.MaterializerError,
        match=f"existing_gate_conflict: {CANDIDATE_GATES[0]}",
    ):
        MATERIALIZER_MODULE.validate_existing_gate_conflicts(
            conflicting_status,
            all_true,
        )

    status_path = tmp_path / "status_input.json"
    relation_path = tmp_path / "invalid_relation.json"
    output_path = tmp_path / "status_compute_candidate_folded.json"
    make_base_status(status_path)
    write_json(relation_path, invalid_relation)

    monkeypatch.setattr(
        MATERIALIZER_MODULE,
        "invoke_relation_validator",
        lambda **_kwargs: {"ok": True},
    )
    report, exit_code = MATERIALIZER_MODULE.build_and_write_folded_status(
        status_path=status_path,
        relation_path=relation_path,
        schema_path=RELATION_SCHEMA,
        validator_path=RELATION_VALIDATOR,
        output_path=output_path,
    )
    assert exit_code == 1
    assert report["ok"] is False
    assert report["relation_validated"] is True
    assert report["output_status_written"] is False
    assert not output_path.exists()


def test_deterministic_fold_and_output_boundary_guards(tmp_path: Path) -> None:
    relation = load_json(RELATION_EXAMPLE)
    candidate_gates = MATERIALIZER_MODULE.derive_candidate_gates(relation)
    base_status = {
        "schema_version": "test_status_v0",
        "run_id": "deterministic-fold",
        "gates": {"existing_gate": True},
    }

    first = MATERIALIZER_MODULE.render_json(
        MATERIALIZER_MODULE.fold_candidate_gates(base_status, candidate_gates)
    )
    second = MATERIALIZER_MODULE.render_json(
        MATERIALIZER_MODULE.fold_candidate_gates(base_status, candidate_gates)
    )
    assert first == second
    assert first.endswith("\n")

    with pytest.raises(
        MATERIALIZER_MODULE.MaterializerError,
        match="refusing_authority_or_contract_surface_output: status.json",
    ):
        MATERIALIZER_MODULE.reject_unsafe_output(
            tmp_path / "status.json",
            protected_paths=(),
        )

    protected = tmp_path / "protected.json"
    write_json(protected, {"value": True})
    with pytest.raises(
        MATERIALIZER_MODULE.MaterializerError,
        match="refusing_to_overwrite_input",
    ):
        MATERIALIZER_MODULE.reject_unsafe_output(
            protected,
            protected_paths=(protected,),
        )


def check_pulsemech_compute_planned_observed_candidate_v0() -> None:
    raise SystemExit(pytest.main([__file__, "-q"]))



# Shared full-schema runtime examples live in an already registered regression.
def _runtime_test_support():
    import importlib.util
    import hashlib
    import sys
    path = Path(__file__).with_name("test_pulsemech_compute_binding_analyzer_core_v0.py")
    name = "pulse_runtime_regression_support_" + hashlib.sha256(path.read_bytes()).hexdigest()
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _runtime_candidate(tmp_path,*,inputs=True,existing=False,tamper=False):
    m=_runtime_test_support();c=m.runtime_test_synthetic_case();r,i=m.runtime_test_relation(c,extent=True)
    if tamper:r["runtime_comparison"]["runtime_binding_sha256"]="0"*64
    status=tmp_path/"base.json";status.write_bytes(m.runtime_test_bytes({"gates":{"existing_gate":True},"metrics":{"fixture":"example"}}))
    relation=tmp_path/"runtime-relation.json";relation.write_bytes(m.runtime_test_bytes(r))
    out=tmp_path/"folded-candidate.json"
    if existing:out.write_bytes(b"owned elsewhere")
    materializer=m.runtime_test_module("fold_pulsemech_compute_planned_observed_relation_into_status_v0.py")
    before=status.read_bytes()
    result,rc=materializer.build_and_write_folded_status(status_path=status,relation_path=relation,
        schema_path=m.ROOT/"schemas/pulsemech_compute_planned_observed_relation_v0.schema.json",
        validator_path=m.ROOT/"tools/check_pulsemech_compute_planned_observed_relation_v0.py",output_path=out,
        runtime_inputs=i if inputs else None)
    assert status.read_bytes()==before
    return result,rc,out


def test_runtime_candidate_is_materialized_without_prescribing_all_true(tmp_path):
    r,rc,out=_runtime_candidate(tmp_path)
    assert rc==0 and r["relation_validated"] is True,r
    assert r["candidate_all_true"] is False
    assert out.is_file()
    folded=json.loads(out.read_bytes())
    assert folded["gates"]["existing_gate"] is True
    assert set(r["candidate_gates"])=={"compute_transition_path_complete","compute_transition_authority_binding_ok","compute_transition_unbound_mutation_absent"}
    assert all(type(v) is bool for v in r["candidate_gates"].values())


def test_runtime_candidate_without_source_inputs_is_not_published(tmp_path):
    r,rc,out=_runtime_candidate(tmp_path,inputs=False)
    assert rc!=0 and not out.exists(),r


def test_runtime_candidate_does_not_replace_existing_output(tmp_path):
    r,rc,out=_runtime_candidate(tmp_path,existing=True)
    assert rc!=0 and out.read_bytes()==b"owned elsewhere",r


def test_runtime_candidate_refuses_forged_runtime_binding(tmp_path):
    r,rc,out=_runtime_candidate(tmp_path,tamper=True)
    assert rc!=0 and not out.exists(),r



def test_runtime_exclusive_publication_never_replaces_foreign_file(tmp_path):
    m=_runtime_test_support();materializer=m.runtime_test_module("fold_pulsemech_compute_planned_observed_relation_into_status_v0.py")
    path=tmp_path/"candidate.json"
    identity=materializer.atomic_write_text(path,"first\n",exclusive=True)
    assert identity==(path.stat().st_dev,path.stat().st_ino)
    import pytest
    with pytest.raises(OSError):materializer.atomic_write_text(path,"second\n",exclusive=True)
    assert path.read_text()=="first\n"
    assert sorted(p.name for p in tmp_path.iterdir())==["candidate.json"]


def test_runtime_failed_recheck_does_not_delete_foreign_output_replacement(tmp_path,monkeypatch):
    m=_runtime_test_support();materializer=m.runtime_test_module("fold_pulsemech_compute_planned_observed_relation_into_status_v0.py")
    original=materializer.verify_regular_file_snapshots
    output=tmp_path/"folded-candidate.json"
    def recheck(snapshots):
        original(snapshots)
        if output.exists():
            # Keep the original inode alive so the replacement cannot recycle it.
            output.rename(tmp_path/"old-owned-output.json")
            output.write_bytes(b"foreign replacement")
            raise materializer.MaterializerError("synthetic_post_publication_failure")
    monkeypatch.setattr(materializer,"verify_regular_file_snapshots",recheck)
    report,rc,path=_runtime_candidate(tmp_path)
    assert rc!=0 and path.read_bytes()==b"foreign replacement",report



def _bounded_unit_module(filename):
    import importlib.util, sys, hashlib
    path=Path(__file__).resolve().parents[1]/"tools"/filename
    name="_bounded_unit_"+hashlib.sha256(path.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

def test_bounded_candidate_cannot_use_a_substitute_validator(tmp_path):
    import json
    materializer=_bounded_unit_module("fold_pulsemech_compute_planned_observed_relation_into_status_v0.py")
    status=tmp_path/"base.json";status.write_text('{"gates":{}}')
    relation=tmp_path/"relation.json";relation.write_text('{"comparison_profile":"bounded_execution_reference_v0"}')
    fake=tmp_path/"validator.py";fake.write_text('raise AssertionError("must not execute")')
    output=tmp_path/"candidate.json"
    diagnostic,code=materializer.build_and_write_folded_status(status_path=status,relation_path=relation,
        schema_path=materializer.DEFAULT_RELATION_SCHEMA,validator_path=fake,output_path=output)
    assert code!=0 and not output.exists()
    assert "bounded_relation_source_inputs_required" in str(diagnostic["errors"])




def _review_2876_fold_args(materializer, tmp_path, context_path):
    return dict(status_path=tmp_path/'status.json', relation_path=tmp_path/'relation.json',
        schema_path=materializer.DEFAULT_RELATION_SCHEMA,
        validator_path=materializer.DEFAULT_RELATION_VALIDATOR, output_path=tmp_path/'output.json',
        bounded_inputs=None, bounded_source_paths=dict(plan_path=tmp_path/'plan.json',
            report_path=tmp_path/'report.json', subject_input_path=tmp_path/'subject.json',
            carrier_path=tmp_path/'capture.zip', runtime_packet_path=tmp_path/'runtime.json',
            repository_root=materializer.ROOT, expected_context_path=context_path,
            expected_prelaunch_sha256="0"*64))


@pytest.mark.parametrize("kind", ["oversized", "symlink", "directory", "duplicate", "nonfinite", "nonobject"])
def test_review_2876_materializer_rejects_context_before_bootstrap(kind, tmp_path, monkeypatch):
    materializer = _bounded_unit_module("fold_pulsemech_compute_planned_observed_relation_into_status_v0.py")
    path = tmp_path / 'context.json'
    if kind == 'directory': path.mkdir()
    elif kind == 'symlink':
        target=tmp_path/'target.json';target.write_bytes(b'{}');path.symlink_to(target)
    else: path.write_bytes({'oversized':b'{}'+b' '*65535, 'duplicate':b'{"x":1,"x":2}',
        'nonfinite':b'{"x":NaN}', 'nonobject':b'[]'}[kind])
    calls=[]
    def forbidden(*a, **kw): calls.append(a);raise AssertionError('invalid context reached bootstrap')
    monkeypatch.setattr(materializer,'_bounded_materializer_verifier',forbidden)
    args = _review_2876_fold_args(materializer,tmp_path,path)
    diagnostic,rc = materializer.build_bounded_folded_status(**args)
    assert rc != 0 and diagnostic['ok'] is False
    assert not calls and not args['output_path'].exists(), diagnostic


def test_review_2876_materializer_forwards_single_context_capture(tmp_path, monkeypatch):
    from types import SimpleNamespace
    materializer = _bounded_unit_module("fold_pulsemech_compute_planned_observed_relation_into_status_v0.py")
    path = tmp_path/'context.json';raw=b'{ "source_commit": "'+b'a'*40+b'" }\n';path.write_bytes(raw)
    passed=[]
    def consume_inputs(**kw):
        passed.append(kw)
        assert kw.get('expected_context_bytes') == raw
        assert 'expected_context_path' not in kw
        return {'report_inputs':{'expected_context':json.loads(raw)}}
    def bootstrap(root,context):
        assert context==json.loads(raw)
        path.write_bytes(b'changed after first capture')
        return SimpleNamespace(load_reconstruction_module=lambda *a,**kw:
            SimpleNamespace(bounded_relation_inputs_from_paths=consume_inputs))
    class EndOfProbe(Exception): pass
    def stop(*a,**kw): raise EndOfProbe('end-of-admission-probe')
    monkeypatch.setattr(materializer,'_bounded_materializer_verifier',bootstrap)
    monkeypatch.setattr(materializer,'reject_unsafe_output',stop)
    args=_review_2876_fold_args(materializer,tmp_path,path)
    diagnostic,rc=materializer.build_bounded_folded_status(**args)
    assert len(passed)==1 and rc!=0,diagnostic
    assert 'end-of-admission-probe' in str(diagnostic['errors'])
    assert not args['output_path'].exists()


def test_review_2876_materializer_fifo_rejects_without_a_writer(tmp_path):
    import os
    fifo=tmp_path/'context';os.mkfifo(fifo)
    code=r"""
import importlib.util,sys
from pathlib import Path
p=Path(sys.argv[1]);s=importlib.util.spec_from_file_location('review_test',p)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
f=m._bounded_unit_module('fold_pulsemech_compute_planned_observed_relation_into_status_v0.py')
args=m._review_2876_fold_args(f,Path(sys.argv[2]).parent,Path(sys.argv[2]))
d,rc=f.build_bounded_folded_status(**args)
assert rc!=0 and d['ok'] is False and not args['output_path'].exists(),d
print('bounded-context-rejected')
"""
    p=subprocess.run([sys.executable,'-I','-B','-c',code,__file__,str(fifo)],
        stdin=subprocess.DEVNULL,capture_output=True,timeout=8,check=False)
    assert p.returncode==0,p.stderr.decode()
    assert p.stdout.strip()==b'bounded-context-rejected'


if __name__ == "__main__":
    check_pulsemech_compute_planned_observed_candidate_v0()
