"""Offline wiring, real hygiene guard and authority-classifier tests. No dispatch."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import pytest
import yaml
from test_q3_native_capture_contract_v0 import ROOT, TOOLS, C, module, request, offline
A=module('acquire_q3_reference_inputs_v0')
WF=C.WORKFLOW


def workflow():return yaml.load((ROOT/WF).read_bytes(),Loader=yaml.BaseLoader)

def classifier():
    spec=importlib.util.spec_from_file_location('q3_inventory_test',ROOT/'scripts/build_normative_shadow_inventory_v0.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def test_exact_manual_owner_scoped_workflow():
    d=workflow();assert set(d['on'])=={'workflow_dispatch'}
    assert set(d['jobs'])=={'acquire'} and d['permissions']=={'contents':'read'}
    j=d['jobs']['acquire'];assert j['permissions']=={'contents':'read','actions':'read'}
    assert j['runs-on']=='ubuntu-24.04' and j['timeout-minutes']=='270'
    assert d['concurrency']['cancel-in-progress']=='false'
    first=j['steps'][0]['run']
    for text in ['GITHUB_ACTOR','GITHUB_TRIGGERING_ACTOR','GITHUB_RUN_ATTEMPT','GITHUB_WORKFLOW_SHA','GITHUB_SHA','refs/heads/main','HKati']:assert text in first
    for step in j['steps']:
        if 'uses' in step:assert re.fullmatch(r'[^@]+@[0-9a-f]{40}',step['uses'])
    python=[s for s in j['steps'] if s.get('uses','').startswith('actions/setup-python@')]
    assert len(python)==1 and python[0]['with']['python-version']=='3.11.16'
    assert set(d['on']['workflow_dispatch']['inputs'])=={'source_commit','native_request','native_request_sha256'}


def test_workflow_cannot_publish_workspace_models_or_hidden_logs():
    text=(ROOT/WF).read_text();d=workflow()
    up=[s for s in d['jobs']['acquire']['steps'] if s.get('uses','').startswith('actions/upload-artifact@')]
    assert len(up)==1 and 'always()' in up[0]['if']
    assert up[0]['with']['retention-days']=='30' and up[0]['with']['overwrite']=='false'
    assert [x.rsplit('/',1)[-1] for x in up[0]['with']['path'].splitlines()]==['evidence.zip','receipt.json','failure.json']
    for forbidden in ['contents: write','id-token: write','actions: write','git push','gh pr','secrets.','pull_request_target']:
        assert forbidden not in text
    assert 'build_q3_reference_summary.py' not in text and 'build_q2_reference_summary.py' not in text
    assert 'timeout --signal=TERM --kill-after=180s 15480s' in text


def guard_script():
    d=yaml.safe_load((ROOT/'.github/workflows/repo_hygiene.yml').read_text())
    s=next(x['run'] for x in d['jobs']['hygiene_guardrails']['steps'] if x.get('name','').startswith('Repo hygiene: enforce Python version sync'))
    return s.split("python3 - <<'PY'\n",1)[1].rsplit('\nPY',1)[0]+'\n'


def guard_run(tmp_path,fault=None):
    (tmp_path/'.github/workflows').mkdir(parents=True)
    (tmp_path/'environment.yml').write_text('dependencies: [python=3.11]\n')
    names=['q2_reference_acquisition_v0.yml','pulse_ci.yml','q2_release_capsule_publication_v0.yml',
           'q2_release_host_tokenizer_verification_v0.yml','q2_release_host_worker_verification_v0.yml',
           'q3_reference_acquisition_v0.yml','paradox_compatibility_v0.yml']
    for n in names:(tmp_path/'.github/workflows'/n).write_bytes((ROOT/'.github/workflows'/n).read_bytes())
    path=tmp_path/WF;d=workflow();j=d['jobs']['acquire'];steps=j['steps']
    setup=next(x for x in steps if x.get('uses','').startswith('actions/setup-python@'))
    if fault=='patch':setup['with']['python-version']='3.11.15'
    elif fault=='floating':setup['with']['python-version']='3.11'
    elif fault=='duplicate':steps.append(copy.deepcopy(setup))
    elif fault=='missing_setup':steps.remove(setup)
    elif fault=='wrong_job':d['jobs']['other']=d['jobs'].pop('acquire')
    elif fault=='other_job':d['jobs']['other']={'steps':[copy.deepcopy(setup)]}
    elif fault=='dynamic':setup['with']['python-version']='${{ inputs.version }}'
    path.write_text(yaml.safe_dump(d,sort_keys=False))
    if fault=='missing_workflow':path.unlink()
    elif fault=='symlink':path.rename(path.with_suffix('.saved'));path.symlink_to(path.with_suffix('.saved'))
    return subprocess.run([sys.executable,'-I','-B','-c',guard_script()],cwd=tmp_path,capture_output=True,text=True,timeout=10)


def test_actual_guard_accepts_q3_q2_and_paradox_together(tmp_path):
    p=guard_run(tmp_path);assert p.returncode==0,p.stdout+p.stderr

@pytest.mark.parametrize('fault',['patch','floating','duplicate','missing_setup','wrong_job','other_job','dynamic','missing_workflow','symlink'])
def test_actual_guard_rejects_out_of_scope_python_changes(tmp_path,fault):
    p=guard_run(tmp_path,fault);assert p.returncode==1,p.stdout+p.stderr
    assert '::error' in p.stdout and 'Traceback' not in p.stderr


def test_exact_classifier_non_authority():
    out=classifier().classify_workflow(ROOT/WF,repo_root=ROOT)
    assert out['authority_impacting']=='no' and out['carrier_class']=='audit_preservation'
    assert all(out[x] is False for x in ['required_gate_participation','attestation_participation','release_path_participation'])

@pytest.mark.parametrize('fault',['newline','permission','trigger','retention','name','python'])
def test_classifier_does_not_grant_name_based_exemption(tmp_path,fault):
    text=(ROOT/WF).read_text()
    if fault=='newline':text+='\n'
    elif fault=='permission':text=text.replace('contents: read','contents: write')
    elif fault=='trigger':text=text.replace('workflow_dispatch:','push:')
    elif fault=='retention':text=text.replace('retention-days: 30','retention-days: 90')
    elif fault=='name':text=text.replace('Q3 native token preflight and capture v0','Renamed Q3')
    elif fault=='python':text=text.replace('3.11.16','3.11.15')
    path=tmp_path/WF;path.parent.mkdir(parents=True);path.write_text(text)
    out=classifier().classify_workflow(path,repo_root=tmp_path)
    assert out['authority_impacting']=='conditional'


def test_all_four_programs_registered_once_tools_manifest_unchanged():
    entries=[x.strip() for x in (ROOT/'ci/pytest-tests.list').read_text().splitlines() if x.strip() and not x.startswith('#')]
    for suffix in ['contract_','protocol_','','workflow_']:
        name='tests/test_q3_native_capture_'+suffix+'v0.py'
        assert entries.count(name)==1 and (ROOT/name).is_file()
    tools=[x.strip() for x in (ROOT/'ci/tools-tests.list').read_text().splitlines() if x.strip() and not x.startswith('#')]
    assert len(tools)==len(set(tools))==169
    assert not [x for x in tools if 'q3_native_capture' in x]


def test_protected_q2_and_existing_q3_not_imported_or_called():
    text='\n'.join((TOOLS/n).read_text() for n in ['q3_native_capture_contract_v0.py','q3_native_runtime_v0.py',
        'run_q3_reference_subject_v0.py','acquire_q3_reference_inputs_v0.py','check_q3_native_capture_v0.py'])
    for name in ['build_q3_reference_summary.py','check_q3_reference_summary.py','prepare_q3_archived_input_bundle_v0.py',
                 'acquire_q2_reference_inputs_v0.py','run_q2_reference_subject_v0.py']:
        assert name not in text

@pytest.mark.parametrize('fault',['repo','event','ref','actor','triggering','attempt','source','workflow_source','run'])
def test_entry_guard_wrong_control_context_before_import_or_network(tmp_path,monkeypatch,fault):
    env={'GITHUB_REPOSITORY':C.REPOSITORY,'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main',
         'GITHUB_ACTOR':'HKati','GITHUB_TRIGGERING_ACTOR':'HKati','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40,
         'GITHUB_WORKFLOW_SHA':'a'*40,'GITHUB_WORKFLOW_REF':C.REPOSITORY+'/'+WF+'@refs/heads/main','GITHUB_RUN_ID':'12345'}
    key,value={'repo':('GITHUB_REPOSITORY','other/repo'),'event':('GITHUB_EVENT_NAME','push'),
        'ref':('GITHUB_REF','refs/heads/other'),'actor':('GITHUB_ACTOR','other'),'triggering':('GITHUB_TRIGGERING_ACTOR','other'),
        'attempt':('GITHUB_RUN_ATTEMPT','2'),'source':('GITHUB_SHA','b'*40),'workflow_source':('GITHUB_WORKFLOW_SHA','b'*40),
        'run':('GITHUB_RUN_ID','0')}[fault]
    env[key]=value
    # Supply only mocked process identity so this reaches the actual context guard.
    monkeypatch.setattr(A.os,'geteuid',lambda:0)
    monkeypatch.setattr(A.sys,'flags',type('Flags',(),{'isolated':1})())
    monkeypatch.setattr(A,'boot_git',lambda *a,**k:pytest.fail('git before context rejection'))
    with pytest.raises(ValueError):A.entry_guard(tmp_path,'a'*40,b'{}',C.digest(b'{}'),env)


def test_request_constructor_cannot_dispatch_or_generate():
    tree=__import__('ast').parse((TOOLS/'q3_native_capture_contract_v0.py').read_text())
    assert not any(isinstance(n,__import__('ast').Attribute) and n.attr in ['generate','urlopen','dispatch'] for n in __import__('ast').walk(tree))
