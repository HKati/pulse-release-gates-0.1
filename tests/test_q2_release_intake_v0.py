"""Offline private-IO probes and explicitly synthetic, independently authored fixtures."""
from __future__ import annotations

import copy
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import io as bytesio
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time
import urllib.error
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "PULSE_safe_pack_v0/tools"
sys.path.insert(0, str(TOOLS))
import q2_intake_io_v0 as IO
import load_q2_release_intake_v0 as LOAD
import evaluate_q2_archived_capture_v0 as PRODUCER
import check_q2_release_intake_v0 as ADMISSION


def zipped(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, value in sorted(members.items()):
            raw, mode = value
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, raw)


def snapshot(path):
    return {"archive_size_bytes": path.stat().st_size,
            "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def metadata_request(source="a" * 40):
    p = LOAD.load_profile(ROOT)
    return {"record_type": "q2_release_intake_request_v0", "request_id": "synthetic-request-only",
            "evaluation_identity": {"repository": "HKati/pulse-release-gates-0.1", "source_commit": source,
                                    "workflow": ".github/workflows/pulse_ci.yml", "event": "workflow_dispatch",
                                    "ref": "refs/heads/main"},
            "selection": copy.deepcopy(p["selection"]), "capture_expectation": copy.deepcopy(p["capture_expectation"]),
            "release_subject": {"repository": "HKati/pulse-release-gates-0.1", "artifact_id": 80000000002,
                                "archive_size_bytes": 123, "archive_sha256": "c" * 64,
                                "capsule_manifest_sha256": "d" * 64, "subject_id": p["subject_id"],
                                "definition_sha256": p["definition_sha256"], "layout_profile": p["layout_profile"]},
            **{k: p[k] for k in ("comparison_profile", "reduction_profile", "native_verification_mode")}}


def synthetic_case(folder, positive=False, runtime_file_count=2):
    """No producer is used to author the expected summary or the native-like records.

    Synthetic bytes exercise IO and relations, including an optional 18,485-file
    cardinality probe. They never represent the historical installation or
    authorize a production profile.
    """
    folder.mkdir(parents=True)
    profile = copy.deepcopy(LOAD.load_profile(ROOT))
    profile["record_status"] = "synthetic_fixture"
    profile["capture_expectation"].update(run_id="80000000001", source_commit="a" * 40)
    schema = json.loads((ROOT / IO.CAPSULE_SCHEMA).read_text())
    configuration = {k: schema["properties"]["configuration"]["properties"][k]["const"]
                     for k in ("effective_generation", "runtime")}
    platform_values = {k: v["const"] for k, v in
                       schema["properties"]["platform_scope"]["properties"]["requirements"]["properties"].items()
                       if "const" in v}
    runtime_data = {"bin/python": b"SYNTHETIC_INTERPRETER_NEVER_EXECUTE\n",
                    "lib/python3.11/site-packages/synthetic.py": b"raise RuntimeError('NEVER_EXECUTE_PAYLOAD')\n"}
    assert 2 <= runtime_file_count <= 18485
    runtime_data.update({f"lib/synthetic_runtime_file_{i:05d}.dat": f"SYNTHETIC_ONLY_{i}\n".encode()
                         for i in range(runtime_file_count - 2)})
    platform_values["bootstrap_python_sha256"] = IO.digest(runtime_data["bin/python"])
    context = {**platform_values, "repository": "HKati/pulse-release-gates-0.1", "source_commit": "a" * 40,
               "run_id": "80000000001", "run_attempt": 1, "event": "workflow_dispatch", "actor": "HKati"}
    source_rows = []
    members = {}
    for path in profile["source_components"]:
        data = (ROOT / path).read_bytes()
        members["source/" + path] = (data, stat.S_IFREG | 0o600)
        source_rows.append({"path": path, "sha256": IO.digest(data), "size": len(data)})
    profile["archived_source_files"] = sorted(source_rows, key=lambda r: r["path"])
    inventory = [{"path": k, "mode": 0o755 if k == "bin/python" else 0o644,
                  "size": len(v), "sha256": IO.digest(v)} for k, v in sorted(runtime_data.items())]
    inventory.append({"path": "lib64", "symlink": "lib"})
    profile["runtime_regular_files"] = len(runtime_data)
    installation = {"inventory": inventory, "authority_effect": "none", "production_gate_eligible": False}
    installation_raw = IO.encode(installation)
    pre = {"context": context, "source_files": profile["archived_source_files"],
           "selection_sha256": profile["selection"]["sha256"], "planned_calls": 150,
           "installation_sha256": IO.digest(installation_raw), "environment_inventory_sha256": IO.digest(IO.encode(inventory)),
           "authority_effect": "none", "production_gate_eligible": False}
    pre_raw = IO.encode(pre)
    ready = copy.deepcopy(configuration)
    ready_raw = IO.encode(ready)
    model_files = {}
    selection = json.loads((ROOT / IO.SELECTION_PATH).read_text())
    for n in selection["evaluation_subject"]["selected_snapshot_files"]:
        model_files["model/" + n] = ("SYNTHETIC_MODEL_DATA:" + n + "\n").encode()
    subject = {**copy.deepcopy(configuration), "platform": context,
               "definition_sha256": profile["definition_sha256"],
               "prelaunch_sha256": IO.digest(pre_raw), "ready_sha256": IO.digest(ready_raw),
               "installation_sha256": IO.digest(installation_raw),
               "environment_inventory_sha256": IO.digest(IO.encode(inventory)),
               "worker_sha256": IO.digest((ROOT / IO.WORKER).read_bytes()),
               "model_files": [{"path": k, "size": len(v), "sha256": IO.digest(v)} for k, v in sorted(model_files.items())],
               "authority_effect": "none", "production_gate_eligible": False}
    subject_raw = IO.encode(subject)
    profile["capture_expectation"].update(subject_sha256=IO.digest(subject_raw), subject_size_bytes=len(subject_raw))
    groups = {"schema_version": "q2_consistency_input_v0", "record_status": "synthetic_fixture",
              "extraction_profile": "typed_final_answer_or_refusal_v0",
              "grouping": {"method_id": "synthetic-fixed", "method_version": "v0", "seed": 0,
                           "sampling_parameters": {"repeats": 3}}, "groups": []}
    for i in range(50):
        eligible = positive or i < 49
        groups["groups"].append({"group_id": f"group-{i:03}", "responses": [
            {"response_id": f"response-{i:03}-{j}", "kind": "answer", "answer": "PRIVATE_SYNTHETIC_RESPONSE"}
            if eligible else {"response_id": f"response-{i:03}-{j}", "kind": "unknown"} for j in range(3)]})
    groups_raw = IO.encode(groups)
    manifest = {"manifest_version": "1.0.0", "dataset_id": "synthetic-Q2-only",
                "time_range": {"from": "2026-01-01", "to": "2026-01-01"},
                "source": {"kind": "other", "uri": "urn:pulse:synthetic:q2"},
                "sampling": {"strategy": "full", "n": 50, "seed": 0},
                "hashes": {"input_sha256": IO.digest(groups_raw)}, "pii_handling": {"scrubbed": True}}
    manifest_raw = IO.encode(manifest)
    n = 50 if positive else 49
    with localcontext() as ctx:
        ctx.prec = 60
        z = Decimal("1.959963984540054")
        lower = Decimal(n) / (Decimal(n) + z * z)  # all eligible groups agree
    binding_files = {"groups": groups_raw, "dataset_manifest": manifest_raw,
                     "metric_spec": (ROOT / "metrics/specs/q2_consistency_v0.yml").read_bytes(),
                     "input_schema": (ROOT / "schemas/metrics/q2_consistency_input_v0.schema.json").read_bytes(),
                     "manifest_schema": (ROOT / "schemas/dataset_manifest.schema.json").read_bytes(),
                     "summary_schema": (ROOT / "schemas/metrics/q2_consistency_summary_v0.schema.json").read_bytes()}
    counts = {"groups_total": 50, "groups_eligible": n, "consistent": n, "inconsistent": 0,
              "unknown": 50-n, "responses_total": 150, "responses_eligible": n*3}
    summary = {"schema_version": "q2_consistency_summary_v0", "spec_id": "q2_consistency_v0", "spec_version": "0.1.0",
               "record_status": "synthetic_fixture", "method": {"kind": "deterministic_reference_reduction",
               "extraction_profile": "typed_final_answer_or_refusal_v0", "normalization_order": ["trim_whitespace", "casefold", "normalize_unicode_nfkc"],
               "comparator": "exact_match", "unicode_version": "14.0.0", "grouping_authentication": "not_established", "inference_executed": False},
               "bindings": {k: {"sha256": IO.digest(v), "size_bytes": len(v)} for k, v in binding_files.items()},
               "counts": counts, "groups": [{"group_id": f"group-{i:03}", "label": "CONSISTENT" if i<n else "UNKNOWN",
               "responses_total": 3, "responses_eligible": 3 if i<n else 0} for i in range(50)],
               "consistency_rate": 1.0, "wilson_lower_bound": float(lower), "alpha": 0.05, "threshold": 0.9,
               "min_n_eligible_groups": 50, "insufficient_evidence": not positive, "pass": positive,
               "authority_effect": "none", "production_gate_eligible": False}
    summary_raw = IO.encode(summary)
    transcript_raw = IO.encode({"record_status": "synthetic_fixture", "no_inference_performed": True})
    binding = {"prelaunch_sha256": IO.digest(pre_raw), "subject_sha256": IO.digest(subject_raw),
               "run_id": context["run_id"], "run_attempt": 1, "source_commit": "a" * 40}
    links = {"binding": binding, "groups_sha256": IO.digest(groups_raw), "manifest_sha256": IO.digest(manifest_raw),
             "transcript_sha256": IO.digest(transcript_raw), "authority_effect": "none", "production_gate_eligible": False}
    objects = {"capture-prelaunch.json": pre_raw, "capture-subject.json": subject_raw,
               "installation.json": installation_raw, "capture-model-ready.json": ready_raw,
               "groups.json": groups_raw, "dataset-manifest.json": manifest_raw, "summary.json": summary_raw,
               "transcript.json": transcript_raw, "handoff.json": IO.encode(links),
               "capture-check.json": IO.encode({**links, "verified_calls": 150, "complete_original_capture_verified": True,
                                                 "decoding_and_extraction_verified": True}),
               "summary-check.json": IO.encode({"ok": True, "recomputed_pass": positive,
                                                 "authority_effect": "none", "production_gate_eligible": False}),
               "reduction.json": IO.encode({"builder_exit_code": 0 if positive else 1, "checker_exit_code": 0,
                   "metric_pass": positive, "groups_sha256": IO.digest(groups_raw), "manifest_sha256": IO.digest(manifest_raw),
                   "summary_sha256": IO.digest(summary_raw), "authority_effect": "none", "production_gate_eligible": False})}
    members.update({k: (v, stat.S_IFREG | 0o600) for k, v in objects.items()})
    report = {"context": context, "record_status": "synthetic_fixture", "no_inference_performed": True,
              "evidence": [{"path": k, "size": len(v[0]), "sha256": IO.digest(v[0])} for k, v in sorted(members.items())],
              "metric_pass": positive, "status": "captured_metric_pass" if positive else "captured_metric_fail",
              "planned_calls": 150, "received_complete_slots": 150, "complete_original_capture_verified": True,
              "authority_effect": "none", "production_gate_eligible": False}
    objects["capture.json"] = IO.encode(report)
    members["capture.json"] = (objects["capture.json"], stat.S_IFREG | 0o600)
    profile["capture_file_bindings"] = {k: {"sha256": IO.digest(v), "size_bytes": len(v)} for k, v in objects.items()}
    profile["capture_members"] = len(members)
    profile["capture_expanded_bytes"] = sum(len(v[0]) for v in members.values())
    zipped(folder / "capture.zip", members)
    profile["capture_expectation"].update(snapshot(folder / "capture.zip"))
    capsule_manifest = {"record_type": "q2_release_subject_capsule_v0", "subject_id": profile["subject_id"],
                       "definition_sha256": profile["definition_sha256"], "capture_subject_sha256": IO.digest(subject_raw),
                       "layout_profile": profile["layout_profile"], "configuration": configuration,
                       "launch": profile["launch"], "platform_scope": {"requirements": platform_values,
                                                                       "release_host_verification": "not_observed"}}
    capsule = {"capsule.json": (IO.encode(capsule_manifest), stat.S_IFREG | 0o600),
               **{k: v for k, v in members.items() if k.startswith("source/")},
               **{k: (v, stat.S_IFREG | profile["model_capsule_mode"]) for k, v in model_files.items()},
               **{"runtime/"+r["path"]: (runtime_data[r["path"]], stat.S_IFREG | r["mode"])
                  for r in inventory if "symlink" not in r},
               "runtime/lib64": (b"lib", stat.S_IFLNK | 0o777)}
    zipped(folder / "capsule.zip", capsule)
    request = metadata_request()
    request["capture_expectation"] = copy.deepcopy(profile["capture_expectation"])
    request["release_subject"].update(snapshot(folder / "capsule.zip"), capsule_manifest_sha256=IO.digest(capsule["capsule.json"][0]))
    return {"folder": folder, "profile": profile, "request": request, "members": members,
            "capsule": capsule, "summary": summary, "raw": objects, "subject": subject}


def run_case(case, consumer):
    result = LOAD.empty_result(case["profile"])
    result["checks"]["request"] = True
    function = PRODUCER.evaluate_inputs if consumer == "producer" else ADMISSION.check_bound_inputs
    return function(ROOT, case["folder"], case["request"], case["profile"], result, IO.Deadline(60))


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":1e999}', b'\xef\xbb\xbf{}',
                                  b'{"x":"\\ud800"}', b'[]', b'{"x":'+b'['*60+b'0'+b']'*60+b'}', b'\xff'])
def test_strict_json_rejects_ambiguity(raw):
    with pytest.raises(IO.IntakeError):
        IO.strict_json(raw)


@pytest.mark.parametrize("name", ["../escape", "/escape", "a/../b", "a//b", "a/./b", "a\\b", "C:/x", "a/", ".", "a\x00b", "é"])
def test_archive_member_names_are_unambiguous(name):
    with pytest.raises(IO.IntakeError):
        IO.safe_member(name)


@pytest.mark.parametrize("mode", [stat.S_IFLNK|0o777, stat.S_IFIFO|0o600, stat.S_IFCHR|0o600, stat.S_IFREG|0o4755])
def test_capture_rejects_nonregular_or_privileged_members(tmp_path, mode):
    path=tmp_path/'bad.zip';zipped(path, {'entry':(b'lib',mode)})
    with pytest.raises(IO.IntakeError):
        with IO.Archive(path,maximum_bytes=10000,max_members=4,member_bytes=100,expanded_bytes=200,deadline=IO.Deadline(3)):
            pass


@pytest.mark.parametrize("attack", ["duplicate","member_limit","expanded_limit","parent_alias"])
def test_archive_bounds(tmp_path, attack):
    path=tmp_path/'bad.zip'
    if attack=='duplicate':
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('same',b'1')
            with pytest.warns(UserWarning): z.writestr('same',b'2')
    else:
        zipped(path, {'entry':(b'x'*50,stat.S_IFREG|0o600), 'entry/child' if attack=='parent_alias' else 'two':(b'y'*50,stat.S_IFREG|0o600)})
    with pytest.raises(IO.IntakeError):
        with IO.Archive(path,maximum_bytes=10000,max_members=1 if attack=='member_limit' else 4,
                        member_bytes=100,expanded_bytes=70 if attack=='expanded_limit' else 200,deadline=IO.Deadline(3)):
            pass


def test_regular_snapshot_rejects_symlink_parent_and_fifo(tmp_path):
    good=tmp_path/'good';good.mkdir();(good/'input').write_bytes(b'x')
    (tmp_path/'link').symlink_to(good,target_is_directory=True)
    with pytest.raises(IO.IntakeError): IO.read_file(tmp_path/'link/input',100)
    os.mkfifo(tmp_path/'fifo')
    with pytest.raises(IO.IntakeError): IO.read_file(tmp_path/'fifo',100)
    (tmp_path/'direct').symlink_to(good/'input')
    with pytest.raises(IO.IntakeError): IO.read_file(tmp_path/'direct',100)


@pytest.mark.parametrize("failure", [False,True])
def test_private_workspace_cleanup_success_and_error(tmp_path, failure):
    repo=tmp_path/'repo';repo.mkdir()
    state=None
    try:
        with IO.private_workspace(repo,tmp_path) as state:
            assert stat.S_IMODE(state['path'].stat().st_mode)==0o700
            (state['path']/'private').write_text('PRIVATE_RAW')
            if failure: raise ValueError('PRIVATE_ERROR')
    except ValueError: pass
    assert state['cleanup_verified'] and not state['path'].exists()


def test_runner_timeout_kills_process_group_and_removes_private_tree(tmp_path):
    repo=tmp_path/'repo';repo.mkdir();marker=tmp_path/'late-marker'
    child=f"import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).write_text('orphan')"
    code=f"import os,subprocess,sys,time; from pathlib import Path; p=Path(os.environ['PULSE_Q2_SUPERVISOR_ROOT']); (p/'raw').write_text('PRIVATE_SENTINEL'); subprocess.Popen([sys.executable,'-c',{child!r}]); print('PRIVATE_STDOUT',flush=True); print('PRIVATE_STDERR',file=sys.stderr,flush=True); time.sleep(5)"
    env={**os.environ,'RUNNER_TEMP':str(tmp_path),'PULSE_Q2_TRANSPORT_TOKEN':'PRIVATE_TOKEN'}
    assert IO.run_q2_command([sys.executable,'-c',code],repo=repo,environment=env,timeout=.1)==2
    time.sleep(1.1)
    assert not marker.exists() and not list(tmp_path.glob('pulse-q2-intake-*'))


def test_clean_environment_removes_entire_q2_namespace():
    value=IO.clean_environment({'PULSE_Q2_TRANSPORT_TOKEN':'SECRET','PULSE_Q2_INTAKE_REQUEST':'RAW',
                                'PULSE_Q2_FUTURE_PRIVATE':'SECRET','SAFE':'yes'})
    assert value=={'SAFE':'yes'}
    assert not any(k.startswith('PULSE_Q2_') for k in IO.replay_environment(Path('/tmp/private')))


def test_matching_request_and_digest_do_not_authorize_transport():
    req=IO.encode(metadata_request()).decode()
    env={LOAD.REQUEST_ENV:req,LOAD.DIGEST_ENV:IO.digest(req.encode()),'GITHUB_SHA':'a'*40}
    with pytest.raises(IO.IntakeError,match='q2_context_rejected'):
        LOAD.trusted_invocation(ROOT,env)


@pytest.mark.parametrize("mutation", ["future_run","extra","wrong_definition","digest_role","wrong_capture","raw_path","wrong_source"])
def test_request_rejects_unbound_or_additional_fields(mutation):
    r=metadata_request()
    if mutation=='future_run':r['evaluation_identity']['run_id']='999'
    if mutation=='extra':r['token']='PRIVATE_TOKEN'
    if mutation=='wrong_definition':r['release_subject']['definition_sha256']='0'*64
    if mutation=='digest_role':r['release_subject']['archive_sha256']=r['release_subject']['definition_sha256']
    if mutation=='wrong_capture':r['capture_expectation']['run_id']='999'
    if mutation=='raw_path':r['capture_path']='/private/capture.zip'
    if mutation=='wrong_source':r['evaluation_identity']['source_commit']='b'*40
    raw=IO.encode(r).decode()
    with pytest.raises(IO.IntakeError):LOAD.metadata_request(ROOT,raw,IO.digest(raw.encode()),'a'*40)


def test_missing_input_public_record_is_closed_and_has_no_secret(monkeypatch):
    monkeypatch.setenv(LOAD.TOKEN_ENV,'PRIVATE_TOKEN_VALUE')
    record=LOAD.consume(ROOT,consumer='producer',environment={LOAD.TOKEN_ENV:'PRIVATE_TOKEN_VALUE'})
    IO.validate(record,IO.read_file(ROOT/IO.RESULT_SCHEMA,128*1024))
    assert record['input_valid'] is False and record['metric_pass'] is None and record['process_exit']==2
    assert record['cleanup']=='not_created' and record['diagnostics']==['q2_request_missing']
    assert 'PRIVATE_TOKEN' not in IO.encode(record).decode() and LOAD.TOKEN_ENV not in os.environ


def test_regular_snapshot_detects_mutation_even_when_bytes_are_restored(tmp_path,monkeypatch):
    path=tmp_path/'input';path.write_bytes(b'original')
    read=IO.os.read;once=[]
    def changing(fd,amount):
        data=read(fd,amount)
        if data and not once:
            once.append(True);path.write_bytes(b'mutation');path.write_bytes(b'original')
        return data
    monkeypatch.setattr(IO.os,'read',changing)
    with pytest.raises(IO.IntakeError,match='q2_unstable_input'):IO.read_file(path,100)


def test_input_hardlinks_are_rejected(tmp_path):
    path=tmp_path/'input';path.write_bytes(b'input');os.link(path,tmp_path/'alias')
    with pytest.raises(IO.IntakeError,match='q2_file_rejected'):IO.read_file(path,100)


def test_failed_cleanup_is_never_reported_as_verified(tmp_path,monkeypatch):
    repo=tmp_path/'repo';repo.mkdir();real=IO.shutil.rmtree;owned=[]
    def fail(path):owned.append(path);raise OSError('PRIVATE_PATH_INFORMATION')
    monkeypatch.setattr(IO.shutil,'rmtree',fail)
    with pytest.raises(IO.IntakeError,match='q2_cleanup_failed'):
        with IO.private_workspace(repo,tmp_path) as state:pass
    assert state['cleanup_verified'] is False
    for path in owned:real(path)


@pytest.mark.parametrize('fault',['repository','symlink','world-readable'])
def test_semantic_entry_point_cannot_use_public_or_aliased_directory(tmp_path,fault):
    repo=tmp_path/'repo';repo.mkdir()
    private=tmp_path/'private';private.mkdir(mode=0o700)
    if fault=='repository':private=repo/'artifacts';private.mkdir(mode=0o700)
    elif fault=='symlink':alias=tmp_path/'alias';alias.symlink_to(private,target_is_directory=True);private=alias
    else:private.chmod(0o755)
    with pytest.raises(IO.IntakeError,match='q2_file_rejected'):IO.check_private_directory(repo,private)



@pytest.mark.parametrize('fault',['local-extra','local-name','local-mode','local-size','local-flags','unindexed-prefix'])
def test_local_zip_headers_cannot_hide_unindexed_or_conflicting_payload(tmp_path,fault):
    import struct
    path=tmp_path/'local.zip';zipped(path,{'entry':(b'payload',stat.S_IFREG|0o600)})
    raw=bytearray(path.read_bytes())
    if fault=='local-extra':struct.pack_into('<H',raw,28,1)
    elif fault=='local-name':raw[30]=ord('X')
    elif fault=='local-mode':struct.pack_into('<H',raw,8,99)
    elif fault=='local-size':struct.pack_into('<I',raw,22,100)
    elif fault=='local-flags':struct.pack_into('<H',raw,6,1)
    else:
        # A self-consistent ZIP with an executable-like prefix is still outside
        # the accepted exact-member representation.
        prefix=b'UNINDEXED_PRIVATE_PAYLOAD'
        central=raw.index(b'PK\x01\x02');ending=raw.rindex(b'PK\x05\x06')
        offset=struct.unpack_from('<I',raw,central+42)[0]
        struct.pack_into('<I',raw,central+42,offset+len(prefix))
        struct.pack_into('<I',raw,ending+16,central+len(prefix))
        raw=prefix+raw
    path.write_bytes(raw)
    with pytest.raises(IO.IntakeError,match='q2_archive_rejected'):
        with IO.Archive(path,maximum_bytes=10000,max_members=4,member_bytes=100,
                        expanded_bytes=200,deadline=IO.Deadline(5)):pass


class ReleaseResponse(bytesio.BytesIO):
    """Offline HTTP body; no network or archive payload is executed."""
    def __init__(self, raw, *, length=True, status=200):
        super().__init__(raw)
        self.status = status
        self.headers = {"Content-Length": str(len(raw))} if length else {}


def release_metadata(delivery):
    root = "https://api.github.com/repos/" + delivery["repository"]
    browser = ("https://github.com/" + delivery["repository"] +
               "/releases/download/" + delivery["tag_name"] + "/")
    release = {"id": delivery["release_id"], "tag_name": delivery["tag_name"],
               "draft": False, "immutable": True, "published_at": "2026-11-12T22:49:43Z",
               "assets": [{"id": a["id"], "name": a["name"], "size": a["size_bytes"],
                           "digest": "sha256:" + a["sha256"], "state": "uploaded",
                           "url": root + "/releases/assets/" + str(a["id"]),
                           "browser_download_url": browser + a["name"]}
                          for a in delivery["assets"]]}
    tag = {"ref": "refs/tags/" + delivery["tag_name"],
           "object": {"type": "commit", "sha": delivery["tag_commit"]}}
    return release, tag


def mock_release_opener(monkeypatch, release, tag, bodies=None, *, redirect=None,
                        length=True):
    """Route only fixed API reads; unexpected requests fail the test."""
    seen = []
    bodies = {} if bodies is None else bodies

    class Opener:
        def open(self, request, timeout):
            assert 0 < timeout <= 30
            seen.append(request)
            url = request.full_url
            if url.startswith("https://release-assets.githubusercontent.com/"):
                return ReleaseResponse(next(iter(bodies.values())), length=length)
            assert url.startswith("https://api.github.com/repos/HKati/pulsemech-q3-runtime-inputs/")
            if "/releases/assets/" in url:
                identifier = int(url.rsplit("/", 1)[1])
                if redirect is not None:
                    raise urllib.error.HTTPError(url, 302, "PRIVATE_REDIRECT_ERROR",
                                                 {"Location": redirect}, bytesio.BytesIO())
                return ReleaseResponse(bodies[identifier], length=length)
            if "/git/ref/tags/" in url:
                return ReleaseResponse(IO.encode(tag))
            assert url.endswith("/releases/443495900")
            return ReleaseResponse(IO.encode(release))

    monkeypatch.setattr(IO.urllib.request, "build_opener", lambda *args: Opener())
    return seen


def test_published_delivery_keeps_historical_origin_separate():
    profile = LOAD.load_profile(ROOT)
    delivery = profile["delivery"]
    assert delivery["repository"] == "HKati/pulsemech-q3-runtime-inputs"
    assert delivery["release_id"] == 443495900
    assert delivery["tag_name"] == "q2-admission-inputs-37600313529-v1"
    assert delivery["tag_commit"] == "d4125baa4bbf7b1b4d2d695a24b1c9bb1fa403b5"
    assert len(delivery["assets"]) == 13
    assert sum(a["size_bytes"] for a in delivery["assets"]) == 454375505
    assert len({a["id"] for a in delivery["assets"]}) == 13
    assert len({a["name"] for a in delivery["assets"]}) == 13
    assert profile["capture_expectation"]["artifact_id"] == 11472726606
    assert delivery["capsule_origin"]["artifact_id"] == 11686701538
    assert delivery["capsule_origin"]["run_id"] == "38097352170"
    assert delivery["capsule_origin"]["source_commit"] == "3aa05dd7f8f95f30d75ab38bdb46419e3735c58c"
    assert delivery["assets"][0]["id"] == 741045803
    assert profile["current_inference_count"] == 0 and profile["authority_effect"] == "none"


def test_release_and_tag_metadata_are_both_verified(monkeypatch):
    delivery = LOAD.load_profile(ROOT)["delivery"]
    release, tag = release_metadata(delivery)
    seen = mock_release_opener(monkeypatch, release, tag)
    IO.GitHubReleaseTransport("PRIVATE_RELEASE_TOKEN").verify_release(delivery, IO.Deadline(5))
    assert len(seen) == 2
    assert any("/releases/443495900" in r.full_url for r in seen)
    assert any("/git/ref/tags/q2-admission-inputs-37600313529-v1" in r.full_url for r in seen)
    assert all(r.get_method() == "GET" for r in seen)
    assert all(r.get_header("Authorization") == "Bearer PRIVATE_RELEASE_TOKEN" for r in seen)


@pytest.mark.parametrize("fault", ["release-id", "tag-name", "draft", "mutable", "missing",
    "duplicate", "extra", "asset-id", "asset-name", "asset-size", "asset-digest", "asset-state",
    "tag-commit", "tag-object", "tag-ref"])
def test_release_metadata_substitution_fails_closed(monkeypatch, fault):
    delivery = LOAD.load_profile(ROOT)["delivery"]
    release, tag = release_metadata(delivery)
    if fault == "release-id": release["id"] += 1
    elif fault == "tag-name": release["tag_name"] = "latest"
    elif fault == "draft": release["draft"] = True
    elif fault == "mutable": release["immutable"] = False
    elif fault == "missing": release["assets"].pop()
    elif fault == "duplicate": release["assets"][-1] = copy.deepcopy(release["assets"][0])
    elif fault == "extra": release["assets"].append({**release["assets"][0], "id": 999, "name": "unexpected.zip"})
    elif fault == "asset-id": release["assets"][0]["id"] += 1
    elif fault == "asset-name": release["assets"][0]["name"] = "renamed.zip"
    elif fault == "asset-size": release["assets"][0]["size"] += 1
    elif fault == "asset-digest": release["assets"][0]["digest"] = "sha256:" + "0" * 64
    elif fault == "asset-state": release["assets"][0]["state"] = "starter"
    elif fault == "tag-commit": tag["object"]["sha"] = "0" * 40
    elif fault == "tag-object": tag["object"]["type"] = "tag"
    else: tag["ref"] = "refs/tags/unreviewed"
    seen = mock_release_opener(monkeypatch, release, tag)
    with pytest.raises(IO.IntakeError):
        IO.GitHubReleaseTransport("PRIVATE_RELEASE_TOKEN").verify_release(delivery, IO.Deadline(5))
    assert all("/releases/assets/" not in r.full_url for r in seen)


def test_release_asset_redirect_drops_api_credentials(monkeypatch, tmp_path):
    delivery = LOAD.load_profile(ROOT)["delivery"]
    payload = b"OFFLINE_SYNTHETIC_RELEASE_BYTES"
    asset = {**delivery["assets"][0], "size_bytes": len(payload), "sha256": IO.digest(payload)}
    release, tag = release_metadata(delivery)
    seen = mock_release_opener(monkeypatch, release, tag, {asset["id"]: payload},
                               redirect="https://release-assets.githubusercontent.com/pinned?sig=PRIVATE_SIGNATURE")
    destination = tmp_path / "asset"
    IO.GitHubReleaseTransport("PRIVATE_RELEASE_TOKEN").download_asset(delivery, asset, destination, IO.Deadline(5))
    assert destination.read_bytes() == payload
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert len(seen) == 2
    assert seen[0].get_header("Authorization") == "Bearer PRIVATE_RELEASE_TOKEN"
    assert seen[1].get_header("Authorization") is None and seen[1].get_header("Cookie") is None


@pytest.mark.parametrize("location", ["http://release-assets.githubusercontent.com/payload",
    "https://release-assets.githubusercontent.com.evil.invalid/payload", "https://evil.invalid/payload",
    "https://user:secret@release-assets.githubusercontent.com/payload",
    "https://release-assets.githubusercontent.com:444/payload",
    "https://release-assets.githubusercontent.com/payload#fragment", "file:///private/input"])
def test_release_asset_rejects_unsafe_redirect(monkeypatch, tmp_path, location):
    delivery = LOAD.load_profile(ROOT)["delivery"]
    release, tag = release_metadata(delivery)
    seen = mock_release_opener(monkeypatch, release, tag, redirect=location)
    with pytest.raises(IO.IntakeError, match="q2_transport_rejected"):
        IO.GitHubReleaseTransport("PRIVATE_RELEASE_TOKEN").download_asset(
            delivery, delivery["assets"][0], tmp_path / "asset", IO.Deadline(5))
    assert len(seen) == 1 and not (tmp_path / "asset").exists()


@pytest.mark.parametrize("fault", ["short", "long", "digest"])
def test_release_stream_checks_bytes_even_without_content_length(monkeypatch, tmp_path, fault):
    delivery = LOAD.load_profile(ROOT)["delivery"]
    expected = b"SYNTHETIC_FIXED_PAYLOAD"
    body = expected[:-1] if fault == "short" else expected + b"X" if fault == "long" else b"X" + expected[1:]
    asset = {**delivery["assets"][0], "size_bytes": len(expected), "sha256": IO.digest(expected)}
    release, tag = release_metadata(delivery)
    seen = mock_release_opener(monkeypatch, release, tag, {asset["id"]: body}, length=False)
    with pytest.raises(IO.IntakeError, match="q2_digest_mismatch"):
        IO.GitHubReleaseTransport("PRIVATE_RELEASE_TOKEN").download_asset(delivery, asset, tmp_path / "asset", IO.Deadline(5))
    assert len(seen) == 1


@pytest.mark.parametrize("fault", ["unavailable", "oversized", "redirect"])
def test_release_metadata_failure_has_no_retry_or_alternate_locator(monkeypatch, fault):
    delivery = LOAD.load_profile(ROOT)["delivery"]
    seen = []
    class Opener:
        def open(self, request, timeout):
            seen.append(request)
            assert request.full_url.endswith("/releases/443495900")
            if fault == "oversized":
                return ReleaseResponse(b" " * (2 * 1024 * 1024 + 1))
            status = 302 if fault == "redirect" else 404
            raise urllib.error.HTTPError(request.full_url, status, "PRIVATE_API_ERROR",
                {"Location": "https://attacker.invalid/private"}, bytesio.BytesIO())
    monkeypatch.setattr(IO.urllib.request, "build_opener", lambda *args: Opener())
    with pytest.raises(IO.IntakeError, match="q2_transport_rejected") as failed:
        IO.GitHubReleaseTransport("PRIVATE_RELEASE_TOKEN").verify_release(delivery, IO.Deadline(5))
    assert len(seen) == 1 and "PRIVATE_" not in str(failed.value)


def test_release_storage_cannot_redirect_again(monkeypatch, tmp_path):
    delivery = LOAD.load_profile(ROOT)["delivery"]
    seen = []
    class Opener:
        def open(self, request, timeout):
            seen.append(request)
            raise urllib.error.HTTPError(request.full_url, 302, "PRIVATE_REDIRECT_ERROR",
                {"Location": "https://release-assets.githubusercontent.com/another"}, bytesio.BytesIO())
    monkeypatch.setattr(IO.urllib.request, "build_opener", lambda *args: Opener())
    with pytest.raises(IO.IntakeError, match="q2_transport_rejected"):
        IO.GitHubReleaseTransport("PRIVATE_RELEASE_TOKEN").download_asset(
            delivery, delivery["assets"][0], tmp_path / "asset", IO.Deadline(5))
    assert len(seen) == 2
    assert seen[1].get_header("Authorization") is None
    assert not (tmp_path / "asset").exists()


@pytest.mark.parametrize("fault", ["extra-url", "wrong-repo", "wrong-release", "wrong-tag", "wrong-commit",
    "duplicate-id", "duplicate-name", "bool-id", "zero-size", "bad-digest", "unknown-asset-field",
    "missing-notice", "origin-substitution"])
def test_reviewed_delivery_binding_is_closed(fault):
    profile = copy.deepcopy(LOAD.load_profile(ROOT))
    delivery = profile["delivery"]
    if fault == "extra-url": delivery["url"] = "https://attacker.invalid/payload"
    elif fault == "wrong-repo": delivery["repository"] = "other/repo"
    elif fault == "wrong-release": delivery["release_id"] += 1
    elif fault == "wrong-tag": delivery["tag_name"] = "latest"
    elif fault == "wrong-commit": delivery["tag_commit"] = "0" * 40
    elif fault == "duplicate-id": delivery["assets"][1]["id"] = delivery["assets"][0]["id"]
    elif fault == "duplicate-name": delivery["assets"][1]["name"] = delivery["assets"][0]["name"]
    elif fault == "bool-id": delivery["assets"][0]["id"] = True
    elif fault == "zero-size": delivery["assets"][0]["size_bytes"] = 0
    elif fault == "bad-digest": delivery["assets"][0]["sha256"] = "0" * 63
    elif fault == "unknown-asset-field": delivery["assets"][0]["url"] = "https://attacker.invalid/payload"
    elif fault == "missing-notice": delivery["assets"].pop()
    else: delivery["capsule_origin"]["artifact_id"] += 1
    with pytest.raises(IO.IntakeError):
        IO.validate_release_delivery(profile)


def tiny_release_case():
    """Different synthetic bytes under the reviewed role names; never historical evidence."""
    profile = copy.deepcopy(LOAD.load_profile(ROOT))
    delivery = profile["delivery"]
    body_by_name = {delivery["capture_filename"]: b"SYNTHETIC_CAPTURE_ONLY\n",
                    delivery["notice_filename"]: b"SYNTHETIC_NOTICE_ONLY\n"}
    original_name = delivery["capsule_original"]["filename"]
    parts = []
    offset = 0
    original = b""
    for index in range(1, 11):
        name = original_name + f".{index:03d}"
        raw = f"RAW_BINARY_PART_{index:03d}\n".encode()
        body_by_name[name] = raw
        parts.append({"index": index, "filename": name, "offset_bytes": offset,
                      "size_bytes": len(raw), "sha256": IO.digest(raw)})
        original += raw
        offset += len(raw)
    delivery["capsule_original"].update(size_bytes=len(original), sha256=IO.digest(original))
    origin = delivery["capsule_origin"]
    manifest = {"schema": "q2_subject_capsule_raw_byte_parts_v1",
                "purpose": "Preserve exact original archive bytes in smaller transport files.",
                "original": copy.deepcopy(delivery["capsule_original"]),
                "historical_origin": {"repository": origin["repository"], "actions_run_id": int(origin["run_id"]),
                    "actions_run_attempt": origin["run_attempt"], "actions_artifact_id": origin["artifact_id"]},
                "part_count": 10, "reconstruction": {"method": "raw_binary_concatenation",
                    "order": "Ascending index in the parts array, 001 through 010.",
                    "verify_each_part_before_concatenation": True,
                    "verify_reconstructed_size_and_sha256_against_original": True,
                    "parts_are_individual_zip_archives": False, "original_zip_recompressed": False},
                "parts": parts, "authority_effect": "none"}
    body_by_name[delivery["manifest_filename"]] = IO.encode(manifest)
    for asset in delivery["assets"]:
        raw = body_by_name[asset["name"]]
        asset.update(size_bytes=len(raw), sha256=IO.digest(raw))
    profile["capture_expectation"].update(archive_size_bytes=len(body_by_name[delivery["capture_filename"]]),
        archive_sha256=IO.digest(body_by_name[delivery["capture_filename"]]))
    request = metadata_request()
    request["capture_expectation"] = copy.deepcopy(profile["capture_expectation"])
    request["release_subject"].update(repository=origin["repository"], artifact_id=origin["artifact_id"],
        archive_size_bytes=len(original), archive_sha256=IO.digest(original),
        capsule_manifest_sha256=delivery["capsule_manifest_sha256"])
    return profile, request, manifest, body_by_name, original


def write_tiny_parts(delivery, bodies, private):
    prefix = delivery["capsule_original"]["filename"] + "."
    for name, raw in bodies.items():
        if name.startswith(prefix):
            (private / name).write_bytes(raw)


def test_raw_part_reconstruction_recovers_exact_ordered_bytes(tmp_path, monkeypatch):
    profile, _, manifest, bodies, original = tiny_release_case()
    delivery = profile["delivery"]
    write_tiny_parts(delivery, bodies, tmp_path)
    monkeypatch.setattr(IO.zipfile, "ZipFile", lambda *a, **k: pytest.fail("Raw reconstruction must not parse or run ZIP payloads"))
    destination = tmp_path / "capsule.zip"
    IO.reconstruct_capsule(delivery, manifest, tmp_path, destination, IO.Deadline(5))
    assert destination.read_bytes() == original
    assert IO.digest(destination.read_bytes()) == delivery["capsule_original"]["sha256"]
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600


@pytest.mark.parametrize("fault", ["part-order", "index", "bool-index", "offset", "part-name", "part-digest",
    "part-size", "part-count", "whole-digest", "origin", "extra-field", "recompressed"])
def test_rehashed_manifest_cannot_change_the_reviewed_reconstruction(tmp_path, fault):
    profile, _, manifest, bodies, _ = tiny_release_case()
    delivery = profile["delivery"]
    write_tiny_parts(delivery, bodies, tmp_path)
    if fault == "part-order": manifest["parts"][0], manifest["parts"][1] = manifest["parts"][1], manifest["parts"][0]
    elif fault == "index": manifest["parts"][0]["index"] = 2
    elif fault == "bool-index": manifest["parts"][0]["index"] = True
    elif fault == "offset": manifest["parts"][1]["offset_bytes"] += 1
    elif fault == "part-name": manifest["parts"][0]["filename"] = "../outside"
    elif fault == "part-digest": manifest["parts"][0]["sha256"] = "0" * 64
    elif fault == "part-size": manifest["parts"][0]["size_bytes"] += 1
    elif fault == "part-count": manifest["part_count"] = 9
    elif fault == "whole-digest": manifest["original"]["sha256"] = "0" * 64
    elif fault == "origin": manifest["historical_origin"]["actions_artifact_id"] += 1
    elif fault == "extra-field": manifest["parts"][0]["url"] = "https://attacker.invalid/part"
    else: manifest["reconstruction"]["original_zip_recompressed"] = True
    # Matching the manifest's own new digest is insufficient: its relationships
    # must still match the separately reviewed delivery binding.
    raw = IO.encode(manifest)
    asset = next(a for a in delivery["assets"] if a["name"] == delivery["manifest_filename"])
    asset.update(size_bytes=len(raw), sha256=IO.digest(raw))
    with pytest.raises(IO.IntakeError):
        IO.reconstruct_capsule(delivery, manifest, tmp_path, tmp_path / "capsule.zip", IO.Deadline(5))


@pytest.mark.parametrize("fault", ["corrupt", "short", "long", "swapped", "missing", "symlink", "whole-digest"])
def test_reconstruction_rechecks_local_part_and_whole_archive_bytes(tmp_path, fault):
    profile, _, manifest, bodies, _ = tiny_release_case()
    delivery = profile["delivery"]
    write_tiny_parts(delivery, bodies, tmp_path)
    first = tmp_path / manifest["parts"][0]["filename"]
    second = tmp_path / manifest["parts"][1]["filename"]
    if fault == "corrupt": first.write_bytes(b"X" + first.read_bytes()[1:])
    elif fault == "short": first.write_bytes(first.read_bytes()[:-1])
    elif fault == "long": first.write_bytes(first.read_bytes() + b"X")
    elif fault == "swapped": first_raw = first.read_bytes(); first.write_bytes(second.read_bytes()); second.write_bytes(first_raw)
    elif fault == "missing": first.unlink()
    elif fault == "symlink": first.unlink(); first.symlink_to(second)
    else:
        delivery["capsule_original"]["sha256"] = "0" * 64
        manifest["original"]["sha256"] = "0" * 64
    with pytest.raises(IO.IntakeError):
        IO.reconstruct_capsule(delivery, manifest, tmp_path, tmp_path / "capsule.zip", IO.Deadline(5))


def test_part_mutation_is_rejected_even_if_original_bytes_are_restored(tmp_path, monkeypatch):
    profile, _, manifest, bodies, _ = tiny_release_case()
    delivery = profile["delivery"]
    write_tiny_parts(delivery, bodies, tmp_path)
    first = tmp_path / manifest["parts"][0]["filename"]
    original = first.read_bytes()
    real_read, changed = IO.os.read, []
    def replacing(fd, amount):
        raw = real_read(fd, amount)
        if raw and not changed:
            changed.append(True)
            first.write_bytes(b"X" * len(original))
            first.write_bytes(original)
        return raw
    monkeypatch.setattr(IO.os, "read", replacing)
    with pytest.raises(IO.IntakeError, match="q2_unstable_input"):
        IO.reconstruct_capsule(delivery, manifest, tmp_path, tmp_path / "capsule.zip", IO.Deadline(5))


def test_release_acquire_downloads_all_assets_and_reconstructs_without_inference(monkeypatch, tmp_path):
    profile, request, _, bodies, original = tiny_release_case()
    delivery = profile["delivery"]
    release, tag = release_metadata(delivery)
    by_id = {a["id"]: bodies[a["name"]] for a in delivery["assets"]}
    seen = mock_release_opener(monkeypatch, release, tag, by_id)
    monkeypatch.setattr(IO.zipfile, "ZipFile", lambda *a, **k: pytest.fail("Transport must not import or execute archive members"))
    IO.GitHubReleaseTransport("PRIVATE_RELEASE_TOKEN").acquire(profile, request, tmp_path, IO.Deadline(5))
    assert (tmp_path / "capsule.zip").read_bytes() == original
    assert (tmp_path / "capture.zip").read_bytes() == bodies[delivery["capture_filename"]]
    downloads = [r for r in seen if "/releases/assets/" in r.full_url]
    assert len(downloads) == 13
    assert {int(r.full_url.rsplit("/", 1)[1]) for r in downloads} == set(by_id)
    assert all("/actions/artifacts/" not in r.full_url for r in seen)
    assert request["release_subject"]["artifact_id"] == 11686701538


@pytest.mark.parametrize("fault", ["capsule-origin", "capsule-bytes", "capsule-manifest", "capture-origin"])
def test_release_acquire_rejects_unbound_origin_before_network(monkeypatch, tmp_path, fault):
    profile, request, _, _, _ = tiny_release_case()
    if fault == "capsule-origin": request["release_subject"]["artifact_id"] += 1
    elif fault == "capsule-bytes": request["release_subject"]["archive_sha256"] = "0" * 64
    elif fault == "capsule-manifest": request["release_subject"]["capsule_manifest_sha256"] = "0" * 64
    else: request["capture_expectation"]["artifact_id"] += 1
    class NoNetwork:
        def open(self, *a, **k): pytest.fail("Unbound historical identity reached the network")
    monkeypatch.setattr(IO.urllib.request, "build_opener", lambda *args: NoNetwork())
    with pytest.raises(IO.IntakeError):
        IO.GitHubReleaseTransport("PRIVATE_RELEASE_TOKEN").acquire(profile, request, tmp_path, IO.Deadline(5))
    assert not list(tmp_path.iterdir())


if __name__=='__main__':
    raise SystemExit(pytest.main([__file__,'-q']))
