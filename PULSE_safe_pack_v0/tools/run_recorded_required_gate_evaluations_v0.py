#!/usr/bin/env python3
"""Run current-run required-gate evaluations and record candidate evidence.

The exact gate set comes from ``gates.required`` in the canonical policy.
Commands come from a checked-in JSON plan and are executed without a shell.
Each plan entry names a checked-in Python evaluator and a JSON result pointer
that must resolve to literal true. Declared outputs are deleted before execution,
then required to be recreated, hashed, and recorded with stdout/stderr.

This tool emits candidate evidence only. It does not write status.json,
materialize release_required gates, replace check_gates.py, or create release
authority.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


OUTPUT_SCHEMA = "required_gate_evidence_v0"
PLAN_SCHEMA = "required_gate_evaluation_plan_v0"
PRODUCER_ID = "pulse_recorded_required_gate_evaluator_v0"
PRODUCER_VERSION = "0.1.0"

TOOL_PATH = (
    "PULSE_safe_pack_v0/tools/"
    "run_recorded_required_gate_evaluations_v0.py"
)
PLAN_PATH = (
    "PULSE_safe_pack_v0/profiles/"
    "required_gate_evaluations_v0.json"
)
POLICY_PATH = "pulse_gate_policy_v0.yml"
REGISTRY_PATH = "pulse_gate_registry_v0.yml"
SCHEMA_PATH = "schemas/required_gate_evidence_v0.schema.json"
OUT_PATH = (
    "PULSE_safe_pack_v0/artifacts/"
    "required_gate_evidence_v0.json"
)
INPUT_ROOT = (
    "PULSE_safe_pack_v0/artifacts/"
    "required_gate_inputs"
)
LOG_ROOT = (
    "PULSE_safe_pack_v0/artifacts/"
    "required_gate_evidence_logs"
)

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GATE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _json_no_duplicates(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key {key!r}")

        out[key] = value

    return out


class _UniqueYamlLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueYamlLoader,
    node: Any,
    deep: bool = False,
) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(
            key_node,
            deep=deep,
        )

        if key in out:
            raise ValueError(
                f"duplicate YAML key {key!r}"
            )

        out[key] = loader.construct_object(
            value_node,
            deep=deep,
        )

    return out


_UniqueYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _load_json(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if not path.is_file():
            errors.append(
                f"{label} not found or not a file: {path}"
            )
            return None

        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_no_duplicates,
            parse_constant=lambda value: (
                _ for _ in ()
            ).throw(
                ValueError(
                    "non-finite JSON constant "
                    f"{value!r}"
                )
            ),
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"{label} is not valid JSON: {exc}"
        )
        return None

    if not isinstance(payload, dict):
        errors.append(
            f"{label} must be a JSON object"
        )
        return None

    return payload


def _load_yaml(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if not path.is_file():
            errors.append(
                f"{label} not found or not a file: {path}"
            )
            return None

        payload = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=_UniqueYamlLoader,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"{label} is not valid YAML: {exc}"
        )
        return None

    if not isinstance(payload, dict):
        errors.append(
            f"{label} must be a YAML mapping"
        )
        return None

    return payload


def _sha256(
    path: Path,
    label: str,
    errors: list[str],
) -> str | None:
    try:
        if not path.is_file():
            errors.append(
                f"{label} not found or not a file: {path}"
            )
            return None

        digest = hashlib.sha256()

        with path.open("rb") as handle:
            for chunk in iter(
                lambda: handle.read(65536),
                b"",
            ):
                digest.update(chunk)

        return digest.hexdigest()

    except OSError as exc:
        errors.append(
            f"{label} could not be hashed: {exc}"
        )
        return None


def _canonical(
    repo: Path,
    supplied: Path,
    expected: str,
    label: str,
    errors: list[str],
) -> Path | None:
    actual = (
        supplied.resolve()
        if supplied.is_absolute()
        else (repo / supplied).resolve()
    )

    canonical = (repo / expected).resolve()

    if actual != canonical:
        errors.append(
            f"{label} must be canonical path "
            f"{expected!r}"
        )
        return None

    if not canonical.is_file():
        errors.append(
            f"{label} not found: {canonical}"
        )
        return None

    return canonical


def _relative(
    repo: Path,
    path: Path,
) -> str:
    return (
        path.resolve()
        .relative_to(repo.resolve())
        .as_posix()
    )


def _gate_list(
    value: Any,
    label: str,
    errors: list[str],
) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(
            f"{label} must be a non-empty array"
        )
        return []

    out: list[str] = []
    seen: set[str] = set()

    for raw in value:
        gate = (
            raw.strip()
            if isinstance(raw, str)
            else ""
        )

        if not GATE_ID_RE.fullmatch(gate):
            errors.append(
                f"{label} contains invalid gate id "
                f"{raw!r}"
            )

        elif gate in seen:
            errors.append(
                f"{label} contains duplicate gate id "
                f"{gate!r}"
            )

        else:
            seen.add(gate)
            out.append(gate)

    return out


def _required_gates(
    policy: dict[str, Any],
    errors: list[str],
) -> list[str]:
    gates = policy.get("gates")

    if not isinstance(gates, dict):
        errors.append(
            "policy must contain canonical "
            "top-level gates mapping"
        )
        return []

    return _gate_list(
        gates.get("required"),
        "gates.required",
        errors,
    )


def _registry_gates(
    registry: dict[str, Any],
    errors: list[str],
) -> set[str]:
    gates = registry.get("gates")

    if not isinstance(gates, dict) or not gates:
        errors.append(
            "registry must contain non-empty "
            "top-level gates mapping"
        )
        return set()

    out: set[str] = set()

    for raw in gates:
        gate = (
            raw.strip()
            if isinstance(raw, str)
            else ""
        )

        if not GATE_ID_RE.fullmatch(gate):
            errors.append(
                "registry contains invalid gate id "
                f"{raw!r}"
            )
        else:
            out.add(gate)

    return out


def _plan_entries(
    plan: dict[str, Any],
    required: list[str],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if plan.get("schema_version") != PLAN_SCHEMA:
        errors.append(
            "plan.schema_version must be "
            f"{PLAN_SCHEMA!r}"
        )

    evaluations = plan.get("evaluations")

    if not isinstance(evaluations, dict) or not evaluations:
        errors.append(
            "plan.evaluations must be a non-empty object"
        )
        return {}

    required_set = set(required)
    planned_set = {
        key
        for key in evaluations
        if isinstance(key, str)
    }

    missing = sorted(
        required_set - planned_set
    )
    extra = sorted(
        planned_set - required_set
    )

    if missing:
        errors.append(
            "plan is missing gates.required entries: "
            f"{missing!r}"
        )

    if extra:
        errors.append(
            "plan contains gates outside "
            f"gates.required: {extra!r}"
        )

    out: dict[str, dict[str, Any]] = {}
    used_paths: set[str] = set()

    for gate in required:
        entry = evaluations.get(gate)
        label = f"plan.evaluations.{gate}"

        if not isinstance(entry, dict):
            errors.append(
                f"{label} must be an object"
            )
            continue

        evaluation_id = entry.get("evaluation_id")
        command = entry.get("command")
        result_spec = entry.get("result")
        artifacts = entry.get("evidence_artifacts")

        if (
            not isinstance(evaluation_id, str)
            or not evaluation_id.strip()
        ):
            errors.append(
                f"{label}.evaluation_id must be "
                "a non-empty string"
            )

        if (
            not isinstance(command, list)
            or len(command) < 2
            or any(
                not isinstance(token, str)
                or not token.strip()
                for token in command
            )
        ):
            errors.append(
                f"{label}.command must contain "
                "{python}, a checked-in evaluator, "
                "and optional arguments"
            )

        elif command[0] != "{python}":
            errors.append(
                f"{label}.command[0] must be "
                "literal '{python}'"
            )

        elif (
            Path(command[1]).is_absolute()
            or not command[1].endswith(".py")
        ):
            errors.append(
                f"{label}.command[1] must be a "
                "repository-relative Python evaluator path"
            )

        if not isinstance(result_spec, dict):
            errors.append(
                f"{label}.result must be an object"
            )
            result_spec = {}

        result_artifact = result_spec.get("artifact")
        result_pointer = result_spec.get("json_pointer")

        if (
            not isinstance(result_artifact, str)
            or not result_artifact.strip()
        ):
            errors.append(
                f"{label}.result.artifact must be "
                "a non-empty string"
            )

        if (
            not isinstance(result_pointer, str)
            or not result_pointer.startswith("/")
        ):
            errors.append(
                f"{label}.result.json_pointer must be "
                "a JSON pointer beginning with '/'"
            )

        if not isinstance(artifacts, list) or not artifacts:
            errors.append(
                f"{label}.evidence_artifacts must be "
                "a non-empty array"
            )
            continue

        normalized: list[dict[str, Any]] = []

        for index, artifact in enumerate(artifacts):
            item_label = (
                f"{label}.evidence_artifacts[{index}]"
            )

            if not isinstance(artifact, dict):
                errors.append(
                    f"{item_label} must be an object"
                )
                continue

            path = artifact.get("path")
            kind = artifact.get("kind")
            schema_version = artifact.get(
                "schema_version"
            )

            if (
                not isinstance(path, str)
                or not path.strip()
            ):
                errors.append(
                    f"{item_label}.path must be "
                    "a non-empty string"
                )
                continue

            path = path.strip()

            if path in used_paths:
                errors.append(
                    "evidence path must be unique "
                    f"across gates: {path!r}"
                )
                continue

            used_paths.add(path)

            if (
                not isinstance(kind, str)
                or not kind.strip()
            ):
                errors.append(
                    f"{item_label}.kind must be "
                    "a non-empty string"
                )
                continue

            if (
                schema_version is not None
                and (
                    not isinstance(schema_version, str)
                    or not schema_version.strip()
                )
            ):
                errors.append(
                    f"{item_label}.schema_version must be "
                    "null or non-empty"
                )
                continue

            normalized.append(
                {
                    "path": path,
                    "kind": kind.strip(),
                    "schema_version": (
                        schema_version.strip()
                        if isinstance(
                            schema_version,
                            str,
                        )
                        else None
                    ),
                }
            )

        artifact_paths = {
            item["path"]
            for item in normalized
        }

        if (
            isinstance(result_artifact, str)
            and result_artifact.strip()
            not in artifact_paths
        ):
            errors.append(
                f"{label}.result.artifact must name "
                "one declared evidence artifact"
            )

        if (
            isinstance(evaluation_id, str)
            and evaluation_id.strip()
            and isinstance(command, list)
            and len(command) >= 2
            and command[0] == "{python}"
            and not Path(command[1]).is_absolute()
            and command[1].endswith(".py")
            and all(
                isinstance(token, str)
                and token.strip()
                for token in command
            )
            and isinstance(result_artifact, str)
            and result_artifact.strip()
            in artifact_paths
            and isinstance(result_pointer, str)
            and result_pointer.startswith("/")
            and normalized
        ):
            out[gate] = {
                "evaluation_id": (
                    evaluation_id.strip()
                ),
                "command": list(command),
                "result": {
                    "artifact": (
                        result_artifact.strip()
                    ),
                    "json_pointer": result_pointer,
                },
                "evidence_artifacts": normalized,
            }

    return out


def _identity(
    repo: Path,
    git_sha: str,
    run_key: str,
    repository: str,
    errors: list[str],
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    sha = (
        git_sha
        or os.getenv("GITHUB_SHA", "")
    ).strip().lower()

    if not sha:
        try:
            sha = subprocess.check_output(
                [
                    "git",
                    "rev-parse",
                    "HEAD",
                ],
                cwd=repo,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip().lower()

        except Exception:  # noqa: BLE001
            sha = ""

    if not GIT_SHA_RE.fullmatch(sha):
        errors.append(
            "git_sha must be a concrete "
            "40-hex commit SHA"
        )
        sha = None

    key = run_key.strip()

    if not key:
        parts = [
            "GITHUB_RUN_ID="
            + os.getenv(
                "GITHUB_RUN_ID",
                "",
            ).strip(),
            "GITHUB_RUN_ATTEMPT="
            + os.getenv(
                "GITHUB_RUN_ATTEMPT",
                "",
            ).strip(),
            "GITHUB_WORKFLOW="
            + os.getenv(
                "GITHUB_WORKFLOW",
                "",
            ).strip(),
        ]

        key = "|".join(
            part
            for part in parts
            if not part.endswith("=")
        )

    if not key:
        errors.append(
            "run_key must be supplied or derivable "
            "from current CI"
        )
        key = None

    repo_name = (
        repository.strip()
        or os.getenv(
            "GITHUB_REPOSITORY",
            "",
        ).strip()
    )

    if not repo_name:
        errors.append(
            "repository must be supplied or available "
            "as GITHUB_REPOSITORY"
        )
        repo_name = None

    return sha, key, repo_name


def _output_path(
    repo: Path,
    raw: str,
    allowed_root: Path,
    label: str,
    errors: list[str],
) -> Path | None:
    candidate = Path(raw)

    if candidate.is_absolute():
        errors.append(
            f"{label} must be repository-relative"
        )
        return None

    resolved = (repo / candidate).resolve()

    try:
        resolved.relative_to(
            allowed_root.resolve()
        )

    except ValueError:
        errors.append(
            f"{label} must be under "
            f"{_relative(repo, allowed_root)!r}"
        )
        return None

    return resolved


def _expand(
    command: list[str],
    repo: Path,
    gate: str,
) -> list[str]:
    values = {
        "{python}": sys.executable,
        "{repo_root}": str(repo),
        "{pack_dir}": str(
            repo / "PULSE_safe_pack_v0"
        ),
        "{artifacts_dir}": str(
            repo
            / "PULSE_safe_pack_v0"
            / "artifacts"
        ),
        "{gate_id}": gate,
    }

    out: list[str] = []

    for token in command:
        for marker, value in values.items():
            token = token.replace(
                marker,
                value,
            )

        out.append(token)

    return out


def _ref(
    repo: Path,
    path: Path,
    kind: str,
    schema_version: str | None,
    errors: list[str],
) -> dict[str, Any] | None:
    digest = _sha256(
        path,
        f"evidence artifact {path}",
        errors,
    )

    if digest is None:
        return None

    return {
        "path": _relative(repo, path),
        "sha256": digest,
        "kind": kind,
        "schema_version": schema_version,
    }


def _json_pointer(
    payload: Any,
    pointer: str,
) -> Any:
    current = payload

    for raw in pointer.split("/")[1:]:
        token = (
            raw
            .replace("~1", "/")
            .replace("~0", "~")
        )

        if (
            isinstance(current, dict)
            and token in current
        ):
            current = current[token]

        elif (
            isinstance(current, list)
            and token.isdigit()
            and int(token) < len(current)
        ):
            current = current[int(token)]

        else:
            raise KeyError(pointer)

    return current


def _validate_schema(
    payload: dict[str, Any],
    schema_path: Path,
) -> list[str]:
    errors: list[str] = []

    schema = _load_json(
        schema_path,
        "required-gate evidence schema",
        errors,
    )

    if schema is None:
        return errors

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    validation_errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: list(
            error.absolute_path
        ),
    )

    for item in validation_errors:
        location = ".".join(
            str(part)
            for part in item.absolute_path
        )

        prefix = (
            f"{location}: "
            if location
            else ""
        )

        errors.append(
            prefix + item.message
        )

    return errors


def run(
    *,
    repo: Path,
    policy_path: Path,
    registry_path: Path,
    plan_path: Path,
    schema_path: Path,
    git_sha: str,
    run_key: str,
    repository: str,
    release_candidate: str | None,
    timeout: int,
) -> tuple[
    dict[str, Any] | None,
    list[str],
    bool,
]:
    errors: list[str] = []
    repo = repo.resolve()

    if not repo.is_dir():
        return (
            None,
            [
                "repo root must be a directory: "
                f"{repo}"
            ],
            False,
        )

    policy_path = _canonical(
        repo,
        policy_path,
        POLICY_PATH,
        "policy",
        errors,
    )

    registry_path = _canonical(
        repo,
        registry_path,
        REGISTRY_PATH,
        "registry",
        errors,
    )

    plan_path = _canonical(
        repo,
        plan_path,
        PLAN_PATH,
        "plan",
        errors,
    )

    schema_path = _canonical(
        repo,
        schema_path,
        SCHEMA_PATH,
        "schema",
        errors,
    )

    tool_path = _canonical(
        repo,
        Path(TOOL_PATH),
        TOOL_PATH,
        "producer tool",
        errors,
    )

    if errors:
        return None, errors, False

    assert policy_path is not None
    assert registry_path is not None
    assert plan_path is not None
    assert schema_path is not None
    assert tool_path is not None

    policy = _load_yaml(
        policy_path,
        "policy",
        errors,
    )

    registry = _load_yaml(
        registry_path,
        "registry",
        errors,
    )

    plan = _load_json(
        plan_path,
        "plan",
        errors,
    )

    if (
        policy is None
        or registry is None
        or plan is None
    ):
        return None, errors, False

    required = _required_gates(
        policy,
        errors,
    )

    registry_ids = _registry_gates(
        registry,
        errors,
    )

    missing_registry = sorted(
        set(required) - registry_ids
    )

    if missing_registry:
        errors.append(
            "required gates missing from registry: "
            f"{missing_registry!r}"
        )

    entries = _plan_entries(
        plan,
        required,
        errors,
    )

    sha, key, repo_name = _identity(
        repo,
        git_sha,
        run_key,
        repository,
        errors,
    )

    if timeout <= 0:
        errors.append(
            "timeout must be greater than zero"
        )

    policy_sha = _sha256(
        policy_path,
        "policy",
        errors,
    )

    registry_sha = _sha256(
        registry_path,
        "registry",
        errors,
    )

    plan_sha = _sha256(
        plan_path,
        "plan",
        errors,
    )

    tool_sha = _sha256(
        tool_path,
        "producer tool",
        errors,
    )

    if errors:
        return None, errors, False

    assert sha is not None
    assert key is not None
    assert repo_name is not None
    assert policy_sha is not None
    assert registry_sha is not None
    assert plan_sha is not None
    assert tool_sha is not None

    input_root = (
        repo / INPUT_ROOT
    ).resolve()

    log_root = (
        repo / LOG_ROOT
    ).resolve()

    input_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    plan_ref = {
        "path": PLAN_PATH,
        "sha256": plan_sha,
        "kind": "evaluation_plan",
        "schema_version": PLAN_SCHEMA,
    }

    gates: dict[str, Any] = {}
    all_passed = True

    for gate in required:
        entry = entries[gate]
        diagnostics: list[str] = []
        prepared: list[
            tuple[
                dict[str, Any],
                Path,
            ]
        ] = []

        for index, descriptor in enumerate(
            entry["evidence_artifacts"]
        ):
            path = _output_path(
                repo,
                descriptor["path"],
                input_root,
                (
                    f"plan.evaluations.{gate}."
                    f"evidence_artifacts[{index}].path"
                ),
                diagnostics,
            )

            if path is None:
                continue

            try:
                if path.exists() or path.is_symlink():
                    if (
                        path.is_dir()
                        and not path.is_symlink()
                    ):
                        diagnostics.append(
                            "declared evidence path is "
                            "a directory: "
                            f"{descriptor['path']!r}"
                        )
                        continue

                    path.unlink()

                path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                prepared.append(
                    (
                        descriptor,
                        path,
                    )
                )

            except OSError as exc:
                diagnostics.append(
                    "could not reset "
                    f"{descriptor['path']!r}: {exc}"
                )

        evaluator_path = (
            repo / entry["command"][1]
        ).resolve()

        try:
            evaluator_path.relative_to(repo)

        except ValueError:
            diagnostics.append(
                "evaluation tool escapes "
                "repository root"
            )

        if (
            evaluator_path.is_symlink()
            or not evaluator_path.is_file()
        ):
            diagnostics.append(
                "evaluation tool must be a checked-in "
                "regular file: "
                f"{entry['command'][1]!r}"
            )

        stdout_path = (
            log_root / f"{gate}.stdout.txt"
        )

        stderr_path = (
            log_root / f"{gate}.stderr.txt"
        )

        stdout = ""
        stderr = ""
        rc: int | None = None

        if not diagnostics:
            env = os.environ.copy()

            env.update(
                {
                    "PULSE_REQUIRED_GATE_ID": gate,
                    (
                        "PULSE_REQUIRED_GATE_"
                        "EVALUATION_ID"
                    ): entry["evaluation_id"],
                    "PULSE_REPO_ROOT": str(repo),
                    "PULSE_ARTIFACT_DIR": str(
                        repo
                        / "PULSE_safe_pack_v0"
                        / "artifacts"
                    ),
                    "PULSE_RUN_MODE": "prod",
                    "PULSE_RUN_KEY": key,
                    "PULSE_GIT_SHA": sha,
                }
            )

            try:
                result = subprocess.run(
                    _expand(
                        entry["command"],
                        repo,
                        gate,
                    ),
                    cwd=repo,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                    check=False,
                )

                rc = result.returncode
                stdout = result.stdout
                stderr = result.stderr

            except subprocess.TimeoutExpired as exc:
                stdout = (
                    exc.stdout.decode(
                        errors="replace"
                    )
                    if isinstance(
                        exc.stdout,
                        bytes,
                    )
                    else str(
                        exc.stdout or ""
                    )
                )

                stderr = (
                    exc.stderr.decode(
                        errors="replace"
                    )
                    if isinstance(
                        exc.stderr,
                        bytes,
                    )
                    else str(
                        exc.stderr or ""
                    )
                )

                diagnostics.append(
                    "evaluation timed out after "
                    f"{timeout} seconds"
                )

            except OSError as exc:
                diagnostics.append(
                    "evaluation command could not run: "
                    f"{exc}"
                )

        stdout_path.write_text(
            stdout,
            encoding="utf-8",
        )

        stderr_path.write_text(
            stderr,
            encoding="utf-8",
        )

        if rc not in (None, 0):
            diagnostics.append(
                "evaluation command exited "
                f"with code {rc}"
            )

        refs: list[dict[str, Any]] = [
            dict(plan_ref)
        ]

        evaluator_ref = _ref(
            repo,
            evaluator_path,
            "evaluation_tool",
            None,
            diagnostics,
        )

        if evaluator_ref:
            refs.append(evaluator_ref)

        for path, kind in (
            (
                stdout_path,
                "evaluation_stdout",
            ),
            (
                stderr_path,
                "evaluation_stderr",
            ),
        ):
            item = _ref(
                repo,
                path,
                kind,
                None,
                diagnostics,
            )

            if item:
                refs.append(item)

        recorded_declared = 0

        for descriptor, path in prepared:
            if (
                path.is_symlink()
                or not path.is_file()
            ):
                diagnostics.append(
                    "declared current-run evidence "
                    "was not produced as a regular file: "
                    f"{descriptor['path']!r}"
                )
                continue

            item = _ref(
                repo,
                path,
                descriptor["kind"],
                descriptor["schema_version"],
                diagnostics,
            )

            if item:
                refs.append(item)
                recorded_declared += 1

        if (
            recorded_declared != len(prepared)
            or recorded_declared == 0
        ):
            diagnostics.append(
                "not all declared current-run evidence "
                "artifacts were recorded"
            )

        result_path = next(
            (
                path
                for descriptor, path in prepared
                if descriptor["path"]
                == entry["result"]["artifact"]
            ),
            None,
        )

        result_value: Any = None

        if (
            result_path is None
            or not result_path.is_file()
        ):
            diagnostics.append(
                "result artifact was not produced"
            )

        else:
            result_payload = _load_json(
                result_path,
                f"{gate} result artifact",
                diagnostics,
            )

            if result_payload is not None:
                try:
                    result_value = _json_pointer(
                        result_payload,
                        entry["result"]["json_pointer"],
                    )

                except KeyError:
                    diagnostics.append(
                        "result JSON pointer "
                        f"{entry['result']['json_pointer']!r} "
                        "was not found"
                    )

                if result_value is not True:
                    diagnostics.append(
                        "result JSON pointer "
                        f"{entry['result']['json_pointer']!r} "
                        "must be literal true"
                    )

        passed = (
            rc == 0
            and result_value is True
            and not diagnostics
        )

        all_passed = (
            all_passed
            and passed
        )

        gates[gate] = {
            "value": passed,
            "status": (
                "passed"
                if passed
                else "failed"
            ),
            "evaluation_id": entry["evaluation_id"],
            "evidence_artifacts": refs,
            "diagnostics": diagnostics,
        }

    payload = {
        "schema_version": OUTPUT_SCHEMA,
        "created_utc": (
            dt.datetime.now(
                dt.timezone.utc
            )
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "run_identity": {
            "git_sha": sha,
            "run_key": key,
            "run_mode": "prod",
        },
        "subject": {
            "repository": repo_name,
            "commit_sha": sha,
            "release_candidate": (
                release_candidate
            ),
        },
        "policy_binding": {
            "policy_path": POLICY_PATH,
            "policy_sha256": policy_sha,
            "policy_set": "required",
        },
        "registry_binding": {
            "registry_path": REGISTRY_PATH,
            "registry_sha256": registry_sha,
        },
        "producer": {
            "id": PRODUCER_ID,
            "version": PRODUCER_VERSION,
            "trusted": True,
            "tool_path": TOOL_PATH,
            "tool_sha256": tool_sha,
        },
        "gates": gates,
        "authority_boundary": {
            "normative": False,
            "creates_release_authority": False,
            "materializes_release_required": False,
            "replaces_check_gates": False,
        },
        "warnings": [],
    }

    schema_errors = _validate_schema(
        payload,
        schema_path,
    )

    if schema_errors:
        return (
            None,
            [
                "schema validation failed: "
                + item
                for item in schema_errors
            ],
            False,
        )

    return payload, [], all_passed


def main(
    argv: list[str] | None = None,
) -> int:
    root = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=str(root),
    )

    parser.add_argument(
        "--policy",
        default=POLICY_PATH,
    )

    parser.add_argument(
        "--registry",
        default=REGISTRY_PATH,
    )

    parser.add_argument(
        "--plan",
        default=PLAN_PATH,
    )

    parser.add_argument(
        "--schema",
        default=SCHEMA_PATH,
    )

    parser.add_argument(
        "--out",
        default=OUT_PATH,
    )

    parser.add_argument(
        "--git-sha",
        default="",
    )

    parser.add_argument(
        "--run-key",
        default="",
    )

    parser.add_argument(
        "--repository",
        default="",
    )

    parser.add_argument(
        "--release-candidate",
        default=os.getenv(
            "GITHUB_REF_NAME",
            "",
        ).strip(),
    )

    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
    )

    args = parser.parse_args(argv)

    repo = Path(
        args.repo_root
    ).resolve()

    out = Path(args.out)

    out = (
        out.resolve()
        if out.is_absolute()
        else (repo / out).resolve()
    )

    try:
        out.relative_to(repo)

    except ValueError:
        print(
            "ERRORS (fail-closed):\n"
            " - output path must remain "
            "inside repository",
            file=sys.stderr,
        )
        return 1

    payload, errors, passed = run(
        repo=repo,
        policy_path=Path(args.policy),
        registry_path=Path(args.registry),
        plan_path=Path(args.plan),
        schema_path=Path(args.schema),
        git_sha=args.git_sha,
        run_key=args.run_key,
        repository=args.repository,
        release_candidate=(
            args.release_candidate.strip()
            or None
        ),
        timeout=args.timeout_seconds,
    )

    if payload is None:
        print(
            "ERRORS (fail-closed):",
            file=sys.stderr,
        )

        for error in errors:
            print(
                f" - {error}",
                file=sys.stderr,
            )

        return 1

    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {out}")

    if not passed:
        print(
            "ERROR: one or more gates failed; "
            "candidate evidence was recorded but "
            "cannot produce a passing prod "
            "candidate status.",
            file=sys.stderr,
        )
        return 1

    print(
        "OK: every policy-required gate has "
        "current-run recorded evidence"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
