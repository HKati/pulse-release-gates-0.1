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


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__,'-q']))
