#!/usr/bin/env python3
"""Offline Q2 preparation and recorded input-pin regressions.

Protocol wheel/model payloads are synthetic. The input-pin tests inspect small
original metadata records from preparation run 37148637546, not model/wheel
payloads. No model download, import, generation, service call, installation or
native qualification is performed here. Synthetic expectations are confined
to protocol tests; no production CLI accepts synthetic provenance or models.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import zipfile

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "PULSE_safe_pack_v0/tools"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load_module("q2_preparation_under_test", TOOLS / "acquire_q2_reference_inputs_v0.py")
C = load_module("q2_preparation_checker_under_test", TOOLS / "check_q2_reference_capture_v0.py")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs): raise AssertionError("offline regression attempted networking")
    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(socket.socket, "connect", reject)


def git(repo, *args):
    result = subprocess.run(["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                             "-C", str(repo), *args], check=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env={"PATH": os.defpath, "HOME": str(repo),
                            "GIT_AUTHOR_NAME": "Synthetic Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                            "GIT_COMMITTER_NAME": "Synthetic Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"})
    return result.stdout.decode().strip()


def wheel_bytes(name, version, *, dependency=None, duplicate_name=False, bad_member=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as z:
        metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
        if duplicate_name: metadata += "Name: other\n"
        if dependency: metadata += f"Requires-Dist: {dependency}\n"
        z.writestr(f"{name}-{version}.dist-info/METADATA", metadata + "\nSynthetic protocol fixture.\n")
        z.writestr(f"{name}-{version}.dist-info/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        if bad_member: z.writestr(bad_member, b"synthetic")
    return stream.getvalue()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    repo = tmp_path / "source"; repo.mkdir()
    source = {}
    for rel in A.SOURCE_PATHS:
        raw = (ROOT / rel).read_bytes()
        target = repo / rel; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        source[rel] = raw
    git(repo, "init", "-q"); git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "Synthetic preparation fixture; not project history")
    source_sha = git(repo, "rev-parse", "HEAD")
    output = tmp_path / "prepared"; output.mkdir()
    for rel, data in source.items(): A.write_new(output / "source" / rel, data)
    config = {"bos_token_id": 1, "eos_token_id": 2, "pad_token_id": 2}
    payloads = {
        "config.json": A.encode(config), "generation_config.json": A.encode(config),
        "merges.txt": b"# Synthetic tokenizer fixture\na b\n",
        "model.safetensors": b"NOT A MODEL: synthetic preparation protocol fixture\n",
        "special_tokens_map.json": A.encode({"bos_token": "<|im_start|>", "eos_token": "<|im_end|>", "pad_token": "<|im_end|>"}),
        "tokenizer_config.json": A.encode({"bos_token": "<|im_start|>", "eos_token": "<|im_end|>",
                                           "pad_token": "<|im_end|>", "chat_template": "synthetic template"}),
        "tokenizer.json": A.encode({"added_tokens": [{"id": 1, "content": "<|im_start|>", "special": True},
                                                     {"id": 2, "content": "<|im_end|>", "special": True}]}),
        "vocab.json": A.encode({"synthetic": 3})}
    synthetic_weights_digest = A.digest(payloads["model.safetensors"])
    monkeypatch.setattr(A, "WEIGHTS_SHA256", synthetic_weights_digest)
    monkeypatch.setattr(C, "FIXED_WEIGHTS_SHA", synthetic_weights_digest)
    monkeypatch.setattr(C, "ORIGIN", "synthetic_protocol_fixture")
    siblings = []; model_rows = []
    for name in A.MODEL_FILES:
        data = payloads[name]; A.write_new(output / "model" / name, data)
        item = {"rfilename": name, "size": len(data),
                "blobId": hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()}
        if name == "model.safetensors": item["lfs"] = {"sha256": synthetic_weights_digest, "size": len(data)}
        siblings.append(item); model_rows.append(A.bind_model_file(name, data, item))
    A.write_new(output / "upstream/model.json", A.encode({"id": A.MODEL, "sha": A.REVISION, "siblings": siblings}))
    A.write_new(output / "q2_reference_model_files_v0.json", A.encode({
        "record_type": "q2_reference_model_files_candidate_v0", "model_repository": A.MODEL,
        "model_revision": A.REVISION, "files": model_rows, "authority_effect": "none",
        "native_runtime_qualified": False, "adopted": False}))
    wheel_rows = []
    for name, version in A.ROOTS.items():
        filename = A.TORCH_WHEEL if name == "torch" else f"{name}-{version}-py3-none-any.whl"
        data = wheel_bytes(name, version); sha = A.digest(data)
        A.write_new(output / "wheelhouse" / filename, data)
        if name == "torch":
            url = "https://download.pytorch.org/whl/cpu/" + filename.replace("+", "%2B")
            mp = "upstream/torch-cpu-index.html"
            A.write_new(output / mp, f'<a href="{url}#sha256={sha}">{filename}</a>'.encode())
        else:
            url = f"https://files.pythonhosted.org/packages/synthetic/{filename}"
            mp = f"upstream/pypi/{name}-{version}.json"
            A.write_new(output / mp, A.encode({"info": {"name": name, "version": version},
                "urls": [{"filename": filename, "url": url, "packagetype": "bdist_wheel", "yanked": False,
                          "digests": {"sha256": sha}}]}))
        wheel_rows.append({"name": name, "version": version, "path": f"wheelhouse/{filename}",
                           "size": len(data), "sha256": sha, "url": url, "upstream_metadata": mp})
    A.write_new(output / "requirements-q2-reference-v0.lock", A.lock_bytes(wheel_rows))
    report = {"record_type": "q2_reference_runtime_preparation_v0",
        "context": {"repository": A.REPOSITORY, "source_commit": source_sha, "workflow": A.WORKFLOW,
                    "run_id": "12345", "run_attempt": 1, "event": "workflow_dispatch", "actor": "HKati",
                    "python": "3.11.16", "architecture": "x86_64", "os": "ubuntu-24.04",
                    "runner_image": "synthetic-not-a-runner", "origin": "synthetic_protocol_fixture"},
        "roots": A.ROOTS, "state": copy.deepcopy(A.STATE), "wheels": wheel_rows,
        "source_paths": list(A.SOURCE_PATHS), "files": A.build_file_index(output)}
    A.write_new(output / "preparation.json", A.encode(report))
    return output, repo, source_sha


def verify(bundle, expected=None):
    output, repo, source_sha = bundle
    return C.inspect_bundle(output, expected or A.digest((output / "preparation.json").read_bytes()), source_sha, "12345", repo)


def report(bundle): return A.strict_json((bundle[0] / "preparation.json").read_bytes())


def replace_report(bundle, obj): (bundle[0] / "preparation.json").write_bytes(A.encode(obj))


def reindex(bundle):
    obj = report(bundle); path = bundle[0] / "preparation.json"; path.unlink()
    obj["files"] = A.build_file_index(bundle[0]); path.write_bytes(A.encode(obj))


def test_positive_synthetic_bundle_is_independently_reconstructed(bundle):
    result, wheels = verify(bundle)
    assert result["context"]["origin"] == "synthetic_protocol_fixture"
    assert len(wheels) == 4 and result["state"]["inference_executed"] is False


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
                                  b'{"x":"\\ud800"}', b'\xef\xbb\xbf{}', b'{"x":', b'\xff'])
@pytest.mark.parametrize("loader", [A.strict_json, C.load_json])
def test_both_json_readers_reject_ambiguous_or_malformed_data(raw, loader):
    with pytest.raises(ValueError): loader(raw)


def test_exact_authored_selection_bytes_are_kept():
    assert A.digest((ROOT / A.SELECTION).read_bytes()) == A.SELECTION_SHA256 == C.FIXED_SELECTION_SHA
    assert A.digest((ROOT / A.REQUESTS).read_bytes()) == A.REQUESTS_SHA256 == C.FIXED_REQUESTS_SHA
    selection = A.strict_json((ROOT / A.SELECTION).read_bytes())
    assert selection['release_subject']['definition']['generation']['bos_token_id'] == 1
    assert selection['request_protocol']['group_count'] == 50
    assert selection['request_protocol']['planned_call_count'] == 150


@pytest.mark.parametrize("key,new", [("authority_effect", "allow"), ("production_gate_eligible", True),
    ("inference_executed", True), ("native_runtime_qualified", True), ("materialized_subject_bound", True),
    ("capture_dispatch_authorized", True), ("dependency_closure_status", "accepted"), ("production_gate_eligible", 0)])
def test_rehashed_readiness_or_authority_promotion_is_rejected(bundle, key, new):
    obj = report(bundle); obj['state'][key] = new; replace_report(bundle, obj)
    with pytest.raises(C.CheckError, match="promotion"): verify(bundle)


@pytest.mark.parametrize("key,new", [("repository", "other/repository"), ("source_commit", "0"*40),
    ("run_id", "67890"), ("run_attempt", 2), ("run_attempt", True), ("event", "push"),
    ("actor", "other"), ("origin", "arbitrary_claim"), ("python", "3.13.5"), ("os", "ubuntu-latest"),
    ("architecture", "arm64"), ("workflow", ".github/workflows/other.yml"), ("runner_image", "")])
def test_cross_context_substitution_is_rejected(bundle, key, new):
    obj = report(bundle); obj['context'][key] = new; replace_report(bundle, obj)
    with pytest.raises(C.CheckError): verify(bundle)


def test_original_external_digest_cannot_be_replaced_by_rehash(bundle):
    original = A.digest((bundle[0]/'preparation.json').read_bytes())
    obj=report(bundle);obj['context']['run_id']='67890';replace_report(bundle,obj)
    with pytest.raises(C.CheckError, match="external_preparation_digest"): verify(bundle, original)


@pytest.mark.parametrize("kind", ["missing", "extra", "duplicate_index", "self_index", "path_traversal",
                                 "index_size_bool", "index_hash", "source_scope", "phase", "extra_field"])
def test_file_inventory_contract_rejects(bundle, kind):
    out=bundle[0];obj=report(bundle)
    if kind=='missing': (out/'model/vocab.json').unlink()
    elif kind=='extra': (out/'extra.json').write_bytes(b'{}')
    elif kind=='duplicate_index': obj['files'].append(copy.deepcopy(obj['files'][0]))
    elif kind=='self_index': obj['files'][0]['path']='preparation.json'
    elif kind=='path_traversal': obj['files'][0]['path']='../outside'
    elif kind=='index_size_bool': obj['files'][0]['size']=True
    elif kind=='index_hash': obj['files'][0]['sha256']='0'*64
    elif kind=='source_scope': obj['source_paths'].pop()
    elif kind=='phase': obj['record_type']='q2_reference_capture_v0'
    elif kind=='extra_field': obj['PASS']=True
    replace_report(bundle,obj)
    with pytest.raises((C.CheckError, FileNotFoundError)): verify(bundle)


@pytest.mark.parametrize("target", ['model/config.json','model/tokenizer.json'])
def test_symlink_and_hardlink_inputs_are_not_admitted(bundle,target,tmp_path):
    out=bundle[0];p=out/target;data=p.read_bytes();p.unlink();outside=tmp_path/'outside';outside.write_bytes(data)
    p.symlink_to(outside)
    with pytest.raises(C.CheckError,match='symlink'):verify(bundle)
    p.unlink();os.link(outside,p)
    with pytest.raises(C.CheckError,match='file_kind'):verify(bundle)


def test_producer_bytes_cannot_replace_independent_source_expectation(bundle):
    p=bundle[0]/'source'/A.SELF;p.write_bytes(p.read_bytes()+b'\n# replacement\n');reindex(bundle)
    with pytest.raises(C.CheckError,match='source_snapshot_mismatch'):verify(bundle)


def test_workload_lexical_reencoding_is_not_exact_file_identity(bundle):
    p=bundle[0]/'source'/A.REQUESTS;p.write_bytes(p.read_bytes().replace(b'1.0',b'1'));reindex(bundle)
    with pytest.raises(C.CheckError,match='source_snapshot_mismatch'):verify(bundle)


def rewrite_model_and_its_internal_hashes(bundle,name,new_value):
    out=bundle[0];path=out/'model'/name;path.write_bytes(A.encode(new_value))
    meta=A.strict_json((out/'upstream/model.json').read_bytes())
    for item in meta['siblings']:
        if item['rfilename']==name:
            data=path.read_bytes();item['size']=len(data)
            item['blobId']=hashlib.sha1(b'blob %d\0'%len(data)+data).hexdigest()
    (out/'upstream/model.json').write_bytes(A.encode(meta))
    rows=[A.bind_model_file(n,(out/'model'/n).read_bytes(),next(i for i in meta['siblings'] if i['rfilename']==n))
          for n in A.MODEL_FILES]
    model_map=A.strict_json((out/'q2_reference_model_files_v0.json').read_bytes());model_map['files']=rows
    (out/'q2_reference_model_files_v0.json').write_bytes(A.encode(model_map));reindex(bundle)


@pytest.mark.parametrize("name,key,value", [('config.json','bos_token_id',0),('generation_config.json','bos_token_id',0),
    ('config.json','eos_token_id',3),('generation_config.json','pad_token_id',None),
    ('tokenizer_config.json','bos_token','<|endoftext|>'),('tokenizer_config.json','chat_template',''),
    ('tokenizer.json','added_tokens',[{'id':1,'content':'wrong','special':True}])])
def test_rehashed_token_substitution_is_still_rejected(bundle,name,key,value):
    obj=A.strict_json((bundle[0]/'model'/name).read_bytes());obj[key]=value
    rewrite_model_and_its_internal_hashes(bundle,name,obj)
    with pytest.raises(C.CheckError):verify(bundle)


def test_upstream_revision_substitution_rehashed_is_rejected(bundle):
    p=bundle[0]/'upstream/model.json';obj=A.strict_json(p.read_bytes());obj['sha']='0'*40;p.write_bytes(A.encode(obj));reindex(bundle)
    with pytest.raises(C.CheckError,match='wrong_model_revision'):verify(bundle)


def test_model_map_cannot_claim_adoption(bundle):
    p=bundle[0]/'q2_reference_model_files_v0.json';obj=A.strict_json(p.read_bytes());obj['adopted']=True;p.write_bytes(A.encode(obj));reindex(bundle)
    with pytest.raises(C.CheckError,match='model_map_not_reconstructed'):verify(bundle)


def test_rehashed_lock_omission_is_rejected(bundle):
    p=bundle[0]/'requirements-q2-reference-v0.lock';p.write_bytes(b'\n'.join(p.read_bytes().splitlines()[:-1])+b'\n');reindex(bundle)
    with pytest.raises(C.CheckError,match='lock_not_exactly_reconstructed'):verify(bundle)


@pytest.mark.parametrize("mutation",['hash','name','version','metadata_path','url','duplicate'])
def test_rehashed_wheel_record_substitution(bundle,mutation):
    obj=report(bundle);row=obj['wheels'][1]
    if mutation=='hash':row['sha256']='0'*64
    elif mutation=='name':row['name']='substitute'
    elif mutation=='version':row['version']='9.9.9'
    elif mutation=='metadata_path':row['upstream_metadata']='upstream/model.json'
    elif mutation=='url':row['url']='https://example.invalid/wheel.whl'
    else:obj['wheels'].append(copy.deepcopy(row))
    replace_report(bundle,obj)
    with pytest.raises(C.CheckError):verify(bundle)


@pytest.mark.parametrize("case",['wrong_hash','yanked','sdist','origin','ambiguous','root_version'])
def test_rehashed_upstream_wheel_metadata_is_rejected(bundle,case):
    out=bundle[0];p=out/'upstream/pypi/transformers-4.57.6.json';obj=A.strict_json(p.read_bytes())
    if case=='wrong_hash':obj['urls'][0]['digests']['sha256']='0'*64
    elif case=='yanked':obj['urls'][0]['yanked']=True
    elif case=='sdist':obj['urls'][0]['packagetype']='sdist'
    elif case=='origin':obj['urls'][0]['url']='https://evil.invalid/wheel.whl'
    elif case=='ambiguous':obj['urls']*=2
    else:obj['info']['version']='4.58.0'
    p.write_bytes(A.encode(obj));reindex(bundle)
    with pytest.raises(C.CheckError):verify(bundle)


@pytest.mark.parametrize("options",[{'dependency':'x @ https://example.invalid/x.whl'}, {'duplicate_name':True},
                                    {'bad_member':'../escape'}, {'bad_member':'/absolute'}])
@pytest.mark.parametrize("inspector",[A.wheel_identity,C.wheel_metadata])
def test_malformed_wheel_metadata_is_rejected(tmp_path,options,inspector):
    p=tmp_path/'package-1.0-py3-none-any.whl';p.write_bytes(wheel_bytes('package','1.0',**options))
    with pytest.raises(ValueError):inspector(p)


@pytest.mark.parametrize("name",['nvidia-cublas-cu12','cuda-runtime','triton','torchvision','torchaudio'])
@pytest.mark.parametrize("inspector",[A.wheel_identity,C.wheel_metadata])
def test_no_unselected_gpu_or_extra_torch_distribution(tmp_path,name,inspector):
    p=tmp_path/(name.replace('-','_')+'-1.0-py3-none-any.whl');p.write_bytes(wheel_bytes(name,'1.0'))
    with pytest.raises(ValueError):inspector(p)


@pytest.mark.parametrize("url",['http://huggingface.co/x','https://huggingface.co.evil.invalid/x',
    'https://token@huggingface.co/x','https://huggingface.co:444/x','file:///etc/passwd','https://evil.invalid/a.hf.co'])
def test_redirect_allowlist_rejects_untrusted_origins(url):
    with pytest.raises(A.PreparationError):A.SafeRedirect.check(url)


@pytest.mark.parametrize("url",['https://huggingface.co/x','https://cas-bridge.xethub.hf.co/x',
    'https://download-r2.pytorch.org/x','https://pypi.org/x','https://files.pythonhosted.org/x'])
def test_selected_download_origins_are_supported(url):A.SafeRedirect.check(url)


def test_no_credential_or_proxy_environment_in_pip(tmp_path,monkeypatch):
    for name in ['HF_TOKEN','GITHUB_TOKEN','OPENAI_API_KEY','HTTPS_PROXY','PIP_INDEX_URL','PYTHONPATH']:
        monkeypatch.setenv(name,'NEVER_COPY_THIS')
    clean=A.clean_env(tmp_path)
    assert all('NEVER_COPY_THIS' not in x for x in clean.values())
    assert clean['PIP_CONFIG_FILE']==os.devnull


@pytest.fixture
def context(monkeypatch,tmp_path):
    sha='a'*40
    env={'GITHUB_REPOSITORY':A.REPOSITORY,'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main',
         'GITHUB_ACTOR':'HKati','GITHUB_TRIGGERING_ACTOR':'HKati','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':sha,
         'GITHUB_WORKFLOW_SHA':sha,'GITHUB_WORKFLOW_REF':f'{A.REPOSITORY}/{A.WORKFLOW}@refs/heads/main',
         'GITHUB_RUN_ID':'12345','ImageOS':'ubuntu24','ImageVersion':'synthetic-context-only'}
    monkeypatch.setattr(A,'git_bytes',lambda *x:(sha+'\n').encode())
    monkeypatch.setattr(A.platform,'python_implementation',lambda:'CPython')
    monkeypatch.setattr(A.platform,'python_version',lambda:'3.11.16')
    monkeypatch.setattr(A.platform,'system',lambda:'Linux')
    monkeypatch.setattr(A.platform,'machine',lambda:'x86_64')
    monkeypatch.setattr(A.platform,'freedesktop_os_release',lambda:{'ID':'ubuntu','VERSION_ID':'24.04'})
    return tmp_path,sha,env


def test_context_positive_is_only_a_synthetic_control_plane_test(context):
    repo,sha,env=context
    assert A.check_context(repo,sha,env)['source_commit']==sha


@pytest.mark.parametrize("key,value",[('GITHUB_REPOSITORY','fork/repo'),('GITHUB_EVENT_NAME','pull_request'),
    ('GITHUB_REF','refs/heads/other'),('GITHUB_ACTOR','other'),('GITHUB_TRIGGERING_ACTOR','other'),
    ('GITHUB_RUN_ATTEMPT','2'),('GITHUB_SHA','b'*40),('GITHUB_WORKFLOW_SHA','b'*40),
    ('GITHUB_WORKFLOW_REF','wrong'),('GITHUB_RUN_ID','0'),('ImageOS','ubuntu22'),('ImageVersion','')])
def test_dispatch_context_fails_before_network(context,key,value):
    repo,sha,env=context;env[key]=value
    with pytest.raises(A.PreparationError):A.check_context(repo,sha,env)


def test_preparer_cannot_start_on_wrong_python(context,monkeypatch):
    repo,sha,env=context;monkeypatch.setattr(A.platform,'python_version',lambda:'3.13.5')
    with pytest.raises(A.PreparationError,match='native_python'):A.check_context(repo,sha,env)


def test_resolution_uses_only_staged_hash_locked_wheels(bundle,monkeypatch):
    _,wheels=verify(bundle)
    monkeypatch.setattr(C.platform,'python_implementation',lambda:'CPython')
    monkeypatch.setattr(C.platform,'python_version',lambda:'3.11.16')
    monkeypatch.setattr(C.platform,'system',lambda:'Linux')
    monkeypatch.setattr(C.platform,'machine',lambda:'x86_64')
    monkeypatch.setattr(C.platform,'freedesktop_os_release',lambda:{'ID':'ubuntu','VERSION_ID':'24.04'})
    calls=[]
    def fake_run(argv,**kwargs):
        calls.append(argv)
        assert '--dry-run' in argv and '--ignore-installed' in argv and '--no-index' in argv
        assert '--require-hashes' in argv and '--only-binary=:all:' in argv and '--no-deps' not in argv
        assert 'NEVER_COPY_THIS' not in repr(kwargs['env'])
        path=Path(argv[argv.index('--report')+1])
        path.write_bytes(A.encode({'version':'1','pip_version':'25.1.1','install':[
            {'metadata':{'name':n,'version':v},'download_info':{'url':(bundle[0]/p).resolve().as_uri()}}
            for n,v,_,p in wheels]}))
        return subprocess.CompletedProcess(argv,0)
    monkeypatch.setattr(C.subprocess,'run',fake_run)
    assert C.resolve_offline(bundle[0],wheels)=='25.1.1' and len(calls)==1


def test_checker_is_separate_and_no_model_code_imported():
    for path in [TOOLS/'acquire_q2_reference_inputs_v0.py',TOOLS/'check_q2_reference_capture_v0.py']:
        tree=ast.parse(path.read_text())
        imports=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):imports += [a.name for a in n.names]
            elif isinstance(n,ast.ImportFrom):imports += [n.module or '']
        assert not any(n.split('.')[0] in {'torch','transformers','huggingface_hub'} for n in imports)
        if path.name.startswith('check_'):
            assert not any('acquire_q2' in n for n in imports)
            assert 'importlib' not in imports and 'runpy' not in imports


@pytest.mark.parametrize("script",['acquire_q2_reference_inputs_v0.py','check_q2_reference_capture_v0.py'])
def test_capture_command_has_no_implementation_or_cli_bypass(script):
    proc=subprocess.run([sys.executable,'-I',str(TOOLS/script),'capture'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
    assert proc.returncode==2 and b'invalid choice' in proc.stderr


def test_workflow_is_manual_preparation_only_and_preserves_exact_sources():
    payload=(ROOT/A.WORKFLOW).read_text();wf=yaml.safe_load(payload)
    triggers=wf.get('on',wf.get(True))
    assert set(triggers)=={'workflow_dispatch'}
    assert wf['permissions']=={'contents':'read'}
    job=wf['jobs']['prepare'];assert job['runs-on']=='ubuntu-24.04' and job['timeout-minutes']==40
    steps=job['steps'];runs='\n'.join(x.get('run','') for x in steps)
    assert 'prepare-runtime' in runs and 'verify-prepared-runtime' in runs
    assert 'run_q2_reference_subject_v0.py' not in runs and 'build_q2_reference_summary.py' not in runs
    assert 'GITHUB_RUN_ATTEMPT' in steps[0]['run'] and 'GITHUB_WORKFLOW_SHA' in steps[0]['run']
    assert 'EXPECTED_SOURCE_SHA' in steps[0]['run']
    uploads=[x for x in steps if x.get('uses','').startswith('actions/upload-artifact@')]
    assert len(uploads)==1 and uploads[0]['with']['include-hidden-files'] is True
    assert uploads[0]['with']['if-no-files-found']=='error' and uploads[0]['with']['overwrite'] is False
    assert 'always()' not in payload and 'secrets.' not in payload and 'contents: write' not in payload
    entries=[l.split('#',1)[0].strip() for l in (ROOT/'ci/tools-tests.list').read_text().splitlines()]
    entries=[x for x in entries if x]
    assert len(entries)==len(set(entries))==157
    assert entries.count('tests/test_q2_reference_acquisition_v0.py')==1


def staged_transport_fixture(bundle, monkeypatch, *, fail_on=None):
    source_output, repo, source_sha = bundle
    old_report = report(bundle)
    sources = {rel: (repo / rel).read_bytes() for rel in A.SOURCE_PATHS}
    paths = {A.HF_API: 'upstream/model.json', A.TORCH_INDEX: 'upstream/torch-cpu-index.html'}
    for name in A.MODEL_FILES:
        paths[f'https://huggingface.co/{A.MODEL}/resolve/{A.REVISION}/{name}'] = 'model/' + name
    for row in old_report['wheels']:
        if row['name'] == 'torch': paths[row['url']] = row['path']
        else: paths[f"https://pypi.org/pypi/{row['name']}/{row['version']}/json"] = row['upstream_metadata']
    class FakeTransport:
        def __init__(self, deadline): pass
        def get(self, url, path, limit):
            assert url in paths, 'Unexpected download in offline fixture'
            if paths[url] == fail_on: raise A.PreparationError('synthetic_download_failure')
            data = (source_output / paths[url]).read_bytes()
            assert len(data) <= limit
            A.write_new(path, data)
            return data
    def fake_pip(wheelhouse, private, deadline):
        for row in old_report['wheels']:
            if row['name'] != 'torch': A.write_new(wheelhouse / Path(row['path']).name,
                                                  (source_output / row['path']).read_bytes())
    monkeypatch.setattr(A, 'Transport', FakeTransport)
    monkeypatch.setattr(A, 'pip_download', fake_pip)
    monkeypatch.setattr(A, 'check_context', lambda *args: old_report['context'])
    monkeypatch.setattr(A, 'fixed_sources', lambda *args: sources)
    return repo, source_sha


def test_preparation_to_separate_check_roundtrip_is_explicitly_synthetic(bundle, monkeypatch, tmp_path):
    repo, source_sha = staged_transport_fixture(bundle, monkeypatch)
    output = tmp_path / 'roundtrip'
    A.prepare(repo, output, source_sha)
    result, wheels = C.inspect_bundle(output, A.digest((output / 'preparation.json').read_bytes()),
                                      source_sha, '12345', repo)
    assert result['context']['origin'] == 'synthetic_protocol_fixture'
    assert result['state']['inference_executed'] is False
    assert result['state']['native_runtime_qualified'] is False
    assert len(wheels) == 4


@pytest.mark.parametrize('failure', ['upstream/model.json', 'model/model.safetensors',
                                   'upstream/torch-cpu-index.html', 'upstream/pypi/transformers-4.57.6.json'])
def test_preparation_failure_never_publishes_a_complete_manifest(bundle, monkeypatch, tmp_path, failure):
    repo, source_sha = staged_transport_fixture(bundle, monkeypatch, fail_on=failure)
    output = tmp_path / 'failure'
    with pytest.raises(A.PreparationError, match='synthetic_download_failure'):
        A.prepare(repo, output, source_sha)
    assert not (output / 'preparation.json').exists()
    assert not (output / 'check.json').exists()


def test_prepare_refuses_existing_output_before_downloading(bundle, monkeypatch):
    repo, source_sha = staged_transport_fixture(bundle, monkeypatch)
    with pytest.raises(A.PreparationError, match='output_already_exists'):
        A.prepare(repo, bundle[0], source_sha)


def test_preparation_has_no_repository_write_or_auto_adoption():
    text = (ROOT / A.WORKFLOW).read_text()
    assert 'git push' not in text and 'gh pr' not in text and 'actions: write' not in text
    assert 'id-token: write' not in text and 'packages: write' not in text
    assert 'requirements-q2-reference-v0.lock' not in (ROOT / 'ci/tools-tests.list').read_text()
    # The pins now enter through an explicit source-reviewed adoption, not
    # through a preparation workflow write. The original candidates and the
    # historical source closure stay bound by the recorded-input oracle.
    _, checked, adopted = _check_recorded_input_pins(ROOT)
    assert adopted['adoption']['scope'] == 'runtime_input_pins_only'
    assert adopted['native_runtime_qualified'] is False
    assert checked['capture_dispatch_authorized'] is False


def _hygiene_python_sync_script():
    workflow = yaml.safe_load((ROOT / '.github/workflows/repo_hygiene.yml').read_text())
    steps = workflow['jobs']['hygiene_guardrails']['steps']
    matches = [step['run'] for step in steps if step.get('name') ==
               'Repo hygiene: enforce Python version sync (environment.yml vs workflows)']
    assert len(matches) == 1
    prefix, script = matches[0].split("python3 - <<'PY'\n", 1)
    assert prefix.strip() == 'set -euo pipefail' and script.endswith('PY\n')
    return script[:-3]


def _run_hygiene_python_sync(tmp_path, *, core_version='3.11', q2_text=None,
                             environment='dependencies: [python=3.11, pip]\n',
                             extra_workflows=None):
    """Execute the actual workflow guard, not a test-side copy of its policy."""
    (tmp_path / 'environment.yml').write_text(environment)
    workflows = tmp_path / '.github/workflows'
    workflows.mkdir(parents=True, exist_ok=True)
    core = {'name': 'synthetic core workflow', 'jobs': {'check': {'steps': [
        {'uses': 'actions/setup-python@synthetic', 'with': {'python-version': core_version}}
    ]}}}
    (workflows / 'core.yml').write_text(yaml.safe_dump(core))
    if q2_text is not None:
        (workflows / 'q2_reference_acquisition_v0.yml').write_text(q2_text)
    for name, content in (extra_workflows or {}).items():
        (workflows / name).write_text(content)
    return subprocess.run([sys.executable, '-I', '-c', _hygiene_python_sync_script()],
                          cwd=tmp_path, capture_output=True, text=True, timeout=10)


def _q2_workflow_text():
    return (ROOT / A.WORKFLOW).read_text()


def test_hygiene_accepts_core_line_and_exact_selected_q2_patch(tmp_path):
    result = _run_hygiene_python_sync(tmp_path, q2_text=_q2_workflow_text())
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'exact patch pins verified' in result.stdout


def test_hygiene_rejects_missing_pinned_workflow(tmp_path):
    result = _run_hygiene_python_sync(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert A.WORKFLOW in result.stdout
    assert 'Pinned workflow must exist as a regular file at its exact path.' in result.stdout
    assert 'exact patch pins verified' not in result.stdout


@pytest.mark.parametrize('renamed', [
    'other.yml', 'Q2_reference_acquisition_v0.yml',
    'q2_reference_acquisition_v0.yaml', 'q2_reference_acquisition_v0.yml.disabled',
])
def test_hygiene_rejects_renamed_pinned_workflow_even_with_core_version(tmp_path, renamed):
    # The alias otherwise satisfies the generic 3.11 rule; failure must be
    # caused by the missing exact path, not by an unrelated version mismatch.
    text = _q2_workflow_text().replace("python-version: '3.11.16'", "python-version: '3.11'")
    result = _run_hygiene_python_sync(tmp_path, extra_workflows={renamed: text})
    assert result.returncode == 1, result.stdout + result.stderr
    assert A.WORKFLOW in result.stdout
    assert 'Pinned workflow must exist as a regular file at its exact path.' in result.stdout
    assert 'exact patch pins verified' not in result.stdout
    assert 'Python version drift detected' not in result.stdout


@pytest.mark.parametrize('kind', ['directory', 'symlink', 'dangling_symlink'])
def test_hygiene_rejects_non_regular_pinned_workflow(tmp_path, kind):
    pinned = tmp_path / A.WORKFLOW
    pinned.parent.mkdir(parents=True)
    if kind == 'directory':
        pinned.mkdir()
    else:
        target = tmp_path / 'synthetic-workflow.txt'
        if kind == 'symlink':
            target.write_text(_q2_workflow_text(), encoding='utf-8')
        pinned.symlink_to(target)
    result = _run_hygiene_python_sync(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert A.WORKFLOW in result.stdout
    assert 'Pinned workflow must exist as a regular file at its exact path.' in result.stdout
    assert 'exact patch pins verified' not in result.stdout
    assert 'Traceback' not in result.stderr


def test_readiness_preparation_inventory_includes_hygiene_workflow():
    text = (ROOT / 'docs/compute/PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md').read_text(encoding='utf-8')
    section = text.split('### 7.1 Executable subset and unresolved byte inputs\n', 1)[1]
    section = section.split('### 7.2 What the preparation actually does', 1)[0]
    assert '#2894 contains thirteen repository paths:' in section
    assert '[the repository-hygiene workflow](../../.github/workflows/repo_hygiene.yml)' in section
    assert 'contains twelve repository paths' not in section


@pytest.mark.parametrize('version', [
    '3.11', '3.11.15', '3.11.17', '3.12.0', '3.110.16',
    '3.11.16-rc1', '3.11.*', '${{ matrix.python }}',
])
def test_hygiene_rejects_q2_patch_drift_and_broader_selector(tmp_path, version):
    original = "python-version: '3.11.16'"
    text = _q2_workflow_text()
    assert text.count(original) == 1
    text = text.replace(original, f'python-version: {json.dumps(version)}')
    result = _run_hygiene_python_sync(tmp_path, q2_text=text)
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'q2_reference_acquisition_v0.yml' in result.stdout
    assert '(expected 3.11.16)' in result.stdout


@pytest.mark.parametrize('version', ['3.10', '3.12', '3.11.16', '3.11.17', '3.110', '3.11.*'])
def test_hygiene_does_not_allow_patch_pins_in_other_workflows(tmp_path, version):
    result = _run_hygiene_python_sync(tmp_path, core_version=version,
                                     q2_text=_q2_workflow_text())
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'core.yml' in result.stdout and '(expected 3.11)' in result.stdout


@pytest.mark.parametrize('replacement', [
    '', "          python-version-file: '.python-version'\n",
    "          python-version: '3.11.16'\n          python-version: '3.11.16'\n",
    "          python-version: '3.11.16'\n          python-version: '3.11'\n",
])
def test_hygiene_rejects_missing_or_multiple_q2_declarations(tmp_path, replacement):
    original = "          python-version: '3.11.16'\n"
    text = _q2_workflow_text()
    assert text.count(original) == 1
    result = _run_hygiene_python_sync(tmp_path, q2_text=text.replace(original, replacement))
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'exactly one declaration of 3.11.16' in result.stdout


@pytest.mark.parametrize('version', ['3.12', '3.11.16', '3.110'])
def test_hygiene_requires_q2_patch_to_refine_the_core_line(tmp_path, version):
    environment = f'dependencies: [python={version}, pip]\n'
    result = _run_hygiene_python_sync(tmp_path, core_version=version,
                                     environment=environment, q2_text=_q2_workflow_text())
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'a patch pin on environment.yml line' in result.stdout


@pytest.mark.parametrize('name', [
    'other.yml', 'Q2_reference_acquisition_v0.yml', 'q2_reference_acquisition_v0.yaml',
])
def test_hygiene_q2_patch_permission_is_exact_path_only(tmp_path, name):
    result = _run_hygiene_python_sync(tmp_path, q2_text=_q2_workflow_text(),
                                     extra_workflows={name: _q2_workflow_text()})
    assert result.returncode == 1, result.stdout + result.stderr
    assert name in result.stdout and '(expected 3.11)' in result.stdout


def test_hygiene_still_rejects_missing_environment_python(tmp_path):
    result = _run_hygiene_python_sync(tmp_path, environment='dependencies: [pip]\n',
                                     q2_text=_q2_workflow_text())
    assert result.returncode == 1
    assert 'No python=<version> dependency found in environment.yml' in result.stdout


def test_q2_setup_keeps_exact_selection_before_preparation():
    workflow = yaml.safe_load(_q2_workflow_text())
    steps = workflow['jobs']['prepare']['steps']
    setups = [(i, step) for i, step in enumerate(steps)
              if step.get('uses', '').startswith('actions/setup-python@')]
    assert len(setups) == 1
    index, setup = setups[0]
    selection = json.loads((ROOT / A.SELECTION).read_bytes())
    assert setup['with']['python-version'] == '3.11.16'
    assert setup['with']['python-version'] == selection['execution_protocol']['runtime_target']['python_target']
    assert setup['with']['python-version'] == selection['release_subject']['definition']['runtime_target']['python_target']
    preparation = [i for i, step in enumerate(steps) if 'prepare-runtime' in step.get('run', '')]
    assert len(preparation) == 1 and index < preparation[0]



# Recorded metadata from the first actual preparation; not an inference fixture.
# These anchors are fixed review expectations, not values accepted from a carrier.
_INPUT_PIN_EVIDENCE = "PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546"
_INPUT_PIN_LOCK = "PULSE_safe_pack_v0/requirements-q2-reference-v0.lock"
_INPUT_PIN_MAP = "PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json"
_INPUT_PIN_SOURCE = "77fc5d51896568db50a2a87f650711a65db8fe8c"
_INPUT_PIN_RUN = "37148637546"
_INPUT_PIN_ARCHIVE_SHA = "b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9"
_INPUT_PIN_RECORDS = {
    "preparation.json": "832b3626e846c96e5d65052ea54c966aabf0ed5f3976ecc5d3b4a3ced006ef4f",
    "q2-runtime-preparation-check.json": "8676b29834f376b44f08f96b19d60d1ab79a9f565167aabd25513cf8694037e3",
    "q2_reference_model_files_v0.json": "b91289806a62957e2613f21afa950d4bf48b917074fde16d3e94681764d74078",
    "requirements-q2-reference-v0.lock": "60cec54ed62df95b299cdeaf386afc7ed0b72f4fb7ec466cf82905bb40168d0f",
}
_INPUT_PIN_HEADER = (
    "# Q2 reference runtime input pins; native qualification and capture remain pending.\n"
)


def _pin_json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2,
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _check_recorded_input_pins(root: Path):
    """Test-only oracle for this one reviewed adoption, not a runtime verifier."""
    evidence_dir = root / _INPUT_PIN_EVIDENCE
    assert {p.name for p in evidence_dir.iterdir()} == set(_INPUT_PIN_RECORDS)
    raw = {}
    for name, expected_hash in _INPUT_PIN_RECORDS.items():
        path = evidence_dir / name
        assert path.is_file() and not path.is_symlink()
        raw[name] = path.read_bytes()
        assert hashlib.sha256(raw[name]).hexdigest() == expected_hash, name
    preparation = json.loads(raw["preparation.json"])
    checked = json.loads(raw["q2-runtime-preparation-check.json"])
    candidate = json.loads(raw["q2_reference_model_files_v0.json"])
    context = preparation["context"]
    assert context["repository"] == "HKati/pulse-release-gates-0.1"
    assert context["source_commit"] == _INPUT_PIN_SOURCE
    assert context["run_id"] == _INPUT_PIN_RUN and context["run_attempt"] == 1
    assert checked["preparation_sha256"] == _INPUT_PIN_RECORDS["preparation.json"]
    assert checked["source_commit"] == _INPUT_PIN_SOURCE and checked["run_id"] == _INPUT_PIN_RUN
    assert checked["candidate_bytes_verified"] is True
    assert checked["offline_dependency_resolution_checked"] is True
    assert checked["installation_performed"] is False
    for key in ("native_runtime_qualified", "inference_executed",
                "materialized_subject_bound", "capture_dispatch_authorized",
                "production_gate_eligible"):
        assert checked[key] is False and preparation["state"][key] is False
    assert preparation["state"]["dependency_closure_status"] == "staged_review_candidate"
    assert checked["dependency_closure_status"] == "staged_review_candidate"
    assert checked["authority_effect"] == preparation["state"]["authority_effect"] == "none"

    rows = preparation["files"]
    entries = {row["path"]: row for row in rows}
    assert len(entries) == len(rows) == 76
    for name in ("requirements-q2-reference-v0.lock", "q2_reference_model_files_v0.json"):
        assert entries[name]["sha256"] == hashlib.sha256(raw[name]).hexdigest()
        assert entries[name]["size"] == len(raw[name])
    assert len(candidate["files"]) == 8 and candidate["adopted"] is False
    assert candidate["native_runtime_qualified"] is False
    for row in candidate["files"]:
        assert {key: row[key] for key in ("path", "sha256", "size")} == entries[row["path"]]
    assert len(preparation["wheels"]) == 30
    wheel_names = [row["name"] for row in preparation["wheels"]]
    assert len(set(wheel_names)) == 30
    versions = {row["name"]: row["version"] for row in preparation["wheels"]}
    assert preparation["roots"] == {
        "torch": "2.8.0+cpu", "transformers": "4.57.6",
        "rfc8785": "0.1.4", "jsonschema": "4.25.1",
    }
    assert all(versions[name] == version for name, version in preparation["roots"].items())
    expected_entries = "".join(
        f'{row["name"]}=={row["version"]} --hash=sha256:{row["sha256"]}\n'
        for row in sorted(preparation["wheels"], key=lambda row: row["name"])
    ).encode("utf-8")
    assert b"".join(raw["requirements-q2-reference-v0.lock"].splitlines(keepends=True)[1:]) == expected_entries
    lock = (root / _INPUT_PIN_LOCK).read_bytes()
    assert lock == _INPUT_PIN_HEADER.encode("utf-8") + expected_entries

    # Bind the still-selected inputs, not the current tools/workflow to the
    # historical preparation commit. Those executable sources must be allowed
    # to evolve for the later worker/capture, with their own source binding.
    selected_inputs = (
        "PULSE_safe_pack_v0/profiles/q2_reference_subject_v0.json",
        "PULSE_safe_pack_v0/examples/q2_reference_field_extraction_v0/requests.json",
    )
    for rel in selected_inputs:
        source = (root / rel).read_bytes()
        assert hashlib.sha256(source).hexdigest() == entries["source/" + rel]["sha256"]
        assert len(source) == entries["source/" + rel]["size"]

    expected = copy.deepcopy(candidate)
    expected["record_type"] = "q2_reference_model_files_v0"
    expected["adopted"] = True
    expected["adoption"] = {
        "scope": "runtime_input_pins_only",
        "repository": "HKati/pulse-release-gates-0.1",
        "preparation_source_commit": _INPUT_PIN_SOURCE,
        "preparation_run_id": _INPUT_PIN_RUN,
        "preparation_run_attempt": 1,
        "preparation_workflow": ".github/workflows/q2_reference_acquisition_v0.yml",
        "target": {"os": "ubuntu-24.04", "architecture": "x86_64", "python": "3.11.16"},
        "artifact": {
            "id": 11282419957, "name": "q2-runtime-preparation-37148637546-1",
            "sha256": _INPUT_PIN_ARCHIVE_SHA, "size": 508460811,
        },
        "source_records": {
            name: {"path": _INPUT_PIN_EVIDENCE + "/" + name,
                   "sha256": digest, "size": len(raw[name])}
            for name, digest in _INPUT_PIN_RECORDS.items()
        },
        "repository_lock": {
            "path": _INPUT_PIN_LOCK, "sha256": hashlib.sha256(lock).hexdigest(), "size": len(lock),
        },
    }
    map_path = root / _INPUT_PIN_MAP
    assert map_path.is_file() and not map_path.is_symlink()
    assert map_path.read_bytes() == _pin_json_bytes(expected)
    return preparation, checked, expected


def _copy_input_pin_fixture(tmp_path: Path):
    preparation = json.loads((ROOT / _INPUT_PIN_EVIDENCE / "preparation.json").read_bytes())
    paths = [_INPUT_PIN_MAP, _INPUT_PIN_LOCK]
    paths += [_INPUT_PIN_EVIDENCE + "/" + name for name in _INPUT_PIN_RECORDS]
    paths += preparation["source_paths"]
    for rel in paths:
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / rel).read_bytes())
    return tmp_path


def test_recorded_runtime_input_pins_match_original_run():
    preparation, checked, adopted = _check_recorded_input_pins(ROOT)
    assert len(preparation["wheels"]) == 30 and len(adopted["files"]) == 8
    assert adopted["adopted"] is True and adopted["native_runtime_qualified"] is False
    assert checked["installation_performed"] is False


@pytest.mark.parametrize("name", list(_INPUT_PIN_RECORDS))
def test_input_pins_reject_changed_original_record(tmp_path, name):
    root = _copy_input_pin_fixture(tmp_path)
    path = root / _INPUT_PIN_EVIDENCE / name
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(AssertionError):
        _check_recorded_input_pins(root)


@pytest.mark.parametrize("name", list(_INPUT_PIN_RECORDS))
def test_input_pins_reject_rehashed_original_record(tmp_path, name):
    root = _copy_input_pin_fixture(tmp_path)
    path = root / _INPUT_PIN_EVIDENCE / name
    raw = path.read_bytes() + b"\n"
    path.write_bytes(raw)
    map_path = root / _INPUT_PIN_MAP
    adopted = json.loads(map_path.read_bytes())
    adopted["adoption"]["source_records"][name].update(
        sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
    map_path.write_bytes(_pin_json_bytes(adopted))
    with pytest.raises(AssertionError):
        _check_recorded_input_pins(root)


@pytest.mark.parametrize("rel", [_INPUT_PIN_MAP, _INPUT_PIN_LOCK] + [
    _INPUT_PIN_EVIDENCE + "/" + name for name in _INPUT_PIN_RECORDS
])
def test_input_pins_reject_missing_adoption_file(tmp_path, rel):
    root = _copy_input_pin_fixture(tmp_path)
    (root / rel).unlink()
    with pytest.raises((AssertionError, FileNotFoundError)):
        _check_recorded_input_pins(root)


@pytest.mark.parametrize("mutation", [
    "remove_entry", "extra_entry", "duplicate_entry", "changed_version",
    "changed_hash", "unhashed_entry", "direct_url", "index_option", "crlf",
])
def test_input_pins_reject_lock_substitution(tmp_path, mutation):
    root = _copy_input_pin_fixture(tmp_path)
    path = root / _INPUT_PIN_LOCK
    raw = path.read_bytes()
    entries = raw.splitlines(keepends=True)
    if mutation == "remove_entry": raw = b"".join(entries[:-1])
    elif mutation == "extra_entry": raw += b"extra==1.0 --hash=sha256:" + b"0" * 64 + b"\n"
    elif mutation == "duplicate_entry": raw += entries[1]
    elif mutation == "changed_version": raw = raw.replace(b"torch==2.8.0+cpu", b"torch==2.8.1+cpu")
    elif mutation == "changed_hash": raw = raw.replace(b"sha256:", b"sha256:0", 1)
    elif mutation == "unhashed_entry": raw = raw.replace(entries[1], entries[1].split(b" --hash")[0] + b"\n")
    elif mutation == "direct_url": raw += b"extra @ https://example.invalid/extra.whl\n"
    elif mutation == "index_option": raw += b"--extra-index-url https://example.invalid/\n"
    elif mutation == "crlf": raw = raw.replace(b"\n", b"\r\n")
    path.write_bytes(raw)
    adopted_path = root / _INPUT_PIN_MAP
    adopted = json.loads(adopted_path.read_bytes())
    adopted["adoption"]["repository_lock"].update(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
    adopted_path.write_bytes(_pin_json_bytes(adopted))
    with pytest.raises(AssertionError):
        _check_recorded_input_pins(root)


@pytest.mark.parametrize("index", range(8))
@pytest.mark.parametrize("field", ["path", "sha256", "size"])
def test_input_pins_reject_model_file_substitution(tmp_path, index, field):
    root = _copy_input_pin_fixture(tmp_path)
    path = root / _INPUT_PIN_MAP
    adopted = json.loads(path.read_bytes())
    if field == "path": adopted["files"][index][field] = "model/substitute.json"
    elif field == "sha256": adopted["files"][index][field] = "0" * 64
    else: adopted["files"][index][field] += 1
    path.write_bytes(_pin_json_bytes(adopted))
    with pytest.raises(AssertionError):
        _check_recorded_input_pins(root)


@pytest.mark.parametrize("mutation", [
    "not_adopted", "qualified", "authority", "wrong_model", "wrong_revision",
    "missing_model", "extra_model", "duplicate_model", "reordered_model",
    "scope", "source", "run", "attempt", "workflow", "target",
    "artifact_id", "artifact_digest", "artifact_name", "artifact_size", "extra_key",
])
def test_input_pins_reject_rebinding_or_authority_promotion(tmp_path, mutation):
    root = _copy_input_pin_fixture(tmp_path)
    path = root / _INPUT_PIN_MAP
    adopted = json.loads(path.read_bytes())
    binding = adopted["adoption"]
    if mutation == "not_adopted": adopted["adopted"] = False
    elif mutation == "qualified": adopted["native_runtime_qualified"] = True
    elif mutation == "authority": adopted["authority_effect"] = "allow"
    elif mutation == "wrong_model": adopted["model_repository"] += "-other"
    elif mutation == "wrong_revision": adopted["model_revision"] = "0" * 40
    elif mutation == "missing_model": adopted["files"].pop()
    elif mutation == "extra_model": adopted["files"].append({"path": "model/extra.json"})
    elif mutation == "duplicate_model": adopted["files"][-1] = copy.deepcopy(adopted["files"][0])
    elif mutation == "reordered_model": adopted["files"].reverse()
    elif mutation == "scope": binding["scope"] = "capture_authorized"
    elif mutation == "source": binding["preparation_source_commit"] = "0" * 40
    elif mutation == "run": binding["preparation_run_id"] = "37148637547"
    elif mutation == "attempt": binding["preparation_run_attempt"] = 2
    elif mutation == "workflow": binding["preparation_workflow"] = ".github/workflows/other.yml"
    elif mutation == "target": binding["target"]["python"] = "3.13.5"
    elif mutation == "artifact_id": binding["artifact"]["id"] += 1
    elif mutation == "artifact_digest": binding["artifact"]["sha256"] = "0" * 64
    elif mutation == "artifact_name": binding["artifact"]["name"] += "-other"
    elif mutation == "artifact_size": binding["artifact"]["size"] += 1
    elif mutation == "extra_key": adopted["production_gate_eligible"] = True
    path.write_bytes(_pin_json_bytes(adopted))
    with pytest.raises(AssertionError):
        _check_recorded_input_pins(root)


def test_input_pins_preserve_non_authorizing_original_evidence():
    _, checked, adopted = _check_recorded_input_pins(ROOT)
    assert checked["capture_dispatch_authorized"] is False
    assert checked["production_gate_eligible"] is False
    assert adopted["authority_effect"] == "none"
    assert adopted["adoption"]["scope"] == "runtime_input_pins_only"


def test_readiness_records_adoption_without_claiming_native_execution():
    text = (ROOT / "docs/compute/PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md").read_text(encoding="utf-8")
    section = text.split("## 8. Recorded runtime-input adoption — no native qualification\n", 1)[1]
    assert "37148637546" in section and "11282419957" in section
    assert _INPUT_PIN_ARCHIVE_SHA in section
    assert "30 exact wheel entries" in section and "eight model/tokenizer files" in section
    assert "does not install or execute" in section
    assert "Original candidate records remain byte-for-byte unchanged" in section



@pytest.mark.parametrize("rel", [
    ".github/workflows/q2_reference_acquisition_v0.yml",
    "PULSE_safe_pack_v0/tools/acquire_q2_reference_inputs_v0.py",
    "PULSE_safe_pack_v0/tools/check_q2_reference_capture_v0.py",
])
def test_input_pins_do_not_rebind_original_preparation_to_future_consumer(tmp_path, rel):
    root = _copy_input_pin_fixture(tmp_path)
    source = root / rel
    source.write_bytes(source.read_bytes() + b"\n# Test-only future consumer revision.\n")
    preparation, _, adopted = _check_recorded_input_pins(root)
    assert preparation["context"]["source_commit"] == _INPUT_PIN_SOURCE
    assert adopted["adoption"]["preparation_source_commit"] == _INPUT_PIN_SOURCE


@pytest.mark.parametrize("rel", [
    "PULSE_safe_pack_v0/profiles/q2_reference_subject_v0.json",
    "PULSE_safe_pack_v0/examples/q2_reference_field_extraction_v0/requests.json",
])
def test_input_pins_reject_changed_selected_inputs(tmp_path, rel):
    root = _copy_input_pin_fixture(tmp_path)
    source = root / rel
    source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(AssertionError):
        _check_recorded_input_pins(root)


if __name__ == '__main__':
    raise SystemExit(pytest.main(['-q','-c',os.devnull,str(Path(__file__).resolve())]))
