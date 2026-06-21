#!/usr/bin/env python3
"""Build verifier-facing recorded-release candidate envelopes.

The builder consumes current-run artifacts that exist before release-required
materialization:

- a non-stubbed prod candidate ``status.json`` built from exact
  ``gates.required`` evidence,
- ``required_gate_evidence_v0.json``,
- ``refusal_delta_summary.json``, and
- canonical external detector ``*_summary.json`` / ``*_summary.jsonl`` files.

It validates identity, policy/registry digests, schema contracts,
required-gate coverage, refusal-delta evidence presence, and external detector
threshold results before writing candidate envelopes for
``check_recorded_release_evidence_v0.py``.

This tool does not materialize ``release_required`` gates, replace
``check_gates.py``, or create release authority.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


INDEX_SCHEMA = "recorded_release_candidate_index_v0"
ENVELOPE_SCHEMA = "recorded_release_candidate_envelope_v0"
REQUIRED_EVIDENCE_SCHEMA = "required_gate_evidence_v0"
STATUS_VERSION = "1.0.0"
BUILDER_ID = "pulse_recorded_release_candidate_builder_v0"
BUILDER_VERSION = "0.1.0"

TOOL = "PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py"
STATUS = "PULSE_safe_pack_v0/artifacts/status.json"
REQUIRED_EVIDENCE = (
    "PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json"
)
REQUIRED_EVIDENCE_SCHEMA_PATH = (
    "schemas/required_gate_evidence_v0.schema.json"
)
STATUS_SCHEMA = "schemas/status/status_v1.schema.json"
ENVELOPE_SCHEMA_PATH = (
    "schemas/recorded_release_candidate_envelope_v0.schema.json"
)
POLICY = "pulse_gate_policy_v0.yml"
REGISTRY = "pulse_gate_registry_v0.yml"
THRESHOLDS = "PULSE_safe_pack_v0/profiles/external_thresholds.yaml"
REFUSAL = "PULSE_safe_pack_v0/artifacts/refusal_delta_summary.json"
EXTERNAL_DIR = "PULSE_safe_pack_v0/artifacts/external"
OUT_DIR = (
    "PULSE_safe_pack_v0/artifacts/recorded_release_candidates"
)
INDEX = (
    "PULSE_safe_pack_v0/artifacts/"
    "recorded_release_candidate_index_v0.json"
)

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GATE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

SUPPORTED_RELEASE_REQUIRED = {
    "detectors_materialized_ok",
    "external_summaries_present",
    "external_all_pass",
    "refusal_delta_evidence_present",
}

EXTERNAL_DETECTORS: dict[str, dict[str, Any]] = {
    "llamaguard": {
        "files": (
            "llamaguard_summary.json",
            "llamaguard_summary.jsonl",
        ),
        "threshold": "llamaguard_violation_rate_max",
        "metric": "llamaguard_violation_rate",
        "preferred": None,
    },
    "promptguard": {
        "files": (
            "promptguard_summary.json",
            "promptguard_summary.jsonl",
        ),
        "threshold": "promptguard_attack_detect_rate_max",
        "metric": "promptguard_attack_detect_rate",
        "preferred": "attack_detect_rate",
    },
    "garak": {
        "files": (
            "garak_summary.json",
            "garak_summary.jsonl",
        ),
        "threshold": "garak_new_critical_max",
        "metric": "garak_new_critical",
        "preferred": "new_critical",
    },
    "azure_eval": {
        "files": (
            "azure_eval_summary.json",
            "azure_eval_summary.jsonl",
        ),
        "threshold": "azure_indirect_jailbreak_rate_max",
        "metric": "azure_indirect_jailbreak_rate",
        "preferred": "azure_indirect_jailbreak_rate",
    },
    "promptfoo": {
        "files": (
            "promptfoo_summary.json",
            "promptfoo_summary.jsonl",
        ),
        "threshold": "promptfoo_fail_rate_max",
        "metric": "promptfoo_fail_rate",
        "preferred": "fail_rate",
    },
    "deepeval": {
        "files": (
            "deepeval_summary.json",
            "deepeval_summary.jsonl",
        ),
        "threshold": "deepeval_fail_rate_max",
        "metric": "deepeval_fail_rate",
        "preferred": "fail_rate",
    },
}

GENERIC_METRIC_KEYS = (
    "value",
    "rate",
    "violation_rate",
    "attack_detect_rate",
    "fail_rate",
    "new_critical",
)


class UniqueYamlLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _yaml_mapping(
    loader: UniqueYamlLoader,
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


UniqueYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _yaml_mapping,
)


def _json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for key, value in pairs:
        if key in out:
            raise ValueError(
                f"duplicate JSON key {key!r}"
            )

        out[key] = value

    return out


def _nonfinite(value: str) -> None:
    raise ValueError(
        f"non-finite JSON constant {value!r}"
    )


def load_json(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: "
                f"{path}"
            )
            return None

        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_object,
            parse_constant=_nonfinite,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"{label} is not valid JSON: {exc}"
        )
        return None

    if not isinstance(value, dict):
        errors.append(
            f"{label} must be a JSON object"
        )
        return None

    return value


def load_json_or_jsonl(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    if path.suffix.lower() != ".jsonl":
        return load_json(
            path,
            label,
            errors,
        )

    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: "
                f"{path}"
            )
            return None

        values: list[dict[str, Any]] = []

        with path.open(
            "r",
            encoding="utf-8",
            errors="strict",
        ) as handle:
            for line_no, raw in enumerate(
                handle,
                start=1,
            ):
                text = raw.strip()

                if not text:
                    continue

                try:
                    value = json.loads(
                        text,
                        object_pairs_hook=_json_object,
                        parse_constant=_nonfinite,
                    )

                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        f"{label} line {line_no} "
                        f"is invalid: {exc}"
                    )
                    continue

                if not isinstance(value, dict):
                    errors.append(
                        f"{label} line {line_no} "
                        "must be an object"
                    )
                    continue

                values.append(value)

    except OSError as exc:
        errors.append(
            f"{label} could not be read: {exc}"
        )
        return None

    if not values:
        errors.append(
            f"{label} must contain at least "
            "one JSON object"
        )
        return None

    return values[-1]


def load_yaml(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: "
                f"{path}"
            )
            return None

        value = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=UniqueYamlLoader,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"{label} is not valid YAML: {exc}"
        )
        return None

    if not isinstance(value, dict):
        errors.append(
            f"{label} must be a YAML mapping"
        )
        return None

    return value


def sha256(
    path: Path,
    label: str,
    errors: list[str],
) -> str | None:
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: "
                f"{path}"
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


def canonical_file(
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
            f"{label} must use canonical path "
            f"{expected!r}"
        )
        return None

    if canonical.is_symlink() or not canonical.is_file():
        errors.append(
            f"{label} not found as a regular file: "
            f"{canonical}"
        )
        return None

    return canonical


def canonical_dir(
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
            f"{label} must use canonical path "
            f"{expected!r}"
        )
        return None

    if canonical.is_symlink() or not canonical.is_dir():
        errors.append(
            f"{label} not found as a regular directory: "
            f"{canonical}"
        )
        return None

    return canonical


def relative(
    repo: Path,
    path: Path,
) -> str:
    return (
        path.resolve()
        .relative_to(repo.resolve())
        .as_posix()
    )


def schema_errors(
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
        key=lambda item: list(
            item.absolute_path
        ),
    ):
        location = ".".join(
            str(part)
            for part in error.absolute_path
        )

        out.append(
            (
                f"{location}: "
                if location
                else ""
            )
            + error.message
        )

    return out


def object_section(
    parent: dict[str, Any],
    key: str,
    label: str,
    errors: list[str],
) -> dict[str, Any]:
    value = parent.get(key)

    if not isinstance(value, dict):
        errors.append(
            f"{label}.{key} must be an object"
        )
        return {}

    return value


def gate_list(
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


def policy_gate_sets(
    policy: dict[str, Any],
    errors: list[str],
) -> tuple[list[str], list[str]]:
    gates = policy.get("gates")

    if not isinstance(gates, dict):
        errors.append(
            "policy must contain canonical "
            "top-level gates mapping"
        )
        return [], []

    required = gate_list(
        gates.get("required"),
        "gates.required",
        errors,
    )

    release_required = gate_list(
        gates.get("release_required"),
        "gates.release_required",
        errors,
    )

    overlap = sorted(
        set(required) & set(release_required)
    )

    if overlap:
        errors.append(
            "gates.required and "
            "gates.release_required overlap: "
            f"{overlap!r}"
        )

    return required, release_required


def registry_ids(
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
        gate = (
            raw.strip()
            if isinstance(raw, str)
            else ""
        )

        if not GATE_ID_RE.fullmatch(gate):
            errors.append(
                f"registry contains invalid gate id "
                f"{raw!r}"
            )
        else:
            out.add(gate)

    return out


def created_utc() -> str:
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


def number(
    value: Any,
    label: str,
    errors: list[str],
) -> float | None:
    if isinstance(value, bool):
        errors.append(
            f"{label} must be numeric, not boolean"
        )
        return None

    if isinstance(value, (int, float)):
        result = float(value)

    elif isinstance(value, str):
        try:
            result = float(value.strip())

        except ValueError:
            errors.append(
                f"{label} must be numeric"
            )
            return None

    else:
        errors.append(
            f"{label} must be numeric"
        )
        return None

    if not math.isfinite(result):
        errors.append(
            f"{label} must be finite"
        )
        return None

    return result


def external_metric(
    payload: dict[str, Any],
    preferred: str | None,
    metric_name: str,
    label: str,
    errors: list[str],
) -> tuple[float | None, str | None]:
    if preferred and preferred in payload:
        return (
            number(
                payload[preferred],
                f"{label}.{preferred}",
                errors,
            ),
            preferred,
        )

    for key in GENERIC_METRIC_KEYS:
        if key in payload:
            return (
                number(
                    payload[key],
                    f"{label}.{key}",
                    errors,
                ),
                key,
            )

    rates = payload.get("failure_rates")

    if isinstance(rates, dict):
        for key in (
            preferred,
            metric_name,
        ):
            if key and key in rates:
                return (
                    number(
                        rates[key],
                        f"{label}.failure_rates.{key}",
                        errors,
                    ),
                    f"failure_rates.{key}",
                )

        numeric: list[tuple[str, float]] = []

        for key, raw in rates.items():
            local: list[str] = []

            value = number(
                raw,
                f"{label}.failure_rates.{key}",
                local,
            )

            if value is not None:
                numeric.append(
                    (
                        str(key),
                        value,
                    )
                )

        if numeric:
            key, value = max(
                numeric,
                key=lambda item: item[1],
            )

            return (
                value,
                f"failure_rates.{key}",
            )

    errors.append(
        f"{label} has no recognized "
        "external metric key"
    )

    return None, None


def validation_check(
    check_id: str,
    kind: str,
    details: str,
    tool_sha: str,
    evidence_paths: list[str],
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "kind": kind,
        "passed": True,
        "details": details,
        "tool_path": TOOL,
        "tool_sha256": tool_sha,
        "evidence_paths": sorted(
            set(evidence_paths)
        ),
        "diagnostics": [],
    }


def envelope(
    *,
    evidence_id: str,
    evidence_kind: str,
    run_identity: dict[str, Any],
    policy_sha: str,
    registry_sha: str,
    tool_sha: str,
    raw_path: str,
    raw_sha: str,
    raw_kind: str,
    raw_schema: str | None,
    gates: list[str],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": ENVELOPE_SCHEMA,
        "created_utc": created_utc(),
        "evidence_id": evidence_id,
        "evidence_kind": evidence_kind,
        "run_identity": dict(
            run_identity
        ),
        "subject_binding": {
            "git_sha": run_identity["git_sha"],
            "run_key": run_identity["run_key"],
        },
        "policy_binding": {
            "policy_path": POLICY,
            "policy_sha256": policy_sha,
            "policy_set": (
                "required+release_required"
            ),
        },
        "registry_binding": {
            "registry_path": REGISTRY,
            "registry_sha256": registry_sha,
        },
        "provenance": {
            "trusted_producer": True,
            "producer_id": BUILDER_ID,
            "producer_version": BUILDER_VERSION,
            "tool_path": TOOL,
            "tool_sha256": tool_sha,
        },
        "raw_evidence_binding": {
            "path": raw_path,
            "sha256": raw_sha,
            "kind": raw_kind,
            "schema_version": raw_schema,
        },
        "required_for_gates": list(gates),
        "candidate_gate_values": {
            gate: True
            for gate in gates
        },
        "validation": {
            "status": "passed",
            "checks": checks,
        },
        "authority_boundary": {
            "normative": False,
            "candidate_only": True,
            "direct_recorded_evidence_candidate": (
                True
            ),
            "creates_release_authority": False,
            "materializes_status": False,
            "materializes_release_required": False,
            "eligible_without_verifier": False,
            "replaces_check_gates": False,
        },
        "warnings": [],
    }


@dataclass(frozen=True)
class Context:
    repo: Path
    status_path: Path
    evidence_path: Path
    refusal_path: Path
    external_dir: Path
    policy_sha: str
    registry_sha: str
    thresholds_sha: str
    tool_sha: str
    required: list[str]
    release_required: list[str]
    run_identity: dict[str, Any]
    subject: dict[str, Any]
    status_sha: str
    evidence_sha: str


def validate_base(
    *,
    repo: Path,
    status: dict[str, Any],
    evidence: dict[str, Any],
    evidence_schema: dict[str, Any],
    status_schema: dict[str, Any],
    policy: dict[str, Any],
    registry: dict[str, Any],
    status_path: Path,
    evidence_path: Path,
    refusal_path: Path,
    external_dir: Path,
    policy_path: Path,
    registry_path: Path,
    thresholds_path: Path,
    tool_path: Path,
    errors: list[str],
) -> Context | None:
    errors.extend(
        "candidate status schema validation "
        f"failed: {item}"
        for item in schema_errors(
            status,
            status_schema,
        )
    )

    errors.extend(
        "required-gate evidence schema "
        f"validation failed: {item}"
        for item in schema_errors(
            evidence,
            evidence_schema,
        )
    )

    required, release_required = (
        policy_gate_sets(
            policy,
            errors,
        )
    )

    unknown = sorted(
        (
            set(required)
            | set(release_required)
        )
        - registry_ids(
            registry,
            errors,
        )
    )

    if unknown:
        errors.append(
            f"policy gates missing from registry: "
            f"{unknown!r}"
        )

    if (
        set(release_required)
        != SUPPORTED_RELEASE_REQUIRED
    ):
        errors.append(
            "gates.release_required must exactly "
            "equal the v0 supported set: "
            f"{sorted(SUPPORTED_RELEASE_REQUIRED)!r}; "
            f"got {sorted(release_required)!r}"
        )

    policy_sha = sha256(
        policy_path,
        "policy",
        errors,
    )

    registry_sha = sha256(
        registry_path,
        "registry",
        errors,
    )

    thresholds_sha = sha256(
        thresholds_path,
        "external thresholds",
        errors,
    )

    tool_sha = sha256(
        tool_path,
        "candidate builder",
        errors,
    )

    status_sha = sha256(
        status_path,
        "candidate status",
        errors,
    )

    evidence_sha = sha256(
        evidence_path,
        "required-gate evidence",
        errors,
    )

    run_identity = object_section(
        evidence,
        "run_identity",
        "evidence",
        errors,
    )

    subject = object_section(
        evidence,
        "subject",
        "evidence",
        errors,
    )

    policy_binding = object_section(
        evidence,
        "policy_binding",
        "evidence",
        errors,
    )

    registry_binding = object_section(
        evidence,
        "registry_binding",
        "evidence",
        errors,
    )

    producer = object_section(
        evidence,
        "producer",
        "evidence",
        errors,
    )

    evidence_gates = object_section(
        evidence,
        "gates",
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
            "evidence.run_identity.git_sha must "
            "be a concrete 40-hex SHA"
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
            "evidence.subject.commit_sha must "
            "equal run_identity.git_sha"
        )

    current_sha = os.getenv(
        "GITHUB_SHA",
        "",
    ).strip().lower()

    if current_sha and current_sha != git_sha:
        errors.append(
            "evidence git_sha must match "
            "current GITHUB_SHA"
        )

    current_repo = os.getenv(
        "GITHUB_REPOSITORY",
        "",
    ).strip()

    if (
        current_repo
        and subject.get("repository") != current_repo
    ):
        errors.append(
            "evidence subject.repository must "
            "match GITHUB_REPOSITORY"
        )

    current_run_key = os.getenv(
        "PULSE_RUN_KEY",
        "",
    ).strip()

    if current_run_key and current_run_key != run_key:
        errors.append(
            "evidence run_key must match "
            "current PULSE_RUN_KEY"
        )

    metrics = object_section(
        status,
        "metrics",
        "status",
        errors,
    )

    status_gates = object_section(
        status,
        "gates",
        "status",
        errors,
    )

    diagnostics = object_section(
        status,
        "diagnostics",
        "status",
        errors,
    )

    if status.get("version") != STATUS_VERSION:
        errors.append(
            f"candidate status version must be "
            f"{STATUS_VERSION!r}"
        )

    if metrics.get("run_mode") != "prod":
        errors.append(
            "candidate status metrics.run_mode "
            "must be 'prod'"
        )

    if (
        metrics.get("git_sha") != git_sha
        or metrics.get("run_key") != run_key
    ):
        errors.append(
            "candidate status identity must "
            "match required-gate evidence"
        )

    if metrics.get("gate_policy_path") != POLICY:
        errors.append(
            "candidate status gate_policy_path "
            "must be canonical"
        )

    if (
        metrics.get("gate_policy_sha256")
        != policy_sha
    ):
        errors.append(
            "candidate status "
            "gate_policy_sha256 mismatch"
        )

    if (
        metrics.get("gate_registry_path")
        != REGISTRY
    ):
        errors.append(
            "candidate status gate_registry_path "
            "must be canonical"
        )

    if (
        metrics.get("gate_registry_sha256")
        != registry_sha
    ):
        errors.append(
            "candidate status "
            "gate_registry_sha256 mismatch"
        )

    if (
        metrics.get("required_gate_evidence_path")
        != REQUIRED_EVIDENCE
    ):
        errors.append(
            "candidate status "
            "required_gate_evidence_path mismatch"
        )

    if (
        metrics.get(
            "required_gate_evidence_sha256"
        )
        != evidence_sha
    ):
        errors.append(
            "candidate status "
            "required_gate_evidence_sha256 mismatch"
        )

    if (
        diagnostics.get("gates_stubbed")
        is not False
    ):
        errors.append(
            "candidate status "
            "diagnostics.gates_stubbed must be false"
        )

    if diagnostics.get("scaffold") is not False:
        errors.append(
            "candidate status "
            "diagnostics.scaffold must be false"
        )

    if (
        diagnostics.get("candidate_status")
        is not True
    ):
        errors.append(
            "candidate status "
            "diagnostics.candidate_status must be true"
        )

    if set(status_gates) != set(required):
        errors.append(
            "candidate status gate keys must "
            "exactly equal gates.required"
        )

    for gate in required:
        if status_gates.get(gate) is not True:
            errors.append(
                f"candidate status gates.{gate} "
                "must be literal true"
            )

    if (
        evidence.get("schema_version")
        != REQUIRED_EVIDENCE_SCHEMA
    ):
        errors.append(
            "evidence.schema_version must be "
            f"{REQUIRED_EVIDENCE_SCHEMA!r}"
        )

    if set(evidence_gates) != set(required):
        errors.append(
            "required-gate evidence keys must "
            "exactly equal gates.required"
        )

    for gate in required:
        item = evidence_gates.get(gate)

        if not isinstance(item, dict):
            errors.append(
                f"evidence.gates.{gate} "
                "must be an object"
            )

        elif (
            item.get("value") is not True
            or item.get("status") != "passed"
            or item.get("diagnostics") != []
        ):
            errors.append(
                f"evidence.gates.{gate} must be "
                "a clean passing result"
            )

    if (
        policy_binding.get("policy_path") != POLICY
        or policy_binding.get("policy_set")
        != "required"
        or policy_binding.get("policy_sha256")
        != policy_sha
    ):
        errors.append(
            "required-gate evidence "
            "policy binding mismatch"
        )

    if (
        registry_binding.get("registry_path")
        != REGISTRY
        or registry_binding.get(
            "registry_sha256"
        )
        != registry_sha
    ):
        errors.append(
            "required-gate evidence "
            "registry binding mismatch"
        )

    if producer.get("trusted") is not True:
        errors.append(
            "required-gate evidence "
            "producer.trusted must be true"
        )

    producer_path_raw = producer.get("tool_path")

    if (
        isinstance(producer_path_raw, str)
        and producer_path_raw.strip()
    ):
        producer_path = (
            repo / producer_path_raw
        ).resolve()

        try:
            producer_path.relative_to(repo)

        except ValueError:
            errors.append(
                "required-gate evidence "
                "producer path escapes repo"
            )

        else:
            producer_digest = sha256(
                producer_path,
                "required-gate evidence producer",
                errors,
            )

            if (
                producer_digest
                != producer.get("tool_sha256")
            ):
                errors.append(
                    "required-gate evidence "
                    "producer digest mismatch"
                )

    else:
        errors.append(
            "required-gate evidence "
            "producer.tool_path must be non-empty"
        )

    if errors or any(
        value is None
        for value in (
            policy_sha,
            registry_sha,
            thresholds_sha,
            tool_sha,
            status_sha,
            evidence_sha,
        )
    ):
        return None

    assert policy_sha
    assert registry_sha
    assert thresholds_sha
    assert tool_sha
    assert status_sha
    assert evidence_sha

    return Context(
        repo=repo,
        status_path=status_path,
        evidence_path=evidence_path,
        refusal_path=refusal_path,
        external_dir=external_dir,
        policy_sha=policy_sha,
        registry_sha=registry_sha,
        thresholds_sha=thresholds_sha,
        tool_sha=tool_sha,
        required=required,
        release_required=release_required,
        run_identity=dict(run_identity),
        subject=dict(subject),
        status_sha=status_sha,
        evidence_sha=evidence_sha,
    )


def detector_candidate(
    ctx: Context,
) -> dict[str, Any]:
    return envelope(
        evidence_id="detector_materialization",
        evidence_kind="detector_materialization",
        run_identity=ctx.run_identity,
        policy_sha=ctx.policy_sha,
        registry_sha=ctx.registry_sha,
        tool_sha=ctx.tool_sha,
        raw_path=REQUIRED_EVIDENCE,
        raw_sha=ctx.evidence_sha,
        raw_kind="required_gate_evidence",
        raw_schema=REQUIRED_EVIDENCE_SCHEMA,
        gates=[
            "detectors_materialized_ok"
        ],
        checks=[
            validation_check(
                (
                    "pulse.recorded.detector."
                    "required-evidence.v0"
                ),
                "semantic",
                (
                    "Required-gate evidence exactly "
                    "covers gates.required and all "
                    "gates passed."
                ),
                ctx.tool_sha,
                [
                    REQUIRED_EVIDENCE,
                    STATUS,
                    POLICY,
                    REGISTRY,
                    REQUIRED_EVIDENCE_SCHEMA_PATH,
                ],
            )
        ],
    )


def refusal_candidate(
    ctx: Context,
    errors: list[str],
) -> dict[str, Any] | None:
    summary = load_json(
        ctx.refusal_path,
        "refusal-delta summary",
        errors,
    )

    if summary is None:
        return None

    raw_n = summary.get("n")

    if isinstance(raw_n, bool):
        errors.append(
            "refusal-delta summary n "
            "must be an integer"
        )
        n = 0

    else:
        try:
            n = int(raw_n)

        except (TypeError, ValueError):
            errors.append(
                "refusal-delta summary n "
                "must be an integer"
            )
            n = 0

    if n <= 0:
        errors.append(
            "refusal-delta summary n must "
            "be greater than zero"
        )

    if summary.get("pass") is not True:
        errors.append(
            "refusal-delta summary pass "
            "must be literal true"
        )

    digest = sha256(
        ctx.refusal_path,
        "refusal-delta summary",
        errors,
    )

    if errors or digest is None:
        return None

    return envelope(
        evidence_id="refusal_delta_summary",
        evidence_kind="refusal_delta_summary",
        run_identity=ctx.run_identity,
        policy_sha=ctx.policy_sha,
        registry_sha=ctx.registry_sha,
        tool_sha=ctx.tool_sha,
        raw_path=REFUSAL,
        raw_sha=digest,
        raw_kind="refusal_delta_summary",
        raw_schema=(
            summary.get("schema_version")
            if isinstance(
                summary.get("schema_version"),
                str,
            )
            else None
        ),
        gates=[
            "refusal_delta_evidence_present"
        ],
        checks=[
            validation_check(
                (
                    "pulse.recorded.refusal-delta."
                    "presence.v0"
                ),
                "semantic",
                (
                    "Refusal-delta summary has n>0 "
                    "and literal pass=true."
                ),
                ctx.tool_sha,
                [REFUSAL],
            )
        ],
    )


def external_candidates(
    ctx: Context,
    thresholds: dict[str, Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    overall = thresholds.get(
        "external_overall_policy",
        "all",
    )

    if (
        not isinstance(overall, str)
        or overall.strip().lower() != "all"
    ):
        errors.append(
            "external_overall_policy must be "
            "'all' for the v0 per-summary "
            "candidate path"
        )
        return {}

    out: dict[str, dict[str, Any]] = {}
    found = 0

    for detector_id, config in (
        EXTERNAL_DETECTORS.items()
    ):
        existing = [
            ctx.external_dir / filename
            for filename in config["files"]
            if (
                ctx.external_dir / filename
            ).exists()
        ]

        if len(existing) > 1:
            errors.append(
                f"external detector {detector_id!r} "
                "has both JSON and JSONL summaries"
            )
            continue

        if not existing:
            continue

        found += 1
        path = existing[0]
        local: list[str] = []

        payload = load_json_or_jsonl(
            path,
            f"external summary {detector_id}",
            local,
        )

        threshold = number(
            thresholds.get(
                config["threshold"]
            ),
            (
                "thresholds."
                f"{config['threshold']}"
            ),
            local,
        )

        value: float | None = None
        source: str | None = None

        if payload is not None:
            value, source = external_metric(
                payload,
                config["preferred"],
                config["metric"],
                (
                    "external summary "
                    f"{detector_id}"
                ),
                local,
            )

        if (
            value is not None
            and threshold is not None
            and value > threshold
        ):
            local.append(
                "external summary "
                f"{detector_id} value {value} "
                f"exceeds threshold {threshold}"
            )

        digest = sha256(
            path,
            f"external summary {detector_id}",
            local,
        )

        if (
            local
            or payload is None
            or threshold is None
            or value is None
            or digest is None
        ):
            errors.extend(local)
            continue

        evidence_id = (
            f"external_{detector_id}"
        )

        out[evidence_id] = envelope(
            evidence_id=evidence_id,
            evidence_kind="external_summary",
            run_identity=ctx.run_identity,
            policy_sha=ctx.policy_sha,
            registry_sha=ctx.registry_sha,
            tool_sha=ctx.tool_sha,
            raw_path=relative(
                ctx.repo,
                path,
            ),
            raw_sha=digest,
            raw_kind=(
                f"external_summary_{detector_id}"
            ),
            raw_schema=(
                payload.get("schema_version")
                if isinstance(
                    payload.get("schema_version"),
                    str,
                )
                else None
            ),
            gates=[
                "external_summaries_present",
                "external_all_pass",
            ],
            checks=[
                validation_check(
                    (
                        "pulse.recorded.external."
                        f"{detector_id}.v0"
                    ),
                    "semantic",
                    (
                        f"Canonical {detector_id} "
                        f"metric {source!r}={value} "
                        "is within "
                        f"{config['threshold']}="
                        f"{threshold}."
                    ),
                    ctx.tool_sha,
                    [
                        relative(
                            ctx.repo,
                            path,
                        ),
                        THRESHOLDS,
                    ],
                )
            ],
        )

    if found == 0:
        errors.append(
            "no canonical external detector "
            "summaries were found"
        )

    return out


def build_candidates(
    *,
    repo: Path,
    status_path: Path,
    evidence_path: Path,
    evidence_schema_path: Path,
    status_schema_path: Path,
    envelope_schema_path: Path,
    policy_path: Path,
    registry_path: Path,
    thresholds_path: Path,
    refusal_path: Path,
    external_dir: Path,
    tool_path: Path,
) -> tuple[
    dict[str, dict[str, Any]] | None,
    dict[str, Any] | None,
    list[str],
]:
    errors: list[str] = []
    repo = repo.resolve()

    if not repo.is_dir():
        return (
            None,
            None,
            [
                "repo root must be a directory: "
                f"{repo}"
            ],
        )

    specs = (
        (
            status_path,
            STATUS,
            "candidate status",
        ),
        (
            evidence_path,
            REQUIRED_EVIDENCE,
            "required-gate evidence",
        ),
        (
            evidence_schema_path,
            REQUIRED_EVIDENCE_SCHEMA_PATH,
            "evidence schema",
        ),
        (
            status_schema_path,
            STATUS_SCHEMA,
            "status schema",
        ),
        (
            envelope_schema_path,
            ENVELOPE_SCHEMA_PATH,
            "envelope schema",
        ),
        (
            policy_path,
            POLICY,
            "policy",
        ),
        (
            registry_path,
            REGISTRY,
            "registry",
        ),
        (
            thresholds_path,
            THRESHOLDS,
            "external thresholds",
        ),
        (
            refusal_path,
            REFUSAL,
            "refusal-delta summary",
        ),
        (
            tool_path,
            TOOL,
            "candidate builder",
        ),
    )

    files = [
        canonical_file(
            repo,
            supplied,
            expected,
            label,
            errors,
        )
        for supplied, expected, label in specs
    ]

    external = canonical_dir(
        repo,
        external_dir,
        EXTERNAL_DIR,
        "external directory",
        errors,
    )

    if (
        errors
        or any(
            path is None
            for path in files
        )
        or external is None
    ):
        return None, None, errors

    (
        status_path,
        evidence_path,
        evidence_schema_path,
        status_schema_path,
        envelope_schema_path,
        policy_path,
        registry_path,
        thresholds_path,
        refusal_path,
        tool_path,
    ) = files  # type: ignore[misc]

    status = load_json(
        status_path,
        "candidate status",
        errors,
    )

    evidence = load_json(
        evidence_path,
        "required-gate evidence",
        errors,
    )

    evidence_schema = load_json(
        evidence_schema_path,
        "evidence schema",
        errors,
    )

    status_schema = load_json(
        status_schema_path,
        "status schema",
        errors,
    )

    envelope_schema = load_json(
        envelope_schema_path,
        "envelope schema",
        errors,
    )

    policy = load_yaml(
        policy_path,
        "policy",
        errors,
    )

    registry = load_yaml(
        registry_path,
        "registry",
        errors,
    )

    thresholds = load_yaml(
        thresholds_path,
        "external thresholds",
        errors,
    )

    if any(
        item is None
        for item in (
            status,
            evidence,
            evidence_schema,
            status_schema,
            envelope_schema,
            policy,
            registry,
            thresholds,
        )
    ):
        return None, None, errors

    assert status is not None
    assert evidence is not None
    assert evidence_schema is not None
    assert status_schema is not None
    assert envelope_schema is not None
    assert policy is not None
    assert registry is not None
    assert thresholds is not None

    try:
        created_utc()

    except ValueError as exc:
        errors.append(str(exc))
        return None, None, errors

    ctx = validate_base(
        repo=repo,
        status=status,
        evidence=evidence,
        evidence_schema=evidence_schema,
        status_schema=status_schema,
        policy=policy,
        registry=registry,
        status_path=status_path,
        evidence_path=evidence_path,
        refusal_path=refusal_path,
        external_dir=external,
        policy_path=policy_path,
        registry_path=registry_path,
        thresholds_path=thresholds_path,
        tool_path=tool_path,
        errors=errors,
    )

    if ctx is None:
        return None, None, errors

    refusal = refusal_candidate(
        ctx,
        errors,
    )

    externals = external_candidates(
        ctx,
        thresholds,
        errors,
    )

    if (
        errors
        or refusal is None
        or not externals
    ):
        return None, None, errors

    envelopes = {
        "detector_materialization": (
            detector_candidate(ctx)
        ),
        "refusal_delta_summary": refusal,
        **externals,
    }

    for evidence_id, item in envelopes.items():
        if item.get("evidence_id") != evidence_id:
            errors.append(
                f"candidate {evidence_id!r} "
                "evidence_id mismatch"
            )

        if (
            set(
                item.get(
                    "required_for_gates",
                    [],
                )
            )
            - set(ctx.release_required)
        ):
            errors.append(
                f"candidate {evidence_id!r} "
                "targets unsupported gates"
            )

        errors.extend(
            f"candidate {evidence_id} schema "
            f"validation failed: {message}"
            for message in schema_errors(
                item,
                envelope_schema,
            )
        )

    external_ids = sorted(
        key
        for key in envelopes
        if key.startswith("external_")
    )

    if not external_ids:
        errors.append(
            "at least one external candidate "
            "is required"
        )

    if errors:
        return None, None, errors

    index = {
        "schema_version": INDEX_SCHEMA,
        "created_utc": created_utc(),
        "run_identity": dict(
            ctx.run_identity
        ),
        "subject": dict(
            ctx.subject
        ),
        "policy_binding": {
            "policy_path": POLICY,
            "policy_sha256": ctx.policy_sha,
            "policy_set": (
                "required+release_required"
            ),
        },
        "registry_binding": {
            "registry_path": REGISTRY,
            "registry_sha256": ctx.registry_sha,
        },
        "source_bindings": {
            "candidate_status": {
                "path": STATUS,
                "sha256": ctx.status_sha,
            },
            "required_gate_evidence": {
                "path": REQUIRED_EVIDENCE,
                "sha256": ctx.evidence_sha,
                "schema_version": (
                    REQUIRED_EVIDENCE_SCHEMA
                ),
            },
            "external_thresholds": {
                "path": THRESHOLDS,
                "sha256": ctx.thresholds_sha,
            },
        },
        "candidate_ids": sorted(envelopes),
        "external_candidate_ids": external_ids,
        "release_required_gates": list(
            ctx.release_required
        ),
        "authority_boundary": {
            "normative": False,
            "creates_release_authority": False,
            "materializes_release_required": False,
            "eligible_without_verifier": False,
            "replaces_check_gates": False,
        },
    }

    return envelopes, index, []


def build_canonical_candidates_for_replay(
    repo: Path,
) -> tuple[
    dict[str, dict[str, Any]] | None,
    dict[str, Any] | None,
    list[str],
]:
    """Recompute canonical candidate envelopes in memory.

    This replay uses the same canonical inputs and producer
    implementation as the normal candidate build.

    It does not clear, replace, or write candidate outputs.
    It does not materialize gates or create release authority.
    """

    return build_candidates(
        repo=repo,
        status_path=Path(
            STATUS
        ),
        evidence_path=Path(
            REQUIRED_EVIDENCE
        ),
        evidence_schema_path=Path(
            REQUIRED_EVIDENCE_SCHEMA_PATH
        ),
        status_schema_path=Path(
            STATUS_SCHEMA
        ),
        envelope_schema_path=Path(
            ENVELOPE_SCHEMA_PATH
        ),
        policy_path=Path(
            POLICY
        ),
        registry_path=Path(
            REGISTRY
        ),
        thresholds_path=Path(
            THRESHOLDS
        ),
        refusal_path=Path(
            REFUSAL
        ),
        external_dir=Path(
            EXTERNAL_DIR
        ),
        tool_path=Path(
            TOOL
        ),
    )


def canonical_output(
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
            f"{label} must use canonical path "
            f"{expected!r}"
        )
        return None

    return canonical


def clear_outputs(
    out_dir: Path,
    index_path: Path,
) -> None:
    """Remove stale outputs before a new build."""

    if out_dir.exists() or out_dir.is_symlink():
        if (
            out_dir.is_symlink()
            or not out_dir.is_dir()
        ):
            out_dir.unlink()

        else:
            shutil.rmtree(out_dir)

    if (
        index_path.exists()
        or index_path.is_symlink()
    ):
        if (
            index_path.is_dir()
            and not index_path.is_symlink()
        ):
            shutil.rmtree(index_path)

        else:
            index_path.unlink()


def write_outputs(
    repo: Path,
    out_dir: Path,
    index_path: Path,
    envelopes: dict[str, dict[str, Any]],
    index: dict[str, Any],
) -> None:
    artifacts = (
        repo
        / "PULSE_safe_pack_v0/artifacts"
    ).resolve()

    artifacts.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = Path(
        tempfile.mkdtemp(
            prefix="recorded-release-",
            dir=artifacts,
        )
    )

    temporary_dir = (
        temporary / "candidates"
    )

    temporary_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    refs: dict[str, dict[str, Any]] = {}

    try:
        for evidence_id in sorted(envelopes):
            path = (
                temporary_dir
                / f"{evidence_id}.json"
            )

            path.write_text(
                json.dumps(
                    envelopes[evidence_id],
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n",
                encoding="utf-8",
            )

            refs[evidence_id] = {
                "path": (
                    f"{OUT_DIR}/"
                    f"{evidence_id}.json"
                ),
                "sha256": hashlib.sha256(
                    path.read_bytes()
                ).hexdigest(),
                "schema_version": (
                    ENVELOPE_SCHEMA
                ),
                "required_for_gates": (
                    envelopes[evidence_id][
                        "required_for_gates"
                    ]
                ),
                "subject_binding": (
                    envelopes[evidence_id][
                        "subject_binding"
                    ]
                ),
            }

        payload = dict(index)
        payload["candidates"] = refs

        temporary_index = (
            temporary / "index.json"
        )

        temporary_index.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        os.replace(
            temporary_dir,
            out_dir,
        )

        target = index_path.with_name(
            index_path.name + ".tmp"
        )

        shutil.copy2(
            temporary_index,
            target,
        )

        os.replace(
            target,
            index_path,
        )

    finally:
        shutil.rmtree(
            temporary,
            ignore_errors=True,
        )


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
        "--status",
        default=STATUS,
    )

    parser.add_argument(
        "--required-evidence",
        default=REQUIRED_EVIDENCE,
    )

    parser.add_argument(
        "--required-evidence-schema",
        default=REQUIRED_EVIDENCE_SCHEMA_PATH,
    )

    parser.add_argument(
        "--status-schema",
        default=STATUS_SCHEMA,
    )

    parser.add_argument(
        "--envelope-schema",
        default=ENVELOPE_SCHEMA_PATH,
    )

    parser.add_argument(
        "--policy",
        default=POLICY,
    )

    parser.add_argument(
        "--registry",
        default=REGISTRY,
    )

    parser.add_argument(
        "--thresholds",
        default=THRESHOLDS,
    )

    parser.add_argument(
        "--refusal-summary",
        default=REFUSAL,
    )

    parser.add_argument(
        "--external-dir",
        default=EXTERNAL_DIR,
    )

    parser.add_argument(
        "--out-dir",
        default=OUT_DIR,
    )

    parser.add_argument(
        "--index",
        default=INDEX,
    )

    args = parser.parse_args(argv)

    repo = Path(
        args.repo_root
    ).resolve()

    if not repo.is_dir():
        print(
            "ERRORS (fail-closed):\n"
            " - repo root is not a directory: "
            f"{repo}",
            file=sys.stderr,
        )
        return 1

    path_errors: list[str] = []

    out_dir = canonical_output(
        repo,
        Path(args.out_dir),
        OUT_DIR,
        "output directory",
        path_errors,
    )

    index_path = canonical_output(
        repo,
        Path(args.index),
        INDEX,
        "index path",
        path_errors,
    )

    if out_dir is None or index_path is None:
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

    clear_outputs(
        out_dir,
        index_path,
    )

    envelopes, index, errors = (
        build_candidates(
            repo=repo,
            status_path=Path(args.status),
            evidence_path=Path(
                args.required_evidence
            ),
            evidence_schema_path=Path(
                args.required_evidence_schema
            ),
            status_schema_path=Path(
                args.status_schema
            ),
            envelope_schema_path=Path(
                args.envelope_schema
            ),
            policy_path=Path(args.policy),
            registry_path=Path(args.registry),
            thresholds_path=Path(
                args.thresholds
            ),
            refusal_path=Path(
                args.refusal_summary
            ),
            external_dir=Path(
                args.external_dir
            ),
            tool_path=Path(TOOL),
        )
    )

    if envelopes is None or index is None:
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

    write_outputs(
        repo,
        out_dir,
        index_path,
        envelopes,
        index,
    )

    print(f"Wrote {index_path}")
    print(
        f"Wrote {len(envelopes)} "
        "candidate envelope(s) under "
        f"{out_dir}"
    )
    print(
        "OK: built verifier-facing "
        "recorded-release candidates without "
        "materializing release_required gates"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
