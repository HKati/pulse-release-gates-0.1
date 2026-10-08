import copy
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_gravity_record_protocol_decodability_wall_v0_2 as wall


def bundle():
    return json.loads((ROOT / 'out/gravity_record_protocol_inputs_v0_1.json').read_text())


def run(tmp_path, data=None, h_req=0.99, margin=0.0, requirement_id='TEST:synthetic-rate-0.99', log_base='log2'):
    src = tmp_path / 'inputs.json'
    dst = tmp_path / 'wall.json'
    src.write_text(json.dumps(bundle() if data is None else data))
    code = wall.build_artifact(str(src), str(dst), None, 2, log_base, margin, True, h_req, requirement_id)
    return code, json.loads(dst.read_text())


def test_explicit_threshold_and_lambda_independence(tmp_path):
    code, original = run(tmp_path)
    assert code == 0
    assert original['cases'][0]['r_c'] == pytest.approx(0.5)
    data = bundle()
    for p in data['cases'][0]['profiles']['lambda']['points']:
        p['value'] = 12.0
    code, changed = run(tmp_path, data)
    assert code == 0
    assert original['cases'] == changed['cases']
    assert original['source_inputs']['sha256'] != changed['source_inputs']['sha256']


def test_requirement_changes_threshold(tmp_path):
    _, result = run(tmp_path, h_req=0.985)
    assert result['cases'][0]['r_c'] == pytest.approx(0.75)


@pytest.mark.parametrize('h_req,expected', [(0.1,'no_wall_in_range'),(2.0,'always_not_decodable')])
def test_requirement_outside_observed_capacity(tmp_path,h_req,expected):
    code, result = run(tmp_path,h_req=h_req)
    assert code == 0
    assert result['cases'][0]['wall_state'] == expected


@pytest.mark.parametrize('kwargs', [dict(h_req=-1),dict(h_req=float('nan')),dict(h_req=True),dict(margin=float('inf')),dict(margin=-1),dict(requirement_id=' '),dict(log_base='bad')])
def test_invalid_configuration(tmp_path,kwargs):
    code, result = run(tmp_path,**kwargs)
    assert code == 2
    assert result['errors']
    assert not result['cases']


@pytest.mark.parametrize('mutation', ['missing','fail','duplicate','range','label','raw_errors'])
def test_unusable_evidence(tmp_path,mutation):
    data=bundle(); kap=data['cases'][0]['profiles']['kappa']
    if mutation=='missing': kap.clear();kap.update(status='MISSING',points=None)
    elif mutation=='fail': kap['status']='FAIL'
    elif mutation=='duplicate': kap['points'].append(copy.deepcopy(kap['points'][0]))
    elif mutation=='range': kap['points'][0]['value']=1.1
    elif mutation=='label': kap['points'][0]['r']='unbound-label'
    else: data['raw_errors']=['unresolved acquisition error']
    code, result=run(tmp_path,data)
    assert code==2
    assert result['errors']


def test_bits_nats_equivalence(tmp_path):
    _, bits=run(tmp_path)
    _, nats=run(tmp_path,h_req=0.99*math.log(2),log_base='ln')
    assert bits['cases'][0]['r_c']==pytest.approx(nats['cases'][0]['r_c'])


def test_cli_requires_requirement(tmp_path):
    process=subprocess.run([sys.executable,str(ROOT/'scripts/build_gravity_record_protocol_decodability_wall_v0_2.py'),'--in',str(ROOT/'out/gravity_record_protocol_inputs_v0_1.json'),'--out',str(tmp_path/'wall.json'),'--alphabet-size','2'],capture_output=True,text=True)
    assert process.returncode==2
    assert '--h-req' in process.stderr


def test_contract_and_legacy_rejection(tmp_path):
    run(tmp_path)
    checker=ROOT/'scripts/check_gravity_record_protocol_decodability_wall_v0_2_contract.py'
    path=tmp_path/'wall.json'
    assert subprocess.run([sys.executable,str(checker),'--in',str(path)],capture_output=True).returncode==0
    old=ROOT/'PULSE_safe_pack_v0/fixtures/decodability_wall_v0_1.demo.json'
    assert subprocess.run([sys.executable,str(checker),'--in',str(old)],capture_output=True).returncode==2
    obj=json.loads(path.read_text());obj['config']['units']='nats_per_tick';path.write_text(json.dumps(obj))
    assert subprocess.run([sys.executable,str(checker),'--in',str(path)],capture_output=True).returncode==2


def test_multiple_crossings():
    case={'case_id':'test','profiles':{'kappa':{'points':[{'r':i,'value':v} for i,v in enumerate([1,.4,1,.4])]}}}
    result=wall.build_case(case,1,0,.5)
    assert result['wall_state']=='non_monotone_warning'
    assert result['diagnostics']['crossings']==3


def test_missing_lambda_does_not_become_requirement(tmp_path):
    data=bundle()
    data['cases'][0]['profiles']['lambda']={'status':'MISSING','points':None}
    code,result=run(tmp_path,data)
    assert code==0
    assert result['cases'][0]['r_c']==pytest.approx(0.5)


def test_committed_fixture_replay(tmp_path):
    _,result=run(tmp_path)
    fixture=json.loads((ROOT/'PULSE_safe_pack_v0/fixtures/decodability_wall_v0_2.demo.json').read_text())
    assert result['cases']==fixture['cases']
    assert result['config']==fixture['config']


def test_one_point_does_not_claim_wall(tmp_path):
    data=bundle()
    data['cases'][0]['profiles']['kappa']['points'].pop()
    code,result=run(tmp_path,data)
    assert code==0
    assert result['cases'][0]['wall_state']=='insufficient_points'
    assert result['cases'][0]['r_c'] is None
