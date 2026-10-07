"""Workflow, transport and source-closure regressions; no GitHub actions run."""
import copy
import io as bytesio
import json
from pathlib import Path
import struct
import sys
import urllib.error
from types import SimpleNamespace

import pytest
import yaml

from test_q2_release_intake_v0 import ROOT, IO, LOAD, metadata_request, zipped


def workflow(name):
    return yaml.load((ROOT/'.github/workflows'/name).read_bytes(),Loader=yaml.BaseLoader)


def test_two_existing_gate_steps_are_the_only_q2_credential_consumers():
    doc=workflow('pulse_ci.yml');steps=doc['jobs']['pulse']['steps']
    expected={'PULSE_Q2_INTAKE_REQUEST':'${{ github.event.inputs.q2_intake_request }}',
              'PULSE_Q2_INTAKE_REQUEST_SHA256':'${{ github.event.inputs.q2_intake_request_sha256 }}',
              'PULSE_Q2_TRANSPORT_TOKEN':'${{ github.token }}'}
    selected=('release-grade record current-run required-gate evidence',
              'release-grade build non-stubbed prod candidate status')
    assert len(doc['jobs'])==8 and sum(len(j['steps']) for j in doc['jobs'].values())==147
    assert [s['name'] for s in steps if any(k.startswith('PULSE_Q2_') for k in s.get('env',{}))]==list(selected)
    for s in steps:
        scoped={k:v for k,v in s.get('env',{}).items() if k.startswith('PULSE_Q2_')}
        assert scoped==(expected if s['name'] in selected else {})
        assert 'inputs.q2_intake_request' not in s.get('run','')
    assert doc['jobs']['pulse']['permissions']['actions']=='read'
    inputs=doc['on']['workflow_dispatch']['inputs']
    assert set(inputs)=={'strict_external_evidence','llamaguard_evidence_mode','q2_intake_request','q2_intake_request_sha256'}
    for key in ('q2_intake_request','q2_intake_request_sha256'):
        assert inputs[key]['type']=='string' and inputs[key]['required']=='false' and inputs[key]['default']==''
    setup=next(s for s in steps if s.get('uses','').startswith('actions/setup-python@'))
    assert setup['with']['python-version']=='3.11.16'
    names=[s['name'] for s in steps]
    upload=next(i for i,s in enumerate(steps) if s.get('uses','').startswith('actions/upload-artifact@')
                and 'llamaguard-current-run-' in s.get('with',{}).get('name',''))
    assert upload<names.index(selected[0])<names.index(selected[1])
    diagnostics=[s for s in steps[names.index(selected[0])+1:] if s.get('uses','').startswith('actions/upload-artifact@') and 'always()' in s.get('if','')]
    assert diagnostics


def test_reference_metadata_fields_are_data_in_both_existing_jobs():
    doc=workflow('pulsemech_compute_whole_runtime_observation_reference.yml')
    assert set(doc['jobs'])=={'acquisition','verification'}
    for field in ('q2_intake_request','q2_intake_request_sha256'):
        assert doc['on']['workflow_dispatch']['inputs'][field]['required']=='true'
        assert doc['on']['workflow_dispatch']['inputs'][field]['type']=='string'
        for job in doc['jobs'].values():
            assert job['env']['PULSE_'+field.upper()]=='${{ inputs.'+field+' }}'
            assert all('inputs.'+field not in step.get('run','') for step in job['steps'])
    assert all('PULSE_Q2_TRANSPORT_TOKEN' not in job.get('env',{}) for job in doc['jobs'].values())


def test_full_current_source_closure_and_all_candidate_pin_families_agree():
    from test_pulsemech_compute_whole_runtime_observation_v0 import BUILDER,PLAN_CHECKER,VERIFIER,CAPTURER
    candidate=IO.PACK+'tools/build_release_grade_candidate_status_v0.py'
    for module in (BUILDER,PLAN_CHECKER):
        assert len(module.SOURCE_ROLES)==60 and len(module._CURRENT_SOURCE_ROLES)==79
        assert len(module._LOCAL_R2_SOURCE_ROLES)==87 and len(module.PUBLIC_R2_SOURCE_ROLES)==92
        paths={p for _,p in module._CURRENT_SOURCE_ROLES}
        assert set(IO.SOURCE_PATHS)<=paths
        expected=module._sha1_git_blob((ROOT/candidate).read_bytes())
        assert all(pins[candidate]==expected for pins in
                   (module._RECORDED_SEMANTIC_PINS,module._FLOOR_SOURCE_PINS,module._RESIDUAL_SOURCE_PINS))
        for path,pin in module._Q2_SOURCE_PINS.items():
            assert pin==module._sha1_git_blob((ROOT/path).read_bytes())
        assert module.EXPECTED_SUBJECT_WORKFLOW_BLOB_SHA1==module._sha1_git_blob((ROOT/module.SUBJECT_WORKFLOW_PATH).read_bytes())
    assert dict(VERIFIER._D3_SOURCE_PINS)==CAPTURER._D3_SOURCE_PINS
    assert dict(VERIFIER._LOCAL_R2_RECORDED_INPUT_SOURCES)[IO.PACK+'tools/run_recorded_required_gate_evaluations_v0.py']==BUILDER._sha1_git_blob((ROOT/IO.PACK/'tools/run_recorded_required_gate_evaluations_v0.py').read_bytes())


@pytest.mark.parametrize('side',['builder','checker'])
@pytest.mark.parametrize('fault',['none','digest','source','event','selection','future-id','extra-root'])
def test_plan_projection_binds_exact_prospective_request(side,fault):
    from test_pulsemech_compute_whole_runtime_observation_v0 import BUILDER,PLAN_CHECKER
    module=BUILDER if side=='builder' else PLAN_CHECKER
    request=metadata_request();pin=None
    if fault=='source':request['evaluation_identity']['source_commit']='b'*40
    elif fault=='event':request['evaluation_identity']['event']='pull_request'
    elif fault=='selection':request['selection']['sha256']='b'*64
    elif fault=='future-id':request['evaluation_identity']['run_id']='1234'
    elif fault=='extra-root':request['command']='touch /tmp/should-never-run'
    raw=IO.encode(request);pin='0'*64 if fault=='digest' else IO.digest(raw)
    sources={path:SimpleNamespace(data=(ROOT/path).read_bytes()) for path in
             (IO.PROFILE_PATH,IO.REQUEST_SCHEMA,IO.SELECTION_PATH)}
    if fault!='none':
        with pytest.raises((module.PlanError,ValueError)):
            module._q2_request_projection(sources,'a'*40,'observed',raw.decode(),pin)
    else:
        result=module._q2_request_projection(sources,'a'*40,'observed',raw.decode(),pin)
        assert result=={'q2_intake_request':raw.decode(),'q2_intake_request_sha256':pin}


def test_tools_registration_is_161_and_does_not_expand_pytest_manifest():
    modules=['tests/test_'+n+'.py' for n in ('q2_release_intake_v0','q2_release_subject_binding_v0',
                                           'q2_required_gate_integration_v0','q2_hosted_intake_workflow_v0')]
    entries=[x.strip() for x in (ROOT/'ci/tools-tests.list').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
    assert len(entries)==len(set(entries))==161
    pytest_entries=(ROOT/'ci/pytest-tests.list').read_text().splitlines()
    assert all(entries.count(name)==1 and name not in pytest_entries for name in modules)


class Response(bytesio.BytesIO):
    status=200
    def __init__(self,raw):super().__init__(raw);self.headers={'Content-Length':str(len(raw))}


def transport_case(monkeypatch,raw=b'controlled-private-payload',location=None):
    requests=[]
    class Opener:
        def open(self,request,timeout):
            assert 0<timeout<=5;requests.append(request)
            if location is not None and len(requests)==1:
                raise urllib.error.HTTPError(request.full_url,302,'private transport exception',{'Location':location},bytesio.BytesIO())
            return Response(raw)
    monkeypatch.setattr(IO.urllib.request,'build_opener',lambda *args:Opener())
    transport=IO.GitHubArtifactTransport('PRIVATE_TRANSPORT_CREDENTIAL')
    return transport,requests,{'archive_size_bytes':len(raw),'archive_sha256':IO.digest(raw)}


def test_transport_token_is_absent_from_signed_redirect(monkeypatch,tmp_path):
    transport,requests,expected=transport_case(monkeypatch,location='https://account.blob.core.windows.net/artifact?sig=PRIVATE_SIGNED_LOCATOR')
    out=tmp_path/'capture.zip';transport.download('HKati/pulse-release-gates-0.1',11472726606,expected,out,IO.Deadline(5))
    assert len(requests)==2
    assert requests[0].get_header('Authorization')=='Bearer PRIVATE_TRANSPORT_CREDENTIAL'
    assert requests[1].get_header('Authorization') is None and requests[1].get_header('Cookie') is None
    assert IO.digest(out.read_bytes())==expected['archive_sha256'] and out.stat().st_mode & 0o777==0o600


@pytest.mark.parametrize('url',['http://a.blob.core.windows.net/x','https://evil.invalid/x',
    'https://blob.core.windows.net.evil.invalid/x','https://user:pass@a.blob.core.windows.net/x',
    'https://a.blob.core.windows.net:444/x','https://a.blob.core.windows.net/x#fragment'])
def test_transport_rejects_untrusted_redirect_without_forwarding_credentials(monkeypatch,tmp_path,url):
    transport,requests,expected=transport_case(monkeypatch,location=url)
    with pytest.raises(IO.IntakeError,match='q2_transport_rejected'):
        transport.download('HKati/pulse-release-gates-0.1',1,expected,tmp_path/'capture.zip',IO.Deadline(5))
    assert len(requests)==1


@pytest.mark.parametrize('fault',['short','long','digest','wrong-repository','bool-artifact'])
def test_transport_input_identity_and_stream_bounds(monkeypatch,tmp_path,fault):
    transport,requests,expected=transport_case(monkeypatch)
    repository='HKati/pulse-release-gates-0.1';identifier=1
    if fault=='short':expected['archive_size_bytes']+=1
    elif fault=='long':expected['archive_size_bytes']-=1
    elif fault=='digest':expected['archive_sha256']='0'*64
    elif fault=='wrong-repository':repository='other/repo'
    else:identifier=True
    with pytest.raises(IO.IntakeError):transport.download(repository,identifier,expected,tmp_path/'out',IO.Deadline(5))


def test_archive_member_count_is_bounded_before_central_directory_parse(tmp_path,monkeypatch):
    path=tmp_path/'crafted.zip';zipped(path,{'a':(b'a',0o100644)})
    raw=bytearray(path.read_bytes());struct.pack_into('<HH',raw,len(raw)-22+8,65534,65534);path.write_bytes(raw)
    monkeypatch.setattr(IO.zipfile,'ZipFile',lambda *a,**k:pytest.fail('Unbounded directory must be rejected before parsing'))
    with pytest.raises(IO.IntakeError,match='q2_archive_limit'):
        IO.Archive(path,maximum_bytes=1000,max_members=2,member_bytes=100,expanded_bytes=200,deadline=IO.Deadline(2))


def test_held_archive_digest_must_match_actual_opened_bytes(tmp_path):
    path=tmp_path/'data.zip';zipped(path,{'a':(b'a',0o100644)})
    with pytest.raises(IO.IntakeError,match='q2_digest_mismatch'):
        IO.Archive(path,maximum_bytes=1000,max_members=2,member_bytes=100,expanded_bytes=200,
                   deadline=IO.Deadline(2),expected_sha256='0'*64)


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__,'-q']))
