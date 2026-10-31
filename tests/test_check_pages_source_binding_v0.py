"""Offline SEC-PAGES-01 regression. No GitHub mutation or external networking.

Git commits, when used, are synthetic fixtures in pytest temporary directories
without remotes. HTTP/ZIP tests exercise production code through local doubles.
"""
from __future__ import annotations

import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import urllib.error
import zipfile

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/check_pages_source_binding_v0.py"
SPEC = importlib.util.spec_from_file_location("pages_binding_under_test", TOOL)
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)
TEST_PATH = "tests/test_check_pages_source_binding_v0.py"
NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)


def repo():
    return {"id": B.REPOSITORY_ID, "full_name": B.REPOSITORY, "fork": False,
            "default_branch": "main", "owner": {"login": B.OWNER, "id": B.OWNER_ID}}


def upstream():
    return {"id": 1234, "repository": repo(), "head_repository": repo(),
            "workflow_id": B.PRODUCER_ID, "path": B.PRODUCER, "name": "PULSE CI",
            "head_branch": "main", "head_sha": "b"*40, "head_commit": {"id": "b"*40},
            "status": "completed", "conclusion": "success", "event": "push", "run_attempt": 1,
            "created_at": "2026-10-29T20:00:00Z", "run_started_at": "2026-10-29T20:00:01Z",
            "updated_at": "2026-10-29T20:05:00Z"}


def environment(sha="a"*40, event="workflow_dispatch"):
    return {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": B.REPOSITORY,
            "GITHUB_REPOSITORY_ID": str(B.REPOSITORY_ID), "GITHUB_REPOSITORY_OWNER": B.OWNER,
            "GITHUB_REPOSITORY_OWNER_ID": str(B.OWNER_ID), "GITHUB_REF": B.REF,
            "GITHUB_REF_TYPE": "branch", "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_API_URL": B.API, "GITHUB_WORKFLOW_REF": f"{B.REPOSITORY}/{B.WORKFLOW}@{B.REF}",
            "GITHUB_SHA": sha, "GITHUB_WORKFLOW_SHA": sha, "GITHUB_EVENT_NAME": event,
            "GITHUB_RUN_ID": "4321", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_ACTOR": B.OWNER,
            "GITHUB_ACTOR_ID": str(B.OWNER_ID), "GITHUB_TRIGGERING_ACTOR": B.OWNER}


def payload(mode="manual_id"):
    data = {"repository": repo(), "sender": {"login": B.OWNER, "id": B.OWNER_ID}, "ref": B.REF}
    if mode == "workflow_run":
        data.update(action="completed", workflow_run=upstream())
    else:
        data["inputs"] = {"run_id": "1234" if mode == "manual_id" else "",
                          "cancel_pages_deployment_id": ""}
    return data


def zip_bytes(items=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in (items or [("report/report_card.html", b"<head></head>report"),
                                       ("report/status.json", b'{"synthetic":true}'),
                                       ("badges/test.svg", b"<svg/>")]):
            archive.writestr(name, content)
    return stream.getvalue()


def artifact(data):
    return {"id": 5678, "name": "pulse-report", "expired": False,
            "size_in_bytes": len(data), "digest": "sha256:" + B.digest_bytes(data),
            "created_at": "2026-10-29T20:02:00Z", "updated_at": "2026-10-29T20:02:00Z",
            "expires_at": "2027-01-27T20:02:00Z",
            "workflow_run": {"id": 1234, "repository_id": B.REPOSITORY_ID,
                             "head_repository_id": B.REPOSITORY_ID, "head_branch": "main", "head_sha": "b"*40}}


class Service:
    def __init__(self):
        self.run = upstream(); self.data = zip_bytes(); self.art = artifact(self.data)
        self.calls = []; self.downloads = []; self.list_extra = []; self.after_download = None
        self.commit_sha = "b"*40; self.latest = None

    def get(self, path):
        self.calls.append(path)
        if path == f"{B.PREFIX}/actions/runs/1234":
            return copy.deepcopy(self.run)
        if path.startswith(f"{B.PREFIX}/actions/workflows/{B.PRODUCER_ID}/runs?"):
            return {"workflow_runs": copy.deepcopy(self.latest if self.latest is not None else [self.run])}
        if path.startswith(f"{B.PREFIX}/actions/runs/1234/artifacts?"):
            rows = [self.art] + self.list_extra
            return {"total_count": len(rows), "artifacts": copy.deepcopy(rows)}
        if path == f"{B.PREFIX}/actions/artifacts/5678":
            return copy.deepcopy(self.art)
        if path == f"{B.PREFIX}/git/commits/" + "b"*40:
            return {"sha": self.commit_sha, "tree": {"sha": "c"*40}}
        raise AssertionError("Unexpected read path: " + path)

    def download(self, artifact_id, target, expected_size):
        assert artifact_id == 5678 and expected_size == len(self.data)
        self.downloads.append(artifact_id); target.write_bytes(self.data)
        if self.after_download:
            self.after_download(self)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("Offline test attempted networking")
    monkeypatch.setattr(socket.socket, "connect", reject)


def execute(tmp_path, mode="manual_id", service=None):
    service = service or Service()
    env = environment(event="workflow_run" if mode == "workflow_run" else "workflow_dispatch")
    event = payload(mode); ctx = B.context(env, event)
    result = B.acquire(service, ctx, event, tmp_path/"state", tmp_path/"artifact", NOW)
    return service, ctx, result


@pytest.mark.parametrize("mode", ["manual_id", "latest", "workflow_run"])
def test_three_authorized_routes_download_exact_id_then_recheck(tmp_path, mode):
    api, ctx, result = execute(tmp_path, mode)
    assert api.downloads == [5678]
    assert result["publisher"]["source_sha"] != result["upstream"]["head_sha"]
    assert result["authority_effect"] == "none"
    assert result["artifact"]["artifact_run_attempt"] is None
    assert result["artifact"]["attempt_evidence"] == "creation_window_only_no_artifact_attempt_id"
    assert B.recheck(api, ctx, tmp_path/"state", tmp_path/"artifact", NOW) == result
    assert (tmp_path/"artifact/report/status.json").read_bytes() == b'{"synthetic":true}'
    assert all("/branches/main" not in call for call in api.calls)  # historical main allowed


@pytest.mark.parametrize("key", list(environment()))
def test_missing_manual_publisher_context_rejected(key):
    env = environment(); del env[key]
    with pytest.raises(B.BindingError):
        B.context(env, payload())


@pytest.mark.parametrize("key,value", [
    ("GITHUB_REF", "refs/heads/topic"), ("GITHUB_REF", "refs/tags/main"),
    ("GITHUB_REPOSITORY", "fork/pulse-release-gates-0.1"), ("GITHUB_REPOSITORY_ID", "1"),
    ("GITHUB_REPOSITORY_OWNER_ID", "1"), ("GITHUB_ACTOR", "someone"),
    ("GITHUB_ACTOR_ID", "1"), ("GITHUB_TRIGGERING_ACTOR", "someone"),
    ("GITHUB_SHA", "b"*40), ("GITHUB_WORKFLOW_SHA", "b"*40),
    ("GITHUB_WORKFLOW_REF", f"{B.REPOSITORY}/{B.WORKFLOW}@refs/heads/topic"),
    ("GITHUB_EVENT_NAME", "pull_request_target"), ("GITHUB_API_URL", "https://attacker.invalid"),
    ("GITHUB_RUN_ID", "1\nverified=true"), ("GITHUB_RUN_ATTEMPT", "0")])
def test_wrong_manual_context_rejected(key, value):
    env = environment(); env[key] = value
    with pytest.raises(B.BindingError):
        B.context(env, payload())


@pytest.mark.parametrize("key,value", [("id", 1), ("id", True), ("full_name", "other/repo"), ("fork", True)])
@pytest.mark.parametrize("where", ["repository", "head_repository"])
def test_fork_or_wrong_upstream_repository_fails_before_download(tmp_path, where, key, value):
    api = Service(); api.run[where][key] = value
    with pytest.raises(B.BindingError):
        execute(tmp_path, service=api)
    assert not api.downloads and not (tmp_path/"state").exists()


@pytest.mark.parametrize("key,value", [
    ("id", 4321), ("id", True), ("workflow_id", 1), ("workflow_id", None),
    ("path", ".github/workflows/other.yml"), ("name", "other"),
    ("status", "in_progress"), ("conclusion", "failure"), ("event", "pull_request"),
    ("event", "workflow_dispatch"), ("head_branch", "topic"), ("head_sha", ""),
    ("head_sha", "a"*40), ("head_commit", {}), ("run_attempt", 0), ("run_attempt", True),
    ("created_at", None), ("run_started_at", "2026-10-29T20:06:00Z"),
    ("updated_at", "2026-10-29T19:00:00Z")])
def test_invalid_producer_never_downloads(tmp_path, key, value):
    api = Service(); api.run[key] = value
    with pytest.raises(B.BindingError):
        execute(tmp_path, service=api)
    assert not api.downloads


@pytest.mark.parametrize("key", list(upstream()))
def test_missing_producer_field_fails_closed(key):
    run = upstream(); del run[key]
    with pytest.raises(B.BindingError):
        B.validate_run(run, 1234)


@pytest.mark.parametrize("key,value", [
    ("id", True), ("name", "other"), ("expired", True), ("expired", None),
    ("size_in_bytes", 0), ("size_in_bytes", B.MAX_ZIP+1), ("digest", None),
    ("digest", "md5:"+"a"*32), ("digest", "sha256:"+"g"*64),
    ("created_at", "2026-10-29T19:59:59Z"), ("updated_at", "2026-10-29T20:06:00Z"),
    ("expires_at", "2026-10-29T20:03:00Z"), ("workflow_run", {})])
def test_invalid_artifact_never_downloads(tmp_path, key, value):
    api = Service(); api.art[key] = value
    with pytest.raises(B.BindingError):
        execute(tmp_path, service=api)
    assert not api.downloads


@pytest.mark.parametrize("key", list(artifact(zip_bytes())))
def test_missing_artifact_field_rejected(key):
    row = artifact(zip_bytes()); del row[key]
    with pytest.raises(B.BindingError):
        B.validate_artifact(row, B.validate_run(upstream(), 1234), NOW)


@pytest.mark.parametrize("key,value", [("id", 99), ("repository_id", 1), ("head_repository_id", 1),
                                      ("head_branch", "topic"), ("head_sha", "d"*40)])
def test_artifact_must_belong_to_exact_run_repository_and_commit(tmp_path, key, value):
    api = Service(); api.art["workflow_run"][key] = value
    with pytest.raises(B.BindingError):
        execute(tmp_path, service=api)
    assert not api.downloads


def test_ambiguous_same_name_artifacts_fail_before_download(tmp_path):
    api = Service(); extra = copy.deepcopy(api.art); extra["id"] = 999
    api.list_extra = [extra]
    with pytest.raises(B.BindingError, match="ambiguous"):
        execute(tmp_path, service=api)
    assert not api.downloads


def test_run_list_mismatch_never_falls_back_to_next_run(tmp_path):
    api = Service(); bad = upstream(); bad["event"] = "pull_request"
    api.latest = [bad, upstream()]
    with pytest.raises(B.BindingError):
        execute(tmp_path, "latest", api)
    assert not api.downloads


def test_payload_api_disagreement_rejected(tmp_path):
    api = Service(); api.run["run_attempt"] = 2
    with pytest.raises(B.BindingError, match="event_api"):
        execute(tmp_path, "workflow_run", api)
    assert not api.downloads


def test_commit_response_mismatch_rejected(tmp_path):
    api = Service(); api.commit_sha = "d"*40
    with pytest.raises(B.BindingError, match="commit_mismatch"):
        execute(tmp_path, service=api)
    assert not api.downloads


@pytest.mark.parametrize("value", ["../123", "1/../../pages", "0", "01", "-1", "1\nkey=value", "1;true", "1?x=y", True])
def test_manual_run_id_not_an_api_or_output_injection(value):
    ev = payload(); ev["inputs"]["run_id"] = value
    with pytest.raises(B.BindingError):
        B.select_run(Service(), B.context(environment(), payload()), ev)


@pytest.mark.parametrize("value", ["../deploy", "1/cancel", "1?x=y", "x"*40, "0", "1\nkey=value", True])
def test_cancel_id_must_be_canonical_decimal_or_sha(value):
    ev = payload(); ev["inputs"]["cancel_pages_deployment_id"] = value
    with pytest.raises(B.BindingError):
        B.select_run(Service(), B.context(environment(), payload()), ev)


@pytest.mark.parametrize("value", ["12345", "a"*40])
def test_valid_cancel_id_is_recorded_not_executed(tmp_path, value):
    api = Service(); ev = payload(); ev["inputs"]["cancel_pages_deployment_id"] = value
    ctx = B.context(environment(), ev)
    result = B.acquire(api, ctx, ev, tmp_path/"state", tmp_path/"artifact", NOW)
    assert result["cancel_pages_deployment_id"] == value
    assert all("pages/deployments" not in p for p in api.calls)


def test_rerun_has_observed_attempt_not_invented_artifact_attempt(tmp_path):
    api = Service(); api.run["run_attempt"] = 2
    api.run["run_started_at"] = "2026-10-29T20:01:00Z"
    _, _, result = execute(tmp_path, service=api)
    assert result["upstream"]["run_attempt"] == 2
    assert result["artifact"]["artifact_run_attempt"] is None


@pytest.mark.parametrize("time", ["2026-10-29T20:00:50Z", "2026-10-29T20:01:00Z"])
def test_previous_or_ambiguous_attempt_artifact_rejected(tmp_path, time):
    api = Service(); api.run["run_attempt"] = 2; api.run["run_started_at"] = "2026-10-29T20:01:00Z"
    api.art["created_at"] = time
    with pytest.raises(B.BindingError):
        execute(tmp_path, service=api)
    assert not api.downloads


@pytest.mark.parametrize("mutation", ["run_attempt", "run_sha", "artifact_digest", "artifact_id", "expired", "duplicate"])
def test_post_download_api_drift_rejected_without_extraction(tmp_path, mutation):
    api = Service()
    def mutate(service):
        if mutation == "run_attempt": service.run["run_attempt"] = 2
        if mutation == "run_sha": service.run["head_sha"] = "d"*40
        if mutation == "artifact_digest": service.art["digest"] = "sha256:"+"d"*64
        if mutation == "artifact_id": service.art["workflow_run"]["id"] = 999
        if mutation == "expired": service.art["expired"] = True
        if mutation == "duplicate": service.list_extra = [copy.deepcopy(service.art)]
    api.after_download = mutate
    with pytest.raises(B.BindingError):
        execute(tmp_path, service=api)
    assert not (tmp_path/"state").exists() and not (tmp_path/"artifact").exists()


def test_wrong_zip_digest_rejected_before_extraction(tmp_path):
    api = Service(); api.art["digest"] = "sha256:" + "0"*64
    with pytest.raises(B.BindingError, match="digest_mismatch"):
        execute(tmp_path, service=api)
    assert not (tmp_path/"artifact").exists() and not (tmp_path/"state").exists()


@pytest.mark.parametrize("change", ["content", "extra", "symlink", "zip", "publisher", "api"])
def test_final_revalidation_detects_drift(tmp_path, change):
    api, ctx, _ = execute(tmp_path)
    if change == "content": (tmp_path/"artifact/report/status.json").write_text("changed")
    if change == "extra": (tmp_path/"artifact/extra").write_text("extra")
    if change == "symlink": (tmp_path/"artifact/link").symlink_to(tmp_path/"state/binding.json")
    if change == "zip": (tmp_path/"state/pulse-report.zip").write_bytes(b"wrong")
    if change == "publisher": ctx["source_sha"] = "c"*40
    if change == "api": api.run["conclusion"] = "failure"
    with pytest.raises(B.BindingError):
        B.recheck(api, ctx, tmp_path/"state", tmp_path/"artifact", NOW)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/../../escape", "a//x", "a/./b", "a\\b",
                                  ".git/config", "a/.git/config", "a/$(touch nope)", "a/`id`", "a/quote\"",
                                  "a/line\nvalue", "C:/escape", "a/semicolon;x"])
def test_unsafe_zip_names_never_extracted(tmp_path, name):
    p = tmp_path/"bad.zip"; p.write_bytes(zip_bytes([(name, b"bad")]))
    with pytest.raises(B.BindingError):
        B.extract(p, tmp_path/"output")
    assert not (tmp_path/"output").exists()


@pytest.mark.parametrize("kind", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK])
def test_zip_special_files_rejected(tmp_path, kind):
    info = zipfile.ZipInfo("unsafe"); info.create_system = 3; info.external_attr = (kind | 0o777) << 16
    p = tmp_path/"bad.zip"; p.write_bytes(zip_bytes([(info, b"outside")]))
    with pytest.raises(B.BindingError, match="special_file"):
        B.extract(p, tmp_path/"output")
    assert not (tmp_path/"output").exists()


@pytest.mark.parametrize("items", [[("a", b"1"), ("a", b"2")], [("a", b"1"), ("A", b"2")],
                                   [("a", b"1"), ("a/b", b"2")]])
def test_zip_duplicate_or_file_directory_alias_rejected(tmp_path, items):
    p = tmp_path/"bad.zip"; p.write_bytes(zip_bytes(items))
    with pytest.raises(B.BindingError):
        B.extract(p, tmp_path/"output")
    assert not (tmp_path/"output").exists()


def test_zip_resource_limits_before_unpacking(tmp_path, monkeypatch):
    p = tmp_path/"data.zip"; p.write_bytes(zip_bytes())
    monkeypatch.setattr(B, "MAX_EXPANDED", 1)
    with pytest.raises(B.BindingError, match="size_limit"):
        B.extract(p, tmp_path/"output")
    assert not (tmp_path/"output").exists()


def test_existing_destination_is_not_removed(tmp_path):
    output = tmp_path/"artifact"; output.mkdir(); (output/"keep").write_text("keep")
    with pytest.raises(B.BindingError): execute(tmp_path)
    assert (output/"keep").read_text() == "keep"


@pytest.mark.parametrize("data", [b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}', b'{"x":NaN}', b'[]', b'bad'])
def test_duplicate_or_invalid_json_rejected(data):
    with pytest.raises(B.BindingError): B.decode(data)


@pytest.mark.parametrize("url", ["http://x.blob.core.windows.net/a", "https://evil.invalid/a",
    "https://x.blob.core.windows.net.evil.invalid/a", "https://token@x.blob.core.windows.net/a",
    "https://x.blob.core.windows.net:444/a", "https://127.0.0.1/a", "https://x.blob.core.windows.net/a#f"])
def test_storage_redirect_is_bounded(url):
    with pytest.raises(B.BindingError): B.storage_url(url)


def test_download_token_only_goes_to_github(tmp_path):
    client = B.GitHubReadOnly("SYNTHETIC_TOKEN")
    data = b"zip-placeholder"; seen = []
    class Response(io.BytesIO):
        status = 200
    class Opener:
        def open(self, request, timeout):
            seen.append(request)
            if len(seen) == 1:
                raise urllib.error.HTTPError(request.full_url, 302, "Found", {
                    "Location": "https://example.blob.core.windows.net/artifact?sig=synthetic"}, None)
            return Response(data)
    client.opener = Opener()
    client.download(5678, tmp_path/"zip", len(data))
    assert all(request.get_method() == "GET" for request in seen)
    assert seen[0].get_header("Authorization") == "Bearer SYNTHETIC_TOKEN"
    assert seen[1].get_header("Authorization") is None
    assert (tmp_path/"zip").read_bytes() == data


def test_api_redirect_not_followed_and_network_error_fails_closed():
    client = B.GitHubReadOnly("SYNTHETIC_TOKEN")
    class Opener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(request.full_url, 302, "Found", {"Location": "https://evil.invalid"}, None)
    client.opener = Opener()
    with pytest.raises(B.BindingError): client.get(B.PREFIX+"/actions/runs/1234")
    assert B.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://evil.invalid") is None


def test_paginated_artifact_list_is_complete_and_stable():
    rows = [{"id": i+1} for i in range(101)]
    class Paged:
        def get(self, path):
            return {"total_count": 101, "artifacts": rows[:100] if path.endswith("&page=1") else rows[100:]}
    assert len(B.list_artifacts(Paged(), 1234)) == 101
    class Truncated:
        def get(self, path): return {"total_count": 101, "artifacts": rows[:99]}
    with pytest.raises(B.BindingError, match="truncated"): B.list_artifacts(Truncated(), 1234)


def git(root, *args):
    result = subprocess.run(["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
        "-c", "user.name=Synthetic Fixture", "-c", "user.email=fixture@example.invalid", "-C", str(root), *args],
        env={"PATH":os.defpath,"HOME":str(root),"GIT_CONFIG_NOSYSTEM":"1","GIT_CONFIG_GLOBAL":os.devnull},
        capture_output=True, check=False, timeout=30)
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout.decode().strip()


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path/"synthetic"; root.mkdir(); git(root, "init", "-q")
    for name in (B.WORKFLOW, B.SELF):
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT/name).read_bytes())
    git(root,"add","."); git(root,"commit","-qm","Synthetic fixture only")
    return root, B.context(environment(git(root,"rev-parse","HEAD")),payload())


def test_exact_checkout_is_read_only(checkout):
    root, ctx = checkout; before=git(root,"rev-parse","HEAD")
    B.check_checkout(root,ctx)
    assert not git(root,"status","--porcelain") and git(root,"rev-parse","HEAD")==before
    assert not git(root,"remote")


@pytest.mark.parametrize("mutation", ["sha", "workflow", "tool", "symlink"])
def test_checkout_identity_rejects_drift(checkout, mutation):
    root, ctx = checkout
    if mutation == "sha": ctx["source_sha"] = "d"*40
    if mutation == "workflow": (root/B.WORKFLOW).write_text("changed")
    if mutation == "tool": (root/B.SELF).write_text("changed")
    if mutation == "symlink":
        (root/B.SELF).unlink(); (root/B.SELF).symlink_to(root/B.WORKFLOW)
    with pytest.raises(B.BindingError): B.check_checkout(root,ctx)


def workflow():
    return yaml.safe_load((ROOT/B.WORKFLOW).read_text())


# Filled from the byte-verified 72e8973e54d8f94422c0dabb264b8316ac8e4de6 baseline.
PRESERVED_STEP_HASHES = {'Prepare Pages site': 'efac5ba747f6ea71f526ac3218e0d03f714bc1e306edf7c272ef0c5a73898653', 'Publish schemas to Pages output': 'ca41ec553a4d844bed596d644912a66dae52c4ad00db4626ef4f3dc8846dfe20', 'Verify schema assets present before upload': 'aeea91f2d507d6d31c84ace517051a57b32d7a460858e99e2cbb0d7914f3347d', 'Generate diagnostics landing page': '61fb6d30692125a8536af036560eec749d3dab668ae29ed688608e971e7003c2', 'Generate diagnostics manifest': '7965e39cc5bd5478e5dd0f8178319fd2129bd3ed77d78c38a1ba75d1a540126a', 'Verify crawler assets present before upload': '0cdbab0358105a5d7bc1b089a39b6191c883ba96b27082ddeaebfc7bfbcf2c0d', 'Workflow summary (Pages publish)': '4a1fe217293510da2ee4278944f8bd379ed6d1a5368ab03c2b641efe9d2d9861', 'Setup Pages': '499f0d06dffaaaf6d921fdb2b0d0d31fb11f37355ac6e85564c65569acca858d', 'Check published Quality Ledger status parity': '8e34a1b7db2431c18d17a4c9e4211566107a986ee1f2c2bc2bf579c32e4241b9', 'Upload Pages artifact': '577a2ce47a69b34030420be0f2a29d46c58c3477bd37e065fa110b91eb4224e2', 'Deploy to GitHub Pages': '3c7b4f1fe115aab6feed935d5fa75c36537c8e18067fd363a98795ad472d6ac4', 'SEO smoke (post-deploy)': '4039f00088acd2e879308f3272e11dec6082bf0753f2566508c2782497b87017'}


@pytest.mark.parametrize("name", list(PRESERVED_STEP_HASHES))
def test_existing_site_and_publication_step_unchanged(name):
    steps = {s["name"]:s for s in workflow()["jobs"]["deploy"]["steps"]}
    assert B.digest_bytes(B.encode(steps[name])) == PRESERVED_STEP_HASHES[name]


def test_all_three_routes_must_pass_binding_before_processing_and_mutation():
    wf = workflow(); steps = wf["jobs"]["deploy"]["steps"]; names = [s["name"] for s in steps]
    assert names[0] == "Checkout trusted publisher source"
    assert names[1] == "Verify and acquire bound pulse-report"
    assert steps[1]["id"] == "runid" and " acquire" in steps[1]["run"]
    assert "if" not in steps[1] and not steps[1].get("continue-on-error", False)
    assert names.index("Verify and acquire bound pulse-report") < names.index("Prepare Pages site")
    assert names.index("Revalidate publication source before Pages setup") < names.index("Setup Pages")
    assert names.index("Check published Quality Ledger status parity") < names.index("Upload Pages artifact")
    assert names.index("Upload Pages artifact") < names.index("Revalidate publication source before deployment")
    assert names.index("Revalidate publication source before deployment") < names.index("Cancel stuck Pages deployment (manual helper)") < names.index("Deploy to GitHub Pages")
    assert all("dawidd6/action-download-artifact" not in s.get("uses","") for s in steps)
    cancel = steps[names.index("Cancel stuck Pages deployment (manual helper)")]
    assert "success()" in cancel["if"] and "workflow_dispatch" in cancel["if"]
    assert " -L -X POST" not in cancel["run"]


def test_permissions_and_publisher_checkout_are_not_broadened():
    wf=workflow(); job=wf["jobs"]["deploy"]
    assert wf["permissions"] == {"contents":"read","actions":"read","pages":"write","id-token":"write"}
    assert "permissions" not in job
    assert wf["concurrency"] == {"group":"github-pages","cancel-in-progress":False}
    step=job["steps"][0]
    assert step["with"] == {"repository":B.REPOSITORY,"ref":"${{ github.workflow_sha }}","persist-credentials":False}
    assert "github.workflow_sha == github.sha" in job["if"]
    assert "github.ref == 'refs/heads/main'" in job["if"]
    assert "github.repository_id == '1061766508'" in job["if"]
    assert "github.actor == 'HKati'" in job["if"]
    source=TOOL.read_text()
    assert 'method="GET"' in source
    assert not re.search(r'method=["\'](POST|PUT|PATCH|DELETE)',source)
    commands = {node.args[0].value for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "git" and node.args and isinstance(node.args[0], ast.Constant)}
    assert commands == {"rev-parse", "status", "show"}


def test_every_shell_block_parses(tmp_path):
    for i, step in enumerate(workflow()["jobs"]["deploy"]["steps"]):
        if "run" not in step: continue
        script = re.sub(r"\$\{\{.*?\}\}", "fixture", step["run"])
        path=tmp_path/f"{i}.sh"; path.write_text(script)
        result=subprocess.run(["/bin/bash","-n",str(path)],capture_output=True)
        assert result.returncode==0, (step["name"],result.stderr.decode())


@pytest.mark.parametrize("name,count", [("tools-tests.list",174),("pytest-tests.list",30)])
def test_registered_once_and_all_existing_entries_preserved(name,count):
    values=[s.split("#",1)[0].strip() for s in (ROOT/"ci"/name).read_text().splitlines()]
    values=[s for s in values if s]
    assert len(values)==len(set(values))==count and values.count(TEST_PATH)==1
    assert all(re.fullmatch(r"(?:tests|tools|ci)/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.py", value)
               for value in values), "CI manifest contains a non-Python path or merge remnant"
    assert values.count("tests/test_q3_preflight_preservation_v0.py")==1
    assert values.count("tests/test_make_og_write_boundary_v0.py")==1
    assert values.count("tests/test_anchor_integrity_v0_1_contract.py")==1


@pytest.mark.parametrize("name,count", [("tools-tests.list",174),("pytest-tests.list",30)])
@pytest.mark.parametrize("remnant", ["security/sec-pages-01-binding-36f8ff5", "main",
                                     "<<<<<<< branch", "=======", ">>>>>>> main"])
def test_manifest_rejects_merge_remnants_even_when_count_matches(tmp_path, monkeypatch, name, count, remnant):
    raw=(ROOT/"ci"/name).read_text()
    assert raw.count("tests/test_exporters.py\n")==1
    target=tmp_path/"ci"/name;target.parent.mkdir()
    target.write_text(raw.replace("tests/test_exporters.py\n",remnant+"\n"))
    # Preserve the declared count: rejection must not depend on count drift.
    monkeypatch.setattr(sys.modules[__name__],"ROOT",tmp_path)
    with pytest.raises(AssertionError,match="non-Python path or merge remnant"):
        test_registered_once_and_all_existing_entries_preserved(name,count)


@pytest.mark.parametrize("name,count", [("tools-tests.list",174),("pytest-tests.list",30)])
def test_manifest_cannot_drop_q3_while_keeping_pages_and_count(tmp_path, monkeypatch, name, count):
    raw=(ROOT/"ci"/name).read_text()
    q3="tests/test_q3_preflight_preservation_v0.py\n"
    assert raw.count(q3)==1
    target=tmp_path/"ci"/name;target.parent.mkdir()
    target.write_text(raw.replace(q3,"tests/missing_q3_placeholder.py\n"))
    monkeypatch.setattr(sys.modules[__name__],"ROOT",tmp_path)
    with pytest.raises(AssertionError):
        test_registered_once_and_all_existing_entries_preserved(name,count)


def test_python_311_grammar_and_all_count_consumers_updated():
    ast.parse(TOOL.read_text(),feature_version=(3,11))
    consumers = ["test_q2_reference_acquisition_v0.py","test_q2_hosted_intake_workflow_v0.py",
        "test_pulsemech_compute_bounded_execution_v0.py","test_pulsemech_compute_current_run_export_candidate_workflow_v0.py",
        "test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py",
        "test_q2_release_host_tokenizer_v0.py","test_q2_release_host_tokenizer_workflow_v0.py",
        "test_q2_release_host_worker_v0.py","test_q3_native_capture_workflow_v0.py"]
    for name in consumers:
        text=(ROOT/"tests"/name).read_text()
        assert len(re.findall(r"==\s*174\b",text))==1,name
        assert not re.search(r"==\s*(?:169|170|171|172)\b",text),name
        ast.parse(text,feature_version=(3,11))
    for name in ("test_q2_release_host_tokenizer_workflow_v0.py","test_q2_release_host_worker_v0.py"):
        assert r"==\s*174\b" in (ROOT/"tests"/name).read_text()


@pytest.mark.parametrize("mode", ["manual_id", "latest", "workflow_run"])
def test_cli_acquire_and_recheck_with_exact_local_checkout(checkout, monkeypatch, mode):
    root, ctx = checkout
    env = environment(ctx["source_sha"], "workflow_run" if mode == "workflow_run" else "workflow_dispatch")
    event_path = root/"event.json"; event_path.write_bytes(B.encode(payload(mode)))
    output = root/"outputs.txt"
    env.update(GITHUB_WORKSPACE=str(root), GITHUB_EVENT_PATH=str(event_path),
               GITHUB_OUTPUT=str(output), GH_TOKEN="SYNTHETIC_TOKEN")
    for key, value in env.items(): monkeypatch.setenv(key, value)
    monkeypatch.chdir(root)
    api = Service()
    def client(token):
        assert token == "SYNTHETIC_TOKEN"
        return api
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return NOW
    monkeypatch.setattr(B, "GitHubReadOnly", client)
    monkeypatch.setattr(B, "datetime", Clock)
    assert B.main(["acquire"]) == 0
    assert output.read_text() == ("run_id=1234\nartifact_id=5678\n"
                                  "cancel_pages_deployment_id=\nsource_verified=true\n")
    record = B.decode((root/"_pages_binding/binding.json").read_bytes())
    assert record["publisher"]["source_sha"] == ctx["source_sha"]
    assert record["upstream"]["head_sha"] == "b"*40
    assert B.main(["recheck"]) == 0
    assert api.downloads == [5678]
    assert not git(root, "remote") and git(root, "rev-parse", "HEAD") == ctx["source_sha"]
    assert not git(root, "status", "--porcelain", "--untracked-files=no")


@pytest.mark.parametrize("mutation", ["actor", "branch", "sha", "workflow", "path", "event_missing"])
def test_cli_bad_identity_or_path_has_no_api_call_or_verified_output(checkout, monkeypatch, mutation):
    root, ctx = checkout
    env = environment(ctx["source_sha"])
    event_path = root/"event.json"; event_path.write_bytes(B.encode(payload()))
    output = root/"outputs.txt"
    env.update(GITHUB_WORKSPACE=str(root), GITHUB_EVENT_PATH=str(event_path),
               GITHUB_OUTPUT=str(output), GH_TOKEN="SYNTHETIC_TOKEN")
    args = ["acquire"]
    if mutation == "actor": env["GITHUB_ACTOR"] = "someone"
    if mutation == "branch": env["GITHUB_REF"] = "refs/heads/topic"
    if mutation == "sha": env["GITHUB_SHA"] = env["GITHUB_WORKFLOW_SHA"] = "d"*40
    if mutation == "workflow": (root/B.WORKFLOW).write_text("modified")
    if mutation == "path": args += ["--destination", "../outside"]
    if mutation == "event_missing": event_path.unlink()
    for key, value in env.items(): monkeypatch.setenv(key, value)
    monkeypatch.chdir(root)
    def forbidden_client(token): raise AssertionError("Rejected context reached network client")
    monkeypatch.setattr(B, "GitHubReadOnly", forbidden_client)
    assert B.main(args) == 1
    assert not output.exists()
    assert not (root/"_pages_binding").exists() and not (root/"_artifact").exists()


if __name__ == "__main__":
    os.environ.pop("PYTEST_ADDOPTS", None)
    os.environ.pop("PYTEST_PLUGINS", None)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    raise SystemExit(pytest.main(["-q", "-o", "addopts=", str(Path(__file__).resolve())]))
