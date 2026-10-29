#!/usr/bin/env python3
"""Q2 tokenizer manual workflow, classification and closed scope regressions."""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "PULSE_safe_pack_v0/tools"))
import check_q2_release_host_tokenizer_v0 as C


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def workflow():
    return yaml.load((ROOT / C.WORKFLOW).read_text(), Loader=yaml.BaseLoader)


def test_manual_one_job_owner_source_attempt_and_permissions():
    doc = workflow()
    assert doc['name'] == 'Q2 native release-host tokenizer verification v0'
    assert set(doc['on']) == {'workflow_dispatch'}
    assert set(doc['on']['workflow_dispatch']['inputs']) == {'source_commit','native_request','native_request_sha256'}
    assert all(row == {'description':row['description'],'required':'true','type':'string'}
               for row in doc['on']['workflow_dispatch']['inputs'].values())
    assert doc['permissions'] == {'contents':'read','actions':'read'}
    assert doc['concurrency']['cancel-in-progress'] == 'false'
    assert set(doc['jobs']) == {'verify_host'}
    job = doc['jobs']['verify_host']
    assert job['runs-on'] == 'ubuntu-24.04' and job['timeout-minutes'] == '30'
    guard = job['steps'][0]['run']
    for token in ('GITHUB_EVENT_NAME','workflow_dispatch','GITHUB_REF','refs/heads/main','GITHUB_ACTOR','HKati',
                  'GITHUB_ACTOR_ID','128643840','GITHUB_TRIGGERING_ACTOR','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_WORKFLOW_SHA'):
        assert token in guard
    assert not any(k in doc['on'] for k in ('push','pull_request','schedule','workflow_run'))


def test_exact_pinned_actions_and_one_setup_step():
    steps = workflow()['jobs']['verify_host']['steps']
    assert [s['uses'] for s in steps if 'uses' in s] == [
        'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1',
        'actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97',
        'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9']
    assert steps[1]['with'] == {'ref':'${{ github.sha }}','persist-credentials':'false'}
    assert steps[2]['with'] == {'python-version':'3.11.16'}
    assert steps[-1]['if'] == 'always()' and steps[-1]['with']['overwrite'] == 'false'
    assert steps[-1]['with']['path'] == '${{ runner.temp }}/q2-native-tokenizer/*.json'
    assert not any(s.get('with',{}).get('archive') == 'false' for s in steps)


def test_no_credential_interpolation_or_model_authority_call():
    steps = workflow()['jobs']['verify_host']['steps']
    runs = '\n'.join(s.get('run','') for s in steps)
    assert '${{' not in runs
    for forbidden in ('run_q2_reference_subject_v0.py','--mode capture-reference','model.generate',
                      'AutoModelForCausalLM','actions/attest@','release_decision','materialize_release','id-token: write'):
        assert forbidden not in (ROOT / C.WORKFLOW).read_text()
    assert steps[3]['env'] == {'PULSE_Q2_TOKENIZER_TOKEN':'${{ github.token }}'}
    assert 'env -i' not in runs  # sudo preserves only the explicit allowlist; service env is independently cleared.
    assert '-I -B PULSE_safe_pack_v0/tools/verify_q2_release_host_tokenizer_v0.py' in runs
    assert 'PULSE_Q2_TOKENIZER_TOKEN' not in steps[-1]['with']['path']


def test_fixed_profile_source_and_scope_contracts():
    p = C.load_profile(ROOT)
    assert p['source_paths'] == list(C.SOURCE_PATHS)
    assert p['claims'] == C.CLAIMS and all(p['claims'][k] is False for k in (
        'model_weights_loaded','worker_launch_executed','full_release_host_verified','production_gate_eligible',
        'active_gate_eligible','same_run_release_authority_eligible'))
    assert p['claims']['current_inference_count'] == 0
    assert p['historical_metrics']['groups_eligible'] == 49
    assert p['inputs']['capsule']['artifact_id'] == 11686701538
    assert p['inputs']['roundtrip']['artifact_id'] == 11686476032
    assert p['interpreter_entries'] == ['runtime/bin/python','runtime/bin/python3','runtime/bin/python3.11']
    assert [r['expected_exit'] for r in p['occurrences']] == [0,0,1,0]
    assert all(r['maximum_seconds'] == 180 for r in p['occurrences'])
    assert p['limits'] == {'phase_seconds':1200,'cleanup_grace_seconds':180,'job_minutes':30,'minimum_free_bytes':8589934592}


def test_no_model_loader_generation_or_legacy_relocated_capture_entry():
    for filename in (C.SELF, C.SUPERVISOR):
        tree = ast.parse((ROOT / filename).read_text())
        forbidden = {'qualify','capture','capture_verified_inputs','verify_installation','run_capture','capture_session','generate'}
        calls = {n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id
                 for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Attribute,ast.Name))}
        assert not calls & forbidden
    checker = ast.parse((ROOT / C.SELF).read_text())
    imports = {n.module for n in ast.walk(checker) if isinstance(n,ast.ImportFrom)}
    assert 'verify_q2_release_host_tokenizer_v0' not in imports


def test_two_tools_tests_exactly_once_and_all_count_consumers():
    entries = [line.strip() for line in (ROOT / 'ci/tools-tests.list').read_text().splitlines()
               if line.strip() and not line.startswith('#')]
    assert len(entries) == len(set(entries)) == 170
    for name in ('tests/test_q2_release_host_tokenizer_v0.py','tests/test_q2_release_host_tokenizer_workflow_v0.py'):
        assert entries.count(name) == 1
        assert name not in (ROOT / 'ci/pytest-tests.list').read_text()
        assert 'pytest.main([__file__])' in (ROOT / name).read_text()
    for name in ('test_q2_reference_acquisition_v0.py','test_q2_hosted_intake_workflow_v0.py',
                 'test_pulsemech_compute_bounded_execution_v0.py','test_pulsemech_compute_current_run_export_candidate_workflow_v0.py',
                 'test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py'):
        assert len(re.findall(r'==\s*170\b',(ROOT / 'tests' / name).read_text())) == 1


@pytest.fixture(scope='module')
def acquisition():
    return module('q2_tokenizer_hygiene_fixtures',ROOT / 'tests/test_q2_reference_acquisition_v0.py')


def test_actual_hygiene_guard_accepts_exact_workflow(acquisition, tmp_path):
    result = acquisition._run_hygiene_python_sync(tmp_path,q2_text=acquisition._q2_workflow_text())
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('fault',['wrong_patch','floating','wrong_job','duplicate_setup','other_job_patch','missing_setup'])
def test_actual_hygiene_guard_rejects_scoped_pin_changes(acquisition, tmp_path, fault):
    doc = workflow();job=doc['jobs']['verify_host'];setup=job['steps'][2]
    if fault == 'wrong_patch': setup['with']['python-version']='3.11.17'
    elif fault == 'floating': setup['with']['python-version']='3.11'
    elif fault == 'wrong_job': doc['jobs']['other']=doc['jobs'].pop('verify_host')
    elif fault == 'duplicate_setup': job['steps'].append(copy.deepcopy(setup))
    elif fault == 'other_job_patch': doc['jobs']['other']={'steps':[copy.deepcopy(setup)]}
    else: job['steps'].remove(setup)
    result = acquisition._run_hygiene_python_sync(tmp_path,q2_text=acquisition._q2_workflow_text(),
        extra_workflows={Path(C.WORKFLOW).name:yaml.safe_dump(doc)})
    assert result.returncode == 1, result.stdout + result.stderr


def test_classifier_exact_workflow_and_tools_non_authorizing(tmp_path):
    classifier=module('q2_tokenizer_classifier',ROOT / 'scripts/build_normative_shadow_inventory_v0.py')
    item=classifier.classify_workflow(ROOT / C.WORKFLOW,repo_root=ROOT)
    assert item['authority_impacting']=='no' and item['carrier_class']=='audit_preservation'
    assert item['required_gate_participation'] is False and item['attestation_participation'] is False
    assert item['release_path_participation'] is False
    tools={r['path']:r for r in classifier.static_authority_entries(ROOT)}
    assert all(tools[n]['authority_impacting']=='no' for n in (C.SELF,C.SUPERVISOR))


@pytest.mark.parametrize('fault',['renamed','wrong_name','attestation','authority_file','gate_policy'])
def test_classifier_no_generic_tokenizer_or_authority_exemption(tmp_path, fault):
    classifier=module('q2_tokenizer_classifier_negative',ROOT / 'scripts/build_normative_shadow_inventory_v0.py')
    path=tmp_path / C.WORKFLOW;path.parent.mkdir(parents=True)
    text=(ROOT / C.WORKFLOW).read_text()
    if fault=='renamed': path=path.with_name('another_tokenizer.yml')
    elif fault=='wrong_name': text=text.replace('name: Q2 native release-host tokenizer verification v0','name: Other')
    elif fault=='attestation': text+='\n# actions/attest@unexpected\n'
    elif fault=='authority_file': text+='\n# materialize_release_decision\n'
    else: text+='\n# pulse_gate_policy\n'
    path.write_text(text)
    item=classifier.classify_workflow(path,repo_root=tmp_path)
    assert item['primary_role']!='non-authorizing Q2 native tokenizer verification workflow'


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
