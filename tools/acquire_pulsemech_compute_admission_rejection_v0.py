#!/usr/bin/env python3
"""Collect exact terminal-run evidence with GET requests only.

Collection is not semantic acceptance. Both success and failure runs are
preserved; the independent checker decides whether an observation satisfies
the prospective plan. Interrupted or rejected acquisitions keep their bytes
and receive completed=false in acquisition.json.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import os
from pathlib import Path
import re
import ssl
import sys
import time
from typing import Any, Protocol
from urllib.parse import urlsplit

try:
    from . import build_pulsemech_compute_admission_rejection_v0 as plan_builder
except ImportError:
    import build_pulsemech_compute_admission_rejection_v0 as plan_builder

FORMAT = "pulsemech_compute_admission_rejection_acquisition_v0"
PREFIX = "repos/" + plan_builder.REPOSITORY
API_HOST = "api.github.com"
_ENDPOINT = re.compile(
    re.escape(PREFIX) + r"/actions/(?:"
    r"runs/[1-9][0-9]*(?:/attempts/1/jobs\?per_page=100&page=[1-9][0-9]*|/artifacts\?per_page=100&page=[1-9][0-9]*)?"
    r"|jobs/[1-9][0-9]*/logs|artifacts/[1-9][0-9]*/zip)"
)


class AcquisitionError(ValueError):
    """Stable rejection code; never include tokens or signed URLs."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise AcquisitionError(code)


class GetTransport(Protocol):
    def get(self, endpoint: str, maximum: int) -> bytes:
        """Return the raw body of a successful bounded GET."""


class GitHubGetTransport:
    """No write-method interface, proxy inheritance, cookies, or auth redirects.

The API may redirect only log/archive downloads to documented GitHub storage
host families. The token is sent solely on the initial api.github.com request.
Redirect URLs are not retained because they can contain temporary credentials.
"""

    def __init__(self, token: str, *, limits: dict[str, int] | None = None) -> None:
        require(isinstance(token, str) and bool(token.strip()) and
                "\r" not in token and "\n" not in token, "github_token_required")
        self._token = token
        self._limits = dict(plan_builder.LIMITS if limits is None else limits)
        require(self._limits == plan_builder.LIMITS, "unsupported_limits")

    @staticmethod
    def _redirect_target(url: str) -> tuple[str, str]:
        try:
            parts = urlsplit(url)
            require(parts.scheme == "https" and parts.hostname is not None and
                    parts.username is None and parts.password is None and
                    parts.port in (None, 443) and not parts.fragment, "unsafe_download_redirect")
            host = parts.hostname.lower()
            allowed = (
                host == "github.com" or host == "objects.githubusercontent.com" or
                host.endswith(".actions.githubusercontent.com") or
                host.endswith(".blob.core.windows.net") or
                host == "github-production-release-asset-2e65be.s3.amazonaws.com" or
                host == "github-production-repository-file-5c1aeb.s3.amazonaws.com"
            )
            require(allowed and parts.path.startswith("/") and not any(
                ord(c) < 32 or ord(c) == 127 for c in url), "unsafe_download_redirect")
            return host, parts.path + ("?" + parts.query if parts.query else "")
        except ValueError as exc:
            if isinstance(exc, AcquisitionError):
                raise
            raise AcquisitionError("unsafe_download_redirect") from exc

    def get(self, endpoint: str, maximum: int) -> bytes:
        require(_ENDPOINT.fullmatch(endpoint) is not None, "unapproved_api_endpoint")
        require(type(maximum) is int and 0 < maximum <= self._limits["max_artifact_bytes"], "invalid_response_bound")
        host, target = API_HOST, "/" + endpoint
        may_redirect = endpoint.endswith("/logs") or endpoint.endswith("/zip")
        deadline = time.monotonic() + self._limits["request_timeout_seconds"]
        for redirect in range(self._limits["max_redirects"] + 1):
            remaining = deadline - time.monotonic()
            require(remaining > 0, "request_deadline_exceeded")
            connection = http.client.HTTPSConnection(host, timeout=remaining, context=ssl.create_default_context())
            headers = {"Accept": "application/vnd.github+json", "Accept-Encoding": "identity",
                       "User-Agent": "pulsemech-admission-observation-v0"}
            if host == API_HOST and redirect == 0:
                headers.update({"Authorization": "Bearer " + self._token,
                                "X-GitHub-Api-Version": "2022-11-28"})
            try:
                connection.request("GET", target, headers=headers)
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    require(may_redirect and redirect < self._limits["max_redirects"], "redirect_rejected")
                    location = response.getheader("Location")
                    require(isinstance(location, str), "redirect_location_missing")
                    host, target = self._redirect_target(location)
                    continue
                require(response.status == 200, "github_get_http_" + str(response.status))
                require(response.getheader("Content-Encoding") in (None, "identity"), "encoded_response_rejected")
                length = response.getheader("Content-Length")
                if length is not None:
                    require(length.isdecimal() and int(length) <= maximum, "response_size_limit")
                chunks = []
                size = 0
                while True:
                    remaining = deadline - time.monotonic()
                    require(remaining > 0, "request_deadline_exceeded")
                    if connection.sock is not None:
                        connection.sock.settimeout(remaining)
                    chunk = response.read(min(65536, maximum - size + 1))
                    if not chunk:
                        break
                    size += len(chunk)
                    require(size <= maximum, "response_size_limit")
                    chunks.append(chunk)
                require(length is None or size == int(length), "response_size_mismatch")
                return b"".join(chunks)
            except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
                raise AcquisitionError("github_get_transport_failed") from exc
            finally:
                connection.close()
        raise AcquisitionError("redirect_limit_exceeded")


def _object(raw: bytes) -> dict[str, Any]:
    try:
        return plan_builder.strict_object(raw)
    except plan_builder.PlanError as exc:
        raise AcquisitionError(str(exc)) from exc


def _positive_integer(value: Any) -> bool:
    return type(value) is int and value > 0


def _validate_plan(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = plan_builder.read_regular(path, plan_builder.LIMITS["max_json_bytes"])
    plan = _object(raw)
    require(plan.get("format") == plan_builder.FORMAT and
            plan.get("profile_id") == plan_builder.PROFILE_ID and
            plan.get("authority_effect") == "none", "unsupported_plan")
    source = plan.get("source", {})
    require(isinstance(source, dict) and source.get("repository") == plan_builder.REPOSITORY and
            re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit", ""))) is not None and
            source.get("workflow_path") == plan_builder.WORKFLOW_PATH and
            source.get("workflow_sha256") == plan_builder.WORKFLOW_SHA256 and
            source.get("policy_sha256") == plan_builder.POLICY_SHA256, "invalid_plan_source")
    require(plan.get("limits") == plan_builder.LIMITS, "unsupported_limits")
    require(plan.get("dispatch") == {"event": "workflow_dispatch", "ref": "refs/heads/main",
            "strict_external_evidence": True, "llamaguard_evidence_mode": "hosted_full_runtime"}, "unsupported_dispatch_profile")
    request = plan.get("request", {})
    require(isinstance(request, dict) and request.get("path") == "input/q2_request.json", "invalid_request_path")
    request_raw = plan_builder.read_regular(path.parent / "input/q2_request.json", 16384)
    require(request.get("bytes") == len(request_raw) and
            request.get("sha256") == hashlib.sha256(request_raw).hexdigest(), "request_digest_mismatch")
    request_value = _object(request_raw)
    require(request_value.get("evaluation_identity") == {"repository": plan_builder.REPOSITORY,
            "source_commit": source["commit"], "workflow": plan_builder.WORKFLOW_PATH,
            "event": "workflow_dispatch", "ref": "refs/heads/main"}, "request_source_mismatch")
    return raw, plan


def _run_identity(run: dict[str, Any], source: str, run_id: int, attempt: int) -> None:
    require(run.get("id") == run_id and type(run.get("id")) is int, "run_id_mismatch")
    require(run.get("run_attempt") == attempt and type(run.get("run_attempt")) is int, "run_attempt_mismatch")
    repository, head_repository = run.get("repository"), run.get("head_repository")
    require(isinstance(repository, dict) and isinstance(head_repository, dict) and
            repository.get("full_name") == plan_builder.REPOSITORY and
            head_repository.get("full_name") == plan_builder.REPOSITORY, "run_repository_mismatch")
    require(run.get("head_sha") == source and run.get("head_branch") == "main", "run_source_mismatch")
    require(run.get("event") == "workflow_dispatch" and run.get("path") == plan_builder.WORKFLOW_PATH,
            "run_workflow_mismatch")
    require(run.get("status") == "completed" and run.get("conclusion") in
            ("success", "failure", "cancelled", "timed_out", "action_required", "neutral", "skipped", "stale", "startup_failure"),
            "terminal_run_required")


def acquire(plan_path: Path, run_id: int, attempt: int, out_dir: Path,
            transport: GetTransport | None = None) -> dict[str, Any]:
    """Collect once. In-process transport injection exists only for unit tests.

    The returned completed flag describes byte collection, never verification.
    On error, the partial acquisition is written before AcquisitionError is
    raised. Existing output directories are never reused or overwritten.
    """
    require(_positive_integer(run_id) and type(attempt) is int and attempt == 1, "exact_first_attempt_required")
    plan_raw, plan = _validate_plan(plan_path)
    if transport is None:
        transport = GitHubGetTransport(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "")
    output = plan_builder.create_output(out_dir)
    for name in ("api", "logs", "archives"):
        (output / name).mkdir(mode=0o700)
    files: list[dict[str, Any]] = []
    total = 0
    result: dict[str, Any] = {
        "format": FORMAT, "profile_id": plan_builder.PROFILE_ID, "authority_effect": "none",
        "plan_sha256": hashlib.sha256(plan_raw).hexdigest(), "repository": plan_builder.REPOSITORY,
        "run_id": run_id, "run_attempt": attempt, "source_commit": plan["source"]["commit"],
        "completed": False, "errors": [], "files": files,
    }

    def save_get(relative: str, endpoint: str, kind: str, maximum: int) -> bytes:
        nonlocal total
        require(_ENDPOINT.fullmatch(endpoint) is not None, "unapproved_api_endpoint")
        budget = min(maximum, plan_builder.LIMITS["max_total_bytes"] - total)
        require(budget > 0, "aggregate_evidence_limit")
        raw = transport.get(endpoint, budget)
        require(isinstance(raw, bytes), "transport_return_type")
        require(len(raw) <= budget, "response_size_limit")
        plan_builder.write_new(output / relative, raw)
        files.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                      "kind": kind, "endpoint": endpoint})
        total += len(raw)
        return raw

    def pages(kind: str, endpoint_prefix: str, maximum_count: int,
              *, after: bool = False) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[int] = set()
        expected_count = None
        for page in range(1, plan_builder.LIMITS["max_pages"] + 1):
            endpoint = endpoint_prefix + f"?per_page=100&page={page}"
            suffix = "-after" if after else ""
            raw = save_get(f"api/{kind}{suffix}-{page:03d}.json", endpoint, kind,
                           plan_builder.LIMITS["max_json_bytes"])
            value = _object(raw)
            count = value.get("total_count")
            require(type(count) is int and 0 <= count <= maximum_count, "page_total_count_limit")
            if expected_count is None:
                expected_count = count
            require(count == expected_count, "page_total_changed")
            batch = value.get(kind)
            require(isinstance(batch, list) and len(batch) <= 100, "invalid_page_items")
            for item in batch:
                require(isinstance(item, dict) and _positive_integer(item.get("id")), "invalid_item_id")
                require(item["id"] not in seen, "duplicate_paginated_id")
                seen.add(item["id"])
                rows.append(item)
            require(len(rows) <= count, "page_count_overflow")
            if len(rows) == count:
                return rows
            require(bool(batch), "pagination_truncated")
        raise AcquisitionError("page_limit_exceeded")

    caught: BaseException | None = None
    try:
        endpoint = f"{PREFIX}/actions/runs/{run_id}"
        run = _object(save_get("api/run.json", endpoint, "run", plan_builder.LIMITS["max_json_bytes"]))
        _run_identity(run, result["source_commit"], run_id, attempt)
        jobs = pages("jobs", f"{PREFIX}/actions/runs/{run_id}/attempts/{attempt}/jobs",
                     plan_builder.LIMITS["max_jobs"])
        artifacts = pages("artifacts", f"{PREFIX}/actions/runs/{run_id}/artifacts",
                          plan_builder.LIMITS["max_artifacts"])
        for job in jobs:
            require(job.get("run_id") == run_id and type(job.get("run_id")) is int and
                    job.get("run_attempt") == attempt and type(job.get("run_attempt")) is int and
                    job.get("head_sha") == result["source_commit"], "job_identity_mismatch")
            require(job.get("status") == "completed", "job_not_terminal")
            steps = job.get("steps")
            require(isinstance(steps, list), "job_steps_missing")
            if steps or job.get("conclusion") != "skipped":
                save_get(f"logs/{job['id']}.txt", f"{PREFIX}/actions/jobs/{job['id']}/logs", "log",
                         plan_builder.LIMITS["max_log_bytes"])
        for artifact in artifacts:
            identity = artifact.get("workflow_run")
            require(isinstance(identity, dict) and identity.get("id") == run_id and
                    type(identity.get("id")) is int and identity.get("head_sha") == result["source_commit"],
                    "artifact_run_identity_mismatch")
            require(artifact.get("expired") is False, "artifact_expired")
            size = artifact.get("size_in_bytes")
            require(type(size) is int and 0 < size <= plan_builder.LIMITS["max_artifact_bytes"], "artifact_size_limit")
            raw = save_get(f"archives/{artifact['id']}.zip", f"{PREFIX}/actions/artifacts/{artifact['id']}/zip", "archive",
                           plan_builder.LIMITS["max_artifact_bytes"])
            require(len(raw) == size, "artifact_size_mismatch")
            digest = artifact.get("digest")
            require(isinstance(digest, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is not None,
                    "artifact_digest_missing")
            require(digest == "sha256:" + hashlib.sha256(raw).hexdigest(), "artifact_digest_mismatch")
        jobs_after = pages("jobs", f"{PREFIX}/actions/runs/{run_id}/attempts/{attempt}/jobs",
                           plan_builder.LIMITS["max_jobs"], after=True)
        artifacts_after = pages("artifacts", f"{PREFIX}/actions/runs/{run_id}/artifacts",
                                plan_builder.LIMITS["max_artifacts"], after=True)
        require(sorted(jobs_after, key=lambda row: row["id"]) == sorted(jobs, key=lambda row: row["id"]),
                "job_inventory_changed")
        require(sorted(artifacts_after, key=lambda row: row["id"]) == sorted(artifacts, key=lambda row: row["id"]),
                "artifact_inventory_changed")
        run_after = _object(save_get("api/run_after.json", endpoint, "run", plan_builder.LIMITS["max_json_bytes"]))
        _run_identity(run_after, result["source_commit"], run_id, attempt)
        for key in ("id", "run_attempt", "head_sha", "head_branch", "event", "path", "status", "conclusion",
                    "created_at", "updated_at", "run_started_at", "workflow_id", "run_number"):
            require(run_after.get(key) == run.get(key), "run_changed_during_collection")
        result["completed"] = True
    except (AcquisitionError, plan_builder.PlanError, OSError, ValueError, TypeError, KeyError, KeyboardInterrupt) as exc:
        caught = exc
        result["errors"] = [str(exc) if isinstance(exc, (AcquisitionError, plan_builder.PlanError))
                            else "collection_interrupted" if isinstance(exc, KeyboardInterrupt) else "collection_failed"]
    finally:
        files.sort(key=lambda item: item["path"])
        plan_builder.write_new(output / "acquisition.json", plan_builder.canonical_bytes(result))
    if caught is not None:
        raise AcquisitionError(result["errors"][0]) from caught
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--attempt", required=True, type=int, choices=[1])
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = acquire(args.plan, args.run_id, args.attempt, args.out_dir)
    except (AcquisitionError, plan_builder.PlanError, OSError, ValueError) as exc:
        code = str(exc) if isinstance(exc, (AcquisitionError, plan_builder.PlanError)) else "acquisition_failed"
        print(plan_builder.canonical_bytes({"error": code, "authority_effect": "none"}).decode(), end="", file=sys.stderr)
        return 1
    print(plan_builder.canonical_bytes({"completed": result["completed"], "authority_effect": "none",
          "acquisition": str(args.out_dir / "acquisition.json"), "verification": "not_performed"}).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
