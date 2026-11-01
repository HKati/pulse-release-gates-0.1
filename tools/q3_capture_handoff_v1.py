#!/usr/bin/env python3
"""Mandatory Q3 capture admission envelope, live handoff and offline replay.

The native controller is the only execution entry. This CLI builds requests or
checks retained carriers; neither subcommand executes a model or dispatches CI.
Historical native-v0 readers and both postflight-v0 components are unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import zipfile

REPOSITORY = 'HKati/pulse-release-gates-0.1'
WORKFLOW = '.github/workflows/q3_reference_acquisition_v0.yml'
SELF = 'tools/q3_capture_handoff_v1.py'
SCHEMA = 'schemas/metrics/q3_capture_handoff_request_v1.schema.json'
ACQUIRER = 'tools/acquire_q3_external_postflight_v0.py'
COMPARATOR = 'tools/check_q3_external_postflight_v0.py'
CONTRACT = 'PULSE_safe_pack_v0/tools/q3_native_capture_contract_v0.py'
EXTRA_SOURCES = tuple(sorted((SELF, SCHEMA, ACQUIRER, COMPARATOR)))
ACQUIRER_SHA = '35b875e6885f56cfe601ae27c92f9acd98e8ddc8805aaeb498157ff7b04e7065'
COMPARATOR_SHA = 'a0bbeb20ae368992883747277946f78a4926ffd71a276756ee611a81a047d16b'
AUTHORIZATION = 'AUTHORIZE_ONE_OWNER_CAPTURE_DISPATCH_WITH_FRESH_POSTFLIGHT_AND_30_DAY_RETENTION'
REQUEST_TYPE = 'q3_capture_handoff_request_v1'
REQUEST_FIELDS = {'record_type', 'repository', 'capture_source_commit',
    'native_request_utf8', 'native_request_sha256', 'postflight_selection_utf8',
    'postflight_selection_sha256', 'handoff_source_files', 'authorization'}
MAX_REQUEST = 128 * 1024
MAX_BUNDLE = 384 * 1024**2
MAX_FILES = 96
CLAIMS = {'authority_effect': 'none', 'production_gate_eligible': False,
    'current_run_evidence': False, 'policy_activation': False,
    'metric_evaluated': False, 'saved_record_authenticates_origin': False,
    'verifier_execution_attested': False, 'artifact_attempt_attestation': None}


class HandoffError(ValueError):
    """Stable error codes only; never interpolate provider responses or tokens."""


def require(value, code):
    if not value:
        raise HandoffError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def pin(raw):
    return {'sha256': digest(raw), 'git_blob_sha1': blob(raw), 'size_bytes': len(raw)}


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def fields(value, expected, code):
    require(type(value) is dict and set(value) == set(expected), code)


def sha(value, length=64):
    return type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}', value) is not None


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def compile_module(name, relative, source, root):
    module = types.ModuleType(name)
    module.__file__ = str(root / relative)
    exec(compile(source, module.__file__, 'exec', dont_inherit=True), module.__dict__)
    return module


def components(root, sources):
    fields(sources, EXTRA_SOURCES, 'HANDOFF_SOURCE_SET')
    require(digest(sources[ACQUIRER]) == ACQUIRER_SHA, 'HANDOFF_ACQUIRER_VERSION')
    require(digest(sources[COMPARATOR]) == COMPARATOR_SHA, 'HANDOFF_COMPARATOR_VERSION')
    m = compile_module('q3_handoff_comparator', COMPARATOR, sources[COMPARATOR], root)
    a = compile_module('q3_handoff_acquirer', ACQUIRER, sources[ACQUIRER], root)
    return a, m


def native_contract(native_sources, root, m):
    require(CONTRACT in native_sources and
        digest(native_sources[CONTRACT]) == m.REVIEWED_CHECKERS[Path(CONTRACT).name],
        'HANDOFF_NATIVE_CONTRACT_VERSION')
    return compile_module('q3_handoff_native_contract', CONTRACT, native_sources[CONTRACT], root)


def validate(raw, expected_sha, native_raw, native_sources, extra_sources, root, a, m):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_REQUEST and sha(expected_sha)
            and digest(raw) == expected_sha, 'HANDOFF_REQUEST_DIGEST_OR_SIZE')
    e = m.strict_json(raw)
    fields(e, REQUEST_FIELDS, 'HANDOFF_REQUEST_FIELDS')
    require(e['record_type'] == REQUEST_TYPE and e['repository'] == REPOSITORY
            and e['authorization'] == AUTHORIZATION, 'HANDOFF_AUTHORIZATION')
    require(sha(e['capture_source_commit'], 40), 'HANDOFF_CAPTURE_SOURCE')
    require(type(e['native_request_utf8']) is str and type(e['postflight_selection_utf8']) is str,
            'HANDOFF_EMBEDDED_BYTES')
    nr = e['native_request_utf8'].encode('utf-8')
    sr = e['postflight_selection_utf8'].encode('utf-8')
    require(nr == native_raw and sha(e['native_request_sha256']) and
            digest(nr) == e['native_request_sha256'], 'HANDOFF_NATIVE_REQUEST')
    require(sha(e['postflight_selection_sha256']) and digest(sr) == e['postflight_selection_sha256'],
            'HANDOFF_SELECTION_DIGEST')
    fields(extra_sources, EXTRA_SOURCES, 'HANDOFF_SOURCE_SET')
    require(encode(e['handoff_source_files']) == encode({n: pin(b) for n,b in extra_sources.items()}),
            'HANDOFF_SOURCE_BINDING')
    require(digest(extra_sources[ACQUIRER]) == ACQUIRER_SHA and
            digest(extra_sources[COMPARATOR]) == COMPARATOR_SHA, 'HANDOFF_COMPONENT_VERSION')
    c = native_contract(native_sources, root, m)
    p = c.load_profile(native_sources)
    c.require(set(native_sources) == set(p['source_files']), 'SOURCE_SCOPE')
    c.task_frame(native_sources, p)
    r = c.validate_request(nr, p)
    require(r['mode'] == 'capture' and r['source_commit'] == e['capture_source_commit'],
            'HANDOFF_CAPTURE_REQUEST')
    s = a.select(sr, e['postflight_selection_sha256'], m)
    require(encode(s['source_files']) == encode({n: pin(b) for n,b in native_sources.items()}),
            'HANDOFF_NATIVE_SOURCE_COMPATIBILITY')
    require(r['approved_token_map_sha256'] == s['token_map_sha256'], 'HANDOFF_APPROVED_MAP')
    return e, r, s


def current_run(raw, run_id, source, preflight_id, m):
    r = m.strict_json(raw)
    require(type(r) is dict and type(r.get('id')) is int and str(r['id']) == run_id
            and run_id != preflight_id and type(r.get('run_attempt')) is int
            and r['run_attempt'] == 1 and r.get('head_sha') == source
            and r.get('head_branch') == 'main' and r.get('event') == 'workflow_dispatch'
            and r.get('status') == 'in_progress' and r.get('conclusion') is None
            and r.get('path') == WORKFLOW
            and r.get('actor',{}).get('login') == 'HKati'
            and r.get('triggering_actor',{}).get('login') == 'HKati', 'HANDOFF_CURRENT_RUN')
    return {'repository': REPOSITORY, 'workflow': WORKFLOW, 'run_id': run_id,
            'run_attempt': 1, 'source_commit': source, 'head_branch': 'main',
            'event': 'workflow_dispatch', 'actor': 'HKati', 'triggering_actor': 'HKati'}


def acquisition_receipt(a, s, selection_sha, result, comparison, reader, started):
    return {'record_type': 'q3_external_postflight_acquisition_v0',
        'status': 'complete', 'disposition': result['disposition'],
        'selection_sha256': selection_sha, 'comparison_sha256': digest(comparison),
        'acquirer_sha256': s['acquirer_sha256'], 'comparator_sha256': s['comparator_sha256'],
        'observation_channel': 'live_github_https_api_and_api_selected_storage',
        'transport_trust': 'local_tls_ca_store_and_github_service',
        'metadata_recheck': 'UNCHANGED', 'api_version': a.API_VERSION,
        'started_at': started, 'completed_at': now(), 'transfers': reader.transfers, **a.BOUNDARIES}


def admission(e, context, comparison):
    return {'record_type': 'q3_capture_admission_v1', 'decision': 'ADMIT_CURRENT_DISPATCH',
        'capture_context': context, 'native_request_sha256': e['native_request_sha256'],
        'postflight_selection_sha256': e['postflight_selection_sha256'],
        'comparison_sha256': digest(comparison),
        'origin_basis': 'fresh_verified_tls_acquisition_in_this_trusted_process',
        'reuse_of_saved_approval_allowed': False, **CLAIMS}


def safe_code(exc):
    value = str(exc)
    if isinstance(exc, ValueError) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,95}', value):
        return value
    return 'HANDOFF_OPERATION_INCOMPLETE'


def zip_bytes(data):
    require(len(data) <= MAX_FILES and sum(map(len,data.values())) <= MAX_BUNDLE, 'HANDOFF_BUNDLE_BOUND')
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED) as z:
        for n,b in sorted(data.items()):
            require(type(n) is str and not n.startswith('/') and '\\' not in n
                    and all(x not in ('','..','.') for x in n.split('/')), 'HANDOFF_MEMBER_PATH')
            i = zipfile.ZipInfo(n, (1980,1,1,0,0,0)); i.external_attr = (stat.S_IFREG|0o600)<<16
            z.writestr(i,b)
    require(len(out.getvalue()) <= MAX_BUNDLE, 'HANDOFF_BUNDLE_BOUND')
    return out.getvalue()


def unzip(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BUNDLE, 'HANDOFF_ARCHIVE_BOUND')
    data = {}; total = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        require(0 < len(z.infolist()) <= MAX_FILES, 'HANDOFF_MEMBER_COUNT')
        for i in z.infolist():
            n=i.filename; mode=i.external_attr>>16
            require(n not in data and n and not n.startswith('/') and '\\' not in n
                and all(x not in ('','..','.') for x in n.split('/'))
                and stat.S_ISREG(mode) and stat.S_IMODE(mode)==0o600
                and not i.flag_bits&1 and i.compress_type==zipfile.ZIP_STORED,
                'HANDOFF_MEMBER_TYPE_OR_PATH')
            total+=i.file_size
            require(total<=MAX_BUNDLE and i.file_size<=MAX_BUNDLE, 'HANDOFF_MEMBER_BOUND')
            data[n]=z.read(i)
    return data


def bundle(data, e, context, status, error, staged_removed):
    require('bundle.json' not in data, 'HANDOFF_BUNDLE_RECURSION')
    b={'record_type':'q3_capture_handoff_bundle_v1','status':status,'error_code':error,
       'capture_context':context,'entry_request_sha256':digest(data['request.json']),
       'native_request_sha256':e['native_request_sha256'],
       'postflight_selection_sha256':e['postflight_selection_sha256'],
       'staging_removed':staged_removed,
       'inventory':{n:{'sha256':digest(v),'size_bytes':len(v)} for n,v in sorted(data.items())},**CLAIMS}
    return zip_bytes({**data,'bundle.json':encode(b)}),b


def verify_native(data, e, context, source, m):
    nr=e['native_request_utf8'].encode('utf-8')
    inner=data['native/evidence.zip']; receipt=m.strict_json(data['native/receipt.json'])
    fields(receipt, set('record_type status mode source_commit archive_sha256 archive_size_bytes '
        'request_sha256 token_map_sha256 result_sha256 claims'.split()), 'HANDOFF_NATIVE_RECEIPT_FIELDS')
    checked=m.native_replay(inner, source, {'request_sha256':digest(nr),
                                           'source_commit':e['capture_source_commit']})
    # Native checker validates the exact closed native archive, source, protocol,
    # cleanup and projection. Only metadata is read here; no archived code is run.
    with zipfile.ZipFile(io.BytesIO(inner)) as z:
        r=z.read('request.json'); result=z.read('result.json')
        pre=m.strict_json(z.read('control-plane.json'))
    require(r==nr and checked.get('mode')=='capture'
            and pre.get('run_id')==context['run_id']
            and type(pre.get('run_attempt')) is int and pre['run_attempt']==1
            and pre.get('source_commit')==e['capture_source_commit'], 'HANDOFF_NATIVE_EXECUTION_BINDING')
    expected={'record_type':'q3_native_capture_receipt_v0',
        'status':'complete' if checked['complete'] else 'incomplete','mode':'capture',
        'source_commit':e['capture_source_commit'],'archive_sha256':digest(inner),
        'archive_size_bytes':len(inner),'request_sha256':digest(nr),
        'token_map_sha256':checked.get('token_map_sha256'),
        'result_sha256':digest(result),'claims':checked['claims']}
    if checked['complete']:
        require(encode(receipt)==encode(expected), 'HANDOFF_NATIVE_RECEIPT_BINDING')
        require(receipt['token_map_sha256']==json.loads(e['native_request_utf8'])['approved_token_map_sha256'],
                'HANDOFF_NATIVE_MAP_BINDING')
    return checked


def check(raw, expected_sha, expected_request, expected_source, expected_run, root, extra_sources):
    require(sha(expected_sha) and digest(raw)==expected_sha, 'HANDOFF_ARCHIVE_DIGEST')
    require(sha(expected_request) and sha(expected_source,40) and type(expected_run) is str
        and re.fullmatch('[1-9][0-9]{0,18}', expected_run), 'HANDOFF_EXPECTATION')
    a,m=components(root,extra_sources)
    data=unzip(raw); b=m.strict_json(data['bundle.json'])
    fields(b, {'record_type','status','error_code','capture_context','entry_request_sha256',
        'native_request_sha256','postflight_selection_sha256','staging_removed','inventory',*CLAIMS},
        'HANDOFF_BUNDLE_FIELDS')
    require(b['record_type']=='q3_capture_handoff_bundle_v1' and
        b['status'] in ('complete','incomplete','rejected'), 'HANDOFF_BUNDLE_STATUS')
    require(all(encode(b[k])==encode(v) for k,v in CLAIMS.items()),'HANDOFF_CLAIMS')
    actual={n:{'sha256':digest(v),'size_bytes':len(v)} for n,v in data.items() if n!='bundle.json'}
    require(encode(actual)==encode(b['inventory']), 'HANDOFF_INVENTORY')
    require(digest(data['request.json'])==expected_request==b['entry_request_sha256'], 'HANDOFF_ENTRY_BINDING')
    src={n[len('capture-source/'):]:v for n,v in data.items() if n.startswith('capture-source/')}
    ex={n[len('handoff-source/'):]:v for n,v in data.items() if n.startswith('handoff-source/')}
    require(ex==extra_sources, 'HANDOFF_CHECKER_SOURCE_SELECTION')
    envelope=m.strict_json(data['request.json'])
    native_raw=envelope['native_request_utf8'].encode('utf-8')
    e,r,s=validate(data['request.json'],expected_request,native_raw,src,ex,root,a,m)
    require(e['capture_source_commit']==expected_source and
            b['capture_context']['run_id']==expected_run and
            b['capture_context']['source_commit']==expected_source,
            'HANDOFF_EXTERNAL_CONTEXT')
    require(b['native_request_sha256']==e['native_request_sha256'] and
            b['postflight_selection_sha256']==e['postflight_selection_sha256'], 'HANDOFF_ENVELOPE_BINDING')
    if b['status']!='complete':
        require(type(b['error_code']) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,95}',b['error_code']),
                'HANDOFF_FAILURE_CODE')
        return {'record_type':'q3_capture_handoff_check_v1','integrity_verified':True,
            'complete':False,'status':b['status'],'error_code':b['error_code'],
            'live_origin_reobserved':False,'new_execution_authorized':False,**CLAIMS}
    require(b['error_code'] is None and b['staging_removed'] is True, 'HANDOFF_COMPLETE_CLOSURE')
    raw_inputs={n:data['postflight/'+n] for n in m.INPUTS}
    expectation=data['postflight/expectation.json']; result=m.compare(expectation,digest(expectation),raw_inputs)
    comparison=m.encode(result)
    require(result['disposition']=='CONSISTENT_OFFLINE' and comparison==data['postflight/comparison.json'],
            'HANDOFF_COMPARISON_REPLAY')
    require(data['postflight/selection.json']==e['postflight_selection_utf8'].encode('utf-8') and
            expectation==m.encode(a.expectation(s,raw_inputs,m)), 'HANDOFF_POSTFLIGHT_SELECTION')
    for name in ('run.json','jobs.json','artifact.json'):
        require(m.encode(m.strict_json(data['postflight/'+name]))==
                m.encode(m.strict_json(data['postflight/'+name.replace('.json','.after.json')])),
                'HANDOFF_POSTFLIGHT_METADATA_CHANGED')
    ctx=current_run(data['capture-run.before.json'],expected_run,expected_source,s['run_id'],m)
    require(ctx==current_run(data['capture-run.after.json'],expected_run,expected_source,s['run_id'],m)
            and encode(ctx)==encode(b['capture_context']), 'HANDOFF_CAPTURE_CONTEXT_REPLAY')
    require(data['admission.json']==encode(admission(e,ctx,comparison)), 'HANDOFF_ADMISSION_REPLAY')
    inv=m.strict_json(data['postflight/inventory.json'])
    acq={n[len('postflight/'):]:v for n,v in data.items() if n.startswith('postflight/') and n!='postflight/inventory.json'}
    require(encode(inv)==encode({'record_type':'q3_postflight_acquisition_inventory_v0',
        'files':{n:{'sha256':digest(v),'size_bytes':len(v)} for n,v in acq.items()},
        'inventory_self_excluded':True,**a.BOUNDARIES}), 'HANDOFF_ACQUISITION_INVENTORY')
    ar=m.strict_json(data['postflight/acquisition.json'])
    fields(ar, {'record_type','status','disposition','selection_sha256','comparison_sha256',
        'acquirer_sha256','comparator_sha256','observation_channel','transport_trust',
        'metadata_recheck','api_version','started_at','completed_at','transfers',*a.BOUNDARIES},
        'HANDOFF_ACQUISITION_RECEIPT_FIELDS')
    expected_receipt={'record_type':'q3_external_postflight_acquisition_v0','status':'complete',
        'disposition':'CONSISTENT_OFFLINE','selection_sha256':e['postflight_selection_sha256'],
        'comparison_sha256':digest(comparison),'acquirer_sha256':ACQUIRER_SHA,
        'comparator_sha256':COMPARATOR_SHA,
        'observation_channel':'live_github_https_api_and_api_selected_storage',
        'transport_trust':'local_tls_ca_store_and_github_service',
        'metadata_recheck':'UNCHANGED','api_version':a.API_VERSION,**a.BOUNDARIES}
    require(all(encode(ar[k])==encode(v) for k,v in expected_receipt.items()),
            'HANDOFF_ACQUISITION_RECEIPT')
    started=m.stamp(ar['started_at']);completed=m.stamp(ar['completed_at'])
    require(started<=completed,'HANDOFF_ACQUISITION_CLOCK')
    a.metadata_valid(s,raw_inputs,m,started);a.metadata_valid(s,raw_inputs,m,completed)
    routes=a.paths(s)
    transfers=[(a.API_PREFIX+'runs/'+expected_run+'/attempts/1',data['capture-run.before.json'],False)]
    transfers.extend((routes[n],raw_inputs[n],n in ('artifact.zip','job.log'))
                     for n in ('run.json','jobs.json','artifact.json','artifact.zip','job.log'))
    transfers.extend((routes[n],data['postflight/'+n.replace('.json','.after.json')],False)
                     for n in ('run.json','jobs.json','artifact.json'))
    require(type(ar['transfers']) is list and len(ar['transfers'])==len(transfers),
            'HANDOFF_TRANSFER_INVENTORY')
    for row,(endpoint,body,is_storage) in zip(ar['transfers'],transfers):
        fields(row,{'endpoint','sha256','size_bytes','download_host'},'HANDOFF_TRANSFER_FIELDS')
        require(row['endpoint']==endpoint and row['sha256']==digest(body)
            and type(row['size_bytes']) is int and row['size_bytes']==len(body),
            'HANDOFF_TRANSFER_BINDING')
        if is_storage:
            require(type(row['download_host']) is str,'HANDOFF_STORAGE_HOST')
            a.storage_url('https://'+row['download_host']+'/retained-host-only')
        else:require(row['download_host'] is None,'HANDOFF_TRANSFER_HOST')
    checked=verify_native(data,e,ctx,src,m)
    require(checked.get('complete') is True, 'HANDOFF_NATIVE_INCOMPLETE')
    allowed={'request.json','bundle.json','capture-run.before.json','capture-run.after.json','admission.json',
             'native/evidence.zip','native/receipt.json'}
    allowed.update('capture-source/'+n for n in src)
    allowed.update('handoff-source/'+n for n in ex)
    allowed.update('postflight/'+n for n in ('selection.json','run.json','jobs.json','artifact.json',
        'artifact.zip','job.log','run.after.json','jobs.after.json','artifact.after.json',
        'expectation.json','comparison.json','acquisition.json','inventory.json'))
    require(set(data)==allowed, 'HANDOFF_COMPLETE_MEMBER_SET')
    return {'record_type':'q3_capture_handoff_check_v1','integrity_verified':True,
        'complete':True,'status':'complete','native_capture_reconstructed':True,
        'external_comparison_reconstructed':True,'capture_run_id':expected_run,
        'capture_source_commit':expected_source,'entry_request_sha256':expected_request,
        'live_origin_reobserved':False,'new_execution_authorized':False,**CLAIMS}


def final_write(c, output, uid, gid, archive, record, receipt):
    """Exclusive publication, fixed names, descriptor-bound custody and readback."""
    fd=os.open(output,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    st=os.fstat(fd); identity=(st.st_dev,st.st_ino); created={}
    values={'evidence.zip':archive}
    if record['status']!='complete':
        values['failure.json']=encode({'record_type':'q3_capture_handoff_failure_v1',
            'complete':False,'error_code':record['error_code'],**CLAIMS})
    values['receipt.json']=encode(receipt)
    def unchanged():
        x=output.lstat();require(stat.S_ISDIR(x.st_mode) and (x.st_dev,x.st_ino)==identity,
                                'HANDOFF_OUTPUT_REPLACED')
    try:
        for n,b in values.items():
            unchanged();c.write_new(output/n,b)
            x=os.stat(n,dir_fd=fd,follow_symlinks=False);created[n]=(x.st_dev,x.st_ino)
        for n,b in values.items():
            f=os.open(n,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
            try:
                x=os.fstat(f);require(stat.S_ISREG(x.st_mode) and x.st_nlink==1 and
                    (x.st_dev,x.st_ino)==created[n], 'HANDOFF_MEMBER_REPLACED')
                os.fchown(f,uid,gid);os.fchmod(f,0o600);os.fsync(f)
                require(c.safe_read(output/n,MAX_BUNDLE)==b, 'HANDOFF_PUBLICATION_READBACK')
            finally:os.close(f)
        unchanged();os.fchown(fd,uid,gid);os.fchmod(fd,0o700);os.fsync(fd);unchanged()
    except BaseException:
        for n,ident in reversed(list(created.items())):
            try:
                x=os.stat(n,dir_fd=fd,follow_symlinks=False)
                if (x.st_dev,x.st_ino)==ident:os.unlink(n,dir_fd=fd)
            except OSError:pass
        raise
    finally:os.close(fd)


def run(c,p,r,native_sources,root,envelope_raw,env,extra_sources,native_execute,plane_check,destination):
    """Called only by the guarded native controller; no saved-verdict input."""
    a,m=components(root,extra_sources)
    e=m.strict_json(envelope_raw); native_raw=e['native_request_utf8'].encode('utf-8')
    e,r,s=validate(envelope_raw,digest(envelope_raw),native_raw,native_sources,extra_sources,root,a,m)
    require(env.get('GITHUB_SHA')==e['capture_source_commit'] and
            env.get('GITHUB_RUN_ATTEMPT')=='1' and
            re.fullmatch('[1-9][0-9]{0,18}',env.get('GITHUB_RUN_ID','')) is not None,
            'HANDOFF_RUNTIME_CONTEXT')
    token=env.get('GITHUB_TOKEN',''); reader=a.GitHubReader(token)
    plane=plane_check(c,r,env,token)
    require(plane['run_id']==env['GITHUB_RUN_ID'] and plane['source_commit']==e['capture_source_commit'],
            'HANDOFF_CONTROL_PLANE')
    output,uid,gid=destination(c,env)  # exclusive run/attempt claim, never removed/reused
    stage=Path(tempfile.mkdtemp(prefix='q3-handoff-',dir=Path(env['RUNNER_TEMP'])))
    os.chmod(stage,0o700)
    st=stage.lstat();stage_identity=(st.st_dev,st.st_ino)
    data={'request.json':envelope_raw, **{'capture-source/'+n:b for n,b in native_sources.items()},
          **{'handoff-source/'+n:b for n,b in extra_sources.items()}}
    context={'repository':REPOSITORY,'workflow':WORKFLOW,'run_id':env['GITHUB_RUN_ID'],
        'run_attempt':1,'source_commit':r['source_commit'],'head_branch':'main',
        'event':'workflow_dispatch','actor':'HKati','triggering_actor':'HKati'}
    status='rejected'; error='HANDOFF_NOT_ADMITTED'; store=None; invoked=False; rc=2
    try:
        route=a.API_PREFIX+'runs/'+context['run_id']+'/attempts/1'
        data['capture-run.before.json']=reader.json(route)
        context=current_run(data['capture-run.before.json'],context['run_id'],r['source_commit'],s['run_id'],m)
        started=now();store=a.EvidenceDirectory(stage/'postflight')
        store.write('selection.json',e['postflight_selection_utf8'].encode('utf-8'))
        result,comparison=a.acquire(s,reader,store,m)
        ar=acquisition_receipt(a,s,e['postflight_selection_sha256'],result,comparison,reader,started)
        store.write('acquisition.json',a.encode(ar));store.finish();store.close();store=None
        require(result['disposition']=='CONSISTENT_OFFLINE','HANDOFF_EXTERNAL_CONTRADICTION')
        data['capture-run.after.json']=reader.json(route)
        require(context==current_run(data['capture-run.after.json'],context['run_id'],r['source_commit'],s['run_id'],m),
                'HANDOFF_CURRENT_RUN_CHANGED')
        data['admission.json']=encode(admission(e,context,comparison))
        # No callback is selected by JSON/CLI. The reviewed controller supplies
        # its existing core. The admission is consumed immediately in-process.
        base=stage/'native-stage';base.mkdir(mode=0o700)
        native_env={**env,'RUNNER_TEMP':str(base)}
        invoked=True
        rc=native_execute(c,p,r,native_sources,root,native_raw,native_env)
        require(type(rc) is int and rc in (0,1,2),'HANDOFF_NATIVE_EXIT')
        nd=base/'q3-reference-capture'/(context['run_id']+'-1')
        for name in ('evidence.zip','receipt.json','failure.json'):
            if (nd/name).exists():data['native/'+name]=a.read_source(nd/name,256*1024**2)
        if rc==0:
            require(verify_native(data,e,context,native_sources,m)['complete'] is True,'HANDOFF_NATIVE_INCOMPLETE')
            status='complete';error=None
        else:
            status='incomplete';error='HANDOFF_NATIVE_INCOMPLETE'
    except BaseException as exc:
        status='incomplete' if invoked else 'rejected';error=safe_code(exc);rc=1 if invoked else 2
    finally:
        if store is not None:store.close()
        # Retain native output even if its core raised after a partial publication.
        nd=stage/'native-stage/q3-reference-capture'/(context['run_id']+'-1')
        if invoked and nd.is_dir():
            try:
                for name in ('evidence.zip','receipt.json','failure.json'):
                    if (nd/name).exists():data['native/'+name]=a.read_source(nd/name,256*1024**2)
            except (OSError,ValueError):status='incomplete';error=error or 'HANDOFF_NATIVE_PRESERVATION_FAILED';rc=1
        # Retain complete already-written original observations, also on denial.
        ext=stage/'postflight'
        if ext.is_dir():
            try:
                for f in sorted(ext.iterdir()):
                    data['postflight/'+f.name]=a.read_source(f,MAX_BUNDLE)
            except (OSError,ValueError):status='incomplete';error=error or 'HANDOFF_PRESERVATION_INCOMPLETE';rc=1
        removed=False
        try:
            st=stage.lstat()
            if stat.S_ISDIR(st.st_mode) and (st.st_dev,st.st_ino)==stage_identity:
                shutil.rmtree(stage);removed=not stage.exists() and not stage.is_symlink()
        except OSError:pass
        if not removed:status='incomplete';error=error or 'HANDOFF_STAGING_CLEANUP_FAILED';rc=1
    archive,record=bundle(data,e,context,status,error,removed)
    if status=='complete':
        try:
            check(archive,digest(archive),digest(envelope_raw),r['source_commit'],context['run_id'],root,extra_sources)
        except (OSError,ValueError,KeyError,TypeError,RecursionError,zipfile.BadZipFile) as exc:
            # Native work may already have happened. Preserve its original bytes,
            # but never publish completion when final reconstruction fails.
            status='incomplete';error=safe_code(exc);rc=1
            archive,record=bundle(data,e,context,status,error,removed)
    receipt={'record_type':'q3_capture_handoff_receipt_v1','status':status,
        'archive_sha256':digest(archive),'archive_size_bytes':len(archive),
        'bundle_sha256':digest(encode(record)),'entry_request_sha256':digest(envelope_raw),
        'native_request_sha256':digest(native_raw),'source_commit':r['source_commit'],
        'capture_run_id':context['run_id'],'run_attempt':1,**CLAIMS}
    final_write(c,output,uid,gid,archive,record,receipt)
    return rc


def git_bytes(root, args):
    run=subprocess.run(['/usr/bin/git','--no-replace-objects','-c','protocol.allow=never',
        '-c','core.hooksPath=/dev/null','-c','safe.directory='+str(root),'-C',str(root),*args],
        env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C.UTF-8',
             'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_NO_LAZY_FETCH':'1'},
        stdin=subprocess.DEVNULL,capture_output=True,timeout=30)
    require(run.returncode==0 and len(run.stdout)<=16*1024**2,'HANDOFF_GIT_SOURCE')
    return run.stdout


def local_sources(root, commit):
    # Read the installed acquirer only as a byte reader after the reviewed digest
    # has been checked; no repository code is loaded from an arbitrary request.
    path=root/ACQUIRER
    require(not any(p.is_symlink() for p in (path,*path.parents)),'HANDOFF_BOOTSTRAP_PATH')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink==1
                and 0<before.st_size<=MAX_REQUEST,'HANDOFF_BOOTSTRAP_BOUND')
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(MAX_REQUEST+1)
        after=os.fstat(fd)
        require(len(raw)==before.st_size and
            (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),
            'HANDOFF_BOOTSTRAP_CHANGED')
    finally:os.close(fd)
    require(digest(raw)==ACQUIRER_SHA,'HANDOFF_ACQUIRER_VERSION')
    a=compile_module('q3_handoff_local_reader',ACQUIRER,raw,root)
    require(sha(commit,40) and git_bytes(root,['rev-parse','--verify','HEAD']).decode().strip()==commit,
            'HANDOFF_CLEAN_SOURCE')
    extras={}
    for n in EXTRA_SOURCES:
        b=a.read_source(root/n,MAX_REQUEST)
        require(git_bytes(root,['cat-file','blob',commit+':'+n])==b,'HANDOFF_DIRTY_SOURCE');extras[n]=b
    a,m=components(root,extras)
    cb=a.read_source(root/CONTRACT,MAX_REQUEST)
    require(digest(cb)==m.REVIEWED_CHECKERS[Path(CONTRACT).name],'HANDOFF_NATIVE_CONTRACT_VERSION')
    c=compile_module('q3_handoff_local_native',CONTRACT,cb,root)
    p=c.load_profile(root);source=c.source_snapshot(root,commit,p)
    return c,p,source,extras,a,m


def build_request(root,commit,native_raw,native_sha,selection_raw,selection_sha,authorization):
    c,p,source,extras,a,m=local_sources(root,commit)
    require(sha(native_sha) and digest(native_raw)==native_sha and sha(selection_sha)
            and digest(selection_raw)==selection_sha,'HANDOFF_BUILD_INPUT_DIGEST')
    value={'record_type':REQUEST_TYPE,'repository':REPOSITORY,'capture_source_commit':commit,
        'native_request_utf8':native_raw.decode('utf-8'),'native_request_sha256':native_sha,
        'postflight_selection_utf8':selection_raw.decode('utf-8'),
        'postflight_selection_sha256':selection_sha,
        'handoff_source_files':{n:pin(b) for n,b in extras.items()},'authorization':authorization}
    raw=encode(value);validate(raw,digest(raw),native_raw,source,extras,root,a,m)
    return raw


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='operation',required=True)
    b=sub.add_parser('build-request')
    for flag in ('repo-root','native-request','selection'):b.add_argument('--'+flag,type=Path,required=True)
    for flag in ('source-commit','native-request-sha256','selection-sha256','authorization'):
        b.add_argument('--'+flag,required=True)
    k=sub.add_parser('check-carrier')
    k.add_argument('--repo-root',type=Path,required=True);k.add_argument('--archive',type=Path,required=True)
    for flag in ('expected-archive-sha256','expected-request-sha256','expected-source-commit','expected-run-id'):
        k.add_argument('--'+flag,required=True)
    args=parser.parse_args(argv)
    try:
        root=args.repo_root.absolute()
        # The CLI checks only its exact current committed implementation.
        commit=args.source_commit if args.operation=='build-request' else args.expected_source_commit
        c,p,src,extras,a,m=local_sources(root,commit)
        if args.operation=='build-request':
            raw=build_request(root,commit,a.read_source(args.native_request,MAX_REQUEST),args.native_request_sha256,
                a.read_source(args.selection,MAX_REQUEST),args.selection_sha256,args.authorization)
            sys.stdout.buffer.write(raw);return 0
        result=check(a.read_source(args.archive,MAX_BUNDLE),args.expected_archive_sha256,
            args.expected_request_sha256,args.expected_source_commit,args.expected_run_id,root,extras)
        sys.stdout.buffer.write(encode(result));return 0 if result['complete'] else 1
    except (OSError,ValueError,KeyError,TypeError,RecursionError,subprocess.SubprocessError,zipfile.BadZipFile) as exc:
        sys.stderr.buffer.write(encode({'record_type':'q3_capture_handoff_error_v1',
            'error_code':safe_code(exc),'new_execution_authorized':False,**CLAIMS}));return 2


if __name__=='__main__':
    raise SystemExit(main())
