#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema
import yaml


TOOL_NAME = "plan_pulsemech_integration_v0"
PLAN_SCHEMA_VERSION = "pulsemech_integration_plan_v0"
PLAN_TYPE = "pulsemech_integration_plan"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REQUEST_SCHEMA = (
    ROOT / "schemas" / "pulsemech_integration_request_v0.schema.json"
)
DEFAULT_COMPONENT_MANIFEST = (
    ROOT / "integration" / "pulsemech_integration_component_manifest_v0.json"
)
DEFAULT_COMPONENT_MANIFEST_SCHEMA = (
    ROOT
    / "schemas"
    / "pulsemech_integration_component_manifest_v0.schema.json"
)
DEFAULT_PLAN_SCHEMA = (
    ROOT / "schemas" / "pulsemech_integration_plan_v0.schema.json"
)

CI_MARKERS: dict[str, tuple[str, ...]] = {
    "github_actions": (
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
    ),
    "gitlab_ci": (
        ".gitlab-ci.yml",
    ),
    "circleci": (
        ".circleci/config.yml",
        ".circleci/config.yaml",
    ),
    "jenkins": (
        "Jenkinsfile",
    ),
    "azure_pipelines": (
        "azure-pipelines.yml",
        "azure-pipelines.yaml",
    ),
    "buildkite": (
        ".buildkite/pipeline.yml",
        ".buildkite/pipeline.yaml",
    ),
}


class PlannerError(RuntimeError):
    pass


class StrictJsonError(ValueError):
    pass


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)

        if key in mapping:
            raise PlannerError(f"duplicate YAML key: {key!r}")

        mapping[key] = loader.construct_object(
            value_node,
            deep=deep,
        )

    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic, read-only PULSEmech "
            "target-repository integration plan."
        )
    )

    parser.add_argument(
        "--request",
        required=True,
    )

    parser.add_argument(
        "--request-schema",
        default=str(DEFAULT_REQUEST_SCHEMA),
    )

    parser.add_argument(
        "--component-manifest",
        default=str(DEFAULT_COMPONENT_MANIFEST),
    )

    parser.add_argument(
        "--component-manifest-schema",
        default=str(DEFAULT_COMPONENT_MANIFEST_SCHEMA),
    )

    parser.add_argument(
        "--plan-schema",
        default=str(DEFAULT_PLAN_SCHEMA),
    )

    parser.add_argument(
        "--source-root",
        default=str(ROOT),
    )

    parser.add_argument(
        "--target-root",
        required=True,
    )

    parser.add_argument(
        "--output",
    )

    return parser.parse_args()


def reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise StrictJsonError(
                f"duplicate JSON key: {key}"
            )

        result[key] = value

    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(
        f"non-finite JSON value: {value}"
    )


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )


def load_yaml(path: Path) -> Any:
    return yaml.load(
        path.read_text(encoding="utf-8"),
        Loader=UniqueKeyLoader,
    )


def render_json(data: dict[str, Any]) -> str:
    return (
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return sha256_bytes(encoded)


def schema_errors(
    schema: dict[str, Any],
    value: Any,
) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )

    return [
        (
            f"schema_error[{list(error.path)}]: "
            f"{error.message}"
        )
        for error in sorted(
            validator.iter_errors(value),
            key=lambda err: list(err.path),
        )
    ]


def validate_schema_document(
    schema: dict[str, Any],
    label: str,
) -> None:
    try:
        jsonschema.Draft202012Validator.check_schema(
            schema
        )
    except Exception as exc:
        raise PlannerError(
            f"{label}_schema_invalid: {exc}"
        ) from exc


def validate_document(
    *,
    schema: dict[str, Any],
    value: Any,
    label: str,
) -> None:
    errors = schema_errors(
        schema,
        value,
    )

    if errors:
        raise PlannerError(
            f"{label}_invalid: "
            + "; ".join(errors)
        )


def normalize_relative_path(
    value: str,
    label: str,
) -> str:
    if "\\" in value:
        raise PlannerError(
            f"{label}_contains_backslash: {value}"
        )

    path = PurePosixPath(value)

    if (
        path.is_absolute()
        or value in {"", "."}
        or ".." in path.parts
    ):
        raise PlannerError(
            f"{label}_unsafe_relative_path: {value}"
        )

    return path.as_posix()


def filesystem_path(
    root: Path,
    relative: str,
) -> Path:
    pure = PurePosixPath(relative)

    return root.joinpath(*pure.parts)


def path_is_within(
    path: Path,
    root: Path,
) -> bool:
    try:
        path.resolve(
            strict=False
        ).relative_to(
            root.resolve(strict=False)
        )

        return True
    except ValueError:
        return False


def ensure_root_directory(
    root: Path,
    label: str,
) -> Path:
    if root.is_symlink():
        raise PlannerError(
            f"{label}_root_is_symlink: {root}"
        )

    if not root.is_dir():
        raise PlannerError(
            f"{label}_root_not_directory: {root}"
        )

    return root.resolve()


def git_head(root: Path) -> str:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "HEAD",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "git rev-parse failed"
        )

        raise PlannerError(
            "source_git_revision_unavailable: "
            + message
        )

    revision = result.stdout.strip().lower()

    if (
        len(revision) != 40
        or any(
            character
            not in "0123456789abcdef"
            for character in revision
        )
    ):
        raise PlannerError(
            f"source_git_revision_invalid: "
            f"{revision!r}"
        )

    return revision


def detect_ci_providers(
    target_root: Path,
) -> list[str]:
    detected: list[str] = []

    for provider, patterns in CI_MARKERS.items():
        provider_found = any(
            any(
                target_root.glob(pattern)
            )
            for pattern in patterns
        )

        if provider_found:
            detected.append(provider)

    return sorted(detected)


def manifest_indexes(
    manifest: dict[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    components: dict[
        str,
        dict[str, Any],
    ] = {}

    for component in manifest["components"]:
        component_id = component["id"]

        if component_id in components:
            raise PlannerError(
                f"duplicate_component_id: "
                f"{component_id}"
            )

        components[component_id] = component

    component_sets: dict[
        str,
        dict[str, Any],
    ] = {}

    for component_set in manifest["component_sets"]:
        set_id = component_set["id"]

        if set_id in component_sets:
            raise PlannerError(
                f"duplicate_component_set_id: "
                f"{set_id}"
            )

        component_sets[set_id] = component_set

    for component_id, component in components.items():
        for required_id in component["requires"]:
            if required_id not in components:
                raise PlannerError(
                    "component_dependency_missing: "
                    f"{component_id} requires "
                    f"{required_id}"
                )

    for set_id, component_set in component_sets.items():
        for root_component in component_set[
            "root_components"
        ]:
            if root_component not in components:
                raise PlannerError(
                    "component_set_root_missing: "
                    f"{set_id} references "
                    f"{root_component}"
                )

    return components, component_sets


def resolve_component_closure(
    requested_sets: list[str],
    components: dict[str, dict[str, Any]],
    component_sets: dict[str, dict[str, Any]],
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    requested_roots: list[str] = []
    gate_sets: list[str] = []
    supported_ci: set[str] | None = None

    for set_id in requested_sets:
        if set_id not in component_sets:
            raise PlannerError(
                f"component_set_not_found: {set_id}"
            )

        component_set = component_sets[set_id]

        requested_roots.extend(
            component_set["root_components"]
        )

        gate_sets.extend(
            component_set["declared_gate_sets"]
        )

        current_ci = set(
            component_set["supported_ci_providers"]
        )

        if supported_ci is None:
            supported_ci = current_ci
        else:
            supported_ci = (
                supported_ci
                & current_ci
            )

    if not supported_ci:
        raise PlannerError(
            "selected_component_sets_"
            "have_no_common_ci_provider"
        )

    resolved: set[str] = set()
    visiting: set[str] = set()

    def visit(component_id: str) -> None:
        if component_id in resolved:
            return

        if component_id in visiting:
            raise PlannerError(
                "component_dependency_cycle: "
                f"{component_id}"
            )

        visiting.add(component_id)

        for required_id in components[
            component_id
        ]["requires"]:
            visit(required_id)

        visiting.remove(component_id)
        resolved.add(component_id)

    for root_component in requested_roots:
        visit(root_component)

    return (
        sorted(resolved),
        sorted(set(gate_sets)),
        sorted(supported_ci),
    )


def excluded(
    relative: str,
    patterns: Iterable[str],
) -> bool:
    path = PurePosixPath(relative)

    return any(
        path.match(pattern)
        for pattern in patterns
    )


def first_symlink_component(
    root: Path,
    relative: str,
) -> str | None:
    current = root

    for part in PurePosixPath(relative).parts:
        current = current / part

        if current.is_symlink():
            return current.relative_to(
                root
            ).as_posix()

        if not current.exists():
            return None

    return None


def source_file_rows(
    *,
    source_root: Path,
    component_id: str,
    component: dict[str, Any],
) -> list[dict[str, Any]]:
    source_path = normalize_relative_path(
        component["source_path"],
        (
            f"component[{component_id}]"
            ".source_path"
        ),
    )

    target_path = normalize_relative_path(
        component["target_path"],
        (
            f"component[{component_id}]"
            ".target_path"
        ),
    )

    source = filesystem_path(
        source_root,
        source_path,
    )

    source_symlink_component = (
        first_symlink_component(
            source_root,
            source_path,
        )
    )

    if source_symlink_component is not None:
        raise PlannerError(
            "source_component_path_contains_symlink: "
            f"{source_symlink_component}"
        )

    if component["kind"] == "file":
        try:
            mode = source.stat().st_mode
        except FileNotFoundError as exc:
            raise PlannerError(
                "source_component_missing: "
                f"{source_path}"
            ) from exc

        if not stat.S_ISREG(mode):
            raise PlannerError(
                "source_component_not_regular_file: "
                f"{source_path}"
            )

        return [
            {
                "component_id": component_id,
                "source_path": source_path,
                "target_path": target_path,
                "source_sha256": (
                    sha256_file(source)
                ),
                "source_size_bytes": (
                    source.stat().st_size
                ),
            }
        ]

    if component["kind"] != "tree":
        raise PlannerError(
            "unsupported_component_kind: "
            f"{component['kind']}"
        )

    if not source.is_dir():
        raise PlannerError(
            "source_component_tree_missing: "
            f"{source_path}"
        )

    patterns = component.get(
        "exclude_patterns",
        [],
    )

    rows: list[dict[str, Any]] = []

    for (
        current_root,
        dir_names,
        file_names,
    ) in os.walk(
        source,
        followlinks=False,
    ):
        current = Path(current_root)

        dir_names.sort()
        file_names.sort()

        for directory_name in list(dir_names):
            directory_path = (
                current
                / directory_name
            )

            relative_to_tree = (
                directory_path
                .relative_to(source)
                .as_posix()
            )

            if excluded(
                relative_to_tree,
                patterns,
            ):
                dir_names.remove(
                    directory_name
                )

                continue

            if directory_path.is_symlink():
                raise PlannerError(
                    "source_component_tree_"
                    "contains_symlink: "
                    f"{source_path}/"
                    f"{relative_to_tree}"
                )

        for file_name in file_names:
            file_path = (
                current
                / file_name
            )

            relative_to_tree = (
                file_path
                .relative_to(source)
                .as_posix()
            )

            if excluded(
                relative_to_tree,
                patterns,
            ):
                continue

            if file_path.is_symlink():
                raise PlannerError(
                    "source_component_tree_"
                    "contains_symlink: "
                    f"{source_path}/"
                    f"{relative_to_tree}"
                )

            mode = file_path.stat().st_mode

            if not stat.S_ISREG(mode):
                raise PlannerError(
                    "source_component_tree_"
                    "contains_non_regular_file: "
                    f"{source_path}/"
                    f"{relative_to_tree}"
                )

            rows.append(
                {
                    "component_id": component_id,
                    "source_path": (
                        f"{source_path}/"
                        f"{relative_to_tree}"
                    ),
                    "target_path": (
                        f"{target_path}/"
                        f"{relative_to_tree}"
                    ),
                    "source_sha256": (
                        sha256_file(file_path)
                    ),
                    "source_size_bytes": (
                        file_path
                        .stat()
                        .st_size
                    ),
                }
            )

    return rows


def collect_source_rows(
    *,
    source_root: Path,
    resolved_components: list[str],
    components: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    by_target: dict[
        str,
        dict[str, Any],
    ] = {}

    for component_id in resolved_components:
        rows = source_file_rows(
            source_root=source_root,
            component_id=component_id,
            component=components[component_id],
        )

        for row in rows:
            target_path = row["target_path"]
            existing = by_target.get(target_path)

            if existing is None:
                by_target[target_path] = row

                continue

            if (
                existing["source_path"]
                != row["source_path"]
                or existing["source_sha256"]
                != row["source_sha256"]
            ):
                raise PlannerError(
                    "target_path_collision: "
                    f"{target_path} from "
                    f"{existing['component_id']} "
                    f"and {component_id}"
                )

    return [
        by_target[path]
        for path in sorted(by_target)
    ]


def first_non_directory_parent(
    target_root: Path,
    relative: str,
) -> str | None:
    current = target_root
    parts = PurePosixPath(relative).parts

    for part in parts[:-1]:
        current = current / part

        if not current.exists():
            return None

        if current.is_symlink():
            return None

        if not current.is_dir():
            return current.relative_to(
                target_root
            ).as_posix()

    return None


def classify_target(
    *,
    target_root: Path,
    row: dict[str, Any],
) -> tuple[str, str, str]:
    target_path = row["target_path"]

    symlink_component = (
        first_symlink_component(
            target_root,
            target_path,
        )
    )

    if symlink_component is not None:
        if symlink_component == target_path:
            return (
                "symlink",
                "conflict",
                "target path is a symlink",
            )

        return (
            "path_component_symlink",
            "conflict",
            (
                "target parent path is "
                "a symlink: "
                f"{symlink_component}"
            ),
        )

    non_directory_parent = (
        first_non_directory_parent(
            target_root,
            target_path,
        )
    )

    if non_directory_parent is not None:
        return (
            "path_component_non_directory",
            "conflict",
            (
                "target parent path is not "
                "a directory: "
                f"{non_directory_parent}"
            ),
        )

    target = filesystem_path(
        target_root,
        target_path,
    )

    if not target.exists():
        return (
            "missing",
            "create",
            "target file is absent",
        )

    if target.is_dir():
        return (
            "directory",
            "conflict",
            "target path is a directory",
        )

    mode = target.stat().st_mode

    if not stat.S_ISREG(mode):
        return (
            "non_regular",
            "conflict",
            (
                "target path is not "
                "a regular file"
            ),
        )

    if (
        sha256_file(target)
        == row["source_sha256"]
    ):
        return (
            "identical",
            "preserve",
            (
                "target file already matches "
                "source digest"
            ),
        )

    return (
        "different",
        "conflict",
        (
            "target file exists with "
            "a different digest"
        ),
    )


def materialize_gate_sets(
    *,
    policy: dict[str, Any],
    gate_set_ids: list[str],
) -> list[dict[str, Any]]:
    gates_root = policy.get("gates")

    if not isinstance(gates_root, dict):
        raise PlannerError(
            "policy_missing_gates_mapping"
        )

    result: list[dict[str, Any]] = []

    for gate_set_id in gate_set_ids:
        gates = gates_root.get(gate_set_id)

        if (
            not isinstance(gates, list)
            or not gates
        ):
            raise PlannerError(
                "policy_gate_set_missing_or_empty: "
                f"{gate_set_id}"
            )

        if not all(
            isinstance(gate, str)
            and gate
            for gate in gates
        ):
            raise PlannerError(
                "policy_gate_set_has_invalid_gate: "
                f"{gate_set_id}"
            )

        if len(gates) != len(set(gates)):
            raise PlannerError(
                "policy_gate_set_has_duplicate_gate: "
                f"{gate_set_id}"
            )

        result.append(
            {
                "id": gate_set_id,
                "gate_count": len(gates),
                "gates": gates,
                "sha256": canonical_digest(
                    gates
                ),
            }
        )

    return result


def relative_display(
    path: Path,
    root: Path,
) -> str:
    try:
        return (
            path.resolve()
            .relative_to(root.resolve())
            .as_posix()
        )
    except ValueError:
        return path.name


def make_finding(
    kind: str,
    path: str,
    message: str,
) -> dict[str, str]:
    return {
        "kind": kind,
        "path": path,
        "message": message,
    }


def build_plan(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    source_root = ensure_root_directory(
        Path(args.source_root),
        "source",
    )

    target_root = ensure_root_directory(
        Path(args.target_root),
        "target",
    )

    request_path = Path(
        args.request
    ).resolve()

    request_schema_path = Path(
        args.request_schema
    ).resolve()

    manifest_path = Path(
        args.component_manifest
    ).resolve()

    manifest_schema_path = Path(
        args.component_manifest_schema
    ).resolve()

    plan_schema_path = Path(
        args.plan_schema
    ).resolve()

    request = load_json(request_path)
    request_schema = load_json(
        request_schema_path
    )
    manifest = load_json(manifest_path)
    manifest_schema = load_json(
        manifest_schema_path
    )
    plan_schema = load_json(
        plan_schema_path
    )

    for schema, label in (
        (
            request_schema,
            "request",
        ),
        (
            manifest_schema,
            "component_manifest",
        ),
        (
            plan_schema,
            "plan",
        ),
    ):
        if not isinstance(schema, dict):
            raise PlannerError(
                f"{label}_schema_not_object"
            )

        validate_schema_document(
            schema,
            label,
        )

    validate_document(
        schema=request_schema,
        value=request,
        label="request",
    )

    validate_document(
        schema=manifest_schema,
        value=manifest,
        label="component_manifest",
    )

    if request["write_mode"] != "plan_only":
        raise PlannerError(
            "write_mode_must_be_plan_only"
        )

    (
        components,
        component_sets,
    ) = manifest_indexes(manifest)

    (
        resolved_components,
        gate_set_ids,
        supported_ci,
    ) = resolve_component_closure(
        request["component_sets"],
        components,
        component_sets,
    )

    declared_ci = request[
        "target_repository"
    ]["ci_provider"]

    unresolved: list[
        dict[str, str]
    ] = []

    if declared_ci not in supported_ci:
        unresolved.append(
            make_finding(
                "unsupported_ci_provider",
                declared_ci,
                (
                    "selected component sets "
                    "support: "
                    + ", ".join(supported_ci)
                ),
            )
        )

    policy_relative = normalize_relative_path(
        manifest["policy_path"],
        "policy_path",
    )

    policy_path = filesystem_path(
        source_root,
        policy_relative,
    )

    if (
        policy_path.is_symlink()
        or not policy_path.is_file()
    ):
        raise PlannerError(
            "policy_path_missing_or_unsafe: "
            f"{policy_relative}"
        )

    policy = load_yaml(policy_path)

    if not isinstance(policy, dict):
        raise PlannerError(
            "policy_not_mapping"
        )

    gate_sets = materialize_gate_sets(
        policy=policy,
        gate_set_ids=gate_set_ids,
    )

    source_rows = collect_source_rows(
        source_root=source_root,
        resolved_components=(
            resolved_components
        ),
        components=components,
    )

    operations: list[
        dict[str, Any]
    ] = []

    conflicts: list[
        dict[str, str]
    ] = []

    for row in source_rows:
        (
            target_state,
            action,
            reason,
        ) = classify_target(
            target_root=target_root,
            row=row,
        )

        operation = {
            **row,
            "target_state": target_state,
            "action": action,
            "reason": reason,
        }

        operations.append(operation)

        if action == "conflict":
            conflicts.append(
                make_finding(
                    f"target_{target_state}",
                    row["target_path"],
                    reason,
                )
            )

    detected_ci = detect_ci_providers(
        target_root
    )

    counts = {
        "create": 0,
        "preserve": 0,
        "conflict": 0,
    }

    for operation in operations:
        counts[
            operation["action"]
        ] += 1

    summary = {
        "files_total": len(operations),
        "create": counts["create"],
        "preserve": counts["preserve"],
        "conflict": counts["conflict"],
        "source_missing": 0,
        "unresolved": len(unresolved),
    }

    apply_eligible = (
        not conflicts
        and not unresolved
    )

    plan: dict[str, Any] = {
        "schema_version": (
            PLAN_SCHEMA_VERSION
        ),
        "plan_type": PLAN_TYPE,
        "tool": TOOL_NAME,
        "request_id": (
            request["request_id"]
        ),
        "source": {
            "repository": (
                manifest[
                    "source_repository"
                ]
            ),
            "revision": git_head(
                source_root
            ),
            "component_manifest_path": (
                relative_display(
                    manifest_path,
                    source_root,
                )
            ),
            "component_manifest_sha256": (
                sha256_file(
                    manifest_path
                )
            ),
            "policy_path": policy_relative,
            "policy_sha256": (
                sha256_file(policy_path)
            ),
        },
        "target": {
            "repository_id": (
                request[
                    "target_repository"
                ]["repository_id"]
            ),
            "default_branch": (
                request[
                    "target_repository"
                ]["default_branch"]
            ),
            "declared_ci_provider": (
                declared_ci
            ),
            "detected_ci_providers": (
                detected_ci
            ),
        },
        "selection": {
            "component_sets": sorted(
                request["component_sets"]
            ),
            "resolved_components": (
                resolved_components
            ),
            "declared_gate_sets": gate_sets,
        },
        "operations": operations,
        "conflicts": conflicts,
        "unresolved": unresolved,
        "summary": summary,
        "apply_eligible": apply_eligible,
        "authority_boundary": {
            "write_mode": "plan_only",
            "writes_target_repository": False,
            "changes_release_authority": False,
            "changes_gate_policy": False,
            "changes_gate_semantics": False,
            "creates_release_decision": False,
        },
    }

    validate_document(
        schema=plan_schema,
        value=plan,
        label="generated_plan",
    )

    return (
        plan,
        0 if apply_eligible else 1,
    )


def diagnostic(
    message: str,
) -> dict[str, Any]:
    return {
        "tool": TOOL_NAME,
        "ok": False,
        "exit_kind": "planner_error",
        "errors": [
            message,
        ],
    }


def output_is_inside_target(
    output: Path,
    target_root: Path,
) -> bool:
    output_resolved = output.resolve(
        strict=False
    )

    target_resolved = target_root.resolve(
        strict=False
    )

    try:
        output_resolved.relative_to(
            target_resolved
        )

        return True
    except ValueError:
        return False


def main() -> int:
    args = parse_args()

    target_root = Path(
        args.target_root
    )

    output = (
        Path(args.output)
        if args.output
        else None
    )

    if (
        output is not None
        and output_is_inside_target(
            output,
            target_root,
        )
    ):
        sys.stdout.write(
            render_json(
                diagnostic(
                    "refusing_to_write_plan_"
                    "inside_target_repository"
                )
            )
        )

        return 2

    try:
        plan, exit_code = build_plan(args)
    except Exception as exc:
        sys.stdout.write(
            render_json(
                diagnostic(str(exc))
            )
        )

        return 2

    rendered = render_json(plan)

    sys.stdout.write(rendered)

    if output is not None:
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            rendered,
            encoding="utf-8",
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
