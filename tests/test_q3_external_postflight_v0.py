#!/usr/bin/env python3
"""Offline postflight comparisons; mutated observations are synthetic, not runs."""
from __future__ import annotations
import ast
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/check_q3_external_postflight_v0.py'
spec = importlib.util.spec_from_file_location('external_postflight_test', TOOL)
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
PRESERVED = ROOT / ('preservation/q3_token_preflight_v0/run_40253690074_attempt_1/'
                    'Q3_TOKEN_PREFLIGHT_RECONCILIATION_40253690074.zip')
PRESERVED_SHA256 = '0a91f36c1e7e738b27ab29a5428e3243a31e9840a4907f01dceabaccceca0c4e'
TEST_PATH = 'tests/test_q3_external_postflight_v0.py'


def archive(items):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, value in items.items():
            z.writestr(name, value)
    return output.getvalue()


@pytest.fixture(scope='module')
def historical():
    package = PRESERVED.read_bytes()
    assert hashlib.sha256(package).hexdigest() == PRESERVED_SHA256
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        raw = {
            'artifact.zip': z.read('original/q3-reference-capture-40253690074-1.zip'),
            'run.json': z.read('evidence/run_metadata.json'),
            'jobs.json': z.read('evidence/jobs_metadata.json'),
            'artifact.json': z.read('evidence/artifact_metadata.json'),
            'job.log': z.read('evidence/workflow_job_121350855532.log'),
        }
    outer = M.unzip(raw['artifact.zip']); inner = M.unzip(outer['evidence.zip'])
    source = {n[7:]: b for n, b in inner.items() if n.startswith('source/')}
    expectation = {
        'record_type': 'q3_external_postflight_expectation_v0',
        'repository': M.REPOSITORY, 'source_commit': 'a9de035d1b3ac227359ca78a98274abe4c9ee186',
        'run_id': '40253690074', 'run_attempt': 1, 'job_id': 121350855532,
        'artifact_id': 12621038763,
        'request_sha256': M.digest(inner['request.json']),
        'token_map_sha256': M.digest(inner['token-map.json']),
        'verifier_sha256': M.digest(TOOL.read_bytes()),
        'inputs': {n: {'sha256': M.digest(b), 'size_bytes': len(b)} for n, b in raw.items()},
        'source_files': {n: {'sha256': M.digest(b), 'size_bytes': len(b), 'git_blob_sha1': M.blob_id(b)}
                         for n, b in source.items()},
    }
    return expectation, raw


def case(historical):
    return copy.deepcopy(historical[0]), dict(historical[1])


def repin(e, raw):
    for n, b in raw.items():
        e['inputs'][n] = {'sha256': M.digest(b), 'size_bytes': len(b)}


def run(e, raw):
    b = M.encode(e)
    return M.compare(b, M.digest(b), raw)


def modify_json(raw, name, path, value):
    d = json.loads(raw[name]); item = d
    for key in path[:-1]: item = item[key]
    item[path[-1]] = value
    raw[name] = M.encode(d)


def test_historical_carrier_replays_but_image_mismatch_stays_blocked(historical):
    e, raw = case(historical); before = copy.deepcopy(raw)
    result = run(e, raw)
    assert result['source_bound_carrier_check'] == 'PASS'
    assert result['disposition'] == 'REJECT_EXTERNAL_CONTRADICTION'
    assert result['image_comparison']['startup']['value'] == '20261012.334.1'
    assert result['image_comparison']['carrier']['value'] == '20261023.334.3'
    assert result['image_comparison']['startup']['version_line'] == 18
    assert result['original_complete_status_preserved'] is True
    assert result['artifact_attempt_attestation'] is None
    assert result['artifact_creation_window_check'] == 'PASS_LIMITED'
    assert raw == before
    assert all(result[k] == v for k, v in M.BOUNDARIES.items())


@pytest.mark.parametrize('startup_version', ['20261023.334.3', '20991231.1.2'])
def test_synthetic_equal_or_different_image_never_grants_handoff(historical, startup_version):
    e, raw = case(historical)
    raw['job.log'] = raw['job.log'].replace(b'Version: 20261012.334.1', ('Version: '+startup_version).encode())
    repin(e, raw); result = run(e, raw)
    assert result['image_comparison']['startup']['value'] == startup_version
    assert result['disposition'] == ('CONSISTENT_OFFLINE' if startup_version == '20261023.334.3'
                                     else 'REJECT_EXTERNAL_CONTRADICTION')
    assert result['capture_handoff_approved'] is False
    assert result['new_execution_authorized'] is False
    assert result['capture_consent'] == 'not_evaluated'
    assert result['evidence_source_authentication'] == 'not_established_by_offline_comparison'


@pytest.mark.parametrize('name', M.INPUTS)
def test_missing_input_rejected(historical, name):
    e, raw = case(historical); del raw[name]
    with pytest.raises(M.PostflightError, match='INPUT_SET'): run(e, raw)


@pytest.mark.parametrize('name', M.INPUTS)
def test_changed_input_fails_external_digest_before_parsing(historical, name, monkeypatch):
    e, raw = case(historical); raw[name] += b'x'
    monkeypatch.setattr(M, 'metadata', lambda *a: pytest.fail('must reject before metadata'))
    with pytest.raises(M.PostflightError, match='INPUT_DIGEST_OR_SIZE'): run(e, raw)


@pytest.mark.parametrize('key,value', [
    ('repository', 'other/repo'), ('source_commit', 'main'), ('run_id', True),
    ('run_id', '0123'), ('run_attempt', True), ('run_attempt', 2), ('job_id', True),
    ('artifact_id', 0), ('request_sha256', 'x'*64), ('verifier_sha256', '0'*64),
])
def test_closed_selection_types_and_verifier_binding(historical, key, value):
    e, raw = case(historical); e[key] = value
    with pytest.raises(M.PostflightError): run(e, raw)


@pytest.mark.parametrize('key', ['capture_handoff_approved', 'source_authentication', 'capture_consent'])
def test_boolean_or_claim_cannot_promote_selection(historical, key):
    e, raw = case(historical); e[key] = True
    with pytest.raises(M.PostflightError, match='EXPECTATION_FIELDS'): run(e, raw)


def test_wrong_expectation_digest_stops_first(historical, monkeypatch):
    e, raw = case(historical)
    monkeypatch.setattr(M, 'strict_json', lambda *a: pytest.fail('parse before digest'))
    with pytest.raises(M.PostflightError, match='EXPECTATION_DIGEST'):
        M.compare(M.encode(e), '0'*64, raw)


METADATA_FAULTS = [
    ('run.json', ['id'], 12), ('run.json', ['run_attempt'], 2),
    ('run.json', ['head_sha'], 'b'*40), ('run.json', ['head_commit','id'], 'b'*40),
    ('run.json', ['event'], 'pull_request'), ('run.json', ['head_branch'], 'other'),
    ('run.json', ['status'], 'in_progress'), ('run.json', ['conclusion'], 'failure'),
    ('run.json', ['path'], '.github/workflows/pulse_ci.yml'),
    ('run.json', ['workflow_id'], 191471316),
    ('run.json', ['repository','id'], 1), ('run.json', ['head_repository','fork'], True),
    ('run.json', ['actor','id'], 1), ('run.json', ['triggering_actor','login'], 'other'),
    ('jobs.json', ['total_count'], 2), ('jobs.json', ['total_count'], True),
    ('jobs.json', ['jobs',0,'id'], 1), ('jobs.json', ['jobs',0,'run_id'], 1),
    ('jobs.json', ['jobs',0,'run_attempt'], 2), ('jobs.json', ['jobs',0,'head_sha'], 'b'*40),
    ('jobs.json', ['jobs',0,'name'], 'other'), ('jobs.json', ['jobs',0,'conclusion'], 'skipped'),
    ('jobs.json', ['jobs',0,'labels'], ['ubuntu-latest']),
    ('jobs.json', ['jobs',0,'completed_at'], '2026-10-26T01:19:50Z'),
    ('artifact.json', ['id'], 1), ('artifact.json', ['name'], 'other'),
    ('artifact.json', ['expired'], True), ('artifact.json', ['expired'], 0),
    ('artifact.json', ['digest'], 'sha256:'+'0'*64),
    ('artifact.json', ['size_in_bytes'], 1),
    ('artifact.json', ['workflow_run','head_repository_id'], 1),
    ('artifact.json', ['workflow_run','id'], 1),
    ('artifact.json', ['workflow_run','head_sha'], 'b'*40),
    ('artifact.json', ['created_at'], '2026-10-25T00:00:00Z'),
    ('artifact.json', ['updated_at'], '2026-10-27T00:00:00Z'),
    ('artifact.json', ['expires_at'], '2026-10-20T00:00:00Z'),
]
@pytest.mark.parametrize('name,path,value', METADATA_FAULTS)
def test_rebound_metadata_still_must_satisfy_relations(historical, name, path, value):
    e, raw = case(historical); modify_json(raw, name, path, value); repin(e, raw)
    with pytest.raises(M.PostflightError): run(e, raw)


@pytest.mark.parametrize('fault', ['missing_image','provisioner_only','duplicate_image','duplicate_version',
    'nested','unclosed','wrong_os','wrong_source','wrong_request','wrong_job','wrong_artifact',
    'wrong_digest','wrong_size','late_image','malformed_timestamp','invalid_utf8','nul'])
def test_exact_startup_log_and_artifact_binding(historical, fault):
    e, raw = case(historical); log = raw['job.log']
    if fault == 'missing_image': log = log.replace(b'##[group]Runner Image\r\n', b'##[group]Unknown Image\r\n').replace(b'##[group]Runner Image\n', b'##[group]Unknown Image\n')
    elif fault == 'provisioner_only': log = log.replace(b'##[group]Runner Image\r\n', b'##[group]Runner Image Provisioner\r\n').replace(b'##[group]Runner Image\n', b'##[group]Runner Image Provisioner\n')
    elif fault == 'duplicate_image': log += b'2026-10-26T01:20:00Z ##[group]Runner Image\n'
    elif fault == 'duplicate_version': log = log.replace(b'Version: 20261012.334.1', b'Version: 20261012.334.1\n2026-10-26T01:19:54Z Version: 20261012.334.1')
    elif fault == 'nested': log = log.replace(b'Image: ubuntu-24.04', b'##[group]Nested')
    elif fault == 'unclosed': log = log.replace(b'##[endgroup]', b'not an end')
    elif fault == 'wrong_os': log = log.replace(b'Image: ubuntu-24.04', b'Image: windows-2025')
    elif fault == 'wrong_source': log = log.replace(b'EXPECTED_SOURCE_SHA: '+e['source_commit'].encode(), b'EXPECTED_SOURCE_SHA: '+b'b'*40)
    elif fault == 'wrong_request': log = log.replace(b'Q3_NATIVE_REQUEST_SHA256: '+e['request_sha256'].encode(), b'Q3_NATIVE_REQUEST_SHA256: '+b'b'*64)
    elif fault == 'wrong_job': log = log.replace(b'Complete job name: acquire', b'Complete job name: other')
    elif fault == 'wrong_artifact': log = log.replace(b'Artifact ID 12621038763', b'Artifact ID 1')
    elif fault == 'wrong_digest': log = log.replace(b'SHA256 digest of uploaded artifact is '+e['inputs']['artifact.zip']['sha256'].encode(), b'SHA256 digest of uploaded artifact is '+b'b'*64)
    elif fault == 'wrong_size': log = log.replace(b'Uploaded bytes 5897022', b'Uploaded bytes 1')
    elif fault == 'late_image': log = log.replace(b'2026-10-26T01:19:54.7777440Z', b'2026-10-26T01:20:54.7777440Z')
    elif fault == 'malformed_timestamp': log += b'no timestamp\n'
    elif fault == 'invalid_utf8': log += b'\xff'
    elif fault == 'nul': log += b'\0'
    assert log != raw['job.log'], fault
    raw['job.log'] = log; repin(e, raw)
    with pytest.raises(M.PostflightError): run(e, raw)


@pytest.mark.parametrize('raw', [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}',
    b'\xef\xbb\xbf{}', b'{"a":"\\ud800"}', b'['*70+b'0'+b']'*70])
def test_strict_json_rejects_ambiguity(raw):
    with pytest.raises(M.PostflightError): M.strict_json(raw)


@pytest.mark.parametrize('name', ['../a', '/a', 'a/../b', 'a//b', './a', 'a\\b', 'a:b', 'a\x00b'])
def test_unsafe_zip_names_rejected(name):
    raw = archive({name.replace('\x00','X'): b'x'})
    if '\x00' in name: raw = raw.replace(b'aXb', b'a\x00b')
    with pytest.raises(M.PostflightError): M.unzip(raw)


def test_duplicate_zip_rejected():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('a',b'a')
        with pytest.warns(UserWarning): z.writestr('a',b'b')
    with pytest.raises(M.PostflightError, match='ZIP_DUPLICATE'): M.unzip(stream.getvalue())


def test_central_directory_count_rejected_before_parser(monkeypatch):
    raw = bytearray(archive({'a':b'a'})); struct.pack_into('<HH',raw,len(raw)-22+8,65534,65534)
    monkeypatch.setattr(M.zipfile,'ZipFile',lambda *a: pytest.fail('unbounded parsing'))
    with pytest.raises(M.PostflightError, match='ZIP_DIRECTORY_BOUND'): M.unzip(bytes(raw))


def test_zip_symlink_rejected():
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:
        item=zipfile.ZipInfo('link');item.create_system=3;item.external_attr=0o120777<<16
        z.writestr(item,b'../escape')
    with pytest.raises(M.PostflightError,match='ZIP_MEMBER_TYPE'): M.unzip(output.getvalue())


@pytest.mark.parametrize('key', ['token_map_sha256', 'request_sha256'])
def test_stale_token_or_request_digest_rejected(historical, key):
    e, raw = case(historical); e[key] = 'b'*64
    with pytest.raises(M.PostflightError): run(e, raw)


def test_source_selection_not_current_main(historical):
    e, raw = case(historical); e['source_commit'] = '32d442dac168df287ee669ceada25870f8c73b31'
    with pytest.raises(M.PostflightError, match='RUN_BINDING'): run(e, raw)


def test_unreviewed_checker_not_loaded(historical, monkeypatch):
    e, raw = case(historical); source = {n:b'' for n in e['source_files']}
    monkeypatch.setattr(M.importlib.util,'spec_from_file_location',lambda *a: pytest.fail('unreviewed code load'))
    with pytest.raises(M.PostflightError,match='UNREVIEWED_NATIVE_CHECKER'):
        M.native_replay(b'', source, e)


@pytest.mark.parametrize('fault',['symlink','parent_symlink','hardlink','oversize','empty','directory'])
def test_safe_read_boundaries(tmp_path, fault):
    file = tmp_path/'original'; file.write_bytes(b'abcd'); path = file
    if fault=='symlink': path=tmp_path/'link';path.symlink_to(file)
    elif fault=='parent_symlink':
        parent=tmp_path/'folder';parent.mkdir();(parent/'x').write_bytes(b'abcd')
        link=tmp_path/'link';link.symlink_to(parent);path=link/'x'
    elif fault=='hardlink': path=tmp_path/'hard';os.link(file,path)
    elif fault=='empty': file.write_bytes(b'')
    elif fault=='directory': path=tmp_path
    with pytest.raises((M.PostflightError,OSError)): M.safe_read(path,3 if fault=='oversize' else 10)


def cli_case(tmp_path, e, raw):
    path=tmp_path/'inputs';path.mkdir()
    for n,b in raw.items():(path/n).write_bytes(b)
    selection=M.encode(e);(tmp_path/'expectation.json').write_bytes(selection)
    return [sys.executable,'-I','-B',str(TOOL),'--input-dir',str(path),
            '--expectation',str(tmp_path/'expectation.json'),'--expectation-sha256',M.digest(selection)]


def test_cli_recomputation_rejects_altered_disposition(historical,tmp_path):
    e,raw=case(historical);command=cli_case(tmp_path,e,raw)
    result=subprocess.run(command,capture_output=True,timeout=45)
    assert result.returncode==2,result.stderr
    report=tmp_path/'report.json';report.write_bytes(result.stdout)
    again=subprocess.run(command+['--check-report',str(report)],capture_output=True,timeout=45)
    assert again.returncode==2 and again.stdout==result.stdout
    altered=json.loads(result.stdout);altered['capture_handoff_approved']=True;report.write_bytes(M.encode(altered))
    denied=subprocess.run(command+['--check-report',str(report)],capture_output=True,timeout=45)
    assert denied.returncode==1 and denied.stdout==b''
    assert json.loads(denied.stderr)['error_code']=='REPORT_RECOMPUTATION_MISMATCH'


def test_cli_missing_inputs_never_authorize(historical,tmp_path):
    e,raw=case(historical);command=cli_case(tmp_path,e,raw);(tmp_path/'inputs/job.log').unlink()
    out=subprocess.run(command,capture_output=True,timeout=15)
    assert out.returncode==1 and out.stdout==b''
    assert json.loads(out.stderr)['capture_handoff_approved'] is False
    assert b'Traceback' not in out.stderr


def test_new_module_registered_once_in_both_manifests():
    for name,count in [('tools-tests.list',172),('pytest-tests.list',28)]:
        entries=[line.split('#',1)[0].strip() for line in (ROOT/'ci'/name).read_text().splitlines()]
        entries=[e for e in entries if e]
        assert len(entries)==len(set(entries))==count
        for target in [TEST_PATH,'tests/test_q3_preflight_preservation_v0.py','tests/test_check_pages_source_binding_v0.py']:
            assert entries.count(target)==1
        assert all(e.endswith('.py') and e.startswith(('tests/','tools/','ci/')) for e in entries)


def test_python311_grammar_and_no_network_dispatch_imports():
    tree=ast.parse(TOOL.read_text(),feature_version=(3,11))
    imports=[node for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom))]
    names={alias.name for node in imports for alias in node.names}
    assert not names.intersection({'socket','requests','urllib.request','transformers','torch','subprocess'})
    assert '20261012.334.1' not in TOOL.read_text() and '20261023.334.3' not in TOOL.read_text()
    assert not set(M.EXPECTED_FIELDS).intersection({'authorization','approved_token_map_sha256'})



def rebound_archive(e, raw, outer):
    old = e['inputs']['artifact.zip']; old_sha = old['sha256']; old_size = old['size_bytes']
    new = archive(outer); raw['artifact.zip'] = new
    a = json.loads(raw['artifact.json']); a['digest'] = 'sha256:' + M.digest(new); a['size_in_bytes'] = len(new)
    raw['artifact.json'] = M.encode(a)
    raw['job.log'] = raw['job.log'].replace(old_sha.encode(), M.digest(new).encode())
    raw['job.log'] = raw['job.log'].replace(('Uploaded bytes '+str(old_size)).encode(),
                                           ('Uploaded bytes '+str(len(new))).encode())
    repin(e, raw)


@pytest.mark.parametrize('fault', ['receipt_status','receipt_mode','receipt_claim_type','receipt_extra',
    'source_mutation','unreviewed_checker','profile_mutation','result_mutation','duplicate_receipt',
    'extra_outer_member','missing_receipt'])
def test_carrier_mutations_cannot_hide_behind_rebound_external_metadata(historical, fault):
    e, raw = case(historical); outer = M.unzip(raw['artifact.zip']); data = M.unzip(outer['evidence.zip'])
    receipt = json.loads(outer['receipt.json'])
    if fault == 'receipt_status': receipt['status'] = 'incomplete'
    elif fault == 'receipt_mode': receipt['mode'] = 'capture'
    elif fault == 'receipt_claim_type': receipt['claims']['production_gate_eligible'] = 0
    elif fault == 'receipt_extra': receipt['capture_handoff_approved'] = True
    elif fault in ('source_mutation', 'unreviewed_checker', 'profile_mutation'):
        name = (M.PROFILE if fault == 'profile_mutation'
                else M.PACK+'tools/q3_native_capture_contract_v0.py')
        data['source/'+name] += b'\n'
        if fault != 'source_mutation':
            changed = data['source/'+name]
            e['source_files'][name] = {'sha256':M.digest(changed),'size_bytes':len(changed),
                                       'git_blob_sha1':M.blob_id(changed)}
    elif fault == 'result_mutation':
        value = json.loads(data['result.json']); value['status'] = 'incomplete';data['result.json'] = M.encode(value)
    outer['evidence.zip'] = archive(data)
    receipt['archive_sha256'] = M.digest(outer['evidence.zip']); receipt['archive_size_bytes'] = len(outer['evidence.zip'])
    receipt['result_sha256'] = M.digest(data['result.json'])
    outer['receipt.json'] = M.encode(receipt)
    if fault == 'duplicate_receipt': outer['receipt.json'] = b'{"a":1,"a":2}'
    elif fault == 'extra_outer_member': outer['failure.json'] = b'{}'
    elif fault == 'missing_receipt': del outer['receipt.json']
    rebound_archive(e, raw, outer)
    with pytest.raises((M.PostflightError,KeyError)):
        run(e, raw)


@pytest.mark.parametrize('suffix', [b'Version:\tother', b'Version:other', b'Image:\tubuntu-24.04'])
def test_malformed_duplicate_image_fields_rejected(historical, suffix):
    e,raw=case(historical)
    raw['job.log']=raw['job.log'].replace(b'Version: 20261012.334.1',
        b'Version: 20261012.334.1\n2026-10-26T01:19:54Z '+suffix)
    repin(e,raw)
    with pytest.raises(M.PostflightError):run(e,raw)


def test_unprefixed_image_cannot_replace_timestamped_evidence(historical):
    e,raw=case(historical)
    raw['job.log']=raw['job.log'].replace(b'/receipt.json\n',b'/receipt.json\n##[group]Runner Image\n')
    repin(e,raw)
    with pytest.raises(M.PostflightError):run(e,raw)


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__,'-q']))
