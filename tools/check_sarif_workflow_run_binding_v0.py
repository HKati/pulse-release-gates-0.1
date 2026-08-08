#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


TOOL_NAME = "check_sarif_workflow_run_binding_v0"
TOOL_VERSION = "0.1.0"
EXPECTED_WORKFLOW_NAME = "PULSE CI"
EXPECTED_WORKFLOW_PATH = ".github/workflows/pulse_ci.yml"
SUPPORTED_EVENTS = frozenset({"pull_request", "push", "workflow_dispatch"})

MAX_API_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
MAX_SARIF_BYTES = 128 * 1024 * 1024

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_TAG_RE = re.compile(r"^[vV][A-Za-z0-9][A-Za-z0-9._-]*$")

METADATA_SUFFIXES = (
    "/meta/sarif_upload.json",
    "/artifacts/meta/sarif_upload.json",
)
SARIF_SUFFIXES = (
    "/reports/sarif.json",
    "/artifacts/reports/sarif.json",
)
METADATA_KEYS = frozenset(
    {
        "event_name",
        "ref",
        "sha",
        "pr_number",
        "is_fork",
    }
)


class BindingError(RuntimeError):
    pass


class StrictJsonError(ValueError):
    pass


@dataclass(frozen=True)
class BindingResult:
    ok: bool
    skip: bool
    reason: str
    event_name: str
    ref: str | None
    sha: str | None
    pr_number: int | None
    is_fork: bool
    source_run_id: int
    source_head_sha: str
    source_head_branch: str


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def parse_json_bytes(payload: bytes, *, label: str) -> Any:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise BindingError(f"{label}_utf8_bom_not_permitted")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BindingError(f"{label}_invalid_utf8: {exc}") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except (json.JSONDecodeError, StrictJsonError) as exc:
        raise BindingError(f"{label}_invalid_json: {exc}") from exc


def _read_bounded_regular_file(
    path: Path,
    *,
    label: str,
    maximum: int,
) -> bytes:
    candidate = path.absolute()
    try:
        metadata = candidate.lstat()
    except OSError as exc:
        raise BindingError(f"{label}_unavailable: {candidate}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise BindingError(f"{label}_symlink_rejected: {candidate}")
    if not stat.S_ISREG(metadata.st_mode):
        raise BindingError(f"{label}_not_regular_file: {candidate}")
    if metadata.st_size > maximum:
        raise BindingError(
            f"{label}_too_large: size={metadata.st_size} maximum={maximum}"
        )
    payload = candidate.read_bytes()
    if len(payload) != metadata.st_size:
        raise BindingError(
            f"{label}_size_changed: expected={metadata.st_size} "
            f"observed={len(payload)}"
        )
    return payload


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BindingError(f"{label}_not_object")
    return value


def _require_string(
    value: Any,
    *,
    label: str,
    non_empty: bool = True,
) -> str:
    if not isinstance(value, str):
        raise BindingError(f"{label}_not_string: {value!r}")
    if non_empty and not value:
        raise BindingError(f"{label}_empty")
    if "\n" in value or "\r" in value or "\x00" in value:
        raise BindingError(f"{label}_control_character_rejected")
    return value


def _require_int(value: Any, *, label: str, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BindingError(f"{label}_not_integer: {value!r}")
    if positive and value <= 0:
        raise BindingError(f"{label}_not_positive: {value!r}")
    return value


def _require_sha40(value: Any, *, label: str) -> str:
    text = _require_string(value, label=label)
    if SHA40_RE.fullmatch(text) is None:
        raise BindingError(f"{label}_not_lowercase_sha40: {text!r}")
    return text


def _nested_object(
    value: dict[str, Any],
    *keys: str,
    label: str,
) -> dict[str, Any]:
    cursor: Any = value
    for key in keys:
        if not isinstance(cursor, dict):
            raise BindingError(f"{label}_not_object")
        cursor = cursor.get(key)
    return _require_object(cursor, label=label)


def _nested_string(
    value: dict[str, Any],
    *keys: str,
    label: str,
) -> str:
    cursor: Any = value
    for key in keys:
        if not isinstance(cursor, dict):
            raise BindingError(f"{label}_parent_not_object")
        cursor = cursor.get(key)
    return _require_string(cursor, label=label)


def _validate_metadata(metadata: Any) -> dict[str, Any]:
    value = _require_object(metadata, label="sarif_metadata")
    observed_keys = frozenset(value)
    if observed_keys != METADATA_KEYS:
        missing = sorted(METADATA_KEYS.difference(observed_keys))
        unexpected = sorted(observed_keys.difference(METADATA_KEYS))
        raise BindingError(
            "sarif_metadata_key_set_mismatch: "
            f"missing={missing!r} unexpected={unexpected!r}"
        )

    event_name = _require_string(
        value.get("event_name"),
        label="sarif_metadata_event_name",
    )
    ref = _require_string(value.get("ref"), label="sarif_metadata_ref")
    sha = _require_sha40(value.get("sha"), label="sarif_metadata_sha")

    pr_number = value.get("pr_number")
    if pr_number is not None:
        pr_number = _require_int(
            pr_number,
            label="sarif_metadata_pr_number",
            positive=True,
        )

    is_fork = value.get("is_fork")
    if not isinstance(is_fork, bool):
        raise BindingError(
            f"sarif_metadata_is_fork_not_boolean: {is_fork!r}"
        )

    return {
        "event_name": event_name,
        "ref": ref,
        "sha": sha,
        "pr_number": pr_number,
        "is_fork": is_fork,
    }


def _validate_run(
    run: Any,
    *,
    repository: str,
    run_id: int,
) -> dict[str, Any]:
    value = _require_object(run, label="workflow_run")

    observed_id = _require_int(
        value.get("id"),
        label="workflow_run_id",
        positive=True,
    )
    if observed_id != run_id:
        raise BindingError(
            f"workflow_run_id_mismatch: expected={run_id} "
            f"observed={observed_id}"
        )

    name = _require_string(value.get("name"), label="workflow_run_name")
    if name != EXPECTED_WORKFLOW_NAME:
        raise BindingError(
            "workflow_run_name_mismatch: "
            f"expected={EXPECTED_WORKFLOW_NAME!r} observed={name!r}"
        )

    path = _require_string(value.get("path"), label="workflow_run_path")
    expected_prefix = f"{EXPECTED_WORKFLOW_PATH}@"
    if not path.startswith(expected_prefix):
        raise BindingError(
            "workflow_run_path_mismatch: "
            f"expected_prefix={expected_prefix!r} observed={path!r}"
        )

    status = _require_string(
        value.get("status"),
        label="workflow_run_status",
    )
    if status != "completed":
        raise BindingError(
            f"workflow_run_not_completed: observed={status!r}"
        )

    event_name = _require_string(
        value.get("event"),
        label="workflow_run_event",
    )
    if event_name not in SUPPORTED_EVENTS:
        raise BindingError(
            f"workflow_run_event_unsupported: {event_name!r}"
        )

    run_repository = _nested_string(
        value,
        "repository",
        "full_name",
        label="workflow_run_repository",
    )
    if run_repository != repository:
        raise BindingError(
            "workflow_run_repository_mismatch: "
            f"expected={repository!r} observed={run_repository!r}"
        )

    head_repository = _nested_string(
        value,
        "head_repository",
        "full_name",
        label="workflow_run_head_repository",
    )
    head_sha = _require_sha40(
        value.get("head_sha"),
        label="workflow_run_head_sha",
    )
    head_branch = _require_string(
        value.get("head_branch"),
        label="workflow_run_head_branch",
    )

    pull_requests = value.get("pull_requests")
    if not isinstance(pull_requests, list):
        raise BindingError("workflow_run_pull_requests_not_array")

    return {
        "raw": value,
        "event_name": event_name,
        "repository": run_repository,
        "head_repository": head_repository,
        "head_sha": head_sha,
        "head_branch": head_branch,
        "pull_requests": pull_requests,
    }


def _api_pull_request_numbers(run: dict[str, Any]) -> list[int]:
    numbers: list[int] = []
    for index, item in enumerate(run["pull_requests"]):
        if not isinstance(item, dict):
            raise BindingError(
                f"workflow_run_pull_requests_item_not_object: index={index}"
            )
        number = _require_int(
            item.get("number"),
            label=f"workflow_run_pull_requests_{index}_number",
            positive=True,
        )
        numbers.append(number)
    if len(numbers) != len(set(numbers)):
        raise BindingError("workflow_run_pull_request_numbers_not_unique")
    return numbers


def _validate_pull_request(
    pull_request: Any,
    *,
    repository: str,
    pr_number: int,
    run: dict[str, Any],
) -> dict[str, Any]:
    pr = _require_object(pull_request, label="pull_request")
    observed_number = _require_int(
        pr.get("number"),
        label="pull_request_number",
        positive=True,
    )
    if observed_number != pr_number:
        raise BindingError(
            "pull_request_number_mismatch: "
            f"expected={pr_number} observed={observed_number}"
        )

    base_repo = _nested_string(
        pr,
        "base",
        "repo",
        "full_name",
        label="pull_request_base_repository",
    )
    if base_repo != repository:
        raise BindingError(
            "pull_request_base_repository_mismatch: "
            f"expected={repository!r} observed={base_repo!r}"
        )

    head_repo = _nested_string(
        pr,
        "head",
        "repo",
        "full_name",
        label="pull_request_head_repository",
    )
    head_sha = _require_sha40(
        _nested_string(
            pr,
            "head",
            "sha",
            label="pull_request_head_sha",
        ),
        label="pull_request_head_sha",
    )
    head_ref = _nested_string(
        pr,
        "head",
        "ref",
        label="pull_request_head_ref",
    )
    base_sha = _require_sha40(
        _nested_string(
            pr,
            "base",
            "sha",
            label="pull_request_base_sha",
        ),
        label="pull_request_base_sha",
    )

    if head_sha != run["head_sha"]:
        raise BindingError(
            "pull_request_head_sha_mismatch: "
            f"run={run['head_sha']!r} pull_request={head_sha!r}"
        )
    if head_ref != run["head_branch"]:
        raise BindingError(
            "pull_request_head_branch_mismatch: "
            f"run={run['head_branch']!r} pull_request={head_ref!r}"
        )
    if head_repo != run["head_repository"]:
        raise BindingError(
            "pull_request_head_repository_mismatch: "
            f"run={run['head_repository']!r} pull_request={head_repo!r}"
        )

    api_numbers = _api_pull_request_numbers(run)
    is_fork = head_repo != base_repo
    if is_fork:
        if api_numbers and api_numbers != [pr_number]:
            raise BindingError(
                "workflow_run_pull_request_binding_mismatch: "
                f"expected_empty_or={[pr_number]!r} observed={api_numbers!r}"
            )
    elif api_numbers != [pr_number]:
        raise BindingError(
            "workflow_run_pull_request_binding_mismatch: "
            f"expected={[pr_number]!r} observed={api_numbers!r}"
        )

    merge_commit_sha = pr.get("merge_commit_sha")
    if merge_commit_sha is not None:
        merge_commit_sha = _require_sha40(
            merge_commit_sha,
            label="pull_request_merge_commit_sha",
        )

    return {
        "head_repository": head_repo,
        "head_sha": head_sha,
        "head_ref": head_ref,
        "base_sha": base_sha,
        "is_fork": is_fork,
        "merge_commit_sha": merge_commit_sha,
    }


def _validate_merge_ref(
    merge_ref: Any,
    *,
    expected_ref: str,
) -> str:
    value = _require_object(merge_ref, label="pull_request_merge_ref")
    observed_ref = _require_string(
        value.get("ref"),
        label="pull_request_merge_ref_name",
    )
    if observed_ref != expected_ref:
        raise BindingError(
            "pull_request_merge_ref_name_mismatch: "
            f"expected={expected_ref!r} observed={observed_ref!r}"
        )

    ref_object = _require_object(
        value.get("object"),
        label="pull_request_merge_ref_object",
    )
    object_type = _require_string(
        ref_object.get("type"),
        label="pull_request_merge_ref_object_type",
    )
    if object_type != "commit":
        raise BindingError(
            "pull_request_merge_ref_not_commit: "
            f"observed={object_type!r}"
        )
    return _require_sha40(
        ref_object.get("sha"),
        label="pull_request_merge_ref_sha",
    )


def _validate_merge_commit(
    merge_commit: Any,
    *,
    merge_sha: str,
    base_sha: str,
    head_sha: str,
) -> None:
    value = _require_object(
        merge_commit,
        label="pull_request_merge_commit",
    )
    observed_sha = _require_sha40(
        value.get("sha"),
        label="pull_request_merge_commit_sha",
    )
    if observed_sha != merge_sha:
        raise BindingError(
            "pull_request_merge_commit_identity_mismatch: "
            f"expected={merge_sha!r} observed={observed_sha!r}"
        )

    parents = value.get("parents")
    if not isinstance(parents, list) or len(parents) != 2:
        raise BindingError(
            "pull_request_merge_commit_parent_count_invalid: "
            f"observed={len(parents) if isinstance(parents, list) else None}"
        )

    parent_shas: list[str] = []
    for index, parent in enumerate(parents):
        parent_object = _require_object(
            parent,
            label=f"pull_request_merge_commit_parent_{index}",
        )
        parent_shas.append(
            _require_sha40(
                parent_object.get("sha"),
                label=f"pull_request_merge_commit_parent_{index}_sha",
            )
        )

    expected = [base_sha, head_sha]
    if parent_shas != expected:
        raise BindingError(
            "pull_request_merge_commit_parents_mismatch: "
            f"expected={expected!r} observed={parent_shas!r}"
        )


def verify_binding(
    *,
    repository: str,
    run_id: int,
    run: Any,
    metadata: Any,
    pull_request: Any | None = None,
    merge_ref: Any | None = None,
    merge_commit: Any | None = None,
) -> BindingResult:
    repository = _require_string(
        repository,
        label="repository",
    )
    run_id = _require_int(run_id, label="run_id", positive=True)
    run_state = _validate_run(
        run,
        repository=repository,
        run_id=run_id,
    )
    meta = _validate_metadata(metadata)

    if meta["event_name"] != run_state["event_name"]:
        raise BindingError(
            "sarif_metadata_event_mismatch: "
            f"expected={run_state['event_name']!r} "
            f"observed={meta['event_name']!r}"
        )

    event_name = run_state["event_name"]

    if event_name == "pull_request":
        if meta["pr_number"] is None:
            raise BindingError("sarif_metadata_pr_number_required")
        if pull_request is None:
            raise BindingError("pull_request_api_snapshot_required")
        if merge_ref is None:
            raise BindingError("pull_request_merge_ref_snapshot_required")
        if merge_commit is None:
            raise BindingError("pull_request_merge_commit_snapshot_required")

        pr = _validate_pull_request(
            pull_request,
            repository=repository,
            pr_number=meta["pr_number"],
            run=run_state,
        )
        expected_ref = f"refs/pull/{meta['pr_number']}/merge"
        merge_sha = _validate_merge_ref(
            merge_ref,
            expected_ref=expected_ref,
        )
        _validate_merge_commit(
            merge_commit,
            merge_sha=merge_sha,
            base_sha=pr["base_sha"],
            head_sha=pr["head_sha"],
        )
        if (
            pr["merge_commit_sha"] is not None
            and pr["merge_commit_sha"] != merge_sha
        ):
            raise BindingError(
                "pull_request_merge_commit_sha_mismatch: "
                f"pull_request={pr['merge_commit_sha']!r} "
                f"merge_ref={merge_sha!r}"
            )

        expected = {
            "ref": expected_ref,
            "sha": merge_sha,
            "pr_number": meta["pr_number"],
            "is_fork": pr["is_fork"],
        }
        for field, expected_value in expected.items():
            if meta[field] != expected_value:
                raise BindingError(
                    f"sarif_metadata_{field}_mismatch: "
                    f"expected={expected_value!r} "
                    f"observed={meta[field]!r}"
                )

        if pr["is_fork"]:
            return BindingResult(
                ok=True,
                skip=True,
                reason="fork_pull_request",
                event_name=event_name,
                ref=None,
                sha=None,
                pr_number=meta["pr_number"],
                is_fork=True,
                source_run_id=run_id,
                source_head_sha=run_state["head_sha"],
                source_head_branch=run_state["head_branch"],
            )

        return BindingResult(
            ok=True,
            skip=False,
            reason="verified_pull_request_merge",
            event_name=event_name,
            ref=expected_ref,
            sha=merge_sha,
            pr_number=meta["pr_number"],
            is_fork=False,
            source_run_id=run_id,
            source_head_sha=run_state["head_sha"],
            source_head_branch=run_state["head_branch"],
        )

    if meta["pr_number"] is not None:
        raise BindingError(
            "sarif_metadata_pr_number_must_be_null_for_non_pr_event"
        )
    if meta["is_fork"] is not False:
        raise BindingError(
            "sarif_metadata_is_fork_must_be_false_for_non_pr_event"
        )
    if run_state["head_repository"] != repository:
        raise BindingError(
            "workflow_run_head_repository_must_equal_repository: "
            f"expected={repository!r} "
            f"observed={run_state['head_repository']!r}"
        )

    if event_name == "push":
        if run_state["head_branch"] == "main":
            expected_ref = "refs/heads/main"
        elif VERSION_TAG_RE.fullmatch(run_state["head_branch"]):
            expected_ref = f"refs/tags/{run_state['head_branch']}"
        else:
            raise BindingError(
                "push_source_ref_outside_pulse_ci_contract: "
                f"head_branch={run_state['head_branch']!r}"
            )
        expected_sha = run_state["head_sha"]
        if meta["ref"] != expected_ref:
            raise BindingError(
                "sarif_metadata_ref_mismatch: "
                f"expected={expected_ref!r} observed={meta['ref']!r}"
            )
        if meta["sha"] != expected_sha:
            raise BindingError(
                "sarif_metadata_sha_mismatch: "
                f"expected={expected_sha!r} observed={meta['sha']!r}"
            )
        return BindingResult(
            ok=True,
            skip=False,
            reason="verified_push",
            event_name=event_name,
            ref=expected_ref,
            sha=expected_sha,
            pr_number=None,
            is_fork=False,
            source_run_id=run_id,
            source_head_sha=run_state["head_sha"],
            source_head_branch=run_state["head_branch"],
        )

    if event_name == "workflow_dispatch":
        branch_ref = f"refs/heads/{run_state['head_branch']}"
        tag_ref = f"refs/tags/{run_state['head_branch']}"
        if meta["ref"] not in {branch_ref, tag_ref}:
            raise BindingError(
                "sarif_metadata_ref_mismatch: "
                f"expected_one_of={[branch_ref, tag_ref]!r} "
                f"observed={meta['ref']!r}"
            )
        if meta["sha"] != run_state["head_sha"]:
            raise BindingError(
                "sarif_metadata_sha_mismatch: "
                f"expected={run_state['head_sha']!r} "
                f"observed={meta['sha']!r}"
            )
        if run_state["head_branch"] != "main" or meta["ref"] != "refs/heads/main":
            return BindingResult(
                ok=True,
                skip=True,
                reason="workflow_dispatch_ref_not_main",
                event_name=event_name,
                ref=None,
                sha=None,
                pr_number=None,
                is_fork=False,
                source_run_id=run_id,
                source_head_sha=run_state["head_sha"],
                source_head_branch=run_state["head_branch"],
            )
        return BindingResult(
            ok=True,
            skip=False,
            reason="verified_workflow_dispatch_main",
            event_name=event_name,
            ref="refs/heads/main",
            sha=run_state["head_sha"],
            pr_number=None,
            is_fork=False,
            source_run_id=run_id,
            source_head_sha=run_state["head_sha"],
            source_head_branch=run_state["head_branch"],
        )

    raise BindingError(f"unreachable_event: {event_name!r}")


def _find_files(
    root: Path,
    *,
    suffixes: Iterable[str],
    label: str,
) -> list[Path]:
    root = root.absolute()
    try:
        root_metadata = root.lstat()
    except OSError as exc:
        raise BindingError(f"{label}_root_unavailable: {root}: {exc}") from exc
    if stat.S_ISLNK(root_metadata.st_mode):
        raise BindingError(f"{label}_root_symlink_rejected: {root}")
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise BindingError(f"{label}_root_not_directory: {root}")

    matches: list[Path] = []
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise BindingError(f"{label}_symlink_rejected: {candidate}")
        if not candidate.is_file():
            continue
        identity = "/" + candidate.relative_to(root).as_posix()
        if any(identity.endswith(suffix) for suffix in suffixes):
            matches.append(candidate)
    return sorted(matches, key=lambda item: item.as_posix())


def _select_metadata(root: Path) -> tuple[dict[str, Any] | None, Path | None]:
    matches = _find_files(
        root,
        suffixes=METADATA_SUFFIXES,
        label="sarif_metadata",
    )
    if not matches:
        return None, None
    if len(matches) != 1:
        raise BindingError(
            "sarif_metadata_file_count_invalid: "
            f"observed={len(matches)} paths="
            f"{[item.as_posix() for item in matches]!r}"
        )
    path = matches[0]
    payload = _read_bounded_regular_file(
        path,
        label="sarif_metadata",
        maximum=MAX_METADATA_BYTES,
    )
    return _require_object(
        parse_json_bytes(payload, label="sarif_metadata"),
        label="sarif_metadata",
    ), path


def _select_sarif(root: Path) -> Path | None:
    matches = _find_files(
        root,
        suffixes=SARIF_SUFFIXES,
        label="sarif",
    )
    if not matches:
        return None
    if len(matches) != 1:
        raise BindingError(
            "sarif_file_count_invalid: "
            f"observed={len(matches)} paths="
            f"{[item.as_posix() for item in matches]!r}"
        )
    path = matches[0]
    _read_bounded_regular_file(
        path,
        label="sarif",
        maximum=MAX_SARIF_BYTES,
    )
    return path


class GitHubApi:
    def __init__(
        self,
        *,
        api_url: str,
        token: str,
        api_version: str,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.api_version = api_version

    def get(self, path: str, *, label: str) -> Any:
        url = f"{self.api_url}{path}"
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": TOOL_NAME,
                "X-GitHub-Api-Version": self.api_version,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read(MAX_API_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise BindingError(
                f"{label}_http_error: status={exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            raise BindingError(f"{label}_network_error: {exc.reason}") from exc
        if len(payload) > MAX_API_RESPONSE_BYTES:
            raise BindingError(
                f"{label}_response_too_large: maximum={MAX_API_RESPONSE_BYTES}"
            )
        return parse_json_bytes(payload, label=label)


def _api_path(repository: str, suffix: str) -> str:
    owner, name = repository.split("/", 1)
    return (
        "/repos/"
        + urllib.parse.quote(owner, safe="")
        + "/"
        + urllib.parse.quote(name, safe="")
        + suffix
    )


def _write_outputs(path: Path, values: dict[str, str]) -> None:
    rendered: list[str] = []
    for key in sorted(values):
        value = values[key]
        if "\n" in value or "\r" in value:
            raise BindingError(f"github_output_value_newline_rejected: {key}")
        rendered.append(f"{key}={value}")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(rendered) + "\n")


def _render_diagnostic(
    *,
    result: BindingResult,
    metadata_path: Path | None,
    sarif_path: Path | None,
) -> str:
    payload = {
        "artifact": {
            "metadata_path": (
                metadata_path.as_posix() if metadata_path is not None else None
            ),
            "sarif_path": (
                sarif_path.as_posix() if sarif_path is not None else None
            ),
        },
        "binding": asdict(result),
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bind a downloaded PULSE SARIF artifact to independently "
            "retrieved GitHub workflow-run identity."
        )
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument(
        "--github-api-url",
        default=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
    )
    parser.add_argument(
        "--github-api-version",
        default=os.environ.get("GITHUB_API_VERSION", "2022-11-28"),
    )
    parser.add_argument(
        "--github-output",
        default=os.environ.get("GITHUB_OUTPUT", ""),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = _require_string(args.repository, label="repository")
    if repository.count("/") != 1:
        raise BindingError(
            f"repository_identity_invalid: {repository!r}"
        )
    run_id = _require_int(args.run_id, label="run_id", positive=True)
    artifact_root = Path(args.artifact_root).absolute()

    token = os.environ.get("GH_TOKEN", "")
    if not token:
        raise BindingError("GH_TOKEN_missing")

    api = GitHubApi(
        api_url=_require_string(
            args.github_api_url,
            label="github_api_url",
        ),
        token=token,
        api_version=_require_string(
            args.github_api_version,
            label="github_api_version",
        ),
    )

    metadata, metadata_path = _select_metadata(artifact_root)
    if metadata is None:
        result = BindingResult(
            ok=True,
            skip=True,
            reason="missing_metadata",
            event_name="unknown",
            ref=None,
            sha=None,
            pr_number=None,
            is_fork=False,
            source_run_id=run_id,
            source_head_sha="unknown",
            source_head_branch="unknown",
        )
        outputs = {
            "reason": result.reason,
            "skip": "true",
        }
        if args.github_output:
            _write_outputs(Path(args.github_output), outputs)
        sys.stdout.write(
            _render_diagnostic(
                result=result,
                metadata_path=None,
                sarif_path=None,
            )
        )
        return 0

    run = api.get(
        _api_path(repository, f"/actions/runs/{run_id}"),
        label="workflow_run_api",
    )
    validated_meta = _validate_metadata(metadata)

    pull_request: Any | None = None
    merge_ref: Any | None = None
    merge_commit: Any | None = None

    run_object = _require_object(run, label="workflow_run_api")
    event_name = run_object.get("event")
    if event_name == "pull_request":
        pr_number = validated_meta.get("pr_number")
        if isinstance(pr_number, bool) or not isinstance(pr_number, int):
            raise BindingError("sarif_metadata_pr_number_required")
        pull_request = api.get(
            _api_path(repository, f"/pulls/{pr_number}"),
            label="pull_request_api",
        )
        expected_ref = f"refs/pull/{pr_number}/merge"
        encoded_ref = urllib.parse.quote(
            expected_ref.removeprefix("refs/"),
            safe="/",
        )
        merge_ref = api.get(
            _api_path(repository, f"/git/ref/{encoded_ref}"),
            label="pull_request_merge_ref_api",
        )
        merge_ref_object = _require_object(
            _require_object(
                merge_ref,
                label="pull_request_merge_ref_api",
            ).get("object"),
            label="pull_request_merge_ref_api_object",
        )
        merge_sha = _require_sha40(
            merge_ref_object.get("sha"),
            label="pull_request_merge_ref_api_sha",
        )
        merge_commit = api.get(
            _api_path(repository, f"/git/commits/{merge_sha}"),
            label="pull_request_merge_commit_api",
        )

    result = verify_binding(
        repository=repository,
        run_id=run_id,
        run=run,
        metadata=metadata,
        pull_request=pull_request,
        merge_ref=merge_ref,
        merge_commit=merge_commit,
    )

    sarif_path = None if result.skip else _select_sarif(artifact_root)
    if not result.skip and sarif_path is None:
        result = BindingResult(
            ok=True,
            skip=True,
            reason="missing_sarif",
            event_name=result.event_name,
            ref=None,
            sha=None,
            pr_number=result.pr_number,
            is_fork=result.is_fork,
            source_run_id=result.source_run_id,
            source_head_sha=result.source_head_sha,
            source_head_branch=result.source_head_branch,
        )

    outputs = {
        "reason": result.reason,
        "skip": "true" if result.skip else "false",
    }
    if not result.skip:
        if result.ref is None or result.sha is None or sarif_path is None:
            raise BindingError("verified_upload_output_incomplete")
        outputs.update(
            {
                "ref": result.ref,
                "sarif_path": sarif_path.as_posix(),
                "sha": result.sha,
            }
        )

    if args.github_output:
        _write_outputs(Path(args.github_output), outputs)

    sys.stdout.write(
        _render_diagnostic(
            result=result,
            metadata_path=metadata_path,
            sarif_path=sarif_path,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BindingError as exc:
        diagnostic = {
            "error": str(exc),
            "ok": False,
            "tool": TOOL_NAME,
            "tool_version": TOOL_VERSION,
        }
        sys.stderr.write(
            json.dumps(
                diagnostic,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        raise SystemExit(2)
