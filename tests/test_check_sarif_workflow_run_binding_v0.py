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
        "pull_requests": [] if pull_requests is None else pull_requests,
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


def _workflow_snapshot(
    *,
    number: int = 42,
    head_repository: str = REPOSITORY,
    head_sha: str = HEAD_SHA,
    head_ref: str = "feature",
    base_repository: str = REPOSITORY,
    base_sha: str = BASE_SHA,
    base_ref: str = "main",
) -> dict[str, Any]:
    return {
        "number": number,
        "head": {
            "repo": {
                "url": "https://api.github.com/repos/" + head_repository,
            },
            "sha": head_sha,
            "ref": head_ref,
        },
        "base": {
            "repo": {
                "url": "https://api.github.com/repos/" + base_repository,
            },
            "sha": base_sha,
            "ref": base_ref,
        },
    }


def _associated_pr(
    *,
    number: int = 42,
    state: str = "open",
    head_repository: str = REPOSITORY,
    head_sha: str = HEAD_SHA,
    head_ref: str = "feature",
    base_repository: str = REPOSITORY,
    base_sha: str = BASE_SHA,
    base_ref: str = "main",
    merge_commit_sha: str | None = MERGE_SHA,
) -> dict[str, Any]:
    return {
        "number": number,
        "state": state,
        "head": {
            "repo": {"full_name": head_repository},
            "sha": head_sha,
            "ref": head_ref,
        },
        "base": {
            "repo": {"full_name": base_repository},
            "sha": base_sha,
            "ref": base_ref,
        },
        "merge_commit_sha": merge_commit_sha,
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


def _same_repo_pr_result(
    *,
    pull_requests: list[dict[str, Any]] | None = None,
    associated_pull_requests: Any | None = None,
    metadata: dict[str, Any] | None = None,
    merge_commit: dict[str, Any] | None = None,
) -> Any:
    return tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="pull_request",
            head_branch="feature",
            head_sha=HEAD_SHA,
            pull_requests=pull_requests,
        ),
        metadata=(
            _metadata(
                event="pull_request",
                ref="refs/pull/42/merge",
                sha=MERGE_SHA,
                pr_number=42,
                is_fork=False,
            )
            if metadata is None
            else metadata
        ),
        merge_commit=_merge_commit() if merge_commit is None else merge_commit,
        associated_pull_requests=associated_pull_requests,
    )


def test_workflow_identity_paths() -> None:
    for path in (
        ".github/workflows/pulse_ci.yml",
        ".github/workflows/pulse_ci.yml@refs/heads/main",
    ):
        result = tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(
                event="push",
                head_branch="main",
                head_sha=MAIN_SHA,
                path=path,
            ),
            metadata=_metadata(
                event="push",
                ref="refs/heads/main",
                sha=MAIN_SHA,
            ),
        )
        assert result.reason == "verified_push"

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


def test_push_and_dispatch_contracts() -> None:
    push_main = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(event="push", head_branch="main", head_sha=MAIN_SHA),
        metadata=_metadata(
            event="push",
            ref="refs/heads/main",
            sha=MAIN_SHA,
        ),
    )
    assert push_main.skip is False
    assert push_main.ref == "refs/heads/main"
    assert push_main.sha == MAIN_SHA

    push_tag = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(event="push", head_branch="v1.2.0", head_sha=TAG_SHA),
        metadata=_metadata(
            event="push",
            ref="refs/tags/v1.2.0",
            sha=TAG_SHA,
        ),
    )
    assert push_tag.reason == "verified_push"

    manual_main = tool.verify_binding(
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
    assert manual_main.reason == "verified_workflow_dispatch_main"

    manual_feature = tool.verify_binding(
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
    assert manual_feature.skip is True
    assert manual_feature.reason == "workflow_dispatch_ref_not_main"

    _expect_error(
        "sarif_metadata_sha_mismatch",
        lambda: tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(event="push", head_branch="main", head_sha=MAIN_SHA),
            metadata=_metadata(
                event="push",
                ref="refs/heads/main",
                sha=TAG_SHA,
            ),
        ),
    )


def test_historical_workflow_run_snapshot_passes() -> None:
    result = _same_repo_pr_result(
        pull_requests=[_workflow_snapshot()],
    )
    assert result.skip is False
    assert result.reason == "verified_pull_request_merge_snapshot"
    assert result.ref == "refs/pull/42/merge"
    assert result.sha == MERGE_SHA


def test_empty_snapshot_uses_exact_commit_association() -> None:
    result = _same_repo_pr_result(
        pull_requests=[],
        associated_pull_requests=[_associated_pr()],
    )
    assert result.skip is False
    assert result.reason == "verified_pull_request_commit_association"
    assert result.ref == "refs/pull/42/merge"
    assert result.sha == MERGE_SHA


def test_observed_failure_shape_is_repaired() -> None:
    observed_head_sha = "f135b90d33b526ecdbbb58772a85f9c548b76f55"
    observed_merge_sha = "bf81e4b7f78d94830911193034274ba808101542"
    observed_base_sha = "8" * 40
    run = _run(
        event="pull_request",
        head_branch="HKati-patch-477872",
        head_sha=observed_head_sha,
        pull_requests=[],
    )
    run["id"] = 31392352655

    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=31392352655,
        run=run,
        metadata=_metadata(
            event="pull_request",
            ref="refs/pull/2808/merge",
            sha=observed_merge_sha,
            pr_number=2808,
            is_fork=False,
        ),
        associated_pull_requests=[
            _associated_pr(
                number=2808,
                head_sha=observed_head_sha,
                head_ref="HKati-patch-477872",
                base_sha=observed_base_sha,
                merge_commit_sha=observed_merge_sha,
            )
        ],
        merge_commit=_merge_commit(
            sha=observed_merge_sha,
            base_sha=observed_base_sha,
            head_sha=observed_head_sha,
        ),
    )
    assert result.skip is False
    assert result.reason == "verified_pull_request_commit_association"


def test_unavailable_or_drifted_association_skips_without_upload_target() -> None:
    cases = [
        ([], "pull_request_snapshot_unavailable"),
        ([_associated_pr(state="closed")], "pull_request_snapshot_unavailable"),
        (
            [_associated_pr(merge_commit_sha="6" * 40)],
            "pull_request_commit_association_drifted",
        ),
        (
            [_associated_pr(head_sha="6" * 40)],
            "pull_request_snapshot_unavailable",
        ),
        (
            [_associated_pr(base_ref="release")],
            "pull_request_snapshot_unavailable",
        ),
        (
            [
                _associated_pr(
                    head_repository="attacker/pulse-release-gates-0.1"
                )
            ],
            "pull_request_snapshot_unavailable",
        ),
    ]
    for associated, reason in cases:
        result = _same_repo_pr_result(
            pull_requests=[],
            associated_pull_requests=associated,
        )
        assert result.skip is True
        assert result.reason == reason
        assert result.ref is None
        assert result.sha is None


def test_ambiguous_or_invalid_snapshot_fails_closed() -> None:
    _expect_error(
        "associated_pull_request_candidate_count_invalid",
        lambda: _same_repo_pr_result(
            pull_requests=[],
            associated_pull_requests=[
                _associated_pr(number=41),
                _associated_pr(number=42),
            ],
        ),
    )
    _expect_error(
        "workflow_run_pull_request_snapshot_count_invalid",
        lambda: _same_repo_pr_result(
            pull_requests=[
                _workflow_snapshot(number=41),
                _workflow_snapshot(number=42),
            ],
        ),
    )
    _expect_error(
        "associated_pull_requests_not_array",
        lambda: _same_repo_pr_result(
            pull_requests=[],
            associated_pull_requests={"number": 42},
        ),
    )


def test_artifact_metadata_cannot_select_the_associated_pr() -> None:
    _expect_error(
        "sarif_metadata_pr_number_mismatch",
        lambda: _same_repo_pr_result(
            pull_requests=[],
            associated_pull_requests=[_associated_pr(number=41)],
        ),
    )
    _expect_error(
        "sarif_metadata_ref_mismatch",
        lambda: _same_repo_pr_result(
            pull_requests=[_workflow_snapshot()],
            metadata=_metadata(
                event="pull_request",
                ref="refs/pull/41/merge",
                sha=MERGE_SHA,
                pr_number=42,
                is_fork=False,
            ),
        ),
    )


def test_merge_commit_must_bind_exact_parents() -> None:
    _expect_error(
        "pull_request_merge_commit_parents_mismatch",
        lambda: _same_repo_pr_result(
            pull_requests=[_workflow_snapshot()],
            merge_commit=_merge_commit(base_sha="7" * 40),
        ),
    )
    _expect_error(
        "pull_request_merge_commit_parents_mismatch",
        lambda: _same_repo_pr_result(
            pull_requests=[],
            associated_pull_requests=[_associated_pr()],
            merge_commit=_merge_commit(head_sha="7" * 40),
        ),
    )


def test_fork_contract_remains_fail_closed() -> None:
    fork_repository = "contributor/pulse-release-gates-0.1"
    result = tool.verify_binding(
        repository=REPOSITORY,
        run_id=RUN_ID,
        run=_run(
            event="pull_request",
            head_branch="feature",
            head_sha=HEAD_SHA,
            head_repository=fork_repository,
            pull_requests=[],
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

    _expect_error(
        "sarif_metadata_is_fork_mismatch",
        lambda: tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(
                event="pull_request",
                head_branch="feature",
                head_sha=HEAD_SHA,
                head_repository=fork_repository,
                pull_requests=[],
            ),
            metadata=_metadata(
                event="pull_request",
                ref="refs/pull/42/merge",
                sha=MERGE_SHA,
                pr_number=42,
                is_fork=False,
            ),
        ),
    )


def test_event_and_json_substitution_fail_closed() -> None:
    _expect_error(
        "sarif_metadata_event_mismatch",
        lambda: tool.verify_binding(
            repository=REPOSITORY,
            run_id=RUN_ID,
            run=_run(event="push", head_branch="main", head_sha=MAIN_SHA),
            metadata=_metadata(
                event="workflow_dispatch",
                ref="refs/heads/main",
                sha=MAIN_SHA,
            ),
        ),
    )

    payload = (
        b'{"event_name":"push","event_name":"pull_request",'
        b'"ref":"refs/heads/main","sha":"'
        + MAIN_SHA.encode("ascii")
        + b'","pr_number":null,"is_fork":false}'
    )
    _expect_error(
        "duplicate JSON key",
        lambda: tool.parse_json_bytes(payload, label="sarif_metadata"),
    )


def test_artifact_file_selection_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "a" / "meta").mkdir(parents=True)
        (root / "b" / "artifacts" / "meta").mkdir(parents=True)
        content = json.dumps(
            _metadata(event="push", ref="refs/heads/main", sha=MAIN_SHA)
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


def test_paginated_commit_association_is_bounded() -> None:
    class FollowupApi(tool.GitHubApi):
        def __init__(self) -> None:
            pass

        def get(self, path: str, *, label: str) -> Any:
            if path.endswith("page=1"):
                return [{}] * tool.ASSOCIATED_PULL_REQUESTS_PAGE_SIZE
            if path.endswith("page=2"):
                return [{"number": 101}]
            raise AssertionError(path)

    values = FollowupApi().get_paginated_array(
        "/commits/sha/pulls",
        label="associated",
    )
    assert len(values) == tool.ASSOCIATED_PULL_REQUESTS_PAGE_SIZE + 1

    class UnboundedApi(tool.GitHubApi):
        def __init__(self) -> None:
            pass

        def get(self, path: str, *, label: str) -> Any:
            return [{}] * tool.ASSOCIATED_PULL_REQUESTS_PAGE_SIZE

    _expect_error(
        "pagination_limit_exceeded",
        lambda: UnboundedApi().get_paginated_array(
            "/commits/sha/pulls",
            label="associated",
        ),
    )


def test_source_uses_only_commit_bound_fallback() -> None:
    source = TOOL_PATH.read_text(encoding="utf-8")
    assert "?exclude_pull_requests=false" in source
    assert 'f"/commits/{encoded_head_sha}/pulls"' in source
    assert 'f"/git/commits/{meta[\'sha\']}"' in source
    assert 'f"/pulls/{pr_number}"' not in source
    assert 'f"/git/ref/{encoded_ref}"' not in source
    assert "pull_request_target" not in source
    assert "subprocess" not in source


def test_workflow_wiring_preserves_privileged_boundary() -> None:
    data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)

    trigger = data.get(True)
    if trigger is None:
        trigger = data.get("on")
    assert isinstance(trigger, dict)
    assert set(trigger) == {"workflow_run"}
    assert "workflow_dispatch" not in trigger
    assert "pull_request_target" not in trigger

    assert data["permissions"] == {
        "contents": "read",
        "actions": "read",
        "pull-requests": "read",
        "security-events": "write",
    }

    job = data["jobs"]["upload-sarif"]
    assert (
        job["if"]
        == "github.event.workflow_run.head_repository.id == github.event.repository.id"
    )

    steps = job["steps"]
    assert [step["name"] for step in steps] == [
        "Checkout trusted SARIF binding verifier",
        "Download pulse-report artifact",
        "Verify workflow-run and SARIF artifact binding",
        "Upload SARIF to GitHub code scanning",
    ]

    checkout = steps[0]
    assert re.fullmatch(r"actions/checkout@[0-9a-f]{40}", checkout["uses"])
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
    assert download["with"]["repository"] == "${{ github.repository }}"

    verify = steps[2]
    assert verify["id"] == "target"
    assert verify["env"] == {"GH_TOKEN": "${{ github.token }}"}
    assert "tools/check_sarif_workflow_run_binding_v0.py" in verify["run"]
    assert '--run-id "${{ github.event.workflow_run.id }}"' in verify["run"]

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
        test_workflow_identity_paths,
        test_push_and_dispatch_contracts,
        test_historical_workflow_run_snapshot_passes,
        test_empty_snapshot_uses_exact_commit_association,
        test_observed_failure_shape_is_repaired,
        test_unavailable_or_drifted_association_skips_without_upload_target,
        test_ambiguous_or_invalid_snapshot_fails_closed,
        test_artifact_metadata_cannot_select_the_associated_pr,
        test_merge_commit_must_bind_exact_parents,
        test_fork_contract_remains_fail_closed,
        test_event_and_json_substitution_fail_closed,
        test_artifact_file_selection_fails_closed,
        test_paginated_commit_association_is_bounded,
        test_source_uses_only_commit_bound_fallback,
        test_workflow_wiring_preserves_privileged_boundary,
    ]
    for test in tests:
        test()
    print(
        "OK: SARIF binding preserves trusted default-branch execution, blocks "
        "fork artifacts before download, repairs empty workflow-run PR snapshots "
        "through a read-only exact-head commit association, rejects ambiguity and "
        "drift, validates immutable merge parents, and never derives a privileged "
        "upload target from artifact metadata alone."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
