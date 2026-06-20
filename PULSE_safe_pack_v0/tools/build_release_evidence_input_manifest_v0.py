#!/usr/bin/env python3
"""Build the runtime release_evidence_input_manifest_v0 artifact.

Input:
    PULSE_safe_pack_v0/artifacts/recorded_release_candidate_index_v0.json

Output:
    PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json

The builder re-verifies every candidate envelope, its raw-evidence digest,
producer provenance, run/subject binding, policy/registry context, validation
checks, and exact gates.release_required coverage before producing the existing
recorded-evidence verifier manifest.

This tool does not verify evidence itself, materialize gates, write status.json,
replace check_gates.py, or create release authority.
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


MANIFEST_SCHEMA_VERSION = "release_evidence_input_manifest_v0"
MANIFEST_ID = "release_evidence_input_manifest_v0"
MANIFEST_VERSION = "0.1.0"
INDEX_SCHEMA_VERSION = "recorded_release_candidate_index_v0"
ENVELOPE_SCHEMA_VERSION = "recorded_release_candidate_envelope_v0"

TOOL_PATH = (
    "PULSE_safe_pack_v0/tools/"
    "build_release_evidence_input_manifest_v0.py"
)
INDEX_PATH = (
    "PULSE_safe_pack_v0/artifacts/"
    "recorded_release_candidate_index_v0.json"
)
CANDIDATE_DIR = (
    "PULSE_safe_pack_v0/artifacts/"
    "recorded_release_candidates"
)
STATUS_PATH = "PULSE_safe_pack_v0/artifacts/status.json"
REQUIRED_EVIDENCE_PATH = (
    "PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json"
)
THRESHOLDS_PATH = "PULSE_safe_pack_v0/profiles/external_thresholds.yaml"
POLICY_PATH = "pulse_gate_policy_v0.yml"
REGISTRY_PATH = "pulse_gate_registry_v0.yml"
ENVELOPE_SCHEMA_PATH = (
    "schemas/recorded_release_candidate_envelope_v0.schema.json"
)
MANIFEST_SCHEMA_PATH = (
    "schemas/release_evidence_input_manifest_v0.schema.json"
)
MANIFEST_CHECKER_PATH = (
    "PULSE_safe_pack_v0/tools/"
    "check_release_evidence_input_manifest_v0.py"
)
OUT_PATH = (
    "PULSE_safe_pack_v0/artifacts/"
    "release_evidence_input_manifest_v0.json"
)

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GATE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
EVIDENCE_ID_RE = re.compile(r"^[a-z][a-z0-9_.:-]*$")

KIND_BY_ENVELOPE_KIND = {
    "detector_materialization": "detector_materialization_report",
    "external_summary": "external_detector_summary",
    "refusal_delta_summary": "refusal_delta_evidence",
}


class UniqueYamlLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


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

        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_nonfinite,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label} is not valid JSON: {exc}")
        return None

    if not isinstance(payload, dict):
        errors.append(f"{label} must be a JSON object")
        return None

    return payload


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

        payload = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=UniqueYamlLoader,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label} is not valid YAML: {exc}")
        return None

    if not isinstance(payload, dict):
        errors.append(f"{label} must be a YAML mapping")
        return None

    return payload


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
            for chunk in iter(lambda: handle.read(65536), b""):
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
            f"{label} not found as a regular file: {canonical}"
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
        errors.append(f"{label} escapes repository root: {raw!r}")
        return None

    if resolved.is_symlink() or not resolved.is_file():
        errors.append(
            f"{label} not found as a regular repository file: {raw!r}"
        )
        return None

    return resolved


def _relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


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
            str(part) for part in error.absolute_path
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


def _string_list(
    value: Any,
    label: str,
    pattern: re.Pattern[str],
    errors: list[str],
    *,
    non_empty: bool = True,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []

    if non_empty and not value:
        errors.append(f"{label} must be a non-empty array")
        return []

    out: list[str] = []
    seen: set[str] = set()

    for raw in value:
        item = raw.strip() if isinstance(raw, str) else ""

        if not pattern.fullmatch(item):
            errors.append(f"{label} contains invalid value {raw!r}")
        elif item in seen:
            errors.append(f"{label} contains duplicate value {item!r}")
        else:
            seen.add(item)
            out.append(item)

    return out


def _release_required_gates(
    policy: dict[str, Any],
    errors: list[str],
) -> list[str]:
    gates = policy.get("gates")

    if not isinstance(gates, dict):
        errors.append(
            "policy must contain canonical top-level gates mapping"
        )
        return []

    return _string_list(
        gates.get("release_required"),
        "gates.release_required",
        GATE_ID_RE,
        errors,
    )


def _registry_ids(
    registry: dict[str, Any],
    errors: list[str],
) -> set[str]:
    gates = registry.get("gates")

    if not isinstance(gates, dict) or not gates:
        errors.append(
            "registry must contain a non-empty top-level gates mapping"
        )
        return set()

    out: set[str] = set()

    for raw in gates:
        gate = raw.strip() if isinstance(raw, str) else ""

        if not GATE_ID_RE.fullmatch(gate):
            errors.append(f"registry contains invalid gate id {raw!r}")
        else:
            out.add(gate)

    return out


def _created_utc() -> str:
    raw = os.getenv("SOURCE_DATE_EPOCH", "").strip()

    if raw:
        if not raw.isdigit():
            raise ValueError(
                "SOURCE_DATE_EPOCH must be an integer Unix timestamp"
            )

        value = dt.datetime.fromtimestamp(
            int(raw),
            tz=dt.timezone.utc,
        )
    else:
        value = dt.datetime.now(dt.timezone.utc)

    return (
        value.replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _verify_digest_ref(
    repo: Path,
    ref: dict[str, Any],
    label: str,
    errors: list[str],
    *,
    expected_path: str | None = None,
) -> tuple[str, Path] | None:
    path_value = ref.get("path")
    path = _repo_file(repo, path_value, f"{label}.path", errors)

    if path is None:
        return None

    relative = _relative(repo, path)

    if expected_path is not None and relative != expected_path:
        errors.append(
            f"{label}.path must be {expected_path!r}; got {relative!r}"
        )

    expected = ref.get("sha256")

    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        errors.append(f"{label}.sha256 must be a 64-hex digest")
        return None

    actual = _sha256(path, label, errors)

    if actual != expected:
        errors.append(
            f"{label}.sha256 mismatch: expected {expected!r}, "
            f"got {actual!r}"
        )
        return None

    return relative, path


def _validate_identity(
    run_identity: dict[str, Any],
    subject: dict[str, Any],
    errors: list[str],
) -> None:
    git_sha = run_identity.get("git_sha")
    run_key = run_identity.get("run_key")

    if not isinstance(git_sha, str) or not GIT_SHA_RE.fullmatch(git_sha):
        errors.append(
            "index.run_identity.git_sha must be a concrete 40-hex SHA"
        )

    if not isinstance(run_key, str) or not run_key.strip():
        errors.append("index.run_identity.run_key must be non-empty")

    if run_identity.get("run_mode") != "prod":
        errors.append("index.run_identity.run_mode must be 'prod'")

    if subject.get("commit_sha") != git_sha:
        errors.append(
            "index.subject.commit_sha must equal "
            "index.run_identity.git_sha"
        )

    repository = subject.get("repository")

    if not isinstance(repository, str) or not repository.strip():
        errors.append("index.subject.repository must be non-empty")

    current_sha = os.getenv("GITHUB_SHA", "").strip().lower()

    if current_sha and current_sha != git_sha:
        errors.append("index git_sha must match current GITHUB_SHA")

    current_repo = os.getenv("GITHUB_REPOSITORY", "").strip()

    if current_repo and current_repo != repository:
        errors.append(
            "index subject.repository must match GITHUB_REPOSITORY"
        )

    current_run_key = os.getenv("PULSE_RUN_KEY", "").strip()

    if current_run_key and current_run_key != run_key:
        errors.append("index run_key must match current PULSE_RUN_KEY")


def _validate_source_bindings(
    repo: Path,
    index: dict[str, Any],
    errors: list[str],
) -> None:
    source_bindings = _object(
        index,
        "source_bindings",
        "index",
        errors,
    )

    expected = {
        "candidate_status": STATUS_PATH,
        "required_gate_evidence": REQUIRED_EVIDENCE_PATH,
        "external_thresholds": THRESHOLDS_PATH,
    }

    if set(source_bindings) != set(expected):
        errors.append(
            "index.source_bindings keys must exactly equal "
            f"{sorted(expected)!r}"
        )

    for key, expected_path in expected.items():
        ref = source_bindings.get(key)

        if not isinstance(ref, dict):
            errors.append(
                f"index.source_bindings.{key} must be an object"
            )
            continue

        _verify_digest_ref(
            repo,
            ref,
            f"index.source_bindings.{key}",
            errors,
            expected_path=expected_path,
        )


def _validate_envelope_checks(
    repo: Path,
    envelope: dict[str, Any],
    evidence_id: str,
    required_evidence_path: str | None,
    errors: list[str],
) -> None:
    validation = _object(
        envelope,
        "validation",
        f"candidate {evidence_id}",
        errors,
    )

    if validation.get("status") != "passed":
        errors.append(
            f"candidate {evidence_id}.validation.status must be 'passed'"
        )

    checks = validation.get("checks")

    if not isinstance(checks, list) or not checks:
        errors.append(
            f"candidate {evidence_id}.validation.checks must be non-empty"
        )
        return

    all_evidence_paths: set[str] = set()

    for index, check in enumerate(checks):
        label = f"candidate {evidence_id}.validation.checks[{index}]"

        if not isinstance(check, dict):
            errors.append(f"{label} must be an object")
            continue

        if check.get("passed") is not True:
            errors.append(f"{label}.passed must be literal true")

        if check.get("diagnostics") != []:
            errors.append(f"{label}.diagnostics must be empty")

        tool_ref = {
            "path": check.get("tool_path"),
            "sha256": check.get("tool_sha256"),
        }
        _verify_digest_ref(repo, tool_ref, f"{label}.tool", errors)

        evidence_paths = check.get("evidence_paths")

        if not isinstance(evidence_paths, list) or not evidence_paths:
            errors.append(f"{label}.evidence_paths must be non-empty")
            continue

        seen: set[str] = set()

        for raw_path in evidence_paths:
            if not isinstance(raw_path, str) or not raw_path.strip():
                errors.append(
                    f"{label}.evidence_paths entries must be non-empty strings"
                )
                continue

            if raw_path in seen:
                errors.append(
                    f"{label}.evidence_paths contains duplicate {raw_path!r}"
                )
                continue

            seen.add(raw_path)
            all_evidence_paths.add(raw_path)
            _repo_file(
                repo,
                raw_path,
                f"{label}.evidence_paths[{raw_path}]",
                errors,
            )

    if (
        isinstance(required_evidence_path, str)
        and required_evidence_path.strip()
        and required_evidence_path not in all_evidence_paths
    ):
        errors.append(
            f"candidate {evidence_id}.validation.checks must reference "
            "the raw evidence path"
        )


def _validate_envelope(
    *,
    repo: Path,
    evidence_id: str,
    candidate_ref: dict[str, Any],
    envelope_schema: dict[str, Any],
    run_identity: dict[str, Any],
    policy_binding: dict[str, Any],
    registry_binding: dict[str, Any],
    release_required: list[str],
    errors: list[str],
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    expected_path = (
        f"{CANDIDATE_DIR}/{evidence_id}.json"
    )

    resolved = _verify_digest_ref(
        repo,
        candidate_ref,
        f"index.candidates.{evidence_id}",
        errors,
        expected_path=expected_path,
    )

    if resolved is None:
        return None, None, []

    _, path = resolved
    envelope = _load_json(
        path,
        f"candidate envelope {evidence_id}",
        errors,
    )

    if envelope is None:
        return None, None, []

    errors.extend(
        f"candidate {evidence_id} schema validation failed: {item}"
        for item in _schema_errors(envelope, envelope_schema)
    )

    if envelope.get("schema_version") != ENVELOPE_SCHEMA_VERSION:
        errors.append(
            f"candidate {evidence_id}.schema_version must be "
            f"{ENVELOPE_SCHEMA_VERSION!r}"
        )

    if envelope.get("evidence_id") != evidence_id:
        errors.append(
            f"candidate {evidence_id}.evidence_id mismatch"
        )

    evidence_kind = envelope.get("evidence_kind")
    manifest_kind = KIND_BY_ENVELOPE_KIND.get(str(evidence_kind))

    if manifest_kind is None:
        errors.append(
            f"candidate {evidence_id}.evidence_kind is unsupported: "
            f"{evidence_kind!r}"
        )

    if envelope.get("run_identity") != run_identity:
        errors.append(
            f"candidate {evidence_id}.run_identity mismatch"
        )

    subject_binding = _object(
        envelope,
        "subject_binding",
        f"candidate {evidence_id}",
        errors,
    )
    expected_subject_binding = {
        "git_sha": run_identity.get("git_sha"),
        "run_key": run_identity.get("run_key"),
    }

    if subject_binding != expected_subject_binding:
        errors.append(
            f"candidate {evidence_id}.subject_binding mismatch"
        )

    if candidate_ref.get("subject_binding") != subject_binding:
        errors.append(
            f"index.candidates.{evidence_id}.subject_binding mismatch"
        )

    if envelope.get("policy_binding") != policy_binding:
        errors.append(
            f"candidate {evidence_id}.policy_binding mismatch"
        )

    if envelope.get("registry_binding") != registry_binding:
        errors.append(
            f"candidate {evidence_id}.registry_binding mismatch"
        )

    provenance = _object(
        envelope,
        "provenance",
        f"candidate {evidence_id}",
        errors,
    )

    if provenance.get("trusted_producer") is not True:
        errors.append(
            f"candidate {evidence_id}.provenance.trusted_producer "
            "must be literal true"
        )

    _verify_digest_ref(
        repo,
        {
            "path": provenance.get("tool_path"),
            "sha256": provenance.get("tool_sha256"),
        },
        f"candidate {evidence_id}.provenance.tool",
        errors,
    )

    raw_binding = _object(
        envelope,
        "raw_evidence_binding",
        f"candidate {evidence_id}",
        errors,
    )
    _verify_digest_ref(
        repo,
        raw_binding,
        f"candidate {evidence_id}.raw_evidence_binding",
        errors,
    )

    required_for_gates = _string_list(
        envelope.get("required_for_gates"),
        f"candidate {evidence_id}.required_for_gates",
        GATE_ID_RE,
        errors,
    )

    if candidate_ref.get("required_for_gates") != required_for_gates:
        errors.append(
            f"index.candidates.{evidence_id}.required_for_gates mismatch"
        )

    if not required_for_gates:
        return None, None, []

    unknown_gates = sorted(
        set(required_for_gates) - set(release_required)
    )

    if unknown_gates:
        errors.append(
            f"candidate {evidence_id} targets gates outside "
            f"gates.release_required: {unknown_gates!r}"
        )

    gate_values = _object(
        envelope,
        "candidate_gate_values",
        f"candidate {evidence_id}",
        errors,
    )

    if set(gate_values) != set(required_for_gates):
        errors.append(
            f"candidate {evidence_id}.candidate_gate_values keys "
            "must exactly equal required_for_gates"
        )

    for gate in required_for_gates:
        if gate_values.get(gate) is not True:
            errors.append(
                f"candidate {evidence_id}.candidate_gate_values.{gate} "
                "must be literal true"
            )

    _validate_envelope_checks(
        repo,
        envelope,
        evidence_id,
        raw_binding.get("path") if isinstance(raw_binding, dict) else None,
        errors,
    )

    boundary = _object(
        envelope,
        "authority_boundary",
        f"candidate {evidence_id}",
        errors,
    )
    expected_boundary = {
        "normative": False,
        "candidate_only": True,
        "direct_recorded_evidence_candidate": True,
        "creates_release_authority": False,
        "materializes_status": False,
        "materializes_release_required": False,
        "eligible_without_verifier": False,
        "replaces_check_gates": False,
    }

    if boundary != expected_boundary:
        errors.append(
            f"candidate {evidence_id}.authority_boundary mismatch"
        )

    if candidate_ref.get("schema_version") != ENVELOPE_SCHEMA_VERSION:
        errors.append(
            f"index.candidates.{evidence_id}.schema_version mismatch"
        )

    return envelope, manifest_kind, required_for_gates


def build_manifest(
    *,
    repo: Path,
    index_path: Path,
    envelope_schema_path: Path,
    manifest_schema_path: Path,
    policy_path: Path,
    registry_path: Path,
    tool_path: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    repo = repo.resolve()

    if not repo.is_dir():
        return None, [f"repo root must be a directory: {repo}"]

    specs = (
        (index_path, INDEX_PATH, "candidate index"),
        (
            envelope_schema_path,
            ENVELOPE_SCHEMA_PATH,
            "candidate envelope schema",
        ),
        (
            manifest_schema_path,
            MANIFEST_SCHEMA_PATH,
            "input manifest schema",
        ),
        (policy_path, POLICY_PATH, "policy"),
        (registry_path, REGISTRY_PATH, "registry"),
        (tool_path, TOOL_PATH, "manifest builder"),
    )

    files = [
        _canonical_file(
            repo,
            supplied,
            expected,
            label,
            errors,
        )
        for supplied, expected, label in specs
    ]

    if errors or any(path is None for path in files):
        return None, errors

    (
        index_path,
        envelope_schema_path,
        manifest_schema_path,
        policy_path,
        registry_path,
        tool_path,
    ) = files  # type: ignore[misc]

    index = _load_json(index_path, "candidate index", errors)
    envelope_schema = _load_json(
        envelope_schema_path,
        "candidate envelope schema",
        errors,
    )
    manifest_schema = _load_json(
        manifest_schema_path,
        "input manifest schema",
        errors,
    )
    policy = _load_yaml(policy_path, "policy", errors)
    registry = _load_yaml(registry_path, "registry", errors)

    if any(
        item is None
        for item in (
            index,
            envelope_schema,
            manifest_schema,
            policy,
            registry,
        )
    ):
        return None, errors

    assert index is not None
    assert envelope_schema is not None
    assert manifest_schema is not None
    assert policy is not None
    assert registry is not None

    if index.get("schema_version") != INDEX_SCHEMA_VERSION:
        errors.append(
            f"index.schema_version must be {INDEX_SCHEMA_VERSION!r}"
        )

    run_identity = _object(index, "run_identity", "index", errors)
    subject = _object(index, "subject", "index", errors)
    policy_binding = _object(
        index,
        "policy_binding",
        "index",
        errors,
    )
    registry_binding = _object(
        index,
        "registry_binding",
        "index",
        errors,
    )

    _validate_identity(run_identity, subject, errors)

    policy_sha = _sha256(policy_path, "policy", errors)
    registry_sha = _sha256(registry_path, "registry", errors)

    expected_policy_binding = {
        "policy_path": POLICY_PATH,
        "policy_sha256": policy_sha,
        "policy_set": "required+release_required",
    }
    expected_registry_binding = {
        "registry_path": REGISTRY_PATH,
        "registry_sha256": registry_sha,
    }

    if policy_binding != expected_policy_binding:
        errors.append("index.policy_binding mismatch")

    if registry_binding != expected_registry_binding:
        errors.append("index.registry_binding mismatch")

    release_required = _release_required_gates(policy, errors)
    registry_gate_ids = _registry_ids(registry, errors)

    missing_registry = sorted(
        set(release_required) - registry_gate_ids
    )

    if missing_registry:
        errors.append(
            "gates.release_required contains registry-missing gates: "
            f"{missing_registry!r}"
        )

    index_release_required = _string_list(
        index.get("release_required_gates"),
        "index.release_required_gates",
        GATE_ID_RE,
        errors,
    )

    if index_release_required != release_required:
        errors.append(
            "index.release_required_gates must exactly match "
            "canonical gates.release_required order"
        )

    _validate_source_bindings(repo, index, errors)

    candidates = _object(index, "candidates", "index", errors)
    candidate_ids = _string_list(
        index.get("candidate_ids"),
        "index.candidate_ids",
        EVIDENCE_ID_RE,
        errors,
    )
    external_candidate_ids = _string_list(
        index.get("external_candidate_ids"),
        "index.external_candidate_ids",
        EVIDENCE_ID_RE,
        errors,
    )

    if candidate_ids != sorted(candidates):
        errors.append(
            "index.candidate_ids must equal sorted index.candidates keys"
        )

    boundary = _object(
        index,
        "authority_boundary",
        "index",
        errors,
    )
    expected_index_boundary = {
        "normative": False,
        "creates_release_authority": False,
        "materializes_release_required": False,
        "eligible_without_verifier": False,
        "replaces_check_gates": False,
    }

    if boundary != expected_index_boundary:
        errors.append("index.authority_boundary mismatch")

    if errors:
        return None, errors

    candidate_evidence: dict[str, Any] = {}
    expected_relation_bindings: dict[str, Any] = {}
    gate_candidates: dict[str, list[str]] = {
        gate: [] for gate in release_required
    }
    relation_ids_by_gate: dict[str, list[str]] = {
        gate: [] for gate in release_required
    }
    discovered_external_ids: list[str] = []

    for evidence_id in candidate_ids:
        ref = candidates.get(evidence_id)

        if not isinstance(ref, dict):
            errors.append(
                f"index.candidates.{evidence_id} must be an object"
            )
            continue

        envelope, manifest_kind, required_for_gates = _validate_envelope(
            repo=repo,
            evidence_id=evidence_id,
            candidate_ref=ref,
            envelope_schema=envelope_schema,
            run_identity=run_identity,
            policy_binding=expected_policy_binding,
            registry_binding=expected_registry_binding,
            release_required=release_required,
            errors=errors,
        )

        if envelope is None or manifest_kind is None:
            continue

        if envelope.get("evidence_kind") == "external_summary":
            discovered_external_ids.append(evidence_id)

        candidate_evidence[evidence_id] = {
            "kind": manifest_kind,
            "path": ref.get("path"),
            "expected_sha256": ref.get("sha256"),
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "subject_binding": dict(envelope["subject_binding"]),
            "provenance_expectations": {
                "trusted_producer_required": True,
            },
            "required_for_gates": list(required_for_gates),
            "verification_required": True,
        }

        for gate in required_for_gates:
            gate_candidates[gate].append(evidence_id)

            subject_relation_id = (
                f"{evidence_id}_to_subject_for_{gate}"
            )
            gate_relation_id = f"{evidence_id}_to_gate_{gate}"

            expected_relation_bindings[subject_relation_id] = {
                "binding_type": "artifact_to_subject",
                "source_evidence_id": evidence_id,
                "target": "subject.commit_sha",
                "required": True,
                "expected_gate_id": gate,
                "failure_if_missing": (
                    "candidate evidence is not bound to the "
                    "current subject commit"
                ),
            }
            expected_relation_bindings[gate_relation_id] = {
                "binding_type": "artifact_to_gate",
                "source_evidence_id": evidence_id,
                "target": f"gate.{gate}",
                "required": True,
                "expected_gate_id": gate,
                "failure_if_missing": (
                    "candidate evidence is not bound to the "
                    f"expected gate {gate}"
                ),
            }

            relation_ids_by_gate[gate].extend(
                [subject_relation_id, gate_relation_id]
            )

    if sorted(discovered_external_ids) != sorted(external_candidate_ids):
        errors.append(
            "index.external_candidate_ids must exactly equal "
            "the external-summary candidate set"
        )

    expected_gate_materialization: dict[str, Any] = {}

    for gate in release_required:
        ids = sorted(gate_candidates[gate])
        relation_ids = relation_ids_by_gate[gate]

        if not ids:
            errors.append(
                f"no verifier-facing candidate covers release-required "
                f"gate {gate!r}"
            )
            continue

        expected_gate_materialization[gate] = {
            "expected_value": True,
            "candidate_evidence_ids": ids,
            "relation_binding_ids": relation_ids,
            "policy_relation": "release_required",
            "materialization_allowed_without_verifier": False,
        }

    if set(candidate_evidence) != set(candidate_ids):
        errors.append(
            "not every indexed candidate produced a manifest entry"
        )

    if errors:
        return None, errors

    try:
        timestamp = _created_utc()
    except ValueError as exc:
        return None, [str(exc)]

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_utc": timestamp,
        "manifest_id": MANIFEST_ID,
        "manifest_version": MANIFEST_VERSION,
        "run_identity": dict(run_identity),
        "subject": dict(subject),
        "policy_binding": expected_policy_binding,
        "registry_binding": expected_registry_binding,
        "candidate_evidence": candidate_evidence,
        "expected_relation_bindings": expected_relation_bindings,
        "expected_gate_materialization": expected_gate_materialization,
        "fail_closed_requirements": [
            "missing candidate evidence fails closed",
            "missing expected relation binding fails closed",
            "missing expected gate materialization binding fails closed",
            "candidate evidence cannot materialize a gate without verifier output",
            "all release-required gates must have verified gate-targeted relations",
        ],
        "warnings": [],
    }

    errors.extend(
        "input manifest schema validation failed: " + item
        for item in _schema_errors(manifest, manifest_schema)
    )

    if errors:
        return None, errors

    return manifest, []


def _canonical_output(
    repo: Path,
    supplied: Path,
    errors: list[str],
) -> Path | None:
    actual = (
        supplied.resolve()
        if supplied.is_absolute()
        else (repo / supplied).resolve()
    )
    canonical = (repo / OUT_PATH).resolve()

    if actual != canonical:
        errors.append(
            f"output must use canonical path {OUT_PATH!r}"
        )
        return None

    return canonical


def _validate_with_existing_checker(
    *,
    repo: Path,
    checker_path: Path,
    schema_path: Path,
    manifest_path: Path,
) -> tuple[bool, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(checker_path),
            "--manifest",
            str(manifest_path),
            "--schema",
            str(schema_path),
        ],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = "\n".join(
        text.strip()
        for text in (result.stdout, result.stderr)
        if text.strip()
    )

    return result.returncode == 0, combined


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(root))
    parser.add_argument("--index", default=INDEX_PATH)
    parser.add_argument(
        "--envelope-schema",
        default=ENVELOPE_SCHEMA_PATH,
    )
    parser.add_argument(
        "--manifest-schema",
        default=MANIFEST_SCHEMA_PATH,
    )
    parser.add_argument("--policy", default=POLICY_PATH)
    parser.add_argument("--registry", default=REGISTRY_PATH)
    parser.add_argument("--checker", default=MANIFEST_CHECKER_PATH)
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args(argv)

    repo = Path(args.repo_root).resolve()

    if not repo.is_dir():
        print(
            "ERRORS (fail-closed):\n"
            f" - repo root must be a directory: {repo}",
            file=sys.stderr,
        )
        return 1

    path_errors: list[str] = []
    output = _canonical_output(repo, Path(args.out), path_errors)
    checker = _canonical_file(
        repo,
        Path(args.checker),
        MANIFEST_CHECKER_PATH,
        "manifest checker",
        path_errors,
    )

    if output is None or checker is None:
        print("ERRORS (fail-closed):", file=sys.stderr)

        for error in path_errors:
            print(f" - {error}", file=sys.stderr)

        return 1

    if output.exists() or output.is_symlink():
        if output.is_dir() and not output.is_symlink():
            print(
                "ERRORS (fail-closed):\n"
                f" - output path is a directory: {output}",
                file=sys.stderr,
            )
            return 1

        output.unlink()

    manifest, errors = build_manifest(
        repo=repo,
        index_path=Path(args.index),
        envelope_schema_path=Path(args.envelope_schema),
        manifest_schema_path=Path(args.manifest_schema),
        policy_path=Path(args.policy),
        registry_path=Path(args.registry),
        tool_path=Path(TOOL_PATH),
    )

    if manifest is None:
        print("ERRORS (fail-closed):", file=sys.stderr)

        for error in errors:
            print(f" - {error}", file=sys.stderr)

        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")

    if temporary.exists() or temporary.is_symlink():
        if temporary.is_dir() and not temporary.is_symlink():
            print(
                "ERRORS (fail-closed):\n"
                f" - temporary output path is a directory: {temporary}",
                file=sys.stderr,
            )
            return 1

        temporary.unlink()

    temporary.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    schema_path = (repo / MANIFEST_SCHEMA_PATH).resolve()

    ok, checker_output = _validate_with_existing_checker(
        repo=repo,
        checker_path=checker,
        schema_path=schema_path,
        manifest_path=temporary,
    )

    if not ok:
        temporary.unlink(missing_ok=True)

        print("ERRORS (fail-closed):", file=sys.stderr)
        print(
            " - existing manifest checker rejected generated manifest",
            file=sys.stderr,
        )

        if checker_output:
            print(checker_output, file=sys.stderr)

        return 1

    os.replace(temporary, output)

    print(f"Wrote {output}")

    if checker_output:
        print(checker_output)

    print(
        "OK: built schema-valid, relation-complete release evidence "
        "input manifest without verifying or materializing gates"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
