"""Offline Q3 contract regressions. No subject inference or native service."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import pytest
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'PULSE_safe_pack_v0/tools'
def module(name):
    spec=importlib.util.spec_from_file_location(name,TOOLS/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
C=module('q3_native_capture_contract_v0')

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def reject(*a,**k):raise AssertionError('offline test attempted network')
    monkeypatch.setattr(socket,'create_connection',reject)
    monkeypatch.setattr(socket.socket,'connect',reject)


def request(mode='token-preflight'):
    p=C.load_profile(ROOT)
    return {'record_type':'q3_native_capture_request_v0','mode':mode,'repository':C.REPOSITORY,
            'source_commit':'a'*40,'profile_sha256':C.PROFILE_SHA256,
            'task_file_sha256':p['fixed_inputs'][C.FRAME+'TASKS_DRAFT.jsonl'],
            'authorization':C.AUTHORIZATIONS[mode], 'approved_token_map_sha256':'b'*64 if mode=='capture' else None,
            'limits':copy.deepcopy(p['limits']),'claims':dict(C.CLAIMS),'new_spend_authorized':0}

@pytest.mark.parametrize('mode',['token-preflight','capture'])
def test_closed_request_and_schema_positive(mode):
    p=C.load_profile(ROOT);r=request(mode)
    assert C.validate_request(C.encode(r),p)==r
    schema=json.loads((ROOT/'schemas/metrics/q3_native_capture_request_v0.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(r)

@pytest.mark.parametrize('fault',['extra','mode','auth','commit','profile','frame','repo','bool_spend','spend',
                                 'capture_no_anchor','preflight_anchor','retry','attempts','tokens','claim','claim_bool','limit_bool','retention'])
def test_request_mutations_fail_closed(fault):
    r=request();p=C.load_profile(ROOT)
    if fault=='extra':r['command']='run-anything'
    elif fault=='mode':r['mode']='generic'
    elif fault=='auth':r['authorization']=''
    elif fault=='commit':r['source_commit']='main'
    elif fault=='profile':r['profile_sha256']='0'*64
    elif fault=='frame':r['task_file_sha256']='0'*64
    elif fault=='repo':r['repository']='other/repo'
    elif fault=='bool_spend':r['new_spend_authorized']=False
    elif fault=='spend':r['new_spend_authorized']=1
    elif fault=='capture_no_anchor':r=request('capture');r['approved_token_map_sha256']=None
    elif fault=='preflight_anchor':r['approved_token_map_sha256']='b'*64
    elif fault=='retry':r['limits']['automatic_retries']=1
    elif fault=='attempts':r['limits']['max_attempts']=205
    elif fault=='tokens':r['limits']['max_new_tokens']=512
    elif fault=='claim':r['claims']['authority_effect']='allow'
    elif fault=='claim_bool':r['claims']['production_gate_eligible']=0
    elif fault=='limit_bool':r['limits']['automatic_retries']=False
    elif fault=='retention':r['limits']['actions_retention_days']=90
    with pytest.raises(ValueError):C.validate_request(C.encode(r),p)

@pytest.mark.parametrize('raw',[b'',b'\xef\xbb\xbf{}',b'{"a":1,"a":2}',b'{"v":NaN}',b'{"v":Infinity}',
                               b'{"v":1e999}',b'{"v":"\\ud800"}',b'\xff',b'{',b'[] trailing',b'['*70+b'0'+b']'*70])
def test_strict_json_rejection(raw):
    with pytest.raises(ValueError):C.strict_json(raw)

@pytest.mark.parametrize('value',[True,False,1.0,'1',None,-1,205])
def test_integer_bounds_are_not_truthiness(value):
    with pytest.raises(ValueError):C.integer(value,0,204)

@pytest.mark.parametrize('name',['../x','/x','a/../b','a//b','a/./b','a\\b','a\x00b','a:b',''])
def test_paths_closed(name):
    with pytest.raises(ValueError):C.relative(name)


def test_exact_204_frame_and_byte_counts():
    frame=C.task_frame(ROOT,C.load_profile(ROOT))
    assert len(frame)==len({x['task_id'] for x in frame})==204
    assert sum(x['task_form']=='contract_lookup' for x in frame)==102
    assert max(len(x['logical_request_text'].encode()) for x in frame)==3855
    assert len({x['context'] for x in frame})==12
    assert all(len(x['messages'])==2 and x['messages'][1]['content']==x['logical_request_text'] for x in frame)


def test_held_sources_survive_directory_removal(tmp_path):
    p=C.load_profile(ROOT);held={name:C.safe_read(ROOT/name) for name in p['source_files']}
    assert C.task_frame(held,p)==C.task_frame(ROOT,p)
    held[C.FRAME+'TASKS_DRAFT.jsonl']+=b'\n'
    with pytest.raises(ValueError):C.task_frame(held,p)

@pytest.mark.parametrize('kind',['symlink','parent_symlink','hardlink','directory','fifo','oversize'])
def test_safe_read_rejects_unsafe_inputs(tmp_path,kind):
    p=tmp_path/'source';p.write_bytes(b'payload')
    if kind=='symlink':q=tmp_path/'q';q.symlink_to(p);p=q
    elif kind=='parent_symlink':d=tmp_path/'d';d.mkdir();(d/'a').write_bytes(b'x');q=tmp_path/'q';q.symlink_to(d);p=q/'a'
    elif kind=='hardlink':os.link(p,tmp_path/'alias')
    elif kind=='directory':p=tmp_path
    elif kind=='fifo':p.unlink();os.mkfifo(p)
    with pytest.raises((ValueError,OSError)):C.safe_read(p,2 if kind=='oversize' else 100)

@pytest.mark.parametrize('mask',[0o000,0o022,0o077,0o200,0o700,0o777])
def test_new_output_restores_exact_mode_without_changing_umask(tmp_path,mask):
    old=os.umask(mask)
    try:
        path=tmp_path/'out';C.write_new(path,b'hello')
        actual=os.umask(mask);assert actual==mask
        assert path.stat().st_mode&0o777==0o600
        assert path.read_bytes()==b'hello'
    finally:os.umask(old)

@pytest.mark.parametrize('failure',['write','zero_write','fsync'])
def test_partial_write_cleanup_and_retry(tmp_path,monkeypatch,failure):
    path=tmp_path/'out'
    with monkeypatch.context() as m:
        if failure=='zero_write':m.setattr(C.os,'write',lambda *a:0)
        elif failure=='write':m.setattr(C.os,'write',lambda *a:(_ for _ in ()).throw(OSError('synthetic')))
        else:m.setattr(C.os,'fsync',lambda *a:(_ for _ in ()).throw(OSError('synthetic')))
        with pytest.raises((ValueError,OSError)):C.write_new(path,b'payload')
    assert not path.exists()
    C.write_new(path,b'retry');assert path.read_bytes()==b'retry'


def test_existing_destination_not_replaced(tmp_path):
    p=tmp_path/'x';p.write_bytes(b'original')
    with pytest.raises(FileExistsError):C.write_new(p,b'new')
    assert p.read_bytes()==b'original'


def test_request_claims_are_detached():
    first=request();first['claims']['authority_effect']='allow'
    assert request()['claims']['authority_effect']=='none'
    assert C.CLAIMS['authority_effect']=='none'


def test_request_constructor_with_actual_offline_git_fixture(tmp_path):
    p=C.load_profile(ROOT)
    for n in p['source_files']:
        dest=tmp_path/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/n).read_bytes())
    env={'PATH':os.defpath,'HOME':str(tmp_path),'GIT_AUTHOR_NAME':'Synthetic Fixture',
         'GIT_AUTHOR_EMAIL':'fixture@example.invalid','GIT_COMMITTER_NAME':'Synthetic Fixture',
         'GIT_COMMITTER_EMAIL':'fixture@example.invalid'}
    def git(*args):return subprocess.run(['/usr/bin/git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','-C',str(tmp_path),*args],env=env,check=True,capture_output=True).stdout
    git('init','-q');git('add','.');git('commit','-qm','Synthetic local fixture; no remote or project commit')
    commit=git('rev-parse','HEAD').decode().strip()
    raw=C.make_request(tmp_path,commit,'token-preflight',C.AUTHORIZATIONS['token-preflight'])
    assert C.validate_request(raw,p)['source_commit']==commit
    target=tmp_path/p['source_files'][0];target.write_bytes(target.read_bytes()+b'\n')
    with pytest.raises(ValueError):C.make_request(tmp_path,commit,'token-preflight',C.AUTHORIZATIONS['token-preflight'])
