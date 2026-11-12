"""Bounded synthetic tests; no fixture constitutes a verified observation."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import acquire_pulsemech_compute_admission_rejection_v0 as acquire
from tools import build_pulsemech_compute_admission_rejection_v0 as build

SOURCE = "a" * 40
RUN = 12345
PREFIX = acquire.PREFIX


def _json(value):
    return build.canonical_bytes(value)


def _zip(members=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, raw in (members or {"evidence.json": b"{}\n"}).items():
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            archive.writestr(info, raw)
    return output.getvalue()


def _plan(tmp_path):
    folder = tmp_path / "plan"
    folder.mkdir()
    (folder / "input").mkdir()
    request = _json({"evaluation_identity": {"repository": build.REPOSITORY,
        "source_commit": SOURCE, "workflow": build.WORKFLOW_PATH,
        "event": "workflow_dispatch", "ref": "refs/heads/main"}})
    (folder / "input/q2_request.json").write_bytes(request)
    plan = {
        "format": build.FORMAT, "profile_id": build.PROFILE_ID, "authority_effect": "none",
        "source": {"repository": build.REPOSITORY, "commit": SOURCE,
                   "workflow_path": build.WORKFLOW_PATH, "workflow_sha256": build.WORKFLOW_SHA256,
                   "policy_sha256": build.POLICY_SHA256},
        "request": {"path": "input/q2_request.json", "bytes": len(request),
                    "sha256": hashlib.sha256(request).hexdigest()},
        "limits": dict(build.LIMITS),
        "dispatch": {"event": "workflow_dispatch", "ref": "refs/heads/main",
                     "strict_external_evidence": True, "llamaguard_evidence_mode": "hosted_full_runtime"},
    }
    path = folder / "plan.json"
    path.write_bytes(_json(plan))
    return path


def _run(**changes):
    result = {"id": RUN, "run_attempt": 1, "repository": {"full_name": build.REPOSITORY},
              "head_repository": {"full_name": build.REPOSITORY}, "head_sha": SOURCE,
              "head_branch": "main", "event": "workflow_dispatch", "path": build.WORKFLOW_PATH,
              "status": "completed", "conclusion": "failure", "workflow_id": 123,
              "created_at": "2020-01-01T00:00:00Z", "updated_at": "2020-01-01T00:05:00Z"}
    result.update(changes)
    return result


def _job(identifier, *, skipped=False):
    return {"id": identifier, "run_id": RUN, "run_attempt": 1, "head_sha": SOURCE,
            "status": "completed", "conclusion": "skipped" if skipped else "failure",
            "steps": [] if skipped else [{"number": 1, "name": "example", "conclusion": "failure"}]}


def _artifact(identifier, raw, **changes):
    result = {"id": identifier, "name": "synthetic-evidence-" + str(identifier),
              "size_in_bytes": len(raw), "expired": False,
              "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
              "workflow_run": {"id": RUN, "head_sha": SOURCE}}
    result.update(changes)
    return result


class RecordedGet:
    def __init__(self, calls):
        self.calls = list(calls)
        self.seen = []

    def get(self, endpoint, maximum):
        self.seen.append(endpoint)
        assert self.calls, "unexpected GET"
        expected, body = self.calls.pop(0)
        assert endpoint == expected
        if isinstance(body, BaseException):
            raise body
        assert len(body) <= maximum
        return body


def _calls(*, jobs=None, archive=None, artifact=None, after=None):
    jobs = [_job(11), _job(12, skipped=True)] if jobs is None else jobs
    archive = _zip() if archive is None else archive
    artifact = _artifact(21, archive) if artifact is None else artifact
    values = [
        (f"{PREFIX}/actions/runs/{RUN}", _json(_run())),
        (f"{PREFIX}/actions/runs/{RUN}/attempts/1/jobs?per_page=100&page=1", _json({"total_count": len(jobs), "jobs": jobs})),
        (f"{PREFIX}/actions/runs/{RUN}/artifacts?per_page=100&page=1", _json({"total_count": 1, "artifacts": [artifact]})),
    ]
    for job in jobs:
        if job["steps"] or job["conclusion"] != "skipped":
            values.append((f"{PREFIX}/actions/jobs/{job['id']}/logs", b"2020-01-01T00:00:00Z actual retained log\n"))
    values.extend([(f"{PREFIX}/actions/artifacts/{artifact['id']}/zip", archive),
                   (f"{PREFIX}/actions/runs/{RUN}/attempts/1/jobs?per_page=100&page=1", _json({"total_count": len(jobs), "jobs": jobs})),
                   (f"{PREFIX}/actions/runs/{RUN}/artifacts?per_page=100&page=1", _json({"total_count": 1, "artifacts": [artifact]})),
                   (f"{PREFIX}/actions/runs/{RUN}", _json(_run() if after is None else after))])
    return values


def _manifest(folder):
    return json.loads((folder / "acquisition.json").read_text())


def test_failed_terminal_run_is_preserved_without_semantic_acceptance(tmp_path):
    plan = _plan(tmp_path)
    network = RecordedGet(_calls())
    result = acquire.acquire(plan, RUN, 1, tmp_path / "out", network)
    assert result["completed"] is True and result["errors"] == []
    assert result["authority_effect"] == "none"
    assert "verified" not in result and "accepted" not in result
    assert json.loads((tmp_path / "out/api/run.json").read_bytes())["conclusion"] == "failure"
    assert not (tmp_path / "out/logs/12.txt").exists()
    assert network.calls == []
    for item in result["files"]:
        raw = (tmp_path / "out" / item["path"]).read_bytes()
        assert item["bytes"] == len(raw)
        assert item["sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("changes,code", [
    ({"head_sha": "b" * 40}, "run_source_mismatch"),
    ({"run_attempt": 2}, "run_attempt_mismatch"),
    ({"status": "in_progress", "conclusion": None}, "terminal_run_required"),
    ({"event": "pull_request"}, "run_workflow_mismatch"),
    ({"repository": {"full_name": "stranger/repository"}}, "run_repository_mismatch"),
    ({"head_repository": None}, "run_repository_mismatch"),
])
def test_rejected_run_metadata_is_saved_before_interpretation(tmp_path, changes, code):
    plan = _plan(tmp_path)
    body = _json(_run(**changes))
    network = RecordedGet([(f"{PREFIX}/actions/runs/{RUN}", body)])
    with pytest.raises(acquire.AcquisitionError, match=code):
        acquire.acquire(plan, RUN, 1, tmp_path / "out", network)
    assert (tmp_path / "out/api/run.json").read_bytes() == body
    manifest = _manifest(tmp_path / "out")
    assert manifest["completed"] is False and manifest["errors"] == [code]
    assert len(manifest["files"]) == 1


def test_full_raw_pagination_and_extra_artifacts_are_retained(tmp_path):
    plan = _plan(tmp_path)
    zip1, zip2 = _zip(), _zip({"additional.txt": b"unexpected output must remain inspectable"})
    jobs = [_job(11), _job(12, skipped=True)]
    arts = [_artifact(21, zip1), _artifact(22, zip2)]
    calls = [(f"{PREFIX}/actions/runs/{RUN}", _json(_run()))]
    for page, job in enumerate(jobs, 1):
        calls.append((f"{PREFIX}/actions/runs/{RUN}/attempts/1/jobs?per_page=100&page={page}",
                      _json({"total_count": 2, "jobs": [job]})))
    for page, artifact in enumerate(arts, 1):
        calls.append((f"{PREFIX}/actions/runs/{RUN}/artifacts?per_page=100&page={page}",
                      _json({"total_count": 2, "artifacts": [artifact]})))
    calls.extend([(f"{PREFIX}/actions/jobs/11/logs", b"raw log\n"),
                  (f"{PREFIX}/actions/artifacts/21/zip", zip1),
                  (f"{PREFIX}/actions/artifacts/22/zip", zip2)])
    calls.extend(calls[1:5])
    calls.append((f"{PREFIX}/actions/runs/{RUN}", _json(_run())))
    result = acquire.acquire(plan, RUN, 1, tmp_path / "out", RecordedGet(calls))
    assert result["completed"] is True
    assert (tmp_path / "out/api/jobs-002.json").is_file()
    assert (tmp_path / "out/api/artifacts-002.json").is_file()
    assert (tmp_path / "out/archives/22.zip").read_bytes() == zip2


@pytest.mark.parametrize("second,code", [
    ({"total_count": 2, "jobs": [_job(11)]}, "duplicate_paginated_id"),
    ({"total_count": 3, "jobs": [_job(12)]}, "page_total_changed"),
    ({"total_count": 2, "jobs": []}, "pagination_truncated"),
])
def test_pagination_failures_preserve_both_raw_pages(tmp_path, second, code):
    plan = _plan(tmp_path)
    calls = [(f"{PREFIX}/actions/runs/{RUN}", _json(_run())),
             (f"{PREFIX}/actions/runs/{RUN}/attempts/1/jobs?per_page=100&page=1", _json({"total_count": 2, "jobs": [_job(11)]})),
             (f"{PREFIX}/actions/runs/{RUN}/attempts/1/jobs?per_page=100&page=2", _json(second))]
    with pytest.raises(acquire.AcquisitionError, match=code):
        acquire.acquire(plan, RUN, 1, tmp_path / "out", RecordedGet(calls))
    assert (tmp_path / "out/api/jobs-002.json").read_bytes() == _json(second)
    assert _manifest(tmp_path / "out")["completed"] is False


def test_unavailable_log_preserves_prior_raw_pages(tmp_path):
    plan = _plan(tmp_path)
    calls = _calls()
    calls[3] = (calls[3][0], acquire.AcquisitionError("github_get_http_404"))
    with pytest.raises(acquire.AcquisitionError, match="github_get_http_404"):
        acquire.acquire(plan, RUN, 1, tmp_path / "out", RecordedGet(calls))
    assert len(_manifest(tmp_path / "out")["files"]) == 3


@pytest.mark.parametrize("changes,code", [
    ({"digest": "sha256:" + "0" * 64}, "artifact_digest_mismatch"),
    ({"size_in_bytes": 1}, "artifact_size_mismatch"),
    ({"digest": None}, "artifact_digest_missing"),
])
def test_archive_is_retained_before_integrity_rejection(tmp_path, changes, code):
    plan = _plan(tmp_path)
    raw = _zip()
    artifact = _artifact(21, raw, **changes)
    with pytest.raises(acquire.AcquisitionError, match=code):
        acquire.acquire(plan, RUN, 1, tmp_path / "out", RecordedGet(_calls(archive=raw, artifact=artifact)))
    assert (tmp_path / "out/archives/21.zip").read_bytes() == raw
    assert _manifest(tmp_path / "out")["completed"] is False


def test_malformed_archive_is_preserved_without_extraction_or_acceptance(tmp_path):
    plan = _plan(tmp_path)
    raw = b"not a ZIP: capture first, interpret independently"
    result = acquire.acquire(plan, RUN, 1, tmp_path / "out", RecordedGet(_calls(archive=raw)))
    assert result["completed"] is True
    assert (tmp_path / "out/archives/21.zip").read_bytes() == raw
    assert "verified" not in result


def test_archive_traversal_is_never_extracted_by_collector(tmp_path):
    plan = _plan(tmp_path)
    raw = _zip({"../../outside.txt": b"must not be extracted"})
    acquire.acquire(plan, RUN, 1, tmp_path / "out", RecordedGet(_calls(archive=raw)))
    assert not (tmp_path / "outside.txt").exists()
    assert (tmp_path / "out/archives/21.zip").read_bytes() == raw


def test_run_rerun_during_collection_rejects_after_preserving_bytes(tmp_path):
    plan = _plan(tmp_path)
    with pytest.raises(acquire.AcquisitionError, match="run_attempt_mismatch"):
        acquire.acquire(plan, RUN, 1, tmp_path / "out", RecordedGet(_calls(after=_run(run_attempt=2))))
    assert (tmp_path / "out/api/run_after.json").is_file()
    assert (tmp_path / "out/archives/21.zip").is_file()
    assert _manifest(tmp_path / "out")["completed"] is False


@pytest.mark.parametrize("which,code", [("jobs", "job_inventory_changed"),
                                       ("artifacts", "artifact_inventory_changed")])
def test_inventory_changed_during_collection_is_rejected(tmp_path, which, code):
    plan = _plan(tmp_path)
    calls = _calls()
    position = 5 if which == "jobs" else 6
    payload = json.loads(calls[position][1])
    payload[which][0]["name"] = "changed after collection"
    calls[position] = (calls[position][0], _json(payload))
    with pytest.raises(acquire.AcquisitionError, match=code):
        acquire.acquire(plan, RUN, 1, tmp_path / "out", RecordedGet(calls))
    assert (tmp_path / f"out/api/{which}-after-001.json").read_bytes() == _json(payload)
    assert _manifest(tmp_path / "out")["completed"] is False


def test_fixed_raw_inputs_produce_identical_collections(tmp_path):
    plan = _plan(tmp_path)
    a = acquire.acquire(plan, RUN, 1, tmp_path / "a", RecordedGet(_calls()))
    b = acquire.acquire(plan, RUN, 1, tmp_path / "b", RecordedGet(_calls()))
    assert a == b
    for relative in [x["path"] for x in a["files"]] + ["acquisition.json"]:
        assert (tmp_path / "a" / relative).read_bytes() == (tmp_path / "b" / relative).read_bytes()


def test_request_change_and_existing_output_are_rejected(tmp_path):
    plan = _plan(tmp_path)
    network = RecordedGet([])
    original = (plan.parent / "input/q2_request.json").read_bytes()
    (plan.parent / "input/q2_request.json").write_bytes(original + b" ")
    with pytest.raises(acquire.AcquisitionError, match="request_digest_mismatch"):
        acquire.acquire(plan, RUN, 1, tmp_path / "out", network)
    assert network.seen == []
    (plan.parent / "input/q2_request.json").write_bytes(original)
    (tmp_path / "out").mkdir()
    (tmp_path / "out/retained.txt").write_bytes(b"retain me")
    with pytest.raises(FileExistsError):
        acquire.acquire(plan, RUN, 1, tmp_path / "out", network)
    assert (tmp_path / "out/retained.txt").read_bytes() == b"retain me"


def test_symlink_output_parent_is_rejected(tmp_path):
    plan = _plan(tmp_path)
    (tmp_path / "real").mkdir()
    (tmp_path / "alias").symlink_to(tmp_path / "real", target_is_directory=True)
    with pytest.raises(build.PlanError, match="symlink_path_rejected"):
        acquire.acquire(plan, RUN, 1, tmp_path / "alias/out", RecordedGet([]))
    assert not (tmp_path / "real/out").exists()


def test_duplicate_json_and_nonfinite_numbers_are_rejected():
    with pytest.raises(build.PlanError, match="duplicate_json_key"):
        build.strict_object(b'{"id":1,"id":2}')
    with pytest.raises(build.PlanError, match="nonfinite_json_number"):
        build.strict_object(b'{"id":NaN}')


@pytest.mark.parametrize("target", [
    "http://productionresults.blob.core.windows.net/log",
    "https://api.github.com/actions/run", "https://evil.example/log",
    "https://objects.githubusercontent.com.evil.example/log",
    "https://user:secret@objects.githubusercontent.com/log",
    "https://objects.githubusercontent.com:8443/log", "https://127.0.0.1/log",
])
def test_unsafe_redirect_hosts_and_authorities_rejected(target):
    with pytest.raises(acquire.AcquisitionError, match="unsafe_download_redirect"):
        acquire.GitHubGetTransport._redirect_target(target)


def test_get_transport_never_forwards_authorization_to_storage(monkeypatch):
    observed = []
    responses = [
        (302, {"Location": "https://productionresults.blob.core.windows.net/log?signed=secret"}, b""),
        (200, {"Content-Length": "4"}, b"body"),
    ]

    class Response:
        def __init__(self, spec):
            self.status, self.headers, raw = spec
            self.stream = io.BytesIO(raw)

        def getheader(self, key):
            return self.headers.get(key)

        def read(self, size):
            return self.stream.read(size)

    class Connection:
        sock = None

        def __init__(self, host, **kwargs):
            self.host = host

        def request(self, method, target, headers):
            observed.append((self.host, method, target, dict(headers)))

        def getresponse(self):
            return Response(responses.pop(0))

        def close(self):
            pass

    monkeypatch.setattr(acquire.http.client, "HTTPSConnection", Connection)
    value = acquire.GitHubGetTransport("synthetic-token").get(f"{PREFIX}/actions/jobs/11/logs", 100)
    assert value == b"body"
    assert [x[1] for x in observed] == ["GET", "GET"]
    assert observed[0][3]["Authorization"] == "Bearer synthetic-token"
    assert "Authorization" not in observed[1][3] and "Cookie" not in observed[1][3]


@pytest.mark.parametrize("endpoint", [
    f"{PREFIX}/actions/workflows/pulse_ci.yml/dispatches",
    f"{PREFIX}/actions/runs/{RUN}/rerun", f"{PREFIX}/actions/runs/{RUN}/cancel",
    f"{PREFIX}/actions/runs/latest", "https://api.github.com/user", "repos/other/repo/actions/runs/1",
])
def test_write_and_latest_endpoints_have_no_transport_path(endpoint):
    with pytest.raises(acquire.AcquisitionError, match="unapproved_api_endpoint"):
        acquire.GitHubGetTransport("synthetic-token").get(endpoint, 100)


def test_reviewed_graph_represents_all_147_steps():
    graph = build.expected_graph((ROOT / build.WORKFLOW_PATH).read_bytes())
    assert len(graph) == 8
    counts = {key: sum(s["expected_result"] == key for job in graph for s in job["steps"])
              for key in ("success", "failure", "skipped", "not_instantiated")}
    assert counts == {"success": 37, "failure": 2, "skipped": 90, "not_instantiated": 18}
    assert graph[0]["steps"][16]["expected_result"] == "failure"
    assert graph[3]["steps"][3]["expected_result"] == "failure"
    assert all(s["expected_result"] == "skipped" for s in graph[3]["steps"][4:])
    assert all(s["name"] == s["name"].strip() for job in graph for s in job["steps"])
    with pytest.raises(build.PlanError, match="workflow_not_reviewed"):
        build.expected_graph((ROOT / build.WORKFLOW_PATH).read_bytes() + b"\n")


def test_q2_request_requires_exact_reviewed_source_and_valid_schema():
    keys = ["schemas/q2_release_intake_request_v0.schema.json",
            "PULSE_safe_pack_v0/profiles/q2_reference_release_intake_v0.json",
            "PULSE_safe_pack_v0/profiles/q2_reference_subject_v0.json"]
    sources = {key: (ROOT / key).read_bytes() for key in keys}
    schema = json.loads(sources[keys[0]])
    request = {key: copy.deepcopy(value["const"]) for key, value in schema["properties"].items() if "const" in value}
    request.update({"request_id": "synthetic-only", "evaluation_identity": {
        "repository": build.REPOSITORY, "source_commit": SOURCE, "workflow": build.WORKFLOW_PATH,
        "event": "workflow_dispatch", "ref": "refs/heads/main"}, "release_subject": {
        "repository": build.REPOSITORY, "artifact_id": 1, "archive_size_bytes": 1,
        "archive_sha256": "0" * 64, "capsule_manifest_sha256": "0" * 64,
        "subject_id": "pulsemech-q2-field-extractor-v0",
        "definition_sha256": "688773b81fcf4f105b8770bc2dde9a68baf78aa76224e5c544cd0656109b07a5",
        "layout_profile": "q2_subject_capsule_v0"}})
    assert build.validate_request(_json(request), sources, SOURCE) == request
    with pytest.raises(build.PlanError, match="q2_evaluation_source_mismatch"):
        build.validate_request(_json(request), sources, "b" * 40)
    request["release_subject"]["archive_size_bytes"] = True
    with pytest.raises(build.PlanError, match="q2_request_schema_rejected"):
        build.validate_request(_json(request), sources, SOURCE)


def _git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def test_source_closure_reads_git_objects_not_dirty_worktree(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "source.txt").write_bytes(b"reviewed bytes\n")
    _git(tmp_path, "add", "source.txt")
    _git(tmp_path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-qm", "synthetic fixture")
    source = _git(tmp_path, "rev-parse", "HEAD").decode().strip()
    (tmp_path / "source.txt").write_bytes(b"unreviewed working tree\n")
    _, inventory, values = build.source_snapshot(tmp_path, source)
    assert values["source.txt"] == b"reviewed bytes\n"
    assert inventory[0]["sha256"] == hashlib.sha256(b"reviewed bytes\n").hexdigest()
    (tmp_path / "link").symlink_to("source.txt")
    _git(tmp_path, "add", "link")
    _git(tmp_path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-qm", "synthetic symlink")
    with pytest.raises(build.PlanError, match="nonregular_git_source"):
        build.source_snapshot(tmp_path, _git(tmp_path, "rev-parse", "HEAD").decode().strip())


@pytest.mark.parametrize("raw", [b"not zip", _zip({"../capsule.json": b"{}"}), _zip({"capsule.json": b"not json"})])
def test_builder_rejects_malformed_or_unsafe_capsule_manifest(tmp_path, raw):
    path = tmp_path / "capsule.zip"
    path.write_bytes(raw)
    with pytest.raises(build.PlanError):
        build.capsule_manifest(path)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
