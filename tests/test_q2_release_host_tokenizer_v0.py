#!/usr/bin/env python3
"""Offline Q2 tokenizer contracts, real filesystem/process and fixture regressions.

No systemd acquisition, model load, genuine tokenizer runtime or inference is
performed. Synthetic kernel/protocol evidence tests validation only. The real
historical reducer/checker, descriptor IO, subprocess EOF and source guards run.
"""
from __future__ import annotations

import copy
import importlib.util
import io as binary_io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import types
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "PULSE_safe_pack_v0/tools"
sys.path.insert(0, str(TOOLS))
import check_q2_release_host_tokenizer_v0 as C
import verify_q2_release_host_tokenizer_v0 as S
S.initialize_modules(ROOT)


def bootstrap_library_fixture(tmp_path, monkeypatch, fault=None):
    """Small archive with scaled limits; no native host/privilege claim."""
    base = tmp_path / 'bootstrap'; (base / 'bin').mkdir(parents=True)
    interpreter = b'fixture interpreter, never executed'
    (base / 'bin/python3.11').write_bytes(interpreter)
    (base / 'lib').mkdir(); (base / 'lib/installer-extra.pyc').write_bytes(b'drift')
    private = tmp_path / 'private'; private.mkdir()
    entries = [('.', tarfile.DIRTYPE, b''), ('lib', tarfile.DIRTYPE, b''),
               ('lib/stock.py', tarfile.REGTYPE, b'fixed library'),
               ('lib/empty', tarfile.REGTYPE, b''),
               ('lib/pkgconfig/python-3.11.pc', tarfile.REGTYPE, b'fixed config'),
               ('lib/pkgconfig/python3.pc', tarfile.SYMTYPE, 'python-3.11.pc'),
               ('setup.sh', tarfile.REGTYPE, b'never execute archive scripts')]
    extra = {
        'traversal': ('lib/../escaped', tarfile.REGTYPE, b'bad'),
        'absolute': ('/escaped', tarfile.REGTYPE, b'bad'),
        'hardlink': ('lib/alias', tarfile.LNKTYPE, 'lib/stock.py'),
        'escape_link': ('lib/alias', tarfile.SYMTYPE, '../../escaped'),
        'absolute_link': ('lib/alias', tarfile.SYMTYPE, '/escaped'),
        'device': ('lib/device', tarfile.CHRTYPE, b''),
        'fifo': ('lib/fifo', tarfile.FIFOTYPE, b''),
        'duplicate': ('lib/stock.py', tarfile.REGTYPE, b'duplicate'),
        'linked_parent': ('lib/alias', tarfile.SYMTYPE, 'pkgconfig'),
        'setuid': ('lib/setuid', tarfile.REGTYPE, b'bad mode'),
    }
    if fault in extra: entries.append(extra[fault])
    if fault == 'linked_parent': entries.append(('lib/alias/child', tarfile.REGTYPE, b'bad alias'))
    archive = private / 'bootstrap.tar.gz'
    with tarfile.open(archive, 'w:gz') as output:
        for name, kind, content in entries:
            member = tarfile.TarInfo('./' + name if not name.startswith('/') else name)
            member.type = kind; member.mode = 0o755 if kind == tarfile.DIRTYPE else 0o644
            if fault == 'setuid' and name == 'lib/setuid': member.mode = 0o4644
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE): member.linkname = content
            if kind == tarfile.REGTYPE:
                member.size = len(content); output.addfile(member, binary_io.BytesIO(content))
            else: output.addfile(member)
    expanded = sum(len(content) for _, kind, content in entries if kind == tarfile.REGTYPE)
    monkeypatch.setattr(C, 'BOOTSTRAP_MEMBER_COUNT', len(entries))
    monkeypatch.setattr(C, 'BOOTSTRAP_EXPANDED_BYTES', expanded)
    monkeypatch.setattr(S.os, 'geteuid', lambda: 0)
    profile = {'bootstrap_prefix': str(base), 'bootstrap_python_sha256': C.io.digest(interpreter),
               'bootstrap': {'archive_size_bytes': archive.stat().st_size,
                             'archive_sha256': C.io.digest(archive.read_bytes())}}
    return private, base, profile


def test_bootstrap_preparation_replaces_drift_with_exact_verified_library(tmp_path, monkeypatch):
    private, base, profile = bootstrap_library_fixture(tmp_path, monkeypatch)
    with pytest.raises(C.io.IntakeError): C.verify_bootstrap(private/'bootstrap.tar.gz', profile, C.Budget(30))
    original_interpreter = (base/'bin/python3.11').read_bytes()
    observed = S.prepare_bootstrap_library(private, profile, C.Budget(30))
    assert observed == C.verify_bootstrap(private/'bootstrap.tar.gz', profile, C.Budget(30))
    assert (base/'lib/stock.py').read_bytes() == b'fixed library'
    assert (base/'lib/empty').read_bytes() == b''
    assert (base/'lib/pkgconfig/python3.pc').readlink().as_posix() == 'python-3.11.pc'
    assert not (base/'lib/installer-extra.pyc').exists()
    assert (base/'bin/python3.11').read_bytes() == original_interpreter
    assert not (base/'setup.sh').exists() and not (private/'bootstrap-library').exists()
    # A second preparation has the same closed inventory, with no accumulated extras.
    assert S.prepare_bootstrap_library(private, profile, C.Budget(30)) == observed


@pytest.mark.parametrize('fault', ['traversal', 'absolute', 'hardlink', 'escape_link', 'absolute_link',
                                 'device', 'fifo', 'duplicate', 'linked_parent', 'setuid',
                                 'archive_digest', 'interpreter_digest', 'count_limit', 'expanded_limit',
                                 'archive_link', 'library_link', 'prefix_link', 'nonroot', 'existing_stage'])
def test_bootstrap_preparation_rejects_before_changing_installed_library(tmp_path, monkeypatch, fault):
    private, base, profile = bootstrap_library_fixture(tmp_path, monkeypatch, fault)
    outside = tmp_path/'outside'; outside.mkdir(); (outside/'untouched').write_bytes(b'outside')
    if fault == 'archive_digest': profile['bootstrap']['archive_sha256'] = '0'*64
    elif fault == 'interpreter_digest': profile['bootstrap_python_sha256'] = '0'*64
    elif fault == 'count_limit': monkeypatch.setattr(C, 'BOOTSTRAP_MEMBER_COUNT', C.BOOTSTRAP_MEMBER_COUNT-1)
    elif fault == 'expanded_limit': monkeypatch.setattr(C, 'BOOTSTRAP_EXPANDED_BYTES', C.BOOTSTRAP_EXPANDED_BYTES-1)
    elif fault == 'archive_link':
        archive=private/'bootstrap.tar.gz'; archive.rename(private/'held.tar.gz'); archive.symlink_to('held.tar.gz')
    elif fault == 'library_link':
        (base/'lib').rename(base/'original-lib'); (base/'lib').symlink_to(outside, target_is_directory=True)
    elif fault == 'prefix_link':
        alias=tmp_path/'prefix-link'; alias.symlink_to(base, target_is_directory=True); profile['bootstrap_prefix']=str(alias)
    elif fault == 'nonroot': monkeypatch.setattr(S.os, 'geteuid', lambda: 1001)
    elif fault == 'existing_stage':
        stage=private/'bootstrap-library'; stage.mkdir(); (stage/'untouched').write_bytes(b'existing')
    with pytest.raises((C.io.IntakeError, FileExistsError)):
        S.prepare_bootstrap_library(private, profile, C.Budget(30))
    original=base/('original-lib' if fault == 'library_link' else 'lib')
    assert (original/'installer-extra.pyc').read_bytes() == b'drift'
    assert (outside/'untouched').read_bytes() == b'outside'
    if fault == 'existing_stage': assert (private/'bootstrap-library/untouched').read_bytes() == b'existing'
    else: assert not (private/'bootstrap-library').exists()


@pytest.mark.parametrize('fault', ['staged_byte', 'installed_byte', 'installed_extra', 'copy_failure', 'staging_cleanup'])
def test_bootstrap_preparation_rejects_drift_and_partial_installation(tmp_path, monkeypatch, fault):
    private, base, profile = bootstrap_library_fixture(tmp_path, monkeypatch)
    actual_verify=C.verify_bootstrap; actual_copy=S.shutil.copytree; actual_remove=S.shutil.rmtree
    def verify(archive, current, budget):
        if fault == 'staged_byte' and Path(current['bootstrap_prefix']) != base:
            (Path(current['bootstrap_prefix'])/'lib/stock.py').write_bytes(b'tainted staging')
        return actual_verify(archive, current, budget)
    def copy(source, destination, *args, **kwargs):
        if fault == 'copy_failure': raise OSError('fixture interrupted copy')
        result=actual_copy(source, destination, *args, **kwargs)
        if Path(destination) == base/'lib':
            if fault == 'installed_byte': (base/'lib/stock.py').write_bytes(b'tainted installation')
            elif fault == 'installed_extra': (base/'lib/extra.pyc').write_bytes(b'undeclared')
        return result
    def remove(path, *args, **kwargs):
        if fault == 'staging_cleanup' and Path(path) == private/'bootstrap-library':
            raise OSError('fixture staging cleanup failure')
        return actual_remove(path, *args, **kwargs)
    monkeypatch.setattr(C, 'verify_bootstrap', verify)
    monkeypatch.setattr(S.shutil, 'copytree', copy)
    monkeypatch.setattr(S.shutil, 'rmtree', remove)
    with pytest.raises((C.io.IntakeError, OSError)):
        S.prepare_bootstrap_library(private, profile, C.Budget(30))
    if fault == 'staged_byte': assert (base/'lib/installer-extra.pyc').read_bytes() == b'drift'
    assert (private/'bootstrap-library').exists() == (fault == 'staging_cleanup')


def legacy():
    spec = importlib.util.spec_from_file_location("q2_tokenizer_legacy_fixtures", ROOT / "tests/test_q2_reference_acquisition_v0.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def prior():
    return legacy()


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=15).stdout


@pytest.fixture
def committed(tmp_path, monkeypatch):
    original_mkdtemp = S.tempfile.mkdtemp
    def local_temp(*args, **kwargs):
        if kwargs.get('dir') == '/var/lib': kwargs['dir'] = str(tmp_path)
        return original_mkdtemp(*args, **kwargs)
    monkeypatch.setattr(S.tempfile, 'mkdtemp', local_temp)
    monkeypatch.setattr(S.os, 'geteuid', lambda: 0)
    repo = tmp_path / "repo"; repo.mkdir()
    for name in C.SOURCE_PATHS:
        dest = repo / name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest); os.chmod(dest, (ROOT / name).stat().st_mode & 0o777)
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
        "commit", "-qm", "Synthetic source fixture")
    return repo, git(repo, "rev-parse", "HEAD").decode().strip()


def owner_env(repo, revision):
    raw = C.io.encode(C.request_for(repo, revision)).rstrip(b"\n")
    return {"GITHUB_REPOSITORY": C.REPOSITORY, "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_SHA": revision, "GITHUB_WORKFLOW": S.NAME, "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_REF": C.REPOSITORY + "/" + C.WORKFLOW + "@refs/heads/main", "GITHUB_ACTOR": "HKati",
        "GITHUB_TRIGGERING_ACTOR": "HKati", "GITHUB_ACTOR_ID": "128643840", "GITHUB_ACTIONS": "true",
        "RUNNER_OS": "Linux", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_WORKSPACE": str(repo),
        "GITHUB_SHA": revision, "GITHUB_RUN_ID": "123456", "GITHUB_JOB": "verify_host",
        S.SOURCE: revision, S.REQUEST: raw.decode(), S.DIGEST: C.io.digest(raw)}


def test_closed_request_valid_exact_bytes_and_two_newlines(committed):
    repo, revision = committed
    raw = C.io.encode(C.request_for(repo, revision))
    for actual in (raw, raw.rstrip(b"\n"), raw + b"\n"):
        assert C.check_request(repo, actual, C.io.digest(actual), revision)["source_commit"] == revision
    with pytest.raises(C.io.IntakeError): C.check_request(repo, raw, C.io.digest(raw.rstrip(b"\n")), revision)


@pytest.mark.parametrize("fault", ["extra", "source", "future_run", "scope", "artifact", "definition", "bool_attempt", "profile"])
def test_closed_request_rejects_coherent_substitutions(fault):
    request = C.request_for(ROOT, "a" * 40)
    if fault == "extra": request["command"] = "arbitrary"
    elif fault == "source": request["source_commit"] = "b" * 40
    elif fault == "future_run": request["run_id"] = "123456"
    elif fault == "scope": request["scope"] = "full_worker"
    elif fault == "artifact": request["inputs"]["capsule"]["artifact_id"] += 1
    elif fault == "definition": request["definition_sha256"] = "b" * 64
    elif fault == "bool_attempt": request["inputs"]["capture"]["run_attempt"] = True
    else: request["profile_sha256"] = "b" * 64
    raw = C.io.encode(request)
    with pytest.raises(C.io.IntakeError): C.check_request(ROOT, raw, C.io.digest(raw), "a" * 40)


@pytest.mark.parametrize("raw", [b'\xef\xbb\xbf{}', b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'[]', b'{"a":"\xff"}', b'{"a":"\\ud800"}'])
def test_request_parser_rejects_ambiguous_or_invalid_encoding(raw):
    with pytest.raises(C.io.IntakeError): C.check_request(ROOT, raw, C.io.digest(raw), "a" * 40)


def test_source_closure_real_git_and_dirty_file(committed):
    repo, revision = committed
    rows = C.source_closure(repo, revision, C.Budget(180))
    assert len(rows) == len(C.SOURCE_PATHS)
    target = repo / C.SELF; target.write_bytes(target.read_bytes() + b"\n# dirty\n")
    with pytest.raises(C.io.IntakeError): C.source_closure(repo, revision, C.Budget(180))


@pytest.mark.parametrize("fault", ["helper", "profile", "source_mode", "source_link", "wrong_actor", "wrong_source"])
def test_preimport_guard_rejects_without_executing_dirty_helper(committed, fault, tmp_path):
    repo, revision = committed; env = owner_env(repo, revision)
    marker = tmp_path / "marker"
    target = repo / "PULSE_safe_pack_v0/tools/q2_intake_io_v0.py"
    if fault == "helper": target.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
    elif fault == "profile": (repo / C.PROFILE).write_bytes(b"{}\n")
    elif fault == "source_mode": os.chmod(target, 0o755 if not target.stat().st_mode & 0o111 else 0o644)
    elif fault == "source_link":
        payload = target.read_bytes(); target.unlink(); (tmp_path / "foreign.py").write_bytes(payload); target.symlink_to(tmp_path / "foreign.py")
    elif fault == "wrong_actor": env["GITHUB_ACTOR"] = "Other"
    else: env["GITHUB_SHA"] = "0" * 40
    with pytest.raises(ValueError): S.bootstrap_sources(repo, env)
    assert not marker.exists()


def test_preimport_snapshot_uses_the_verified_buffer(committed):
    repo, revision = committed
    snapshot = S.bootstrap_sources(repo, owner_env(repo, revision))
    try:
        expected = (repo / C.SELF).read_bytes()
        (repo / C.SELF).write_bytes(b"changed after snapshot")
        assert (snapshot / C.SELF).read_bytes() == expected
        assert all(p.stat().st_uid == os.getuid() for p in snapshot.rglob("*") if p.is_file())
    finally: shutil.rmtree(snapshot)


def test_authorize_actual_event_and_committed_source(committed, tmp_path):
    repo,revision=committed;env=owner_env(repo,revision)
    event={'inputs':{'source_commit':revision,'native_request':env[S.REQUEST],'native_request_sha256':env[S.DIGEST]},
           'ref':'main','sender':{'login':'HKati','id':128643840,'type':'User'},'repository':{'full_name':C.REPOSITORY}}
    path=tmp_path/'event.json';path.write_bytes(C.io.encode(event));env['GITHUB_EVENT_PATH']=str(path)
    binding,sources,raw=S.authorize(repo,env,C.Budget(180))
    assert binding['source_commit']==revision and sources==C.source_closure(repo,revision,C.Budget(180))
    event['inputs']['native_request_sha256']='0'*64;path.write_bytes(C.io.encode(event))
    with pytest.raises(C.io.IntakeError):S.authorize(repo,env,C.Budget(180))


@pytest.mark.parametrize('fault',[None,'main','actor','actor_id_type','attempt','event','workflow','job','job_attempt','job_status','source'])
def test_api_control_plane_is_required_and_closed(monkeypatch,fault):
    binding={'repository':C.REPOSITORY,'workflow':C.WORKFLOW,'source_commit':'a'*40,'run_id':'123456','run_attempt':1,'job_name':'verify_host'}
    main={'object':{'sha':'a'*40}}
    run={'id':123456,'run_attempt':1,'head_sha':'a'*40,'event':'workflow_dispatch','head_branch':'main','path':C.WORKFLOW,
         'repository':{'full_name':C.REPOSITORY},'head_repository':{'full_name':C.REPOSITORY},
         'actor':{'login':'HKati','id':128643840},'triggering_actor':{'login':'HKati','id':128643840}}
    jobs={'total_count':1,'jobs':[{'name':'verify_host','id':234567,'run_id':123456,'run_attempt':1,'head_sha':'a'*40,'status':'in_progress'}]}
    if fault=='main':main['object']['sha']='b'*40
    elif fault=='actor':run['actor']['login']='Other'
    elif fault=='actor_id_type':run['actor']['id']=128643840.0
    elif fault=='attempt':run['run_attempt']=True
    elif fault=='event':run['event']='push'
    elif fault=='workflow':run['path']='other.yml'
    elif fault=='job':jobs['total_count']=2
    elif fault=='job_attempt':jobs['jobs'][0]['run_attempt']=True
    elif fault=='job_status':jobs['jobs'][0]['status']='completed'
    elif fault=='source':jobs['jobs'][0]['head_sha']='b'*40
    rows=iter([main,run,jobs]);monkeypatch.setattr(S.transport,'api_json',lambda *_args:next(rows))
    if fault is None:assert S.authenticate_current(object(),binding,C.Budget(180))=={**binding,'job_id':'234567'}
    else:
        with pytest.raises(C.io.IntakeError):S.authenticate_current(object(),binding,C.Budget(180))


@pytest.fixture
def projected(tmp_path, monkeypatch):
    root = tmp_path / "projection"; root.mkdir()
    (root / "source").mkdir(); path = root / "source/helper.py"; path.write_bytes(b"bound source\n")
    # Ownership is an explicit metadata double: ordinary CI has no chown
    # privilege, and this local host maps only UID/GID 0. Bytes, modes, nlinks,
    # descriptor reads and directory extent remain actual filesystem behavior.
    owners = {}
    original_lstat = Path.lstat
    def chown(path, uid, gid): owners[str(path)] = (uid, gid)
    def lstat(path):
        info = original_lstat(path)
        if path == root or root in path.parents:
            values = {name: getattr(info, name) for name in dir(info) if name.startswith('st_')}
            values['st_uid'], values['st_gid'] = owners.get(str(path), (0, 65534))
            return types.SimpleNamespace(**values)
        return info
    monkeypatch.setattr(os, 'chown', chown)
    monkeypatch.setattr(Path, 'lstat', lstat)
    os.chown(path, 0, 65534); os.chmod(path, 0o440); S.freeze_directories(root)
    row = C.file_row(path, "source/helper.py", "source:helper.py", 0o600)
    return root, path, [row]


def test_projection_original_bytes_and_archive_mode_are_preserved(projected):
    root, path, rows = projected
    C.check_tree(root, rows, C.Budget(180))
    assert path.read_bytes() == b"bound source\n" and rows[0]["archive_mode"] == 0o600


def test_projection_extracts_large_binary_with_archive_bound_not_json_default(projected,tmp_path):
    root,_path,_rows=projected;root.chmod(0o750)
    raw=b'\0'*(16*1024*1024+1)
    path=tmp_path/'binary.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('large.bin',raw)
    budget=C.Budget(180)
    with C.io.Archive(path,maximum_bytes=path.stat().st_size,max_members=1,
        member_bytes=len(raw),expanded_bytes=len(raw),deadline=budget) as archive:
        with pytest.raises(C.io.IntakeError):archive.read('large.bin')
        rows=S.extract_projection(archive,root/'capsule','capsule',(),budget)
    C.check_tree(root/'capsule',rows,budget)
    assert rows[0]['size_bytes']==len(raw) and rows[0]['sha256']==C.io.digest(raw)
    assert (root/'capsule/large.bin').read_bytes()==raw


@pytest.mark.parametrize('fault',[None,'filled','alias','symlink','fifo'])
def test_archive_bound_empty_payload_retains_all_file_guards(projected,fault):
    root,path,_rows=projected
    path.chmod(0o640);path.write_bytes(b'');path.chmod(0o440)
    row=C.file_row(path,'source/helper.py','source:helper.py',0o600)
    assert row['size_bytes']==0 and row['sha256']==C.io.digest(b'')
    C.check_tree(root,[row],C.Budget(180))
    if fault is None:return
    root.chmod(0o750);(root/'source').chmod(0o750)
    if fault=='filled':path.chmod(0o640);path.write_bytes(b'substitute');path.chmod(0o440)
    elif fault=='alias':os.link(path,root/'alias')
    elif fault=='symlink':path.unlink();path.symlink_to('/dev/null')
    else:path.unlink();os.mkfifo(path,0o440)
    root.chmod(0o550);(root/'source').chmod(0o550)
    with pytest.raises(C.io.IntakeError):C.check_tree(root,[row],C.Budget(180))


def test_payload_reader_rejects_changed_held_file(projected,monkeypatch):
    _root,path,_rows=projected
    actual_read=os.read;changed=False
    def mutate(fd,count):
        nonlocal changed
        raw=actual_read(fd,count)
        if raw and not changed:
            changed=True;path.chmod(0o640);path.write_bytes(b'changed while held');path.chmod(0o440)
        return raw
    monkeypatch.setattr(C.os,'read',mutate)
    with pytest.raises(C.io.IntakeError) as error:C.payload_binding(path,1024,C.Budget(180))
    assert changed and error.value.code=='q2_unstable_input'


@pytest.mark.parametrize('name',[
    'lib/python3.11/site-packages/setuptools/_vendor/jaraco/text/Lorem ipsum.txt',
    'lib/python3.11/site-packages/setuptools/command/launcher manifest.xml',
    'lib/python3.11/site-packages/setuptools/script (dev).tmpl'])
def test_exact_official_bootstrap_names_do_not_broaden_capsule_grammar(name):
    C.bootstrap_member(name,True)
    with pytest.raises(C.io.IntakeError):C.bootstrap_member(name,False)
    with pytest.raises(C.io.IntakeError):C.io.safe_member(name)


@pytest.mark.parametrize('name',['lib/other name.py','lib/../other.py','/lib/absolute.py',
                                'lib/./dot.py','lib/escape\\name.py'])
def test_bootstrap_rejects_generic_spaces_and_escaping_names(name):
    with pytest.raises(C.io.IntakeError):C.bootstrap_member(name,True)


@pytest.mark.parametrize("fault", ["bytes", "unreadable", "writable", "owner", "group", "alias", "escape", "extra", "extra_dir", "duplicate"])
def test_projection_rejects_mutation_alias_or_unreadable_source(projected, fault):
    root, path, rows = projected
    if fault in ('bytes', 'alias', 'escape', 'extra', 'extra_dir'):
        root.chmod(0o750); (root / 'source').chmod(0o750)
    if fault == "bytes": path.chmod(0o640); path.write_bytes(b"other bytes\n"); path.chmod(0o440)
    elif fault == "unreadable": path.chmod(0o600)
    elif fault == "writable": path.chmod(0o460)
    elif fault == "owner": os.chown(path, 65534, 65534)
    elif fault == "group": os.chown(path, 0, 0)
    elif fault == "alias": os.link(path, root / "alias")
    elif fault == "escape": path.unlink(); path.symlink_to("/etc/passwd")
    elif fault == "extra": (root / "source/extra.pth").write_bytes(b"extra")
    elif fault == "extra_dir": (root / "empty-extra").mkdir()
    else: rows.append(copy.deepcopy(rows[0]))
    root.chmod(0o550); (root / 'source').chmod(0o550)
    with pytest.raises((C.io.IntakeError, OSError)): C.check_tree(root, rows, C.Budget(180))


def test_projection_actual_modes_grant_read_and_deny_subject_write(projected, tmp_path):
    root, path, rows = projected
    import stat
    assert stat.S_IMODE(path.stat().st_mode) == 0o440
    assert stat.S_IMODE(root.stat().st_mode) == 0o550
    C.check_tree(root, rows, C.Budget(180))


@pytest.mark.parametrize('fault',[None,'digest','size','origin','mode','duplicate','omitted'])
def test_every_projected_source_matches_reviewed_bytes(committed,fault):
    repo,revision=committed
    sources=C.source_closure(repo,revision,C.Budget(180))
    rows=[{'path':r['path'],'origin':'source:'+r['path'],'archive_mode':None,'kind':'file',
           'uid':0,'gid':65534,'mode':0o440,'size_bytes':r['size_bytes'],'sha256':r['sha256']} for r in sources]
    if fault=='digest':rows[0]['sha256']='0'*64
    elif fault=='size':rows[0]['size_bytes']+=1
    elif fault=='origin':rows[0]['origin']='capsule:'+rows[0]['path']
    elif fault=='mode':rows[0]['mode']=0o550
    elif fault=='duplicate':rows.append(copy.deepcopy(rows[0]))
    elif fault=='omitted':rows.pop()
    projection={'trees':{'source':rows}}
    if fault is None:C.check_source_projection(projection,sources)
    else:
        with pytest.raises(C.io.IntakeError):C.check_source_projection(projection,sources)


@pytest.fixture
def protocol(prior, tmp_path):
    f = prior.capture_synthetic.__wrapped__(tmp_path)
    evidence = f["output"]
    for name, obj in (("capture-prelaunch.json", f["pre"]), ("capture-subject.json", f["subject"]),
                      ("capture-model-ready.json", f["ready"]), ("transcript.json", f["terminal"])):
        (evidence / name).write_bytes(C.io.encode(obj))
    for slot in f["pre"]["slots"]:
        (evidence / "calls" / (slot["call_id"] + ".intent.json")).write_bytes(C.io.encode({
            "slot": slot, "binding": f["terminal"]["binding"], "generation_seconds": 15, "retries": 0, "intent": "before_GO"}))
    groups, manifest = prior.capture_reconstruct(f)
    (evidence / "groups.json").write_bytes(groups); (evidence / "dataset-manifest.json").write_bytes(manifest)
    return f


def test_all_150_record_derivations_use_tokenizer_and_do_not_generate(protocol):
    f = protocol; before = f["counters"]["calls"]
    groups, manifest = C.derive_records(ROOT, f["output"], f["tokenizer"], f["config"])
    assert groups == (f["output"] / "groups.json").read_bytes()
    assert manifest == (f["output"] / "dataset-manifest.json").read_bytes()
    assert f["counters"]["calls"] == before  # Synthetic worker setup is outside this checker.
    assert sum(len(g["responses"]) for g in json.loads(groups)["groups"]) == 150


@pytest.mark.parametrize("fault", ["omitted", "duplicated", "reordered", "token", "text", "configuration", "tokenizer", "decoder", "intent", "group_output"])
def test_150_record_replay_rejects_coherent_and_incoherent_substitution(protocol, fault):
    f = protocol; evidence = f["output"]
    terminal = f["terminal"]
    stem = "calls/" + terminal["occurrences"][0]["slot"]["call_id"]
    if fault == "omitted": terminal["occurrences"].pop()
    elif fault == "duplicated": terminal["occurrences"][1] = copy.deepcopy(terminal["occurrences"][0])
    elif fault == "reordered": terminal["occurrences"][0], terminal["occurrences"][1] = terminal["occurrences"][1], terminal["occurrences"][0]
    elif fault in ("token", "text", "configuration"):
        name = stem + ".response.json"; obj = C.io.strict_json((evidence / name).read_bytes())
        if fault == "token": obj["new_token_ids"][0] += 1
        elif fault == "text": obj["text"] = "substitute"
        else: obj["effective_generation"]["do_sample"] = True
        raw = C.io.encode(obj); (evidence / name).write_bytes(raw)
        terminal["occurrences"][0]["response"].update(size=len(raw), sha256=C.io.digest(raw))
    elif fault == "tokenizer": f["tokenizer"].apply_chat_template = lambda *args, **kwargs: [1, 999]
    elif fault == "decoder": f["tokenizer"].decode = lambda *args, **kwargs: "different"
    elif fault == "intent": (evidence / (stem + ".intent.json")).write_bytes(b"{}\n")
    else: (evidence / "groups.json").write_bytes(b"{}\n")
    (evidence / "transcript.json").write_bytes(C.io.encode(terminal))
    with pytest.raises((C.io.IntakeError, ValueError, KeyError)):
        C.derive_records(ROOT, evidence, f["tokenizer"], f["config"])


def test_existing_real_reducer_and_checker_keep_historical_negative(tmp_path):
    p = C.load_profile(ROOT)
    archive = ROOT / "PULSE_safe_pack_v0/examples/q2_reference_capture_v0/run_37600313529"
    # Preserved metadata includes the exact summary, while response fixtures
    # build a real 49/50 negative dataset and use the unchanged two CLIs.
    prior = legacy(); f = prior.capture_synthetic.__wrapped__(tmp_path)
    f["records"][0][0]["new_token_ids"] = [41] * 32
    f["records"][0][0]["stop_reason"] = "token_limit"
    f["records"][0][0]["text"] = "alternate"
    import base64
    f["records"][0][0]["text_utf8_base64"] = base64.b64encode(b"alternate").decode()
    # Make the entire first group unknown; leave all other groups consistent.
    for response, _ready in f["records"][:3]:
        response.update(new_token_ids=[41]*32, stop_reason="token_limit", text="alternate", text_utf8_base64=base64.b64encode(b"alternate").decode())
    groups, manifest = prior.capture_reconstruct(f)
    work = tmp_path / "reduction"; work.mkdir()
    (work / "groups.json").write_bytes(groups); (work / "dataset-manifest.json").write_bytes(manifest)
    common = ["--groups", str(work / "groups.json"), "--dataset-manifest", str(work / "dataset-manifest.json"),
              "--expected-groups-sha256", C.io.digest(groups), "--expected-manifest-sha256", C.io.digest(manifest)]
    rc = subprocess.run([sys.executable, "-I", "-B", str(ROOT / C.io.REDUCER), *common, "--out", str(work / "summary.json")],
                        capture_output=True, timeout=20)
    assert rc.returncode == 1
    summary = C.io.strict_json((work / "summary.json").read_bytes())
    assert summary["counts"]["groups_eligible"] == 49 and summary["pass"] is False
    check = subprocess.run([sys.executable, "-I", "-B", str(ROOT / C.io.CHECKER), *common, "--summary", str(work / "summary.json"),
        "--expected-summary-sha256", C.io.digest((work / "summary.json").read_bytes())], capture_output=True, timeout=20)
    assert check.returncode == 0 and json.loads(check.stdout)["recomputed_pass"] is False
    assert json.loads((archive / "summary.json").read_bytes())["counts"]["groups_eligible"] == 49
    assert p["claims"]["current_inference_count"] == 0


@pytest.mark.parametrize("exit_code, expected, accepted", [(0,0,True),(1,1,True),(1,0,False),(0,1,False),(2,1,False),(-9,0,False)])
def test_real_process_terminal_exit_and_eof(exit_code, expected, accepted):
    process = subprocess.Popen([sys.executable, "-I", "-B", "-c", f"import sys; sys.exit({exit_code})"], stdout=subprocess.PIPE)
    reader = S.native.BoundedReader(process.stdout)
    service = types.SimpleNamespace(reader=reader, process=process, deadline=__import__('time').monotonic()+3,
                                   runtime_deadline_ns=__import__('time').monotonic_ns()+3_000_000_000)
    try:
        if accepted: assert S.complete_expected(service, expected, C.Budget(3)) == (b"", expected)
        else:
            with pytest.raises(C.io.IntakeError): S.complete_expected(service, expected, C.Budget(3))
        assert reader.eof and process.poll() is not None
    finally:
        if process.poll() is None: process.kill(); process.wait(timeout=2)
        reader.close(); process.stdout.close()


def test_missing_eof_and_timeout_are_not_completion():
    process = subprocess.Popen([sys.executable, "-I", "-B", "-c", "import time; time.sleep(3)"], stdout=subprocess.PIPE)
    reader = S.native.BoundedReader(process.stdout)
    now = __import__('time').monotonic()
    service = types.SimpleNamespace(reader=reader, process=process, deadline=now+.05, runtime_deadline_ns=int((now+.05)*1e9))
    try:
        with pytest.raises((C.io.IntakeError, S.native.NativeQualificationError)):
            S.complete_expected(service, 0, C.Budget(.05))
        assert not reader.eof
    finally:
        process.kill(); process.wait(timeout=2); reader.close(); process.stdout.close()


def test_cleanup_grace_is_shared_not_reset(monkeypatch):
    budget=types.SimpleNamespace(end=1000.0)
    for now,expected in [(999.0,180),(1000.0,180),(1100.0,80),(1179.0,1)]:
        monkeypatch.setattr(S.time,'monotonic',lambda:now)
        assert S.cleanup_seconds(budget)==expected
    monkeypatch.setattr(S.time,'monotonic',lambda:1180.0)
    with pytest.raises(C.io.IntakeError):S.cleanup_seconds(budget)


def test_projection_descriptor_access_keeps_private_payloads_separate(tmp_path, monkeypatch):
    """Real descriptor IO with owner-mode equivalents of subject permissions.

    This is not UID-65534/systemd evidence. Ownership is explicitly doubled;
    the zero group permissions on private are exercised as zero owner access.
    """
    run = tmp_path/'run'; run.mkdir(mode=0o700)
    private = run/'private'; private.mkdir(mode=0o700)
    projection = run/'projection'; projection.mkdir(mode=0o700)
    payload = projection/'profile.json'; payload.write_bytes(b'{"fixed":true}'); payload.chmod(0o440)
    secret = private/'archive.zip'; secret.write_bytes(b'private archive')
    ownership = []
    monkeypatch.setattr(S.os, 'chown', lambda path, uid, gid: ownership.append((path, uid, gid)))
    try:
        # Same failure as the old parent's missing read permission. Traversal
        # permits open(file), but the held-directory reader correctly rejects.
        run.chmod(0o111)
        assert payload.read_bytes() == b'{"fixed":true}'
        try:
            C.io.read_file(payload, 1024)
        except C.io.IntakeError as exc:
            assert exc.code == 'q2_file_rejected'
        else:
            pytest.skip('Descriptor permission test requires a reader without DAC bypass')
        run.chmod(0o700)
        S.expose_projection(run)
        assert C.io.read_file(payload, 1024) == b'{"fixed":true}'
        assert stat.S_IMODE(run.stat().st_mode) == stat.S_IMODE(projection.stat().st_mode) == 0o550
        assert stat.S_IMODE(private.stat().st_mode) == 0o700
        assert ownership == [(private, 0, 0), (projection, 0, 65534), (run, 0, 65534)]
        private.chmod(0)  # Owner-mode equivalent of private's actual group bits.
        with pytest.raises(C.io.IntakeError, match='q2_file_rejected'):
            C.io.read_file(secret, 1024)
        assert C.io.read_file(payload, 1024) == b'{"fixed":true}'
    finally:
        for directory in (run, private, projection): directory.chmod(0o700)


@pytest.mark.parametrize('fault', ['extra_payload', 'private_mode', 'private_link', 'projection_link', 'ownership'])
def test_projection_exposure_rejects_unsafe_layout(tmp_path, monkeypatch, fault):
    run = tmp_path/'run'; run.mkdir(mode=0o700)
    for name in ('private', 'projection'): (run/name).mkdir(mode=0o700)
    calls = []
    def own(*args):
        calls.append(args)
        if fault == 'ownership': raise PermissionError('fixture ownership failure')
    monkeypatch.setattr(S.os, 'chown', own)
    if fault == 'extra_payload': (run/'archive.zip').write_bytes(b'not private')
    elif fault == 'private_mode': (run/'private').chmod(0o750)
    elif fault.endswith('_link'):
        path = run/fault.removesuffix('_link'); path.rmdir(); path.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises((C.io.IntakeError, PermissionError)): S.expose_projection(run)
    assert stat.S_IMODE(run.stat().st_mode) == 0o700
    assert fault == 'ownership' or calls == []


@pytest.mark.parametrize('raw,expected', [
    (b'q2_file_rejected\n', 'q2_file_rejected'),
    (b'private-token=do-not-publish\nq2_file_rejected\n', 'q2_file_rejected'),
    (b'q2_file_rejected\nq2_file_rejected\n', 'q2_file_rejected'),
    (b'q2_file_rejected\nq2_timeout\n', 'unknown'),
    (b'prefix q2_file_rejected\n', 'unknown'),
    (b'private-token=do-not-publish\n', 'unknown'),
    (b'', 'unknown'),
    (b'q2_file_rejected\n'+b'x'*(128*1024), 'unknown'),
])
def test_child_diagnostics_are_bounded_closed_codes(tmp_path, raw, expected):
    log = tmp_path/'private.stderr'; log.write_bytes(raw)
    assert S.child_error_code(log) == expected


@pytest.mark.parametrize('kind', ['missing', 'symlink', 'fifo'])
def test_unavailable_child_diagnostics_do_not_replace_failure(tmp_path, kind):
    log = tmp_path/'private.stderr'
    if kind == 'symlink': log.symlink_to(tmp_path/'missing')
    elif kind == 'fifo': os.mkfifo(log)
    assert S.child_error_code(log) == 'unknown'


@pytest.mark.parametrize('error,expected', [
    (C.io.IntakeError('q2_file_rejected'), 'q2_file_rejected'),
    (S.native.NativeQualificationError('capture_service_not_inactive'), 'capture_service_not_inactive'),
    (S.native.NativeQualificationError('private-token=do-not-publish'), 'unknown'),
    (OSError('private-token=do-not-publish'), 'unknown'),
    (ValueError('q2_file_rejected'), 'unknown'),
])
def test_exception_diagnostics_never_publish_arbitrary_messages(error, expected):
    detail = S.failure_detail(error, 'q2_cleanup_failed')
    assert detail['reason'] == expected
    assert 'do-not-publish' not in json.dumps(detail)


@pytest.mark.parametrize('fault',[None,'startup','exit','exit_and_cleanup','no_eof','cleanup','cleanup_evidence',
                                 'projection_mutation','bootstrap_drift','extra_output','bad_output'])
def test_occurrence_stops_and_reaps_before_any_accepted_handoff(tmp_path,monkeypatch,fault):
    """Real child/EOF/output; explicit kernel, ownership and bootstrap doubles.

    This exercises the supervisor failure boundary, not systemd acquisition.
    """
    import time
    p=C.load_profile(ROOT);root=tmp_path/'projection';root.mkdir()
    for name in ('work','handoff','source','inputs'):(root/name).mkdir()
    helper=root/'source'/C.TOOLS/'check_q2_reference_capture_v0.py'
    helper.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/C.TOOLS/'check_q2_reference_capture_v0.py',helper)
    expected_helper=C.io.digest(helper.read_bytes())
    summary=ROOT/'PULSE_safe_pack_v0/examples/q2_reference_capture_v0/run_37600313529/summary.json'
    script="from pathlib import Path; import sys,time; "
    script+=("time.sleep(2); " if fault=='no_eof' else '')
    script+="Path('summary.json').write_bytes("+('b\'{}\\n\'' if fault=='bad_output' else "Path(sys.argv[1]).read_bytes()")+"); "
    script+=("Path('unexpected.json').write_bytes(b'{}'); " if fault=='extra_output' else '')
    script+="sys.stderr.write('private-token=do-not-publish\\nq2_file_rejected\\n'); "
    script+='sys.exit('+('0' if fault in ('exit','exit_and_cleanup') else '1')+')'
    declared={'id':'summary_builder','stage':'reduction','expected_exit':1,'outputs':['summary.json'],
              'input_bindings':[],'argv':[sys.executable,'-I','-B','-c',script,str(summary)]}
    pre={'bootstrap_lib_sha256':'b'*64,
         'source_bindings':[{'path':C.TOOLS+'check_q2_reference_capture_v0.py','sha256':expected_helper}]}
    children=[];closures=[];projection_checks=[]
    class KernelDouble:
        def __init__(self,prefix,stage,command,work,_python,_log,phase_end):
            launch=time.monotonic_ns();self.unit=prefix+'-'+stage+'.service'
            self.runtime_deadline_ns=launch+180_000_000_000
            self.deadline=min(phase_end,time.monotonic()+(0.05 if fault=='no_eof' else 3))
            self.log=_log.open('xb')
            self.process=subprocess.Popen(command,cwd=work,stdout=subprocess.PIPE,stderr=self.log)
            self.reader=S.native.BoundedReader(self.process.stdout);children.append(self)
            if fault=='startup':raise C.io.IntakeError('q2_context_rejected')
            self.observation={'pid':self.process.pid}
            self.isolation_observed_ns=time.monotonic_ns();self.exec_ns=time.monotonic_ns()
    def close(service):
        closures.append(service.unit)
        if service.process.poll() is None:service.process.kill()
        service.process.wait(timeout=2);service.reader.close();service.process.stdout.close();service.log.close()
        if fault=='projection_mutation':helper.write_bytes(b'mutated after exit')
        if fault=='cleanup':raise C.io.IntakeError('q2_cleanup_failed')
        if fault=='exit_and_cleanup':raise S.native.NativeQualificationError('capture_service_not_inactive')
        return {'unit':service.unit,'properties':{'LoadState':'not-found','ActiveState':'inactive','ControlGroup':''},
                'cgroup_empty_or_removed':True,'client_reaped':fault!='cleanup_evidence'}
    def projection_check(_root,_projection,_profile,_budget):
        projection_checks.append(C.io.digest(helper.read_bytes()))
        C.io.require(projection_checks[-1]==expected_helper,'q2_source_mismatch')
    monkeypatch.setattr(S,'ObservedService',KernelDouble)
    monkeypatch.setattr(S.native,'close_capture_service',close)
    monkeypatch.setattr(C,'check_projection',projection_check)
    monkeypatch.setattr(C,'verify_bootstrap',lambda *_args:'c'*64 if fault=='bootstrap_drift' else 'b'*64)
    monkeypatch.setattr(os,'chown',lambda *_args:None)
    try:
        if fault is None:
            result=S.run_occurrence(root,tmp_path,declared,{'fixture':True},pre,p,C.Budget(10))
            assert result['exit_code']==1 and result['stdout_eof'] is True
            assert result['outputs']=={'summary.json':p['historical_output_sha256']['summary.json']}
            assert result['exit_ns']<=result['cleanup_ns']<=result['output_frozen_ns']
            assert (root/'handoff/summary_builder/summary.json').read_bytes()==summary.read_bytes()
        else:
            with pytest.raises(S.OccurrenceFailure) as rejected:
                S.run_occurrence(root,tmp_path,declared,{'fixture':True},pre,p,C.Budget(10))
            assert rejected.value.observation['status']=='failed'
            observation = rejected.value.observation
            assert 'do-not-publish' not in json.dumps(observation)
            if fault in ('exit','exit_and_cleanup'):
                assert observation['exit_code'] == 0 and observation['expected_exit'] == 1
                assert observation['failure_phase'] == 'completion'
                assert observation['child_error_code'] == 'q2_file_rejected'
                assert rejected.value.code == 'q2_replay_rejected'
                assert observation['cleanup_verified'] == (fault == 'exit')
            if fault == 'exit_and_cleanup':
                assert observation['cleanup_error'] == {'error_code':'q2_cleanup_failed',
                    'reason':'capture_service_not_inactive'}
                assert observation['cleanup'] is None
            if fault in ('cleanup','cleanup_evidence'):
                assert observation['failure_phase'] == 'cleanup'
                assert observation['cleanup_verified'] is False
                assert rejected.value.code == 'q2_cleanup_failed'
            if fault in ('startup','no_eof'): assert observation['exit_code'] is None
            assert not (root/'handoff/summary_builder/summary.json').exists()
        assert len(children)==len(closures)==1 and children[0].process.poll() is not None
        assert not (tmp_path/'result.json').exists()
    finally:
        for directory in root.rglob('*'):
            if directory.is_dir():directory.chmod(0o750)


def test_atomic_publication_never_overwrites_and_rejects_symlink(tmp_path):
    S.atomic_publish(tmp_path, "result.json", b"first")
    with pytest.raises(FileExistsError): S.atomic_publish(tmp_path, "result.json", b"second")
    assert (tmp_path / "result.json").read_bytes() == b"first"
    (tmp_path / "alias.json").symlink_to("result.json")
    with pytest.raises(FileExistsError): S.atomic_publish(tmp_path, "alias.json", b"substitute")
    assert not list(tmp_path.glob('.q2-tokenizer-*'))


@pytest.mark.parametrize('fault',['mode','file_sync','link','temporary_unlink','directory_sync'])
def test_failed_publication_removes_its_new_entry(tmp_path,monkeypatch,fault):
    original_sync,original_link,original_unlink=os.fsync,os.link,os.unlink
    def sync(fd):
        import stat
        is_directory=stat.S_ISDIR(os.fstat(fd).st_mode)
        if (fault=='directory_sync' and is_directory) or (fault=='file_sync' and not is_directory):
            raise OSError('fixture synchronization failure')
        return original_sync(fd)
    def link(*args,**kwargs):
        if fault=='link':raise OSError('fixture link failure')
        return original_link(*args,**kwargs)
    unlink_calls=[]
    def unlink(path,*args,**kwargs):
        unlink_calls.append(str(path))
        if fault=='temporary_unlink' and len(unlink_calls)==1:raise OSError('fixture unlink failure')
        return original_unlink(path,*args,**kwargs)
    monkeypatch.setattr(os,'fsync',sync);monkeypatch.setattr(os,'link',link);monkeypatch.setattr(os,'unlink',unlink)
    if fault=='mode':
        monkeypatch.setattr(os,'fchmod',lambda *_args:(_ for _ in ()).throw(OSError('fixture mode failure')))
    with pytest.raises(OSError):S.atomic_publish(tmp_path,'result.json',b'accepted candidate')
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('fault',[None,'bootstrap_preparation','first_occurrence','second_occurrence','receipt_replay',
                                 'source_after_replay','private_cleanup','bootstrap_cleanup','both_cleanups',
                                 'execution_and_cleanup','final_publication'])
def test_collector_publishes_acceptance_only_after_both_private_trees_removed(committed,tmp_path,monkeypatch,fault):
    """Collector integration with explicit transport/kernel/replay doubles.

    Actual source guard, candidate files, exclusive publication and deletion
    ordering run. Native acquisition is tested separately in owner-run evidence.
    """
    repo,revision=committed;p=C.load_profile(repo);env=owner_env(repo,revision)
    runner=tmp_path/'runner';runner.mkdir();env['RUNNER_TEMP']=str(runner)
    event=tmp_path/'dispatch.json'
    event.write_bytes(C.io.encode({'inputs':{'source_commit':revision,'native_request':env[S.REQUEST],
        'native_request_sha256':env[S.DIGEST]},'ref':'main','sender':{'login':'HKati','id':128643840,'type':'User'},
        'repository':{'full_name':C.REPOSITORY}}));env['GITHUB_EVENT_PATH']=str(event)
    bootstrap=tmp_path/'bootstrap-snapshot';bootstrap.mkdir();(bootstrap/'held-source.py').write_bytes(b'held source')
    private_paths=[];calls=[];replays=[]
    actual_mkdtemp=S.tempfile.mkdtemp
    def make_run_directory(**kwargs):
        path=Path(actual_mkdtemp(prefix=kwargs['prefix'],dir=tmp_path))
        private_paths.append(path)
        return str(path)
    monkeypatch.setattr(S.tempfile,'mkdtemp',make_run_directory)
    monkeypatch.setattr(S,'host_record',lambda *_args:dict(p['archived_platform_requirements']))
    monkeypatch.setattr(S.shutil,'disk_usage',lambda *_args:types.SimpleNamespace(free=9*1024**3))
    monkeypatch.setattr(S.io,'GitHubArtifactTransport',lambda *_args:object())
    monkeypatch.setattr(S,'authenticate_current',lambda _client,binding,_budget:{**binding,'job_id':'234567'})
    monkeypatch.setattr(S.transport,'download_artifact',lambda _client,_expected,destination,_budget:C.io.write_new(destination,b'fixture archive'))
    monkeypatch.setattr(S.transport,'download_bootstrap',lambda _expected,destination,_budget:C.io.write_new(destination,b'fixture bootstrap'))
    monkeypatch.setattr(C,'verify_bootstrap',lambda *_args:'b'*64)
    def prepare_bootstrap(*_args):
        if fault == 'bootstrap_preparation': raise C.io.IntakeError('q2_replay_environment')
        return 'b'*64
    monkeypatch.setattr(S,'prepare_bootstrap_library',prepare_bootstrap)
    monkeypatch.setattr(C,'check_prelaunch',lambda *_args:None)
    monkeypatch.setattr(os,'chown',lambda *_args:None)
    preparation=[]
    def prepare(private,root,_profile,_budget):
        preparation.append('prepare');(root/'verifier').mkdir();return ['fixture verifier rows']
    def bind(_root,rows,*_args):
        assert preparation==['prepare'] and rows==['fixture verifier rows'];preparation.append('bind')
    monkeypatch.setattr(S,'prepare_verifier',prepare)
    monkeypatch.setattr(C,'bind_collector_dependencies',bind)
    def materialize(_repo,private,root,_profile,_sources,_budget):
        assert preparation==['prepare','bind'] and private['verifier_rows']==['fixture verifier rows']
        assert private['path'] == root.parent/'private' and root.parent == private_paths[0]
        (root/'inputs').mkdir()
        return {'record_type':'q2_tokenizer_projection_v0','trees':{}},{'capture-subject.json':{'platform':p['archived_platform_requirements']}}
    monkeypatch.setattr(S,'materialize',materialize)
    def occurrence(root,_private,declared,*_args):
        index=len(calls);calls.append(declared['id'])
        assert _private == root.parent/'private' and stat.S_IMODE(_private.stat().st_mode) == 0o700
        assert stat.S_IMODE(root.parent.stat().st_mode) == 0o550
        if (fault in ('first_occurrence','execution_and_cleanup') and index==0) or (fault=='second_occurrence' and index==1):
            raise S.OccurrenceFailure('q2_replay_rejected',{'id':declared['id'],'status':'failed',
                'unit':None,'pid':None,'exec_ns':None,'cleanup':None,'cleanup_verified':False})
        # The explicit kernel double also supplies root's native DAC ability.
        (root/'handoff').chmod(0o700)
        handoff=root/'handoff'/declared['id'];handoff.mkdir()
        for name in declared['outputs']:C.io.write_new(handoff/name,C.io.encode({'fixture_only':True}))
        return {'id':declared['id'],'status':'completed'}
    monkeypatch.setattr(S,'run_occurrence',occurrence)
    def replay(_repo,evidence,_inputs):
        assert {q.name for q in evidence.iterdir()}==set(C.PUBLIC_FILES)
        assert private_paths[0].exists() and not (runner/'q2-native-tokenizer/result.json').exists()
        replays.append(evidence)
        if fault=='receipt_replay':raise C.io.IntakeError('q2_replay_rejected')
        if fault=='source_after_replay':(repo/C.SELF).write_bytes(b'changed after replay')
    monkeypatch.setattr(C,'validate_receipt',replay)
    original_publish=S.atomic_publish
    def publish(directory,name,raw):
        if fault=='final_publication' and name=='result.json':raise OSError('fixture final publication failure')
        return original_publish(directory,name,raw)
    monkeypatch.setattr(S,'atomic_publish',publish)
    actual_rmtree=shutil.rmtree
    def remove(path,*args,**kwargs):
        path=Path(path)
        if path==bootstrap or path in private_paths:
            assert not (runner/'q2-native-tokenizer/result.json').exists()
            if (path==bootstrap and fault in ('bootstrap_cleanup','both_cleanups')) or (path in private_paths and fault in ('private_cleanup','both_cleanups','execution_and_cleanup')):
                raise OSError('fixture cleanup failure')
            # Ordinary CI/local root lacks the native runner's DAC capability;
            # this fixture restores deletion permissions, then deletes real data.
            path.chmod(0o700)
            for item in path.rglob('*'):
                if item.is_dir() and not item.is_symlink():item.chmod(0o700)
        return actual_rmtree(path,*args,**kwargs)
    monkeypatch.setattr(S.shutil,'rmtree',remove)
    try:
        if fault is None:
            result=S.supervise(repo,env,bootstrap_snapshot=bootstrap)
            assert result['status']=='native_tokenizer_verified' and result['claims']==C.CLAIMS
            assert not bootstrap.exists() and not private_paths[0].exists()
            assert {q.name for q in (runner/'q2-native-tokenizer').iterdir()}==set(C.PUBLIC_FILES)
        else:
            with pytest.raises((C.io.IntakeError,S.OccurrenceFailure,OSError)):S.supervise(repo,env,bootstrap_snapshot=bootstrap)
            output=runner/'q2-native-tokenizer'
            assert not (output/'result.json').exists()
            rejection=C.io.strict_json((output/'failure.json').read_bytes())
            assert rejection['status']=='rejected' and rejection['claims']==C.CLAIMS
            assert rejection['cleanup']==('not_verified' if fault in ('private_cleanup','bootstrap_cleanup','both_cleanups','first_occurrence','second_occurrence','execution_and_cleanup') else 'verified_removed')
            assert rejection['directory_cleanup']['run_directory']==('not_verified' if fault in ('private_cleanup','both_cleanups','execution_and_cleanup') else 'verified_removed')
            assert rejection['directory_cleanup']['bootstrap_snapshot']==('not_verified' if fault in ('bootstrap_cleanup','both_cleanups') else 'verified_removed')
            assert set(rejection['cleanup_errors']) == ({'run_directory','bootstrap_snapshot'} if fault=='both_cleanups' else
                {'run_directory'} if fault in ('private_cleanup','execution_and_cleanup') else {'bootstrap_snapshot'} if fault=='bootstrap_cleanup' else set())
            if fault in ('first_occurrence','second_occurrence','execution_and_cleanup'):
                assert rejection['error_code']=='q2_replay_rejected'
                failed=1 if fault=='second_occurrence' else 0
                assert len(calls)==failed+1
                assert rejection['occurrences'][failed]['status']=='failed'
                assert all(r['status']=='not_started' for r in rejection['occurrences'][failed+1:])
            if fault == 'bootstrap_preparation':
                assert not calls and all(r['status']=='not_started' for r in rejection['occurrences'])
        assert len(replays)==(0 if fault in ('bootstrap_preparation','first_occurrence','second_occurrence','execution_and_cleanup') else 1)
    finally:
        for path in [bootstrap,*private_paths]:
            if path.exists():
                path.chmod(0o700)
                for item in path.rglob('*'):
                    if item.is_dir() and not item.is_symlink():item.chmod(0o700)
                actual_rmtree(path)


@pytest.mark.parametrize('existing',['directory','symlink'])
def test_collector_leaves_preexisting_output_untouched(committed,tmp_path,monkeypatch,existing):
    repo,revision=committed;p=C.load_profile(repo);env=owner_env(repo,revision)
    runner=tmp_path/'runner';runner.mkdir();env['RUNNER_TEMP']=str(runner)
    target=tmp_path/'existing';target.mkdir();(target/'result.json').write_bytes(b'preexisting')
    destination=runner/'q2-native-tokenizer'
    if existing=='symlink':destination.symlink_to(target,target_is_directory=True)
    else:destination.mkdir();(destination/'result.json').write_bytes(b'preexisting')
    monkeypatch.setattr(S,'authorize',lambda *_args:({},[],b'{}'))
    monkeypatch.setattr(S,'host_record',lambda *_args:dict(p['archived_platform_requirements']))
    monkeypatch.setattr(S.shutil,'disk_usage',lambda *_args:types.SimpleNamespace(free=9*1024**3))
    with pytest.raises(FileExistsError):S.supervise(repo,env)
    assert {q.name for q in destination.iterdir()}=={'result.json'}
    assert (destination/'result.json').read_bytes()==b'preexisting'


@pytest.fixture
def verifier_metadata(tmp_path):
    """Synthetic packages; actual closed distribution metadata inspection."""
    p=C.load_profile(ROOT);verifier=tmp_path/'verifier'
    site=verifier/'lib/python3.11/site-packages';site.mkdir(parents=True)
    for row in p['verifier_wheels']:
        folder=site/(row['name'].replace('-','_')+'-'+row['version']+'.dist-info');folder.mkdir()
        (folder/'METADATA').write_text('Metadata-Version: 2.1\nName: '+row['name']+'\nVersion: '+row['version']+'\n')
    return verifier,site,p


@pytest.mark.parametrize('fault',[None,'missing','extra','duplicate','version'])
def test_verifier_dependencies_require_all_and_only_pinned_versions(verifier_metadata,fault):
    verifier,site,p=verifier_metadata
    metadata=next(site.glob('attrs-*.dist-info/METADATA'))
    if fault=='missing':metadata.unlink()
    elif fault in ('extra','duplicate'):
        folder=site/'unexpected-1.dist-info';folder.mkdir()
        (folder/'METADATA').write_text('Metadata-Version: 2.1\nName: '+('attrs' if fault=='duplicate' else 'unexpected')+'\nVersion: 26.1.0\n')
    elif fault=='version':metadata.write_text('Metadata-Version: 2.1\nName: attrs\nVersion: 0\n')
    if fault is None:assert C.verifier_dependencies(verifier,p)==site
    else:
        with pytest.raises(C.io.IntakeError):C.verifier_dependencies(verifier,p)


@pytest.mark.parametrize('fault',[None,'unverified_tree','cached_external','imported_external'])
def test_collector_dependency_binding_rejects_unverified_or_external_packages(verifier_metadata,tmp_path,monkeypatch,fault):
    verifier,site,p=verifier_metadata;checked=[];imported=[]
    # Import execution is a labeled package double; tree acceptance precedes it.
    runtime=types.SimpleNamespace(modules={},path=[])
    monkeypatch.setattr(C,'sys',runtime)
    def check(*_args):
        checked.append('tree')
        if fault=='unverified_tree':raise C.io.IntakeError('q2_digest_mismatch')
        return C.verifier_dependencies(verifier,p)
    monkeypatch.setattr(C,'check_verifier_tree',check)
    external=tmp_path/'external.py';external.write_bytes(b'external package')
    if fault=='cached_external':runtime.modules['jsonschema']=types.SimpleNamespace(__file__=str(external))
    for name in C.VERIFIER_MODULES:(site/(name+'.py')).write_bytes(b'fixture package')
    def import_package(name):
        assert checked==['tree'];imported.append(name)
        runtime.modules[name]=types.SimpleNamespace(__file__=str(external if fault=='imported_external' and name=='jsonschema' else site/(name+'.py')))
    monkeypatch.setattr(C.importlib,'import_module',import_package)
    if fault is None:
        assert C.bind_collector_dependencies(verifier,[],p,C.Budget(180))==site
        assert imported==list(C.VERIFIER_MODULES) and runtime.path==[str(site)]
    else:
        with pytest.raises(C.io.IntakeError):C.bind_collector_dependencies(verifier,[],p,C.Budget(180))
        if fault in ('unverified_tree','cached_external'):assert imported==[] and runtime.path==[]


def test_bootstrap_import_and_request_contract_run_without_third_party_packages(committed,tmp_path):
    """Actual clean isolated Python; no pip or site-package dependencies."""
    repo,revision=committed;environment=tmp_path/'bare-python'
    subprocess.run([sys.executable,'-I','-B','-m','venv','--without-pip','--copies',str(environment)],
        check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    code='''
import importlib.util,json,sys
from pathlib import Path
assert all(importlib.util.find_spec(name) is None for name in ('jsonschema','yaml','rfc8785'))
repo=Path(sys.argv[1]);sys.path.insert(0,str(repo/'PULSE_safe_pack_v0/tools'))
import verify_q2_release_host_tokenizer_v0 as S
S.initialize_modules(repo)
C=S.independent
raw=C.io.encode(C.request_for(repo,sys.argv[2]))
assert C.check_request(repo,raw,C.io.digest(raw),sys.argv[2])['source_commit']==sys.argv[2]
assert C.main(['replay','--repo-root',str(repo),'--evidence',str(repo),'--inputs',str(repo)])==2
print('clean_bootstrap_request_verified')
'''
    process=subprocess.run([str(environment/'bin/python'),'-I','-B','-c',code,str(repo),revision],
        check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    assert process.stdout==b'clean_bootstrap_request_verified\n'
    assert process.stderr==b'q2_replay_environment\n'


def test_fresh_verifier_empty_directories_are_removed_without_following_links(tmp_path):
    verifier=tmp_path/'verifier';(verifier/'include/python3.11').mkdir(parents=True)
    (verifier/'lib').mkdir();(verifier/'lib/bound.py').write_bytes(b'preserved bytes')
    external=tmp_path/'external';(external/'empty').mkdir(parents=True)
    (verifier/'linked').symlink_to(external,target_is_directory=True)
    S.prune_empty_verifier_directories(verifier)
    assert not (verifier/'include').exists() and (external/'empty').is_dir()
    assert (verifier/'linked').is_symlink() and (verifier/'lib/bound.py').read_bytes()==b'preserved bytes'


def test_actual_unsupported_host_fails_before_any_native_or_transport_work(monkeypatch):
    p = C.load_profile(ROOT)
    if Path("/proc/1/comm").read_text().strip() == "systemd":
        monkeypatch.setattr(S.platform, "python_version", lambda: "0.0.0")
    with pytest.raises(C.io.IntakeError): S.host_record({"ImageVersion":"20261004.327.1"}, p)


@pytest.fixture
def receipt_fixture(committed, prior, tmp_path, monkeypatch):
    """Explicit synthetic kernel/transport records; real source and metric check.

    Archive transport/origin validation is isolated here; the native production
    path has no fixture flag or alternative input contract.
    """
    repo, revision = committed; p = C.load_profile(repo)
    evidence = tmp_path / 'receipt'; evidence.mkdir()
    request_raw = C.io.encode(C.request_for(repo, revision))
    sources = C.source_closure(repo, revision, C.Budget(180))
    projection = {'record_type':'q2_tokenizer_projection_v0','trees':{}}
    row = {'path':'fixture.bin','origin':'input:fixture','archive_mode':None,'kind':'file',
           'uid':0,'gid':65534,'mode':0o440,'size_bytes':1,'sha256':'a'*64}
    for tree in ('inputs','capsule','historical','verifier'): projection['trees'][tree]=[dict(row)]
    projection['trees']['source']=[{'path':r['path'],'origin':'source:'+r['path'],'archive_mode':None,
        'kind':'file','uid':0,'gid':65534,'mode':0o440,'size_bytes':r['size_bytes'],'sha256':r['sha256']} for r in sources]
    projection_raw=C.io.encode(projection)
    root=Path('/var/lib/pulse-q2-tokenizer-fixture1/projection')
    pre={'record_type':'q2_tokenizer_prelaunch_v0','scope':C.SCOPE,
        'binding':{'repository':C.REPOSITORY,'workflow':C.WORKFLOW,'source_commit':revision,'run_id':'123456',
                   'run_attempt':1,'job_name':'verify_host','job_id':'234567'},
        'request_sha256':C.io.digest(request_raw),'source_bindings':sources,'inputs':p['inputs'],
        'projection_root':str(root),'projection_sha256':C.io.digest(projection_raw),'bootstrap_lib_sha256':'b'*64,
        'occurrences':C.execution_plan(root,C.io.digest(projection_raw),p),'phase_start_ns':1_000_000_000,
        'phase_deadline_ns':1201_000_000_000,'claims':C.CLAIMS}
    pre_sha=C.io.digest(C.io.encode(pre))
    input_report={'record_type':'q2_native_tokenizer_input_check_v0','occurrence_id':'input_check',
        'prelaunch_sha256':pre_sha,'projection_sha256':pre['projection_sha256'],'inputs':p['inputs'],**C.CLAIMS}
    token_report={'record_type':'q2_native_tokenizer_check_v0','occurrence_id':'tokenizer_check','prelaunch_sha256':pre_sha,
        'verified_calls':150,'groups_sha256':p['historical_output_sha256']['groups.json'],
        'manifest_sha256':p['historical_output_sha256']['dataset-manifest.json'],'runtime_versions':p['runtime_versions'],
        'tokenizer_class':'FixtureTokenizerFast','tokenizer_module':'lib/python3.11/site-packages/transformers/fixture.py',
        'configuration_sha256':p['configuration_sha256'],**C.CLAIMS}
    hashes=p['historical_output_sha256']
    outputs=[{'input-check.json':C.io.digest(C.io.encode(input_report))},
             {'tokenizer-check.json':C.io.digest(C.io.encode(token_report)),**{n:hashes[n] for n in ('groups.json','dataset-manifest.json')}},
             {'summary.json':hashes['summary.json']},{'summary-check.json':hashes['summary-check.json']}]
    occurrences=[]
    for i,declared in enumerate(pre['occurrences']):
        unit='pulse-q2-'+chr(ord('a')+i)*24+'-'+declared['stage']+'.service'
        obs=prior.synthetic_sandbox()
        old_unit=obs['unit']
        def replace(value):
            if isinstance(value,str):return value.replace(old_unit,unit)
            if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
            if isinstance(value,list):return [replace(v) for v in value]
            return value
        obs=replace(obs);obs['stage']=declared['stage'];obs['pid']=10000+i;obs['properties']['RuntimeMaxUSec']='3min'
        bindings=[]
        for binding in declared['input_bindings']:
            producer=binding['producer'];digest=binding['sha256']
            if digest is None:digest=outputs[C.OCCURRENCES.index(producer)][binding['name']]
            bindings.append({**binding,'sha256':digest})
        cleanup={'unit':unit,'properties':{'LoadState':'not-found','ActiveState':'inactive','ControlGroup':''},
                 'cgroup_empty_or_removed':True,'client_reaped':True}
        tick=(2+i*2)*1_000_000_000
        occurrences.append({'id':declared['id'],'status':'completed','argv':declared['argv'],
            'expected_exit':declared['expected_exit'],'exit_code':declared['expected_exit'],'unit':unit,'pid':obs['pid'],
            'launch_ns':tick,'isolation_observed_ns':tick+5,'exec_ns':tick+10,'exit_ns':tick+20,
            'cleanup_ns':tick+30,'output_frozen_ns':tick+40,'stdout_eof':True,
            'isolation':obs,'cleanup':cleanup,'input_bindings':bindings,'projection_after_sha256':pre['projection_sha256'],
            'outputs':outputs[i]})
    old=p['archived_platform_requirements'];host={**old,'kernel':'fixture-other-kernel','runner_image':'20261011.1'}
    result={'schema_version':'q2_release_host_tokenizer_result_v0','status':'native_tokenizer_verified','scope':C.SCOPE,
        'binding':pre['binding'],'source_bindings':sources,'inputs':p['inputs'],'request_sha256':pre['request_sha256'],
        'prelaunch_sha256':pre_sha,'projection_sha256':pre['projection_sha256'],'phase_start_ns':pre['phase_start_ns'],
        'phase_deadline_ns':pre['phase_deadline_ns'],'occurrences':occurrences,'host':host,
        'archived_platform_requirements':old,'platform_matches':{k:host[k]==old[k] for k in old},
        'full_archived_platform_match':False,'metrics':p['historical_metrics'],'claims':C.CLAIMS,
        'cleanup':'verified_removed','independent_check':'evidence_reconstructed','clock_relation':'not_verified',
        'resource_measurement':'unavailable'}
    documents={'request.json':request_raw,'prelaunch.json':C.io.encode(pre),'projection.json':projection_raw,
               'input-check.json':C.io.encode(input_report),'tokenizer-check.json':C.io.encode(token_report),'result.json':C.io.encode(result)}
    for name,raw in documents.items():(evidence/name).write_bytes(raw)
    fixture_dir=tmp_path/'metric-fixture';fixture_dir.mkdir()
    f=prior.capture_synthetic.__wrapped__(fixture_dir)
    import base64
    for response,_ready in f['records'][:3]:
        response.update(new_token_ids=[41]*32,stop_reason='token_limit',text='alternate',text_utf8_base64=base64.b64encode(b'alternate').decode())
    groups,manifest=prior.capture_reconstruct(f)
    g=fixture_dir/'groups.json';m=fixture_dir/'dataset-manifest.json';g.write_bytes(groups);m.write_bytes(manifest)
    builder=C.import_bound(repo,C.io.REDUCER)
    summary=C.io.encode(builder.build(g,m,C.io.digest(groups),C.io.digest(manifest)))
    raw={'groups.json':groups,'dataset-manifest.json':manifest,'summary.json':summary}
    monkeypatch.setattr(C,'verify_archives',lambda *_args:({'fixture_transport_only':True},raw))
    monkeypatch.setattr(C,'check_projection_origins',lambda *_args:None)
    return repo,evidence,result,token_report


def test_complete_fixture_receipt_preserves_negative_and_platform_drift(receipt_fixture):
    repo,evidence,result,_=receipt_fixture
    assert C.validate_receipt(repo,evidence,evidence)==result
    assert result['full_archived_platform_match'] is False and result['claims']['full_release_host_verified'] is False


@pytest.mark.parametrize('fault',['missing','duplicate','reordered','argv','wrong_exit','timeout','no_eof','leftover_cgroup',
    'unreaped','property_only','uid','netns','pid','extra_observation','wrong_producer','different_input','changed_projection',
    'false_platform','false_full_host','model_loaded','worker_launch','fresh_inference','authority','metric_pass','source','extra_output','extra_artifact','extra_field'])
def test_fixture_receipt_rejects_incomplete_or_overstated_evidence(receipt_fixture,fault):
    repo,evidence,result,_=receipt_fixture;result=copy.deepcopy(result);occ=result['occurrences'][1]
    if fault=='missing':result['occurrences'].pop()
    elif fault=='duplicate':result['occurrences'][2]=copy.deepcopy(occ)
    elif fault=='reordered':result['occurrences'][0],result['occurrences'][1]=result['occurrences'][1],result['occurrences'][0]
    elif fault=='argv':occ['argv'][0]='/usr/bin/python'
    elif fault=='wrong_exit':result['occurrences'][2]['exit_code']=0
    elif fault=='timeout':occ['exit_ns']=result['phase_deadline_ns']+1
    elif fault=='no_eof':occ['stdout_eof']=False
    elif fault=='leftover_cgroup':occ['cleanup']['cgroup_empty_or_removed']=False
    elif fault=='unreaped':occ['cleanup']['client_reaped']=False
    elif fault=='property_only':occ['isolation']={'properties':occ['isolation']['properties']}
    elif fault=='uid':occ['isolation']['uid']=0
    elif fault=='netns':occ['isolation']['child_netns']=occ['isolation']['host_netns']
    elif fault=='pid':occ['pid']+=9
    elif fault=='extra_observation':occ['isolation']['self_reported']=True
    elif fault=='wrong_producer':result['occurrences'][2]['input_bindings'][0]['producer']='summary_builder'
    elif fault=='different_input':result['occurrences'][2]['input_bindings'][0]['sha256']='0'*64
    elif fault=='changed_projection':occ['projection_after_sha256']='0'*64
    elif fault=='false_platform':result['platform_matches']['kernel']=True
    elif fault=='false_full_host':result['claims']['full_release_host_verified']=True
    elif fault=='model_loaded':result['claims']['model_weights_loaded']=True
    elif fault=='worker_launch':result['claims']['worker_launch_executed']=True
    elif fault=='fresh_inference':result['claims']['current_inference_count']=150
    elif fault=='authority':result['claims']['authority_effect']='ALLOW'
    elif fault=='metric_pass':result['claims']['historical_metric_pass']=True
    elif fault=='source':result['source_bindings'][0]['sha256']='0'*64
    elif fault=='extra_output':result['occurrences'][0]['outputs']['unexpected.json']='0'*64
    elif fault=='extra_artifact':(evidence/'unexpected.json').write_bytes(b'{}\n')
    else:result['production_certificate']={}
    (evidence/'result.json').write_bytes(C.io.encode(result))
    with pytest.raises((C.io.IntakeError,ValueError,KeyError)):C.validate_receipt(repo,evidence,evidence)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
