#!/usr/bin/env python3
"""Build a non-stubbed prod candidate status from required-gate evidence.

Input:
    PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json

Output:
    PULSE_safe_pack_v0/artifacts/status.json

The builder verifies exact ``gates.required`` coverage, current-run identity,
canonical policy/registry bindings, producer and artifact digests, and every
per-gate ``required_gate_evaluation_result_v0`` artifact before writing the
candidate status.

It does not materialize ``release_required`` gates, replace ``check_gates.py``,
or create release authority.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

BUILDER_ID = "pulse_release_grade_candidate_status_builder_v0"
BUILDER_VERSION = "0.1.0"
STATUS_VERSION = "1.0.0"
EVIDENCE_SCHEMA_VERSION = "required_gate_evidence_v0"
RESULT_SCHEMA_VERSION = "required_gate_evaluation_result_v0"
PLAN_SCHEMA_VERSION = "required_gate_evaluation_plan_v0"

TOOL_PATH = "PULSE_safe_pack_v0/tools/build_release_grade_candidate_status_v0.py"
EVIDENCE_PATH = "PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json"
EVIDENCE_SCHEMA_PATH = "schemas/required_gate_evidence_v0.schema.json"
RESULT_SCHEMA_PATH = "schemas/required_gate_evaluation_result_v0.schema.json"
STATUS_SCHEMA_PATH = "schemas/status/status_v1.schema.json"
POLICY_PATH = "pulse_gate_policy_v0.yml"
REGISTRY_PATH = "pulse_gate_registry_v0.yml"
PLAN_PATH = "PULSE_safe_pack_v0/profiles/required_gate_evaluations_v0.json"
OUT_PATH = "PULSE_safe_pack_v0/artifacts/status.json"
ARTIFACT_ROOT = "PULSE_safe_pack_v0/artifacts"
RESULT_ROOT = "PULSE_safe_pack_v0/artifacts/required_gate_inputs"

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GATE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class UniqueYamlLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueYamlLoader,
    node: Any,
    deep: bool = False,
) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)

        if key in out:
            raise ValueError(f"duplicate YAML key {key!r}")

        out[key] = loader.construct_object(value_node, deep=deep)

    return out


UniqueYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _unique_json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key {key!r}")

        out[key] = value

    return out


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value!r}")


def _load_json(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: {path}"
            )
            return None

        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_nonfinite,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label} is not valid JSON: {exc}")
        return None

    if not isinstance(value, dict):
        errors.append(f"{label} must be a JSON object")
        return None

    return value


def _load_yaml(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: {path}"
            )
            return None

        value = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=UniqueYamlLoader,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label} is not valid YAML: {exc}")
        return None

    if not isinstance(value, dict):
        errors.append(f"{label} must be a YAML mapping")
        return None

    return value


def _sha256(
    path: Path,
    label: str,
    errors: list[str],
) -> str | None:
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: {path}"
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
        errors.append(f"{label} could not be hashed: {exc}")
        return None


def _canonical_file(
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
            f"{label} must use canonical path {expected!r}"
        )
        return None

    if canonical.is_symlink() or not canonical.is_file():
        errors.append(
            f"{label} not found as a checked-in regular file: "
            f"{canonical}"
        )
        return None

    return canonical


def _repo_file(
    repo: Path,
    raw: Any,
    label: str,
    errors: list[str],
) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        errors.append(
            f"{label} must be a non-empty repository-relative path"
        )
        return None

    relative = Path(raw.strip())

    if relative.is_absolute():
        errors.append(f"{label} must be repository-relative")
        return None

    resolved = (repo / relative).resolve()

    try:
        resolved.relative_to(repo.resolve())
    except ValueError:
        errors.append(
            f"{label} escapes repository root: {raw!r}"
        )
        return None

    if resolved.is_symlink() or not resolved.is_file():
        errors.append(
            f"{label} not found as a regular repository file: "
            f"{raw!r}"
        )
        return None

    return resolved


def _relative(
    repo: Path,
    path: Path,
) -> str:
    return (
        path.resolve()
        .relative_to(repo.resolve())
        .as_posix()
    )


def _schema_errors(
    payload: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    out: list[str] = []

    for error in sorted(
        validator.iter_errors(payload),
        key=lambda item: list(item.absolute_path),
    ):
        location = ".".join(
            str(part)
            for part in error.absolute_path
        )

        out.append(
            (f"{location}: " if location else "")
            + error.message
        )

    return out


def _object(
    parent: dict[str, Any],
    key: str,
    label: str,
    errors: list[str],
) -> dict[str, Any]:
    value = parent.get(key)

    if not isinstance(value, dict):
        errors.append(f"{label}.{key} must be an object")
        return {}

    return value


def _gate_list(
    value: Any,
    label: str,
    errors: list[str],
) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a non-empty array")
        return []

    out: list[str] = []
    seen: set[str] = set()

    for raw in value:
        gate = raw.strip() if isinstance(raw, str) else ""

        if not GATE_ID_RE.fullmatch(gate):
            errors.append(
                f"{label} contains invalid gate id {raw!r}"
            )

        elif gate in seen:
            errors.append(
                f"{label} contains duplicate gate id {gate!r}"
            )

        else:
            seen.add(gate)
            out.append(gate)

    return out


def _gate_sets(
    policy: dict[str, Any],
    errors: list[str],
) -> tuple[list[str], list[str]]:
    gates = policy.get("gates")

    if not isinstance(gates, dict):
        errors.append(
            "policy must contain canonical top-level gates mapping"
        )
        return [], []

    required = _gate_list(
        gates.get("required"),
        "gates.required",
        errors,
    )
    release_required = _gate_list(
        gates.get("release_required"),
        "gates.release_required",
        errors,
    )

    overlap = sorted(
        set(required) & set(release_required)
    )

    if overlap:
        errors.append(
            "gates.required and gates.release_required "
            f"overlap: {overlap!r}"
        )

    return required, release_required


def _registry_ids(
    registry: dict[str, Any],
    errors: list[str],
) -> set[str]:
    gates = registry.get("gates")

    if not isinstance(gates, dict) or not gates:
        errors.append(
            "registry must contain a non-empty "
            "top-level gates mapping"
        )
        return set()

    out: set[str] = set()

    for raw in gates:
        gate = raw.strip() if isinstance(raw, str) else ""

        if not GATE_ID_RE.fullmatch(gate):
            errors.append(
                f"registry contains invalid gate id {raw!r}"
            )
        else:
            out.add(gate)

    return out


def _plan_entries(
    plan: dict[str, Any],
    required: list[str],
    errors: list[str],
) -> dict[str, tuple[str, str]]:
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        errors.append(
            f"plan.schema_version must be "
            f"{PLAN_SCHEMA_VERSION!r}"
        )

    evaluations = plan.get("evaluations")

    if not isinstance(evaluations, dict) or not evaluations:
        errors.append(
            "plan.evaluations must be a non-empty object"
        )
        return {}

    missing = sorted(
        set(required) - set(evaluations)
    )
    extra = sorted(
        set(evaluations) - set(required)
    )

    if missing:
        errors.append(
            "plan is missing gates.required entries: "
            f"{missing!r}"
        )

    if extra:
        errors.append(
            "plan contains gates outside gates.required: "
            f"{extra!r}"
        )

    out: dict[str, tuple[str, str]] = {}

    for gate in required:
        entry = evaluations.get(gate)

        if not isinstance(entry, dict):
            errors.append(
                f"plan.evaluations.{gate} must be an object"
            )
            continue

        evaluation_id = entry.get("evaluation_id")
        result = entry.get("result")

        if (
            not isinstance(evaluation_id, str)
            or not evaluation_id.strip()
        ):
            errors.append(
                f"plan.evaluations.{gate}.evaluation_id "
                "must be non-empty"
            )
            continue

        if not isinstance(result, dict):
            errors.append(
                f"plan.evaluations.{gate}.result must be an object"
            )
            continue

        artifact = result.get("artifact")

        if (
            not isinstance(artifact, str)
            or not artifact.strip()
        ):
            errors.append(
                f"plan.evaluations.{gate}.result.artifact "
                "must be non-empty"
            )
            continue

        if result.get("json_pointer") != "/pass":
            errors.append(
                f"plan.evaluations.{gate}.result.json_pointer "
                "must be '/pass'"
            )
            continue

        out[gate] = (
            evaluation_id.strip(),
            artifact.strip(),
        )

    return out


def _verify_ref(
    repo: Path,
    ref: dict[str, Any],
    label: str,
    errors: list[str],
) -> tuple[str, Path] | None:
    path = _repo_file(
        repo,
        ref.get("path"),
        f"{label}.path",
        errors,
    )
    expected = ref.get("sha256")

    if path is None:
        return None

    if (
        not isinstance(expected, str)
        or not SHA256_RE.fullmatch(expected)
    ):
        errors.append(
            f"{label}.sha256 must be a 64-hex digest"
        )
        return None

    actual = _sha256(path, label, errors)

    if actual != expected:
        errors.append(
            f"{label}.sha256 mismatch: "
            f"expected {expected!r}, got {actual!r}"
        )
        return None

    return _relative(repo, path), path


def _verify_refs(
    repo: Path,
    raw: Any,
    label: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        errors.append(
            f"{label} must be a non-empty array"
        )
        return {}

    out: dict[str, dict[str, Any]] = {}

    for index, ref in enumerate(raw):
        item_label = f"{label}[{index}]"

        if not isinstance(ref, dict):
            errors.append(
                f"{item_label} must be an object"
            )
            continue

        resolved = _verify_ref(
            repo,
            ref,
            item_label,
            errors,
        )

        if resolved is None:
            continue

        relative, _ = resolved

        if relative in out:
            errors.append(
                f"{label} contains duplicate path {relative!r}"
            )
            continue

        out[relative] = ref

    return out


def _verify_result(
    *,
    repo: Path,
    gate: str,
    evaluation_id: str,
    result_path: Path,
    result_schema: dict[str, Any],
    run_identity: dict[str, Any],
    subject: dict[str, Any],
    policy_sha: str,
    registry_sha: str,
    plan_sha: str,
    errors: list[str],
) -> list[str]:
    result = _load_json(
        result_path,
        f"{gate} result",
        errors,
    )

    if result is None:
        return []

    errors.extend(
        f"{gate} result schema validation failed: {item}"
        for item in _schema_errors(
            result,
            result_schema,
        )
    )

    if result.get("schema_version") != RESULT_SCHEMA_VERSION:
        errors.append(
            f"{gate} result schema_version mismatch"
        )

    if result.get("gate_id") != gate:
        errors.append(
            f"{gate} result gate_id mismatch"
        )

    if result.get("evaluation_id") != evaluation_id:
        errors.append(
            f"{gate} result evaluation_id mismatch"
        )

    if (
        result.get("pass") is not True
        or result.get("status") != "passed"
    ):
        errors.append(
            f"{gate} result must be passed "
            "with literal pass=true"
        )

    if (
        _object(
            result,
            "run_identity",
            f"{gate} result",
            errors,
        )
        != run_identity
    ):
        errors.append(
            f"{gate} result run_identity mismatch"
        )

    if (
        _object(
            result,
            "subject",
            f"{gate} result",
            errors,
        )
        != subject
    ):
        errors.append(
            f"{gate} result subject mismatch"
        )

    policy = _object(
        result,
        "policy_binding",
        f"{gate} result",
        errors,
    )

    if (
        policy.get("policy_path") != POLICY_PATH
        or policy.get("policy_set") != "required"
    ):
        errors.append(
            f"{gate} result policy context mismatch"
        )

    if policy.get("policy_sha256") != policy_sha:
        errors.append(
            f"{gate} result policy digest mismatch"
        )

    registry = _object(
        result,
        "registry_binding",
        f"{gate} result",
        errors,
    )

    if registry.get("registry_path") != REGISTRY_PATH:
        errors.append(
            f"{gate} result registry path mismatch"
        )

    if registry.get("registry_sha256") != registry_sha:
        errors.append(
            f"{gate} result registry digest mismatch"
        )

    plan = _object(
        result,
        "plan_binding",
        f"{gate} result",
        errors,
    )

    if (
        plan.get("plan_path") != PLAN_PATH
        or plan.get("plan_schema_version")
        != PLAN_SCHEMA_VERSION
    ):
        errors.append(
            f"{gate} result plan context mismatch"
        )

    if plan.get("plan_sha256") != plan_sha:
        errors.append(
            f"{gate} result plan digest mismatch"
        )

    evaluator = _object(
        result,
        "evaluator",
        f"{gate} result",
        errors,
    )

    evaluator_ref = {
        "path": evaluator.get("tool_path"),
        "sha256": evaluator.get("tool_sha256"),
    }

    _verify_ref(
        repo,
        evaluator_ref,
        f"{gate} evaluator",
        errors,
    )

    input_refs = _verify_refs(
        repo,
        result.get("input_artifacts"),
        f"{gate} result input_artifacts",
        errors,
    )

    checks = result.get("checks")

    if not isinstance(checks, list) or not checks:
        errors.append(
            f"{gate} result checks must be a non-empty array"
        )

    else:
        for index, check in enumerate(checks):
            label = f"{gate} result checks[{index}]"

            if not isinstance(check, dict):
                errors.append(
                    f"{label} must be an object"
                )
                continue

            if (
                check.get("passed") is not True
                or check.get("exit_code") != 0
            ):
                errors.append(
                    f"{label} must pass with exit_code 0"
                )

            if check.get("diagnostics") not in ([], None):
                errors.append(
                    f"{label}.diagnostics must be empty"
                )

            evidence_paths = check.get("evidence_paths")

            if (
                not isinstance(evidence_paths, list)
                or not evidence_paths
            ):
                errors.append(
                    f"{label}.evidence_paths must be non-empty"
                )

            else:
                for path in evidence_paths:
                    if path not in input_refs:
                        errors.append(
                            f"{label} references unbound "
                            f"artifact {path!r}"
                        )

    if result.get("diagnostics") != []:
        errors.append(
            f"{gate} result diagnostics must be empty"
        )

    warnings = result.get("warnings")

    if not isinstance(warnings, list):
        errors.append(
            f"{gate} result warnings must be an array"
        )
        return []

    out: list[str] = []

    for item in warnings:
        if (
            not isinstance(item, str)
            or not item.strip()
        ):
            errors.append(
                f"{gate} result warnings entries "
                "must be non-empty strings"
            )
        else:
            out.append(item.strip())

    return out


def _created_utc() -> str:
    raw = os.getenv(
        "SOURCE_DATE_EPOCH",
        "",
    ).strip()

    if raw:
        if not raw.isdigit():
            raise ValueError(
                "SOURCE_DATE_EPOCH must be an "
                "integer Unix timestamp"
            )

        value = dt.datetime.fromtimestamp(
            int(raw),
            tz=dt.timezone.utc,
        )

    else:
        value = dt.datetime.now(
            dt.timezone.utc
        )

    return (
        value.replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_candidate_status(
    *,
    repo: Path,
    evidence_path: Path,
    evidence_schema_path: Path,
    result_schema_path: Path,
    status_schema_path: Path,
    policy_path: Path,
    registry_path: Path,
    plan_path: Path,
    builder_path: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    repo = repo.resolve()

    if not repo.is_dir():
        return None, [
            f"repo root must be a directory: {repo}"
        ]

    paths = [
        _canonical_file(
            repo,
            evidence_path,
            EVIDENCE_PATH,
            "required-gate evidence",
            errors,
        ),
        _canonical_file(
            repo,
            evidence_schema_path,
            EVIDENCE_SCHEMA_PATH,
            "evidence schema",
            errors,
        ),
        _canonical_file(
            repo,
            result_schema_path,
            RESULT_SCHEMA_PATH,
            "result schema",
            errors,
        ),
        _canonical_file(
            repo,
            status_schema_path,
            STATUS_SCHEMA_PATH,
            "status schema",
            errors,
        ),
        _canonical_file(
            repo,
            policy_path,
            POLICY_PATH,
            "policy",
            errors,
        ),
        _canonical_file(
            repo,
            registry_path,
            REGISTRY_PATH,
            "registry",
            errors,
        ),
        _canonical_file(
            repo,
            plan_path,
            PLAN_PATH,
            "evaluation plan",
            errors,
        ),
        _canonical_file(
            repo,
            builder_path,
            TOOL_PATH,
            "candidate status builder",
            errors,
        ),
    ]

    if errors:
        return None, errors

    assert all(path is not None for path in paths)

    (
        evidence_path,
        evidence_schema_path,
        result_schema_path,
        status_schema_path,
        policy_path,
        registry_path,
        plan_path,
        builder_path,
    ) = paths  # type: ignore[misc]

    evidence = _load_json(
        evidence_path,
        "required-gate evidence",
        errors,
    )
    evidence_schema = _load_json(
        evidence_schema_path,
        "evidence schema",
        errors,
    )
    result_schema = _load_json(
        result_schema_path,
        "result schema",
        errors,
    )
    status_schema = _load_json(
        status_schema_path,
        "status schema",
        errors,
    )
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
        "evaluation plan",
        errors,
    )

    if any(
        value is None
        for value in (
            evidence,
            evidence_schema,
            result_schema,
            status_schema,
            policy,
            registry,
            plan,
        )
    ):
        return None, errors

    assert evidence is not None
    assert evidence_schema is not None
    assert result_schema is not None
    assert status_schema is not None
    assert policy is not None
    assert registry is not None
    assert plan is not None

    errors.extend(
        "required-gate evidence schema validation failed: "
        + item
        for item in _schema_errors(
            evidence,
            evidence_schema,
        )
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
        "evaluation plan",
        errors,
    )
    evidence_sha = _sha256(
        evidence_path,
        "required-gate evidence",
        errors,
    )
    builder_sha = _sha256(
        builder_path,
        "candidate status builder",
        errors,
    )

    required, release_required = _gate_sets(
        policy,
        errors,
    )
    registry_ids = _registry_ids(
        registry,
        errors,
    )

    unknown = sorted(
        (
            set(required)
            | set(release_required)
        )
        - registry_ids
    )

    if unknown:
        errors.append(
            "policy gates missing from registry: "
            f"{unknown!r}"
        )

    plan_entries = _plan_entries(
        plan,
        required,
        errors,
    )

    if (
        evidence.get("schema_version")
        != EVIDENCE_SCHEMA_VERSION
    ):
        errors.append(
            "evidence.schema_version must be "
            f"{EVIDENCE_SCHEMA_VERSION!r}"
        )

    run_identity = _object(
        evidence,
        "run_identity",
        "evidence",
        errors,
    )
    subject = _object(
        evidence,
        "subject",
        "evidence",
        errors,
    )

    git_sha = run_identity.get("git_sha")
    run_key = run_identity.get("run_key")

    if (
        not isinstance(git_sha, str)
        or not GIT_SHA_RE.fullmatch(git_sha)
    ):
        errors.append(
            "evidence.run_identity.git_sha must be "
            "a concrete 40-hex SHA"
        )

    if (
        not isinstance(run_key, str)
        or not run_key.strip()
    ):
        errors.append(
            "evidence.run_identity.run_key "
            "must be non-empty"
        )

    if run_identity.get("run_mode") != "prod":
        errors.append(
            "evidence.run_identity.run_mode "
            "must be 'prod'"
        )

    if subject.get("commit_sha") != git_sha:
        errors.append(
            "evidence.subject.commit_sha must equal "
            "run_identity.git_sha"
        )

    policy_binding = _object(
        evidence,
        "policy_binding",
        "evidence",
        errors,
    )

    if (
        policy_binding.get("policy_path")
        != POLICY_PATH
        or policy_binding.get("policy_set")
        != "required"
    ):
        errors.append(
            "evidence policy context mismatch"
        )

    if (
        policy_sha is not None
        and policy_binding.get("policy_sha256")
        != policy_sha
    ):
        errors.append(
            "evidence policy digest mismatch"
        )

    registry_binding = _object(
        evidence,
        "registry_binding",
        "evidence",
        errors,
    )

    if (
        registry_binding.get("registry_path")
        != REGISTRY_PATH
    ):
        errors.append(
            "evidence registry path mismatch"
        )

    if (
        registry_sha is not None
        and registry_binding.get("registry_sha256")
        != registry_sha
    ):
        errors.append(
            "evidence registry digest mismatch"
        )

    producer = _object(
        evidence,
        "producer",
        "evidence",
        errors,
    )

    _verify_ref(
        repo,
        {
            "path": producer.get("tool_path"),
            "sha256": producer.get("tool_sha256"),
        },
        "evidence producer",
        errors,
    )

    if producer.get("trusted") is not True:
        errors.append(
            "evidence.producer.trusted must be literal true"
        )

    gates = evidence.get("gates")

    if not isinstance(gates, dict):
        errors.append(
            "evidence.gates must be an object"
        )
        gates = {}

    missing = sorted(
        set(required) - set(gates)
    )
    extra = sorted(
        set(gates) - set(required)
    )

    if missing:
        errors.append(
            "evidence.gates is missing required gates: "
            f"{missing!r}"
        )

    if extra:
        errors.append(
            "evidence.gates contains non-required gates: "
            f"{extra!r}"
        )

    if errors:
        return None, errors

    assert policy_sha is not None
    assert registry_sha is not None
    assert plan_sha is not None
    assert evidence_sha is not None
    assert builder_sha is not None

    final_gates: dict[str, bool] = {}
    result_warnings: list[str] = []
    result_root = (repo / RESULT_ROOT).resolve()

    for gate in required:
        local: list[str] = []
        item = gates.get(gate)

        if not isinstance(item, dict):
            errors.append(
                f"evidence.gates.{gate} must be an object"
            )
            continue

        if (
            item.get("value") is not True
            or item.get("status") != "passed"
        ):
            local.append(
                f"evidence.gates.{gate} must be "
                "passed with literal value=true"
            )

        if item.get("diagnostics") != []:
            local.append(
                f"evidence.gates.{gate}.diagnostics "
                "must be empty"
            )

        plan_item = plan_entries.get(gate)

        if plan_item is None:
            local.append(
                f"no valid plan entry for {gate!r}"
            )
            errors.extend(local)
            continue

        evaluation_id, result_relative = plan_item

        if item.get("evaluation_id") != evaluation_id:
            local.append(
                f"evidence.gates.{gate}.evaluation_id "
                "does not match plan"
            )

        refs = _verify_refs(
            repo,
            item.get("evidence_artifacts"),
            f"evidence.gates.{gate}.evidence_artifacts",
            local,
        )

        result_ref = refs.get(result_relative)

        if result_ref is None:
            local.append(
                f"evidence.gates.{gate} does not bind "
                f"{result_relative!r}"
            )

        else:
            if (
                result_ref.get("kind")
                != "required_gate_evaluation"
            ):
                local.append(
                    f"evidence.gates.{gate} "
                    "result kind mismatch"
                )

            if (
                result_ref.get("schema_version")
                != RESULT_SCHEMA_VERSION
            ):
                local.append(
                    f"evidence.gates.{gate} "
                    "result schema_version mismatch"
                )

        result_path = _repo_file(
            repo,
            result_relative,
            f"{gate} result",
            local,
        )

        if result_path is not None:
            try:
                result_path.relative_to(result_root)
            except ValueError:
                local.append(
                    f"{gate} result must remain under "
                    f"{RESULT_ROOT!r}"
                )

        if (
            result_path is not None
            and result_ref is not None
        ):
            actual = _sha256(
                result_path,
                f"{gate} result",
                local,
            )

            if actual != result_ref.get("sha256"):
                local.append(
                    f"{gate} result digest does not "
                    "match aggregate binding"
                )

            warnings = _verify_result(
                repo=repo,
                gate=gate,
                evaluation_id=evaluation_id,
                result_path=result_path,
                result_schema=result_schema,
                run_identity=run_identity,
                subject=subject,
                policy_sha=policy_sha,
                registry_sha=registry_sha,
                plan_sha=plan_sha,
                errors=local,
            )

            result_warnings.extend(
                f"{gate}: {warning}"
                for warning in warnings
            )

        if local:
            errors.extend(local)
        else:
            final_gates[gate] = True

    if errors:
        return None, errors

    warnings = evidence.get("warnings")

    if not isinstance(warnings, list):
        return None, [
            "evidence.warnings must be an array"
        ]

    clean_warnings: list[str] = []

    for item in warnings:
        if (
            not isinstance(item, str)
            or not item.strip()
        ):
            return None, [
                "evidence.warnings entries must be "
                "non-empty strings"
            ]

        clean_warnings.append(item.strip())

    all_warnings = (
        clean_warnings
        + result_warnings
    )

    try:
        timestamp = _created_utc()
    except ValueError as exc:
        return None, [str(exc)]

    status = {
        "version": STATUS_VERSION,
        "created_utc": timestamp,
        "gates": final_gates,
        "metrics": {
            "run_mode": "prod",
            "git_sha": git_sha,
            "run_key": run_key,
            "gate_policy_path": POLICY_PATH,
            "gate_policy_sha256": policy_sha,
            "gate_registry_path": REGISTRY_PATH,
            "gate_registry_sha256": registry_sha,
            "required_gate_evidence_path": EVIDENCE_PATH,
            "required_gate_evidence_sha256": evidence_sha,
            "required_gate_evidence_schema_version": (
                EVIDENCE_SCHEMA_VERSION
            ),
            "required_gate_evidence_created_utc": (
                evidence.get("created_utc")
            ),
            "required_gate_count": len(required),
            "required_gate_pass_count": len(final_gates),
            "required_gate_evidence_producer": (
                producer.get("id")
            ),
            "candidate_status_builder": BUILDER_ID,
            "candidate_status_builder_version": (
                BUILDER_VERSION
            ),
            "candidate_status_builder_path": TOOL_PATH,
            "candidate_status_builder_sha256": (
                builder_sha
            ),
        },
        "diagnostics": {
            "gates_stubbed": False,
            "scaffold": False,
            "candidate_status": True,
            "required_gate_evidence_warning_count": (
                len(all_warnings)
            ),
            "required_gate_evidence_warnings": (
                all_warnings
            ),
        },
        "meta": {
            "artifact_role": (
                "release_grade_candidate_status"
            ),
            "source_evidence": {
                "path": EVIDENCE_PATH,
                "sha256": evidence_sha,
                "schema_version": (
                    EVIDENCE_SCHEMA_VERSION
                ),
            },
            "authority_boundary": {
                "normative": False,
                "creates_release_authority": False,
                "materializes_release_required": False,
                "replaces_check_gates": False,
            },
        },
    }

    status_errors = _schema_errors(
        status,
        status_schema,
    )

    if status_errors:
        return None, [
            "candidate status schema validation failed: "
            + item
            for item in status_errors
        ]

    if any(
        gate in final_gates
        for gate in release_required
    ):
        return None, [
            "candidate status must not "
            "pre-materialize gates.release_required"
        ]

    return status, []


def _output_path(
    repo: Path,
    raw: Path,
    errors: list[str],
) -> Path | None:
    output = (
        raw.resolve()
        if raw.is_absolute()
        else (repo / raw).resolve()
    )
    root = (repo / ARTIFACT_ROOT).resolve()

    try:
        output.relative_to(root)
    except ValueError:
        errors.append(
            f"output path must remain under "
            f"{ARTIFACT_ROOT!r}"
        )
        return None

    if output == root:
        errors.append(
            "output path must name a file"
        )
        return None

    return output


def main(
    argv: list[str] | None = None,
) -> int:
    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=str(root),
    )
    parser.add_argument(
        "--evidence",
        default=EVIDENCE_PATH,
    )
    parser.add_argument(
        "--evidence-schema",
        default=EVIDENCE_SCHEMA_PATH,
    )
    parser.add_argument(
        "--result-schema",
        default=RESULT_SCHEMA_PATH,
    )
    parser.add_argument(
        "--status-schema",
        default=STATUS_SCHEMA_PATH,
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
        "--out",
        default=OUT_PATH,
    )

    args = parser.parse_args(argv)

    repo = Path(
        args.repo_root
    ).resolve()

    if not repo.is_dir():
        print(
            "ERRORS (fail-closed):\n"
            f" - repo root must be a directory: {repo}",
            file=sys.stderr,
        )
        return 1

    path_errors: list[str] = []

    output = _output_path(
        repo,
        Path(args.out),
        path_errors,
    )

    if output is None:
        print(
            "ERRORS (fail-closed):",
            file=sys.stderr,
        )

        for error in path_errors:
            print(
                f" - {error}",
                file=sys.stderr,
            )

        return 1

    if output.exists() or output.is_symlink():
        if (
            output.is_dir()
            and not output.is_symlink()
        ):
            print(
                "ERRORS (fail-closed):\n"
                " - output path is a directory: "
                f"{output}",
                file=sys.stderr,
            )
            return 1

        output.unlink()

    status, errors = build_candidate_status(
        repo=repo,
        evidence_path=Path(args.evidence),
        evidence_schema_path=Path(
            args.evidence_schema
        ),
        result_schema_path=Path(
            args.result_schema
        ),
        status_schema_path=Path(
            args.status_schema
        ),
        policy_path=Path(args.policy),
        registry_path=Path(args.registry),
        plan_path=Path(args.plan),
        builder_path=Path(TOOL_PATH),
    )

    if status is None:
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

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = output.with_name(
        output.name + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            status,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        output,
    )

    print(f"Wrote {output}")
    print(
        "OK: built non-stubbed prod candidate status "
        "from exact policy-required evidence"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
