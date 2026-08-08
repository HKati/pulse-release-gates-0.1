#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "check_sarif_workflow_run_binding_v0.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "upload_sarif.yml"

REPOSITORY = "HKati/pulse-release-gates-0.1"
RUN_ID = 123456789
BASE_SHA = "1" * 40
HEAD_SHA = "2" * 40
MERGE_SHA = "3" * 40
MAIN_SHA = "4" * 40
TAG_SHA = "5" * 40


def _load_tool() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_check_sarif_workflow_run_binding_v0",
        TOOL_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("tool module spec unavailable")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _run(
    *,
    event: str,
    head_branch: str,
    head_sha: str,
    head_repository: str = REPOSITORY,
    pull_requests: list[dict[str, Any]] | None = None,
    path: str = ".github/workflows/pulse_ci.yml",
) -> dict[str, Any]:
    return {
        "id": RUN_ID,
        "name": "PULSE CI",
        "path": path,
        "status": "completed",
        "conclusion": "success",
        "event": event,
        "head_branch": head_branch,
        "head_sha": head_sha,
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": head_repository},
        "pull_requests": pull_requests or [],
    }


def _metadata(
    *,
    event: str,
    ref: str,
    sha: str,
    pr_number: int | None = None,
    is_fork: bool = False,
) -> dict[str, Any]:
    return {
        "event_name": event,
        "ref": ref,
        "sha": sha,
        "pr_number": pr_number,
        "is_fork": is_fork,
    }


def _pull_request_snapshot(
    *,
    number: int = 42,
    head_repository: str = REPOSITORY,
    head_sha: str = HEAD_SHA,
    head_ref: str = "feature",
    base_sha: str = BASE_SHA,
    base_ref: str = "main",
) -> dict[str, Any]:
    return {
        "number": number,
        "head": {
            "repo": {
                "url": "https://api.github.com/repos/"
                + head_repository,
            },
            "sha": head_sha,
            "ref": head_ref,
        },
        "base": {
            "repo": {
                "url": "https://api.github.com/repos/"
                + REPOSITORY,
            },
            "sha": base_sha,
            "ref": base_ref,
        },
    }


def _merge_commit(
    *,
    sha: str = MERGE_SHA,
    base_sha: str = BASE_SHA,
    head_sha: str = HEAD_SHA,
) -> dict[str, Any]:
    return {
        "sha": sha,
        "parents": [
            {"sha": base_sha},
            {"sha": head_sha},
        ],
    }


def _expect_error(
    expected: str,
    function: Callable[[], Any],
) -> None:
    try:
        function()
    except tool.BindingError as exc:
        if expected not in str(exc):
            raise AssertionError(
                f"expected error containing {expected!r}, observed {exc!r}"
            ) from exc
    else:
        raise AssertionError(f"expected BindingError containing {expected!r}")


def test_workflow_path_without_suffix_passes() -> None:
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="push",
            head_branch="main",
            head_sha=MAIN_SHA,
            path=".github/workflows/pulse_ci.yml",
        ),
        metadata=_metadata(
            event="push",
            ref="refs/heads/main",
            sha=MAIN_SHA,
        ),
    )
    assert result.skip is False


def test_workflow_path_with_suffix_passes() -> None:
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="push",
            head_branch="main",
            head_sha=MAIN_SHA,
            path=".github/workflows/pulse_ci.yml@refs/heads/main",
        ),
        metadata=_metadata(
            event="push",
            ref="refs/heads/main",
            sha=MAIN_SHA,
        ),
    )
    assert result.skip is False


def test_workflow_path_prefix_substitution_fails() -> None:
    _expect_error(
        "workflow_run_path_mismatch",
        lambda: tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(
                event="push",
                head_branch="main",
                head_sha=MAIN_SHA,
                path=".github/workflows/pulse_ci.yml.evil@main",
            ),
            metadata=_metadata(
                event="push",
                ref="refs/heads/main",
                sha=MAIN_SHA,
            ),
        ),
    )


def test_push_main_passes() -> None:
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="push",
            head_branch="main",
            head_sha=MAIN_SHA,
        ),
        metadata=_metadata(
            event="push",
            ref="refs/heads/main",
            sha=MAIN_SHA,
        ),
    )
    assert result.ok is True
    assert result.skip is False
    assert result.reason == "verified_push"
    assert result.ref == "refs/heads/main"
    assert result.sha == MAIN_SHA


def test_push_tag_passes() -> None:
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="push",
            head_branch="v1.2.0",
            head_sha=TAG_SHA,
        ),
        metadata=_metadata(
            event="push",
            ref="refs/tags/v1.2.0",
            sha=TAG_SHA,
        ),
    )
    assert result.skip is False
    assert result.ref == "refs/tags/v1.2.0"
    assert result.sha == TAG_SHA


def test_push_hyphenated_tag_passes() -> None:
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="push",
            head_branch="v-rc1",
            head_sha=TAG_SHA,
        ),
        metadata=_metadata(
            event="push",
            ref="refs/tags/v-rc1",
            sha=TAG_SHA,
        ),
    )
    assert result.skip is False
    assert result.ref == "refs/tags/v-rc1"


def test_push_metadata_mismatch_fails() -> None:
    _expect_error(
        "sarif_metadata_sha_mismatch",
        lambda: tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(
                event="push",
                head_branch="main",
                head_sha=MAIN_SHA,
            ),
            metadata=_metadata(
                event="push",
                ref="refs/heads/main",
                sha=TAG_SHA,
            ),
        ),
    )


def test_workflow_dispatch_main_passes() -> None:
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="workflow_dispatch",
            head_branch="main",
            head_sha=MAIN_SHA,
        ),
        metadata=_metadata(
            event="workflow_dispatch",
            ref="refs/heads/main",
            sha=MAIN_SHA,
        ),
    )
    assert result.skip is False
    assert result.reason == "verified_workflow_dispatch_main"


def test_workflow_dispatch_feature_skips() -> None:
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="workflow_dispatch",
            head_branch="feature",
            head_sha=HEAD_SHA,
        ),
        metadata=_metadata(
            event="workflow_dispatch",
            ref="refs/heads/feature",
            sha=HEAD_SHA,
        ),
    )
    assert result.skip is True
    assert result.reason == "workflow_dispatch_ref_not_main"
    assert result.ref is None
    assert result.sha is None


def test_same_repository_pull_request_snapshot_passes() -> None:
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="pull_request",
            head_branch="feature",
            head_sha=HEAD_SHA,
            pull_requests=[_pull_request_snapshot()],
        ),
        metadata=_metadata(
            event="pull_request",
            ref="refs/pull/42/merge",
            sha=MERGE_SHA,
            pr_number=42,
            is_fork=False,
        ),
        merge_commit=_merge_commit(),
    )
    assert result.skip is False
    assert result.reason == "verified_pull_request_merge_snapshot"
    assert result.ref == "refs/pull/42/merge"
    assert result.sha == MERGE_SHA


def test_fork_pull_request_snapshot_skips() -> None:
    fork_repository = "contributor/pulse-release-gates-0.1"
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="pull_request",
            head_branch="feature",
            head_sha=HEAD_SHA,
            head_repository=fork_repository,
            pull_requests=[
                _pull_request_snapshot(
                    head_repository=fork_repository,
                )
            ],
        ),
        metadata=_metadata(
            event="pull_request",
            ref="refs/pull/42/merge",
            sha=MERGE_SHA,
            pr_number=42,
            is_fork=True,
        ),
    )
    assert result.skip is True
    assert result.reason == "fork_pull_request"
    assert result.ref is None
    assert result.sha is None


def test_pull_request_number_substitution_fails() -> None:
    _expect_error(
        "sarif_metadata_pr_number_mismatch",
        lambda: tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(
                event="pull_request",
                head_branch="feature",
                head_sha=HEAD_SHA,
                pull_requests=[_pull_request_snapshot(number=41)],
            ),
            metadata=_metadata(
                event="pull_request",
                ref="refs/pull/42/merge",
                sha=MERGE_SHA,
                pr_number=42,
                is_fork=False,
            ),
            merge_commit=_merge_commit(),
        ),
    )


def test_pull_request_snapshot_head_substitution_fails() -> None:
    _expect_error(
        "workflow_run_pull_request_head_sha_mismatch",
        lambda: tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(
                event="pull_request",
                head_branch="feature",
                head_sha=HEAD_SHA,
                pull_requests=[
                    _pull_request_snapshot(head_sha="6" * 40)
                ],
            ),
            metadata=_metadata(
                event="pull_request",
                ref="refs/pull/42/merge",
                sha=MERGE_SHA,
                pr_number=42,
                is_fork=False,
            ),
            merge_commit=_merge_commit(),
        ),
    )


def test_pull_request_merge_parent_substitution_fails() -> None:
    _expect_error(
        "pull_request_merge_commit_parents_mismatch",
        lambda: tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(
                event="pull_request",
                head_branch="feature",
                head_sha=HEAD_SHA,
                pull_requests=[_pull_request_snapshot()],
            ),
            metadata=_metadata(
                event="pull_request",
                ref="refs/pull/42/merge",
                sha=MERGE_SHA,
                pr_number=42,
                is_fork=False,
            ),
            merge_commit=_merge_commit(base_sha="7" * 40),
        ),
    )


def test_pull_request_live_state_is_not_required() -> None:
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="pull_request",
            head_branch="feature",
            head_sha=HEAD_SHA,
            pull_requests=[_pull_request_snapshot()],
        ),
        metadata=_metadata(
            event="pull_request",
            ref="refs/pull/42/merge",
            sha=MERGE_SHA,
            pr_number=42,
            is_fork=False,
        ),
        merge_commit=_merge_commit(),
    )
    assert result.reason == "verified_pull_request_merge_snapshot"


def test_event_substitution_fails() -> None:
    _expect_error(
        "sarif_metadata_event_mismatch",
        lambda: tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(
                event="push",
                head_branch="main",
                head_sha=MAIN_SHA,
            ),
            metadata=_metadata(
                event="workflow_dispatch",
                ref="refs/heads/main",
                sha=MAIN_SHA,
            ),
        ),
    )


def test_strict_metadata_json_rejects_duplicate_keys() -> None:
    payload = (
        b'{"event_name":"push","event_name":"pull_request",'
        b'"ref":"refs/heads/main","sha":"'
        + MAIN_SHA.encode("ascii")
        + b'","pr_number":null,"is_fork":false}'
    )
    _expect_error(
        "duplicate JSON key",
        lambda: tool.parse_json_bytes(
            payload,
            label="sarif_metadata",
        ),
    )


def test_artifact_selection_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "a" / "meta").mkdir(parents=True)
        (root / "b" / "artifacts" / "meta").mkdir(parents=True)
        content = json.dumps(
            _metadata(
                event="push",
                ref="refs/heads/main",
                sha=MAIN_SHA,
            )
        )
        (root / "a" / "meta" / "sarif_upload.json").write_text(content)
        (
            root
            / "b"
            / "artifacts"
            / "meta"
            / "sarif_upload.json"
        ).write_text(content)
        _expect_error(
            "sarif_metadata_file_count_invalid",
            lambda: tool._select_metadata(root),
        )


def test_verifier_uses_completed_run_snapshot() -> None:
    source = TOOL_PATH.read_text(encoding="utf-8")
    assert "?exclude_pull_requests=false" in source
    assert 'f"/git/commits/{merge_sha}"' in source
    assert 'f"/pulls/{pr_number}"' not in source
    assert 'f"/git/ref/{encoded_ref}"' not in source


def test_workflow_wiring() -> None:
    data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)

    trigger = data.get(True)
    if trigger is None:
        trigger = data.get("on")
    assert isinstance(trigger, dict)
    assert "workflow_run" in trigger
    assert "workflow_dispatch" not in trigger

    permissions = data["permissions"]
    assert permissions == {
        "contents": "read",
        "actions": "read",
        "security-events": "write",
    }

    steps = data["jobs"]["upload-sarif"]["steps"]
    assert [step["name"] for step in steps] == [
        "Checkout trusted SARIF binding verifier",
        "Download pulse-report artifact",
        "Verify workflow-run and SARIF artifact binding",
        "Upload SARIF to GitHub code scanning",
    ]

    checkout = steps[0]
    assert re.fullmatch(
        r"actions/checkout@[0-9a-f]{40}",
        checkout["uses"],
    )
    assert checkout["with"] == {
        "ref": "${{ github.event.repository.default_branch }}",
        "persist-credentials": False,
    }

    download = steps[1]
    assert re.fullmatch(
        r"actions/download-artifact@[0-9a-f]{40}",
        download["uses"],
    )
    assert download["with"]["run-id"] == "${{ github.event.workflow_run.id }}"

    verify = steps[2]
    assert verify["id"] == "target"
    assert (
        "tools/check_sarif_workflow_run_binding_v0.py"
        in verify["run"]
    )
    assert (
        '--run-id "${{ github.event.workflow_run.id }}"'
        in verify["run"]
    )

    upload = steps[3]
    assert re.fullmatch(
        r"github/codeql-action/upload-sarif@[0-9a-f]{40}",
        upload["uses"],
    )
    assert upload["if"] == "steps.target.outputs.skip == 'false'"
    assert upload["with"] == {
        "sarif_file": "${{ steps.target.outputs.sarif_path }}",
        "ref": "${{ steps.target.outputs.ref }}",
        "sha": "${{ steps.target.outputs.sha }}",
        "category": "pulse-gates",
    }


def main() -> int:
    tests = [
        test_workflow_path_without_suffix_passes,
        test_workflow_path_with_suffix_passes,
        test_workflow_path_prefix_substitution_fails,
        test_push_main_passes,
        test_push_tag_passes,
        test_push_hyphenated_tag_passes,
        test_push_metadata_mismatch_fails,
        test_workflow_dispatch_main_passes,
        test_workflow_dispatch_feature_skips,
        test_same_repository_pull_request_snapshot_passes,
        test_fork_pull_request_snapshot_skips,
        test_pull_request_number_substitution_fails,
        test_pull_request_snapshot_head_substitution_fails,
        test_pull_request_merge_parent_substitution_fails,
        test_pull_request_live_state_is_not_required,
        test_event_substitution_fails,
        test_strict_metadata_json_rejects_duplicate_keys,
        test_artifact_selection_fails_closed,
        test_verifier_uses_completed_run_snapshot,
        test_workflow_wiring,
    ]
    for test in tests:
        test()
    print(
        "OK: SARIF workflow-run binding verifies API-derived event, repository, "
        "historical PR snapshot, immutable merge-parent, ref, SHA and fork "
        "identities; preserves "
        "immutable first-party upload wiring; skips fork and unprivileged "
        "manual runs; and fails closed on substitution or duplicate metadata."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
