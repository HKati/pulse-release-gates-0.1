"""Offline SEC-OG-01 tests. Pushes use disposable local bare repos only.

No GitHub credentials, project commits, Actions dispatch or external network.
Pillow is not a CI test dependency: generation choreography uses a narrow test
substitute; real PNG/CRC/decompression and Git mutation boundaries execute.
"""
from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import types
import zlib

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/make_og_write_boundary_v0.py"
SPEC = importlib.util.spec_from_file_location("og_boundary_under_test", TOOL)
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)
TEST_PATH = "tests/test_make_og_write_boundary_v0.py"


def chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)


def png(width=1200, height=630, *, pixel=b"\x10\x20\x30", filter_byte=0):
    rows = (bytes([filter_byte]) + pixel * width) * height
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def environment(sha="a" * 40):
    return {
        "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": B.REPOSITORY, "GITHUB_REPOSITORY_ID": B.REPOSITORY_ID,
        "GITHUB_REPOSITORY_OWNER": B.OWNER, "GITHUB_REPOSITORY_OWNER_ID": B.OWNER_ID,
        "GITHUB_ACTOR": B.OWNER, "GITHUB_ACTOR_ID": B.OWNER_ID,
        "GITHUB_TRIGGERING_ACTOR": B.OWNER, "GITHUB_REF": B.REF,
        "GITHUB_REF_TYPE": "branch", "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_WORKFLOW_REF": B.REPOSITORY + "/" + B.WORKFLOW + "@" + B.REF,
        "GITHUB_SHA": sha, "GITHUB_WORKFLOW_SHA": sha,
        "GITHUB_RUN_ID": "123456", "GITHUB_RUN_ATTEMPT": "1",
    }


def event():
    return {"repository": {"id": int(B.REPOSITORY_ID), "full_name": B.REPOSITORY,
                           "default_branch": "main", "fork": False,
                           "owner": {"id": int(B.OWNER_ID), "login": B.OWNER}},
            "sender": {"id": int(B.OWNER_ID), "login": B.OWNER}, "ref": B.REF,
            "inputs": {"source": "hero_dark_4k.png", "bgcolor": "#000000"}}


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("SEC-OG-01 offline test attempted networking")
    monkeypatch.setattr(socket.socket, "connect", reject)
    original = B.git
    def confined_git(repo, *args, **kwargs):
        if "push" in args:
            # Production keeps a fixed HTTPS URL; only the test monkeypatches
            # the module constant to a disposable local fixture destination.
            assert B.REMOTE.startswith("/") and Path(B.REMOTE).is_dir()
            assert "github.com" not in B.REMOTE
        return original(repo, *args, **kwargs)
    monkeypatch.setattr(B, "git", confined_git)


def fixture_git(repo, *args):
    command = ["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
               "-c", "user.name=Synthetic Fixture", "-c", "user.email=fixture@example.invalid",
               "-C", str(repo), *args]
    p = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=B.git_env(), check=False)
    assert p.returncode == 0, p.stderr.decode()
    return p.stdout.decode().strip()


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / "source"; repo.mkdir()
    fixture_git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("Synthetic isolated fixture, not project history.\n")
    fixture_git(repo, "add", "README.md")
    fixture_git(repo, "commit", "-q", "-m", "Synthetic root")
    (repo / "hero_dark_4k.png").write_bytes(png(3, 2))
    (repo / B.OUTPUT).write_bytes(png(pixel=b"\x01\x02\x03"))
    (repo / "tools").mkdir()
    (repo / "tools/make_og_write_boundary_v0.py").write_bytes(TOOL.read_bytes())
    fixture_git(repo, "add", ".")
    fixture_git(repo, "commit", "-q", "-m", "Synthetic source")
    base = fixture_git(repo, "rev-parse", "HEAD")
    context = B.authorised_context(environment(base), event())
    candidate = tmp_path / "candidate"; candidate.mkdir()
    image = png()
    source, blob = B.checkout_source(repo, context)
    (candidate / B.OUTPUT).write_bytes(image)
    (candidate / B.RECEIPT).write_bytes(B.encode(B.receipt(context, source, blob, image)))
    return repo, context, candidate, image


def test_authorised_owner_main_exact_workflow_source():
    context = B.authorised_context(environment(), event())
    assert context["source_sha"] == context["workflow_sha"] == "a" * 40
    assert context["actor_id"] == B.OWNER_ID


def test_authorised_owner_rerun_has_a_new_attempt_identity():
    env = environment(); env["GITHUB_RUN_ATTEMPT"] = "2"
    assert B.authorised_context(env, event())["run_attempt"] == "2"


@pytest.mark.parametrize("key", list(environment()))
@pytest.mark.parametrize("mutation", ["missing", "mismatched"])
def test_context_fields_fail_closed(key, mutation):
    env = environment()
    if mutation == "missing": env.pop(key)
    else: env[key] = "incorrect"
    with pytest.raises(B.BoundaryError): B.authorised_context(env, event())


@pytest.mark.parametrize("sha", ["", "0"*40, "a"*39, "a"*41, "A"*40, "g"*40, "a"*40+"\n"])
def test_invalid_source_revision(sha):
    with pytest.raises(B.BoundaryError): B.authorised_context(environment(sha), event())


@pytest.mark.parametrize("value", ["0", "01", "-1", "1\n", "1,2", "9"*21])
@pytest.mark.parametrize("key", ["GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"])
def test_invalid_run_identity(key, value):
    env = environment(); env[key] = value
    with pytest.raises(B.BoundaryError): B.authorised_context(env, event())


@pytest.mark.parametrize("path,value", [
    (("repository", "id"), 1), (("repository", "id"), True),
    (("repository", "full_name"), "other/repo"), (("repository", "fork"), True),
    (("repository", "default_branch"), "other"), (("repository", "owner", "id"), 1),
    (("repository", "owner", "login"), "other"), (("sender", "id"), 1),
    (("sender", "login"), "other"), (("ref",), "refs/heads/other"),
])
def test_event_identity_mismatch(path, value):
    payload = event(); obj = payload
    for key in path[:-1]: obj = obj[key]
    obj[path[-1]] = value
    with pytest.raises(B.BoundaryError): B.authorised_context(environment(), payload)


@pytest.mark.parametrize("source", ["", "/etc/passwd", "../image.png", "a/../image.png",
    ".git/config", "a/.git/config", "a//b.png", "./image.png", "a\\b.png", "x\ny.png", "a"*513])
def test_source_path_rejection(source):
    payload = event(); payload["inputs"]["source"] = source
    with pytest.raises(B.BoundaryError): B.authorised_context(environment(), payload)


@pytest.mark.parametrize("bg", ["", None, True, "a\nb", "a"*129])
def test_invalid_background_input(bg):
    payload = event(); payload["inputs"]["bgcolor"] = bg
    with pytest.raises(B.BoundaryError): B.authorised_context(environment(), payload)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'[]', b'\xff'])
def test_strict_json_rejects(raw):
    with pytest.raises((ValueError, UnicodeError)): B.strict_json(raw)


def test_valid_bundle_is_bound_to_context_source_and_exact_image(repository):
    repo, context, bundle, image = repository
    assert B.validate_bundle(repo, context, bundle, B.sha256(image)) == image


@pytest.mark.parametrize("field", ["source_sha", "run_id", "run_attempt", "workflow_sha", "actor_id",
                                  "triggering_actor", "repository", "ref", "source_path", "bgcolor"])
def test_receipt_cannot_authorise_itself(repository, field):
    repo, context, bundle, image = repository
    record = B.strict_json((bundle / B.RECEIPT).read_bytes())
    record["context"][field] = "substituted"
    (bundle / B.RECEIPT).write_bytes(B.encode(record))
    with pytest.raises(B.BoundaryError, match="candidate_binding"):
        B.validate_bundle(repo, context, bundle, B.sha256(image))


@pytest.mark.parametrize("mutation", ["extra", "missing", "symlink", "hardlink", "digest", "source_blob", "size_bool"])
def test_bundle_shape_and_bytes_rejections(repository, tmp_path, mutation):
    repo, context, bundle, image = repository
    if mutation == "extra": (bundle / "run.sh").write_text("not executable input")
    elif mutation == "missing": (bundle / B.RECEIPT).unlink()
    elif mutation == "symlink":
        (bundle / B.OUTPUT).unlink(); (tmp_path / "outside").write_bytes(image)
        (bundle / B.OUTPUT).symlink_to(tmp_path / "outside")
    elif mutation == "hardlink": os.link(bundle / B.OUTPUT, tmp_path / "linked")
    elif mutation == "digest": (bundle / B.OUTPUT).write_bytes(png(pixel=b"\x55\x66\x77"))
    else:
        record = B.strict_json((bundle / B.RECEIPT).read_bytes())
        if mutation == "source_blob": record["source_git_blob"] = "0"*40
        else: record["output_size"] = True
        (bundle / B.RECEIPT).write_bytes(B.encode(record))
    with pytest.raises((B.BoundaryError, OSError)):
        B.validate_bundle(repo, context, bundle, B.sha256(image))


@pytest.mark.parametrize("mutation", ["changed_source", "extra_staged", "extra_untracked", "symlink_source",
                                     "wrong_head", "redirect_git_config"])
def test_no_commit_on_dirty_or_mismatched_source(repository, mutation):
    repo, context, bundle, image = repository
    before = fixture_git(repo, "rev-parse", "HEAD")
    if mutation == "changed_source": (repo / "hero_dark_4k.png").write_bytes(png(4, 3))
    elif mutation == "extra_staged":
        (repo / "README.md").write_text("unexpected change")
        fixture_git(repo, "add", "README.md")
    elif mutation == "extra_untracked": (repo / "unexpected.txt").write_text("unexpected")
    elif mutation == "symlink_source":
        (repo / "hero_dark_4k.png").unlink(); (repo / "hero_dark_4k.png").symlink_to(B.OUTPUT)
    elif mutation == "wrong_head": context["source_sha"] = "0"*40
    else: fixture_git(repo, "config", "url.https://other.invalid/.insteadOf", "https://github.com/")
    with pytest.raises((B.BoundaryError, OSError)):
        B.prepare_commit(repo, context, bundle, B.sha256(image))
    assert fixture_git(repo, "rev-parse", "HEAD") == before


def test_png_accepts_exact_rgb_canvas():
    B.validate_png(png())


@pytest.mark.parametrize("mutation", ["dimensions", "signature", "crc", "tail", "missing_iend", "metadata",
                                     "truncated", "filter", "oversized_stream", "extra_zlib_stream"])
def test_png_payload_rejections(mutation):
    raw = png()
    if mutation == "dimensions": raw = png(1199, 630)
    elif mutation == "signature": raw = b"not a png" + raw[9:]
    elif mutation == "crc": raw = raw[:29] + bytes([raw[29] ^ 1]) + raw[30:]
    elif mutation == "tail": raw += b"trailing bytes"
    elif mutation == "missing_iend": raw = raw[:-12]
    elif mutation == "metadata": raw = raw[:-12] + chunk(b"tEXt", b"unexpected") + raw[-12:]
    elif mutation == "truncated": raw = raw[:44]
    elif mutation == "filter": raw = png(filter_byte=5)
    else:
        data = zlib.compress(b"\0" * (630 * 3601 + (1 if mutation == "oversized_stream" else 0)))
        if mutation == "extra_zlib_stream": data += zlib.compress(b"tail")
        raw = raw[:33] + chunk(b"IDAT", data) + chunk(b"IEND", b"")
    with pytest.raises((B.BoundaryError, zlib.error)): B.validate_png(raw)


def test_prepare_commit_changes_exactly_one_regular_file(repository):
    repo, context, bundle, image = repository
    commit = B.prepare_commit(repo, context, bundle, B.sha256(image))
    B.validate_commit(repo, context["source_sha"], commit, image)
    assert fixture_git(repo, "diff", "--name-only", context["source_sha"], commit) == B.OUTPUT
    assert (repo / B.OUTPUT).read_bytes() == image


def test_unchanged_output_does_not_create_commit(repository):
    repo, context, bundle, image = repository
    image = (repo / B.OUTPUT).read_bytes()
    source, blob = B.checkout_source(repo, context)
    (bundle / B.OUTPUT).write_bytes(image)
    (bundle / B.RECEIPT).write_bytes(B.encode(B.receipt(context, source, blob, image)))
    assert B.prepare_commit(repo, context, bundle, B.sha256(image)) is None
    assert fixture_git(repo, "rev-parse", "HEAD") == context["source_sha"]


def test_nochange_cli_does_not_need_or_use_push_token(repository, tmp_path):
    repo, context, bundle, image = repository
    image = (repo / B.OUTPUT).read_bytes()
    source, blob = B.checkout_source(repo, context)
    (bundle / B.OUTPUT).write_bytes(image)
    (bundle / B.RECEIPT).write_bytes(B.encode(B.receipt(context, source, blob, image)))
    ev = tmp_path / "event.json"; ev.write_bytes(B.encode(event()))
    summary = tmp_path / "summary.md"
    env = environment(context["source_sha"])
    env.update(PATH=os.defpath, GITHUB_EVENT_PATH=str(ev), GITHUB_WORKSPACE=str(repo),
               GITHUB_STEP_SUMMARY=str(summary), OG_ARTIFACT_ID="123", OG_EXPECTED_SHA256=B.sha256(image))
    p = subprocess.run([sys.executable, "-I", str(repo / "tools/make_og_write_boundary_v0.py"),
                        "write", "--bundle", str(bundle)], env=env, capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr.decode()
    assert b"unchanged_no_commit_no_push" in p.stdout
    assert fixture_git(repo, "rev-parse", "HEAD") == context["source_sha"]


@pytest.mark.parametrize("field,value", [("GITHUB_ACTOR", "other"), ("GITHUB_TRIGGERING_ACTOR", "other"),
                                        ("GITHUB_REF", "refs/heads/other")])
def test_unauthorised_cli_rejects_before_local_commit(repository, tmp_path, field, value):
    repo, context, bundle, image = repository
    ev = tmp_path / "event.json"; ev.write_bytes(B.encode(event()))
    env = environment(context["source_sha"]); env[field] = value
    env.update(PATH=os.defpath, GITHUB_EVENT_PATH=str(ev), GITHUB_WORKSPACE=str(repo),
               OG_ARTIFACT_ID="123", OG_EXPECTED_SHA256=B.sha256(image))
    p = subprocess.run([sys.executable, "-I", str(repo / "tools/make_og_write_boundary_v0.py"),
                        "write", "--bundle", str(bundle)], env=env, capture_output=True, timeout=30)
    assert p.returncode == 1 and b"unauthorised_context" in p.stderr
    assert fixture_git(repo, "rev-parse", "HEAD") == context["source_sha"]


def bare_remote(repository, tmp_path, monkeypatch):
    repo, context, bundle, image = repository
    remote = tmp_path / "remote.git"
    fixture_git(tmp_path, "clone", "--bare", str(repo), str(remote))
    monkeypatch.setattr(B, "REMOTE", str(remote))
    return remote


def test_actual_local_push_moves_only_main_and_never_persists_token(repository, tmp_path, monkeypatch):
    remote = bare_remote(repository, tmp_path, monkeypatch)
    repo, context, bundle, image = repository
    commit = B.prepare_commit(repo, context, bundle, B.sha256(image))
    B.push_commit(repo, context["source_sha"], commit, "synthetic-token-not-a-credential")
    assert fixture_git(remote, "rev-parse", "refs/heads/main") == commit
    assert fixture_git(remote, "for-each-ref", "--format=%(refname)") == B.REF
    assert b"synthetic-token" not in (repo / ".git/config").read_bytes()


@pytest.mark.parametrize("movement", ["advance", "rewind", "delete"])
def test_changed_remote_tip_rejects_without_force_or_retry(repository, tmp_path, monkeypatch, movement):
    remote = bare_remote(repository, tmp_path, monkeypatch)
    repo, context, bundle, image = repository
    if movement == "advance":
        other = tmp_path / "other"
        fixture_git(tmp_path, "clone", str(remote), str(other))
        (other / "README.md").write_text("Concurrent authorized change.\n")
        fixture_git(other, "add", "README.md"); fixture_git(other, "commit", "-q", "-m", "Synthetic concurrent change")
        fixture_git(other, "push", str(remote), "HEAD:" + B.REF)
    elif movement == "rewind":
        parent = fixture_git(remote, "rev-parse", "main^")
        fixture_git(remote, "update-ref", B.REF, parent)
    else: fixture_git(remote, "update-ref", "-d", B.REF)
    before = fixture_git(remote, "for-each-ref", "--format=%(refname) %(objectname)")
    commit = B.prepare_commit(repo, context, bundle, B.sha256(image))
    with pytest.raises(B.BoundaryError, match="push_rejected"):
        B.push_commit(repo, context["source_sha"], commit, "synthetic")
    assert fixture_git(remote, "for-each-ref", "--format=%(refname) %(objectname)") == before


@pytest.mark.parametrize("mutation", ["wrong_old", "wrong_new", "other_ref", "multiple", "empty", "oversized", "other_remote"])
def test_pre_push_hook_exact_update_tuple(tmp_path, mutation):
    old, new, remote = "a"*40, "b"*40, "/synthetic/remote.git"
    path = tmp_path / "hook"; path.write_text(B.pre_push_program(old, new, remote))
    row = f"{new} {new} {B.REF} {old}\n"; args = [remote, remote]
    if mutation == "wrong_old": row = row.replace(old, "c"*40)
    elif mutation == "wrong_new": row = row.replace(new, "c"*40)
    elif mutation == "other_ref": row = row.replace(B.REF, "refs/heads/other")
    elif mutation == "multiple": row += row
    elif mutation == "empty": row = ""
    elif mutation == "oversized": row = row.rstrip() + " " * 5000
    else: args[1] = "/other/remote.git"
    p = subprocess.run([sys.executable, "-I", str(path), *args], input=row.encode(), capture_output=True)
    assert p.returncode == 1


def test_generator_preserves_contain_rgb_canvas_no_crop(repository, tmp_path, monkeypatch):
    repo, context, _, expected_png = repository
    calls = []
    class FakeImage:
        width, height = 900, 630
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def convert(self, mode): calls.append(("convert", mode)); return self
        def paste(self, image, xy): calls.append(("paste", xy))
        def save(self, target, fmt): calls.append(("save", fmt)); target.write(expected_png)
    def open_image(stream):
        assert stream.read() == (repo / context["source_path"]).read_bytes()
        calls.append(("open",)); return FakeImage()
    def contain(image, size): calls.append(("contain", size)); return image
    def new(mode, size, bg): calls.append(("new", mode, size, bg)); return FakeImage()
    pil = types.ModuleType("PIL")
    pil.Image = types.SimpleNamespace(open=open_image, new=new)
    pil.ImageOps = types.SimpleNamespace(contain=contain)
    monkeypatch.setitem(sys.modules, "PIL", pil)
    bundle = tmp_path / "generated"
    record = B.generate(repo, context, bundle)
    assert calls == [("open",), ("convert", "RGB"), ("contain", (1200, 630)),
                     ("new", "RGB", (1200, 630), "#000000"), ("paste", (150, 0)), ("save", "PNG")]
    assert B.validate_bundle(repo, context, bundle, record["output_sha256"]) == expected_png
    assert fixture_git(repo, "rev-parse", "HEAD") == context["source_sha"]


def workflow():
    return yaml.load((ROOT / B.WORKFLOW).read_text(), Loader=yaml.BaseLoader)


def test_workflow_authorisation_precedes_checkout_and_write_job():
    wf = workflow(); assert set(wf["on"]) == {"workflow_dispatch"}
    assert set(wf["on"]["workflow_dispatch"]["inputs"]) == {"source", "bgcolor"}
    jobs = wf["jobs"]; assert set(jobs) == {"generate", "write_image"}
    first = jobs["generate"]["steps"][0]
    assert first["name"] == "Reject unauthorized dispatch before checkout" and "exit 1" in first["run"]
    fragments = ["github.event_name == 'workflow_dispatch'", "github.repository == '" + B.REPOSITORY + "'",
                 "github.repository_id == '" + B.REPOSITORY_ID + "'", "github.repository_owner_id == '" + B.OWNER_ID + "'",
                 "github.actor == 'HKati'", "github.actor_id == '" + B.OWNER_ID + "'",
                 "github.triggering_actor == 'HKati'", "github.ref == 'refs/heads/main'",
                 "github.ref_type == 'branch'", "github.workflow_sha == github.sha",
                 "github.workflow_ref == '" + B.REPOSITORY + "/" + B.WORKFLOW + "@" + B.REF + "'"]
    for guard in (first["env"]["OG_AUTHORIZED"], jobs["write_image"]["if"]):
        assert all(fragment in guard for fragment in fragments)
        assert "||" not in guard
    assert jobs["write_image"]["needs"] == "generate"
    assert "needs.generate.result == 'success'" in jobs["write_image"]["if"]


def test_permissions_are_job_scoped_and_writer_has_no_install_or_pillow():
    wf = workflow()
    assert wf["permissions"] == {"contents": "read"}
    assert wf["jobs"]["generate"]["permissions"] == {"contents": "read"}
    writer = wf["jobs"]["write_image"]
    assert writer["permissions"] == {"contents": "write"}
    commands = "\n".join(step.get("run", "") for step in writer["steps"])
    assert not re.search(r"\bpip\b", commands) and "Pillow" not in commands and " generate " not in commands
    assert commands.count("make_og_write_boundary_v0.py write ") == 1
    assert all("GITHUB_TOKEN" not in step.get("env", {}) for step in writer["steps"][:-1])
    assert wf["concurrency"] == {"group": "make-og-main", "cancel-in-progress": "false"}


def test_exact_checkout_artifact_identity_and_no_cross_run_download():
    wf = workflow(); jobs = wf["jobs"]
    for job in jobs.values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", step["uses"])
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["ref"] == "${{ github.sha }}"
                assert step["with"]["persist-credentials"] == "false"
    steps = jobs["write_image"]["steps"]
    assert "preflight" in steps[1]["run"]
    download = steps[2]["with"]
    assert download["artifact-ids"] == "${{ needs.generate.outputs.artifact_id }}"
    assert download["path"] == "${{ runner.temp }}/og-candidate/"
    assert download["digest-mismatch"] == "error"
    assert not {"github-token", "repository", "run-id", "name", "pattern"} & set(download)
    upload = jobs["generate"]["steps"][-1]["with"]
    assert upload["name"] == "og-image-${{ github.run_id }}-${{ github.run_attempt }}"
    assert upload["if-no-files-found"] == "error" and upload["overwrite"] == "false"
    assert "run_attempt" in upload["name"]


def test_shell_syntax_and_no_direct_expression_interpolation(tmp_path):
    for job in workflow()["jobs"].values():
        for i, step in enumerate(job["steps"]):
            if "run" in step:
                assert "${{" not in step["run"]
                p = tmp_path / f"step-{i}.sh"; p.write_text(step["run"])
                result = subprocess.run(["/bin/bash", "-n", str(p)], capture_output=True)
                assert result.returncode == 0, result.stderr.decode()


def test_registered_exactly_once_in_both_manifests():
    for name in ("tools-tests.list", "pytest-tests.list"):
        entries = [line.split("#", 1)[0].strip() for line in (ROOT / "ci" / name).read_text().splitlines()]
        entries = [entry for entry in entries if entry]
        assert len(entries) == len(set(entries)) and entries.count(TEST_PATH) == 1


def test_git_environment_and_push_have_no_force_or_persisted_token():
    env = B.git_env()
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull and env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert "GITHUB_TOKEN" not in env and "GIT_CONFIG_COUNT" not in env
    source = TOOL.read_text()
    assert '"--force"' not in source and '"--force-with-lease"' not in source
    assert '"--no-verify"' not in source and "remote set-url" not in source
    assert "git commit" not in source.split("def prepare_commit", 1)[1].split("def pre_push_program", 1)[0].replace("git add nor git commit", "")


def test_missing_output_is_created_as_the_only_regular_file(repository):
    repo, context, bundle, image = repository
    fixture_git(repo, "rm", B.OUTPUT)
    fixture_git(repo, "commit", "-q", "-m", "Synthetic absent output baseline")
    context["source_sha"] = fixture_git(repo, "rev-parse", "HEAD")
    context["workflow_sha"] = context["source_sha"]
    source, blob = B.checkout_source(repo, context)
    (bundle / B.RECEIPT).write_bytes(B.encode(B.receipt(context, source, blob, image)))
    commit = B.prepare_commit(repo, context, bundle, B.sha256(image))
    B.validate_commit(repo, context["source_sha"], commit, image)
    assert (repo / B.OUTPUT).read_bytes() == image


def test_index_injection_after_preflight_is_rejected_before_commit(repository, monkeypatch):
    repo, context, bundle, image = repository
    original = B.git
    inserted = False
    def inject(repo_arg, *args, **kwargs):
        nonlocal inserted
        if "hash-object" in args and not inserted:
            inserted = True
            (repo / "README.md").write_text("Unexpected staged change")
            fixture_git(repo, "add", "README.md")
        return original(repo_arg, *args, **kwargs)
    monkeypatch.setattr(B, "git", inject)
    with pytest.raises(B.BoundaryError, match="staged_path_scope"):
        B.prepare_commit(repo, context, bundle, B.sha256(image))
    assert fixture_git(repo, "rev-parse", "HEAD") == context["source_sha"]


@pytest.mark.parametrize("artifact,digest", [("", "a"*64), ("0", "a"*64),
    ("1,2", "a"*64), ("1\n", "a"*64), ("123", ""), ("123", "g"*64)])
def test_bad_artifact_selection_cli_never_creates_a_commit(repository, tmp_path, artifact, digest):
    repo, context, bundle, image = repository
    ev = tmp_path / "event.json"; ev.write_bytes(B.encode(event()))
    env = environment(context["source_sha"])
    env.update(PATH=os.defpath, GITHUB_EVENT_PATH=str(ev), GITHUB_WORKSPACE=str(repo),
               OG_ARTIFACT_ID=artifact, OG_EXPECTED_SHA256=digest)
    result = subprocess.run([sys.executable, "-I", str(repo / "tools/make_og_write_boundary_v0.py"),
                             "write", "--bundle", str(bundle)], env=env, capture_output=True, timeout=30)
    assert result.returncode == 1
    assert fixture_git(repo, "rev-parse", "HEAD") == context["source_sha"]


if __name__ == "__main__":
    raise SystemExit(pytest.main(["-q", "-o", "addopts=", str(Path(__file__).resolve())]))
