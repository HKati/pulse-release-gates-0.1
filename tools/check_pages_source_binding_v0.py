#!/usr/bin/env python3
"""SEC-PAGES-01: read-only GitHub source binding before Pages processing.

This is a publication boundary, not release authority or artifact attestation.
Only this module's GitHub client performs network I/O; it exposes GET only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPOSITORY = "HKati/pulse-release-gates-0.1"
REPOSITORY_ID = 1061766508
OWNER = "HKati"
OWNER_ID = 128643840
REF = "refs/heads/main"
WORKFLOW = ".github/workflows/publish_report_pages.yml"
SELF = "tools/check_pages_source_binding_v0.py"
PRODUCER = ".github/workflows/pulse_ci.yml"
PRODUCER_ID = 191471316
ARTIFACT = "pulse-report"
API = "https://api.github.com"
PREFIX = f"/repos/{REPOSITORY}"
MAX_ZIP = 100 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024
MAX_FILES = 10000
MAX_JSON = 8 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
NUMBER = re.compile(r"[1-9][0-9]{0,18}\Z")
# These names also remain inert in the legacy shell-based site summaries.
SAFE_NAME = re.compile(r"[A-Za-z0-9_./@+ =,-]+\Z")
SCHEMA = "PULSE_pages_source_binding_v0"


class BindingError(ValueError):
    """A missing, ambiguous or mismatched publication binding."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise BindingError(code)


def integer(value: object, code: str) -> int:
    require(type(value) is int and 0 < value < 2**63, code)
    return value


def decimal(value: object, code: str) -> int:
    require(isinstance(value, str) and NUMBER.fullmatch(value) is not None, code)
    return integer(int(value), code)


def obj(value: object, code: str) -> dict:
    require(isinstance(value, dict), code)
    return value


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), "regular_file_required")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decode(data: bytes) -> dict:
    require(len(data) <= MAX_JSON, "json_size_limit")
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate_json_key")
            out[key] = value
        return out
    def nonfinite(_):
        raise BindingError("nonfinite_json_number")
    try:
        result = json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BindingError("invalid_json") from exc
    return obj(result, "json_object_required")


def timestamp(value: object, code: str) -> datetime:
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value) is not None, code)
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise BindingError(code) from exc


def repository(value: object) -> None:
    data = obj(value, "repository_missing")
    require(integer(data.get("id"), "repository_id_missing") == REPOSITORY_ID, "repository_id_mismatch")
    require(data.get("full_name") == REPOSITORY and data.get("fork") is False, "repository_identity_mismatch")
    owner = obj(data.get("owner"), "owner_missing")
    require(owner.get("login") == OWNER and integer(owner.get("id"), "owner_id_missing") == OWNER_ID, "owner_mismatch")


def owner_actor(value: object) -> None:
    actor = obj(value, "actor_missing")
    require(actor.get("login") == OWNER and integer(actor.get("id"), "actor_id_missing") == OWNER_ID, "actor_not_authorized")


def context(env: dict, event: dict) -> dict:
    expected = {
        "GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_REPOSITORY_ID": str(REPOSITORY_ID), "GITHUB_REPOSITORY_OWNER": OWNER,
        "GITHUB_REPOSITORY_OWNER_ID": str(OWNER_ID), "GITHUB_REF": REF,
        "GITHUB_REF_TYPE": "branch", "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_API_URL": API, "GITHUB_WORKFLOW_REF": f"{REPOSITORY}/{WORKFLOW}@{REF}",
    }
    for key, value in expected.items():
        require(env.get(key) == value, "publisher_context_" + key)
    repository(event.get("repository"))
    require(event["repository"].get("default_branch") == "main", "default_branch_mismatch")
    sha = env.get("GITHUB_SHA", "")
    require(SHA.fullmatch(sha) is not None and env.get("GITHUB_WORKFLOW_SHA") == sha, "publisher_source_mismatch")
    event_name = env.get("GITHUB_EVENT_NAME")
    require(event_name in {"workflow_dispatch", "workflow_run"}, "publisher_event_not_allowed")
    run_id = decimal(env.get("GITHUB_RUN_ID"), "publisher_run_missing")
    attempt = decimal(env.get("GITHUB_RUN_ATTEMPT"), "publisher_attempt_missing")
    if event_name == "workflow_dispatch":
        require(event.get("ref") == REF, "dispatch_ref_mismatch")
        owner_actor(event.get("sender"))
        require(env.get("GITHUB_ACTOR") == OWNER and env.get("GITHUB_ACTOR_ID") == str(OWNER_ID), "dispatch_actor_mismatch")
        require(env.get("GITHUB_TRIGGERING_ACTOR") == OWNER, "dispatch_triggering_actor_not_authorized")
    else:
        require(event.get("action") == "completed", "workflow_run_action_mismatch")
    if attempt > 1:
        require(env.get("GITHUB_TRIGGERING_ACTOR") == OWNER, "publisher_rerun_actor_not_authorized")
    return {"repository": REPOSITORY, "repository_id": REPOSITORY_ID,
            "workflow_path": WORKFLOW, "source_sha": sha, "workflow_sha": sha,
            "run_id": run_id, "run_attempt": attempt, "event": event_name}


def check_checkout(root: Path, publisher: dict) -> None:
    """Read-only Git identity checks, before invoking any upstream artifact code."""
    env = {"PATH": os.defpath, "HOME": str(root), "LC_ALL": "C",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    def git(*args):
        result = subprocess.run(["/usr/bin/git", "-C", str(root), *args], env=env,
                                capture_output=True, check=False, timeout=30)
        require(result.returncode == 0, "checkout_git_read_failed")
        return result.stdout
    require(git("rev-parse", "HEAD").decode().strip() == publisher["source_sha"], "checkout_sha_mismatch")
    require(not git("status", "--porcelain", "--untracked-files=no"), "checkout_tracked_changes")
    for name in (WORKFLOW, SELF):
        path = root / name
        require(path.is_file() and not path.is_symlink(), "trusted_code_not_regular")
        require(path.read_bytes() == git("show", f"{publisher['source_sha']}:{name}"), "trusted_code_mismatch")


def validate_run(data: dict, run_id: int) -> dict:
    repository(data.get("repository")); repository(data.get("head_repository"))
    require(integer(data.get("id"), "upstream_run_missing") == run_id, "upstream_run_id_mismatch")
    require(integer(data.get("workflow_id"), "workflow_id_missing") == PRODUCER_ID, "producer_workflow_id_mismatch")
    require(data.get("path") == PRODUCER and data.get("name") == "PULSE CI", "producer_workflow_path_mismatch")
    require(data.get("status") == "completed" and data.get("conclusion") == "success", "upstream_not_successful")
    require(data.get("event") == "push" and data.get("head_branch") == "main", "upstream_source_not_allowed")
    sha = data.get("head_sha", "")
    require(isinstance(sha, str) and SHA.fullmatch(sha) is not None, "upstream_sha_missing")
    require(obj(data.get("head_commit"), "head_commit_missing").get("id") == sha, "head_commit_mismatch")
    attempt = integer(data.get("run_attempt"), "upstream_attempt_missing")
    times = {key: data.get(key) for key in ("created_at", "run_started_at", "updated_at")}
    parsed = {key: timestamp(value, "run_time_" + key) for key, value in times.items()}
    require(parsed["created_at"] <= parsed["run_started_at"] <= parsed["updated_at"], "run_time_order")
    return {"id": run_id, "workflow_id": PRODUCER_ID, "workflow_path": PRODUCER,
            "repository_id": REPOSITORY_ID, "head_repository_id": REPOSITORY_ID,
            "head_branch": "main", "head_sha": sha, "event": "push",
            "status": "completed", "conclusion": "success", "run_attempt": attempt, **times}


def validate_artifact(data: dict, run: dict, now: datetime) -> dict:
    artifact_id = integer(data.get("id"), "artifact_id_missing")
    require(data.get("name") == ARTIFACT and data.get("expired") is False, "artifact_name_or_expiry")
    size = integer(data.get("size_in_bytes"), "artifact_size_missing")
    require(size <= MAX_ZIP, "artifact_size_limit")
    digest = data.get("digest", "")
    require(isinstance(digest, str) and DIGEST.fullmatch(digest) is not None, "artifact_digest_missing")
    binding = obj(data.get("workflow_run"), "artifact_run_binding_missing")
    for key in ("id", "repository_id", "head_repository_id"):
        require(integer(binding.get(key), "artifact_binding_" + key) == run[key], "artifact_binding_" + key)
    for key in ("head_sha", "head_branch"):
        require(binding.get(key) == run[key], "artifact_binding_" + key)
    created = timestamp(data.get("created_at"), "artifact_creation_missing")
    updated = timestamp(data.get("updated_at"), "artifact_update_missing")
    expires = timestamp(data.get("expires_at"), "artifact_expiration_missing")
    started = timestamp(run["run_started_at"], "run_start_missing")
    completed = timestamp(run["updated_at"], "run_update_missing")
    require(started <= created <= updated <= completed, "artifact_outside_selected_attempt_window")
    # Second-resolution equal timestamps cannot disambiguate two attempts.
    if run["run_attempt"] > 1:
        require(started < created, "ambiguous_rerun_creation_time")
    require(expires > now and expires > created, "artifact_expired")
    return {"id": artifact_id, "name": ARTIFACT, "size_in_bytes": size,
            "digest": digest, "created_at": data["created_at"], "updated_at": data["updated_at"],
            "expires_at": data["expires_at"], "expired": False,
            "workflow_run": {key: binding[key] for key in ("id", "repository_id", "head_repository_id", "head_branch", "head_sha")},
            "artifact_run_attempt": None,
            "attempt_evidence": "creation_window_only_no_artifact_attempt_id"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def storage_url(url: object) -> str:
    require(isinstance(url, str), "archive_location_missing")
    try:
        parts = urllib.parse.urlsplit(url)
        valid = (parts.scheme == "https" and not parts.username and not parts.password
                 and parts.port in (None, 443) and not parts.fragment
                 and parts.hostname is not None
                 and any(parts.hostname.endswith(suffix) for suffix in
                         (".blob.core.windows.net", ".actions.githubusercontent.com")))
    except ValueError as exc:
        raise BindingError("archive_location_invalid") from exc
    require(valid, "archive_location_not_allowed")
    return url


class GitHubReadOnly:
    """No redirect forwarding of Authorization; no POST/PUT/PATCH/DELETE."""
    def __init__(self, token: str):
        require(bool(token) and "\n" not in token and "\r" not in token, "github_token_missing")
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, path: str):
        require(path.startswith(PREFIX + "/") and ".." not in path and "\n" not in path and "\r" not in path, "api_path_invalid")
        return urllib.request.Request(API + path, method="GET", headers={
            "Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"})

    def get(self, path: str) -> dict:
        try:
            with self.opener.open(self.request(path), timeout=30) as response:
                require(response.status == 200, "api_status_not_ok")
                return decode(response.read(MAX_JSON + 1))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise BindingError("github_read_failed") from exc

    def download(self, artifact_id: int, target: Path, expected_size: int) -> None:
        integer(artifact_id, "download_artifact_id")
        location = None
        try:
            with self.opener.open(self.request(f"{PREFIX}/actions/artifacts/{artifact_id}/zip"), timeout=30):
                raise BindingError("archive_redirect_required")
        except urllib.error.HTTPError as exc:
            require(exc.code == 302, "archive_redirect_status")
            location = storage_url(exc.headers.get("Location"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise BindingError("archive_lookup_failed") from exc
        # A new, unauthenticated request: the GitHub token never goes to storage.
        request = urllib.request.Request(location, method="GET", headers={"Accept": "application/octet-stream"})
        try:
            with self.opener.open(request, timeout=60) as response, target.open("xb") as output:
                require(response.status == 200, "archive_download_status")
                count = 0
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    require(count <= expected_size and count <= MAX_ZIP, "archive_download_size_limit")
                    output.write(chunk)
                require(count == expected_size, "archive_download_size_mismatch")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise BindingError("archive_download_failed") from exc


def list_artifacts(api, run_id: int) -> list[dict]:
    rows = []
    total = None
    for page in range(1, 12):
        data = api.get(f"{PREFIX}/actions/runs/{run_id}/artifacts?name={ARTIFACT}&per_page=100&page={page}")
        count = data.get("total_count")
        require(type(count) is int and 0 <= count <= 1000, "artifact_list_count_invalid")
        if total is None:
            total = count
        require(total == count, "artifact_list_changed")
        batch = data.get("artifacts")
        require(isinstance(batch, list) and len(batch) <= 100, "artifact_list_invalid")
        rows.extend(obj(row, "artifact_list_item_invalid") for row in batch)
        require(len(rows) <= total, "artifact_list_count_mismatch")
        if len(rows) == total:
            ids = [integer(row.get("id"), "artifact_list_id_missing") for row in rows]
            require(len(ids) == len(set(ids)), "artifact_list_duplicate_id")
            return rows
        require(len(batch) == 100, "artifact_list_truncated")
    raise BindingError("artifact_list_limit")


def one_artifact(api, run: dict, now: datetime) -> dict:
    rows = [row for row in list_artifacts(api, run["id"]) if row.get("name") == ARTIFACT]
    require(len(rows) == 1, "artifact_missing_or_ambiguous")
    result = validate_artifact(rows[0], run, now)
    exact = validate_artifact(api.get(f"{PREFIX}/actions/artifacts/{result['id']}"), run, now)
    require(exact == result, "artifact_list_detail_mismatch")
    return result


def select_run(api, publisher: dict, event: dict) -> tuple[int, str, str]:
    cancel = ""
    if publisher["event"] == "workflow_run":
        run = obj(event.get("workflow_run"), "workflow_run_payload_missing")
        run_id = integer(run.get("id"), "workflow_run_id_missing")
        validate_run(run, run_id)
        return run_id, "workflow_run", cancel
    inputs = obj(event.get("inputs") or {}, "dispatch_inputs_invalid")
    value = inputs.get("run_id", "")
    require(isinstance(value, str), "dispatch_run_id_invalid")
    raw_cancel = inputs.get("cancel_pages_deployment_id", "")
    require(isinstance(raw_cancel, str), "cancel_id_invalid")
    cancel = raw_cancel.strip()
    require(not cancel or NUMBER.fullmatch(cancel) is not None or SHA.fullmatch(cancel) is not None, "cancel_id_invalid")
    if value.strip():
        return decimal(value.strip(), "dispatch_run_id_invalid"), "manual_id", cancel
    listing = api.get(f"{PREFIX}/actions/workflows/{PRODUCER_ID}/runs?branch=main&event=push&status=success&per_page=50")
    runs = listing.get("workflow_runs")
    require(isinstance(runs, list) and 0 < len(runs) <= 50, "no_successful_main_run")
    # The GitHub API returns newest first; validate it, never skip a bad candidate.
    first = obj(runs[0], "latest_run_invalid")
    run_id = integer(first.get("id"), "latest_run_id_missing")
    validate_run(first, run_id)
    return run_id, "latest_successful_main_push", cancel


def archive_check(path: Path, artifact: dict) -> None:
    require(path.is_file() and not path.is_symlink(), "archive_not_regular")
    require(path.stat().st_size == artifact["size_in_bytes"], "archive_size_mismatch")
    require("sha256:" + file_digest(path) == artifact["digest"], "archive_digest_mismatch")


def safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    require(0 < len(members) <= MAX_FILES, "zip_member_count")
    seen = set(); files = set(); total = 0
    for item in members:
        name = item.filename
        require(item.orig_filename == name and SAFE_NAME.fullmatch(name) is not None, "zip_name_not_safe")
        require(not name.startswith("/") and "\\" not in name, "zip_absolute_path")
        parts = name.rstrip("/").split("/")
        require(all(p and p not in {".", ".."} and p.casefold() != ".git" for p in parts), "zip_path_traversal")
        key = "/".join(parts).casefold()
        require(key not in seen, "zip_duplicate_path")
        seen.add(key)
        require(not item.flag_bits & 1, "zip_encrypted")
        require(item.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}, "zip_compression_not_allowed")
        kind = stat.S_IFMT(item.external_attr >> 16)
        require(kind in ({0, stat.S_IFDIR} if item.is_dir() else {0, stat.S_IFREG}), "zip_special_file")
        require(item.file_size >= 0 and (not item.is_dir() or item.file_size == 0), "zip_size_invalid")
        total += item.file_size
        require(total <= MAX_EXPANDED, "zip_expanded_size_limit")
        if not item.is_dir():
            files.add(key)
    for key in seen:
        parts = key.split("/")
        require(not any("/".join(parts[:i]) in files for i in range(1, len(parts))), "zip_file_directory_collision")
    require(bool(files), "zip_no_files")
    return members


def extract(archive_path: Path, destination: Path) -> list[dict]:
    require(not destination.exists() and not destination.is_symlink(), "artifact_destination_exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        members = safe_members(archive)  # Inspect *all* names before any extraction.
        with tempfile.TemporaryDirectory(prefix=".pages-extract-", dir=destination.parent) as temporary:
            root = Path(temporary) / "payload"; root.mkdir()
            for item in members:
                target = root / item.filename
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                count = 0
                with archive.open(item) as source, target.open("xb") as output:
                    while chunk := source.read(1024 * 1024):
                        count += len(chunk)
                        require(count <= item.file_size, "zip_actual_size_limit")
                        output.write(chunk)
                require(count == item.file_size, "zip_actual_size_mismatch")
                target.chmod(0o644)
            manifest = extracted_manifest(root)
            require(not destination.exists() and not destination.is_symlink(), "artifact_destination_changed")
            root.rename(destination)
            return manifest


def extracted_manifest(root: Path) -> list[dict]:
    require(root.is_dir() and not root.is_symlink(), "artifact_directory_missing")
    result = []
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "extracted_symlink")
        if path.is_dir():
            continue
        require(path.is_file(), "extracted_special_file")
        result.append({"path": path.relative_to(root).as_posix(), "size": path.stat().st_size,
                       "sha256": file_digest(path)})
    return result


def stable_source(api, run: dict, artifact: dict, now: datetime) -> None:
    current = validate_run(api.get(f"{PREFIX}/actions/runs/{run['id']}"), run["id"])
    require(current == run, "upstream_run_changed")
    require(one_artifact(api, current, now) == artifact, "upstream_artifact_changed")


def acquire(api, publisher: dict, event: dict, state: Path, destination: Path, now: datetime) -> dict:
    require(not state.exists() and not state.is_symlink(), "state_destination_exists")
    require(not destination.exists() and not destination.is_symlink(), "artifact_destination_exists")
    run_id, selection, cancel = select_run(api, publisher, event)
    run = validate_run(api.get(f"{PREFIX}/actions/runs/{run_id}"), run_id)
    if publisher["event"] == "workflow_run":
        require(validate_run(event["workflow_run"], run_id) == run, "event_api_run_mismatch")
    commit = api.get(f"{PREFIX}/git/commits/{run['head_sha']}")
    require(commit.get("sha") == run["head_sha"], "upstream_commit_mismatch")
    tree = obj(commit.get("tree"), "upstream_tree_missing").get("sha", "")
    require(isinstance(tree, str) and SHA.fullmatch(tree) is not None, "upstream_tree_missing")
    artifact = one_artifact(api, run, now)
    state.mkdir(parents=True)
    archive = state / "pulse-report.zip"
    try:
        api.download(artifact["id"], archive, artifact["size_in_bytes"])
        archive_check(archive, artifact)
        stable_source(api, run, artifact, now)
        members = extract(archive, destination)
        record = {"schema": SCHEMA, "version": "v0", "authority_effect": "none",
                  "binding_scope": "publication_source_not_release_authority",
                  "selection": selection, "publisher": publisher, "upstream": run,
                  "upstream_tree_sha": tree, "artifact": artifact,
                  "archive_sha256": artifact["digest"].split(":", 1)[1],
                  "extracted_files": members, "cancel_pages_deployment_id": cancel}
        (state / "binding.json").write_bytes(encode(record))
        return record
    except Exception:
        # No receipt or verified output survives a failed acquisition.
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        shutil.rmtree(state)
        raise


def recheck(api, publisher: dict, state: Path, destination: Path, now: datetime) -> dict:
    record = decode((state / "binding.json").read_bytes())
    require(record.get("schema") == SCHEMA and record.get("version") == "v0", "receipt_schema")
    require(record.get("authority_effect") == "none" and record.get("publisher") == publisher, "receipt_publisher_mismatch")
    run = obj(record.get("upstream"), "receipt_run_missing")
    artifact = obj(record.get("artifact"), "receipt_artifact_missing")
    stable_source(api, run, artifact, now)
    archive_check(state / "pulse-report.zip", artifact)
    require(record.get("archive_sha256") == artifact["digest"].split(":", 1)[1], "receipt_digest_mismatch")
    require(record.get("extracted_files") == extracted_manifest(destination), "extracted_content_changed")
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("acquire", "recheck"))
    parser.add_argument("--state", type=Path, default=Path("_pages_binding"))
    parser.add_argument("--destination", type=Path, default=Path("_artifact"))
    args = parser.parse_args(argv)
    try:
        env = dict(os.environ)
        event = decode(Path(env["GITHUB_EVENT_PATH"]).read_bytes())
        publisher = context(env, event)
        root = Path(env["GITHUB_WORKSPACE"]).resolve()
        require(Path.cwd().resolve() == root, "workspace_mismatch")
        # Fixed locations prevent CLI/path drift from reaching the source tree.
        require(args.state == Path("_pages_binding") and args.destination == Path("_artifact"), "output_path_not_allowed")
        check_checkout(root, publisher)
        api = GitHubReadOnly(env.get("GH_TOKEN", ""))
        now = datetime.now(timezone.utc)
        if args.mode == "acquire":
            record = acquire(api, publisher, event, args.state, args.destination, now)
            with Path(env["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
                output.write(f"run_id={record['upstream']['id']}\n")
                output.write(f"artifact_id={record['artifact']['id']}\n")
                output.write(f"cancel_pages_deployment_id={record['cancel_pages_deployment_id']}\n")
                output.write("source_verified=true\n")
        else:
            recheck(api, publisher, args.state, args.destination, now)
        print("Pages publication source binding verified (no release authority).")
        return 0
    except (BindingError, KeyError, OSError, ValueError, zipfile.BadZipFile,
            zipfile.LargeZipFile, RuntimeError, subprocess.SubprocessError) as exc:
        # Do not print exception payloads: they may contain signed URLs or tokens.
        code = str(exc) if isinstance(exc, BindingError) else type(exc).__name__
        print("::error::Pages source binding rejected: " + code, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
