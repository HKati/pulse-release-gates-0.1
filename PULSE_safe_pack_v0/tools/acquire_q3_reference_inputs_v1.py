#!/usr/bin/env python3
"""Owner-only Q3 historical admission and 203-task continuation; no metrics.

The stdlib entry guard precedes helper imports, authenticated acquisition,
installation and subject execution. PR/push is never an execution route.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import ssl
import stat
import subprocess
import sys
import time
import types
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

REPOSITORY='HKati/pulse-release-gates-0.1'
WORKFLOW='.github/workflows/q3_reference_acquisition_v1.yml'
CONTRACT='PULSE_safe_pack_v0/tools/q3_native_capture_contract_v1.py'
PROFILE='PULSE_safe_pack_v0/profiles/q3_native_capture_v1.json'
SELF='PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v1.py'
RUNTIME='PULSE_safe_pack_v0/tools/q3_native_runtime_v1.py'
WORKER='PULSE_safe_pack_v0/tools/run_q3_reference_subject_v1.py'
CHECKER='PULSE_safe_pack_v0/tools/check_q3_native_capture_v1.py'
HISTORICAL='tools/check_q3_historical_observation_v1.py'
POSTFLIGHT_READER='tools/acquire_q3_external_postflight_v1.py'
SOURCE_FILES = ('.github/workflows/q3_reference_acquisition_v0.yml', '.github/workflows/q3_reference_acquisition_v1.yml', 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/preparation.json', 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/q2-runtime-preparation-check.json', 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/q2_reference_model_files_v0.json', 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/requirements-q2-reference-v0.lock', 'PULSE_safe_pack_v0/examples/q3_native_capture_v0/COMMON_INSTRUCTIONS.txt', 'PULSE_safe_pack_v0/examples/q3_native_capture_v0/SOURCE_CONTEXT_BINDINGS.json', 'PULSE_safe_pack_v0/examples/q3_native_capture_v0/TASKS_DRAFT.jsonl', 'PULSE_safe_pack_v0/examples/q3_native_capture_v0/TASK_ORDER.json', 'PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json', 'PULSE_safe_pack_v0/profiles/q3_native_capture_v0.json', 'PULSE_safe_pack_v0/profiles/q3_native_capture_v1.json', 'PULSE_safe_pack_v0/requirements-q2-reference-v0.lock', 'PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py', 'PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v1.py', 'PULSE_safe_pack_v0/tools/check_q3_native_capture_v0.py', 'PULSE_safe_pack_v0/tools/check_q3_native_capture_v1.py', 'PULSE_safe_pack_v0/tools/q3_native_capture_contract_v0.py', 'PULSE_safe_pack_v0/tools/q3_native_capture_contract_v1.py', 'PULSE_safe_pack_v0/tools/q3_native_runtime_v0.py', 'PULSE_safe_pack_v0/tools/q3_native_runtime_v1.py', 'PULSE_safe_pack_v0/tools/run_q3_reference_subject_v0.py', 'PULSE_safe_pack_v0/tools/run_q3_reference_subject_v1.py', 'docs/compute/PULSEMECH_Q3_ARCHIVED_INPUT_PREPARATION_v0.md', 'docs/compute/PULSEMECH_Q3_REFERENCE_RECOMPUTATION_v0.md', 'docs/compute/q3_capture_continuation_amendment_v1/CONTINUATION_PLAN.json', 'docs/compute/q3_capture_continuation_amendment_v1/continuation_plan.schema.json', 'schemas/metrics/q3_capture_handoff_request_v2.schema.json', 'schemas/metrics/q3_native_capture_request_v0.schema.json', 'schemas/metrics/q3_native_capture_request_v1.schema.json', 'schemas/metrics/q3_native_capture_result_v0.schema.json', 'schemas/metrics/q3_native_capture_result_v1.schema.json', 'tools/acquire_q3_external_postflight_v1.py', 'tools/check_q3_continuation_composite_v1.py', 'tools/check_q3_external_postflight_v1.py', 'tools/check_q3_historical_observation_v1.py', 'tools/q3_capture_handoff_v2.py')


# Transport selection is part of this already sealed controller source. No
# workflow input, request URL or ambient environment variable can select a
# different source. Publication/configuration is not runner retrieval evidence
# and does not authorize preflight, capture or measurement.
RUNTIME_TRANSPORT = {
    'kind': 'github-release-assets-v0',
    'repository': 'HKati/pulsemech-q3-runtime-inputs',
    'repository_id': 1450778044,
    'release_id': 438650666,
    'tag': 'q2-runtime-37148637546-1-v1',
    'tag_commit': 'd4125baa4bbf7b1b4d2d695a24b1c9bb1fa403b5',
}
RUNTIME_SPLIT_MANIFEST_SHA256 = '67eff809f8cf000f82b8365f1fc535ca82ffea167e2834488166915454c87f37'
_RUNTIME_PARTS_SHA256 = '0f7af070258c3bb6206c240e00cfe5464169666fbaf9fa9540b68c7ee384d341'
_RUNTIME_ORIGIN_SHA256 = '2f9d0516281bed710c68f27d61fad47eea996d0875212be64022a551dcc1621a'
RUNTIME_ORIGIN = {'filename': 'q2-runtime-preparation-37148637546-1.zip',
 'size_bytes': 508460811,
 'sha256': 'b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9',
 'original_run_id': '37148637546',
 'original_run_attempt': 1,
 'original_artifact_id': 11282419957,
 'original_source_commit': '77fc5d51896568db50a2a87f650711a65db8fe8c'}
RUNTIME_PARTS = ({'index': 1,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.001',
  'size_bytes': 25423041,
  'sha256': 'a99d34615119c69c5ba68054fa5e14e4e37828e8bbf12b569711886b7d373a0e',
  'offset_start': 0,
  'offset_end_exclusive': 25423041},
 {'index': 2,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.002',
  'size_bytes': 25423041,
  'sha256': '08c8ce6e853524fe0812e97d7c7e8e32c56728eb002be10e1f748f0b335ccec6',
  'offset_start': 25423041,
  'offset_end_exclusive': 50846082},
 {'index': 3,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.003',
  'size_bytes': 25423041,
  'sha256': 'bbdd47142671f1022f79d8c51ff1cf7f3ad36af64c35a1c07448a7d14e5be515',
  'offset_start': 50846082,
  'offset_end_exclusive': 76269123},
 {'index': 4,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.004',
  'size_bytes': 25423041,
  'sha256': '8b0c3aee20f5492b76598dbcd4e2af984c6295f1955ed2cc8e01d5813cabed12',
  'offset_start': 76269123,
  'offset_end_exclusive': 101692164},
 {'index': 5,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.005',
  'size_bytes': 25423041,
  'sha256': '19d689b4283374b6828973b3df216476627d4358a39ddd89c7f981de90d65d44',
  'offset_start': 101692164,
  'offset_end_exclusive': 127115205},
 {'index': 6,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.006',
  'size_bytes': 25423041,
  'sha256': '971dd1cf636b68d2f41a3b67eaa176a3be645707b94a904e4c29808d3b9c3012',
  'offset_start': 127115205,
  'offset_end_exclusive': 152538246},
 {'index': 7,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.007',
  'size_bytes': 25423041,
  'sha256': '6d6fad777bf3ef9014ade7fdf03c34f53af27140bfd6468d09d1f4ffe96b5617',
  'offset_start': 152538246,
  'offset_end_exclusive': 177961287},
 {'index': 8,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.008',
  'size_bytes': 25423041,
  'sha256': '932044ee2b88b02e56cbea68d1c9cefc4abc5338142ed06b1d31c76c84f1affd',
  'offset_start': 177961287,
  'offset_end_exclusive': 203384328},
 {'index': 9,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.009',
  'size_bytes': 25423041,
  'sha256': 'ee12b35b15a1efcbdc00ca5eff1db5021f93805ab809356d705d500a4cf06fb7',
  'offset_start': 203384328,
  'offset_end_exclusive': 228807369},
 {'index': 10,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.010',
  'size_bytes': 25423041,
  'sha256': '70bbd9d6ffe9b7a71b7f6723946b634d7ecd8001d60aa185915d64268c7d3fbd',
  'offset_start': 228807369,
  'offset_end_exclusive': 254230410},
 {'index': 11,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.011',
  'size_bytes': 25423041,
  'sha256': '4b5c14864c885831b9e0e999b2e210a02ea8b6ad3ea15f5b50f7f4ab7e912713',
  'offset_start': 254230410,
  'offset_end_exclusive': 279653451},
 {'index': 12,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.012',
  'size_bytes': 25423041,
  'sha256': 'e5b4f8b667f08403c9fa0d1f4a4b49900f9ec3b8f4e6aa5a27db18ec1c3f1371',
  'offset_start': 279653451,
  'offset_end_exclusive': 305076492},
 {'index': 13,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.013',
  'size_bytes': 25423041,
  'sha256': 'bc4ae5c262274fe6afba6f3f5e8f4aed9a18d4d9423c210223cd396b4a0858e1',
  'offset_start': 305076492,
  'offset_end_exclusive': 330499533},
 {'index': 14,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.014',
  'size_bytes': 25423041,
  'sha256': '52c03baac0181133d6cde5aff69f086062828faa090c09912dba9eb5fd989f11',
  'offset_start': 330499533,
  'offset_end_exclusive': 355922574},
 {'index': 15,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.015',
  'size_bytes': 25423041,
  'sha256': 'c773e46bfee0941fb74f618ad3cd53b9b95dc243cedcb11786d265cd9c140f49',
  'offset_start': 355922574,
  'offset_end_exclusive': 381345615},
 {'index': 16,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.016',
  'size_bytes': 25423041,
  'sha256': 'fc1cc48947c2dd649ae3b3b2f71f5200511cd23e678633ddb97034f02f32752b',
  'offset_start': 381345615,
  'offset_end_exclusive': 406768656},
 {'index': 17,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.017',
  'size_bytes': 25423041,
  'sha256': '157f3263139e31909481cf603caa5bb3e4a17e55cd740831987adc7571893cfc',
  'offset_start': 406768656,
  'offset_end_exclusive': 432191697},
 {'index': 18,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.018',
  'size_bytes': 25423041,
  'sha256': 'da2e77f3e606ec22ba22c26d56c111314b5c31134d82981f22c214a823093061',
  'offset_start': 432191697,
  'offset_end_exclusive': 457614738},
 {'index': 19,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.019',
  'size_bytes': 25423041,
  'sha256': '146b777c3be81578a6466fd51b48c76345c7749876dc784ce1e6c77efbe0907a',
  'offset_start': 457614738,
  'offset_end_exclusive': 483037779},
 {'index': 20,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.020',
  'size_bytes': 25423032,
  'sha256': '6be9a0f37d32177b4da03be065df9956057b52bed75d57add0b2de7a1bdd7ae8',
  'offset_start': 483037779,
  'offset_end_exclusive': 508460811})



# Exact public release inventory; the four non-runtime companion/source assets
# are checked as metadata, not fetched or executed by the acquisition controller.
_RUNTIME_RELEASE_SOURCE_SHA256 = '16ac2d147f12e0bd4db769b0bf9a9fe717465ab834a0a1cb047ce38aefb9ddac'
_RUNTIME_RELEASE_ASSETS_SHA256 = '58c9e698caea11381e3bf2c916568cc18b0fe7bdac4cb5de2e3b2f4e81ed00dc'
RUNTIME_RELEASE_ASSETS = ({'asset_id': 728263266,
  'filename': 'Q3_RUNTIME_PARTS.json',
  'size_bytes': 7014,
  'sha256': '67eff809f8cf000f82b8365f1fc535ca82ffea167e2834488166915454c87f37'},
 {'asset_id': 728325322,
  'filename': 'Q3_RUNTIME_SOURCE_NOTICE_COMPANION_v2.zip',
  'size_bytes': 30532275,
  'sha256': 'cae9424e62696704db0d543c646f8ebb600d0650bbc260c80cc2207f76a40611'},
 {'asset_id': 728245570,
  'filename': 'gcc-4.8.5-44.el7.src.rpm',
  'size_bytes': 79314655,
  'sha256': '642c4085f6af9565e39583e54a9d7a5d9e6b93dd8c8e9474aec8a892d6c7aa36'},
 {'asset_id': 728264607,
  'filename': 'gcc-8.5.0-26.el8_10.alma.1.src.rpm',
  'size_bytes': 65714006,
  'sha256': '0911864c260a75ae030f3144616e7e5e1359e04ce1c9730ab83906486e3bc79f'},
 {'asset_id': 728284300,
  'filename': 'gcc-libraries-8.3.1-2.1.1.el7.src.rpm',
  'size_bytes': 137336608,
  'sha256': 'cf2a1d2c2e5a56eb2e495c2638e64769b73db07555e1f7ce34cbd9feff6891f5'},
 {'asset_id': 727868107,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.001',
  'size_bytes': 25423041,
  'sha256': 'a99d34615119c69c5ba68054fa5e14e4e37828e8bbf12b569711886b7d373a0e'},
 {'asset_id': 727895131,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.002',
  'size_bytes': 25423041,
  'sha256': '08c8ce6e853524fe0812e97d7c7e8e32c56728eb002be10e1f748f0b335ccec6'},
 {'asset_id': 727915062,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.003',
  'size_bytes': 25423041,
  'sha256': 'bbdd47142671f1022f79d8c51ff1cf7f3ad36af64c35a1c07448a7d14e5be515'},
 {'asset_id': 727921421,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.004',
  'size_bytes': 25423041,
  'sha256': '8b0c3aee20f5492b76598dbcd4e2af984c6295f1955ed2cc8e01d5813cabed12'},
 {'asset_id': 727947000,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.005',
  'size_bytes': 25423041,
  'sha256': '19d689b4283374b6828973b3df216476627d4358a39ddd89c7f981de90d65d44'},
 {'asset_id': 727962998,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.006',
  'size_bytes': 25423041,
  'sha256': '971dd1cf636b68d2f41a3b67eaa176a3be645707b94a904e4c29808d3b9c3012'},
 {'asset_id': 727981350,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.007',
  'size_bytes': 25423041,
  'sha256': '6d6fad777bf3ef9014ade7fdf03c34f53af27140bfd6468d09d1f4ffe96b5617'},
 {'asset_id': 727986211,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.008',
  'size_bytes': 25423041,
  'sha256': '932044ee2b88b02e56cbea68d1c9cefc4abc5338142ed06b1d31c76c84f1affd'},
 {'asset_id': 728018669,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.009',
  'size_bytes': 25423041,
  'sha256': 'ee12b35b15a1efcbdc00ca5eff1db5021f93805ab809356d705d500a4cf06fb7'},
 {'asset_id': 728024743,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.010',
  'size_bytes': 25423041,
  'sha256': '70bbd9d6ffe9b7a71b7f6723946b634d7ecd8001d60aa185915d64268c7d3fbd'},
 {'asset_id': 728029290,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.011',
  'size_bytes': 25423041,
  'sha256': '4b5c14864c885831b9e0e999b2e210a02ea8b6ad3ea15f5b50f7f4ab7e912713'},
 {'asset_id': 728039446,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.012',
  'size_bytes': 25423041,
  'sha256': 'e5b4f8b667f08403c9fa0d1f4a4b49900f9ec3b8f4e6aa5a27db18ec1c3f1371'},
 {'asset_id': 728044184,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.013',
  'size_bytes': 25423041,
  'sha256': 'bc4ae5c262274fe6afba6f3f5e8f4aed9a18d4d9423c210223cd396b4a0858e1'},
 {'asset_id': 728048948,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.014',
  'size_bytes': 25423041,
  'sha256': '52c03baac0181133d6cde5aff69f086062828faa090c09912dba9eb5fd989f11'},
 {'asset_id': 728055341,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.015',
  'size_bytes': 25423041,
  'sha256': 'c773e46bfee0941fb74f618ad3cd53b9b95dc243cedcb11786d265cd9c140f49'},
 {'asset_id': 728081578,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.016',
  'size_bytes': 25423041,
  'sha256': 'fc1cc48947c2dd649ae3b3b2f71f5200511cd23e678633ddb97034f02f32752b'},
 {'asset_id': 728090048,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.017',
  'size_bytes': 25423041,
  'sha256': '157f3263139e31909481cf603caa5bb3e4a17e55cd740831987adc7571893cfc'},
 {'asset_id': 728105373,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.018',
  'size_bytes': 25423041,
  'sha256': 'da2e77f3e606ec22ba22c26d56c111314b5c31134d82981f22c214a823093061'},
 {'asset_id': 728148443,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.019',
  'size_bytes': 25423041,
  'sha256': '146b777c3be81578a6466fd51b48c76345c7749876dc784ce1e6c77efbe0907a'},
 {'asset_id': 728151616,
  'filename': 'q2-runtime-preparation-37148637546-1.zip.020',
  'size_bytes': 25423032,
  'sha256': '6be9a0f37d32177b4da03be065df9956057b52bed75d57add0b2de7a1bdd7ae8'})

class EntryRejected(ValueError):
    pass


def entry_require(v):
    if not v:raise EntryRejected('Q3_ENTRY_REJECTED')


def boot_read(path,limit=16*1024*1024):
    entry_require(not any(p.is_symlink() for p in [path,*path.parents]))
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        a=os.fstat(fd);entry_require(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_size<=limit)
        with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(limit+1)
        b=os.fstat(fd)
        entry_require(len(raw)==a.st_size and (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==
                      (b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns))
        return raw
    finally:os.close(fd)


def boot_git(root,args):
    p=subprocess.run(['/usr/bin/git','--no-replace-objects','-c','protocol.allow=never',
                      '-c','core.hooksPath=/dev/null','-c','safe.directory='+str(root),'-C',str(root),*args],
                     env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C.UTF-8',
                          'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_NO_LAZY_FETCH':'1'},
                     stdin=subprocess.DEVNULL,capture_output=True,timeout=30)
    entry_require(p.returncode==0 and len(p.stdout)<=16*1024*1024);return p.stdout


def entry_guard(root,commit,raw,request_sha,env,*,observation_only=False):
    entry_require(sys.flags.isolated and (observation_only or os.geteuid()==0))
    entry_require(type(commit) is str and re.fullmatch(r'[a-f0-9]{40}',commit) is not None)
    entry_require(type(raw) is bytes and len(raw)<=128*1024 and hashlib.sha256(raw).hexdigest()==request_sha)
    expected={'GITHUB_REPOSITORY':REPOSITORY,'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main',
              'GITHUB_ACTOR':'HKati','GITHUB_TRIGGERING_ACTOR':'HKati','GITHUB_RUN_ATTEMPT':'1',
              'GITHUB_SHA':commit,'GITHUB_WORKFLOW_SHA':commit,
              'GITHUB_WORKFLOW_REF':REPOSITORY+'/'+WORKFLOW+'@refs/heads/main'}
    entry_require(all(env.get(k)==v for k,v in expected.items()))
    entry_require(re.fullmatch(r'[1-9][0-9]{0,19}',env.get('GITHUB_RUN_ID','')) is not None)
    entry_require(Path(__file__).resolve()==(root/SELF).resolve())
    entry_require(boot_git(root,['rev-parse','--verify','HEAD']).decode().strip()==commit)
    snapshot={}
    for name in SOURCE_FILES:
        b=boot_read(root/name);entry_require(boot_git(root,['cat-file','blob',commit+':'+name])==b);snapshot[name]=b
    module=types.ModuleType('q3_held_contract');module.__file__=str(root/CONTRACT)
    exec(compile(snapshot[CONTRACT],module.__file__,'exec'),module.__dict__)
    p=module.load_profile(snapshot)
    module.require(set(p['source_files'])==set(SOURCE_FILES),'SOURCE_SCOPE')
    entry=module.strict_json(raw,128*1024)
    if type(entry) is dict and entry.get('record_type')=='q3_capture_handoff_request_v2':
        module.require(type(entry.get('native_request_utf8')) is str,'HANDOFF_NATIVE_REQUEST')
        native_raw=entry['native_request_utf8'].encode('utf-8')
        r=module.validate_request(native_raw,p)
        module.require(r['mode']=='capture','HANDOFF_CAPTURE_ONLY')
    else:
        r=module.validate_request(raw,p)
        module.require(r['mode']=='token-preflight','CAPTURE_HANDOFF_REQUIRED')
    module.require(r['source_commit']==commit,'REQUEST_SOURCE')
    module.task_frame(snapshot,p)
    return module,p,r,snapshot


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def api_bytes(path,token,limit=16*1024*1024):
    # Paths are constructed by this program, never accepted from the request.
    entry_require(path.startswith('/repos/'+REPOSITORY+'/') or path=='/repos/'+REPOSITORY)
    req=urllib.request.Request('https://api.github.com'+path,headers={
        'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
        'X-GitHub-Api-Version':'2022-11-28','User-Agent':'PULSE-Q3-native-v1'})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=15) as response:
        entry_require(response.status==200);raw=response.read(limit+1)
    entry_require(len(raw)<=limit);return raw


def control_plane(C,request,env,token):
    run_id=env['GITHUB_RUN_ID']
    base='/repos/'+REPOSITORY
    run=C.strict_json(api_bytes(base+'/actions/runs/'+run_id+'/attempts/1',token))
    repo=C.strict_json(api_bytes(base,token))
    branch=C.strict_json(api_bytes(base+'/branches/main',token))
    C.require(type(run['id']) is int and str(run['id'])==run_id and type(run['run_attempt']) is int
              and run['run_attempt']==1 and run['head_sha']==request['source_commit']
              and run['head_branch']=='main' and run['event']=='workflow_dispatch'
              and run['path'].split('@',1)[0]==WORKFLOW
              and run['actor']['login']=='HKati' and run['triggering_actor']['login']=='HKati'
              and repo['full_name']==REPOSITORY and repo['private'] is False
              and branch['commit']['sha']==request['source_commit'],'CONTROL_PLANE_MISMATCH')
    return {'run_id':run_id,'run_attempt':1,'source_commit':request['source_commit'],
            'repository':REPOSITORY,'repository_private':False,'event':'workflow_dispatch',
            'workflow':WORKFLOW,'head_branch':'main','actor':'HKati','triggering_actor':'HKati',
            'clock_relation':'not_verified'}


def _runtime_archive_identity():
    return {key:RUNTIME_ORIGIN[key] for key in ('filename','size_bytes','sha256')}


def _validate_runtime_parts(C,parts,archive_identity):
    """Validate an ordered inventory; production additionally pins its bytes.

    The small explicit parameters are an offline-test seam, not a CLI/input
    override.  download_runtime() uses only the sealed production constants.
    """
    C.fields(archive_identity,{'filename','size_bytes','sha256'},'RUNTIME_ARCHIVE_FIELDS')
    filename=C.relative(archive_identity['filename'])
    C.require('/' not in filename,'RUNTIME_ARCHIVE_FILENAME')
    C.integer(archive_identity['size_bytes'],1,508460811,'RUNTIME_ARCHIVE_SIZE')
    C.require(C.sha256_string(archive_identity['sha256']),'RUNTIME_ARCHIVE_DIGEST')
    C.require(type(parts) in (list,tuple) and len(parts)==20,'RUNTIME_PART_COUNT')
    offset=0
    for ordinal,row in enumerate(parts,1):
        C.fields(row,{'index','filename','size_bytes','sha256','offset_start','offset_end_exclusive'},
                 'RUNTIME_PART_FIELDS')
        C.require(type(row['index']) is int and row['index']==ordinal
                  and row['filename']==filename+f'.{ordinal:03d}','RUNTIME_PART_ORDER')
        C.integer(row['size_bytes'],1,25423041,'RUNTIME_PART_SIZE')
        C.require(C.sha256_string(row['sha256']),'RUNTIME_PART_DIGEST')
        C.require(type(row['offset_start']) is int and row['offset_start']==offset
                  and type(row['offset_end_exclusive']) is int
                  and row['offset_end_exclusive']==offset+row['size_bytes'],'RUNTIME_PART_OFFSETS')
        offset+=row['size_bytes']
    C.require(offset==archive_identity['size_bytes'],'RUNTIME_PART_TOTAL')


def _runtime_source(C,source):
    if type(source) is dict and source.get('kind')=='github-release-assets-v0':
        C.fields(source,{'kind','repository','repository_id','release_id','tag','tag_commit'},
                 'RUNTIME_RELEASE_SOURCE_FIELDS')
        C.require(C.digest(C.encode(source))==_RUNTIME_RELEASE_SOURCE_SHA256,'RUNTIME_RELEASE_SOURCE_PIN')
        return dict(source)
    C.fields(source,{'kind','repository','commit','prefix'},'RUNTIME_TRANSPORT_FIELDS')
    C.require(type(source['kind']) is str and source['kind'] in
              ('original-actions-artifact-v0','github-repository-parts-v0')
              and source['repository']==REPOSITORY,'RUNTIME_TRANSPORT_SCOPE')
    if source['kind']=='original-actions-artifact-v0':
        C.require(source['commit'] is None and source['prefix'] is None,'RUNTIME_ARTIFACT_SOURCE')
    else:
        C.require(source['commit'] is not None and source['prefix'] is not None,
                  'RUNTIME_TRANSPORT_UNCONFIGURED')
        C.require(type(source['commit']) is str and re.fullmatch(r'[a-f0-9]{40}',source['commit'])
                  is not None and source['commit']!='0'*40,'RUNTIME_TRANSPORT_COMMIT')
        C.relative(source['prefix'])
    return dict(source)


def runtime_transport_plan(C,p):
    """Resolve only the descriptor sealed with this controller's source bytes."""
    C.require(C.digest(C.encode(RUNTIME_ORIGIN))==_RUNTIME_ORIGIN_SHA256,'RUNTIME_ORIGIN_PIN')
    expected={key:RUNTIME_ORIGIN[source] for key,source in
              (('artifact_id','original_artifact_id'),('run_id','original_run_id'),
               ('size_bytes','size_bytes'),('sha256','sha256'))}
    C.require(C.encode(p['runtime_archive'])==C.encode(expected),'RUNTIME_ORIGIN_BINDING')
    C.require(RUNTIME_SPLIT_MANIFEST_SHA256==
              '67eff809f8cf000f82b8365f1fc535ca82ffea167e2834488166915454c87f37'
              and C.digest(C.encode(RUNTIME_PARTS))==_RUNTIME_PARTS_SHA256,'RUNTIME_PARTS_PIN')
    _validate_runtime_parts(C,RUNTIME_PARTS,_runtime_archive_identity())
    source=_runtime_source(C,RUNTIME_TRANSPORT)
    if source['kind']=='github-repository-parts-v0':
        for row in RUNTIME_PARTS:C.relative(source['prefix']+'/'+row['filename'])
    elif source['kind']=='github-release-assets-v0':
        _runtime_release_assets(C)
    return source


def _runtime_timeout(C,end):
    remaining=end-time.monotonic()
    C.require(remaining>0,'RUNTIME_DOWNLOAD_DEADLINE')
    return min(15.0,remaining)


def _runtime_release_assets(C):
    C.require(type(RUNTIME_RELEASE_ASSETS) is tuple and len(RUNTIME_RELEASE_ASSETS)==25
              and C.digest(C.encode(RUNTIME_RELEASE_ASSETS))==_RUNTIME_RELEASE_ASSETS_SHA256,
              'RUNTIME_RELEASE_ASSETS_PIN')
    assets={row['filename']:dict(row) for row in RUNTIME_RELEASE_ASSETS}
    C.require(len(assets)==25 and len({row['asset_id'] for row in assets.values()})==25,
              'RUNTIME_RELEASE_ASSET_SET')
    for part in RUNTIME_PARTS:
        row=assets[part['filename']]
        C.require(row['size_bytes']==part['size_bytes'] and row['sha256']==part['sha256'],
                  'RUNTIME_RELEASE_PART_BINDING')
    manifest=assets['Q3_RUNTIME_PARTS.json']
    C.require(manifest['size_bytes']==7014 and manifest['sha256']==RUNTIME_SPLIT_MANIFEST_SHA256,
              'RUNTIME_RELEASE_MANIFEST_BINDING')
    return assets


def _release_asset_endpoint(source,asset):
    return ('https://api.github.com/repos/'+source['repository']+'/releases/assets/'+str(asset['asset_id']))


def _release_header(C,headers,name):
    values=headers.get_all(name,[])
    C.require(len(values)<=1 and all(type(v) is str for v in values),'RUNTIME_RELEASE_HEADERS')
    return values[0] if values else None


def _release_response(C,response,maximum,*,exact_size=None,json_body=False):
    """Reject ambiguous framing/encoding before any response bytes are consumed."""
    try:
        C.require(response.status==200,'RUNTIME_RELEASE_HTTP_STATUS')
        C.require(_release_header(C,response.headers,'Content-Encoding') in (None,'identity'),
                  'RUNTIME_RELEASE_CONTENT_ENCODING')
        length=_release_header(C,response.headers,'Content-Length')
        transfer=_release_header(C,response.headers,'Transfer-Encoding')
        C.require(transfer in (None,'chunked') and not (transfer and length),'RUNTIME_RELEASE_FRAMING')
        if length is not None:
            C.require(re.fullmatch(r'[0-9]{1,10}',length) is not None
                      and 0<int(length)<=maximum,'RUNTIME_RELEASE_CONTENT_LENGTH')
            if exact_size is not None:
                C.require(int(length)==exact_size,'RUNTIME_RELEASE_CONTENT_LENGTH')
        if json_body:
            media=_release_header(C,response.headers,'Content-Type')
            C.require(media is not None and media.split(';',1)[0].strip().lower()
                      in ('application/json','application/vnd.github+json'),'RUNTIME_RELEASE_JSON_MEDIA')
    except BaseException:
        response.close();raise
    return response


def _public_release_open(C,url,end,*,binary=False):
    # This public companion needs no token. A fresh opener has no cookies or
    # auth handler, ignores ambient proxies, and never follows redirects itself.
    request=urllib.request.Request(url,headers={
        'Accept':'application/octet-stream' if binary else 'application/vnd.github+json',
        'Accept-Encoding':'identity','X-GitHub-Api-Version':'2022-11-28','User-Agent':'PULSE-Q3-runtime-v1'})
    try:
        return urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),NoRedirect()).open(
                request,timeout=_runtime_timeout(C,end))
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError,TimeoutError,OSError):
        raise C.ContractError('RUNTIME_RELEASE_UNAVAILABLE') from None


def _release_read_bounded(C,response,maximum,end):
    read_once=getattr(response,'read1',None)
    C.require(callable(read_once),'RUNTIME_RELEASE_STREAM_READER')
    chunks=[];total=0
    while True:
        _runtime_timeout(C,end)
        limit=min(65536,maximum-total+1)
        chunk=read_once(limit)
        _runtime_timeout(C,end)
        C.require(type(chunk) is bytes and len(chunk)<=limit,'RUNTIME_RELEASE_READ')
        if not chunk:break
        total+=len(chunk)
        C.require(total<=maximum,'RUNTIME_RELEASE_BODY_SIZE');chunks.append(chunk)
    length=_release_header(C,response.headers,'Content-Length')
    C.require(length is None or total==int(length),'RUNTIME_RELEASE_BODY_SIZE')
    return b''.join(chunks)


def _release_api_json(C,source,suffix,end):
    # Only the repository, fixed release, and exact tag reference are metadata
    # routes. No latest lookup, search, caller URL, pagination or fallback.
    C.require(suffix in ('','/releases/'+str(source['release_id']),'/git/ref/tags/'+source['tag']),
              'RUNTIME_RELEASE_API_SCOPE')
    url='https://api.github.com/repos/'+source['repository']+suffix
    try:response=_public_release_open(C,url,end)
    except urllib.error.HTTPError as exc:
        exc.close();raise C.ContractError('RUNTIME_RELEASE_METADATA_HTTP') from None
    with _release_response(C,response,1024*1024,json_body=True):
        raw=_release_read_bounded(C,response,1024*1024,end)
    return C.strict_json(raw,maximum=1024*1024)


def _runtime_release_metadata(C,source,end):
    """Retain a bounded identity projection, not signed URLs or download counts."""
    source=_runtime_source(C,source);assets=_runtime_release_assets(C)
    repo=_release_api_json(C,source,'',end)
    release=_release_api_json(C,source,'/releases/'+str(source['release_id']),end)
    tag=_release_api_json(C,source,'/git/ref/tags/'+source['tag'],end)
    C.require(all(type(x) is dict for x in (repo,release,tag)),'RUNTIME_RELEASE_METADATA_SHAPE')
    obj=tag.get('object');rows=release.get('assets')
    C.require(type(obj) is dict and type(rows) is list and len(rows)==25,'RUNTIME_RELEASE_METADATA_SHAPE')
    observed=[];base='https://api.github.com/repos/'+source['repository']
    for row in rows:
        C.require(type(row) is dict and type(row.get('name')) is str
                  and row['name'] in assets,'RUNTIME_RELEASE_ASSET_NAME')
        fixed=assets[row['name']]
        C.require(row.get('url')==_release_asset_endpoint(source,fixed)
                  and row.get('browser_download_url')=='https://github.com/'+source['repository']+
                  '/releases/download/'+source['tag']+'/'+fixed['filename'],'RUNTIME_RELEASE_ASSET_URL')
        digest=row.get('digest')
        C.require(type(digest) is str and digest.startswith('sha256:'),'RUNTIME_RELEASE_ASSET_DIGEST')
        observed.append({'asset_id':row.get('id'),'filename':row['name'],'size_bytes':row.get('size'),
                         'sha256':digest[7:],'state':row.get('state')})
    observed.sort(key=lambda row:row['filename'])
    value={'repository':{'id':repo.get('id'),'full_name':repo.get('full_name'),'private':repo.get('private')},
           'release':{'id':release.get('id'),'tag_name':release.get('tag_name'),
                      'draft':release.get('draft'),'immutable':release.get('immutable')},
           'tag':{'ref':tag.get('ref'),'object_type':obj.get('type'),'commit':obj.get('sha')},
           'assets':observed}
    expected={'repository':{'id':source['repository_id'],'full_name':source['repository'],'private':False},
              'release':{'id':source['release_id'],'tag_name':source['tag'],'draft':False,'immutable':True},
              'tag':{'ref':'refs/tags/'+source['tag'],'object_type':'commit','commit':source['tag_commit']},
              'assets':[{**row,'state':'uploaded'} for row in RUNTIME_RELEASE_ASSETS]}
    C.require(release.get('url')==base+'/releases/'+str(source['release_id'])
              and C.encode(value)==C.encode(expected),'RUNTIME_RELEASE_METADATA_MISMATCH')
    return value


def _open_runtime_release_asset(C,source,asset,end):
    source=_runtime_source(C,source);assets=_runtime_release_assets(C)
    C.require(type(asset) is dict and asset.get('filename') in assets
              and C.encode(asset)==C.encode(assets[asset['filename']]),'RUNTIME_RELEASE_ASSET_PIN')
    endpoint=_release_asset_endpoint(source,asset)
    try:response=_public_release_open(C,endpoint,end,binary=True)
    except urllib.error.HTTPError as exc:
        try:
            C.require(exc.code==302,'RUNTIME_RELEASE_ASSET_HTTP')
            location=_release_header(C,exc.headers,'Location')
            C.require(type(location) is str and 0<len(location)<=16384
                      and not any(ord(c)<33 or ord(c)==127 for c in location)
                      and '\\' not in location,'RUNTIME_RELEASE_REDIRECT')
            u=urllib.parse.urlsplit(location)
            # GitHub's public Release asset service; the signed query stays in
            # memory only and is never included in receipts or diagnostics.
            C.require(u.scheme=='https' and u.netloc in
                      ('release-assets.githubusercontent.com','release-assets.githubusercontent.com:443')
                      and not u.fragment and re.fullmatch('/github-production-release-asset/'+
                      str(source['repository_id'])+r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                      u.path) is not None,'RUNTIME_RELEASE_REDIRECT')
        finally:exc.close()
        try:response=_public_release_open(C,location,end,binary=True)
        except urllib.error.HTTPError as exc:
            exc.close();raise C.ContractError('RUNTIME_RELEASE_REDIRECT_CHAIN') from None
    return _release_response(C,response,asset['size_bytes'],exact_size=asset['size_bytes'])


def _runtime_release_manifest(C,source,assets,end):
    asset=assets['Q3_RUNTIME_PARTS.json']
    with _open_runtime_release_asset(C,source,asset,end) as response:
        raw=_release_read_bounded(C,response,asset['size_bytes'],end)
    C.require(len(raw)==asset['size_bytes'] and C.digest(raw)==asset['sha256'],
              'RUNTIME_RELEASE_MANIFEST_BYTES')
    manifest=C.strict_json(raw)
    C.require(type(manifest) is dict and manifest.get('part_count')==20
              and manifest.get('split_method')=='contiguous_original_bytes_no_recompression'
              and C.encode(manifest.get('original'))==C.encode(RUNTIME_ORIGIN)
              and C.encode(manifest.get('parts'))==C.encode(RUNTIME_PARTS),'RUNTIME_RELEASE_MANIFEST_CONTENT')
    return {**asset,'endpoint':_release_asset_endpoint(source,asset)}


def _download_runtime_release(C,source,target,phase_deadline):
    end=min(phase_deadline,time.monotonic()+180);assets=_runtime_release_assets(C)
    before=_runtime_release_metadata(C,source,end)
    manifest=_runtime_release_manifest(C,source,assets,end)
    after=[]
    def recheck():
        value=_runtime_release_metadata(C,source,end)
        C.require(C.encode(value)==C.encode(before),'RUNTIME_RELEASE_METADATA_CHANGED')
        after.append(value)
    observed=_assemble_runtime_parts(C,RUNTIME_PARTS,_runtime_archive_identity(),target,end,
        lambda part:_open_runtime_release_asset(C,source,assets[part['filename']],end),after_verify=recheck)
    parts=[{**row,'asset_id':assets[row['filename']]['asset_id'],
            'endpoint':_release_asset_endpoint(source,assets[row['filename']])} for row in observed['parts']]
    return {'record_type':'q3_runtime_transport_v1','transport':source,'origin':dict(RUNTIME_ORIGIN),
            'split_manifest_sha256':RUNTIME_SPLIT_MANIFEST_SHA256,'manifest_asset':manifest,'parts':parts,
            'metadata_checks':{'before':before,'after':after[0]},
            'archive_size_bytes':observed['size_bytes'],'archive_sha256':observed['sha256'],
            'claims':dict(C.CLAIMS)}


def _open_runtime_part(C,token,source,part,end):
    """Open one exact-commit raw Contents response without credential redirects."""
    source=_runtime_source(C,source)
    C.require(source['kind']=='github-repository-parts-v0','RUNTIME_PART_SOURCE')
    filename=C.relative(part['filename']);C.require('/' not in filename,'RUNTIME_PART_FILENAME')
    path=C.relative(source['prefix']+'/'+filename)
    C.require(type(token) is str and 0<len(token)<=4096 and '\r' not in token and '\n' not in token,
              'READ_TOKEN_REQUIRED')
    quoted=urllib.parse.quote(path,safe='/')
    endpoint='https://api.github.com/repos/'+REPOSITORY+'/contents/'+quoted+'?ref='+source['commit']
    request=urllib.request.Request(endpoint,headers={
        'Authorization':'Bearer '+token,'Accept':'application/vnd.github.raw+json',
        'Accept-Encoding':'identity','X-GitHub-Api-Version':'2022-11-28','User-Agent':'PULSE-Q3-native-v1'})
    try:
        response=urllib.request.build_opener(NoRedirect()).open(request,timeout=_runtime_timeout(C,end))
    except urllib.error.HTTPError as exc:
        try:
            C.require(exc.code in (301,302,303,307,308),'RUNTIME_PART_HTTP_STATUS')
            # Only this exact immutable public raw path may receive a redirect.
            # No bearer token, query credential or ambient request header follows.
            raw_url='https://raw.githubusercontent.com/'+REPOSITORY+'/'+source['commit']+'/'+quoted
            C.require(exc.headers.get('Location','')==raw_url,'RUNTIME_PART_REDIRECT_SOURCE')
        finally:exc.close()
        try:
            response=urllib.request.build_opener(NoRedirect()).open(
                urllib.request.Request(raw_url,headers={'Accept-Encoding':'identity'}),
                timeout=_runtime_timeout(C,end))
        except urllib.error.HTTPError as exc:
            exc.close();raise C.ContractError('RUNTIME_PART_REDIRECT_CHAIN') from None
    if response.status!=200:
        response.close();raise C.ContractError('RUNTIME_PART_HTTP_STATUS')
    try:
        encodings=response.headers.get_all('Content-Encoding',[])
        C.require(encodings in ([],['identity']),'RUNTIME_PART_CONTENT_ENCODING')
    except BaseException:
        response.close();raise
    return response


def _assemble_runtime_parts(C,parts,archive_identity,target,end,open_part,*,after_verify=None):
    """Stream and verify an ordered inventory; never execute archive contents."""
    _validate_runtime_parts(C,parts,archive_identity)
    C.require(time.monotonic()<end,'RUNTIME_DOWNLOAD_DEADLINE')
    target=Path(target);created=False;identity=None;total=0;whole=hashlib.sha256();observed=[]
    try:
        with target.open('xb') as output:
            created=True;st=os.fstat(output.fileno());identity=(st.st_dev,st.st_ino)
            os.fchmod(output.fileno(),0o600)
            for part in parts:
                C.require(time.monotonic()<end,'RUNTIME_DOWNLOAD_DEADLINE')
                count=0;digest=hashlib.sha256();start=total
                with open_part(part) as response:
                    read_once=getattr(response,'read1',None)
                    C.require(callable(read_once),'RUNTIME_PART_STREAM_READER')
                    while True:
                        C.require(time.monotonic()<end,'RUNTIME_DOWNLOAD_DEADLINE')
                        maximum=min(65536,part['size_bytes']-count+1)
                        # HTTPResponse.read(n) may keep filling n bytes under a
                        # slow trickle.  read1 returns after at most one buffered
                        # read, allowing the absolute deadline to be rechecked.
                        chunk=read_once(maximum)
                        C.require(time.monotonic()<end,'RUNTIME_DOWNLOAD_DEADLINE')
                        C.require(type(chunk) is bytes and len(chunk)<=maximum,'RUNTIME_PART_READ')
                        if not chunk:break
                        count+=len(chunk);total+=len(chunk)
                        C.require(count<=part['size_bytes'] and total<=archive_identity['size_bytes'],
                                  'RUNTIME_PART_DOWNLOAD_SIZE')
                        digest.update(chunk);whole.update(chunk);output.write(chunk)
                actual=digest.hexdigest()
                C.require(count==part['size_bytes'] and actual==part['sha256'],'RUNTIME_PART_MISMATCH')
                observed.append({'index':part['index'],'filename':part['filename'],'size_bytes':count,
                                 'sha256':actual,'offset_start':start,'offset_end_exclusive':total})
            archive_sha=whole.hexdigest()
            C.require(total==archive_identity['size_bytes'] and archive_sha==archive_identity['sha256'],
                      'RUNTIME_ARCHIVE_MISMATCH')
            output.flush();os.fsync(output.fileno())
            if after_verify is not None:after_verify()
            C.require(time.monotonic()<end,'RUNTIME_DOWNLOAD_DEADLINE')
        return {'size_bytes':total,'sha256':archive_sha,'parts':observed}
    except BaseException:
        # An existing caller file is never removed; only this call's private
        # inode may be discarded.  The outer lifecycle owns residual cleanup.
        if created:
            try:
                st=target.lstat()
                if (st.st_dev,st.st_ino)==identity:target.unlink()
            except OSError:pass
        raise


def download_runtime_artifact(C,p,token,target,phase_deadline):
    a=p['runtime_archive'];base='/repos/'+REPOSITORY
    meta=C.strict_json(api_bytes(base+'/actions/artifacts/'+str(a['artifact_id']),token))
    C.require(type(meta['id']) is int and meta['id']==a['artifact_id'] and meta['expired'] is False
              and meta['size_in_bytes']==a['size_bytes'] and meta['digest']=='sha256:'+a['sha256']
              and str(meta['workflow_run']['id'])==a['run_id'],'RUNTIME_ARTIFACT_METADATA')
    req=urllib.request.Request('https://api.github.com'+base+'/actions/artifacts/'+str(a['artifact_id'])+'/zip',
        headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    try:
        response=urllib.request.build_opener(NoRedirect()).open(req,timeout=15)
    except urllib.error.HTTPError as exc:
        C.require(exc.code in (301,302,303,307,308),'RUNTIME_REDIRECT_REQUIRED')
        location=exc.headers.get('Location','');u=urllib.parse.urlsplit(location)
        C.require(u.scheme=='https' and not u.username and not u.password and u.port in (None,443)
                  and u.hostname is not None and (u.hostname.endswith('.blob.core.windows.net')
                  or u.hostname.endswith('.actions.githubusercontent.com')),'RUNTIME_REDIRECT_HOST')
        # No bearer token or ambient request headers are forwarded to signed storage.
        response=urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(location),timeout=15)
    else:
        response.close();raise C.ContractError('RUNTIME_REDIRECT_REQUIRED')
    end=min(phase_deadline,time.monotonic()+180);total=0;h=hashlib.sha256()
    with response, target.open('xb') as f:
        os.fchmod(f.fileno(),0o600)
        while True:
            C.require(time.monotonic()<end,'RUNTIME_DOWNLOAD_DEADLINE')
            b=response.read(65536)
            if not b:break
            total+=len(b);C.require(total<=a['size_bytes'],'RUNTIME_DOWNLOAD_SIZE')
            h.update(b);f.write(b)
        f.flush();os.fsync(f.fileno())
    C.require(total==a['size_bytes'] and h.hexdigest()==a['sha256'],'RUNTIME_ARCHIVE_MISMATCH')
    return {'size_bytes':total,'sha256':h.hexdigest(),'parts':[]}


def download_runtime(C,p,token,target,phase_deadline):
    """Acquire exactly one source selected by the sealed controller, no fallback."""
    source=runtime_transport_plan(C,p)
    if source['kind']=='github-release-assets-v0':
        return _download_runtime_release(C,source,target,phase_deadline)
    if source['kind']=='original-actions-artifact-v0':
        observed=download_runtime_artifact(C,p,token,target,phase_deadline)
        manifest_sha=None;parts=[]
    else:
        end=min(phase_deadline,time.monotonic()+180)
        observed=_assemble_runtime_parts(C,RUNTIME_PARTS,_runtime_archive_identity(),target,end,
            lambda part:_open_runtime_part(C,token,source,part,end))
        manifest_sha=RUNTIME_SPLIT_MANIFEST_SHA256
        parts=[{**row,'path':source['prefix']+'/'+row['filename']} for row in observed['parts']]
    return {'record_type':'q3_runtime_transport_v0','transport':source,'origin':dict(RUNTIME_ORIGIN),
            'split_manifest_sha256':manifest_sha,'parts':parts,
            'archive_size_bytes':observed['size_bytes'],'archive_sha256':observed['sha256'],
            'claims':dict(C.CLAIMS)}


def load_sealed(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod);return mod


def failure_code(exc):
    if isinstance(exc,KeyboardInterrupt):return 'CAPTURE_INTERRUPTED'
    if isinstance(exc,ValueError) and len(exc.args)==1 and type(exc.args[0]) is str:
        code=exc.args[0]
        if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,95}',code):return code
    return 'RUNTIME_OR_EVIDENCE_UNAVAILABLE'


def receive_tokens(C,R,svc,frame,p,evidence,binding):
    deadline=min(svc.deadline,time.monotonic()+300)
    ready=svc.reader.line(deadline);R.save(evidence/'worker-ready.json',ready)
    C.require(C.strict_json(ready)=={'record_type':'q3_worker_ready_v1','binding':binding,'mode':p['_mode']},'WORKER_READY')
    svc.send(b'TOKENIZE\n');rows=[]
    for task in frame:
        raw=svc.reader.line(deadline);R.save(evidence/'tokens'/(task['task_id']+'.json'),raw)
        value=C.strict_json(raw)
        C.fields(value,{'record_type','binding','row'})
        C.require(value['record_type']=='q3_token_row_v1' and value['binding']==binding,'TOKEN_ROW_BINDING')
        row=value['row'];C.fields(row,{'task_id','ordinal','input_ids','messages_sha256','logical_request_sha256'})
        C.require(row['task_id']==task['task_id'] and type(row['ordinal']) is int and row['ordinal']==task['ordinal'],'TOKEN_ROW_ORDER')
        ids=row['input_ids'];C.require(type(ids) is list and 1<=len(ids)<=p['limits']['max_prompt_tokens']
            and all(type(i) is int and 0<=i<49152 for i in ids),'TOKEN_BOUNDS')
        C.require(row['messages_sha256']==C.digest(C.encode(task['messages']))
            and row['logical_request_sha256']==C.digest(task['logical_request_text'].encode()),'TOKEN_ROW_INPUT')
        rows.append(row)
    token_map={'record_type':'q3_token_map_v1','profile_sha256':C.PROFILE_SHA256,'model_revision':p['model_revision'],
               'task_file_sha256':p['fixed_inputs'][C.FRAME+'TASKS_DRAFT.jsonl'],'rows':rows}
    token_bytes=C.encode(token_map);sha=C.digest(token_bytes)
    end_raw=svc.reader.line(deadline);R.save(evidence/'token-map-end.json',end_raw)
    C.require(C.strict_json(end_raw)=={'record_type':'q3_token_map_end_v1','binding':binding,'token_map_sha256':sha,'task_count':204},'TOKEN_MAP_END')
    R.save(evidence/'token-map.json',token_bytes)
    return token_map,sha


def exchange_capture(C,R,K,life,svc,p,frame,token_map,binding,evidence,terminal,prefix,historical_sha):
    map_sha=C.digest(C.encode(token_map));svc.send(('LOAD '+map_sha+'\n').encode())
    raw=svc.reader.line(min(svc.deadline,time.monotonic()+180));R.save(evidence/'model-ready.json',raw)
    ready=C.strict_json(raw)
    C.fields(ready,{'record_type','binding','token_map_sha256','effective_generation','runtime'})
    C.require(ready['record_type']=='q3_model_ready_v1' and ready['binding']==binding and ready['token_map_sha256']==map_sha,'MODEL_READY')
    K.validate_generation(ready['effective_generation'],p)
    C.require(C.digest(C.encode(ready['effective_generation']))==p['effective_generation_sha256'],'GENERATION_CONFIGURATION')
    C.require(C.encode(ready['runtime'])==C.encode(K.expected_runtime(p)),'MODEL_READY_RUNTIME')
    subject={'record_type':'q3_capture_subject_v1','binding':binding,
             'model_ready_sha256':C.digest(raw),'token_map_sha256':map_sha,
             'historical_verification_sha256':historical_sha}
    subject_raw=C.encode(subject);R.save(evidence/'subject.json',subject_raw)
    full_binding={**binding,'subject_sha256':C.digest(subject_raw)}
    svc.send(('BIND '+C.digest(subject_raw)+'\n').encode())
    bound=svc.reader.line(min(svc.deadline,time.monotonic()+20));R.save(evidence/'bound.json',bound)
    C.require(C.strict_json(bound)=={'record_type':'q3_bound_v1','binding':full_binding},'BOUND_ACK')
    C.require(len(frame)==203 and len(terminal['occurrences'])==203,'CONTINUATION_COUNT')
    for task,row,occ in zip(frame,token_map['rows'][1:],terminal['occurrences']):
        name=task['task_id'];stem=evidence/'calls'/name
        occ['status']='preparation_failed'
        svc.send(('PREPARE '+name+'\n').encode())
        ready_raw=svc.reader.line(min(svc.deadline,time.monotonic()+20));R.save(stem.with_suffix('.ready.json'),ready_raw)
        sr=C.strict_json(ready_raw)
        slot={'task_id':name,'ordinal':task['ordinal'],'continuation_ordinal':task['continuation_ordinal'],'attempt':1}
        C.require(sr=={'record_type':'q3_slot_ready_v1','binding':full_binding,'slot':slot,
                       'input_ids':row['input_ids'],'effective_generation':ready['effective_generation'],'runtime':ready['runtime']},'SLOT_READY')
        R.save(stem.with_suffix('.intent.json'),C.encode({'task_id':name,'ordinal':task['ordinal'],
                'continuation_ordinal':task['continuation_ordinal'],
                'binding':full_binding,'intent':'before_GO','attempt':1}))
        occ['intent_saved_ns']=time.monotonic_ns()
        timer=prefix+f"-call-{task['ordinal']:03d}"
        arm=time.monotonic_ns();occ['watchdog_arm_begin_ns']=arm;life.arm(timer,svc.unit)
        C.require(time.monotonic_ns()+60*1000000000 < min(arm+65*1000000000,svc.runtime_deadline_ns), 'FULL_RESPONSE_WINDOW_UNAVAILABLE')
        C.require(not svc.reader.buffer and not svc.reader.selector.select(0),'UNSOLICITED_RESPONSE')
        occ['status']='attempt_uncertain';terminal['attempted_calls']+=1
        start=svc.send(('GENERATE '+name+'\n').encode());deadline=start+60*1000000000
        occ['generation_start_ns']=start;occ['generation_deadline_ns']=deadline
        raw=svc.reader.line(deadline/1e9);received=time.monotonic_ns()
        occ['response_received_ns']=received
        # Preserve the exact bounded frame before interpreting content or termination.
        R.save(stem.with_suffix('.response.json'),raw)
        C.require(received<=deadline and len(raw)<=p['limits']['max_raw_frame_bytes'],'RESPONSE_LATE_OR_LARGE')
        close=life.disarm(timer,min(svc.deadline,time.monotonic()+30));occ['watchdog_closed_ns']=close['closed_ns']
        response=C.strict_json(raw)
        # The full independent frame validator also checks exact slot, token IDs,
        # configuration/runtime, UTF-8/base64 and EOS-or-cap consistency.  No
        # subsequent PREPARE can occur before this and watchdog closure pass.
        K.check_live_response(response,sr,p,full_binding,slot,row['input_ids'])
        text=response['text'].encode('utf-8');C.require(len(text)<=p['limits']['max_response_utf8_bytes'],'RESPONSE_TEXT_BOUND')
        R.save(stem.with_suffix('.utf8'),text)
        occ['status']='length_terminated' if response.get('stop_reason')=='token_limit' else 'completed'
        C.require(occ['watchdog_closed_ns']>=received,'WATCHDOG_CLOSURE_ORDER')
    svc.send(b'FINISH\n');end=svc.reader.line(svc.deadline);R.save(evidence/'session-end.json',end)
    C.require(C.strict_json(end)=={'record_type':'q3_session_end_v1','binding':full_binding,'completed_calls':203},'SESSION_END')


def output_destination(C,env):
    uid=int(env.get('SUDO_UID','-1'));gid=int(env.get('SUDO_GID','-1'))
    C.require(0<uid<2**31 and 0<gid<2**31,'OUTPUT_OWNER')
    base=Path(env['RUNNER_TEMP']).absolute()
    C.require(base.is_dir() and not any(p.is_symlink() for p in [base,*base.parents]),'OUTPUT_PARENT')
    parent=base/'q3-reference-capture'
    try:parent.mkdir(mode=0o700);os.chmod(parent,0o700);os.chown(parent,uid,gid)
    except FileExistsError:pass
    st=parent.lstat();C.require(stat.S_ISDIR(st.st_mode) and st.st_uid==uid and stat.S_IMODE(st.st_mode)==0o700,'OUTPUT_PARENT_MODE')
    target=parent/(env['GITHUB_RUN_ID']+'-1')
    target.mkdir(mode=0o700);os.chmod(target,0o700)
    C.require(stat.S_IMODE(target.lstat().st_mode)==0o700,'OUTPUT_DIRECTORY_MODE')
    return target,uid,gid


def build_carrier(C,data,request,status,error):
    C.require('result.json' not in data,'RESULT_RECURSION')
    result={'record_type':'q3_native_capture_result_v1','mode':request['mode'],'status':status,'error_code':error,
            'source_commit':request['source_commit'],'request_sha256':C.digest(data['request.json']),
            'inventory':{n:{'size_bytes':len(b),'sha256':C.digest(b)} for n,b in sorted(data.items())},'claims':dict(C.CLAIMS)}
    all_data={**data,'result.json':C.encode(result)}
    C.require(sum(map(len,all_data.values()))<=256*1024*1024 and len(all_data)<=2000,'CARRIER_BOUND')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as z:
        for name,raw in sorted(all_data.items()):
            C.relative(name);info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.external_attr=(stat.S_IFREG|0o600)<<16
            z.writestr(info,raw)
    return out.getvalue(),result


def publish(C,K,snapshot,output,uid,gid,data,request,status,error):
    archive,result=build_carrier(C,data,request,status,error)
    directory=os.open(output,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    ds=os.fstat(directory);directory_identity=(ds.st_dev,ds.st_ino);owned={}
    def unchanged_directory():
        now=output.lstat()
        C.require(stat.S_ISDIR(now.st_mode) and (now.st_dev,now.st_ino)==directory_identity,'PUBLICATION_DIRECTORY_CHANGED')
    def create(name,raw):
        unchanged_directory();C.write_new(output/name,raw)
        st=os.stat(name,dir_fd=directory,follow_symlinks=False)
        owned[name]=(st.st_dev,st.st_ino)
        unchanged_directory()
    try:
        create('evidence.zip',archive)
        checked=K.check_carrier(output/'evidence.zip',snapshot,C.digest(archive),
                                C.digest(data['request.json']),request['source_commit'])
        C.require(checked['complete']==(status=='complete'),'FINAL_CARRIER_CHECK')
        receipt={'record_type':'q3_native_capture_receipt_v1','status':status,'mode':request['mode'],
                 'archive_sha256':C.digest(archive),'archive_size_bytes':len(archive),
                 'result_sha256':C.digest(C.encode(result)),'request_sha256':C.digest(data['request.json']),
                 'source_commit':request['source_commit'],'token_map_sha256':C.digest(data['token-map.json']) if 'token-map.json' in data else None,
                 'claims':dict(C.CLAIMS)}
        if status=='incomplete':
            create('failure.json',C.encode({'record_type':'q3_native_failure_v1','error_code':error,'complete':False,'claims':dict(C.CLAIMS)}))
        create('receipt.json',C.encode(receipt))
        for name,identity in owned.items():
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
            try:
                st=os.fstat(fd)
                C.require(stat.S_ISREG(st.st_mode) and (st.st_dev,st.st_ino)==identity,'PUBLISHED_MEMBER_REPLACED')
                # Change only the retained owned object, never a substituted pathname.
                os.fchown(fd,uid,gid);os.fchmod(fd,0o600);os.fsync(fd)
                st=os.fstat(fd);at=os.stat(name,dir_fd=directory,follow_symlinks=False)
                C.require((at.st_dev,at.st_ino)==identity and st.st_uid==uid and st.st_gid==gid
                          and stat.S_IMODE(st.st_mode)==0o600,'PUBLISHED_MEMBER_CUSTODY')
            finally:os.close(fd)
        unchanged_directory();os.fchown(directory,uid,gid);os.fchmod(directory,0o700)
        C.require(C.safe_read(output/'evidence.zip',256*1024*1024)==archive
                  and C.safe_read(output/'receipt.json')==C.encode(receipt),'PUBLISHED_READBACK')
        st=os.fstat(directory)
        C.require(st.st_uid==uid and st.st_gid==gid and stat.S_IMODE(st.st_mode)==0o700,'PUBLISHED_DIRECTORY_CUSTODY')
        unchanged_directory();os.fsync(directory)
        return receipt
    except BaseException:
        # A replacement is preserved; absence/partial publication is never success.
        for name,identity in reversed(list(owned.items())):
            try:
                st=os.stat(name,dir_fd=directory,follow_symlinks=False)
                if (st.st_dev,st.st_ino)==identity:os.unlink(name,dir_fd=directory)
            except OSError:pass
        raise
    finally:os.close(directory)


def setup_workspace(C,snapshot,work):
    """No subject has started here. Never recursively remove an unowned replacement."""
    identity=None
    try:
        work.mkdir(mode=0o700)
        st=work.lstat();identity=(st.st_dev,st.st_ino)
        os.chmod(work,0o700,follow_symlinks=False)
        sources=work/'source';sources.mkdir(mode=0o755);os.chmod(sources,0o755)
        for name,b in snapshot.items():
            path=sources/name;path.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
            for parent in path.parents:
                if parent==work:break
                os.chmod(parent,0o755,follow_symlinks=False)
            C.write_new(path,b,0o444)
        R=load_sealed('q3_verified_runtime',sources/RUNTIME)
        K=load_sealed('q3_verified_independent_checker',sources/CHECKER)
        R.freeze(sources);os.chmod(work,0o755)
        evidence=R.private_directory(work/'evidence',mode=0o755)
        logs=R.private_directory(work/'private')
        return R,K,sources,evidence,logs
    except BaseException as exc:
        cleaned=False
        if identity is not None:
            try:
                st=work.lstat()
                if stat.S_ISDIR(st.st_mode) and (st.st_dev,st.st_ino)==identity:
                    shutil.rmtree(work);cleaned=not work.exists() and not work.is_symlink()
            except OSError:pass
        # Retain original failure and explicit uncertain-cleanup state separately.
        err=EntryRejected(failure_code(exc));err.cleanup_complete=cleaned
        raise err from exc


def setup_failure(C,output,uid,gid,request,exc):
    record={'record_type':'q3_native_setup_failure_v1','complete':False,
            'error_code':failure_code(exc),'cleanup_complete':getattr(exc,'cleanup_complete',False),
            'source_commit':request['source_commit'],'claims':dict(C.CLAIMS)}
    raw=C.encode(record);path=output/'failure.json';C.write_new(path,raw)
    st=path.lstat();identity=(st.st_dev,st.st_ino)
    try:
        os.chown(path,uid,gid,follow_symlinks=False);os.chmod(path,0o600,follow_symlinks=False)
        os.chown(output,uid,gid,follow_symlinks=False);os.chmod(output,0o700,follow_symlinks=False)
        st=path.lstat();C.require((st.st_dev,st.st_ino)==identity and st.st_uid==uid and st.st_gid==gid
                                 and stat.S_IMODE(st.st_mode)==0o600 and C.safe_read(path)==raw,'FAILURE_CUSTODY')
        fd=os.open(output,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(fd)
        finally:os.close(fd)
    except BaseException:
        # No success receipt was created; a failed failure-report handoff remains a failure.
        raise
    return 1


def historical_metadata(C,plan,run_raw,jobs_raw,artifact_raw,image_raw):
    """Reject a different, expired or retried history before downloading bytes."""
    old=plan['historical_capture']
    run=C.strict_json(run_raw);jobs=C.strict_json(jobs_raw)
    C.require(type(run) is dict and type(jobs) is dict,'HISTORICAL_METADATA_SHAPE')
    C.require(type(run.get('id')) is int and str(run['id'])==old['run_id']
              and type(run.get('run_attempt')) is int and run['run_attempt']==1
              and run.get('head_sha')==old['source_commit'] and run.get('head_branch')=='main'
              and run.get('event')=='workflow_dispatch' and run.get('status')=='completed'
              and run.get('conclusion')=='failure'
              and run.get('path','').split('@',1)[0]=='.github/workflows/q3_reference_acquisition_v0.yml'
              and run.get('actor',{}).get('login')=='HKati'
              and run.get('triggering_actor',{}).get('login')=='HKati'
              and run.get('repository',{}).get('full_name')==REPOSITORY,
              'HISTORICAL_RUN_IDENTITY')
    C.require(type(jobs.get('total_count')) is int and jobs['total_count']==1
              and type(jobs.get('jobs')) is list and len(jobs['jobs'])==1,'HISTORICAL_JOB_SCOPE')
    job=jobs['jobs'][0]
    C.require(type(job) is dict and type(job.get('id')) is int and job['id']==old['job_id']
              and type(job.get('run_id')) is int and str(job['run_id'])==old['run_id']
              and type(job.get('run_attempt')) is int and job['run_attempt']==1
              and job.get('head_sha')==old['source_commit'] and job.get('name')=='acquire'
              and job.get('status')=='completed' and job.get('conclusion')=='failure',
              'HISTORICAL_JOB_IDENTITY')
    projected=[]
    for raw,key in ((artifact_raw,'capture_artifact'),(image_raw,'runner_image_artifact')):
        fixed=old[key];a=C.strict_json(raw)
        C.require(type(a) is dict and type(a.get('id')) is int and a['id']==fixed['artifact_id']
                  and a.get('name')==fixed['name'] and a.get('expired') is False
                  and type(a.get('size_in_bytes')) is int and a['size_in_bytes']==fixed['size_bytes']
                  and a.get('digest')=='sha256:'+fixed['sha256']
                  and type(a.get('workflow_run')) is dict
                  and str(a['workflow_run'].get('id'))==old['run_id']
                  and a['workflow_run'].get('head_sha')==old['source_commit'],
                  'HISTORICAL_ARTIFACT_IDENTITY')
        expires=a.get('expires_at')
        C.require(type(expires) is str and expires.endswith('Z'),'HISTORICAL_EXPIRY')
        expiry=datetime.datetime.fromisoformat(expires.replace('Z','+00:00'))
        C.require(expiry>datetime.datetime.now(datetime.timezone.utc),'HISTORICAL_EXPIRED')
        projected.append({'id':a['id'],'name':a['name'],'size_bytes':a['size_in_bytes'],
                          'sha256':fixed['sha256'],'expired':False,'expires_at':expires,
                          'run_id':old['run_id'],'source_commit':old['source_commit']})
    return {'run_id':old['run_id'],'run_attempt':1,'source_commit':old['source_commit'],
            'job_id':old['job_id'],'run_conclusion':'failure','job_conclusion':'failure',
            'artifacts':projected}


def acquire_historical(C,R,sources,snapshot,token,evidence,raw,request,env,phase_deadline):
    """One fixed historical selection, fresh GETs, unchanged original carriers."""
    plan=C.load_amendment(snapshot);old=plan['historical_capture']
    A=load_sealed('q3_historical_readonly_acquirer',sources/POSTFLIGHT_READER)
    reader=A.GitHubReader(token)
    base='/repos/'+REPOSITORY+'/actions/'
    routes={
        'run':base+'runs/'+old['run_id']+'/attempts/1',
        'jobs':base+'runs/'+old['run_id']+'/attempts/1/jobs?per_page=100&page=1',
        'artifact':base+'artifacts/'+str(old['capture_artifact']['artifact_id']),
        'image-artifact':base+'artifacts/'+str(old['runner_image_artifact']['artifact_id']),
    }
    data={}
    def metadata(when):
        result={}
        for kind,path in routes.items():
            C.require(time.monotonic()<phase_deadline,'HISTORICAL_ACQUISITION_DEADLINE')
            body=reader.json(path);name='historical/'+kind+'.'+when+'.json'
            R.save(evidence/name,body);data[name]=body;result[kind]=body
        return historical_metadata(C,plan,result['run'],result['jobs'],result['artifact'],result['image-artifact'])
    before=metadata('before')
    for key,name in (('capture_artifact','capture-artifact.zip'),('runner_image_artifact','runner-image-artifact.zip')):
        fixed=old[key]
        C.require(time.monotonic()<phase_deadline,'HISTORICAL_ACQUISITION_DEADLINE')
        body=reader.download(base+'artifacts/'+str(fixed['artifact_id'])+'/zip',fixed['size_bytes'])
        C.require(len(body)==fixed['size_bytes'] and C.digest(body)==fixed['sha256'],'HISTORICAL_CARRIER_MISMATCH')
        name='historical/'+name;R.save(evidence/name,body);data[name]=body
    after=metadata('after')
    C.require(C.encode(before)==C.encode(after),'HISTORICAL_METADATA_CHANGED')
    C.require(time.monotonic()<phase_deadline,'HISTORICAL_ACQUISITION_DEADLINE')
    acquisition={
        'record_type':'q3_historical_acquisition_v1',
        'current_binding':{'request_sha256':C.digest(raw),'source_commit':request['source_commit'],
                           'run_id':env['GITHUB_RUN_ID'],'run_attempt':1,'controller_sha256':C.digest(snapshot[SELF])},
        'selection':{'run_id':old['run_id'],'run_attempt':1,'job_id':old['job_id'],
                     'source_commit':old['source_commit'],'artifact_id':old['capture_artifact']['artifact_id'],
                     'image_artifact_id':old['runner_image_artifact']['artifact_id']},
        'inventory':{name:{'size_bytes':len(body),'sha256':C.digest(body)} for name,body in sorted(data.items())},
        'claims':dict(C.CLAIMS),
    }
    R.save(evidence/'historical/current-acquisition.json',C.encode(acquisition))


def verify_historical_before_worker(C,R,life,sources,snapshot,work,bundle,venv,python,logs,evidence,deadline,request):
    """Decode the old singleton with no causal model, then require service closure."""
    checking=R.private_directory(work/'historicalcheck',uid=65534,gid=65534)
    R.phase(life,work.name,'historicalcheck',
        [venv/'bin/python','-I','-B',sources/HISTORICAL,'--phase','verify-tokens',
         '--source-root',sources,'--bundle',bundle,'--evidence',evidence,
         '--output',checking/'historical-verification.json'],
        checking,python,logs,deadline,evidence)
    R.freeze(checking)
    receipt=C.safe_read(checking/'historical-verification.json')
    # A phase must return and close before this receipt can reach prelaunch.
    closed=C.strict_json(C.safe_read(evidence/'historicalcheck-cleanup.json'))
    C.require(closed.get('launch_attempted') is True and closed.get('client_reaped') is True
              and closed.get('cgroup_empty_or_removed') is True
              and closed.get('unit')==work.name+'-historicalcheck.service','HISTORICAL_PHASE_CLEANUP')
    R.save(evidence/'historical-verification.json',receipt)
    selected=C.digest(receipt)
    if request['mode']=='capture':
        C.require(selected==request['historical_verification_sha256'],'HISTORICAL_APPROVAL_MISMATCH')
    for name,body in snapshot.items():C.require(C.safe_read(sources/name)==body,'SEALED_SOURCE_CHANGED')
    return selected


def execute(C,p,request,snapshot,root,raw,env):
    # No helper import or network operation before entry_guard returns.
    # Inactive candidate configuration fails before even a control-plane query.
    transport_source=runtime_transport_plan(C,p)
    token=env.get('GITHUB_TOKEN','');C.require(bool(token),'READ_TOKEN_REQUIRED')
    plane=control_plane(C,request,env,token)
    output,uid,gid=output_destination(C,env)
    work=Path('/var/lib')/('pulse-q3-'+uuid.uuid4().hex[:24])
    try:
        R,K,sources,evidence,logs=setup_workspace(C,snapshot,work)
    except BaseException as exc:
        return setup_failure(C,output,uid,gid,request,exc)
    life=R.Lifecycle();phase_deadline=time.monotonic()+p['limits']['acquisition_phase_seconds']
    full_frame=C.task_frame(snapshot,p)
    frame=full_frame if request['mode']=='token-preflight' else C.continuation_frame(snapshot,p)
    status='incomplete';error='CAPTURE_INCOMPLETE';svc=None;terminal=None;data={}
    original_signal={}
    def interrupted(signum,frame):raise KeyboardInterrupt()
    for signum in (signal.SIGTERM,signal.SIGINT):
        original_signal[signum]=signal.signal(signum,interrupted)
    try:
        R.save(evidence/'request.json',raw)
        R.save(evidence/'control-plane.json',C.encode(plane))
        for name,b in snapshot.items():R.save(evidence/'source'/name,b)
        acquire_historical(C,R,sources,snapshot,token,evidence,raw,request,env,phase_deadline)
        platform=R.platform_context();R.save(evidence/'platform.json',C.encode(platform))
        C.require(shutil.disk_usage(work).free>=6*1024**3,'INSUFFICIENT_WORK_DISK')
        archive=work/'runtime.zip';transport=download_runtime(C,p,token,archive,phase_deadline)
        C.require(transport['transport']==transport_source,'RUNTIME_TRANSPORT_SOURCE_DRIFT')
        transport['binding']={'request_sha256':C.digest(raw),'source_commit':request['source_commit'],
                              'run_id':env['GITHUB_RUN_ID'],'run_attempt':1,
                              'controller_sha256':C.digest(snapshot[SELF])}
        transport_raw=C.encode(transport);R.save(evidence/'runtime-transport.json',transport_raw)
        # Immutable selected bytes are inspected; archive code is never executed here.
        checked=K.verify_archive(archive,work/'staged',sources)
        R.save(evidence/'input-check.json',C.encode(checked))
        bundle=work/'staged/bundle';R.freeze(work/'staged');os.chmod(work/'staged',0o755);os.chmod(bundle,0o755)
        python=Path(sys.executable).resolve()
        install=R.private_directory(work/'install',uid=65534,gid=65534)
        R.phase(life,work.name,'installer',[python,'-I','-B','-c',R.INSTALLER,install,bundle/'wheelhouse',sources/'PULSE_safe_pack_v0/requirements-q2-reference-v0.lock',install],
                install,python,logs,phase_deadline,evidence)
        venv=install/'venv';R.freeze(install);os.chmod(install,0o755)
        for name in ['bootstrap.json','pip-report.json']:R.save(evidence/name,C.safe_read(install/name))
        checking=R.private_directory(work/'installcheck',uid=65534,gid=65534)
        R.phase(life,work.name,'installcheck',[python,'-I','-B',sources/CHECKER,'--phase','verify-installation',
            '--source-root',sources,'--venv',venv,'--bundle',bundle,'--bootstrap-inventory',evidence/'bootstrap.json',
            '--pip-report',evidence/'pip-report.json','--output',checking/'installation.json'],
            checking,python,logs,phase_deadline,evidence)
        R.freeze(checking);installation=C.safe_read(checking/'installation.json')
        R.save(evidence/'installation.json',installation)
        historical_sha=verify_historical_before_worker(C,R,life,sources,snapshot,work,bundle,venv,
            python,logs,evidence,phase_deadline,request)
        pre={'record_type':'q3_native_prelaunch_v1','request':request,'source_commit':request['source_commit'],
             'run_id':env['GITHUB_RUN_ID'],'run_attempt':1,'source_files':{n:C.digest(b) for n,b in snapshot.items()},
             'platform_sha256':C.digest(C.encode(platform)),'control_plane_sha256':C.digest(C.encode(plane)),
             'installation_sha256':C.digest(installation),
             'runtime_transport_sha256':C.digest(transport_raw),
             'historical_verification_sha256':historical_sha,
             'historical_phase_cleanup_sha256':C.digest(C.safe_read(evidence/'historicalcheck-cleanup.json')),
             'historical_acquisition_sha256':C.digest(C.safe_read(evidence/'historical/current-acquisition.json')),
             'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'clock_relation':'not_verified'}
        pre_raw=C.encode(pre);R.save(evidence/'prelaunch.json',pre_raw)
        binding={'prelaunch_sha256':C.digest(pre_raw),'source_commit':request['source_commit'],
                 'run_id':env['GITHUB_RUN_ID'],'run_attempt':1}
        terminal={'record_type':'q3_capture_terminal_v1','mode':request['mode'],'binding':binding,
                  'complete':False,'error_code':'CAPTURE_INCOMPLETE','attempted_calls':0,
                  'occurrences':[{'task_id':t['task_id'],'ordinal':t['ordinal'],'attempt':1,
                   **({'continuation_ordinal':t['continuation_ordinal']} if request['mode']=='capture' else {}),
                   'status':'not_requested' if request['mode']=='token-preflight' else 'not_started'} for t in frame],
                  'worker_exit_code':None,'stdout_eof':False,'worker_deadline_ns':None,
                  'worker_exit_observed_ns':None,'ended_at':None}
        worker_work=R.private_directory(work/'worker',uid=65534,gid=65534)
        stage='preflight' if request['mode']=='token-preflight' else 'captureworker'
        svc=life.start(work.name,stage,[venv/'bin/python','-I','-B',sources/WORKER,'--source-root',sources,
                    '--bundle',bundle,'--prelaunch',evidence/'prelaunch.json','--expected-prelaunch-sha256',C.digest(pre_raw)],
                    worker_work,python,logs/'worker.log',phase_deadline)
        terminal['worker_deadline_ns']=svc.runtime_deadline_ns
        R.save(evidence/'worker-sandbox.json',C.encode(svc.observation))
        token_map,map_sha=receive_tokens(C,R,svc,full_frame,{**p,'_mode':request['mode']},evidence,binding)
        if request['mode']=='token-preflight':
            svc.send(b'FINISH\n');end=svc.reader.line(svc.deadline);R.save(evidence/'session-end.json',end)
            C.require(C.strict_json(end)=={'record_type':'q3_session_end_v1','binding':binding,'completed_calls':0},'PREFLIGHT_SESSION_END')
        else:
            C.require(map_sha==request['approved_token_map_sha256'],'APPROVED_TOKEN_MAP_MISMATCH')
            exchange_capture(C,R,K,life,svc,p,frame,token_map,binding,evidence,terminal,work.name,historical_sha)
        svc.complete();terminal.update(worker_exit_code=0,stdout_eof=True,
            worker_exit_observed_ns=time.monotonic_ns(),ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        C.require(terminal['worker_exit_observed_ns']<=terminal['worker_deadline_ns'],'WORKER_TERMINAL_LATE')
        closed=svc.close(min(phase_deadline,time.monotonic()+30));R.save(evidence/'worker-cleanup.json',C.encode(closed))
        terminal.update(complete=True,error_code=None)
        R.save(evidence/'terminal.json',C.encode(terminal))
        decode=R.private_directory(work/'decodecheck',uid=65534,gid=65534)
        R.phase(life,work.name,'decodecheck',[venv/'bin/python','-I','-B',sources/CHECKER,'--phase','verify-tokens',
            '--source-root',sources,'--bundle',bundle,'--evidence',evidence,'--output',decode/'token-check.json'],
            decode,python,logs,phase_deadline,evidence)
        R.freeze(decode);R.save(evidence/'token-check.json',C.safe_read(decode/'token-check.json'))
        if request['mode']=='capture':R.save(evidence/'examples.jsonl',C.safe_read(decode/'examples.jsonl'))
        for name,b in snapshot.items():C.require(C.safe_read(sources/name)==b,'SEALED_SOURCE_CHANGED')
        C.require(time.monotonic()<=phase_deadline,'PHASE_DEADLINE')
        status='complete';error=None
    except BaseException as exc:
        error=failure_code(exc)
        if terminal is not None:
            terminal.update(complete=False,error_code=error)
            if svc is not None and svc.reader is not None and svc.reader.buffer:
                try:R.save(evidence/'unfinished-protocol-prefix.bin',svc.reader.buffer[:1024*1024])
                except Exception:pass
    finally:
        # Preserve the first failure while bounded cleanup runs. Outer workflow/timeout
        # still supplies a hard kill if this process cannot complete its grace.
        for sig in original_signal:signal.signal(sig,signal.SIG_IGN)
        cleanup=life.cleanup()
        if not cleanup['cleanup_complete']:
            status='incomplete';error=error or 'CLEANUP_UNVERIFIED'
        if terminal is not None and not (evidence/'terminal.json').exists():
            try:R.save(evidence/'terminal.json',C.encode(terminal))
            except Exception:status='incomplete';error=error or 'TERMINAL_PRESERVATION_FAILED'
        try:data=K.read_evidence(evidence)
        except Exception:
            status='incomplete';error=error or 'EVIDENCE_READBACK_FAILED';data={'request.json':raw}
        removed=False
        if cleanup['cleanup_complete']:
            try:shutil.rmtree(work);removed=not work.exists() and not work.is_symlink()
            except Exception:pass
        else:
            try:os.chmod(work,0o700)
            except OSError:pass
        cleanup['private_tree_removed']=removed
        data['lifecycle.json']=C.encode(cleanup)
        if not removed:status='incomplete';error=error or 'PRIVATE_TREE_CLEANUP_FAILED'
        try:
            if status=='complete':K.validate_complete(snapshot,data)
        except Exception as exc:status='incomplete';error=failure_code(exc)
        if status!='complete':
            # Diagnostics never enter the closed complete-carrier format or
            # replace the first execution failure. They also survive successful
            # cleanup following an incomplete generation.
            details=getattr(life,'cleanup_details',None)
            if details is not None:data['lifecycle-diagnostics.json']=C.encode(details)
        try:receipt=publish(C,K,snapshot,output,uid,gid,data,request,status,error)
        finally:
            for sig,old in original_signal.items():signal.signal(sig,old)
    print('Q3 '+request['mode']+' '+status+'; no labels, metric or release authority.')
    return 0 if status=='complete' else 1



# The versioned native core is reached through this mandatory capture handoff.
# A saved approval does not bypass fresh current-controller acquisition/admission.
HANDOFF_SOURCE='tools/q3_capture_handoff_v2.py'
HANDOFF_SOURCES=('schemas/metrics/q3_capture_handoff_request_v2.schema.json',
                 'tools/acquire_q3_external_postflight_v1.py',
                 'tools/check_q3_external_postflight_v1.py',
                 'tools/q3_capture_handoff_v2.py')


def execute_handoff(C,p,request,snapshot,root,raw,env):
    # A missing payload source is not a reason to acquire or compare an old
    # preflight, and never activates a fallback to the original artifact.
    runtime_transport_plan(C,p)
    extra={}
    for name in HANDOFF_SOURCES:
        b=boot_read(root/name,128*1024)
        entry_require(boot_git(root,['cat-file','blob',request['source_commit']+':'+name])==b)
        extra[name]=b
    mod=types.ModuleType('q3_verified_capture_handoff_v2');mod.__file__=str(root/HANDOFF_SOURCE)
    exec(compile(extra[HANDOFF_SOURCE],mod.__file__,'exec',dont_inherit=True),mod.__dict__)
    entry_require(tuple(mod.EXTRA_SOURCES)==HANDOFF_SOURCES)
    return mod.run(C,p,request,snapshot,root,raw,env,extra,execute,control_plane,output_destination)


# Same-job runner-image observations. These records do not authorize execution.
# Keep this stdlib code in the already source-bound native controller: no new
# executable dependency is silently added to the closed native-v0 source list.
IMAGE_RECORD = 'q3_runner_image_observation_v0'
IMAGE_REPORT = 'q3_runner_image_comparison_v0'
IMAGE_STAGES = ('initial', 'pre-sudo', 'root-entry')
IMAGE_FILES = ('initial.json', 'pre-sudo.json', 'root-entry.json', 'comparison.json')
IMAGE_MAX = 256 * 1024


def image_binding(C, request, raw, env):
    C.require(env.get('GITHUB_JOB') == 'acquire', 'RUNNER_IMAGE_JOB')
    return {'repository': REPOSITORY, 'workflow': WORKFLOW, 'job_key': 'acquire',
            'run_id': env['GITHUB_RUN_ID'], 'run_attempt': 1,
            'source_commit': request['source_commit'], 'request_sha256': C.digest(raw)}


def image_directory(C, env, *, initial=False):
    """Use only the current run's fixed directory; no user-selected report path."""
    base = Path(env.get('RUNNER_TEMP', ''))
    C.require(base.is_absolute() and str(base) != '/' and not any(
        x.is_symlink() for x in (base, *base.parents)), 'RUNNER_IMAGE_OUTPUT_PATH')
    C.require(base.is_dir(), 'RUNNER_IMAGE_OUTPUT_PATH')
    run = env.get('GITHUB_RUN_ID', '')
    C.require(re.fullmatch(r'[1-9][0-9]{0,19}', run) is not None
              and env.get('GITHUB_RUN_ATTEMPT') == '1', 'RUNNER_IMAGE_RUN')
    parent = base / 'q3-runner-image'
    parent.mkdir(mode=0o700, exist_ok=True)
    C.require(not parent.is_symlink() and parent.is_dir(), 'RUNNER_IMAGE_OUTPUT_PATH')
    target = parent / (run + '-1')
    # Initial acquisition never replaces another attempt's observations.
    target.mkdir(mode=0o700, exist_ok=not initial)
    C.require(not target.is_symlink() and target.is_dir(), 'RUNNER_IMAGE_OUTPUT_PATH')
    return target


def image_proc_identity(pid, proc_root=Path('/proc')):
    """Bounded procfs parsing; start ticks distinguish a reused PID."""
    with (proc_root / str(pid) / 'stat').open('rb') as f:
        raw = f.read(16385)
    if len(raw) > 16384 or not raw.startswith((str(pid) + ' (').encode()):
        raise ValueError('RUNNER_IMAGE_WORKER')
    tail = raw.rpartition(b') ')[2].split()
    if len(tail) < 20 or not tail[1].isdigit() or not tail[19].isdigit():
        raise ValueError('RUNNER_IMAGE_WORKER')
    return int(tail[1]), int(tail[19])


def image_worker(proc_root=Path('/proc'), start_pid=None):
    """Resolve .setup_info from the actual ancestor Runner.Worker instance.

    Never search a cache, scan unrelated processes or choose the first filename.
    proc_root/start_pid are Python test seams, not accepted CLI arguments.
    """
    pid = os.getpid() if start_pid is None else start_pid
    seen = set()
    for _ in range(64):
        if type(pid) is not int or pid <= 0 or pid in seen:
            break
        seen.add(pid)
        parent, ticks = image_proc_identity(pid, proc_root)
        # An unreadable ancestor executable is an incomplete observation, not
        # permission to skip an unknown process and select another instance.
        executable = os.readlink(proc_root / str(pid) / 'exe')
        path = Path(executable)
        if path.name == 'Runner.Worker':
            if (not path.is_absolute() or ' (deleted)' in executable
                    or not re.fullmatch(r'bin(?:\.[0-9]+(?:\.[0-9]+){1,3})?', path.parent.name)):
                raise ValueError('RUNNER_IMAGE_WORKER')
            disk = path.stat()
            running = (proc_root / str(pid) / 'exe').stat()
            if (disk.st_dev, disk.st_ino) != (running.st_dev, running.st_ino):
                raise ValueError('RUNNER_IMAGE_WORKER')
            if image_proc_identity(pid, proc_root) != (parent, ticks):
                raise ValueError('RUNNER_IMAGE_WORKER')
            return {'pid': pid, 'start_ticks': ticks, 'executable': executable}, path.parent.parent
        pid = parent
    raise ValueError('RUNNER_IMAGE_WORKER')


def image_environment(env):
    """Only two allowlisted fields; invalid raw values are never published."""
    image_os = env.get('ImageOS')
    version = env.get('ImageVersion')
    valid_os = type(image_os) is str and re.fullmatch(r'ubuntu[0-9]{2}', image_os) is not None
    valid_version = (type(version) is str and len(version) <= 128
                     and re.fullmatch(r'[0-9]{8}\.[0-9]+\.[0-9]+', version) is not None)
    return {'image_os': image_os if valid_os else None,
            'image_version': version if valid_version else None}, valid_os and valid_version


def image_group(C, raw):
    """Extract exactly one Runner Image group, not Runner Image Provisioner."""
    data = C.strict_json(raw, IMAGE_MAX)
    C.require(type(data) is list and 0 < len(data) <= 64, 'RUNNER_IMAGE_GROUP')
    matches = []
    for item in data:
        C.require(type(item) is dict, 'RUNNER_IMAGE_GROUP')
        # JSON.NET's upstream reader is case-insensitive. Accept the two known
        # serializations, but reject ambiguous duplicate aliases explicitly.
        groups = [item[k] for k in ('group', 'Group') if k in item]
        C.require(len(groups) <= 1, 'RUNNER_IMAGE_GROUP')
        if groups == ['Runner Image']:
            details = [item[k] for k in ('detail', 'Detail') if k in item]
            C.require(len(details) == 1 and type(details[0]) is str, 'RUNNER_IMAGE_GROUP')
            matches.append(details[0])
    C.require(len(matches) == 1, 'RUNNER_IMAGE_GROUP')
    lines = matches[0].replace('\r\n', '\n').split('\n')
    values = {}
    for label in ('Image', 'Version'):
        # Collect all label occurrences before validating complete values.
        found = re.findall(r'^[ \t]*' + label + r':([^\r\n]*)$', '\n'.join(lines), re.M)
        C.require(len(found) == 1 and found[0].startswith(' '), 'RUNNER_IMAGE_FIELD')
        values[label] = found[0][1:]
    C.require(re.fullmatch(r'ubuntu-[0-9]{2}\.[0-9]{2}', values['Image']) is not None
              and len(values['Version']) <= 128
              and re.fullmatch(r'[0-9]{8}\.[0-9]+\.[0-9]+', values['Version']) is not None,
              'RUNNER_IMAGE_FIELD')
    return {'image': values['Image'], 'version': values['Version']}


def image_source(C, path):
    """Retain a digest of the source and only its allowed image fields."""
    record = {'sha256': None, 'size_bytes': None, 'image': None, 'version': None, 'error': None}
    try:
        raw = C.safe_read(path, IMAGE_MAX)
        record.update(sha256=C.digest(raw), size_bytes=len(raw))
        record.update(image_group(C, raw))
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        record['error'] = 'RUNNER_IMAGE_SOURCE_UNREADABLE_OR_INVALID'
    return record


def image_collect(C, env):
    environment, valid = image_environment(env)
    record = {'environment': environment, 'worker': None,
              'setup_info': None, 'imagedata': None, 'errors': []}
    if not valid:
        record['errors'].append('RUNNER_IMAGE_ENV_INVALID')
    try:
        worker, runner_root = image_worker()
        record['worker'] = worker
        record['setup_info'] = image_source(C, runner_root / '.setup_info')
        if image_worker()[0] != worker:
            record['errors'].append('RUNNER_IMAGE_WORKER_CHANGED')
    except (OSError, ValueError, KeyError, TypeError):
        record['errors'].append('RUNNER_IMAGE_WORKER_UNAVAILABLE')
    record['imagedata'] = image_source(C, Path('/imagegeneration/imagedata.json'))
    for name in ('setup_info', 'imagedata'):
        if record[name] is None or record[name]['error'] is not None:
            record['errors'].append('RUNNER_IMAGE_' + name.upper() + '_INCOMPLETE')
    return record


def image_observe(C, request, snapshot, raw, env, phase):
    C.require(phase in IMAGE_STAGES, 'RUNNER_IMAGE_STAGE')
    binding = image_binding(C, request, raw, env)
    directory = image_directory(C, env, initial=phase == 'initial')
    previous = None
    previous_error = None
    if phase != 'initial':
        prior = IMAGE_STAGES[IMAGE_STAGES.index(phase) - 1] + '.json'
        try:
            previous = C.digest(C.safe_read(directory / prior, IMAGE_MAX))
        except (OSError, ValueError):
            previous_error = 'RUNNER_IMAGE_PREVIOUS_MISSING'
    observed = image_collect(C, env)
    if previous_error:
        observed['errors'].append(previous_error)
    record = {'record_type': IMAGE_RECORD, 'phase': phase, 'binding': binding,
              'observer_sha256': C.digest(snapshot[SELF]), 'previous_sha256': previous,
              'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'observation': observed, 'authority_effect': 'none'}
    C.write_new(directory / (phase + '.json'), C.encode(record), mode=0o644)
    print('Q3_RUNNER_IMAGE_OBSERVATION ' + C.encode(record).decode('utf-8').rstrip('\n'), flush=True)
    return record, directory


def image_compare(C, records, binding, observer_sha):
    """Recompute from observations; a stored status/approval is not an input."""
    errors = []
    conflicts = []
    previous = None
    for phase in IMAGE_STAGES:
        raw = records.get(phase)
        try:
            r = C.strict_json(raw, IMAGE_MAX)
            C.fields(r, {'record_type', 'phase', 'binding', 'observer_sha256', 'previous_sha256',
                         'observed_at', 'observation', 'authority_effect'}, 'RUNNER_IMAGE_RECORD')
            C.require(r['record_type'] == IMAGE_RECORD and r['phase'] == phase
                      and C.encode(r['binding']) == C.encode(binding) and r['observer_sha256'] == observer_sha
                      and r['authority_effect'] == 'none' and r['previous_sha256'] == previous,
                      'RUNNER_IMAGE_BINDING')
            C.require(type(r['observed_at']) is str and len(r['observed_at']) <= 64,
                      'RUNNER_IMAGE_TIME')
            o = r['observation']
            C.fields(o, {'environment', 'worker', 'setup_info', 'imagedata', 'errors'}, 'RUNNER_IMAGE_RECORD')
            C.require(o['errors'] == [], 'RUNNER_IMAGE_INCOMPLETE')
            C.fields(o['environment'], {'image_os', 'image_version'}, 'RUNNER_IMAGE_RECORD')
            ev, ok = image_environment({'ImageOS': o['environment']['image_os'],
                                       'ImageVersion': o['environment']['image_version']})
            C.require(ok and ev == o['environment'], 'RUNNER_IMAGE_ENV_INVALID')
            worker = o['worker']
            C.fields(worker, {'pid', 'start_ticks', 'executable'}, 'RUNNER_IMAGE_WORKER')
            C.require(type(worker['pid']) is int and worker['pid'] > 0
                      and type(worker['start_ticks']) is int and worker['start_ticks'] > 0
                      and type(worker['executable']) is str
                      and worker['executable'].endswith('/Runner.Worker'), 'RUNNER_IMAGE_WORKER')
            versions = [ev['image_version']]
            for name in ('setup_info', 'imagedata'):
                src = o[name]
                C.fields(src, {'sha256', 'size_bytes', 'image', 'version', 'error'}, 'RUNNER_IMAGE_RECORD')
                C.require(src['error'] is None and C.sha256_string(src['sha256'])
                          and type(src['size_bytes']) is int and 0 < src['size_bytes'] <= IMAGE_MAX
                          and type(src['version']) is str and len(src['version']) <= 128
                          and re.fullmatch(r'[0-9]{8}\.[0-9]+\.[0-9]+', src['version']) is not None,
                          'RUNNER_IMAGE_SOURCE')
                if src['image'] != 'ubuntu-24.04':
                    conflicts.append(phase + ':IMAGE_LABEL')
                versions.append(src['version'])
            if ev['image_os'] != 'ubuntu24' or len(set(versions)) != 1:
                conflicts.append(phase + ':IMAGE_VALUES')
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
            errors.append(phase + ':INCOMPLETE_OR_INVALID')
        previous = C.digest(raw) if type(raw) is bytes else None
    if not errors:
        observations = [C.strict_json(records[s], IMAGE_MAX)['observation'] for s in IMAGE_STAGES]
        first = observations[0]
        for phase, o in zip(IMAGE_STAGES[1:], observations[1:]):
            if o['worker'] != first['worker']:
                conflicts.append(phase + ':WORKER_CHANGED')
            if o['environment'] != first['environment']:
                conflicts.append(phase + ':ENVIRONMENT_CHANGED')
            for name in ('setup_info', 'imagedata'):
                if o[name] != first[name]:
                    conflicts.append(phase + ':' + name.upper() + '_CHANGED')
    status = 'incomplete' if errors else 'contradictory' if conflicts else 'consistent'
    return {'record_type': IMAGE_REPORT, 'binding': binding, 'observer_sha256': observer_sha,
            'status': status, 'errors': errors, 'conflicts': conflicts,
            'observation_sha256': {s: C.digest(records[s]) if type(records.get(s)) is bytes else None
                                   for s in IMAGE_STAGES},
            'native_execution_started_at_comparison': False,
            'capture_handoff_approved': False, 'authority_effect': 'none'}


def image_gate(C, request, snapshot, raw, env):
    """Run at the supported root entry, before either native execution route."""
    _, directory = image_observe(C, request, snapshot, raw, env, 'root-entry')
    records = {}
    for phase in IMAGE_STAGES:
        try:
            records[phase] = C.safe_read(directory / (phase + '.json'), IMAGE_MAX)
        except (OSError, ValueError):
            records[phase] = None
    report = image_compare(C, records, image_binding(C, request, raw, env), C.digest(snapshot[SELF]))
    # Close the read/write interval; replacement is not silently accepted.
    for phase, prior in records.items():
        if prior is not None:
            try:
                unchanged = C.safe_read(directory / (phase + '.json'), IMAGE_MAX) == prior
            except (OSError, ValueError):
                unchanged = False
            if not unchanged:
                report['status'] = 'incomplete'
                report['errors'].append(phase + ':RECORD_CHANGED')
    C.write_new(directory / 'comparison.json', C.encode(report), mode=0o644)
    print('Q3_RUNNER_IMAGE_COMPARISON ' + C.encode(report).decode('utf-8').rstrip('\n'), flush=True)
    print('Q3 runner-image observation: ' + report['status'] + '; no execution permission in saved records.')
    C.require(report['status'] == 'consistent', 'RUNNER_IMAGE_' + report['status'].upper())
    return report


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--source-commit',required=True)
    ap.add_argument('--request',required=True);ap.add_argument('--request-sha256',required=True)
    ap.add_argument('--image-observation',choices=('initial','pre-sudo'))
    args=ap.parse_args(argv)
    try:
        raw=args.request.encode('utf-8');root=args.repo_root.absolute();env=dict(os.environ)
        C,p,request,snapshot=entry_guard(root,args.source_commit,raw,args.request_sha256,env,
                                       observation_only=args.image_observation is not None)
        if args.image_observation is not None:
            image_observe(C,request,snapshot,raw,env,args.image_observation)
            return 0
        image_gate(C,request,snapshot,raw,env)
        if request['mode']=='capture':
            return execute_handoff(C,p,request,snapshot,root,raw,env)
        return execute(C,p,request,snapshot,root,raw,env)
    except BaseException:
        print('Q3 rejected or final publication unavailable; no successful capture claimed.',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
