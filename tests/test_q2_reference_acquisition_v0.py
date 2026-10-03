#!/usr/bin/env python3
"""Offline Q2 preparation protocol tests; all wheel/model payloads are synthetic.

No model download, import, generation, service call or native qualification is
performed here. Synthetic expectations are monkeypatched only in these tests;
the production CLI has no switch accepting synthetic provenance or new models.
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
    assert not (ROOT / 'PULSE_safe_pack_v0/requirements-q2-reference-v0.lock').exists()
    assert not (ROOT / 'PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json').exists()


if __name__ == '__main__':
    raise SystemExit(pytest.main(['-q','-c',os.devnull,str(Path(__file__).resolve())]))
