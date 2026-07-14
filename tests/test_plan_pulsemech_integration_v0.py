#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "tools" / "plan_pulsemech_integration_v0.py"
REQUEST_SCHEMA = ROOT / "schemas" / "pulsemech_integration_request_v0.schema.json"
COMPONENT_MANIFEST_SCHEMA = (
    ROOT / "schemas" / "pulsemech_integration_component_manifest_v0.schema.json"
)
PLAN_SCHEMA = ROOT / "schemas" / "pulsemech_integration_plan_v0.schema.json"
CANONICAL_MANIFEST = (
    ROOT / "integration" / "pulsemech_integration_component_manifest_v0.json"
)
EXAMPLE_REQUEST = (
    ROOT
    / "examples"
    / "integration"
    / "pulsemech_integration_request_core_v0.json"
)
POLICY = ROOT / "pulse_gate_policy_v0.yml"
TOOLS_TESTS_LIST = ROOT / "ci" / "tools-tests.list"

THIS_TEST = "tests/test_plan_pulsemech_integration_v0.py"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_tree(root: Path) -> dict[str, tuple[str, ...]]:
    snapshot: dict[str, tuple[str, ...]] = {}

    for path in sorted(
        root.rglob("*"),
        key=lambda item: item.as_posix(),
    ):
        relative = path.relative_to(root).as_posix()

        if path.is_symlink():
            snapshot[relative] = (
                "symlink",
                os.readlink(path),
            )
        elif path.is_dir():
            snapshot[relative] = ("directory",)
        elif path.is_file():
            snapshot[relative] = (
                "file",
                sha256_bytes(path.read_bytes()),
            )
        else:
            snapshot[relative] = ("non_regular",)

    return snapshot


def run_checked(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, (
        result.stdout + result.stderr
    )


def initialize_git_repository(
    source_root: Path,
) -> str:
    run_checked(
        [
            "git",
            "init",
            "-q",
        ],
        cwd=source_root,
    )

    run_checked(
        [
            "git",
            "config",
            "user.name",
            "PULSEmech planner test",
        ],
        cwd=source_root,
    )

    run_checked(
        [
            "git",
            "config",
            "user.email",
            "pulsemech-planner@example.invalid",
        ],
        cwd=source_root,
    )

    run_checked(
        [
            "git",
            "add",
            ".",
        ],
        cwd=source_root,
    )

    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_DATE": (
                "2000-01-01T00:00:00Z"
            ),
            "GIT_COMMITTER_DATE": (
                "2000-01-01T00:00:00Z"
            ),
        }
    )

    run_checked(
        [
            "git",
            "commit",
            "-q",
            "-m",
            "planner fixture",
        ],
        cwd=source_root,
        env=env,
    )

    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        cwd=source_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, (
        result.stdout + result.stderr
    )

    revision = result.stdout.strip()

    assert len(revision) == 40

    return revision


def build_fixture(
    tmp_path: Path,
) -> dict[str, Path]:
    tmp_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_root = tmp_path / "source"
    target_root = tmp_path / "target"

    source_root.mkdir()
    target_root.mkdir()

    (
        source_root
        / "components"
    ).mkdir()

    (
        source_root
        / "component_tree"
        / "nested"
    ).mkdir(
        parents=True,
    )

    (
        source_root
        / "components"
        / "base.txt"
    ).write_text(
        "base\n",
        encoding="utf-8",
    )

    (
        source_root
        / "components"
        / "root.txt"
    ).write_text(
        "root\n",
        encoding="utf-8",
    )

    (
        source_root
        / "component_tree"
        / "a.txt"
    ).write_text(
        "a\n",
        encoding="utf-8",
    )

    (
        source_root
        / "component_tree"
        / "nested"
        / "b.txt"
    ).write_text(
        "b\n",
        encoding="utf-8",
    )

    (
        source_root
        / "pulse_gate_policy_v0.yml"
    ).write_text(
        "gates:\n"
        "  core_required:\n"
        "    - gate_alpha\n"
        "    - gate_beta\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": (
            "pulsemech_integration_"
            "component_manifest_v0"
        ),
        "manifest_type": (
            "pulsemech_integration_"
            "component_manifest"
        ),
        "source_repository": "example/source",
        "policy_path": (
            "pulse_gate_policy_v0.yml"
        ),
        "components": [
            {
                "id": "base_component",
                "kind": "file",
                "source_path": (
                    "components/base.txt"
                ),
                "target_path": (
                    "vendor/base.txt"
                ),
                "requires": [],
            },
            {
                "id": "tree_component",
                "kind": "tree",
                "source_path": (
                    "component_tree"
                ),
                "target_path": (
                    "vendor/tree"
                ),
                "requires": [
                    "base_component",
                ],
                "exclude_patterns": [],
            },
            {
                "id": "root_component",
                "kind": "file",
                "source_path": (
                    "components/root.txt"
                ),
                "target_path": (
                    "vendor/root.txt"
                ),
                "requires": [
                    "tree_component",
                ],
            },
        ],
        "component_sets": [
            {
                "id": (
                    "canonical_core_lane_v0"
                ),
                "description": (
                    "Synthetic deterministic "
                    "integration fixture."
                ),
                "root_components": [
                    "root_component",
                ],
                "declared_gate_sets": [
                    "core_required",
                ],
                "supported_ci_providers": [
                    "github_actions",
                ],
                "authority_boundary": (
                    "Planning only; no "
                    "release-authority effect."
                ),
            }
        ],
    }

    request = {
        "schema_version": (
            "pulsemech_integration_request_v0"
        ),
        "request_type": (
            "pulsemech_integration_request"
        ),
        "request_id": (
            "synthetic-core-plan-v0"
        ),
        "target_repository": {
            "repository_id": (
                "example/target"
            ),
            "default_branch": "main",
            "ci_provider": (
                "github_actions"
            ),
        },
        "component_sets": [
            "canonical_core_lane_v0",
        ],
        "write_mode": "plan_only",
        "existing_file_policy": {
            "identical": "preserve",
            "different": "conflict",
            "symlink": "conflict",
            "non_regular": "conflict",
        },
    }

    manifest_path = (
        tmp_path
        / "component_manifest.json"
    )

    request_path = (
        tmp_path
        / "request.json"
    )

    write_json(
        manifest_path,
        manifest,
    )

    write_json(
        request_path,
        request,
    )

    initialize_git_repository(
        source_root,
    )

    return {
        "source_root": source_root,
        "target_root": target_root,
        "manifest": manifest_path,
        "request": request_path,
    }


def run_planner(
    fixture: dict[str, Path],
    *,
    request_path: Path | None = None,
    manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> tuple[
    subprocess.CompletedProcess[str],
    dict[str, Any],
]:
    command = [
        sys.executable,
        str(PLANNER),
        "--request",
        str(
            request_path
            or fixture["request"]
        ),
        "--request-schema",
        str(REQUEST_SCHEMA),
        "--component-manifest",
        str(
            manifest_path
            or fixture["manifest"]
        ),
        "--component-manifest-schema",
        str(COMPONENT_MANIFEST_SCHEMA),
        "--plan-schema",
        str(PLAN_SCHEMA),
        "--source-root",
        str(fixture["source_root"]),
        "--target-root",
        str(fixture["target_root"]),
    ]

    if output_path is not None:
        command.extend(
            [
                "--output",
                str(output_path),
            ]
        )

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.stdout, result.stderr

    payload = json.loads(
        result.stdout
    )

    assert isinstance(
        payload,
        dict,
    )

    return result, payload


def operation_for(
    plan: dict[str, Any],
    target_path: str,
) -> dict[str, Any]:
    matches = [
        operation
        for operation
        in plan.get(
            "operations",
            [],
        )
        if operation.get(
            "target_path"
        )
        == target_path
    ]

    assert len(matches) == 1, matches

    return matches[0]


def test_repository_contract_and_canonical_empty_target_plan(
    tmp_path: Path,
) -> None:
    required_paths = (
        PLANNER,
        REQUEST_SCHEMA,
        COMPONENT_MANIFEST_SCHEMA,
        PLAN_SCHEMA,
        CANONICAL_MANIFEST,
        EXAMPLE_REQUEST,
        POLICY,
        TOOLS_TESTS_LIST,
    )

    for path in required_paths:
        assert path.is_file(), path

    request_schema = load_json(
        REQUEST_SCHEMA
    )

    manifest_schema = load_json(
        COMPONENT_MANIFEST_SCHEMA
    )

    plan_schema = load_json(
        PLAN_SCHEMA
    )

    for schema in (
        request_schema,
        manifest_schema,
        plan_schema,
    ):
        jsonschema.Draft202012Validator.check_schema(
            schema
        )

    request = load_json(
        EXAMPLE_REQUEST
    )

    manifest = load_json(
        CANONICAL_MANIFEST
    )

    jsonschema.Draft202012Validator(
        request_schema
    ).validate(
        request
    )

    jsonschema.Draft202012Validator(
        manifest_schema
    ).validate(
        manifest
    )

    component_ids = [
        component["id"]
        for component
        in manifest["components"]
    ]

    assert len(component_ids) == len(
        set(component_ids)
    )

    component_id_set = set(
        component_ids
    )

    for component in manifest[
        "components"
    ]:
        assert set(
            component["requires"]
        ).issubset(
            component_id_set
        )

        source_path = ROOT.joinpath(
            *Path(
                component["source_path"]
            ).parts
        )

        if component["kind"] == "file":
            assert source_path.is_file(), (
                source_path
            )
        else:
            assert source_path.is_dir(), (
                source_path
            )

    target_root = (
        tmp_path
        / "canonical-target"
    )

    target_root.mkdir()

    before = snapshot_tree(
        target_root
    )

    fixture = {
        "source_root": ROOT,
        "target_root": target_root,
        "manifest": CANONICAL_MANIFEST,
        "request": EXAMPLE_REQUEST,
    }

    result, plan = run_planner(
        fixture
    )

    assert result.returncode == 0, (
        result.stdout
        + result.stderr
    )

    jsonschema.Draft202012Validator(
        plan_schema
    ).validate(
        plan
    )

    assert plan[
        "apply_eligible"
    ] is True

    assert plan["conflicts"] == []
    assert plan["unresolved"] == []

    assert (
        plan["summary"]["files_total"]
        > 0
    )

    assert (
        plan["summary"]["create"]
        == plan["summary"]["files_total"]
    )

    assert all(
        operation["action"]
        == "create"
        for operation
        in plan["operations"]
    )

    assert snapshot_tree(
        target_root
    ) == before

    policy = yaml.safe_load(
        POLICY.read_text(
            encoding="utf-8"
        )
    )

    expected_gates = (
        policy["gates"][
            "core_required"
        ]
    )

    planned_gate_sets = (
        plan["selection"][
            "declared_gate_sets"
        ]
    )

    assert len(
        planned_gate_sets
    ) == 1

    assert (
        planned_gate_sets[0]["id"]
        == "core_required"
    )

    assert (
        planned_gate_sets[0]["gates"]
        == expected_gates
    )

    assert (
        planned_gate_sets[0][
            "gate_count"
        ]
        == len(expected_gates)
    )

    entries = [
        line.split(
            "#",
            1,
        )[0].strip()
        for line
        in TOOLS_TESTS_LIST.read_text(
            encoding="utf-8"
        ).splitlines()
    ]

    entries = [
        entry
        for entry in entries
        if entry
    ]

    assert entries.count(
        THIS_TEST
    ) == 1


def test_repeated_planning_is_byte_deterministic(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(
        tmp_path
    )

    before = snapshot_tree(
        fixture["target_root"]
    )

    first_result, first_plan = (
        run_planner(fixture)
    )

    second_result, second_plan = (
        run_planner(fixture)
    )

    assert first_result.returncode == 0
    assert second_result.returncode == 0

    assert (
        first_result.stdout
        == second_result.stdout
    )

    assert first_plan == second_plan

    assert snapshot_tree(
        fixture["target_root"]
    ) == before

    assert (
        first_plan["selection"][
            "resolved_components"
        ]
        == [
            "base_component",
            "root_component",
            "tree_component",
        ]
    )

    assert (
        first_plan["selection"][
            "declared_gate_sets"
        ][0]["gates"]
        == [
            "gate_alpha",
            "gate_beta",
        ]
    )


def test_identical_target_file_is_preserved(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(
        tmp_path
    )

    target_file = (
        fixture["target_root"]
        / "vendor"
        / "base.txt"
    )

    target_file.parent.mkdir(
        parents=True
    )

    target_file.write_bytes(
        (
            fixture["source_root"]
            / "components"
            / "base.txt"
        ).read_bytes()
    )

    result, plan = run_planner(
        fixture
    )

    assert result.returncode == 0, (
        result.stdout
        + result.stderr
    )

    operation = operation_for(
        plan,
        "vendor/base.txt",
    )

    assert (
        operation["target_state"]
        == "identical"
    )

    assert (
        operation["action"]
        == "preserve"
    )

    assert (
        plan["summary"]["preserve"]
        == 1
    )

    assert (
        plan["summary"]["conflict"]
        == 0
    )

    assert plan[
        "apply_eligible"
    ] is True


def test_different_target_file_conflicts_fail_closed(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(
        tmp_path
    )

    target_file = (
        fixture["target_root"]
        / "vendor"
        / "base.txt"
    )

    target_file.parent.mkdir(
        parents=True
    )

    target_file.write_text(
        "different\n",
        encoding="utf-8",
    )

    result, plan = run_planner(
        fixture
    )

    assert result.returncode == 1, (
        result.stdout
        + result.stderr
    )

    operation = operation_for(
        plan,
        "vendor/base.txt",
    )

    assert (
        operation["target_state"]
        == "different"
    )

    assert (
        operation["action"]
        == "conflict"
    )

    assert (
        plan["summary"]["conflict"]
        == 1
    )

    assert plan[
        "apply_eligible"
    ] is False

    assert any(
        finding["path"]
        == "vendor/base.txt"
        for finding
        in plan["conflicts"]
    )


def test_target_path_hazards_fail_closed(
    tmp_path: Path,
) -> None:
    symlink_fixture = build_fixture(
        tmp_path
        / "symlink-case"
    )

    outside = (
        tmp_path
        / "outside.txt"
    )

    outside.write_text(
        "outside\n",
        encoding="utf-8",
    )

    symlink_target = (
        symlink_fixture[
            "target_root"
        ]
        / "vendor"
        / "base.txt"
    )

    symlink_target.parent.mkdir(
        parents=True
    )

    try:
        symlink_target.symlink_to(
            outside
        )
    except OSError as exc:
        pytest.skip(
            "symlink creation "
            f"unavailable: {exc}"
        )

    (
        symlink_result,
        symlink_plan,
    ) = run_planner(
        symlink_fixture
    )

    assert (
        symlink_result.returncode
        == 1
    )

    symlink_operation = (
        operation_for(
            symlink_plan,
            "vendor/base.txt",
        )
    )

    assert (
        symlink_operation[
            "target_state"
        ]
        == "symlink"
    )

    assert (
        symlink_operation["action"]
        == "conflict"
    )

    assert outside.read_text(
        encoding="utf-8"
    ) == "outside\n"

    parent_fixture = build_fixture(
        tmp_path
        / "parent-file-case"
    )

    parent = (
        parent_fixture[
            "target_root"
        ]
        / "vendor"
    )

    parent.write_text(
        "not a directory\n",
        encoding="utf-8",
    )

    (
        parent_result,
        parent_plan,
    ) = run_planner(
        parent_fixture
    )

    assert (
        parent_result.returncode
        == 1
    )

    assert parent_plan[
        "apply_eligible"
    ] is False

    assert any(
        operation["target_state"]
        == (
            "path_component_"
            "non_directory"
        )
        and operation["action"]
        == "conflict"
        for operation
        in parent_plan["operations"]
    )


def test_output_inside_target_is_refused_before_write(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(
        tmp_path
    )

    output_path = (
        fixture["target_root"]
        / (
            "pulsemech_integration_"
            "plan_v0.json"
        )
    )

    before = snapshot_tree(
        fixture["target_root"]
    )

    result, diagnostic = run_planner(
        fixture,
        output_path=output_path,
    )

    assert result.returncode == 2

    assert diagnostic["ok"] is False

    assert (
        diagnostic["exit_kind"]
        == "planner_error"
    )

    assert diagnostic["errors"] == [
        (
            "refusing_to_write_plan_"
            "inside_target_repository"
        )
    ]

    assert not output_path.exists()

    assert snapshot_tree(
        fixture["target_root"]
    ) == before


def test_unsupported_ci_provider_is_unresolved_and_ineligible(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(
        tmp_path
    )

    request = load_json(
        fixture["request"]
    )

    request[
        "target_repository"
    ]["ci_provider"] = "gitlab_ci"

    request_path = (
        tmp_path
        / "request-gitlab.json"
    )

    write_json(
        request_path,
        request,
    )

    result, plan = run_planner(
        fixture,
        request_path=request_path,
    )

    assert result.returncode == 1, (
        result.stdout
        + result.stderr
    )

    assert plan[
        "apply_eligible"
    ] is False

    assert plan["conflicts"] == []

    assert (
        plan["summary"]["unresolved"]
        == 1
    )

    assert plan["unresolved"] == [
        {
            "kind": (
                "unsupported_ci_provider"
            ),
            "path": "gitlab_ci",
            "message": (
                "selected component sets "
                "support: github_actions"
            ),
        }
    ]


def test_manifest_dependency_errors_fail_closed(
    tmp_path: Path,
) -> None:
    missing_fixture = build_fixture(
        tmp_path
        / "missing-case"
    )

    missing_manifest = load_json(
        missing_fixture["manifest"]
    )

    missing_manifest[
        "components"
    ][0]["requires"] = [
        "absent_component"
    ]

    missing_manifest_path = (
        tmp_path
        / (
            "missing-dependency-"
            "manifest.json"
        )
    )

    write_json(
        missing_manifest_path,
        missing_manifest,
    )

    (
        missing_result,
        missing_diagnostic,
    ) = run_planner(
        missing_fixture,
        manifest_path=(
            missing_manifest_path
        ),
    )

    assert (
        missing_result.returncode
        == 2
    )

    assert any(
        "component_dependency_missing"
        in error
        for error
        in missing_diagnostic["errors"]
    )

    cycle_fixture = build_fixture(
        tmp_path
        / "cycle-case"
    )

    cycle_manifest = load_json(
        cycle_fixture["manifest"]
    )

    cycle_manifest[
        "components"
    ][0]["requires"] = [
        "root_component"
    ]

    cycle_manifest_path = (
        tmp_path
        / "cycle-manifest.json"
    )

    write_json(
        cycle_manifest_path,
        cycle_manifest,
    )

    (
        cycle_result,
        cycle_diagnostic,
    ) = run_planner(
        cycle_fixture,
        manifest_path=(
            cycle_manifest_path
        ),
    )

    assert (
        cycle_result.returncode
        == 2
    )

    assert any(
        "component_dependency_cycle"
        in error
        for error
        in cycle_diagnostic["errors"]
    )


if __name__ == "__main__":
    raise SystemExit(
        pytest.main(
            [__file__]
        )
    )
