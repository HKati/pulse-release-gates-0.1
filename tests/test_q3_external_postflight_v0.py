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
    for name,count in [('tools-tests.list',174),('pytest-tests.list',30)]:
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


IDENTITY_ANCHORS = [
    ('EXPECTED_SOURCE_SHA', 'source_commit'),
    ('Q3_NATIVE_REQUEST_SHA256', 'request_sha256'),
]


def equal_image_case(historical):
    """Synthetic equal-image observation; never a new native execution."""
    e, raw = case(historical)
    raw['job.log'] = raw['job.log'].replace(
        b'Version: 20261012.334.1', b'Version: 20261023.334.3')
    repin(e, raw)
    return e, raw


def insert_anchor_occurrence(raw, label, payload, position='after'):
    """Insert beside an existing anchor without removing valid occurrences."""
    lines = raw['job.log'].splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines)
               if re.fullmatch(rb'\S+\s+' + label.encode() + rb': [0-9a-f]+\r?\n', line)]
    assert len(indices) >= 2, label
    i = indices[0] if position == 'before' else indices[-1] + 1
    sibling = lines[indices[0] if position == 'before' else indices[-1]]
    timestamp = sibling.split(b' ', 1)[0]
    lines.insert(i, timestamp + b' ' + payload.encode('utf-8') + b'\n')
    raw['job.log'] = b''.join(lines)


@pytest.mark.parametrize('label,key', IDENTITY_ANCHORS)
@pytest.mark.parametrize('position', ['before', 'after'])
@pytest.mark.parametrize('fault', [
    'nonhex', 'empty', 'whitespace', 'uppercase', 'short', 'long',
    'wrong_hex', 'suffix', 'embedded_space', 'no_separator_space',
    'tab_separator', 'trailing_space', 'space_before_colon', 'missing_colon',
])
def test_every_identity_anchor_occurrence_validated(historical, label, key, position, fault):
    e, raw = equal_image_case(historical)
    expected = e[key]
    variants = {
        'nonhex': ': invalid',
        'empty': ':',
        'whitespace': ':   ',
        'uppercase': ': ' + expected.upper(),
        'short': ': ' + expected[:-1],
        'long': ': ' + expected + '0',
        'wrong_hex': ': ' + ('0' if expected[0] != '0' else '1') + expected[1:],
        'suffix': ': ' + expected + '-invalid',
        'embedded_space': ': ' + expected[:5] + ' ' + expected[5:],
        'no_separator_space': ':' + expected,
        'tab_separator': ':\t' + expected,
        'trailing_space': ': ' + expected + ' ',
        'space_before_colon': ' : ' + expected,
        'missing_colon': ' ' + expected,
    }
    insert_anchor_occurrence(raw, label, '  ' + label + variants[fault], position)
    repin(e, raw)  # Prove semantic rejection, not merely a stale input digest.
    with pytest.raises(M.PostflightError, match='^LOG_REQUEST_SOURCE$'):
        run(e, raw)


@pytest.mark.parametrize('label,key', IDENTITY_ANCHORS)
@pytest.mark.parametrize('indent', ['', '  ', '\t'])
def test_repeated_matching_identity_anchors_remain_consistent(historical, label, key, indent):
    e, raw = equal_image_case(historical)
    insert_anchor_occurrence(raw, label, indent + label + ': ' + e[key])
    repin(e, raw)
    result = run(e, raw)
    assert result['disposition'] == 'CONSISTENT_OFFLINE'
    assert all(result[k] == v for k, v in M.BOUNDARIES.items())


@pytest.mark.parametrize('label,key', IDENTITY_ANCHORS)
def test_missing_identity_anchor_fails_closed(historical, label, key):
    e, raw = equal_image_case(historical)
    lines = raw['job.log'].splitlines(keepends=True)
    kept = [line for line in lines if not re.fullmatch(
        rb'\S+\s+' + label.encode() + rb': [0-9a-f]+\r?\n', line)]
    assert len(kept) < len(lines)
    raw['job.log'] = b''.join(kept)
    repin(e, raw)
    with pytest.raises(M.PostflightError, match='^LOG_REQUEST_SOURCE$'):
        run(e, raw)


@pytest.mark.parametrize('label,key', IDENTITY_ANCHORS)
def test_similarly_named_field_is_not_an_identity_anchor(historical, label, key):
    e, raw = equal_image_case(historical)
    insert_anchor_occurrence(raw, label, '  ' + label + '_EXTRA: invalid')
    repin(e, raw)
    assert run(e, raw)['disposition'] == 'CONSISTENT_OFFLINE'


@pytest.mark.parametrize('label,key', IDENTITY_ANCHORS)
def test_cli_rejects_malformed_duplicate_identity_anchor(historical, tmp_path, label, key):
    e, raw = equal_image_case(historical)
    insert_anchor_occurrence(raw, label, '  ' + label + ': invalid')
    repin(e, raw)
    result = subprocess.run(cli_case(tmp_path, e, raw), capture_output=True, timeout=45)
    assert result.returncode == 1 and result.stdout == b''
    diagnostic = json.loads(result.stderr)
    assert diagnostic['error_code'] == 'LOG_REQUEST_SOURCE'
    assert diagnostic['disposition'] == 'REJECT_INVALID_OR_INCOMPLETE'
    assert all(diagnostic[k] == v for k, v in M.BOUNDARIES.items())



# Read-only acquisition companion. All provider responses below are synthetic
# adapters over preserved bytes; these tests are not new GitHub observations.
ACQUIRE_TOOL = ROOT / 'tools/acquire_q3_external_postflight_v0.py'


@pytest.fixture
def acquirer(monkeypatch):
    spec = importlib.util.spec_from_file_location('q3_acquisition_test', ACQUIRE_TOOL)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'utc_now', lambda: module.datetime(2026, 11, 1, tzinfo=module.timezone.utc))
    monkeypatch.setattr(module.socket, 'create_connection',
                        lambda *a, **k: pytest.fail('test attempted real network access'))
    return module


def acquisition_selection(acquirer, historical):
    e, _ = case(historical)
    return {'record_type': 'q3_external_postflight_acquisition_request_v0',
            **{k: e[k] for k in acquirer.IDENTITIES},
            'archive': e['inputs']['artifact.zip'], 'source_files': e['source_files'],
            'comparator_sha256': e['verifier_sha256'],
            'acquirer_sha256': M.digest(ACQUIRE_TOOL.read_bytes())}


class AcquisitionAdapter:
    def __init__(self, acquirer, selected, raw, after=None, fail_at=None):
        self.a = acquirer; self.selected = selected; self.raw = raw
        self.after = after or {}; self.fail_at = fail_at; self.calls = []
        self.transfers = []; self.counts = {}
        self.names = {v: k for k, v in acquirer.paths(selected).items()}

    def take(self, path, download):
        self.calls.append((path, download))
        if len(self.calls) == self.fail_at:
            raise self.a.AcquisitionError('HTTP_TRANSPORT')
        name = self.names[path]
        self.counts[name] = self.counts.get(name, 0) + 1
        body = self.after.get(name, self.raw[name]) if self.counts[name] > 1 else self.raw[name]
        self.transfers.append({'endpoint': path, 'sha256': self.a.digest(body),
                               'size_bytes': len(body), 'download_host': None})
        return body

    def json(self, path): return self.take(path, False)
    def download(self, path, maximum): return self.take(path, True)


def acquisition_run(acquirer, historical, tmp_path, *, raw=None, after=None, selected=None):
    selected = selected or acquisition_selection(acquirer, historical)
    raw = raw or dict(historical[1])
    module = acquirer.load_comparator()
    selection_bytes = acquirer.encode(selected)
    acquirer.select(selection_bytes, acquirer.digest(selection_bytes), module)
    adapter = AcquisitionAdapter(acquirer, selected, raw, after=after)
    output = tmp_path / 'acquisition'; store = acquirer.EvidenceDirectory(output)
    try:
        store.write('selection.json', selection_bytes)
        result, body = acquirer.acquire(selected, adapter, store, module,
            lambda: acquirer.datetime(2026, 11, 1, tzinfo=acquirer.timezone.utc))
        store.finish()
        return result, adapter, output
    finally:
        store.close()


def test_acquisition_historical_discrepancy_is_preserved(acquirer, historical, tmp_path):
    result, adapter, output = acquisition_run(acquirer, historical, tmp_path)
    assert result['disposition'] == 'REJECT_EXTERNAL_CONTRADICTION'
    assert len(adapter.calls) == 8
    assert all('/attempts/1' in p for p, _ in adapter.calls if '/runs/' in p)
    for n, b in historical[1].items(): assert (output/n).read_bytes() == b
    inv = json.loads((output/'inventory.json').read_bytes())
    assert set(inv['files']) == {p.name for p in output.iterdir()} - {'inventory.json'}
    assert all(inv[k] == v for k, v in acquirer.BOUNDARIES.items())
    for name, pin in inv['files'].items():
        b = (output/name).read_bytes()
        assert len(b) == pin['size_bytes'] and M.digest(b) == pin['sha256']
    assert stat_mode(output) == 0o700
    assert all(stat_mode(p) == 0o600 for p in output.iterdir())


def stat_mode(path):
    import stat
    return stat.S_IMODE(path.stat().st_mode)


def test_acquisition_synthetic_consistency_remains_non_authorizing(acquirer, historical, tmp_path):
    e, raw = equal_image_case(historical)
    result, adapter, output = acquisition_run(acquirer, historical, tmp_path, raw=raw)
    assert result['disposition'] == 'CONSISTENT_OFFLINE'
    assert result['capture_handoff_approved'] is False and result['authority_effect'] == 'none'
    assert result['evidence_source_authentication'] == 'not_established_by_offline_comparison'
    assert (output/'job.log').read_bytes() == raw['job.log']


@pytest.mark.parametrize('key', ['source_commit','run_id','run_attempt','job_id','artifact_id',
    'request_sha256','token_map_sha256','comparator_sha256','acquirer_sha256','repository',
    'record_type','archive','source_files','extra'])
def test_acquisition_closed_selection_rejected_before_network(acquirer, historical, key):
    s = acquisition_selection(acquirer, historical)
    s[key] = {'invalid': True} if key in ('archive','source_files') else None
    body = acquirer.encode(s)
    with pytest.raises((acquirer.AcquisitionError, M.PostflightError, ValueError)):
        acquirer.select(body, acquirer.digest(body), acquirer.load_comparator())


@pytest.mark.parametrize('raw', [b'{"a":1,"a":2}', b'{"a":NaN}', b'\xef\xbb\xbf{}', b'[]', b''])
def test_acquisition_invalid_selection_json_fails_closed(acquirer, raw):
    with pytest.raises(ValueError):
        acquirer.select(raw, acquirer.digest(raw), acquirer.load_comparator())


def test_acquisition_selection_digest_rejected(acquirer, historical):
    b = acquirer.encode(acquisition_selection(acquirer, historical))
    with pytest.raises(acquirer.AcquisitionError, match='SELECTION_DIGEST'):
        acquirer.select(b, '0'*64, acquirer.load_comparator())


def test_acquisition_unreviewed_comparator_not_loaded(acquirer, monkeypatch):
    monkeypatch.setattr(acquirer, 'COMPARATOR_SHA256', '0'*64)
    with pytest.raises(acquirer.AcquisitionError, match='UNREVIEWED_COMPARATOR'):
        acquirer.load_comparator()


@pytest.mark.parametrize('name,path,value', [
    ('run.json',['id'],1), ('run.json',['run_attempt'],2),
    ('run.json',['head_sha'],'0'*40), ('run.json',['status'],'in_progress'),
    ('run.json',['conclusion'],'failure'), ('run.json',['event'],'push'),
    ('run.json',['repository','id'],1), ('run.json',['actor','login'],'someone'),
    ('jobs.json',['total_count'],2), ('jobs.json',['jobs',0,'id'],1),
    ('artifact.json',['id'],1), ('artifact.json',['digest'],'sha256:'+'0'*64),
    ('artifact.json',['expired'],True), ('artifact.json',['workflow_run','head_sha'],'0'*40),
    ('artifact.json',['expires_at'],'2026-10-27T00:00:00Z'),
])
def test_acquisition_metadata_fault_stops_before_download(acquirer, historical, tmp_path, name, path, value):
    s = acquisition_selection(acquirer,historical); raw = dict(historical[1])
    modify_json(raw,name,path,value)
    adapter = AcquisitionAdapter(acquirer,s,raw)
    store = acquirer.EvidenceDirectory(tmp_path/'out')
    try:
        with pytest.raises(ValueError):
            acquirer.acquire(s,adapter,store,acquirer.load_comparator(),
                lambda: acquirer.datetime(2026,11,1,tzinfo=acquirer.timezone.utc))
        assert not any(download for _, download in adapter.calls)
        assert not (tmp_path/'out/artifact.zip').exists()
    finally: store.close()


@pytest.mark.parametrize('name', ['run.json','jobs.json','artifact.json'])
def test_acquisition_ancillary_metadata_change_rejects(acquirer, historical, tmp_path, name):
    after = dict(historical[1]); obj=json.loads(after[name]);obj['new_ancillary_field']='changed'
    after[name]=M.encode(obj)
    with pytest.raises(acquirer.AcquisitionError,match='METADATA_CHANGED_DURING_ACQUISITION'):
        acquisition_run(acquirer,historical,tmp_path,after=after)
    assert not (tmp_path/'acquisition/comparison.json').exists()
    assert (tmp_path/'acquisition'/name.replace('.json','.after.json')).read_bytes()==after[name]


@pytest.mark.parametrize('name', ['run.json','jobs.json','artifact.json'])
def test_acquisition_json_whitespace_change_preserves_raw_bytes(acquirer,historical,tmp_path,name):
    after=dict(historical[1]);after[name]=json.dumps(json.loads(after[name]),indent=3).encode()
    result,_,output=acquisition_run(acquirer,historical,tmp_path,after=after)
    assert result['disposition']=='REJECT_EXTERNAL_CONTRADICTION'
    assert (output/name.replace('.json','.after.json')).read_bytes()==after[name]


@pytest.mark.parametrize('fault',['changed','short','oversize'])
def test_acquisition_archive_size_digest_faults_reject(acquirer,historical,tmp_path,fault):
    raw=dict(historical[1]);b=raw['artifact.zip']
    raw['artifact.zip']={'changed':b[:-1]+bytes([b[-1]^1]),'short':b[:-1],'oversize':b+b'x'}[fault]
    with pytest.raises(acquirer.AcquisitionError,match='ARCHIVE_DIGEST_OR_SIZE|DOWNLOAD_SIZE'):
        acquisition_run(acquirer,historical,tmp_path,raw=raw)
    assert not (tmp_path/'acquisition/comparison.json').exists()


@pytest.mark.parametrize('label,key', IDENTITY_ANCHORS)
def test_acquisition_cannot_restore_malformed_log_anchor_pass(acquirer,historical,tmp_path,label,key):
    _,raw=equal_image_case(historical)
    insert_anchor_occurrence(raw,label,label+': invalid')
    with pytest.raises(ValueError,match='LOG_REQUEST_SOURCE'):
        acquisition_run(acquirer,historical,tmp_path,raw=raw)


@pytest.mark.parametrize('value',[
    'http://x.blob.core.windows.net/a', 'https://api.github.com/a',
    'https://x.blob.core.windows.net.evil.test/a', 'https://evil.test/a',
    'https://user@x.blob.core.windows.net/a', 'https://x.blob.core.windows.net:443/a',
    'https://x.blob.core.windows.net/a#fragment', 'https://x.blob.core.windows.net\\evil/a',
    '//x.blob.core.windows.net/a', 'file:///tmp/x', 'https://127.0.0.1/a',
    'https://x..blob.core.windows.net/a','https://X.blob.core.windows.net/a',
    'https://x.blob.core.windows.net//a','https://x.blob.core.windows.net/a\r\nInjected: value',
    None, '', 'https://x.blob.core.windows.net/'+'a'*8192,
])
def test_acquisition_storage_redirect_restrictions(acquirer,value):
    with pytest.raises(acquirer.AcquisitionError,match='STORAGE_URL'):acquirer.storage_url(value)


@pytest.mark.parametrize('value',[
    'https://example.blob.core.windows.net/container/log?sv=version&sig=sensitive',
    'https://example.actions.githubusercontent.com/path?token=sensitive',
])
def test_acquisition_only_supported_https_storage_urls(acquirer,value):
    assert acquirer.storage_url(value)==value


@pytest.mark.parametrize('path',[
    '/repos/other/repo/actions/runs/1/attempts/1',
    '/repos/HKati/pulse-release-gates-0.1/actions/runs/1/attempts/2',
    '/repos/HKati/pulse-release-gates-0.1/actions/runs/1/rerun',
    '/repos/HKati/pulse-release-gates-0.1/actions/runs/1/cancel',
    '/repos/HKati/pulse-release-gates-0.1/actions/workflows/q3.yml/dispatches',
    '/repos/HKati/pulse-release-gates-0.1/actions/artifacts/01',
    '/repos/HKati/pulse-release-gates-0.1/actions/artifacts/1?url=evil',
    'https://evil.test/', '//evil.test/', '/../../secrets',
])
def test_acquisition_api_route_allowlist(acquirer,path):
    with pytest.raises(acquirer.AcquisitionError,match='API_ENDPOINT'):acquirer.api_url(path)


class AcquisitionHTTPResponse:
    def __init__(self,status=200,body=b'{}',headers=None):
        from email.message import Message
        self.status=status;self.body=io.BytesIO(body);self.closed=False;self.headers=Message()
        for k,v in (headers if headers is not None else [('Content-Type','application/json')]):
            self.headers[k]=v
    def read1(self,n):return self.body.read(n)
    def close(self):self.closed=True


def http_adapter(monkeypatch,acquirer,responses):
    calls=[];handlers=[]
    class Opener:
        def open(self,request,timeout):
            calls.append((request,timeout))
            assert responses,'unexpected HTTP request or retry'
            response=responses.pop(0)
            if isinstance(response,BaseException):raise response
            return response
    def build(*h):handlers.append(h);return Opener()
    monkeypatch.setattr(acquirer.urllib.request,'build_opener',build)
    return calls,handlers


def test_acquisition_storage_never_receives_api_credentials(acquirer,monkeypatch):
    location='https://store.blob.core.windows.net/a?sig=sensitive-signed-value'
    responses=[AcquisitionHTTPResponse(302,headers=[('Location',location)]),
               AcquisitionHTTPResponse(body=b'zip',headers=[('Content-Length','3')])]
    originals=list(responses);calls,handlers=http_adapter(monkeypatch,acquirer,responses)
    reader=acquirer.GitHubReader('secret-token')
    assert reader.download(acquirer.API_PREFIX+'artifacts/123/zip',10)==b'zip'
    assert len(calls)==2 and not responses and all(r.closed for r in originals)
    assert calls[0][0].get_header('Authorization')=='Bearer secret-token'
    assert calls[1][0].get_header('Authorization') is None
    assert all(r.get_method()=='GET' for r,_ in calls)
    assert all(0<timeout<=acquirer.IO_TIMEOUT for _,timeout in calls)
    for items in handlers:
        assert any(isinstance(h,acquirer.urllib.request.ProxyHandler) and h.proxies=={} for h in items)
        assert any(isinstance(h,acquirer.NoRedirect) for h in items)
        tls=[h._context for h in items if isinstance(h,acquirer.urllib.request.HTTPSHandler)][0]
        assert tls.check_hostname and tls.verify_mode==acquirer.ssl.CERT_REQUIRED
    receipt=acquirer.encode(reader.transfers)
    assert b'secret-token' not in receipt and b'sensitive-signed-value' not in receipt
    assert b'store.blob.core.windows.net' in receipt


@pytest.mark.parametrize('status',[301,303,307,308,401,403,404,410,429,500])
def test_acquisition_unexpected_http_status_no_retry(acquirer,monkeypatch,status):
    response=AcquisitionHTTPResponse(status,headers=[('Location','https://x.blob.core.windows.net/a')])
    calls,_=http_adapter(monkeypatch,acquirer,[response]);reader=acquirer.GitHubReader('token')
    with pytest.raises(acquirer.AcquisitionError,match='HTTP_STATUS'):
        reader.json(acquirer.API_PREFIX+'artifacts/1')
    assert len(calls)==1 and response.closed


@pytest.mark.parametrize('status',[200,301,303,307,308,404,410,429])
def test_acquisition_requires_exact_api_302_for_binary(acquirer,monkeypatch,status):
    response=AcquisitionHTTPResponse(status,headers=[('Location','https://x.blob.core.windows.net/a')])
    calls,_=http_adapter(monkeypatch,acquirer,[response]);reader=acquirer.GitHubReader('token')
    with pytest.raises(acquirer.AcquisitionError,match='DOWNLOAD_REDIRECT_STATUS'):
        reader.download(acquirer.API_PREFIX+'artifacts/1/zip',10)
    assert len(calls)==1 and response.closed


def test_acquisition_storage_second_redirect_rejected(acquirer,monkeypatch):
    responses=[AcquisitionHTTPResponse(302,headers=[('Location','https://x.blob.core.windows.net/a')]),
               AcquisitionHTTPResponse(302,headers=[('Location','https://evil.test/a')])]
    calls,_=http_adapter(monkeypatch,acquirer,responses);reader=acquirer.GitHubReader('token')
    with pytest.raises(acquirer.AcquisitionError,match='HTTP_STATUS'):
        reader.download(acquirer.API_PREFIX+'jobs/1/logs',10)
    assert len(calls)==2


@pytest.mark.parametrize('headers,body',[
    ([('Content-Type','application/json'),('Content-Length','9')],b'{}'),
    ([('Content-Type','application/json'),('Content-Length','1')],b'{}'),
    ([('Content-Type','application/json'),('Content-Length','0')],b''),
    ([('Content-Type','application/json'),('Content-Length','-1')],b'{}'),
    ([('Content-Type','application/json'),('Content-Length','999999999999')],b'{}'),
    ([('Content-Type','application/json'),('Content-Length','2'),('Content-Length','2')],b'{}'),
    ([('Content-Type','application/json'),('Content-Encoding','gzip')],b'{}'),
    ([('Content-Type','text/html')],b'<html>error</html>'),
    ([('Content-Type','application/json'),('Link','<https://evil.test/>; rel="next"')],b'{}'),
    ([('Content-Type','application/json')],b''),
])
def test_acquisition_http_representation_faults(acquirer,monkeypatch,headers,body):
    calls,_=http_adapter(monkeypatch,acquirer,[AcquisitionHTTPResponse(body=body,headers=headers)])
    with pytest.raises(acquirer.AcquisitionError):
        acquirer.GitHubReader('token').json(acquirer.API_PREFIX+'artifacts/1')
    assert len(calls)==1


def test_acquisition_http_chunked_size_limit(acquirer,monkeypatch):
    response=AcquisitionHTTPResponse(body=b'x'*11,headers=[])
    calls,_=http_adapter(monkeypatch,acquirer,[response])
    with pytest.raises(acquirer.AcquisitionError,match='HTTP_SIZE'):
        acquirer.GitHubReader('token')._get('https://x.blob.core.windows.net/a',10,False)
    assert len(calls)==1 and response.closed


@pytest.mark.parametrize('kind',['timeout','url_error','incomplete_read'])
def test_acquisition_transport_errors_hide_provider_text(acquirer,monkeypatch,kind):
    errors={'timeout':TimeoutError('secret-url'),
            'url_error':acquirer.urllib.error.URLError('secret-token'),
            'incomplete_read':acquirer.http.client.IncompleteRead(b'secret-content')}
    calls,_=http_adapter(monkeypatch,acquirer,[errors[kind]])
    with pytest.raises(acquirer.AcquisitionError,match='^HTTP_TRANSPORT$'):
        acquirer.GitHubReader('token').json(acquirer.API_PREFIX+'artifacts/1')
    assert len(calls)==1


def test_acquisition_deadline_stops_before_connection(acquirer,monkeypatch):
    reader=acquirer.GitHubReader('token');reader._deadline=0
    calls,_=http_adapter(monkeypatch,acquirer,[])
    with pytest.raises(acquirer.AcquisitionError,match='ACQUISITION_DEADLINE'):
        reader.json(acquirer.API_PREFIX+'artifacts/1')
    assert not calls


@pytest.mark.parametrize('token',['','has space','bad\nheader',None,'x'*513])
def test_acquisition_token_validation(acquirer,token):
    with pytest.raises(acquirer.AcquisitionError,match='TOKEN_MISSING_OR_INVALID'):
        acquirer.GitHubReader(token)


def test_acquisition_reader_rejects_token_forwarding_to_arbitrary_endpoint(acquirer,monkeypatch):
    calls,_=http_adapter(monkeypatch,acquirer,[]);reader=acquirer.GitHubReader('token')
    with pytest.raises(acquirer.AcquisitionError,match='API_ENDPOINT'):
        reader._get('https://api.github.com.evil.test/repos/x',10,True)
    assert not calls


@pytest.mark.parametrize('kind',['existing','symlink','parent_symlink'])
def test_acquisition_output_never_overwrites_existing_or_follows_symlinks(acquirer,tmp_path,kind):
    real=tmp_path/'real';real.mkdir();(real/'keep').write_bytes(b'unchanged')
    path=real
    if kind=='symlink': path=tmp_path/'alias';path.symlink_to(real)
    elif kind=='parent_symlink':
        link=tmp_path/'alias';link.symlink_to(real);path=link/'new'
    with pytest.raises(OSError):acquirer.EvidenceDirectory(path)
    assert (real/'keep').read_bytes()==b'unchanged' and not (real/'new').exists()


def test_acquisition_existing_output_member_never_replaced(acquirer,tmp_path):
    store=acquirer.EvidenceDirectory(tmp_path/'out')
    try:
        store.write('run.json',b'first')
        with pytest.raises(FileExistsError):store.write('run.json',b'second')
        assert (tmp_path/'out/run.json').read_bytes()==b'first'
    finally:store.close()


def test_acquisition_output_inventory_rejects_untracked_members(acquirer,tmp_path):
    store=acquirer.EvidenceDirectory(tmp_path/'out')
    try:
        store.write('run.json',b'first');(tmp_path/'out/extra').write_bytes(b'x')
        with pytest.raises(acquirer.AcquisitionError,match='OUTPUT_INVENTORY'):store.finish()
    finally:store.close()


def acquisition_cli_inputs(acquirer,historical,tmp_path):
    selection=tmp_path/'selected.json';body=acquirer.encode(acquisition_selection(acquirer,historical))
    selection.write_bytes(body)
    return ['--selection',str(selection),'--selection-sha256',acquirer.digest(body)]


def test_acquisition_cli_validate_only_has_no_network_or_output(acquirer,historical,tmp_path):
    args=acquisition_cli_inputs(acquirer,historical,tmp_path)
    env=os.environ.copy();env.pop('GITHUB_TOKEN',None)
    result=subprocess.run([sys.executable,'-I','-B',str(ACQUIRE_TOOL),*args,'--validate-selection-only'],
                          capture_output=True,env=env,timeout=15)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout)
    assert report['selection_valid'] is True and report['network_accessed'] is False
    assert set(p.name for p in tmp_path.iterdir())=={'selected.json'}
    assert all(report[k]==v for k,v in acquirer.BOUNDARIES.items())


@pytest.mark.parametrize('fault',['no_consent','no_token','bad_hash','conflicting_validate'])
def test_acquisition_cli_failure_before_network_or_output(acquirer,historical,tmp_path,fault,monkeypatch,capfd):
    args=acquisition_cli_inputs(acquirer,historical,tmp_path)
    monkeypatch.delenv('GITHUB_TOKEN',raising=False)
    if fault=='no_token':args+=['--allow-network','--output-dir',str(tmp_path/'out')]
    elif fault=='bad_hash':args[-1]='0'*64
    elif fault=='conflicting_validate':args+=['--validate-selection-only','--allow-network']
    assert acquirer.main(args)==1
    stdout,stderr=capfd.readouterr();assert stdout==''
    failure=json.loads(stderr)
    assert failure['status']=='incomplete' and failure['new_execution_authorized'] is False
    assert set(p.name for p in tmp_path.iterdir())=={'selected.json'}


@pytest.mark.parametrize('equal_image',[False,True])
def test_acquisition_cli_synthetic_adapter_receipt_inventory(acquirer,historical,tmp_path,monkeypatch,capfd,equal_image):
    args=acquisition_cli_inputs(acquirer,historical,tmp_path)
    s=acquisition_selection(acquirer,historical);raw=dict(historical[1])
    if equal_image:_,raw=equal_image_case(historical)
    adapter=AcquisitionAdapter(acquirer,s,raw)
    monkeypatch.setattr(acquirer,'GitHubReader',lambda token:adapter)
    output=tmp_path/'out'
    assert acquirer.main(args+['--allow-network','--output-dir',str(output)])==(0 if equal_image else 2)
    stdout,stderr=capfd.readouterr();assert stderr==''
    receipt=json.loads(stdout);assert receipt==json.loads((output/'acquisition.json').read_bytes())
    assert receipt['status']=='complete' and receipt['metadata_recheck']=='UNCHANGED'
    assert all(receipt[k]==v for k,v in acquirer.BOUNDARIES.items())
    inventory=json.loads((output/'inventory.json').read_bytes())['files']
    assert set(inventory)=={p.name for p in output.iterdir()}-{'inventory.json'}
    assert 'comparison.json' in inventory and 'failure.json' not in inventory


@pytest.mark.parametrize('fail_at',[1,2,3,4,5,6,7,8])
def test_acquisition_cli_partial_records_preserved_without_retry(acquirer,historical,tmp_path,monkeypatch,capfd,fail_at):
    args=acquisition_cli_inputs(acquirer,historical,tmp_path)
    adapter=AcquisitionAdapter(acquirer,acquisition_selection(acquirer,historical),dict(historical[1]),fail_at=fail_at)
    monkeypatch.setattr(acquirer,'GitHubReader',lambda token:adapter)
    output=tmp_path/'out'
    assert acquirer.main(args+['--allow-network','--output-dir',str(output)])==1
    stdout,stderr=capfd.readouterr();assert stdout==''
    failure=json.loads(stderr);assert failure['error_code']=='HTTP_TRANSPORT'
    assert len(adapter.calls)==fail_at and failure['status']=='incomplete'
    assert not (output/'acquisition.json').exists() and not (output/'comparison.json').exists()
    inventory=json.loads((output/'inventory.json').read_bytes())['files']
    assert set(inventory)=={p.name for p in output.iterdir()}-{'inventory.json'}
    assert set(inventory)>={'failure.json','selection.json'}
    assert all(failure[k]==v for k,v in acquirer.BOUNDARIES.items())


def test_acquisition_cannot_expose_dispatch_or_synthetic_cli_switches(acquirer):
    source=ACQUIRE_TOOL.read_text();tree=ast.parse(source,feature_version=(3,11))
    imports={a.name for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names}
    assert not imports.intersection({'torch','transformers','subprocess'})
    assert 'method=\'GET\'' in source and 'method=\'POST\'' not in source
    arguments={n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call)
               and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument'
               and n.args and isinstance(n.args[0],ast.Constant)}
    assert arguments=={'--selection','--selection-sha256','--output-dir',
                        '--validate-selection-only','--allow-network'}


def test_acquisition_old_offline_comparator_bytes_remain_pinned(acquirer):
    assert M.digest(TOOL.read_bytes())==acquirer.COMPARATOR_SHA256
    assert M.BOUNDARIES['capture_handoff_approved'] is False
    assert M.BOUNDARIES['evidence_source_authentication']=='not_established_by_offline_comparison'




@pytest.mark.parametrize('fault',['content','mode','hardlink','symlink','truncate'])
def test_acquisition_inventory_checks_final_file_bytes(acquirer,tmp_path,fault):
    directory=tmp_path/'out';store=acquirer.EvidenceDirectory(directory)
    try:
        store.write('run.json',b'first');path=directory/'run.json'
        if fault=='content':path.write_bytes(b'other')
        elif fault=='truncate':path.write_bytes(b'')
        elif fault=='mode':path.chmod(0o644)
        elif fault=='hardlink':os.link(path,tmp_path/'outside')
        else:
            path.unlink();external=tmp_path/'external';external.write_bytes(b'first');path.symlink_to(external)
        with pytest.raises((acquirer.AcquisitionError,OSError)):store.finish()
        assert not (directory/'inventory.json').exists()
    finally:store.close()


def test_acquisition_expiry_during_download_is_not_accepted(acquirer,historical,tmp_path):
    s=acquisition_selection(acquirer,historical);adapter=AcquisitionAdapter(acquirer,s,dict(historical[1]))
    times=iter([acquirer.datetime(2026,11,1,tzinfo=acquirer.timezone.utc),
                acquirer.datetime(2026,12,1,tzinfo=acquirer.timezone.utc)])
    store=acquirer.EvidenceDirectory(tmp_path/'out')
    try:
        with pytest.raises(acquirer.AcquisitionError,match='ARTIFACT_NOT_CURRENT'):
            acquirer.acquire(s,adapter,store,acquirer.load_comparator(),lambda:next(times))
        assert len(adapter.calls)==8 and not (tmp_path/'out/comparison.json').exists()
    finally:store.close()


def test_acquisition_urllib_http_error_302_is_handled_without_token_forwarding(acquirer,monkeypatch):
    from email.message import Message
    headers=Message();headers['Location']='https://x.blob.core.windows.net/a?sig=secret'
    redirect=acquirer.urllib.error.HTTPError(acquirer.API_ROOT+acquirer.API_PREFIX+'artifacts/1/zip',
                                           302,'Found',headers,io.BytesIO(b''))
    calls,_=http_adapter(monkeypatch,acquirer,[redirect,AcquisitionHTTPResponse(body=b'abc',headers=[])])
    reader=acquirer.GitHubReader('token')
    assert reader.download(acquirer.API_PREFIX+'artifacts/1/zip',10)==b'abc'
    assert calls[1][0].get_header('Authorization') is None


def test_acquisition_duplicate_location_rejected(acquirer,monkeypatch):
    response=AcquisitionHTTPResponse(302,headers=[('Location','https://x.blob.core.windows.net/a'),
                                               ('Location','https://y.blob.core.windows.net/b')])
    calls,_=http_adapter(monkeypatch,acquirer,[response])
    with pytest.raises(acquirer.AcquisitionError,match='DUPLICATE_HTTP_HEADER'):
        acquirer.GitHubReader('token').download(acquirer.API_PREFIX+'jobs/1/logs',10)
    assert len(calls)==1 and response.closed


def test_acquisition_no_redirect_handler_never_follows_automatically(acquirer):
    assert acquirer.NoRedirect().redirect_request(None,None,302,'Found',{},'https://evil.test/') is None


@pytest.mark.parametrize('fault',['link','parent_link','hardlink','empty','oversize','directory'])
def test_acquisition_selected_source_reader_rejects_aliases(acquirer,tmp_path,fault):
    path=tmp_path/'source';path.write_bytes(b'abc')
    if fault=='link':q=tmp_path/'link';q.symlink_to(path);path=q
    elif fault=='parent_link':
        d=tmp_path/'dir';d.mkdir();(d/'source').write_bytes(b'abc')
        link=tmp_path/'link';link.symlink_to(d);path=link/'source'
    elif fault=='hardlink':os.link(path,tmp_path/'alias')
    elif fault=='empty':path.write_bytes(b'')
    elif fault=='directory':path=tmp_path
    with pytest.raises((acquirer.AcquisitionError,OSError)):
        acquirer.read_source(path,2 if fault=='oversize' else 4)


def test_acquisition_output_write_failure_cannot_report_complete(acquirer,historical,tmp_path,monkeypatch,capfd):
    args=acquisition_cli_inputs(acquirer,historical,tmp_path)
    adapter=AcquisitionAdapter(acquirer,acquisition_selection(acquirer,historical),dict(historical[1]))
    monkeypatch.setattr(acquirer,'GitHubReader',lambda token:adapter)
    original=acquirer.EvidenceDirectory.write
    def write(self,name,raw):
        if name=='artifact.zip':raise OSError('sensitive-provider-diagnostic')
        return original(self,name,raw)
    monkeypatch.setattr(acquirer.EvidenceDirectory,'write',write)
    assert acquirer.main(args+['--allow-network','--output-dir',str(tmp_path/'out')])==1
    stdout,stderr=capfd.readouterr();assert stdout=='' and 'sensitive-provider-diagnostic' not in stderr
    assert json.loads(stderr)['status']=='incomplete'
    assert not (tmp_path/'out/acquisition.json').exists()
    assert (tmp_path/'out/failure.json').exists()


# Mandatory capture handoff v1. All provider/process records below are explicitly
# synthetic controls. The historical package is never modified on disk.
HANDOFF_TOOL = ROOT / 'tools/q3_capture_handoff_v1.py'
NATIVE_COLLECTOR = 'PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py'


def handoff_module(root=ROOT):
    spec=importlib.util.spec_from_file_location('q3_handoff_test', root/'tools/q3_capture_handoff_v1.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def native_mod(root, name):
    path=root/'PULSE_safe_pack_v0/tools'/(name+'.py')
    spec=importlib.util.spec_from_file_location(name+'_handoff_test',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def current_native_sources(root=ROOT):
    p=json.loads((root/M.PROFILE).read_bytes())
    return {n:(root/n).read_bytes() for n in p['source_files']}


def synthetic_bound_preflight(historical, source):
    """Rebind a COPY to selected source bytes for positive integration controls.

    This is not a new observation of the historical source or a correction of its
    image discrepancy. Every changed fixture is independently marked synthetic.
    """
    e,raw=equal_image_case(historical);outer=M.unzip(raw['artifact.zip']);d=M.unzip(outer['evidence.zip'])
    old=M.digest(d['prelaunch.json'])
    for n,b in source.items():d['source/'+n]=b
    pre=json.loads(d['prelaunch.json']);pre['source_files']={n:M.digest(b) for n,b in source.items()}
    d['prelaunch.json']=M.encode(pre);new=M.digest(d['prelaunch.json'])
    for n in list(d):
        if not n.startswith('source/') and n not in ('prelaunch.json','result.json'):
            d[n]=d[n].replace(old.encode(),new.encode())
    result=json.loads(d['result.json']);result['inventory']={n:{'size_bytes':len(b),'sha256':M.digest(b)}
        for n,b in d.items() if n!='result.json'}
    d['result.json']=M.encode(result)
    receipt=json.loads(outer['receipt.json']);inner=archive(d)
    receipt.update(archive_sha256=M.digest(inner),archive_size_bytes=len(inner),result_sha256=M.digest(d['result.json']))
    e['source_files']={n:{'sha256':M.digest(b),'git_blob_sha1':M.blob_id(b),'size_bytes':len(b)} for n,b in source.items()}
    rebound_archive(e,raw,{'evidence.zip':inner,'receipt.json':M.encode(receipt)})
    assert run(e,raw)['disposition']=='CONSISTENT_OFFLINE'
    return e,raw


def synthetic_native_capture(source, original_preflight, request, run_id):
    """Finite TEST ONLY protocol carrier using synthetic responses, not inference."""
    c=native_mod(ROOT,'q3_native_capture_contract_v0');p=c.load_profile(source);frame=c.task_frame(source,p)
    k=native_mod(ROOT,'check_q3_native_capture_v0');a=native_mod(ROOT,'acquire_q3_reference_inputs_v0')
    d=M.unzip(M.unzip(original_preflight['artifact.zip'])['evidence.zip']);d.pop('result.json')
    d.update({'source/'+n:b for n,b in source.items()})
    d['request.json']=c.encode(request)
    plane=json.loads(d['control-plane.json']);plane.update(run_id=run_id,source_commit=request['source_commit'])
    d['control-plane.json']=c.encode(plane)
    pre=json.loads(d['prelaunch.json']);pre.update(request=request,source_commit=request['source_commit'],run_id=run_id,
        source_files={n:c.digest(b) for n,b in source.items()},control_plane_sha256=c.digest(d['control-plane.json']))
    d['prelaunch.json']=c.encode(pre)
    binding={'prelaunch_sha256':c.digest(d['prelaunch.json']),'source_commit':request['source_commit'],'run_id':run_id,'run_attempt':1}
    mapping=json.loads(d['token-map.json']);ms=c.digest(d['token-map.json'])
    d['worker-ready.json']=c.encode({'record_type':'q3_worker_ready_v0','binding':binding,'mode':'capture'})
    d['token-map-end.json']=c.encode({'record_type':'q3_token_map_end_v0','binding':binding,'token_map_sha256':ms,'task_count':204})
    for row in mapping['rows']:d['tokens/'+row['task_id']+'.json']=c.encode({'record_type':'q3_token_row_v0','binding':binding,'row':row})
    generation={**p['generation'],'disable_compile':True};runtime=k.expected_runtime(p)
    d['model-ready.json']=c.encode({'record_type':'q3_model_ready_v0','binding':binding,'token_map_sha256':ms,
        'effective_generation':generation,'runtime':runtime})
    d['subject.json']=c.encode({'record_type':'q3_capture_subject_v0','binding':binding,
        'model_ready_sha256':c.digest(d['model-ready.json']),'token_map_sha256':ms})
    full={**binding,'subject_sha256':c.digest(d['subject.json'])}
    d['bound.json']=c.encode({'record_type':'q3_bound_v0','binding':full})
    sb=json.loads(d['worker-sandbox.json']);oldunit=sb['unit'];prefix=oldunit.rsplit('-preflight.service',1)[0]
    sb['unit']=prefix+'-captureworker.service';sb['stage']='captureworker'
    sb['run_mount']=json.loads(json.dumps(sb['run_mount']).replace(oldunit,sb['unit']))
    sb['properties']['RuntimeMaxUSec']='14400s';sb['capture_runtime_seconds']=14400
    d['worker-sandbox.json']=c.encode(sb)
    cleanup=json.loads(d['worker-cleanup.json']);cleanup['unit']=sb['unit'];d['worker-cleanup.json']=c.encode(cleanup)
    lifecycle=json.loads(d['lifecycle.json'])
    for svc in lifecycle['services']:
        if svc['unit']==oldunit:svc['unit']=sb['unit']
    occ=[];timers=[];examples=[]
    for task,row in zip(frame,mapping['rows']):
        slot={'task_id':task['task_id'],'ordinal':task['ordinal'],'attempt':1};stem='calls/'+task['task_id']
        moment=task['ordinal']*100_000_000_000
        ready={'record_type':'q3_slot_ready_v0','binding':full,'slot':slot,'input_ids':row['input_ids'],
            'effective_generation':generation,'runtime':runtime}
        # Empty EOS text is an allowed synthetic transport observation, not a Q1 label.
        response={**ready,'record_type':'q3_response_v0','new_token_ids':[2],'text':'','text_utf8_base64':'','stop_reason':'eos'}
        d[stem+'.ready.json']=c.encode(ready);d[stem+'.response.json']=c.encode(response);d[stem+'.utf8']=b''
        d[stem+'.intent.json']=c.encode({**slot,'binding':full,'intent':'before_GO'})
        occ.append({**slot,'status':'completed','intent_saved_ns':moment,'watchdog_arm_begin_ns':moment+1,
            'generation_start_ns':moment+2,'generation_deadline_ns':moment+60_000_000_002,
            'response_received_ns':moment+3,'watchdog_closed_ns':moment+4})
        timer=prefix+f"-call-{task['ordinal']:03d}"
        timers.append({'prefix':timer,'closure':{'units':[{'unit':timer+'-watchdog'+suffix,
            'LoadState':'not-found','ActiveState':'inactive'} for suffix in ('.timer','.service')],'closed_ns':moment+4}})
        examples.append({'example_id':task['task_id'],'prompt':task['prompt'],'response':'','context':task['context'],
                         'metadata':{'task_form':task['task_form']}})
    lifecycle['timers']=timers;d['lifecycle.json']=c.encode(lifecycle)
    d['examples.jsonl']=b''.join(c.encode(x) for x in examples)
    d['session-end.json']=c.encode({'record_type':'q3_session_end_v0','binding':full,'completed_calls':204})
    terminal=json.loads(d['terminal.json']);terminal.update(mode='capture',binding=binding,attempted_calls=204,
        occurrences=occ,worker_deadline_ns=30_000_000_000_000,worker_exit_observed_ns=29_000_000_000_000)
    d['terminal.json']=c.encode(terminal)
    d['token-check.json']=c.encode({'record_type':'q3_native_token_check_v0','request_sha256':c.digest(d['request.json']),
        'prelaunch_sha256':c.digest(d['prelaunch.json']),'token_map_sha256':ms,'checked_tasks':204,'checked_responses':204,
        'tokenization_reperformed':True,'generation_executed':False,'examples_sha256':c.digest(d['examples.jsonl']),
        'claims':dict(c.CLAIMS)})
    assert k.validate_complete(source,d)['complete'] is True
    inner,result=a.build_carrier(c,d,request,'complete',None)
    receipt={'record_type':'q3_native_capture_receipt_v0','status':'complete','mode':'capture',
        'archive_sha256':c.digest(inner),'archive_size_bytes':len(inner),'result_sha256':c.digest(c.encode(result)),
        'request_sha256':c.digest(d['request.json']),'source_commit':request['source_commit'],
        'token_map_sha256':ms,'claims':dict(c.CLAIMS)}
    return {'evidence.zip':inner,'receipt.json':c.encode(receipt)}


@pytest.fixture(scope='module')
def handoff_case(historical):
    h=handoff_module();source=current_native_sources();e,raw=synthetic_bound_preflight(historical,source)
    extra={n:(ROOT/n).read_bytes() for n in h.EXTRA_SOURCES};a,m=h.components(ROOT,extra)
    s=acquisition_selection(a,(e,raw));c=native_mod(ROOT,'q3_native_capture_contract_v0')
    nr=json.loads(M.unzip(M.unzip(raw['artifact.zip'])['evidence.zip'])['request.json'])
    nr.update(mode='capture',source_commit='c'*40,authorization=c.AUTHORIZATIONS['capture'],
              approved_token_map_sha256=s['token_map_sha256'])
    nb=c.encode(nr);sr=a.encode(s)
    envelope={'record_type':h.REQUEST_TYPE,'repository':h.REPOSITORY,'capture_source_commit':nr['source_commit'],
        'native_request_utf8':nb.decode(),'native_request_sha256':h.digest(nb),
        'postflight_selection_utf8':sr.decode(),'postflight_selection_sha256':h.digest(sr),
        'handoff_source_files':{n:h.pin(b) for n,b in extra.items()},'authorization':h.AUTHORIZATION}
    current={'id':90001,'run_attempt':1,'head_sha':nr['source_commit'],'head_branch':'main',
        'event':'workflow_dispatch','status':'in_progress','conclusion':None,'path':h.WORKFLOW,
        'actor':{'login':'HKati'},'triggering_actor':{'login':'HKati'}}
    native=synthetic_native_capture(source,raw,nr,'90001')
    return {'h':h,'a':a,'m':m,'c':c,'source':source,'extra':extra,'s':s,'raw':raw,'envelope':envelope,
            'nr':nr,'native':native,'current':current}


def hvalidate(f,envelope=None,source=None,extra=None):
    h=f['h'];e=envelope or f['envelope'];raw=h.encode(e)
    return h.validate(raw,h.digest(raw),f['c'].encode(f['nr']),source or f['source'],extra or f['extra'],
                      ROOT,f['a'],f['m'])


def test_handoff_v1_request_preserves_v0_nested_contract(handoff_case):
    f=handoff_case;e,r,s=hvalidate(f)
    assert r==f['nr'] and s==f['s']
    schema=json.loads((ROOT/f['h'].SCHEMA).read_bytes())
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(schema);Draft202012Validator(schema).validate(e)


@pytest.mark.parametrize('key',sorted({'record_type','repository','capture_source_commit','native_request_utf8',
    'native_request_sha256','postflight_selection_utf8','postflight_selection_sha256','handoff_source_files','authorization'}))
@pytest.mark.parametrize('action',['missing','wrong'])
def test_handoff_closed_envelope_rejects_invalid_fields(handoff_case,key,action):
    e=copy.deepcopy(handoff_case['envelope'])
    if action=='missing':e.pop(key)
    else:e[key]=None
    with pytest.raises((ValueError,KeyError,TypeError)):hvalidate(handoff_case,e)


@pytest.mark.parametrize('key',['approved','authenticated','skip_postflight','saved_receipt','reader','callback','retry'])
def test_handoff_envelope_has_no_override_or_adapter_inputs(handoff_case,key):
    e=copy.deepcopy(handoff_case['envelope']);e[key]=True
    with pytest.raises(ValueError,match='HANDOFF_REQUEST_FIELDS'):hvalidate(handoff_case,e)


@pytest.mark.parametrize('name',['tools/q3_capture_handoff_v1.py','tools/acquire_q3_external_postflight_v0.py',
    'tools/check_q3_external_postflight_v0.py','schemas/metrics/q3_capture_handoff_request_v1.schema.json'])
def test_handoff_extra_source_substitution_rejected(handoff_case,name):
    f=handoff_case;ex=dict(f['extra']);ex[name]+=b'\n'
    with pytest.raises(ValueError,match='SOURCE_BINDING'):hvalidate(f,extra=ex)


@pytest.mark.parametrize('name',['PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py',
    '.github/workflows/q3_reference_acquisition_v0.yml','docs/compute/PULSEMECH_Q3_REFERENCE_RECOMPUTATION_v0.md'])
def test_handoff_changed_native_source_cannot_reuse_preflight(handoff_case,name):
    source=dict(handoff_case['source']);source[name]+=b'\n'
    with pytest.raises(ValueError,match='NATIVE_SOURCE_COMPATIBILITY|FIXED_INPUT_CHANGED'):hvalidate(handoff_case,source=source)


@pytest.mark.parametrize('field,value',[('id',True),('id',0),('run_attempt',True),('run_attempt',2),
    ('head_sha','d'*40),('head_branch','other'),('event','push'),('status','completed'),('conclusion','success'),
    ('path','other.yml'),('actor',{'login':'someone'}),('triggering_actor',{'login':'someone'})])
def test_handoff_requires_actual_current_owner_dispatch(handoff_case,field,value):
    f=handoff_case;r=copy.deepcopy(f['current']);r[field]=value
    with pytest.raises(ValueError,match='HANDOFF_CURRENT_RUN'):
        f['h'].current_run(M.encode(r),'90001','c'*40,f['s']['run_id'],M)


def test_handoff_preflight_cannot_be_its_own_capture(handoff_case):
    f=handoff_case
    with pytest.raises(ValueError,match='HANDOFF_CURRENT_RUN'):
        f['h'].current_run(M.encode(f['current']),'90001','c'*40,'90001',M)


def hrun(f,tmp_path,monkeypatch,*,fault=None):
    h=handoff_module();a,m=h.components(ROOT,f['extra'])
    monkeypatch.setattr(h,'components',lambda root,sources:(a,m))
    monkeypatch.setattr(a,'utc_now',lambda:M.stamp('2026-11-01T00:00:00Z'))
    monkeypatch.setattr(h,'now',lambda:'2026-11-01T00:00:00Z')
    if fault=='final_replay':monkeypatch.setattr(h,'check',lambda *args:(_ for _ in ()).throw(ValueError('SYNTHETIC_FINAL_REPLAY')))
    if fault=='stage_cleanup':
        import types
        monkeypatch.setattr(h,'shutil',types.SimpleNamespace(rmtree=lambda *args:(_ for _ in ()).throw(OSError('synthetic cleanup'))))
    monkeypatch.setattr(a.socket,'create_connection',lambda *args,**kw:pytest.fail('no live network in regressions'))
    raw=dict(f['raw'])
    if fault=='contradiction':raw['job.log']=raw['job.log'].replace(b'Version: 20261023.334.3',b'Version: 20261012.334.1')
    adapter=AcquisitionAdapter(a,f['s'],raw,fail_at=4 if fault=='transport' else None)
    current_path=a.API_PREFIX+'runs/90001/attempts/1';current_calls=[]
    class Reader:
        def __init__(self,token):assert token=='synthetic-never-sent';self.transfers=[]
        def json(self,path):
            if fault=='missing_network_token':raise ValueError('TOKEN_REQUIRED')
            if path==current_path:
                current_calls.append(path);r=copy.deepcopy(f['current'])
                if fault=='current_changed' and len(current_calls)==2:r['head_sha']='d'*40
                b=M.encode(r)
                self.transfers.append({'endpoint':path,'sha256':M.digest(b),'size_bytes':len(b),'download_host':None})
                return b
            b=adapter.json(path);self.transfers.append(adapter.transfers[-1]);return b
        def download(self,path,maximum):
            b=adapter.download(path,maximum);row=dict(adapter.transfers[-1]);row['download_host']='synthetic.blob.core.windows.net'
            self.transfers.append(row);return b
    monkeypatch.setattr(a,'GitHubReader',Reader)
    rt=tmp_path/'runner';rt.mkdir();out=tmp_path/'out';calls=[]
    env={'GITHUB_TOKEN':'synthetic-never-sent','GITHUB_RUN_ID':'90001','GITHUB_RUN_ATTEMPT':'1',
         'GITHUB_SHA':'c'*40,'RUNNER_TEMP':str(rt)}
    def destination(c,env):out.mkdir(mode=0o700);return out,os.getuid(),os.getgid()
    def native(c,p,r,source,root,raw,native_env):
        calls.append((r,raw));assert len(current_calls)==2
        assert native_env['RUNNER_TEMP']!=env['RUNNER_TEMP']
        target=Path(native_env['RUNNER_TEMP'])/'q3-reference-capture/90001-1';target.mkdir(parents=True)
        for name,b in f['native'].items():target.joinpath(name).write_bytes(b)
        if fault=='native_raise':
            (target/'failure.json').write_bytes(b'{"synthetic":true}\n');raise ValueError('SYNTHETIC_NATIVE_FAILURE')
        if fault=='native_incomplete':return 1
        if fault=='native_wrong_run':
            # A coherently rebound run mismatch is tested separately through native replay.
            target.joinpath('receipt.json').write_bytes(b'{}')
        return 0
    plane=lambda *args:{'run_id':'90001','source_commit':'c'*40}
    rc=h.run(f['c'],f['c'].load_profile(f['source']),f['nr'],f['source'],ROOT,h.encode(f['envelope']),env,
             f['extra'],native,plane,destination)
    return h,rc,out,calls,current_calls,rt


def test_handoff_live_sequence_calls_core_once_and_offline_replays(handoff_case,tmp_path,monkeypatch):
    h,rc,out,calls,reads,rt=hrun(handoff_case,tmp_path,monkeypatch)
    assert rc==0 and len(calls)==1 and len(reads)==2 and not list(rt.iterdir())
    assert calls[0][1]==handoff_case['c'].encode(handoff_case['nr'])
    raw=(out/'evidence.zip').read_bytes();receipt=json.loads((out/'receipt.json').read_bytes())
    assert receipt['record_type']=='q3_capture_handoff_receipt_v1' and receipt['status']=='complete'
    result=h.check(raw,h.digest(raw),h.digest(h.encode(handoff_case['envelope'])),'c'*40,'90001',ROOT,handoff_case['extra'])
    assert result['complete'] is True and result['live_origin_reobserved'] is False
    assert result['new_execution_authorized'] is False and result['saved_record_authenticates_origin'] is False
    nested=h.unzip(raw)
    for name,b in handoff_case['native'].items():assert nested['native/'+name]==b
    assert set(p.name for p in out.iterdir())=={'evidence.zip','receipt.json'}
    assert stat_mode(out)==0o700 and all(stat_mode(p)==0o600 for p in out.iterdir())


@pytest.mark.parametrize('fault',['contradiction','transport','current_changed'])
def test_handoff_denial_prevents_native_callback_and_preserves(handoff_case,tmp_path,monkeypatch,fault):
    h,rc,out,calls,reads,rt=hrun(handoff_case,tmp_path,monkeypatch,fault=fault)
    assert rc==2 and calls==[] and not list(rt.iterdir())
    assert json.loads((out/'receipt.json').read_bytes())['status']=='rejected'
    assert (out/'failure.json').exists()
    d=h.unzip((out/'evidence.zip').read_bytes())
    assert not any(n.startswith('native/') for n in d)
    assert d['request.json']==h.encode(handoff_case['envelope'])
    assert json.loads(d['bundle.json'])['error_code']


@pytest.mark.parametrize('fault',['native_raise','native_incomplete','native_wrong_run'])
def test_handoff_native_failures_remain_incomplete(handoff_case,tmp_path,monkeypatch,fault):
    h,rc,out,calls,reads,rt=hrun(handoff_case,tmp_path,monkeypatch,fault=fault)
    assert rc==1 and len(calls)==1 and not list(rt.iterdir())
    assert json.loads((out/'receipt.json').read_bytes())['status']=='incomplete'
    d=h.unzip((out/'evidence.zip').read_bytes());assert d['native/evidence.zip']==handoff_case['native']['evidence.zip']
    if fault=='native_raise':assert 'native/failure.json' in d


@pytest.fixture(scope='module')
def handoff_complete_bytes(handoff_case,tmp_path_factory):
    # Use a local MonkeyPatch scope so a later test cannot accidentally retain a transport double.
    with pytest.MonkeyPatch.context() as mp:
        h,rc,out,*_=hrun(handoff_case,tmp_path_factory.mktemp('handoff-complete'),mp)
        assert rc==0
        return out.joinpath('evidence.zip').read_bytes()


def rebind_handoff_bundle(h,data):
    record=json.loads(data['bundle.json']);record['inventory']={n:{'sha256':h.digest(b),'size_bytes':len(b)}
        for n,b in data.items() if n!='bundle.json'}
    data['bundle.json']=h.encode(record);return h.zip_bytes(data)


@pytest.mark.parametrize('fault',['admission','comparison','missing_native','wrong_run','claim','staging',
    'inventory','extra','after_metadata','selection','native_receipt','native_archive','current_run'])
def test_handoff_replay_rejects_coherently_rehashed_false_completion(handoff_case,handoff_complete_bytes,fault):
    f=handoff_case;h=f['h'];d=h.unzip(handoff_complete_bytes)
    if fault=='admission':d['admission.json']=h.encode({'decision':'ADMIT_CURRENT_DISPATCH'})
    elif fault=='comparison':d['postflight/comparison.json']=h.encode({'disposition':'CONSISTENT_OFFLINE'})
    elif fault=='missing_native':del d['native/evidence.zip']
    elif fault=='wrong_run':
        v=json.loads(d['bundle.json']);v['capture_context']['run_id']='99999';d['bundle.json']=h.encode(v)
    elif fault=='claim':
        v=json.loads(d['bundle.json']);v['authority_effect']='allow';d['bundle.json']=h.encode(v)
    elif fault=='staging':
        v=json.loads(d['bundle.json']);v['staging_removed']=False;d['bundle.json']=h.encode(v)
    elif fault=='inventory':
        v=json.loads(d['bundle.json']);v['inventory']={};d['bundle.json']=h.encode(v)
    elif fault=='extra':d['approval.json']=b'true'
    elif fault=='after_metadata':d['postflight/run.after.json']=b'{}'
    elif fault=='selection':d['postflight/selection.json']=b'{}'
    elif fault=='native_receipt':d['native/receipt.json']=b'{}'
    elif fault=='native_archive':d['native/evidence.zip']+=b'x'
    elif fault=='current_run':
        v=json.loads(d['capture-run.before.json']);v['event']='push';d['capture-run.before.json']=h.encode(v)
    raw=h.zip_bytes(d) if fault=='inventory' else rebind_handoff_bundle(h,d)
    with pytest.raises((ValueError,KeyError,TypeError,zipfile.BadZipFile)):
        h.check(raw,h.digest(raw),h.digest(h.encode(f['envelope'])),'c'*40,'90001',ROOT,f['extra'])


@pytest.mark.parametrize('field,value',[('archive','0'*64),('request','0'*64),('source','d'*40),('run','90002')])
def test_handoff_replay_requires_independent_capture_anchors(handoff_case,handoff_complete_bytes,field,value):
    f=handoff_case;h=f['h'];args=[h.digest(handoff_complete_bytes),h.digest(h.encode(f['envelope'])),'c'*40,'90001']
    args[['archive','request','source','run'].index(field)]=value
    with pytest.raises(ValueError):h.check(handoff_complete_bytes,*args,ROOT,f['extra'])


def test_handoff_native_core_is_not_the_cli_admission_route():
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0');tree=ast.parse((ROOT/NATIVE_COLLECTOR).read_text())
    guard=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='entry_guard')
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    assert 'CAPTURE_HANDOFF_REQUIRED' in ast.get_source_segment((ROOT/NATIVE_COLLECTOR).read_text(),guard)
    text=ast.get_source_segment((ROOT/NATIVE_COLLECTOR).read_text(),main)
    assert "request['mode']=='capture'" in text and 'return execute_handoff(' in text
    assert tuple(a.HANDOFF_SOURCES)==handoff_module().EXTRA_SOURCES
    workflow=(ROOT/M.WORKFLOW).read_text()
    assert 'acquire_q3_reference_inputs_v0.py' in workflow and 'q3_capture_handoff_v1.py' not in workflow
    assert 'contents: write' not in workflow and 'actions: write' not in workflow


@pytest.mark.parametrize('mode',['token-preflight','capture'])
def test_handoff_main_routes_to_exact_mandatory_path(monkeypatch,mode):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0');calls=[]
    monkeypatch.setattr(a,'entry_guard',lambda *args,**kwargs:('C','P',{'mode':mode},{'source':'snapshot'}))
    monkeypatch.setattr(a,'image_gate',lambda *args:calls.append('image'))
    monkeypatch.setattr(a,'execute',lambda *args:calls.append('native') or 0)
    monkeypatch.setattr(a,'execute_handoff',lambda *args:calls.append('handoff') or 0)
    assert a.main(['--repo-root',str(ROOT),'--source-commit','a'*40,'--request','{}','--request-sha256',M.digest(b'{}')])==0
    assert calls==(['image','native'] if mode=='token-preflight' else ['image','handoff'])


@pytest.mark.parametrize('raw',[b'{}',b'[]',b'{"record_type":"q3_capture_handoff_request_v1"}',
    b'{"record_type":"q3_capture_handoff_request_v1","record_type":"other"}'])
def test_handoff_malformed_cli_cannot_reach_runtime(tmp_path,monkeypatch,raw):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0')
    monkeypatch.setattr(a,'execute',lambda *args:pytest.fail('unvalidated native execution'))
    monkeypatch.setattr(a,'execute_handoff',lambda *args:pytest.fail('unvalidated handoff'))
    assert a.main(['--repo-root',str(tmp_path),'--source-commit','a'*40,'--request',raw.decode(),
                   '--request-sha256',M.digest(raw)])==2


def test_handoff_python311_grammar_and_no_generation_or_dispatch():
    tree=ast.parse(HANDOFF_TOOL.read_text(),feature_version=(3,11))
    assert not any(isinstance(n,ast.Attribute) and n.attr in ('generate','dispatch','create_workflow_dispatch') for n in ast.walk(tree))
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='run' for n in ast.walk(main))


@pytest.fixture(scope='module')
def handoff_checkout(handoff_case,tmp_path_factory):
    """Commit exact source bytes locally; no upstream identity or execution claim."""
    f=handoff_case;root=tmp_path_factory.mktemp('handoff-source')/'repo';root.mkdir()
    for name,raw in {**f['source'],**f['extra']}.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    env={'PATH':'/usr/bin:/bin','HOME':str(root),'LANG':'C.UTF-8','GIT_CONFIG_NOSYSTEM':'1',
         'GIT_CONFIG_GLOBAL':'/dev/null','GIT_AUTHOR_NAME':'Synthetic test',
         'GIT_AUTHOR_EMAIL':'test@example.invalid','GIT_COMMITTER_NAME':'Synthetic test',
         'GIT_COMMITTER_EMAIL':'test@example.invalid','GIT_AUTHOR_DATE':'2026-11-01T00:00:00Z',
         'GIT_COMMITTER_DATE':'2026-11-01T00:00:00Z'}
    for args in (['init','-q'],['add','.'],['commit','-q','-m','Synthetic handoff test only']):
        result=subprocess.run(['/usr/bin/git','-c','core.hooksPath=/dev/null','-C',str(root),*args],
                              env=env,capture_output=True,timeout=30)
        assert result.returncode==0,result.stderr
    commit=subprocess.check_output(['/usr/bin/git','-C',str(root),'rev-parse','HEAD'],env=env,timeout=10).decode().strip()
    native=copy.deepcopy(f['nr']);native['source_commit']=commit;nb=f['c'].encode(native)
    selection=f['a'].encode(f['s'])
    h=handoff_module(root)
    envelope=h.build_request(root,commit,nb,h.digest(nb),selection,h.digest(selection),h.AUTHORIZATION)
    return root,commit,native,nb,selection,envelope


def guarded_test_entry(root,commit,monkeypatch):
    import types
    a=native_mod(root,'acquire_q3_reference_inputs_v0')
    monkeypatch.setattr(a,'sys',types.SimpleNamespace(flags=types.SimpleNamespace(isolated=1)))
    monkeypatch.setattr(a.os,'geteuid',lambda:0)
    env={'GITHUB_REPOSITORY':M.REPOSITORY,'GITHUB_EVENT_NAME':'workflow_dispatch',
         'GITHUB_REF':'refs/heads/main','GITHUB_ACTOR':'HKati','GITHUB_TRIGGERING_ACTOR':'HKati',
         'GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':commit,'GITHUB_WORKFLOW_SHA':commit,
         'GITHUB_WORKFLOW_REF':M.REPOSITORY+'/'+M.WORKFLOW+'@refs/heads/main','GITHUB_RUN_ID':'90001'}
    return a,env


def test_handoff_actual_git_bound_entry_rejects_legacy_capture(handoff_checkout,monkeypatch):
    root,commit,native,nb,_,_=handoff_checkout;a,env=guarded_test_entry(root,commit,monkeypatch)
    monkeypatch.setattr(a,'api_bytes',lambda *args:pytest.fail('network before admission'))
    with pytest.raises(ValueError,match='CAPTURE_HANDOFF_REQUIRED'):
        a.entry_guard(root,commit,nb,M.digest(nb),env)


@pytest.mark.parametrize('mode',['token-preflight','capture'])
def test_handoff_actual_git_bound_entry_preserves_preflight_and_accepts_envelope(handoff_checkout,monkeypatch,mode):
    root,commit,native,nb,_,envelope=handoff_checkout;a,env=guarded_test_entry(root,commit,monkeypatch)
    if mode=='token-preflight':
        c=native_mod(root,'q3_native_capture_contract_v0');r=copy.deepcopy(native)
        r.update(mode=mode,approved_token_map_sha256=None,authorization=c.AUTHORIZATIONS[mode]);raw=c.encode(r)
    else:raw=envelope
    c,p,r,source=a.entry_guard(root,commit,raw,M.digest(raw),env)
    assert r['mode']==mode and r['source_commit']==commit and len(source)==21


def test_handoff_actual_entry_invalid_envelope_never_reaches_network(handoff_checkout,monkeypatch):
    root,commit,_,_,_,envelope=handoff_checkout;a,env=guarded_test_entry(root,commit,monkeypatch)
    e=json.loads(envelope);e['authorization']='not-authorized';raw=M.encode(e)
    c,p,r,source=a.entry_guard(root,commit,raw,M.digest(raw),env)
    monkeypatch.setattr(a,'control_plane',lambda *args:pytest.fail('network before authorization'))
    monkeypatch.setattr(a,'execute',lambda *args:pytest.fail('native before authorization'))
    with pytest.raises(ValueError,match='HANDOFF_AUTHORIZATION'):
        a.execute_handoff(c,p,r,source,root,raw,env)


def test_handoff_builder_cli_only_constructs_exact_request(handoff_checkout,tmp_path):
    root,commit,_,nb,selection,envelope=handoff_checkout;h=handoff_module(root)
    (tmp_path/'native.json').write_bytes(nb);(tmp_path/'selection.json').write_bytes(selection)
    command=[sys.executable,'-I','-B',str(root/h.SELF),'build-request','--repo-root',str(root),
        '--source-commit',commit,'--native-request',str(tmp_path/'native.json'),
        '--native-request-sha256',h.digest(nb),'--selection',str(tmp_path/'selection.json'),
        '--selection-sha256',h.digest(selection),'--authorization',h.AUTHORIZATION]
    done=subprocess.run(command,capture_output=True,timeout=30)
    assert done.returncode==0 and done.stdout==envelope and done.stderr==b''
    assert set(p.name for p in tmp_path.iterdir())=={'native.json','selection.json'}
    command[command.index('--authorization')+1]='NO'
    rejected=subprocess.run(command,capture_output=True,timeout=30)
    assert rejected.returncode==2 and rejected.stdout==b'' and b'Traceback' not in rejected.stderr


@pytest.mark.parametrize('name',['tools/q3_capture_handoff_v1.py',
    'schemas/metrics/q3_capture_handoff_request_v1.schema.json'])
def test_handoff_loader_rejects_dirty_additional_sources_before_network(handoff_checkout,monkeypatch,name):
    root,commit,_,_,_,envelope=handoff_checkout;a,env=guarded_test_entry(root,commit,monkeypatch)
    c,p,r,source=a.entry_guard(root,commit,envelope,M.digest(envelope),env)
    path=root/name;original=path.read_bytes()
    monkeypatch.setattr(a,'control_plane',lambda *args:pytest.fail('network from dirty closure'))
    monkeypatch.setattr(a,'execute',lambda *args:pytest.fail('native from dirty closure'))
    try:
        path.write_bytes(original+b'\n')
        with pytest.raises(ValueError):a.execute_handoff(c,p,r,source,root,envelope,env)
    finally:path.write_bytes(original)


@pytest.mark.parametrize('field,value',[('metadata_recheck','CHANGED'),('acquirer_sha256','f'*64),
    ('comparator_sha256','f'*64),('api_version','2099-01-01'),('saved_record_authenticates_origin',True),
    ('transport_trust','self_asserted'),('started_at','2099-01-01T00:00:00Z'),
    ('completed_at','2000-01-01T00:00:00Z'),('transfers',[]),('extra',True)])
def test_handoff_saved_acquisition_claims_are_not_trusted_after_rehash(handoff_case,handoff_complete_bytes,field,value):
    f=handoff_case;h=f['h'];d=h.unzip(handoff_complete_bytes)
    ar=json.loads(d['postflight/acquisition.json']);ar[field]=value;d['postflight/acquisition.json']=M.encode(ar)
    inv=json.loads(d['postflight/inventory.json']);body=d['postflight/acquisition.json']
    inv['files']['acquisition.json']={'sha256':M.digest(body),'size_bytes':len(body)}
    d['postflight/inventory.json']=M.encode(inv);raw=rebind_handoff_bundle(h,d)
    with pytest.raises((ValueError,KeyError,TypeError)):
        h.check(raw,h.digest(raw),h.digest(h.encode(f['envelope'])),'c'*40,'90001',ROOT,f['extra'])


@pytest.mark.parametrize('field,value',[('endpoint','/unselected'),('sha256','f'*64),
    ('size_bytes',True),('download_host','evil.invalid')])
def test_handoff_transfer_bindings_survive_rehash(handoff_case,handoff_complete_bytes,field,value):
    f=handoff_case;h=f['h'];d=h.unzip(handoff_complete_bytes);ar=json.loads(d['postflight/acquisition.json'])
    ar['transfers'][4][field]=value;d['postflight/acquisition.json']=M.encode(ar)
    inv=json.loads(d['postflight/inventory.json']);body=d['postflight/acquisition.json']
    inv['files']['acquisition.json']={'sha256':M.digest(body),'size_bytes':len(body)}
    d['postflight/inventory.json']=M.encode(inv);raw=rebind_handoff_bundle(h,d)
    with pytest.raises(ValueError):h.check(raw,h.digest(raw),h.digest(h.encode(f['envelope'])),'c'*40,'90001',ROOT,f['extra'])


@pytest.mark.parametrize('fault',['missing_network_token','final_replay','stage_cleanup'])
def test_handoff_operational_failures_never_publish_complete(handoff_case,tmp_path,monkeypatch,fault):
    h,rc,out,calls,reads,rt=hrun(handoff_case,tmp_path,monkeypatch,fault=fault)
    assert rc!=0 and json.loads((out/'receipt.json').read_bytes())['status']!='complete'
    assert (out/'failure.json').exists()
    if fault=='missing_network_token':assert not calls
    else:assert len(calls)==1


@pytest.mark.parametrize('fault',['preexisting','write','readback','custody'])
def test_handoff_publication_cannot_overwrite_or_leave_success(handoff_case,handoff_complete_bytes,tmp_path,monkeypatch,fault):
    f=handoff_case;h=f['h'];out=tmp_path/'out';out.mkdir();record=json.loads(h.unzip(handoff_complete_bytes)['bundle.json'])
    receipt={'record_type':'synthetic_test_receipt'};c=native_mod(ROOT,'q3_native_capture_contract_v0')
    if fault=='preexisting':(out/'evidence.zip').write_bytes(b'preserve-existing')
    elif fault=='write':
        original=c.write_new
        def write(path,raw,*args):
            if path.name=='receipt.json':raise OSError('injected write failure')
            return original(path,raw,*args)
        monkeypatch.setattr(c,'write_new',write)
    elif fault=='readback':
        original=c.safe_read
        def read(path,*args):
            raw=original(path,*args)
            return raw+b'x' if path.name=='receipt.json' and (out/'receipt.json').exists() else raw
        monkeypatch.setattr(c,'safe_read',read)
    else:monkeypatch.setattr(h.os,'fchown',lambda *args:(_ for _ in ()).throw(OSError('injected custody failure')))
    with pytest.raises((OSError,ValueError)):
        h.final_write(c,out,os.getuid(),os.getgid(),handoff_complete_bytes,record,receipt)
    assert not (out/'receipt.json').exists()
    if fault=='preexisting':assert (out/'evidence.zip').read_bytes()==b'preserve-existing'


@pytest.mark.parametrize('name',['../escape','/absolute','native/../../escape','native\\escape','a//b','a/./b'])
def test_handoff_archive_paths_reject_before_use(name):
    h=handoff_module();buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        i=zipfile.ZipInfo(name);i.external_attr=(0o100000|0o600)<<16;z.writestr(i,b'{}')
    with pytest.raises(ValueError):h.unzip(buf.getvalue())


def test_handoff_manifest_counts_remain_174_and_30():
    for filename,count in [('tools-tests.list',174),('pytest-tests.list',30)]:
        rows=[line.split('#',1)[0].strip() for line in (ROOT/'ci'/filename).read_text().splitlines()]
        rows=[r for r in rows if r]
        assert len(rows)==len(set(rows))==count and rows.count(TEST_PATH)==1



# Runner-image guard: source-bound synthetic controls, never hosted observations.
@pytest.fixture
def image_case(tmp_path, monkeypatch):
    a = native_mod(ROOT, 'acquire_q3_reference_inputs_v0')
    c = native_mod(ROOT, 'q3_native_capture_contract_v0')
    raw = b'{"synthetic":"image guard only"}'
    env = {'GITHUB_RUN_ID': '90123', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_JOB': 'acquire',
           'RUNNER_TEMP': str(tmp_path), 'ImageOS': 'ubuntu24', 'ImageVersion': '20261026.354.1',
           'GITHUB_TOKEN': 'DO_NOT_PUBLISH_SECRET'}
    source = {a.SELF: (ROOT / a.SELF).read_bytes()}
    request = {'source_commit': 'c'*40, 'mode': 'token-preflight'}
    observed = {'environment': {'image_os': 'ubuntu24', 'image_version': '20261026.354.1'},
        'worker': {'pid': 123, 'start_ticks': 456, 'executable': '/synthetic/runner/bin/Runner.Worker'},
        'setup_info': {'sha256': 'a'*64, 'size_bytes': 123, 'image': 'ubuntu-24.04',
                       'version': '20261026.354.1', 'error': None},
        'imagedata': {'sha256': 'b'*64, 'size_bytes': 100, 'image': 'ubuntu-24.04',
                      'version': '20261026.354.1', 'error': None}, 'errors': []}
    monkeypatch.setattr(a, 'image_collect', lambda *args: copy.deepcopy(observed))
    return a, c, request, source, raw, env, observed


def image_records(f):
    a,c,req,src,raw,env,_ = f
    records = {}
    for phase in a.IMAGE_STAGES:
        record, directory = a.image_observe(c,req,src,raw,env,phase)
        records[phase] = (directory/(phase+'.json')).read_bytes()
    return records


def image_rechain(a,c,records):
    previous = None
    for phase in a.IMAGE_STAGES:
        r=json.loads(records[phase]);r['previous_sha256']=previous
        records[phase]=c.encode(r);previous=c.digest(records[phase])


def test_image_positive_chain_is_not_saved_capture_permission(image_case):
    a,c,req,src,raw,env,_=image_case
    records=image_records(image_case)
    out=a.image_compare(c,records,a.image_binding(c,req,raw,env),c.digest(src[a.SELF]))
    assert out['status']=='consistent'
    assert out['capture_handoff_approved'] is False and out['authority_effect']=='none'
    assert out['native_execution_started_at_comparison'] is False
    assert b'DO_NOT_PUBLISH_SECRET' not in b''.join(records.values())


@pytest.mark.parametrize('phase',['initial','pre-sudo','root-entry'])
@pytest.mark.parametrize('field',['environment','setup_info','imagedata'])
def test_image_conflicting_source_rejects_without_rewriting(image_case,phase,field):
    a,c,req,src,raw,env,_=image_case;records=image_records(image_case)
    r=json.loads(records[phase]);key='image_version' if field=='environment' else 'version'
    r['observation'][field][key]='20261025.353.1';records[phase]=c.encode(r)
    image_rechain(a,c,records);original=copy.deepcopy(records)
    out=a.image_compare(c,records,a.image_binding(c,req,raw,env),c.digest(src[a.SELF]))
    assert out['status']=='contradictory' and records==original
    assert phase+':IMAGE_VALUES' in out['conflicts']


@pytest.mark.parametrize('phase',['initial','pre-sudo','root-entry'])
@pytest.mark.parametrize('fault',['missing','extra','binding','bool_attempt','observer','chain','source_missing',
                                  'source_hash','bool_size','version','worker','errors','duplicate_json'])
def test_image_partial_or_rebound_records_never_pass(image_case,phase,fault):
    a,c,req,src,raw,env,_=image_case;records=image_records(image_case)
    r=json.loads(records[phase])
    if fault=='missing': records.pop(phase)
    elif fault=='extra':r['approved']=True
    elif fault=='binding':r['binding']['run_id']='99999'
    elif fault=='bool_attempt':r['binding']['run_attempt']=True
    elif fault=='observer':r['observer_sha256']='f'*64
    elif fault=='chain':r['previous_sha256']='f'*64
    elif fault=='source_missing':r['observation']['setup_info']=None
    elif fault=='source_hash':r['observation']['imagedata']['sha256']='invalid'
    elif fault=='bool_size':r['observation']['imagedata']['size_bytes']=True
    elif fault=='version':r['observation']['setup_info']['version']='invalid'
    elif fault=='worker':r['observation']['worker']['pid']=True
    elif fault=='errors':r['observation']['errors']=['MISSING']
    if fault not in ('missing','duplicate_json'):records[phase]=c.encode(r)
    if fault=='duplicate_json':records[phase]=records[phase].replace(b'{',b'{"phase":"wrong",',1)
    out=a.image_compare(c,records,a.image_binding(c,req,raw,env),c.digest(src[a.SELF]))
    assert out['status']=='incomplete'


@pytest.mark.parametrize('phase',['pre-sudo','root-entry'])
@pytest.mark.parametrize('field',['worker','setup_info','imagedata','all_versions'])
def test_image_same_job_temporal_drift_is_not_normalized(image_case,phase,field):
    a,c,req,src,raw,env,_=image_case;records=image_records(image_case)
    r=json.loads(records[phase]);o=r['observation']
    if field=='worker':o['worker']['start_ticks']+=1
    elif field=='all_versions':
        o['environment']['image_version']='20261027.355.1'
        for k in ('setup_info','imagedata'):o[k]['version']='20261027.355.1'
    else:o[field]['sha256']='f'*64
    records[phase]=c.encode(r);image_rechain(a,c,records)
    out=a.image_compare(c,records,a.image_binding(c,req,raw,env),c.digest(src[a.SELF]))
    assert out['status']=='contradictory'


@pytest.mark.parametrize('fault',['missing','duplicate_group','bad_group','duplicate_key','ambiguous_alias',
    'empty_version','duplicate_version','malformed_duplicate','indented_duplicate','wrong_type','bad_version'])
def test_image_metadata_parser_fails_closed(fault):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0');c=native_mod(ROOT,'q3_native_capture_contract_v0')
    group={'group':'Runner Image','detail':'Image: ubuntu-24.04\nVersion: 20261026.354.1'};d=[group]
    if fault=='missing':d=[]
    elif fault=='duplicate_group':d.append(dict(group))
    elif fault=='bad_group':group['group']='Runner Image Provisioner'
    elif fault=='ambiguous_alias':group['Group']='Runner Image'
    elif fault=='empty_version':group['detail']='Image: ubuntu-24.04\nVersion: '
    elif fault=='duplicate_version':group['detail']+='\nVersion: 20261026.354.1'
    elif fault=='malformed_duplicate':group['detail']+='\nVersion: invalid'
    elif fault=='indented_duplicate':group['detail']+='\n  Version: invalid'
    elif fault=='wrong_type':group['detail']=True
    elif fault=='bad_version':group['detail']='Image: ubuntu-24.04\nVersion: invalid'
    raw=c.encode(d)
    if fault=='duplicate_key':raw=raw.replace(b'"group":',b'"group":"other","group":')
    with pytest.raises(ValueError):a.image_group(c,raw)


@pytest.mark.parametrize('capitalized',[False,True])
def test_image_parser_excludes_provisioner_and_private_groups(capitalized):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0');c=native_mod(ROOT,'q3_native_capture_contract_v0')
    d=[{'group':'_internal_private','detail':'DO_NOT_PUBLISH'},
       {'group':'Runner Image Provisioner','detail':'Version: 999'},
       {'group':'Runner Image','detail':'Image: ubuntu-24.04\r\nVersion: 20261026.354.1\r\nIncluded Software: private'}]
    if capitalized:d=[{k.capitalize():v for k,v in x.items()} for x in d]
    assert a.image_group(c,c.encode(d))=={'image':'ubuntu-24.04','version':'20261026.354.1'}


@pytest.mark.parametrize('value',[None,'','secret\nvalue','::error::secret','X'*129,True])
def test_image_bad_environment_values_are_not_published(value):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0')
    out,valid=a.image_environment({'ImageOS':'ubuntu24','ImageVersion':value,'GITHUB_TOKEN':'secret'})
    assert not valid and out=={'image_os':'ubuntu24','image_version':None}


def test_image_source_read_does_not_publish_other_metadata(tmp_path):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0');c=native_mod(ROOT,'q3_native_capture_contract_v0')
    p=tmp_path/'setup';raw=c.encode([{'group':'Runner Image','detail':'Image: ubuntu-24.04\nVersion: 20261026.354.1'},
                                  {'group':'_internal_token','detail':'DO_NOT_PUBLISH_SECRET'}]);p.write_bytes(raw)
    r=a.image_source(c,p)
    assert r['sha256']==c.digest(raw) and r['error'] is None
    assert b'DO_NOT_PUBLISH_SECRET' not in c.encode(r)


@pytest.mark.parametrize('kind',['symlink','parent_symlink','hardlink','fifo','missing','oversize'])
def test_image_source_unreadable_or_aliased_stays_incomplete(tmp_path,kind):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0');c=native_mod(ROOT,'q3_native_capture_contract_v0')
    p=tmp_path/'metadata';p.write_bytes(b'[]')
    if kind=='symlink':q=tmp_path/'link';q.symlink_to(p);p=q
    elif kind=='parent_symlink':q=tmp_path/'dirlink';q.symlink_to(tmp_path);p=q/'metadata'
    elif kind=='hardlink':os.link(p,tmp_path/'alias')
    elif kind=='fifo':p.unlink();os.mkfifo(p)
    elif kind=='missing':p.unlink()
    else:p.write_bytes(b'x'*(a.IMAGE_MAX+1))
    assert a.image_source(c,p)['error'] is not None


def fake_image_proc(tmp_path):
    proc=tmp_path/'proc';root=tmp_path/'runner';(root/'bin').mkdir(parents=True)
    worker=root/'bin/Runner.Worker';worker.write_bytes(b'not executable synthetic worker')
    shell=tmp_path/'shell';shell.write_bytes(b'not executable synthetic shell')
    for pid,parent,ticks,path in [(22,11,200,shell),(11,1,100,worker)]:
        d=proc/str(pid);d.mkdir(parents=True)
        # State is field 3, PPID field 4, starttime field 22.
        tail=['S',str(parent)]+['0']*17+[str(ticks)]
        (d/'stat').write_text(str(pid)+' (name with ) parentheses) '+' '.join(tail)+'\n')
        (d/'exe').symlink_to(path)
    return proc,root


def test_image_actual_proc_parser_selects_ancestor_not_cache(tmp_path):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0');proc,root=fake_image_proc(tmp_path)
    identity,selected=a.image_worker(proc,22)
    assert selected==root and identity['pid']==11 and identity['start_ticks']==100


@pytest.mark.parametrize('fault',['no_worker','stat_malformed','pid_cycle','exe_missing','wrong_bin'])
def test_image_ambiguous_or_unreadable_worker_has_no_fallback(tmp_path,fault):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0');proc,root=fake_image_proc(tmp_path)
    if fault=='no_worker':(proc/'11/exe').unlink();(proc/'11/exe').symlink_to(tmp_path/'shell')
    elif fault=='stat_malformed':(proc/'11/stat').write_bytes(b'bad')
    elif fault=='pid_cycle':(proc/'22/stat').write_text('22 (shell) '+' '.join(['S','22']+['0']*17+['200']))
    elif fault=='exe_missing':(proc/'22/exe').unlink()
    else:
        p=tmp_path/'wrong/Runner.Worker';p.parent.mkdir();p.write_bytes(b'fake')
        (proc/'11/exe').unlink();(proc/'11/exe').symlink_to(p)
    with pytest.raises((ValueError,OSError)):a.image_worker(proc,22)


def test_image_initial_observation_does_not_overwrite(image_case):
    a,c,req,src,raw,env,_=image_case
    a.image_observe(c,req,src,raw,env,'initial')
    directory=Path(env['RUNNER_TEMP'])/'q3-runner-image/90123-1'
    original=(directory/'initial.json').read_bytes()
    with pytest.raises(FileExistsError):a.image_observe(c,req,src,raw,env,'initial')
    assert (directory/'initial.json').read_bytes()==original


@pytest.mark.parametrize('mode',['token-preflight','capture'])
@pytest.mark.parametrize('fault',['conflict','missing','sudo_drift'])
def test_image_actual_gate_stops_main_before_any_native_route(image_case,monkeypatch,mode,fault):
    a,c,req,src,raw,env,observed=image_case;req['mode']=mode
    a.image_observe(c,req,src,raw,env,'initial')
    if fault!='missing':a.image_observe(c,req,src,raw,env,'pre-sudo')
    if fault=='conflict':observed['setup_info']['version']='20261025.353.1'
    elif fault=='sudo_drift':observed['environment']['image_version']='20261027.355.1'
    monkeypatch.setattr(a,'entry_guard',lambda *args,**kwargs:(c,{},req,src))
    for k,v in env.items():monkeypatch.setenv(k,v)
    monkeypatch.setattr(a,'execute',lambda *args:pytest.fail('native call on rejected image'))
    monkeypatch.setattr(a,'execute_handoff',lambda *args:pytest.fail('handoff on rejected image'))
    assert a.main(['--repo-root',str(ROOT),'--source-commit',req['source_commit'],'--request',raw.decode(),
                   '--request-sha256',c.digest(raw)])==2
    d=Path(env['RUNNER_TEMP'])/'q3-runner-image/90123-1'
    report=json.loads((d/'comparison.json').read_bytes())
    assert report['status']==('incomplete' if fault=='missing' else 'contradictory')
    assert report['native_execution_started_at_comparison'] is False
    assert b'DO_NOT_PUBLISH_SECRET' not in b''.join(p.read_bytes() for p in d.glob('*.json'))
    assert (d/'root-entry.json').stat().st_mode&0o777==0o644


@pytest.mark.parametrize('mode',['token-preflight','capture'])
def test_image_positive_main_checks_real_gate_before_route(image_case,monkeypatch,mode):
    a,c,req,src,raw,env,_=image_case;req['mode']=mode
    for phase in ('initial','pre-sudo'):a.image_observe(c,req,src,raw,env,phase)
    monkeypatch.setattr(a,'entry_guard',lambda *args,**kwargs:(c,{},req,src))
    for k,v in env.items():monkeypatch.setenv(k,v)
    calls=[]
    def native(*args):
        report=json.loads((Path(env['RUNNER_TEMP'])/'q3-runner-image/90123-1/comparison.json').read_bytes())
        assert report['status']=='consistent';calls.append(mode);return 0
    monkeypatch.setattr(a,'execute',native);monkeypatch.setattr(a,'execute_handoff',native)
    assert a.main(['--repo-root',str(ROOT),'--source-commit',req['source_commit'],'--request',raw.decode(),
                   '--request-sha256',c.digest(raw)])==0
    assert calls==[mode]


def test_image_observation_cli_requires_real_source_and_cannot_execute(handoff_checkout,monkeypatch,tmp_path):
    root,commit,_,_,_,_=handoff_checkout;c=native_mod(root,'q3_native_capture_contract_v0');a=native_mod(root,'acquire_q3_reference_inputs_v0')
    request_raw=c.make_request(root,commit,'token-preflight',c.AUTHORIZATIONS['token-preflight'])
    _,env=guarded_test_entry(root,commit,monkeypatch)
    env.update(GITHUB_JOB='acquire',RUNNER_TEMP=str(tmp_path))
    for k,v in env.items():monkeypatch.setenv(k,v)
    import types
    monkeypatch.setattr(a,'sys',types.SimpleNamespace(flags=types.SimpleNamespace(isolated=1),stderr=sys.stderr))
    monkeypatch.setattr(a.os,'geteuid',lambda:1001)
    monkeypatch.setattr(a,'image_collect',lambda *args:{'environment':{'image_os':None,'image_version':None},
        'worker':None,'setup_info':None,'imagedata':None,'errors':['SYNTHETIC_MISSING']})
    monkeypatch.setattr(a,'execute',lambda *args:pytest.fail('observation dispatched native'))
    monkeypatch.setattr(a,'execute_handoff',lambda *args:pytest.fail('observation dispatched handoff'))
    argv=['--repo-root',str(root),'--source-commit',commit,'--request',request_raw.decode(),
          '--request-sha256',c.digest(request_raw),'--image-observation','initial']
    assert a.main(argv)==0
    record=json.loads((tmp_path/'q3-runner-image'/ (env['GITHUB_RUN_ID']+'-1')/'initial.json').read_bytes())
    assert record['observer_sha256']==c.digest((root/a.SELF).read_bytes())
    assert record['binding']['source_commit']==commit


def test_image_workflow_observes_before_python_and_on_both_sides_of_sudo():
    import yaml
    workflow=yaml.load((ROOT/M.WORKFLOW).read_bytes(),Loader=yaml.BaseLoader)
    steps=workflow['jobs']['acquire']['steps']
    initial=next(i for i,s in enumerate(steps) if s.get('id')=='image_initial')
    setup=next(i for i,s in enumerate(steps) if s.get('uses','').startswith('actions/setup-python@'))
    native=next(s for s in steps if s.get('id')=='native')['run']
    assert initial<setup and '--image-observation initial' in steps[initial]['run']
    assert native.index('--image-observation pre-sudo')<native.index('sudo --preserve-env=')
    assert 'GITHUB_RUN_ID,GITHUB_JOB,GITHUB_TOKEN' in native
    main=ast.get_source_segment((ROOT/NATIVE_COLLECTOR).read_text(),
          next(n for n in ast.parse((ROOT/NATIVE_COLLECTOR).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main'))
    assert main.index('image_gate(')<main.index('return execute_handoff(')<main.index('return execute(')
    assert 'continue-on-error' not in json.dumps(workflow)


def test_image_separate_artifact_has_closed_non_secret_members():
    import yaml
    workflow=yaml.load((ROOT/M.WORKFLOW).read_bytes(),Loader=yaml.BaseLoader)
    uploads=[s for s in workflow['jobs']['acquire']['steps'] if s.get('uses','').startswith('actions/upload-artifact@')]
    side=next(s for s in uploads if s['with']['name'].startswith('q3-runner-image-'))
    assert len(uploads)==2 and side['with']['overwrite']=='false' and side['with']['retention-days']=='30'
    assert side['if']=="failure() && steps.image_initial.outcome != 'skipped'"
    assert [p.rsplit('/',1)[-1] for p in side['with']['path'].splitlines()]==list(native_mod(ROOT,'acquire_q3_reference_inputs_v0').IMAGE_FILES)
    for forbidden in ['**','*.json','.setup_info','imagedata.json','.credentials']:
        assert forbidden not in side['with']['path']




@pytest.mark.parametrize('mode',['token-preflight','capture'])
def test_image_actual_git_entry_refuses_missing_observation_before_network(handoff_checkout,monkeypatch,tmp_path,mode):
    root,commit,native,nb,_,envelope=handoff_checkout
    c=native_mod(root,'q3_native_capture_contract_v0')
    a,env=guarded_test_entry(root,commit,monkeypatch)
    import types
    monkeypatch.setattr(a,'sys',types.SimpleNamespace(flags=types.SimpleNamespace(isolated=1),stderr=sys.stderr))
    env.update(GITHUB_JOB='acquire',RUNNER_TEMP=str(tmp_path))
    for k,v in env.items():monkeypatch.setenv(k,v)
    raw=(c.make_request(root,commit,mode,c.AUTHORIZATIONS[mode]) if mode=='token-preflight' else envelope)
    monkeypatch.setattr(a,'image_collect',lambda *args:{'environment':{'image_os':None,'image_version':None},
        'worker':None,'setup_info':None,'imagedata':None,'errors':['SYNTHETIC_UNAVAILABLE']})
    monkeypatch.setattr(a,'api_bytes',lambda *args:pytest.fail('network before image admission'))
    monkeypatch.setattr(a,'execute',lambda *args:pytest.fail('native before image admission'))
    monkeypatch.setattr(a,'execute_handoff',lambda *args:pytest.fail('capture before image admission'))
    assert a.main(['--repo-root',str(root),'--source-commit',commit,'--request',raw.decode(),
                   '--request-sha256',c.digest(raw)])==2
    report=json.loads((tmp_path/'q3-runner-image'/ (env['GITHUB_RUN_ID']+'-1')/'comparison.json').read_bytes())
    assert report['status']=='incomplete' and report['binding']['source_commit']==commit


def test_image_observation_log_keeps_existing_postflight_and_single_artifact_contract(historical):
    e,raw=equal_image_case(historical)
    # Explicit synthetic log-format control, not an observed guard execution.
    marker=b'2026-10-26T00:00:00Z Q3_RUNNER_IMAGE_COMPARISON {"synthetic":true,"authority_effect":"none"}\n'
    raw['job.log']+=marker;repin(e,raw)
    assert run(e,raw)['disposition']=='CONSISTENT_OFFLINE'
    raw['job.log']+=b'2026-10-26T00:00:00Z SHA256 digest of uploaded artifact is '+b'a'*64+b'\n'
    repin(e,raw)
    with pytest.raises(ValueError,match='LOG_ARTIFACT_DIGEST'):run(e,raw)


def test_image_collect_uses_live_worker_and_never_environment_file_override(monkeypatch):
    a=native_mod(ROOT,'acquire_q3_reference_inputs_v0');c=native_mod(ROOT,'q3_native_capture_contract_v0')
    worker={'pid':123,'start_ticks':456,'executable':'/fixed/runner/bin/Runner.Worker'};seen=[]
    monkeypatch.setattr(a,'image_worker',lambda:(worker,Path('/fixed/runner')))
    def read(path,limit):
        seen.append(str(path));assert limit==a.IMAGE_MAX
        return c.encode([{'group':'Runner Image','detail':'Image: ubuntu-24.04\nVersion: 20261026.354.1'}])
    monkeypatch.setattr(c,'safe_read',read)
    observation=a.image_collect(c,{'ImageOS':'ubuntu24','ImageVersion':'20261026.354.1',
                                  'SETUP_INFO':'/evil','GITHUB_TOKEN':'DO_NOT_PUBLISH'})
    assert seen==['/fixed/runner/.setup_info','/imagegeneration/imagedata.json']
    assert observation['errors']==[] and 'DO_NOT_PUBLISH' not in c.encode(observation).decode()




@pytest.mark.parametrize('fault',['comparison_exists','write_failure','output_symlink'])
def test_image_gate_output_failure_never_reaches_native(image_case,monkeypatch,fault):
    a,c,req,src,raw,env,_=image_case
    for phase in ('initial','pre-sudo'):a.image_observe(c,req,src,raw,env,phase)
    directory=Path(env['RUNNER_TEMP'])/'q3-runner-image/90123-1'
    if fault=='comparison_exists':(directory/'comparison.json').write_bytes(b'original')
    elif fault=='write_failure':monkeypatch.setattr(c,'write_new',lambda *a,**k:(_ for _ in ()).throw(OSError('synthetic')))
    else:
        moved=directory.with_name('held');directory.rename(moved);directory.symlink_to(moved)
    monkeypatch.setattr(a,'entry_guard',lambda *args,**kwargs:(c,{},req,src))
    for k,v in env.items():monkeypatch.setenv(k,v)
    monkeypatch.setattr(a,'execute',lambda *args:pytest.fail('native despite preservation failure'))
    monkeypatch.setattr(a,'execute_handoff',lambda *args:pytest.fail('handoff despite preservation failure'))
    assert a.main(['--repo-root',str(ROOT),'--source-commit',req['source_commit'],'--request',raw.decode(),
                   '--request-sha256',c.digest(raw)])==2
    if fault=='comparison_exists':assert (directory/'comparison.json').read_bytes()==b'original'


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__,'-q']))
