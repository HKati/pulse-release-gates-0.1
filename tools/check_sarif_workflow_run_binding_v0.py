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
TOOL_VERSION = "0.2.0"
EXPECTED_WORKFLOW_NAME = "PULSE CI"
EXPECTED_WORKFLOW_PATH = ".github/workflows/pulse_ci.yml"
SUPPORTED_EVENTS = frozenset({"pull_request", "push", "workflow_dispatch"})

MAX_API_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
MAX_SARIF_BYTES = 128 * 1024 * 1024
ASSOCIATED_PULL_REQUESTS_PAGE_SIZE = 100
ASSOCIATED_PULL_REQUESTS_MAX_PAGES = 2

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")

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


def _require_array(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise BindingError(f"{label}_not_array")
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


def _optional_sha40(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _require_sha40(value, label=label)


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


def _repository_identity(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    repository = _require_object(value, label=label)
    full_name = repository.get("full_name")
    if full_name is not None:
        return _require_string(full_name, label=f"{label}_full_name")

    url = repository.get("url")
    if url is None:
        return None
    url_text = _require_string(url, label=f"{label}_url")
    parsed = urllib.parse.urlparse(url_text)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[-3] != "repos":
        raise BindingError(
            f"{label}_url_not_repository_api_identity: {url_text!r}"
        )
    return (
        urllib.parse.unquote(parts[-2])
        + "/"
        + urllib.parse.unquote(parts[-1])
    )


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
    path_identity, separator, path_ref = path.partition("@")
    if path_identity != EXPECTED_WORKFLOW_PATH or (separator and not path_ref):
        raise BindingError(
            "workflow_run_path_mismatch: "
            f"expected_path={EXPECTED_WORKFLOW_PATH!r} observed={path!r}"
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
    pull_requests = _require_array(
        value.get("pull_requests"),
        label="workflow_run_pull_requests",
    )

    return {
        "event_name": event_name,
        "repository": run_repository,
        "head_repository": head_repository,
        "head_sha": head_sha,
        "head_branch": head_branch,
        "pull_requests": pull_requests,
    }


def _validate_workflow_run_snapshot(
    snapshot: Any,
    *,
    repository: str,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    value = _require_object(snapshot, label="workflow_run_pull_request")
    number = _require_int(
        value.get("number"),
        label="workflow_run_pull_request_number",
        positive=True,
    )
    head = _require_object(
        value.get("head"),
        label="workflow_run_pull_request_head",
    )
    base = _require_object(
        value.get("base"),
        label="workflow_run_pull_request_base",
    )

    head_sha = _require_sha40(
        head.get("sha"),
        label="workflow_run_pull_request_head_sha",
    )
    head_ref = _require_string(
        head.get("ref"),
        label="workflow_run_pull_request_head_ref",
    )
    base_sha = _require_sha40(
        base.get("sha"),
        label="workflow_run_pull_request_base_sha",
    )
    base_ref = _require_string(
        base.get("ref"),
        label="workflow_run_pull_request_base_ref",
    )

    if head_sha != run_state["head_sha"]:
        raise BindingError(
            "workflow_run_pull_request_head_sha_mismatch: "
            f"run={run_state['head_sha']!r} snapshot={head_sha!r}"
        )
    if head_ref != run_state["head_branch"]:
        raise BindingError(
            "workflow_run_pull_request_head_branch_mismatch: "
            f"run={run_state['head_branch']!r} snapshot={head_ref!r}"
        )
    if base_ref != "main":
        raise BindingError(
            "workflow_run_pull_request_base_ref_mismatch: "
            f"expected='main' observed={base_ref!r}"
        )

    head_repository = _repository_identity(
        head.get("repo"),
        label="workflow_run_pull_request_head_repository",
    )
    if (
        head_repository is not None
        and head_repository != run_state["head_repository"]
    ):
        raise BindingError(
            "workflow_run_pull_request_head_repository_mismatch: "
            f"run={run_state['head_repository']!r} "
            f"snapshot={head_repository!r}"
        )

    base_repository = _repository_identity(
        base.get("repo"),
        label="workflow_run_pull_request_base_repository",
    )
    if base_repository is not None and base_repository != repository:
        raise BindingError(
            "workflow_run_pull_request_base_repository_mismatch: "
            f"expected={repository!r} snapshot={base_repository!r}"
        )

    return {
        "number": number,
        "head_sha": head_sha,
        "head_ref": head_ref,
        "head_repository": run_state["head_repository"],
        "base_sha": base_sha,
        "base_ref": base_ref,
        "base_repository": repository,
        "is_fork": run_state["head_repository"] != repository,
        "merge_commit_sha": None,
        "source": "workflow_run_snapshot",
    }


def _validate_associated_pull_request(
    pull_request: Any,
    *,
    index: int,
) -> dict[str, Any]:
    label = f"associated_pull_request_{index}"
    value = _require_object(pull_request, label=label)
    number = _require_int(
        value.get("number"),
        label=f"{label}_number",
        positive=True,
    )
    state = _require_string(value.get("state"), label=f"{label}_state")
    head = _require_object(value.get("head"), label=f"{label}_head")
    base = _require_object(value.get("base"), label=f"{label}_base")

    head_sha = _require_sha40(head.get("sha"), label=f"{label}_head_sha")
    head_ref = _require_string(head.get("ref"), label=f"{label}_head_ref")
    base_sha = _require_sha40(base.get("sha"), label=f"{label}_base_sha")
    base_ref = _require_string(base.get("ref"), label=f"{label}_base_ref")
    head_repository = _repository_identity(
        head.get("repo"),
        label=f"{label}_head_repository",
    )
    base_repository = _repository_identity(
        base.get("repo"),
        label=f"{label}_base_repository",
    )
    merge_commit_sha = _optional_sha40(
        value.get("merge_commit_sha"),
        label=f"{label}_merge_commit_sha",
    )

    return {
        "number": number,
        "state": state,
        "head_sha": head_sha,
        "head_ref": head_ref,
        "head_repository": head_repository,
        "base_sha": base_sha,
        "base_ref": base_ref,
        "base_repository": base_repository,
        "is_fork": head_repository != base_repository,
        "merge_commit_sha": merge_commit_sha,
        "source": "commit_association",
    }


def _resolve_pull_request_snapshot(
    run_state: dict[str, Any],
    *,
    repository: str,
    associated_pull_requests: Any | None,
) -> dict[str, Any] | None:
    snapshots = run_state["pull_requests"]
    if len(snapshots) > 1:
        raise BindingError(
            "workflow_run_pull_request_snapshot_count_invalid: "
            f"observed={len(snapshots)}"
        )
    if len(snapshots) == 1:
        return _validate_workflow_run_snapshot(
            snapshots[0],
            repository=repository,
            run_state=run_state,
        )

    if run_state["head_repository"] != repository:
        return None
    if associated_pull_requests is None:
        return None

    raw_candidates = _require_array(
        associated_pull_requests,
        label="associated_pull_requests",
    )
    candidates: list[dict[str, Any]] = []
    for index, raw_candidate in enumerate(raw_candidates):
        candidate = _validate_associated_pull_request(
            raw_candidate,
            index=index,
        )
        if (
            candidate["state"] == "open"
            and candidate["head_sha"] == run_state["head_sha"]
            and candidate["head_ref"] == run_state["head_branch"]
            and candidate["head_repository"] == run_state["head_repository"]
            and candidate["base_ref"] == "main"
            and candidate["base_repository"] == repository
        ):
            candidates.append(candidate)

    if not candidates:
        return None
    if len(candidates) != 1:
        raise BindingError(
            "associated_pull_request_candidate_count_invalid: "
            f"observed={len(candidates)}"
        )
    return candidates[0]


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


def _skip_result(
    *,
    reason: str,
    event_name: str,
    run_id: int,
    run_state: dict[str, Any],
    pr_number: int | None,
    is_fork: bool,
) -> BindingResult:
    return BindingResult(
        ok=True,
        skip=True,
        reason=reason,
        event_name=event_name,
        ref=None,
        sha=None,
        pr_number=pr_number,
        is_fork=is_fork,
        source_run_id=run_id,
        source_head_sha=run_state["head_sha"],
        source_head_branch=run_state["head_branch"],
    )


def _verify_validated_binding(
    *,
    repository: str,
    run_id: int,
    run_state: dict[str, Any],
    meta: dict[str, Any],
    pull_request_snapshot: dict[str, Any] | None,
    merge_commit: Any | None,
) -> BindingResult:
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

        metadata_ref = f"refs/pull/{meta['pr_number']}/merge"
        if meta["ref"] != metadata_ref:
            raise BindingError(
                "sarif_metadata_ref_mismatch: "
                f"expected={metadata_ref!r} observed={meta['ref']!r}"
            )

        run_is_fork = run_state["head_repository"] != repository
        if meta["is_fork"] != run_is_fork:
            raise BindingError(
                "sarif_metadata_is_fork_mismatch: "
                f"expected={run_is_fork!r} observed={meta['is_fork']!r}"
            )
        if run_is_fork:
            return _skip_result(
                reason="fork_pull_request",
                event_name=event_name,
                run_id=run_id,
                run_state=run_state,
                pr_number=meta["pr_number"],
                is_fork=True,
            )

        if pull_request_snapshot is None:
            return _skip_result(
                reason="pull_request_snapshot_unavailable",
                event_name=event_name,
                run_id=run_id,
                run_state=run_state,
                pr_number=meta["pr_number"],
                is_fork=False,
            )

        expected_ref = f"refs/pull/{pull_request_snapshot['number']}/merge"
        expected = {
            "pr_number": pull_request_snapshot["number"],
            "ref": expected_ref,
            "is_fork": False,
        }
        for field, expected_value in expected.items():
            if meta[field] != expected_value:
                raise BindingError(
                    f"sarif_metadata_{field}_mismatch: "
                    f"expected={expected_value!r} observed={meta[field]!r}"
                )

        if pull_request_snapshot["source"] == "commit_association":
            if pull_request_snapshot["merge_commit_sha"] != meta["sha"]:
                return _skip_result(
                    reason="pull_request_commit_association_drifted",
                    event_name=event_name,
                    run_id=run_id,
                    run_state=run_state,
                    pr_number=pull_request_snapshot["number"],
                    is_fork=False,
                )

        if merge_commit is None:
            raise BindingError("pull_request_merge_commit_snapshot_required")
        _validate_merge_commit(
            merge_commit,
            merge_sha=meta["sha"],
            base_sha=pull_request_snapshot["base_sha"],
            head_sha=pull_request_snapshot["head_sha"],
        )

        reason = (
            "verified_pull_request_merge_snapshot"
            if pull_request_snapshot["source"] == "workflow_run_snapshot"
            else "verified_pull_request_commit_association"
        )
        return BindingResult(
            ok=True,
            skip=False,
            reason=reason,
            event_name=event_name,
            ref=expected_ref,
            sha=meta["sha"],
            pr_number=pull_request_snapshot["number"],
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
        elif run_state["head_branch"].startswith(("v", "V")):
            expected_ref = f"refs/tags/{run_state['head_branch']}"
        else:
            raise BindingError(
                "push_source_ref_outside_pulse_ci_contract: "
                f"head_branch={run_state['head_branch']!r}"
            )
        if meta["ref"] != expected_ref:
            raise BindingError(
                "sarif_metadata_ref_mismatch: "
                f"expected={expected_ref!r} observed={meta['ref']!r}"
            )
        if meta["sha"] != run_state["head_sha"]:
            raise BindingError(
                "sarif_metadata_sha_mismatch: "
                f"expected={run_state['head_sha']!r} observed={meta['sha']!r}"
            )
        return BindingResult(
            ok=True,
            skip=False,
            reason="verified_push",
            event_name=event_name,
            ref=expected_ref,
            sha=run_state["head_sha"],
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
                f"expected={run_state['head_sha']!r} observed={meta['sha']!r}"
            )
        if run_state["head_branch"] != "main" or meta["ref"] != "refs/heads/main":
            return _skip_result(
                reason="workflow_dispatch_ref_not_main",
                event_name=event_name,
                run_id=run_id,
                run_state=run_state,
                pr_number=None,
                is_fork=False,
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


def verify_binding(
    *,
    repository: str,
    run_id: int,
    run: Any,
    metadata: Any,
    merge_commit: Any | None = None,
    associated_pull_requests: Any | None = None,
) -> BindingResult:
    repository = _require_string(repository, label="repository")
    run_id = _require_int(run_id, label="run_id", positive=True)
    run_state = _validate_run(run, repository=repository, run_id=run_id)
    meta = _validate_metadata(metadata)

    pull_request_snapshot: dict[str, Any] | None = None
    if run_state["event_name"] == "pull_request":
        pull_request_snapshot = _resolve_pull_request_snapshot(
            run_state,
            repository=repository,
            associated_pull_requests=associated_pull_requests,
        )

    return _verify_validated_binding(
        repository=repository,
        run_id=run_id,
        run_state=run_state,
        meta=meta,
        pull_request_snapshot=pull_request_snapshot,
        merge_commit=merge_commit,
    )


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

    def get_paginated_array(
        self,
        path: str,
        *,
        label: str,
    ) -> list[Any]:
        items: list[Any] = []
        separator = "&" if "?" in path else "?"
        for page in range(1, ASSOCIATED_PULL_REQUESTS_MAX_PAGES + 1):
            value = self.get(
                path
                + separator
                + f"per_page={ASSOCIATED_PULL_REQUESTS_PAGE_SIZE}&page={page}",
                label=f"{label}_page_{page}",
            )
            page_items = _require_array(
                value,
                label=f"{label}_page_{page}",
            )
            items.extend(page_items)
            if len(page_items) < ASSOCIATED_PULL_REQUESTS_PAGE_SIZE:
                return items
        raise BindingError(
            f"{label}_pagination_limit_exceeded: "
            f"pages={ASSOCIATED_PULL_REQUESTS_MAX_PAGES} "
            f"page_size={ASSOCIATED_PULL_REQUESTS_PAGE_SIZE}"
        )


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
        raise BindingError(f"repository_identity_invalid: {repository!r}")
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
        outputs = {"reason": result.reason, "skip": "true"}
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
        _api_path(
            repository,
            f"/actions/runs/{run_id}?exclude_pull_requests=false",
        ),
        label="workflow_run_api",
    )
    run_state = _validate_run(
        run,
        repository=repository,
        run_id=run_id,
    )
    meta = _validate_metadata(metadata)

    associated_pull_requests: Any | None = None
    if (
        run_state["event_name"] == "pull_request"
        and run_state["head_repository"] == repository
        and len(run_state["pull_requests"]) == 0
    ):
        encoded_head_sha = urllib.parse.quote(
            run_state["head_sha"],
            safe="",
        )
        associated_pull_requests = api.get_paginated_array(
            _api_path(
                repository,
                f"/commits/{encoded_head_sha}/pulls",
            ),
            label="associated_pull_requests_api",
        )

    pull_request_snapshot: dict[str, Any] | None = None
    if run_state["event_name"] == "pull_request":
        pull_request_snapshot = _resolve_pull_request_snapshot(
            run_state,
            repository=repository,
            associated_pull_requests=associated_pull_requests,
        )

    merge_commit: Any | None = None
    if (
        run_state["event_name"] == "pull_request"
        and run_state["head_repository"] == repository
        and pull_request_snapshot is not None
    ):
        merge_commit = api.get(
            _api_path(repository, f"/git/commits/{meta['sha']}"),
            label="pull_request_merge_commit_api",
        )

    result = _verify_validated_binding(
        repository=repository,
        run_id=run_id,
        run_state=run_state,
        meta=meta,
        pull_request_snapshot=pull_request_snapshot,
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
