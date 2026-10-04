#!/usr/bin/env python3
"""Offline Q2 preparation, adopted-input and native-diagnostic regressions.

Real Q2 metadata is inspected without model/wheel payload downloads. Native
protocol tests use explicitly synthetic archives, wheels, tensors and framework
doubles. Two installer-body tests actually install one tiny synthetic wheel into
fresh offline virtual environments; neither installs the Q2 runtime closure.
No actual model import/generation, systemd service, workflow dispatch or native
qualification is performed. Synthetic expectations are confined to tests; no
production CLI accepts synthetic provenance, alternative models or bypasses.
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


def test_workflow_preserves_manual_preparation_branch_and_exact_sources():
    payload=(ROOT/A.WORKFLOW).read_text();wf=yaml.safe_load(payload)
    triggers=wf.get('on',wf.get(True))
    assert set(triggers)=={'workflow_dispatch'}
    assert wf['permissions']=={'contents':'read'}
    job=wf['jobs']['prepare'];assert job['runs-on']=='ubuntu-24.04' and job['timeout-minutes']==40
    steps=job['steps'];runs='\n'.join(x.get('run','') for x in steps if x.get('if')=="inputs.mode == 'prepare-runtime'")
    assert 'prepare-runtime' in runs and 'verify-prepared-runtime' in runs
    assert 'run_q2_reference_subject_v0.py' not in runs and 'build_q2_reference_summary.py' not in runs
    assert 'GITHUB_RUN_ATTEMPT' in steps[0]['run'] and 'GITHUB_WORKFLOW_SHA' in steps[0]['run']
    assert 'EXPECTED_SOURCE_SHA' in steps[0]['run']
    uploads=[x for x in steps if x.get('uses','').startswith('actions/upload-artifact@') and x.get('if')=="inputs.mode == 'prepare-runtime'"]
    assert len(uploads)==1 and uploads[0]['with']['include-hidden-files'] is True
    assert uploads[0]['with']['if-no-files-found']=='error' and uploads[0]['with']['overwrite'] is False
    assert 'always()' not in uploads[0]['if'] and 'secrets.' not in payload and 'contents: write' not in payload
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
    preparation = [i for i, step in enumerate(steps) if 'acquire_q2_reference_inputs_v0.py' in step.get('run', '')]
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




# Native qualification protocol tests. All model/tokenizer objects below are
# explicit synthetic doubles. No real model, download or systemd job is started.
N = load_module('q2_native_supervisor_under_test', TOOLS / 'qualify_q2_reference_runtime_v0.py')
K = load_module('q2_native_checker_under_test', TOOLS / 'check_q2_reference_qualification_v0.py')
W = load_module('q2_native_worker_under_test', TOOLS / 'run_q2_reference_subject_v0.py')


def test_native_source_closure_and_fixed_diagnostic_agree():
    assert N.SOURCES == K.SOURCE_PATHS
    assert K.parse((ROOT / K.DIAGNOSTIC).read_bytes()) == K.DIAGNOSTIC_VALUE
    assert W.MESSAGES == K.DIAGNOSTIC_VALUE['messages']
    assert W.GENERATION == K.GENERATION
    assert N.PREPARATION_SOURCE == K.ORIGINAL_SOURCE == _INPUT_PIN_SOURCE
    assert N.ARCHIVE_SHA == K.ARCHIVE_SHA == _INPUT_PIN_ARCHIVE_SHA
    assert N.ARCHIVE_SIZE == K.ARCHIVE_SIZE == 508460811
    assert A.SOURCE_PATHS == (A.WORKFLOW, A.SELF, A.CHECKER, A.SELECTION, A.REQUESTS)
    assert hashlib.sha256((TOOLS / 'acquire_q2_reference_inputs_v0.py').read_bytes()).hexdigest() == 'd82e103b601bc118a21001f315c70b8cbe9d8d94b05a6c40406ef9b328cf4609'
    assert hashlib.sha256((TOOLS / 'check_q2_reference_capture_v0.py').read_bytes()).hexdigest() == 'beb0e3d3d9de451fb862090cb92267bc62191386528f1735feb2b3e4b04e02be'


def test_native_revalidates_all_small_original_and_adopted_records():
    prep, original, adopted = K.adopted_inputs(ROOT)
    assert len(prep['files']) == 76 and len(prep['wheels']) == 30
    assert set(original) == set(K.RECORDS)
    assert adopted['native_runtime_qualified'] is False
    assert adopted['adoption']['preparation_source_commit'] != 'bd5b8a65743999c0fae360dd1dd8ec3056b6f1e5'


@pytest.mark.parametrize('name', list(K.FIXED_FILES))
def test_native_rejects_rehashed_small_input_replacements(tmp_path, name):
    for rel in K.FIXED_FILES:
        path = tmp_path / rel; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / rel).read_bytes())
    path = tmp_path / name; path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(K.QualificationCheckError, match='fixed_repository_input_changed'):
        K.adopted_inputs(tmp_path)


@pytest.mark.parametrize('loader', [K.parse, N.strict_json, W.json_value])
@pytest.mark.parametrize('raw', [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}',
                                  b'{"a":"\\ud800"}', b'\xef\xbb\xbf{}', b'\xff', b'{'])
def test_native_readers_reject_ambiguous_records(loader, raw):
    with pytest.raises((ValueError, UnicodeError)):
        loader(raw)


@pytest.mark.parametrize('reader', [K.read, N.safe_read, W.file_bytes])
@pytest.mark.parametrize('mutation', ['file_symlink', 'parent_symlink', 'hardlink', 'fifo', 'oversize'])
def test_native_file_readers_reject_unsafe_inputs(tmp_path, reader, mutation):
    folder = tmp_path / 'folder'; folder.mkdir()
    path = folder / 'in'; path.write_bytes(b'hello')
    if mutation == 'file_symlink':
        original = tmp_path / 'original'; path.rename(original); path.symlink_to(original)
    elif mutation == 'parent_symlink':
        alias = tmp_path / 'alias'; alias.symlink_to(folder, target_is_directory=True); path = alias / 'in'
    elif mutation == 'hardlink':
        os.link(path, tmp_path / 'other')
    elif mutation == 'fifo':
        path.unlink(); os.mkfifo(path)
    with pytest.raises((ValueError, OSError)):
        reader(path, 4 if mutation == 'oversize' else 100)


@pytest.fixture
def native_source(tmp_path):
    repo = tmp_path / 'native-source'; repo.mkdir()
    for rel in N.SOURCES:
        path = repo / rel; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / rel).read_bytes())
    git(repo, 'init', '-q'); git(repo, 'add', '.')
    git(repo, 'commit', '-q', '-m', 'Synthetic native source fixture; not project provenance')
    return repo, git(repo, 'rev-parse', 'HEAD'), tmp_path / 'frozen-source'


def test_native_source_snapshot_is_independently_bound_to_git_bytes(native_source):
    repo, commit, snapshot = native_source
    produced = N.snapshot_sources(repo, snapshot, commit)
    checked = K.check_sources(snapshot, repo, commit)
    assert produced == checked and len(checked) == len(N.SOURCES)
    assert commit != K.ORIGINAL_SOURCE
    assert K.adopted_inputs(snapshot)[0]['context']['source_commit'] == K.ORIGINAL_SOURCE


@pytest.mark.parametrize('where', ['checkout', 'snapshot'])
@pytest.mark.parametrize('name', [N.WORKER, N.CHECKER, N.DIAGNOSTIC, N.SCHEMA])
def test_native_source_change_is_not_accepted_by_rehash(native_source, where, name):
    repo, commit, snapshot = native_source
    N.snapshot_sources(repo, snapshot, commit)
    path = (repo if where == 'checkout' else snapshot) / name
    path.write_bytes(path.read_bytes() + b'\n')
    if where == 'checkout':
        with pytest.raises(N.NativeQualificationError, match='source_checkout_bytes'):
            N.snapshot_sources(repo, snapshot.parent / 'second', commit)
    else:
        with pytest.raises(K.QualificationCheckError, match='consumer_source_mismatch'):
            K.check_sources(snapshot, repo, commit)


def synthetic_native_archive(tmp_path, monkeypatch, mutation=None):
    """78 tiny carrier members, explicitly NOT the actual 508 MB runtime."""
    payloads = {f'data/fixture-{i:03d}': f'synthetic {i}\n'.encode() for i in range(76)}
    prep = {'files': [{'path': p, 'size': len(raw), 'sha256': K.sha(raw)} for p, raw in payloads.items()]}
    if mutation == 'manifest_hash': prep['files'][0]['sha256'] = '0' * 64
    if mutation == 'manifest_size_bool': prep['files'][0]['size'] = True
    if mutation == 'manifest_size': prep['files'][0]['size'] += 1
    original = {'preparation.json': K.encoded(prep), 'q2-runtime-preparation-check.json': b'{}\n'}
    pins = dict(K.RECORDS)
    pins['preparation.json'] = K.sha(original['preparation.json'])
    pins['q2-runtime-preparation-check.json'] = K.sha(original['q2-runtime-preparation-check.json'])
    monkeypatch.setattr(K, 'RECORDS', pins)
    contents = [('q2-runtime-preparation/' + p, data) for p, data in payloads.items()]
    contents += [('q2-runtime-preparation/preparation.json', original['preparation.json']),
                 ('q2-runtime-preparation-check.json', original['q2-runtime-preparation-check.json'])]
    if mutation == 'missing': contents.pop(0)
    elif mutation == 'extra': contents.append(('unselected', b'x'))
    elif mutation == 'duplicate': contents[-1] = contents[0]
    elif mutation == 'traversal': contents[0] = ('../outside', b'x')
    elif mutation == 'rootless': contents = [(p.replace('q2-runtime-preparation/', ''), d) for p, d in contents]
    elif mutation == 'payload': contents[0] = (contents[0][0], b'changed\n')
    archive = tmp_path / 'synthetic.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as z:
        for i, (name, data) in enumerate(contents):
            item = zipfile.ZipInfo(name)
            item.create_system = 3
            import stat as _stat
            mode = _stat.S_IFREG | 0o644
            if i == 0 and mutation == 'symlink': mode = _stat.S_IFLNK | 0o777
            item.external_attr = mode << 16
            z.writestr(item, data)
    monkeypatch.setattr(K, 'ARCHIVE_SHA', K.sha(archive.read_bytes()))
    monkeypatch.setattr(K, 'ARCHIVE_SIZE', archive.stat().st_size)
    return archive, prep, original


def test_native_archive_full_byte_roundtrip_is_only_synthetic(tmp_path, monkeypatch):
    archive, prep, original = synthetic_native_archive(tmp_path, monkeypatch)
    root = K.unpack_verified_archive(archive, tmp_path / 'unpacked', prep, original)
    assert len(list(p for p in root.rglob('*') if p.is_file())) == 77
    for row in prep['files']:
        raw = (root / row['path']).read_bytes()
        assert len(raw) == row['size'] and K.sha(raw) == row['sha256']


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'duplicate', 'traversal', 'rootless',
                                     'payload', 'symlink', 'manifest_hash', 'manifest_size', 'manifest_size_bool'])
def test_native_archive_rejects_rehashed_structural_or_payload_attacks(tmp_path, monkeypatch, mutation):
    archive, prep, original = synthetic_native_archive(tmp_path, monkeypatch, mutation)
    with pytest.raises((K.QualificationCheckError, zipfile.BadZipFile)):
        K.unpack_verified_archive(archive, tmp_path / 'unpacked', prep, original)
    assert not (tmp_path / 'outside').exists()


@pytest.mark.parametrize('mutation', ['changed_byte', 'truncated', 'appended'])
def test_native_archive_external_anchor_cannot_be_changed(tmp_path, monkeypatch, mutation):
    archive, prep, original = synthetic_native_archive(tmp_path, monkeypatch)
    raw = archive.read_bytes()
    if mutation == 'changed_byte': raw = raw[:100] + bytes([raw[100] ^ 1]) + raw[101:]
    elif mutation == 'truncated': raw = raw[:-1]
    else: raw += b'x'
    archive.write_bytes(raw)
    with pytest.raises(K.QualificationCheckError):
        K.unpack_verified_archive(archive, tmp_path / 'unpacked', prep, original)
    assert not (tmp_path / 'unpacked').exists()


def test_native_archive_does_not_replace_an_existing_destination(tmp_path, monkeypatch):
    archive, prep, original = synthetic_native_archive(tmp_path, monkeypatch)
    out = tmp_path / 'existing'; out.mkdir(); (out / 'sentinel').write_bytes(b'keep')
    with pytest.raises(K.QualificationCheckError, match='staging_exists'):
        K.unpack_verified_archive(archive, out, prep, original)
    assert (out / 'sentinel').read_bytes() == b'keep'


def native_wheel():
    """A complete tiny offline test wheel. No model libraries or real weights."""
    import base64 as _base64
    name = 'fake_q2_native_fixture'; di = name + '-1.0.dist-info'
    files = {
        name + '/__init__.py': b'VALUE = "synthetic fixture; not inference evidence"\n',
        di + '/METADATA': b'Metadata-Version: 2.1\nName: fake-q2-native-fixture\nVersion: 1.0\n\nSynthetic only.\n',
        di + '/WHEEL': b'Wheel-Version: 1.0\nGenerator: synthetic-offline-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
    }
    records = []
    for path, data in files.items():
        h = _base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
        records.append(f'{path},sha256={h},{len(data)}\n')
    records.append(f'{di}/RECORD,,\n')
    files[di + '/RECORD'] = ''.join(records).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        for path, data in files.items(): z.writestr(path, data)
    return name + '-1.0-py3-none-any.whl', buffer.getvalue(), files


@pytest.fixture
def installed_synthetic(tmp_path, monkeypatch):
    import base64 as _base64
    env = tmp_path / 'venv'; env.mkdir()
    (env / 'pyvenv.cfg').write_text('include-system-site-packages = false\n')
    (env / 'bin').mkdir(); (env / 'bin/python').write_bytes(b'NOT AN EXECUTABLE: synthetic fixture\n')
    bootstrap = tmp_path / 'bootstrap.json'; bootstrap.write_bytes(K.encoded(K.tree_inventory(env)))
    bundle = tmp_path / 'bundle'; (bundle / 'wheelhouse').mkdir(parents=True)
    filename, raw, files = native_wheel()
    wheel = bundle / 'wheelhouse' / filename; wheel.write_bytes(raw)
    row = {'name': 'fake-q2-native-fixture', 'version': '1.0', 'path': 'wheelhouse/' + filename,
           'size': len(raw), 'sha256': K.sha(raw)}
    prep_raw = K.encoded({'wheels': [row]})
    (bundle / 'preparation.json').write_bytes(prep_raw)
    monkeypatch.setattr(K, 'RECORDS', {**K.RECORDS, 'preparation.json': K.sha(prep_raw)})
    site = env / 'lib/python3.11/site-packages'
    for name, data in files.items():
        path = site / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    di = site / 'fake_q2_native_fixture-1.0.dist-info'
    (di / 'INSTALLER').write_bytes(b'pip\n')
    record = (di / 'RECORD').read_bytes()
    h = _base64.urlsafe_b64encode(hashlib.sha256(b'pip\n').digest()).rstrip(b'=').decode()
    (di / 'RECORD').write_bytes(record + f'fake_q2_native_fixture-1.0.dist-info/INSTALLER,sha256={h},4\n'.encode())
    report = {'version': '1', 'install': [{'metadata': {'name': row['name'], 'version': row['version']},
              'download_info': {'url': wheel.as_uri(), 'archive_info': {'hashes': {'sha256': row['sha256']}}}}]}
    pip_report = tmp_path / 'pip-report.json'; pip_report.write_bytes(K.encoded(report))
    return env, bundle, bootstrap, pip_report


def test_native_installation_checker_reconstructs_synthetic_wheel_payloads(installed_synthetic):
    result = K.verify_installation(*installed_synthetic)
    assert result['wheel_payload_file_count'] == 3
    assert result['distributions'] == {'fake-q2-native-fixture': {'version': '1.0',
        'metadata': 'lib/python3.11/site-packages/fake_q2_native_fixture-1.0.dist-info/METADATA'}}
    assert result['authority_effect'] == 'none' and result['production_gate_eligible'] is False


@pytest.mark.parametrize('mutation', ['payload', 'payload_and_record', 'extra_import', 'extra_pth',
    'bootstrap', 'system_site', 'report_remote', 'report_version', 'report_hash', 'report_duplicate',
    'report_missing', 'wheel_changed', 'preparation_rehash', 'record_unhashed', 'record_traversal', 'pyc'])
def test_native_installation_checker_rejects_substitution(installed_synthetic, mutation):
    import base64 as _base64
    env, bundle, bootstrap, pip_report = installed_synthetic
    site = env / 'lib/python3.11/site-packages'
    package = site / 'fake_q2_native_fixture/__init__.py'
    record = site / 'fake_q2_native_fixture-1.0.dist-info/RECORD'
    if mutation in ('payload', 'payload_and_record'):
        package.write_bytes(b'SUBSTITUTED = True\n')
        if mutation == 'payload_and_record':
            h = _base64.urlsafe_b64encode(hashlib.sha256(package.read_bytes()).digest()).rstrip(b'=').decode()
            lines = record.read_text().splitlines(True)
            lines[0] = f'fake_q2_native_fixture/__init__.py,sha256={h},{package.stat().st_size}\n'
            record.write_text(''.join(lines))
    elif mutation == 'extra_import': (site / 'unselected.py').write_bytes(b'x=1\n')
    elif mutation == 'extra_pth': (site / 'unselected.pth').write_bytes(b'import unselected\n')
    elif mutation == 'bootstrap': (env / 'bin/python').write_bytes(b'changed\n')
    elif mutation == 'system_site': (env / 'pyvenv.cfg').write_text('include-system-site-packages = true\n')
    elif mutation.startswith('report_'):
        obj = K.parse(pip_report.read_bytes()); item = obj['install'][0]
        if mutation == 'report_remote': item['download_info']['url'] = 'https://example.invalid/wheel.whl'
        elif mutation == 'report_version': item['metadata']['version'] = '2.0'
        elif mutation == 'report_hash': item['download_info']['archive_info']['hashes']['sha256'] = '0' * 64
        elif mutation == 'report_duplicate': obj['install'] *= 2
        else: obj['install'] = []
        pip_report.write_bytes(K.encoded(obj))
    elif mutation == 'wheel_changed':
        path = next((bundle / 'wheelhouse').iterdir()); path.write_bytes(path.read_bytes() + b'changed')
    elif mutation == 'preparation_rehash':
        path = bundle / 'preparation.json'; path.write_bytes(path.read_bytes() + b'\n')
    elif mutation == 'record_unhashed': record.write_bytes(record.read_bytes().replace(b'INSTALLER,sha256=', b'INSTALLER,,#'))
    elif mutation == 'record_traversal': record.write_bytes(record.read_bytes() + b'../../../../../../etc/passwd,,\n')
    elif mutation == 'pyc': (site / 'unselected.pyc').write_bytes(b'NOT BYTECODE\n')
    with pytest.raises((K.QualificationCheckError, ValueError, OSError)):
        K.verify_installation(*installed_synthetic)


@pytest.mark.parametrize('bad_hash', [False, True])
def test_actual_offline_installer_body_with_tiny_synthetic_wheel_only(tmp_path, bad_hash):
    # Real subprocess, fresh venv, ensurepip, hash-locked --no-index pip.
    # Host Python is recorded by the handoff; this is NOT native qualification,
    # and no systemd isolation, real Q2 wheel, tokenizer or model is claimed.
    filename, raw, _ = native_wheel()
    wheelhouse = tmp_path / 'wheels'; wheelhouse.mkdir()
    (wheelhouse / filename).write_bytes(raw)
    lock = tmp_path / 'synthetic.lock'
    lock.write_text('fake-q2-native-fixture==1.0 --hash=sha256:' + ('0' * 64 if bad_hash else K.sha(raw)) + '\n')
    work = tmp_path / 'work'; work.mkdir()
    result = subprocess.run([sys.executable, '-I', '-B', '-c', N.INSTALLER,
        str(work), str(wheelhouse), str(lock), str(work)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=N.clean_env(work), timeout=60)
    if bad_hash:
        assert result.returncode != 0
        assert b'Expected sha256' in (work / 'pip-install.log').read_bytes()
    else:
        assert result.returncode == 0, result.stderr.decode()
        report = json.loads((work / 'pip-report.json').read_bytes())
        assert [x['metadata']['name'] for x in report['install']] == ['fake-q2-native-fixture']
        assert report['install'][0]['download_info']['archive_info']['hashes']['sha256'] == K.sha(raw)
        assert not list((work / 'venv').rglob('*.pyc'))
        assert b'offline_installation_finished' in result.stdout


def synthetic_response(new_ids=None, text=' quartz\n'):
    import base64 as _base64
    return {'record_type': 'q2_native_diagnostic_response_v0', 'binding': {},
            'call_id': 'diagnostic-0001', 'attempt': 1, 'scored': False,
            'input_ids': [1, 11, 12], 'new_token_ids': [41, 2] if new_ids is None else new_ids,
            'text': text, 'text_utf8_base64': _base64.b64encode(text.encode()).decode(),
            'stop_reason': 'eos' if new_ids is None or new_ids[-1] == 2 else 'token_limit',
            'effective_generation': {}, 'runtime': {}}


@pytest.mark.parametrize('text', ['', ' quartz\n', 'I refuse to answer.', 'Őrzött adat\n第二行', '__UNKNOWN__'])
def test_native_checker_preserves_full_text_without_scoring_or_repair(text):
    value = synthetic_response(text=text)
    K.validate_tokens_and_text(value, [1, 11, 12], lambda ids: text)
    assert value['text'] == text and value['scored'] is False


def test_native_checker_accepts_completed_cap_but_not_a_timeout():
    value = synthetic_response(new_ids=[41] * 32)
    K.validate_tokens_and_text(value, [1, 11, 12], lambda ids: ' quartz\n')
    value['stop_reason'] = 'timeout'
    with pytest.raises(K.QualificationCheckError):
        K.validate_tokens_and_text(value, [1, 11, 12], lambda ids: ' quartz\n')


@pytest.mark.parametrize('mutation', ['extra', 'missing', 'call', 'attempt_bool', 'attempt_two', 'scored',
    'input', 'input_bool', 'token_bool', 'negative', 'out_of_vocab', 'too_many', 'empty', 'short_no_eos',
    'duplicate_eos', 'stop', 'trimmed', 'changed_utf8', 'decode_mismatch'])
def test_native_checker_rejects_rehashed_token_text_records(mutation):
    value = synthetic_response()
    if mutation == 'extra': value['PASS'] = True
    elif mutation == 'missing': del value['input_ids']
    elif mutation == 'call': value['call_id'] = 'group-001-repeat-1'
    elif mutation == 'attempt_bool': value['attempt'] = True
    elif mutation == 'attempt_two': value['attempt'] = 2
    elif mutation == 'scored': value['scored'] = True
    elif mutation == 'input': value['input_ids'] = [1, 11, 13]
    elif mutation == 'input_bool': value['input_ids'][0] = True
    elif mutation == 'token_bool': value['new_token_ids'][0] = True
    elif mutation == 'negative': value['new_token_ids'][0] = -1
    elif mutation == 'out_of_vocab': value['new_token_ids'][0] = 49152
    elif mutation == 'too_many': value['new_token_ids'] = [41] * 32 + [2]
    elif mutation == 'empty': value['new_token_ids'] = []
    elif mutation == 'short_no_eos': value['new_token_ids'] = [41]
    elif mutation == 'duplicate_eos': value['new_token_ids'] = [2, 41, 2]
    elif mutation == 'stop': value['stop_reason'] = 'timeout'
    elif mutation == 'trimmed': value['text'] = value['text'].strip()
    elif mutation == 'changed_utf8': value['text_utf8_base64'] = 'Y2hhbmdlZA=='
    with pytest.raises(K.QualificationCheckError):
        K.validate_tokens_and_text(value, [1, 11, 12], lambda ids: 'wrong' if mutation == 'decode_mismatch' else ' quartz\n')


@pytest.mark.parametrize('tail,reason', [([2], 'eos'), ([41, 2], 'eos'), ([41] * 32, 'token_limit')])
def test_worker_continuation_split_keeps_original_ids(tail, reason):
    assert W.split_continuation([1, 11], [1, 11] + tail) == (tail, reason)


@pytest.mark.parametrize('tail', [[], [41], [41] * 33, [2, 2], [True, 2], [-1, 2], [49152, 2]])
def test_worker_never_turns_incomplete_execution_into_unknown(tail):
    with pytest.raises(W.WorkerError):
        W.split_continuation([1, 11], [1, 11] + tail)


def test_worker_rejects_a_changed_generated_prompt_prefix():
    with pytest.raises(W.WorkerError, match='generated_prefix_changed'):
        W.split_continuation([1, 11], [1, 12, 41, 2])


def synthetic_sandbox(stage='worker'):
    return {'stage': stage, 'unit': 'pulse-q2-' + 'a' * 24 + '-' + stage + '.service', 'pid': 123,
            'host_netns': 'net:[1]', 'child_netns': 'net:[2]', 'uid': 65534,
            'no_new_privs': True, 'capabilities': '0000000000000000',
            'ipv4_blocked': True, 'ipv6_blocked': True, 'memory_max': '4294967296',
            'memory_swap_max': '0', 'pids_max': '64', 'cpu_max': '100000 100000',
            'properties': {**{k: N.PROPERTIES[k] for k in ('PrivateNetwork', 'NoNewPrivileges',
                'ProtectSystem', 'ProtectHome', 'KillMode', 'SendSIGKILL', 'User', 'Group',
                'CapabilityBoundingSet', 'RestrictAddressFamilies')},
                'RuntimeMaxUSec': {480: '8min', 300: '5min', 180: '3min'}[N.STAGES[stage]]}}


@pytest.mark.parametrize('stage', list(N.STAGES))
def test_checker_accepts_consistent_synthetic_kernel_observation_only(stage):
    # This is protocol validation, not a real namespace or cgroup observation.
    K.verify_sandbox_observation(synthetic_sandbox(stage), stage)


@pytest.mark.parametrize('key,value', [('host_netns', 'net:[2]'), ('child_netns', 'declared_offline'),
    ('uid', 0), ('uid', False), ('no_new_privs', False), ('no_new_privs', 1),
    ('capabilities', 'ffffffffffffffff'), ('ipv4_blocked', False), ('ipv6_blocked', False),
    ('memory_max', 'max'), ('memory_swap_max', 'max'), ('pids_max', 'max'), ('cpu_max', 'max 100000'),
    ('pid', True), ('stage', 'installer'), ('unit', 'unrelated.service')])
def test_checker_rejects_unenforced_or_self_declared_isolation(key, value):
    observed = synthetic_sandbox(); observed[key] = value
    with pytest.raises(K.QualificationCheckError):
        K.verify_sandbox_observation(observed, 'worker')


@pytest.mark.parametrize('property_name', ['PrivateNetwork', 'NoNewPrivileges', 'ProtectSystem', 'ProtectHome',
    'KillMode', 'SendSIGKILL', 'User', 'Group', 'CapabilityBoundingSet', 'RestrictAddressFamilies', 'RuntimeMaxUSec'])
def test_checker_requires_each_effective_service_control(property_name):
    value = synthetic_sandbox(); value['properties'][property_name] = 'unavailable'
    with pytest.raises(K.QualificationCheckError):
        K.verify_sandbox_observation(value, 'worker')


def test_service_command_uses_real_kernel_controls_and_no_credentials(tmp_path, monkeypatch):
    for name in ('HF_TOKEN', 'GITHUB_TOKEN', 'HTTPS_PROXY', 'OPENAI_API_KEY', 'PYTHONPATH', 'LD_PRELOAD'):
        monkeypatch.setenv(name, 'DO_NOT_INHERIT')
    command = N.service_command('pulse-q2-' + 'a' * 24 + '-worker.service', 'worker',
                                ['/fixed/venv/bin/python', '-I', '/fixed/worker.py'], tmp_path, Path('/fixed/python'))
    for prop in ('PrivateNetwork=yes', 'NoNewPrivileges=yes', 'RestrictAddressFamilies=AF_UNIX',
                 'MemoryMax=4294967296', 'MemorySwapMax=0', 'TasksMax=64',
                 'KillMode=control-group', 'RuntimeMaxSec=180', 'ProtectSystem=strict'):
        assert '--property=' + prop in command
    assert '/usr/bin/env' in command and '-i' in command
    assert 'DO_NOT_INHERIT' not in repr(command)
    assert N.BARRIER in command and 'connect sendto sendmsg sendmmsg' in repr(command)


def test_generation_watchdog_is_an_independent_systemd_timer(monkeypatch):
    calls = []
    def control(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=b'', stderr=b'')
    monkeypatch.setattr(N, 'control', control)
    prefix = 'pulse-q2-' + 'a' * 24
    timer = N.watchdog(prefix, prefix + '-worker.service')
    assert timer == prefix + '-watchdog.timer'
    assert '--on-active=20s' in calls[0] and '--timer-property=AccuracySec=1us' in calls[0]
    assert N.GENERATION_NS == 15_000_000_000
    assert '--kill-whom=all' in calls[0] and '--signal=KILL' in calls[0]
    assert calls[1] == ['/usr/bin/systemctl', 'is-active', '--quiet', timer]


def test_watchdog_failure_cannot_be_ignored(monkeypatch):
    monkeypatch.setattr(N, 'control', lambda *a, **k: (_ for _ in ()).throw(N.NativeQualificationError('unavailable')))
    with pytest.raises(N.NativeQualificationError):
        N.watchdog('pulse-q2-' + 'a' * 24, 'pulse-q2-' + 'a' * 24 + '-worker.service')


@pytest.mark.parametrize('payload,limit', [(b'first\nsecond\n', 100), (b'x' * 8192, 100)])
def test_real_subprocess_framing_and_output_bound(payload, limit):
    import time as _time
    proc = subprocess.Popen([sys.executable, '-I', '-c', 'import os;os.write(1,' + repr(payload) + ')'],
                            stdout=subprocess.PIPE, start_new_session=True)
    reader = N.BoundedReader(proc.stdout, limit)
    try:
        if limit == 100 and len(payload) > limit:
            with pytest.raises(N.NativeQualificationError, match='protocol_output_bound'):
                reader.line(_time.monotonic() + 5)
        else:
            assert reader.line(_time.monotonic() + 5) == b'first\n'
            assert reader.finish(_time.monotonic() + 5) == b'second\n'
    finally:
        proc.wait(timeout=5); reader.close(); proc.stdout.close()


def test_real_harmless_subprocess_deadline_is_external_to_child():
    import time as _time
    import signal as _signal
    proc = subprocess.Popen([sys.executable, '-I', '-c', 'import time;time.sleep(30)'],
                            stdout=subprocess.PIPE, start_new_session=True)
    reader = N.BoundedReader(proc.stdout)
    started = _time.monotonic()
    try:
        with pytest.raises(N.NativeQualificationError, match='external_deadline_expired'):
            reader.line(started + 0.1)
        assert proc.poll() is None
    finally:
        os.killpg(proc.pid, _signal.SIGKILL); proc.wait(timeout=5)
        reader.close(); proc.stdout.close()
    assert _time.monotonic() - started < 3


def test_real_local_checker_timeout_kills_its_process_group(tmp_path):
    import time as _time
    with pytest.raises(subprocess.TimeoutExpired):
        N.bounded_local([sys.executable, '-I', '-c', 'import time;time.sleep(30)'],
                        tmp_path / 'timeout.log', _time.monotonic() + 0.15)
    assert (tmp_path / 'timeout.log').exists()


@pytest.mark.parametrize('script,extras', [
    ('qualify_q2_reference_runtime_v0.py', ['qualify-runtime', '--repo-root', '/unused', '--archive', '/unused',
       '--output-dir', '/unused', '--expected-source-sha', '0' * 40]),
    ('run_q2_reference_subject_v0.py', ['--source-root', '/unused', '--bundle', '/unused',
       '--prelaunch', '/unused', '--expected-prelaunch-sha256', '0' * 64]),
    ('check_q2_reference_qualification_v0.py', ['verify-inputs', '--archive', '/unused', '--staging', '/unused',
       '--source-root', '/unused', '--repo-root', '/unused', '--expected-source-sha', '0' * 40, '--output', '/unused'])])
@pytest.mark.parametrize('bypass', ['--skip-isolation', '--synthetic', '--model', '--retries', '--prompt'])
def test_native_clis_have_no_runtime_or_model_bypass(script, extras, bypass):
    result = subprocess.run([sys.executable, '-I', str(TOOLS / script), *extras, bypass, 'test'],
                            capture_output=True, timeout=10)
    assert result.returncode == 2 and b'unrecognized arguments' in result.stderr


def test_native_qualification_needs_explicit_consent_before_any_work(tmp_path, monkeypatch):
    monkeypatch.setattr(N, 'check_context', lambda *a: (_ for _ in ()).throw(AssertionError('must not run')))
    with pytest.raises(N.NativeQualificationError, match='explicit_unscored_diagnostic_confirmation_required'):
        N.qualify(tmp_path, tmp_path / 'missing.zip', tmp_path / 'out', '0' * 40, False)
    assert not (tmp_path / 'out').exists()


def test_native_checker_does_not_import_or_execute_producer_or_worker():
    text = (TOOLS / 'check_q2_reference_qualification_v0.py').read_text()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any('qualify_q2_reference' in n.name or 'run_q2_reference' in n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert not any(x in (node.module or '') for x in ('qualify_q2_reference', 'run_q2_reference'))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in ('generate', 'from_pretrained') or (
                node.func.attr == 'from_pretrained' and isinstance(node.func.value, ast.Name)
                and node.func.value.id == 'AutoTokenizer')
    assert 'AutoModelForCausalLM' not in text


def test_worker_load_and_generation_controls_are_explicit_in_source():
    tree = ast.parse((TOOLS / 'run_q2_reference_subject_v0.py').read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    loads = [n for n in calls if n.func.attr == 'from_pretrained']
    assert len(loads) == 2
    for call in loads:
        kw = {k.arg: k.value for k in call.keywords}
        assert isinstance(kw['local_files_only'], ast.Constant) and kw['local_files_only'].value is True
        assert isinstance(kw['trust_remote_code'], ast.Constant) and kw['trust_remote_code'].value is False
    model_call = next(n for n in loads if n.func.value.id == 'AutoModelForCausalLM')
    kw = {k.arg: k.value for k in model_call.keywords}
    assert kw['use_safetensors'].value is True and kw['attn_implementation'].value == 'eager'
    generation = [n for n in calls if n.func.attr == 'generate']
    assert len(generation) == 1
    assert {k.arg: k.value for k in generation[0].keywords}['use_model_defaults'].value is False
    assert not any(n.func.attr in ('compile', 'load', 'load_state_dict') for n in calls)


def test_workflow_native_mode_is_manual_separate_and_explicitly_consented():
    workflow = yaml.safe_load(_q2_workflow_text())
    inputs = workflow.get('on', workflow.get(True))['workflow_dispatch']['inputs']
    assert inputs['mode']['default'] == 'prepare-runtime'
    assert inputs['mode']['options'] == ['prepare-runtime', 'qualify-runtime']
    assert inputs['confirm_diagnostic_retention']['default'] is False
    steps = workflow['jobs']['prepare']['steps']
    guard = steps[0]['run']
    assert 'CONFIRM_DIAGNOSTIC' in guard and 'case "$MODE"' in guard
    native = [s for s in steps if s.get('id') == 'qualify']
    assert len(native) == 1 and native[0]['if'] == "inputs.mode == 'qualify-runtime'"
    assert '/usr/bin/timeout --signal=TERM --kill-after=180s 1200s' in native[0]['run']
    assert '--confirm-one-unscored-diagnostic' in native[0]['run']
    download = next(s for s in steps if 'curl --fail' in s.get('run', ''))
    assert download['if'] == "inputs.mode == 'qualify-runtime'"
    assert '11282419957/zip' in download['run'] and N.ARCHIVE_SHA in download['run']
    assert '--retry 0' in download['run'] and '--location-trusted' not in download['run']
    uploads = [s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@')]
    assert len(uploads) == 2
    assert all(s['with']['overwrite'] is False and s['with']['include-hidden-files'] is True for s in uploads)
    assert sum("inputs.mode == 'qualify-runtime'" in s['if'] for s in uploads) == 1
    assert 'build_q2_reference_summary.py' not in _q2_workflow_text()
    assert 'check_gates.py' not in _q2_workflow_text()


def test_native_sources_have_python_311_syntax_without_execution():
    for name in (N.SELF, N.CHECKER, N.WORKER):
        ast.parse((ROOT / name).read_text(), feature_version=(3, 11))
    ast.parse(N.INSTALLER, feature_version=(3, 11))
    ast.parse(N.BARRIER, feature_version=(3, 11))


def test_workflow_shell_syntax_is_valid_without_running_any_step(tmp_path):
    workflow = yaml.safe_load(_q2_workflow_text())
    for index, step in enumerate(workflow['jobs']['prepare']['steps']):
        if 'run' not in step: continue
        script = tmp_path / f'step-{index}.sh'; script.write_text(step['run'])
        result = subprocess.run(['/bin/bash', '-n', str(script)], capture_output=True, timeout=10)
        assert result.returncode == 0, result.stderr.decode()




def synthetic_jcs_subset(value):
    """Test double for this integral-number fixture, NOT a general JCS library."""
    if type(value) is dict:
        return b'{' + b','.join(synthetic_jcs_subset(k) + b':' + synthetic_jcs_subset(value[k])
                               for k in sorted(value, key=lambda k: k.encode('utf-16-be'))) + b'}'
    if type(value) is list:
        return b'[' + b','.join(synthetic_jcs_subset(x) for x in value) + b']'
    if type(value) is float:
        assert value.is_integer(), 'Only the selected fixture integral-number subset is supported'
        return str(int(value)).encode()
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()


@pytest.fixture
def diagnostic_synthetic(installed_synthetic, tmp_path, monkeypatch):
    """Complete in-process protocol fixture with synthetic framework doubles."""
    import contextlib
    import types
    import importlib.metadata
    env, bundle, bootstrap, pip_report = installed_synthetic
    source = tmp_path / 'source'
    for name in N.SOURCES:
        path = source / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    (bundle / 'model').mkdir()
    model_rows = []
    for name in sorted(W.MODEL_NAMES):
        raw = (b'{"bos_token_id":1,"eos_token_id":2,"pad_token_id":2}\n'
               if name in ('config.json', 'generation_config.json') else b'SYNTHETIC NON-MODEL BYTES\n')
        (bundle / 'model' / name).write_bytes(raw)
        model_rows.append({'path': 'model/' + name, 'size': len(raw), 'sha256': K.sha(raw)})
    map_raw = K.encoded({'files': model_rows})
    (source / W.MODEL_MAP).write_bytes(map_raw)
    monkeypatch.setattr(W, 'PINNED_MAP', K.sha(map_raw))
    monkeypatch.setattr(K, 'adopted_inputs', lambda root: None)
    monkeypatch.setattr(K, 'native_target', lambda: None)
    monkeypatch.setattr(W, 'platform', types.SimpleNamespace(
        python_implementation=lambda: 'CPython', python_version=lambda: '3.11.16',
        system=lambda: 'Linux', machine=lambda: 'x86_64',
        freedesktop_os_release=lambda: {'ID': 'ubuntu', 'VERSION_ID': '24.04'}))
    monkeypatch.setattr(W.os, 'getuid', lambda: 65534)
    output = io.BytesIO()
    fake_sys = types.SimpleNamespace(flags=types.SimpleNamespace(isolated=True),
        prefix=str(env), base_prefix='/synthetic-bootstrap',
        stdin=types.SimpleNamespace(buffer=io.BytesIO(b'GENERATE diagnostic-0001\n')),
        stdout=types.SimpleNamespace(buffer=output))
    monkeypatch.setattr(W, 'sys', fake_sys)
    monkeypatch.setattr(K, 'sys', fake_sys)
    class Tensor:
        def __init__(self, data): self.data = data; self.shape = (len(data), len(data[0]))
        def __getitem__(self, i): return types.SimpleNamespace(tolist=lambda: list(self.data[i]))
    class Config:
        def __init__(self, **kwargs): self.values = kwargs
        def to_dict(self): return {'transformers_version': '4.57.6', **self.values}
    torch = types.ModuleType('torch'); torch.__file__ = str(env / 'synthetic_torch.py')
    torch.__version__ = '2.8.0+cpu'; torch.version = types.SimpleNamespace(cuda=None)
    torch.float32 = 'torch.float32'; torch.long = 'torch.int64'
    counters = {'generate': 0, 'model_load': 0, 'tokenizer_load': 0, 'seeds': [], 'threads': None, 'interop': None,
                'deterministic': False, 'generation_kwargs': None}
    torch.set_num_threads = lambda x: counters.update(threads=x)
    torch.set_num_interop_threads = lambda x: counters.update(interop=x)
    torch.use_deterministic_algorithms = lambda x: counters.update(deterministic=x)
    torch.get_num_threads = lambda: counters['threads']
    torch.get_num_interop_threads = lambda: counters['interop']
    torch.are_deterministic_algorithms_enabled = lambda: counters['deterministic']
    torch.manual_seed = lambda x: counters['seeds'].append(x)
    torch.inference_mode = contextlib.nullcontext
    torch.tensor = lambda data, **kw: Tensor(data)
    torch.ones_like = lambda t: Tensor([[1] * len(t.data[0])])
    class Tokenizer:
        is_fast = True; bos_token_id = 1; eos_token_id = 2; pad_token_id = 2
        def apply_chat_template(self, messages, **kwargs):
            assert messages == W.MESSAGES
            assert kwargs == {'tokenize': True, 'add_generation_prompt': True}
            return [1, 11, 12]
        def decode(self, ids, **kwargs):
            assert kwargs == {'skip_special_tokens': True, 'clean_up_tokenization_spaces': False}
            return ' quartz\n'
    class LlamaForCausalLM:
        training = True; is_quantized = False
        config = types.SimpleNamespace(_attn_implementation='eager')
        def to(self, device): assert device == 'cpu'; return self
        def eval(self): self.training = False; return self
        def parameters(self):
            return [types.SimpleNamespace(device=types.SimpleNamespace(type='cpu'), dtype=torch.float32)]
        def generate(self, **kwargs):
            counters['generate'] += 1; counters['generation_kwargs'] = kwargs
            assert kwargs['use_model_defaults'] is False
            assert kwargs['generation_config'].values['disable_compile'] is True
            assert counters['seeds'][-1] == 1729
            return Tensor([kwargs['input_ids'].data[0] + [41, 2]])
    def load_tokenizer(path, **kwargs):
        counters['tokenizer_load'] += 1
        assert Path(path) == bundle / 'model'
        assert kwargs == {'local_files_only': True, 'trust_remote_code': False, 'use_fast': True}
        return Tokenizer()
    def load_model(path, **kwargs):
        counters['model_load'] += 1
        assert Path(path) == bundle / 'model'
        assert kwargs == {'local_files_only': True, 'trust_remote_code': False, 'use_safetensors': True,
                          'torch_dtype': torch.float32, 'attn_implementation': 'eager', 'device_map': None}
        return LlamaForCausalLM()
    transformers = types.ModuleType('transformers'); transformers.__file__ = str(env / 'synthetic_transformers.py')
    transformers.__version__ = '4.57.6'; transformers.GenerationConfig = Config
    transformers.AutoTokenizer = types.SimpleNamespace(from_pretrained=load_tokenizer)
    transformers.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=load_model)
    rfc = types.ModuleType('rfc8785'); rfc.__file__ = str(env / 'synthetic_rfc.py'); rfc.dumps = synthetic_jcs_subset
    for name, mod in (('torch', torch), ('transformers', transformers), ('rfc8785', rfc)):
        monkeypatch.setitem(sys.modules, name, mod)
    old_version = importlib.metadata.version
    versions = {'torch': '2.8.0+cpu', 'transformers': '4.57.6', 'rfc8785': '0.1.4'}
    monkeypatch.setattr(importlib.metadata, 'version', lambda name: versions[name] if name in versions else old_version(name))
    rows = [{'path': name, 'size': (source / name).stat().st_size,
             'sha256': K.sha((source / name).read_bytes())} for name in N.SOURCES]
    installation_raw = K.encoded(K.verify_installation(env, bundle, bootstrap, pip_report))
    expected_source = 'c' * 40; expected_run = '123456'
    pre = {'record_type': 'q2_native_prelaunch_v0', 'context': {
        'source_commit': expected_source, 'run_id': expected_run, 'run_attempt': 1,
        'repository': 'HKati/pulse-release-gates-0.1', 'actor': 'HKati', 'event': 'workflow_dispatch',
        'workflow': N.WF}, 'source_files': rows, 'preparation_source_commit': K.ORIGINAL_SOURCE,
        'preparation_run_id': K.ORIGINAL_RUN, 'artifact_sha256': K.ARCHIVE_SHA,
        'selection_sha256': K.FIXED_FILES[K.SELECTION], 'workload_sha256': K.FIXED_FILES[K.WORKLOAD],
        'diagnostic_sha256': K.sha((source / K.DIAGNOSTIC).read_bytes()),
        'installation_sha256': K.sha(installation_raw),
        'environment_inventory_sha256': K.sha(K.encoded(K.parse(installation_raw)['inventory'])),
        'limits': {'generation_seconds': 15, 'phase_seconds': 1200, 'memory_bytes': 4294967296, 'tasks': 64},
        'authority_effect': 'none', 'production_gate_eligible': False, 'scored_call_count': 0}
    pre_raw = K.encoded(pre); pre_path = tmp_path / 'prelaunch.json'; pre_path.write_bytes(pre_raw)
    assert W.run(source, bundle, pre_path, K.sha(pre_raw)) == 0
    ready_raw, response_raw = [line + b'\n' for line in output.getvalue().splitlines()]
    observation = {'sandbox': synthetic_sandbox(), 'generation_start_ns': 1000,
        'response_received_ns': 2000, 'generation_deadline_ns': 15_000_001_000,
        'watchdog_armed': True, 'watchdog_unit': 'pulse-q2-' + 'a' * 24 + '-watchdog.timer', 'worker_exit_code': 0}
    arguments = [source, bundle, env, pre_raw, installation_raw, response_raw, ready_raw, observation,
                 bootstrap, pip_report, synthetic_sandbox('installer'), synthetic_sandbox('installcheck'),
                 expected_source, expected_run, K.sha(K.encoded(rows))]
    return arguments, counters


def test_native_worker_and_separate_checker_full_protocol_with_synthetic_doubles(diagnostic_synthetic):
    arguments, counters = diagnostic_synthetic
    assert counters['model_load'] == counters['generate'] == 1
    assert counters['tokenizer_load'] == 1
    result = K.verify_diagnostic(*arguments)
    assert counters['generate'] == 1 and counters['model_load'] == 1
    assert counters['tokenizer_load'] == 2  # independent prompt/decoding reconstruction
    assert result['single_unscored_diagnostic_verified'] is True
    assert result['qualification_scope'] == 'one_unscored_diagnostic'
    assert result['authority_effect'] == 'none' and result['production_gate_eligible'] is False
    assert result['malicious_platform_resistance'] is False
    response = K.parse(arguments[5])
    assert response['text'] == ' quartz\n' and response['new_token_ids'] == [41, 2]
    assert response['effective_generation']['disable_compile'] is True


@pytest.mark.parametrize('mutation', ['prelaunch_whitespace', 'prelaunch_extra', 'source_commit', 'run_id',
    'run_attempt_bool', 'history_rebound', 'archive', 'scored_bool', 'authority', 'limit_bool', 'limit_relaxed',
    'installation_bytes', 'source_scope', 'source_hash', 'diagnostic_hash', 'runtime_file', 'model_file',
    'response_whitespace', 'response_binding', 'response_binding_bool', 'effective_sample', 'effective_sample_integer',
    'effective_compile', 'runtime_compile', 'runtime_bool', 'runtime_threads', 'ready_binding', 'ready_extra',
    'ready_runtime', 'late_response', 'negative_time', 'watchdog_missing', 'worker_failed', 'worker_exit_bool',
    'installer_network', 'installer_memory', 'installcheck_namespace', 'worker_namespace', 'extra_observation', 'relaxed_stage_timeout', 'different_timer', 'different_installer'])
def test_native_separate_checker_rejects_rehashed_full_protocol_mutations(diagnostic_synthetic, mutation):
    args, _ = diagnostic_synthetic
    args = list(args)
    pre = K.parse(args[3]); response = K.parse(args[5]); ready = K.parse(args[6]); observation = copy.deepcopy(args[7])
    if mutation == 'prelaunch_whitespace': args[3] += b'\n'
    elif mutation == 'prelaunch_extra': pre['PASS'] = True
    elif mutation == 'source_commit': pre['context']['source_commit'] = 'd' * 40
    elif mutation == 'run_id': pre['context']['run_id'] = '9999'
    elif mutation == 'run_attempt_bool': pre['context']['run_attempt'] = True
    elif mutation == 'history_rebound': pre['preparation_source_commit'] = pre['context']['source_commit']
    elif mutation == 'archive': pre['artifact_sha256'] = '0' * 64
    elif mutation == 'scored_bool': pre['scored_call_count'] = False
    elif mutation == 'authority': pre['production_gate_eligible'] = True
    elif mutation == 'limit_bool': pre['limits']['tasks'] = True
    elif mutation == 'limit_relaxed': pre['limits']['generation_seconds'] = 60
    elif mutation == 'installation_bytes': args[4] += b'\n'
    elif mutation == 'source_scope': pre['source_files'] = pre['source_files'][:-1]
    elif mutation == 'source_hash': pre['source_files'][0]['sha256'] = '0' * 64
    elif mutation == 'diagnostic_hash': pre['diagnostic_sha256'] = '0' * 64
    elif mutation == 'runtime_file': (args[2] / 'bin/python').write_bytes(b'REPLACED\n')
    elif mutation == 'model_file': (args[1] / 'model/model.safetensors').write_bytes(b'REPLACED\n')
    elif mutation == 'response_whitespace': args[5] += b'\n'
    elif mutation == 'response_binding': response['binding']['run_id'] = '9876'
    elif mutation == 'response_binding_bool': response['binding']['run_attempt'] = True
    elif mutation == 'effective_sample': response['effective_generation']['do_sample'] = True
    elif mutation == 'effective_sample_integer': response['effective_generation']['do_sample'] = 0
    elif mutation == 'effective_compile': response['effective_generation']['disable_compile'] = False
    elif mutation == 'runtime_compile': response['runtime']['compile'] = True
    elif mutation == 'runtime_bool': response['runtime']['evaluation'] = 1
    elif mutation == 'runtime_threads': response['runtime']['threads'] = 2
    elif mutation == 'ready_binding': ready['binding']['source_commit'] = 'd' * 40
    elif mutation == 'ready_extra': ready['extra'] = True
    elif mutation == 'ready_runtime': ready['runtime']['seed'] = 1730
    elif mutation == 'late_response': observation['response_received_ns'] = observation['generation_deadline_ns'] + 1
    elif mutation == 'negative_time': observation['generation_start_ns'] = -1
    elif mutation == 'watchdog_missing': observation['watchdog_armed'] = False
    elif mutation == 'worker_failed': observation['worker_exit_code'] = -9
    elif mutation == 'worker_exit_bool': observation['worker_exit_code'] = False
    elif mutation == 'installer_network': args[10]['ipv4_blocked'] = False
    elif mutation == 'installer_memory': args[10]['memory_max'] = 'max'
    elif mutation == 'installcheck_namespace': args[11]['child_netns'] = args[11]['host_netns']
    elif mutation == 'worker_namespace': observation['sandbox']['child_netns'] = observation['sandbox']['host_netns']
    elif mutation == 'extra_observation': observation['producer_pass'] = True
    elif mutation == 'relaxed_stage_timeout': observation['sandbox']['properties']['RuntimeMaxUSec'] = '8min'
    elif mutation == 'different_timer': observation['watchdog_unit'] = 'pulse-q2-' + 'b' * 24 + '-watchdog.timer'
    elif mutation == 'different_installer': args[10]['unit'] = 'pulse-q2-' + 'b' * 24 + '-installer.service'
    if mutation != 'prelaunch_whitespace': args[3] = K.encoded(pre)
    if mutation != 'response_whitespace': args[5] = K.encoded(response)
    args[6] = K.encoded(ready); args[7] = observation
    with pytest.raises((K.QualificationCheckError, ValueError, OSError, KeyError)):
        K.verify_diagnostic(*args)



def test_native_git_trust_exception_is_exact_path_not_global(tmp_path, monkeypatch):
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b'synthetic blob', stderr=b'')
    monkeypatch.setattr(K.subprocess, 'run', run)
    assert K.git_blob(tmp_path, 'a' * 40, 'source.py') == b'synthetic blob'
    assert 'safe.directory=' + str(tmp_path) in calls[0]
    assert 'safe.directory=*' not in calls[0]
    assert 'protocol.allow=never' in calls[0]
    assert calls[0][-1] == 'a' * 40 + ':source.py'


def test_native_historical_checker_uses_scoped_independent_git_reader(tmp_path, monkeypatch):
    import types
    captured = {}
    class Loader:
        def exec_module(self, module):
            def inspect(*args):
                captured['args'] = args
                assert module.git_blob is K.git_blob
                return 'synthetic-bound-result'
            module.inspect_bundle = inspect
    monkeypatch.setattr(K.importlib.util, 'spec_from_file_location', lambda *args: types.SimpleNamespace(loader=Loader()))
    monkeypatch.setattr(K.importlib.util, 'module_from_spec', lambda spec: types.SimpleNamespace())
    result = K.check_prepared_bytes(tmp_path / 'bundle', tmp_path / 'source', tmp_path / 'repo')
    assert result == 'synthetic-bound-result'
    assert captured['args'][2:4] == (K.ORIGINAL_SOURCE, K.ORIGINAL_RUN)


def test_native_live_evidence_is_not_hidden_by_protect_home(tmp_path, monkeypatch):
    # Run the real supervisor's early-failure/preservation path with a synthetic
    # context and no systemd service, installation, model import or inference.
    import tempfile
    source = tmp_path / 'repo'; source.mkdir()
    archive = tmp_path / 'invalid.zip'; archive.write_bytes(b'not the selected archive')
    destination = tmp_path / 'runner-home' / 'qualification'; destination.parent.mkdir()
    real_mkdtemp = tempfile.mkdtemp
    observed = {}
    def stage_dir(*, prefix, dir):
        assert dir == '/var/tmp'
        value = real_mkdtemp(prefix=prefix, dir=tmp_path)
        observed['stage'] = Path(value)
        return value
    def snapshot(repo, target, expected):
        target.mkdir()
        assert target.parent / 'evidence' != destination
        assert (target.parent / 'evidence').is_dir()
        observed['live'] = target.parent / 'evidence'
        return []
    monkeypatch.setattr(N.tempfile, 'mkdtemp', stage_dir)
    monkeypatch.setattr(N, 'check_context', lambda *args: {'origin': 'synthetic_failure_test'})
    monkeypatch.setattr(N, 'snapshot_sources', snapshot)
    monkeypatch.setattr(N, 'freeze', lambda path: None)
    monkeypatch.setattr(N, 'remove_watchdog', lambda prefix: None)
    monkeypatch.setattr(N.os, 'chown', lambda *args: None)
    monkeypatch.setattr(N, 'run_service', lambda *args: pytest.fail('No service may run on invalid archive'))
    assert N.qualify(source, archive, destination, 'a' * 40, True) == 1
    report = json.loads((destination / 'qualification.json').read_bytes())
    assert report['status'] == 'failed' and report['error_code'] == 'original_archive_digest'
    assert report['native_runtime_qualified'] is False and report['scored_call_count'] == 0
    assert not observed['stage'].exists()
    assert N.PROPERTIES['ProtectHome'] == 'yes'


def synthetic_qualification_report(status='qualified'):
    return {
        'record_type': 'q2_reference_qualification_v0', 'status': status,
        'native_runtime_qualified': status == 'qualified', 'diagnostic_call_limit': 1,
        'scored_call_count': 0, 'capture_dispatch_authorized': False,
        'production_gate_eligible': False, 'authority_effect': 'none',
        'error_code': None if status == 'qualified' else 'synthetic_failure',
        'context': {'repository': N.REPOSITORY, 'source_commit': 'a' * 40, 'workflow': N.WF,
                    'run_id': '12345', 'run_attempt': 1, 'actor': 'HKati', 'event': 'workflow_dispatch',
                    'runner_image': 'synthetic-not-a-runner', 'python': '3.11.16', 'os': 'ubuntu-24.04',
                    'architecture': 'x86_64', 'kernel': 'synthetic', 'libc': ['glibc', 'synthetic'],
                    'bootstrap_python_sha256': '0' * 64, 'origin': 'owner_dispatched_github_native_diagnostic'},
        'preparation_source_commit': N.PREPARATION_SOURCE, 'preparation_run_id': N.PREPARATION_RUN,
        'artifact_sha256': N.ARCHIVE_SHA, 'phase_start_ns': 1, 'phase_end_ns': 2,
        'evidence': [], 'limitations': [
            'GitHub host and bootstrap CPython/pip remain trusted',
            'one diagnostic does not establish 150-call capture viability',
            'no score, acquisition completeness, release admission or malicious-platform proof']}


@pytest.mark.parametrize('status', ['qualified', 'failed'])
def test_qualification_schema_accepts_only_structural_synthetic_records(status):
    import jsonschema
    schema = json.loads((ROOT / N.SCHEMA).read_bytes())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(synthetic_qualification_report(status))


@pytest.mark.parametrize('key,value', [
    ('record_type', 'release_allow'), ('native_runtime_qualified', False),
    ('diagnostic_call_limit', 2), ('diagnostic_call_limit', True),
    ('scored_call_count', 150), ('scored_call_count', False),
    ('capture_dispatch_authorized', True), ('production_gate_eligible', True),
    ('authority_effect', 'allow'), ('error_code', 'failed'),
    ('preparation_source_commit', 'a' * 40), ('preparation_run_id', '12345'),
    ('artifact_sha256', '0' * 64), ('extra', 'not allowed')])
def test_qualification_schema_rejects_promotions_and_mismatched_states(key, value):
    import jsonschema
    schema = json.loads((ROOT / N.SCHEMA).read_bytes())
    report = synthetic_qualification_report(); report[key] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(report)


if __name__ == '__main__':
    raise SystemExit(pytest.main(['-q','-c',os.devnull,str(Path(__file__).resolve())]))


# Timing correction: deterministic clocks and synthetic services only. The
# production supervisor functions execute unchanged; no systemd/model is run.
@pytest.fixture
def generation_window(tmp_path, monkeypatch):
    import types
    class Clock:
        ns = 100_000_000_000
        def monotonic_ns(self): return self.ns
        def monotonic(self): return self.ns / 1e9
        def advance(self, ns): self.ns += ns
    clock = Clock()
    state = types.SimpleNamespace(clock=clock, events=[], control_delays=[0, 0],
        save_delays={}, response_delay=14_000_000_000, exit_delay=0, send_delay=0,
        force_late_line=False, exit_failure=False, save_failure=None, go_count=0,
        go_ns=None, received_ns=None, timer_deadline=None, timer_active=False,
        closed=False, completed=False, response=b'{"text":"synthetic unscored response"}\n')
    prefix = 'pulse-q2-' + 'a' * 24
    state.prefix = prefix
    state.output = tmp_path / 'timing-evidence'; state.output.mkdir()
    state.phase_deadline = clock.monotonic() + 1200
    real_save = N.save
    def save(path, raw):
        state.events.append(('save', path.name, clock.ns, state.closed, state.go_count))
        clock.advance(state.save_delays.get(path.name, 0))
        if path.name == state.save_failure: raise OSError('synthetic fsync failure')
        real_save(path, raw)
    def control(argv, **kwargs):
        state.events.append(('control', tuple(argv), clock.ns, state.closed, state.go_count))
        if argv[0] == '/usr/bin/systemd-run':
            value = next(a for a in argv if a.startswith('--on-active='))
            seconds = int(value.split('=')[1][:-1])
            state.timer_deadline = clock.ns + seconds * 1_000_000_000
            state.timer_active = True
            clock.advance(state.control_delays[0])
        elif 'is-active' in argv:
            clock.advance(state.control_delays[1])
            N.require(clock.ns < state.timer_deadline, 'synthetic_watchdog_expired')
        elif 'stop' in argv:
            state.timer_active = False
        return subprocess.CompletedProcess(argv, 0, stdout=b'', stderr=b'')
    def advance_bounded(target, deadline, *, allow_late=False):
        if state.timer_active and target >= state.timer_deadline:
            clock.ns = state.timer_deadline
            raise N.NativeQualificationError('synthetic_watchdog_expired')
        if target > int(deadline * 1e9) and not allow_late:
            clock.ns = int(deadline * 1e9)
            raise N.NativeQualificationError('external_deadline_expired')
        clock.ns = target
    class Reader:
        def line(self, deadline):
            if not state.go_count:
                return b'{"record_type":"q2_native_model_ready_v0"}\n'
            state.read_deadline = deadline
            advance_bounded(state.go_ns + state.response_delay, deadline,
                            allow_late=state.force_late_line)
            state.received_ns = clock.ns
            state.events.append(('response', None, clock.ns, state.closed, state.go_count))
            return state.response
    class SyntheticService:
        unit = prefix + '-worker.service'
        reader = Reader()
        observation = synthetic_sandbox()
        runtime_deadline_ns = clock.ns + 180_000_000_000
        deadline = state.phase_deadline
        def send(self, raw):
            assert raw == b'GENERATE diagnostic-0001\n'
            assert state.go_count == 0
            clock.advance(state.send_delay)
            state.go_count += 1; state.go_ns = clock.ns
            state.events.append(('send', raw, clock.ns, state.closed, state.go_count))
            return clock.ns
        def complete(self, *, empty_tail=False, deadline=None):
            assert empty_tail is True
            state.exit_deadline = deadline
            advance_bounded(clock.ns + state.exit_delay, deadline)
            if state.exit_failure: raise N.NativeQualificationError('isolated_service_failed')
            state.completed = True
            return b'', 0
        def close(self):
            state.closed = True
            state.events.append(('close', None, clock.ns, state.closed, state.go_count))
    state.service = SyntheticService()
    monkeypatch.setattr(N, 'time', clock)
    monkeypatch.setattr(N, 'save', save)
    monkeypatch.setattr(N, 'control', control)
    return state


def run_generation_window(state):
    return N.exchange_diagnostic(state.service, state.prefix, state.output, state.phase_deadline)


@pytest.mark.parametrize('delays', [(0, 0), (100_000_000, 100_000_000),
    (1_000_000_000, 1_000_000_000), (2_000_000_000, 2_000_000_000),
    (2_400_000_000, 2_400_000_000)])
def test_generation_window_preserves_fifteen_seconds_after_slow_arming(generation_window, delays):
    state = generation_window; state.control_delays = delays
    state.response_delay = 14_999_999_999
    assert run_generation_window(state) == state.response
    occurrence = json.loads((state.output / 'occurrence.json').read_bytes())
    assert occurrence['generation_start_ns'] == state.go_ns
    assert occurrence['generation_deadline_ns'] - state.go_ns == 15_000_000_000
    assert occurrence['response_received_ns'] == state.go_ns + state.response_delay
    assert state.go_count == 1 and state.closed and state.completed and not state.timer_active


@pytest.mark.parametrize('name', ['worker-sandbox.json', 'generation-intent.json',
    'generation-start.json', 'original-response.json', 'occurrence.json'])
def test_generation_window_slow_fsync_never_consumes_response_time(generation_window, name):
    state = generation_window; state.save_delays[name] = 8_000_000_000
    state.response_delay = 14_900_000_000
    assert run_generation_window(state) == state.response
    assert round(state.read_deadline * 1e9) - state.go_ns == 15_000_000_000
    begin = next(i for i, row in enumerate(state.events) if row[0] == 'send')
    end = next(i for i, row in enumerate(state.events) if row[0] == 'response')
    assert not any(row[0] in ('save', 'control') for row in state.events[begin + 1:end])
    intent = json.loads((state.output / 'generation-intent.json').read_bytes())
    assert intent['state'] == 'permission_recorded_before_GO' and intent['generation_seconds'] == 15
    assert next(row for row in state.events if row[:2] == ('save', 'generation-intent.json'))[4] == 0
    for filename in ('generation-start.json', 'original-response.json', 'occurrence.json'):
        assert next(row for row in state.events if row[:2] == ('save', filename))[3] is True
    start = json.loads((state.output / 'generation-start.json').read_bytes())
    assert start['state'] == 'GO_written_timing_retained_after_worker_stop'


@pytest.mark.parametrize('delays', [(3_000_000_000, 2_000_000_000),
    (3_000_000_000, 3_000_000_000), (5_000_000_000, 0),
    (0, 6_000_000_000), (20_000_000_000, 0)])
def test_generation_window_exhausted_backstop_refuses_before_go(generation_window, delays):
    state = generation_window; state.control_delays = delays
    with pytest.raises(N.NativeQualificationError): run_generation_window(state)
    assert state.go_count == 0 and state.closed and not state.timer_active
    assert not (state.output / 'generation-start.json').exists()
    assert not (state.output / 'occurrence.json').exists()


@pytest.mark.parametrize('cap', ['worker', 'phase'])
@pytest.mark.parametrize('remaining', [0, 14_000_000_000, 15_000_000_000])
def test_generation_window_never_borrows_from_a_stage_or_phase_cap(generation_window, cap, remaining):
    state = generation_window
    if cap == 'worker': state.service.runtime_deadline_ns = state.clock.ns + remaining
    else: state.phase_deadline = (state.clock.ns + remaining) / 1e9
    with pytest.raises(N.NativeQualificationError, match='full_generation_window_unavailable'):
        run_generation_window(state)
    assert state.go_count == 0 and state.closed


def test_generation_window_rechecks_caps_across_command_delivery(generation_window):
    state = generation_window; state.send_delay = 6_000_000_000
    with pytest.raises(N.NativeQualificationError, match='full_generation_window_unavailable'):
        run_generation_window(state)
    assert state.go_count == 1 and state.closed and not state.completed
    start = json.loads((state.output / 'generation-start.json').read_bytes())
    assert start['generation_start_ns'] == state.go_ns
    assert start['generation_deadline_ns'] == state.go_ns + 15_000_000_000
    assert not (state.output / 'occurrence.json').exists()


@pytest.mark.parametrize('offset', [0, 1, 1_000_000_000, 4_000_000_000])
def test_generation_window_has_no_late_response_grace(generation_window, offset):
    state = generation_window; state.response_delay = 15_000_000_000 + offset
    state.force_late_line = True
    if offset:
        with pytest.raises(N.NativeQualificationError, match='late_generation_response'):
            run_generation_window(state)
        assert not (state.output / 'occurrence.json').exists()
    else:
        assert run_generation_window(state) == state.response
        assert (state.output / 'occurrence.json').exists()
    assert (state.output / 'original-response.json').read_bytes() == state.response
    assert state.closed and not state.timer_active and state.go_count == 1


def test_generation_window_no_response_is_a_failure_not_an_original_record(generation_window):
    state = generation_window; state.response_delay = 16_000_000_000
    with pytest.raises(N.NativeQualificationError, match='external_deadline_expired'):
        run_generation_window(state)
    assert state.closed and not state.timer_active
    assert not (state.output / 'original-response.json').exists()
    assert not (state.output / 'occurrence.json').exists()


@pytest.mark.parametrize('delay', [0, 1_000_000_000, 4_000_000_000])
def test_generation_window_timely_response_has_separate_bounded_exit(generation_window, delay):
    state = generation_window; state.response_delay = 14_900_000_000; state.exit_delay = delay
    assert run_generation_window(state) == state.response
    assert state.completed and state.closed
    assert state.exit_deadline <= state.timer_deadline / 1e9
    assert state.read_deadline < state.exit_deadline


@pytest.mark.parametrize('failure', ['exit_code', 'late_exit'])
def test_generation_window_exit_failure_keeps_original_bytes_without_success(generation_window, failure):
    state = generation_window
    if failure == 'exit_code': state.exit_failure = True
    else: state.exit_delay = 8_000_000_000
    with pytest.raises(N.NativeQualificationError): run_generation_window(state)
    assert state.closed and not state.timer_active
    assert (state.output / 'original-response.json').read_bytes() == state.response
    assert not (state.output / 'occurrence.json').exists()


@pytest.mark.parametrize('filename', ['worker-sandbox.json', 'generation-intent.json',
    'generation-start.json', 'original-response.json'])
def test_generation_window_evidence_failure_cannot_leave_worker_running(generation_window, filename):
    state = generation_window; state.save_failure = filename
    with pytest.raises(OSError, match='synthetic fsync failure'): run_generation_window(state)
    assert state.closed and not state.timer_active
    if filename in ('worker-sandbox.json', 'generation-intent.json'): assert state.go_count == 0


def test_generation_window_service_send_is_a_real_complete_nonblocking_pipe_write():
    import types
    import time as real_time
    read_fd, write_fd = os.pipe()
    try:
        with os.fdopen(write_fd, 'wb', buffering=0) as stream:
            service = N.Service.__new__(N.Service)
            service.process = types.SimpleNamespace(stdin=stream, poll=lambda: None)
            before = real_time.monotonic_ns()
            delivered = service.send(b'GENERATE diagnostic-0001\n')
            assert before <= delivered <= real_time.monotonic_ns()
            assert os.get_blocking(write_fd) is False
            assert os.read(read_fd, 512) == b'GENERATE diagnostic-0001\n'
    finally:
        os.close(read_fd)


def test_generation_window_full_real_control_pipe_cannot_block():
    import types
    import time as real_time
    read_fd, write_fd = os.pipe()
    try:
        with os.fdopen(write_fd, 'wb', buffering=0) as stream:
            os.set_blocking(write_fd, False)
            while True:
                try: os.write(write_fd, b'x' * 4096)
                except BlockingIOError: break
            service = N.Service.__new__(N.Service)
            service.process = types.SimpleNamespace(stdin=stream, poll=lambda: None)
            before = real_time.monotonic()
            with pytest.raises(N.NativeQualificationError, match='control_pipe_not_writable'):
                service.send(b'GENERATE diagnostic-0001\n')
            assert real_time.monotonic() - before < 1
    finally:
        os.close(read_fd)


@pytest.mark.parametrize('payload', [b'', b'x' * 513, 'GENERATE diagnostic-0001\n'])
def test_generation_window_control_command_must_fit_atomic_pipe_bound(payload):
    service = N.Service.__new__(N.Service)
    with pytest.raises(N.NativeQualificationError, match='control_command_bound'):
        service.send(payload)


def test_generation_window_partial_control_delivery_cannot_authorize(monkeypatch):
    import types
    service = N.Service.__new__(N.Service)
    service.process = types.SimpleNamespace(stdin=types.SimpleNamespace(fileno=lambda: 123), poll=lambda: None)
    monkeypatch.setattr(N, 'os', types.SimpleNamespace(set_blocking=lambda *a: None,
                                                     write=lambda fd, raw: len(raw) - 1))
    with pytest.raises(N.NativeQualificationError, match='incomplete_control_write'):
        service.send(b'GENERATE diagnostic-0001\n')


@pytest.fixture
def timed_synthetic_qualification(generation_window, tmp_path, monkeypatch):
    """Exercise qualify() itself; all installation/model services are doubles."""
    import tempfile
    state = generation_window
    source = tmp_path / 'synthetic-repo'; source.mkdir()
    archive = tmp_path / 'synthetic.zip'; archive.write_bytes(b'synthetic timing fixture; not runtime bytes')
    destination = tmp_path / 'published-synthetic-evidence'
    real_mkdtemp = tempfile.mkdtemp
    monkeypatch.setattr(N.tempfile, 'mkdtemp', lambda *, prefix, dir: real_mkdtemp(prefix=prefix, dir=tmp_path))
    monkeypatch.setattr(N, 'check_context', lambda *a: {'origin': 'synthetic_timing_fixture', 'run_id': '123'})
    monkeypatch.setattr(N, 'ARCHIVE_SIZE', archive.stat().st_size)
    monkeypatch.setattr(N, 'ARCHIVE_SHA', N.sha(archive.read_bytes()))
    monkeypatch.setattr(N, 'freeze', lambda path: None)
    monkeypatch.setattr(N, 'writable_directory', lambda path: path.mkdir())
    monkeypatch.setattr(N.os, 'chown', lambda *a: None)
    def snapshot(repo, target, expected):
        target.mkdir()
        for path in (N.SELECTION, N.WORKLOAD, N.DIAGNOSTIC):
            item = target / path; item.parent.mkdir(parents=True, exist_ok=True)
            item.write_bytes(b'{"origin":"synthetic_timing_fixture"}\n')
        return []
    monkeypatch.setattr(N, 'snapshot_sources', snapshot)
    def input_check(command, log, deadline):
        stage = Path(command[command.index('--staging') + 1]); (stage / 'bundle').mkdir(parents=True)
        target = Path(command[command.index('--output') + 1])
        target.write_bytes(N.encode({'source_files': [], 'preparation_source_commit': N.PREPARATION_SOURCE}))
        log.write_bytes(b'synthetic input-check double; no runtime checked\n')
    monkeypatch.setattr(N, 'bounded_local', input_check)
    def run_service(prefix, stage, command, work, python, output, deadline):
        if stage == 'installer':
            (work / 'venv').mkdir()
            for name in ('bootstrap.json', 'bootstrap-pip.log', 'pip-report.json', 'pip-install.log'):
                (work / name).write_bytes(b'{}\n')
        elif stage == 'installcheck':
            (work / 'installation.json').write_bytes(N.encode({'inventory': []}))
        elif stage == 'decodecheck':
            (work / 'diagnostic-check.json').write_bytes(N.encode({
                'native_runtime_qualified': True, 'original_decoding_verified': True,
                'single_unscored_diagnostic_verified': True,
                'response_sha256': command[command.index('--expected-response-sha256') + 1],
                'prelaunch_sha256': command[command.index('--expected-prelaunch-sha256') + 1]}))
        else: raise AssertionError('unexpected synthetic stage')
    monkeypatch.setattr(N, 'run_service', run_service)
    def worker_service(*args):
        state.service.runtime_deadline_ns = state.clock.ns + 180_000_000_000
        return state.service
    monkeypatch.setattr(N, 'Service', worker_service)
    def run():
        rc = N.qualify(source, archive, destination, 'a' * 40, True)
        return rc, json.loads((destination / 'qualification.json').read_bytes()), destination
    return state, run


@pytest.mark.parametrize('lag', ['arming', 'pre_go_fsync', 'response_fsync', 'combined'])
def test_generation_window_full_supervisor_keeps_timely_response(timed_synthetic_qualification, lag):
    state, run = timed_synthetic_qualification
    state.response_delay = 14_000_000_000
    if lag in ('arming', 'combined'): state.control_delays = [1_000_000_000, 1_000_000_000]
    if lag in ('pre_go_fsync', 'combined'):
        state.save_delays.update({'worker-sandbox.json': 3_000_000_000, 'generation-start.json': 3_000_000_000})
    if lag in ('response_fsync', 'combined'): state.save_delays['original-response.json'] = 3_000_000_000
    rc, report, destination = run()
    assert rc == 0 and report['status'] == 'qualified'
    assert report['context']['origin'] == 'synthetic_timing_fixture'
    assert report['scored_call_count'] == 0 and report['authority_effect'] == 'none'
    occurrence = json.loads((destination / 'occurrence.json').read_bytes())
    assert occurrence['generation_start_ns'] == state.go_ns
    assert occurrence['generation_deadline_ns'] == state.go_ns + 15_000_000_000
    assert state.go_count == 1 and state.closed
    assert (destination / 'original-response.json').read_bytes() == state.response


def test_generation_window_post_write_scheduling_cannot_extend_deadline(monkeypatch):
    import types
    clock = types.SimpleNamespace(ns=100_000_000_000)
    service = N.Service.__new__(N.Service)
    service.process = types.SimpleNamespace(stdin=types.SimpleNamespace(fileno=lambda: 123), poll=lambda: None)
    def write(fd, raw):
        # Authorization has already entered the pipe at this point. Simulate
        # the sender being descheduled before the syscall returns to Python.
        clock.ns += 4_000_000_000
        return len(raw)
    monkeypatch.setattr(N, 'time', types.SimpleNamespace(monotonic_ns=lambda: clock.ns))
    monkeypatch.setattr(N, 'os', types.SimpleNamespace(set_blocking=lambda *a: None, write=write))
    start = service.send(b'GENERATE diagnostic-0001\n')
    assert start == 100_000_000_000
    assert start + N.GENERATION_NS == 115_000_000_000
    assert start + N.GENERATION_NS - clock.ns == 11_000_000_000


# Timeout cleanup regressions. No native runtime or model is executed: the real
# supervisor is stopped during a synthetic source snapshot, before acquisition.
def _qualification_timeout_spec():
    import re
    workflow = yaml.safe_load(_q2_workflow_text())
    step = next(s for s in workflow['jobs']['prepare']['steps'] if s.get('id') == 'qualify')
    matches = re.findall(
        r'(/usr/bin/timeout)\s+--signal=(\w+)\s+--kill-after=(\d+)s\s+(\d+)s', step['run'])
    assert len(matches) == 1, 'one explicit externally bounded qualification command is required'
    binary, termination_signal, grace, execution = matches[0]
    return binary, termination_signal, int(grace), int(execution)


def test_timeout_cleanup_keeps_execution_cap_and_separate_finite_grace():
    binary, termination_signal, grace, execution = _qualification_timeout_spec()
    assert (binary, termination_signal, execution, grace) == ('/usr/bin/timeout', 'TERM', 1200, 180)
    assert execution + grace == 1380
    workflow = yaml.safe_load(_q2_workflow_text())
    job = workflow['jobs']['prepare']
    assert job['timeout-minutes'] == 40
    # Archive acquisition has its own 180s cap; do not consume the upload margin.
    assert 180 + execution + grace < job['timeout-minutes'] * 60
    native = next(s for s in job['steps'] if s.get('id') == 'qualify')
    assert native.get('continue-on-error', False) is False
    assert '--preserve-status' not in native['run'] and '|| true' not in native['run']
    upload = next(s for s in job['steps'] if
        s.get('uses', '').startswith('actions/upload-artifact@') and
        "inputs.mode == 'qualify-runtime'" in s.get('if', ''))
    assert upload['if'] == "always() && inputs.mode == 'qualify-runtime' && steps.qualify.outcome != 'skipped'"
    assert upload['with']['path'] == '${{ runner.temp }}/q2-native-qualification'
    assert upload['with']['if-no-files-found'] == 'error'
    assert upload['with']['overwrite'] is False


@pytest.mark.parametrize('control_times_out', [False, True])
def test_timeout_cleanup_grace_covers_real_cleanup_call_budgets(monkeypatch, control_times_out):
    """Account for actual production close/removal calls, using virtual waits."""
    import types
    calls = []; waits = []; killed = []
    default = N.control.__defaults__[0]
    assert default == 15
    def control(command, timeout=default, *, check=True):
        calls.append((command, timeout, check))
        if control_times_out:
            raise subprocess.TimeoutExpired(command, timeout)
        return subprocess.CompletedProcess(command, 0, stdout=b'', stderr=b'')
    def wait(*, timeout):
        waits.append(timeout)
        raise subprocess.TimeoutExpired('synthetic systemd-run client', timeout)
    monkeypatch.setattr(N, 'control', control)
    monkeypatch.setattr(N.os, 'killpg', lambda pid, sig: killed.append((pid, sig)))
    service = N.Service.__new__(N.Service)
    service.unit = 'pulse-q2-' + 'd' * 24 + '-worker.service'
    service.process = types.SimpleNamespace(pid=12345, poll=lambda: None, wait=wait,
                                           stdin=io.BytesIO(), stdout=io.BytesIO())
    service.reader = types.SimpleNamespace(close=lambda: None)
    service.log = io.BytesIO()
    service.close()
    # exchange_diagnostic's finally and qualify's finally both remove the timer.
    prefix = 'pulse-q2-' + 'd' * 24
    N.remove_watchdog(prefix)
    N.remove_watchdog(prefix)
    assert [x[1] for x in calls] == [10, 10, 15, 15] and waits == [5]
    assert all(x[2] is False for x in calls)
    assert [x[0][1] for x in calls] == ['kill', 'stop', 'stop', 'stop']
    assert killed == [(12345, N.signal.SIGKILL)]
    assert service.log.closed and service.process.stdin.closed and service.process.stdout.closed
    control_budget = sum(x[1] for x in calls) + sum(waits)
    assert control_budget == 55
    _, _, grace, _ = _qualification_timeout_spec()
    assert grace - control_budget >= 120, 'reserve at least 120s for evidence I/O and publication'


def _run_timeout_cleanup_probe(command, *, env=None, bound=20):
    """Run only harmless test children; reap the complete test group on failure."""
    import signal
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=env, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=bound)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate(timeout=5)
        pytest.fail('harmless timeout-cleanup regression exceeded its independent test bound')
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
    return subprocess.CompletedProcess(command, process.returncode, stdout=stdout, stderr=stderr)


def test_timeout_cleanup_real_supervisor_publishes_failure_after_slow_cleanup(tmp_path):
    """Real GNU timeout, SIGTERM handler, qualify finally, fsync and publication.

    Only the execution duration is accelerated to 2s. The configured cleanup
    grace is used unchanged; a 6s control double exceeds the former 5s grace.
    The real model, installer, systemd and archive verifier are never started.
    """
    binary, termination_signal, grace, execution = _qualification_timeout_spec()
    assert execution == 1200 and termination_signal == 'TERM'
    child = tmp_path / 'synthetic-timeout-cleanup.py'
    child.write_text(r'''
import importlib.util, os, pathlib, subprocess, sys, tempfile, time
module_path, case = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('synthetic_timeout_supervisor', module_path)
n = importlib.util.module_from_spec(spec); spec.loader.exec_module(n)
repo = case / 'source'; repo.mkdir()
archive = case / 'not-a-runtime.zip'; archive.write_bytes(b'synthetic; never consumed')
destination = case / 'artifact'
real_mkdtemp = tempfile.mkdtemp
n.tempfile.mkdtemp = lambda *, prefix, dir: real_mkdtemp(prefix=prefix, dir=case)
n.check_context = lambda *a: {'origin': 'synthetic_timeout_cleanup', 'run_id': '1'}
n.os.chown = lambda *a: None

def snapshot(*args):
    target = args[1]
    n.save(target.parent / 'evidence' / 'partial-source.log', b'synthetic original evidence\n')
    (case / 'snapshot-entered').write_bytes(b'no model or acquisition started\n')
    time.sleep(60)
    raise AssertionError('the external timeout did not stop the synthetic snapshot')

def control(command, timeout=15, *, check=True):
    assert command[0:2] == ['/usr/bin/systemctl', 'stop']
    assert command[-2].endswith('-watchdog.timer')
    (case / 'cleanup-entered').write_bytes(b'synthetic slow watchdog stop\n')
    time.sleep(6)
    (case / 'cleanup-finished').write_bytes(b'cleanup completed\n')
    return subprocess.CompletedProcess(command, 0, stdout=b'', stderr=b'')

def forbidden(*args, **kwargs):
    raise AssertionError('native operations are forbidden in this offline regression')

n.snapshot_sources = snapshot
n.control = control
n.bounded_local = forbidden
n.run_service = forbidden
n.Service = forbidden
raise SystemExit(n.main(['qualify-runtime', '--repo-root', str(repo), '--archive', str(archive),
    '--output-dir', str(destination), '--expected-source-sha', 'a' * 40,
    '--confirm-one-unscored-diagnostic']))
''', encoding='utf-8')
    result = _run_timeout_cleanup_probe(
        [binary, '--signal=TERM', f'--kill-after={grace}s', '2s', sys.executable, '-I', '-B',
         str(child), str(TOOLS / 'qualify_q2_reference_runtime_v0.py'), str(tmp_path)],
        env={'PATH': os.defpath, 'LANG': 'C.UTF-8'})
    assert (tmp_path / 'snapshot-entered').is_file(), result.stderr.decode()
    assert (tmp_path / 'cleanup-entered').is_file(), result.stderr.decode()
    assert result.returncode == 124, (result.returncode, result.stdout, result.stderr)
    assert (tmp_path / 'cleanup-finished').is_file()
    destination = tmp_path / 'artifact'
    report = json.loads((destination / 'qualification.json').read_bytes())
    assert report['status'] == 'failed' and report['error_code'] == 'external_phase_timeout'
    assert report['native_runtime_qualified'] is False
    assert report['capture_dispatch_authorized'] is False and report['production_gate_eligible'] is False
    assert report['scored_call_count'] == 0 and report['authority_effect'] == 'none'
    assert report['context']['origin'] == 'synthetic_timeout_cleanup'
    original = (destination / 'partial-source.log').read_bytes()
    assert original == b'synthetic original evidence\n'
    assert report['evidence'] == [{'path': 'partial-source.log', 'size': len(original),
                                  'sha256': hashlib.sha256(original).hexdigest()}]
    assert not (destination / 'original-response.json').exists()
    assert not list(tmp_path.glob('pulse-q2-*'))


@pytest.mark.parametrize('exit_code', [0, 7])
def test_timeout_cleanup_unused_grace_does_not_delay_normal_exit(exit_code):
    import time
    binary, termination_signal, grace, execution = _qualification_timeout_spec()
    start = time.monotonic()
    result = _run_timeout_cleanup_probe(
        [binary, f'--signal={termination_signal}', f'--kill-after={grace}s', f'{execution}s',
         sys.executable, '-I', '-B', '-c', f'raise SystemExit({exit_code})'], bound=10)
    assert result.returncode == exit_code
    assert time.monotonic() - start < 10


def test_timeout_cleanup_sigkill_backstop_remains_effective_for_a_stuck_child(tmp_path):
    """Accelerate both durations; exercise real GNU SIGKILL without a 23min test."""
    binary, termination_signal, grace, execution = _qualification_timeout_spec()
    assert (termination_signal, grace, execution) == ('TERM', 180, 1200)
    ready = tmp_path / 'ignoring-term'
    result = _run_timeout_cleanup_probe(
        [binary, '--signal=TERM', '--kill-after=0.2s', '2s', sys.executable, '-I', '-B', '-c',
         'import pathlib,signal,sys,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
         'pathlib.Path(sys.argv[1]).write_text("synthetic stuck child"); time.sleep(60)', str(ready)], bound=10)
    assert ready.is_file()
    # GNU timeout may itself receive the group SIGKILL: Popen then reports -9.
    assert result.returncode in (-9, 137)
