#!/usr/bin/env python3
"""Verify a release-grade external-summary attestation fail closed.

This tool verifies the external summary and its verification envelope before
the summary can be admitted to the recorded-release candidate path.

Mechanical boundary:

external summary
-> canonical summary schema
-> canonical verification-envelope schema
-> summary digest and reference binding
-> signer-policy admission
-> cryptographic GitHub attestation verification
-> verified/non-authoritative verification report

The report produced here does not create release authority, materialize gates,
modify status.json, or replace check_gates.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


REPORT_SCHEMA_VERSION = (
    "external_summary_attestation_verifier_v1"
)
SUMMARY_SCHEMA_VERSION = "external_summary_v1"
ENVELOPE_SCHEMA_VERSION = (
    "external_summary_envelope_v1"
)

SUMMARY_SCHEMA_PATH = (
    "schemas/external_summary_v1.schema.json"
)
ENVELOPE_SCHEMA_PATH = (
    "schemas/external_summary_envelope_v1.schema.json"
)
SIGNER_POLICY_PATH = "policy/external_signers_v1.yml"
THRESHOLD_POLICY_PATH = (
    "PULSE_safe_pack_v0/profiles/"
    "external_thresholds.yaml"
)
EXTERNAL_DIR = "PULSE_safe_pack_v0/artifacts/external"

GITHUB_ATTESTATION_MODE = "github-attestation"
GITHUB_OIDC_ISSUER = (
    "https://token.actions.githubusercontent.com"
)
SLSA_PROVENANCE_V1 = (
    "https://slsa.dev/provenance/v1"
)

SHA256_RE = re.compile(
    r"^[0-9a-f]{64}$",
    re.IGNORECASE,
)
GIT_SHA_RE = re.compile(
    r"^[0-9a-f]{40}$",
    re.IGNORECASE,
)
GITHUB_IDENTITY_RE = re.compile(
    r"^repo:"
    r"(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
    r":workflow:"
    r"(?P<workflow>[A-Za-z0-9_.\-/]+)$"
)

AUTHORITY_BOUNDARY = {
    "normative": False,
    "creates_release_authority": False,
    "materializes_status": False,
    "materializes_release_required": False,
    "replaces_check_gates": False,
}


class UniqueYamlLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _yaml_mapping(
    loader: UniqueYamlLoader,
    node: Any,
    deep: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(
            key_node,
            deep=deep,
        )

        if key in result:
            raise ValueError(
                f"duplicate YAML key {key!r}"
            )

        result[key] = loader.construct_object(
            value_node,
            deep=deep,
        )

    return result


UniqueYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _yaml_mapping,
)


def _json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise ValueError(
                f"duplicate JSON key {key!r}"
            )

        result[key] = value

    return result


def _nonfinite(value: str) -> None:
    raise ValueError(
        f"non-finite JSON constant {value!r}"
    )


def _is_non_empty_text(
    value: Any,
) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
    )


def _load_json(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if (
            path.is_symlink()
            or not path.is_file()
        ):
            errors.append(
                f"{label} not found as a "
                f"regular file: {path}"
            )
            return None

        value = json.loads(
            path.read_text(
                encoding="utf-8",
            ),
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


def _load_yaml(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if (
            path.is_symlink()
            or not path.is_file()
        ):
            errors.append(
                f"{label} not found as a "
                f"regular file: {path}"
            )
            return None

        value = yaml.load(
            path.read_text(
                encoding="utf-8",
            ),
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


def _sha256(
    path: Path,
    label: str,
    errors: list[str],
) -> str | None:
    try:
        if (
            path.is_symlink()
            or not path.is_file()
        ):
            errors.append(
                f"{label} not found as a "
                f"regular file: {path}"
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
            f"{label} could not be hashed: "
            f"{exc}"
        )
        return None


def _canonical_file(
    *,
    repo_root: Path,
    supplied: Path,
    label: str,
    expected: str | None,
    errors: list[str],
) -> Path | None:
    path = (
        supplied.resolve()
        if supplied.is_absolute()
        else (repo_root / supplied).resolve()
    )

    try:
        path.relative_to(repo_root)

    except ValueError:
        errors.append(
            f"{label} must remain inside "
            f"the repository root: {path}"
        )
        return None

    if expected is not None:
        canonical = (
            repo_root / expected
        ).resolve()

        if path != canonical:
            errors.append(
                f"{label} must use canonical "
                f"path {expected!r}"
            )
            return None

    if (
        path.is_symlink()
        or not path.is_file()
    ):
        errors.append(
            f"{label} not found as a "
            f"regular non-symlink file: {path}"
        )
        return None

    return path


def _external_file(
    *,
    repo_root: Path,
    external_root: Path,
    supplied: Path,
    label: str,
    errors: list[str],
) -> Path | None:
    path = (
        supplied.resolve()
        if supplied.is_absolute()
        else (repo_root / supplied).resolve()
    )

    try:
        path.relative_to(
            external_root.resolve()
        )

    except ValueError:
        errors.append(
            f"{label} must remain inside "
            f"{EXTERNAL_DIR!r}"
        )
        return None

    if (
        path.is_symlink()
        or not path.is_file()
    ):
        errors.append(
            f"{label} not found as a "
            f"regular non-symlink file: {path}"
        )
        return None

    return path


def _relative(
    repo_root: Path,
    path: Path,
) -> str:
    return (
        path.resolve()
        .relative_to(repo_root.resolve())
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

    result: list[str] = []

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

        result.append(
            (
                f"{location}: "
                if location
                else ""
            )
            + error.message
        )

    return result


def _section(
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


def _string_list(
    value: Any,
    label: str,
    errors: list[str],
) -> list[str]:
    if not isinstance(value, list):
        errors.append(
            f"{label} must be an array"
        )
        return []

    result: list[str] = []

    for raw in value:
        if not _is_non_empty_text(raw):
            errors.append(
                f"{label} entries must be "
                "non-empty strings"
            )
            continue

        result.append(
            str(raw).strip()
        )

    return result


def _identity_to_signer_workflow(
    identity: str,
    errors: list[str],
) -> tuple[str | None, str | None]:
    match = GITHUB_IDENTITY_RE.fullmatch(
        identity
    )

    if match is None:
        errors.append(
            "GitHub attestation identity must "
            "use "
            "'repo:<owner>/<repo>:workflow:"
            "<workflow-name-or-path>'"
        )
        return None, None

    repository = match.group(
        "repository"
    )
    workflow = match.group(
        "workflow"
    )

    workflow_path = Path(workflow)

    if (
        workflow_path.is_absolute()
        or ".." in workflow_path.parts
    ):
        errors.append(
            "GitHub attestation workflow "
            "identity must be a safe "
            "repository-relative workflow name "
            "or path"
        )
        return None, None

    workflow_text = workflow_path.as_posix()

    if "/" not in workflow_text:
        workflow_text = (
            ".github/workflows/"
            f"{workflow_text}"
        )

    if not workflow_text.endswith(
        (".yml", ".yaml")
    ):
        workflow_text += ".yml"

    signer_workflow = (
        f"github.com/{repository}/"
        f"{workflow_text}"
    )

    return repository, signer_workflow


def _match_signer_policy(
    *,
    policy: dict[str, Any],
    tool_name: str,
    mode: str,
    identity: str,
    release_contribution: str,
    errors: list[str],
) -> None:
    defaults = _section(
        policy,
        "release_grade_defaults",
        "signer policy",
        errors,
    )

    required_true = (
        "require_schema_valid_summary",
        "require_schema_valid_envelope",
        "require_summary_digest",
        "require_subject_digest",
        "require_tool_identity",
        "require_tool_version",
        "require_threshold_ref",
        "require_signer_identity",
        "require_verification_before_fold_in",
    )

    for key in required_true:
        if defaults.get(key) is not True:
            errors.append(
                "signer policy "
                f"release_grade_defaults.{key} "
                "must be literal true"
            )

    if (
        defaults.get(
            "allow_unsigned_release_grade"
        )
        is not False
    ):
        errors.append(
            "signer policy must set "
            "allow_unsigned_release_grade=false"
        )

    if (
        defaults.get(
            "allow_unverified_fold_in"
        )
        is not False
    ):
        errors.append(
            "signer policy must set "
            "allow_unverified_fold_in=false"
        )

    signing_modes = _section(
        policy,
        "allowed_signing_modes",
        "signer policy",
        errors,
    )

    release_modes = _string_list(
        signing_modes.get("release_grade"),
        (
            "signer policy."
            "allowed_signing_modes."
            "release_grade"
        ),
        errors,
    )

    if mode not in release_modes:
        errors.append(
            f"signing mode {mode!r} is not "
            "allowed for release-grade evidence"
        )

    tool_policies = _section(
        policy,
        "tool_policies",
        "signer policy",
        errors,
    )

    tool_policy = tool_policies.get(
        tool_name
    )

    if not isinstance(tool_policy, dict):
        errors.append(
            f"signer policy has no tool policy "
            f"for {tool_name!r}"
        )
        return

    if (
        tool_policy.get(
            "release_grade_contribution_allowed"
        )
        is not True
    ):
        errors.append(
            f"signer policy does not allow "
            f"release-grade contribution for "
            f"{tool_name!r}"
        )

    allowed_groups = _string_list(
        tool_policy.get(
            "allowed_identity_groups"
        ),
        (
            "signer policy.tool_policies."
            f"{tool_name}."
            "allowed_identity_groups"
        ),
        errors,
    )

    identities = _section(
        policy,
        "allowed_identities",
        "signer policy",
        errors,
    )

    matched = False

    for group_name in allowed_groups:
        group = identities.get(
            group_name
        )

        if not isinstance(group, dict):
            errors.append(
                f"signer policy identity group "
                f"{group_name!r} is missing"
            )
            continue

        entries = group.get("identities")

        if not isinstance(entries, list):
            errors.append(
                f"signer policy identity group "
                f"{group_name!r}.identities "
                "must be an array"
            )
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(
                    f"signer policy identity group "
                    f"{group_name!r} entries "
                    "must be objects"
                )
                continue

            pattern = entry.get("pattern")

            if not _is_non_empty_text(pattern):
                errors.append(
                    f"signer policy identity group "
                    f"{group_name!r} pattern "
                    "must be non-empty"
                )
                continue

            pattern_text = str(
                pattern
            ).strip()

            if any(
                token in pattern_text
                for token in (
                    "*",
                    "?",
                    "[",
                    "]",
                )
            ):
                errors.append(
                    "release-grade signer identity "
                    "patterns must be exact and "
                    "must not contain wildcards"
                )
                continue

            if identity != pattern_text:
                continue

            entry_modes = _string_list(
                entry.get("modes"),
                (
                    "signer policy identity "
                    f"group {group_name!r}.modes"
                ),
                errors,
            )

            contributions = _string_list(
                entry.get(
                    "release_contributions"
                ),
                (
                    "signer policy identity "
                    f"group {group_name!r}."
                    "release_contributions"
                ),
                errors,
            )

            if (
                mode in entry_modes
                and release_contribution
                in contributions
            ):
                matched = True

    if not matched:
        errors.append(
            "signer identity is not allowed "
            "for the declared signing mode and "
            "release contribution"
        )


def verify_external_summary_attestation(
    *,
    repo_root: Path,
    summary_path: Path,
    envelope_path: Path,
    summary_schema_path: Path,
    envelope_schema_path: Path,
    signer_policy_path: Path,
    expected_repository: str,
    expected_source_digest: str,
    gh_executable: str = "gh",
) -> dict[str, Any]:
    errors: list[str] = []
    repo_root = repo_root.resolve()

    report: dict[str, Any] = {
        "schema_version": (
            REPORT_SCHEMA_VERSION
        ),
        "status": "failed",
        "summary": {},
        "envelope": {},
        "signer": {},
        "attestation": {
            "backend": "gh-attestation",
            "verified": False,
        },
        "errors": errors,
        "authority_boundary": dict(
            AUTHORITY_BOUNDARY
        ),
    }

    if not repo_root.is_dir():
        errors.append(
            f"repo root must be a directory: "
            f"{repo_root}"
        )
        return report

    if (
        not _is_non_empty_text(
            expected_repository
        )
        or "/" not in expected_repository
    ):
        errors.append(
            "expected repository must use "
            "'<owner>/<repo>' form"
        )

    if (
        not isinstance(
            expected_source_digest,
            str,
        )
        or not GIT_SHA_RE.fullmatch(
            expected_source_digest
        )
    ):
        errors.append(
            "expected source digest must be "
            "a concrete 40-hex git SHA"
        )

    external_root = (
        repo_root / EXTERNAL_DIR
    ).resolve()

    summary = _external_file(
        repo_root=repo_root,
        external_root=external_root,
        supplied=summary_path,
        label="external summary",
        errors=errors,
    )

    verification_envelope = (
        _external_file(
            repo_root=repo_root,
            external_root=external_root,
            supplied=envelope_path,
            label=(
                "external summary "
                "verification envelope"
            ),
            errors=errors,
        )
    )

    summary_schema_file = _canonical_file(
        repo_root=repo_root,
        supplied=summary_schema_path,
        expected=SUMMARY_SCHEMA_PATH,
        label="external summary schema",
        errors=errors,
    )

    envelope_schema_file = (
        _canonical_file(
            repo_root=repo_root,
            supplied=envelope_schema_path,
            expected=ENVELOPE_SCHEMA_PATH,
            label=(
                "external summary "
                "envelope schema"
            ),
            errors=errors,
        )
    )

    signer_policy_file = _canonical_file(
        repo_root=repo_root,
        supplied=signer_policy_path,
        expected=SIGNER_POLICY_PATH,
        label="external signer policy",
        errors=errors,
    )

    if errors:
        return report

    assert summary is not None
    assert verification_envelope is not None
    assert summary_schema_file is not None
    assert envelope_schema_file is not None
    assert signer_policy_file is not None

    summary_payload = _load_json(
        summary,
        "external summary",
        errors,
    )
    envelope_payload = _load_json(
        verification_envelope,
        (
            "external summary "
            "verification envelope"
        ),
        errors,
    )
    summary_schema = _load_json(
        summary_schema_file,
        "external summary schema",
        errors,
    )
    envelope_schema = _load_json(
        envelope_schema_file,
        (
            "external summary "
            "envelope schema"
        ),
        errors,
    )
    signer_policy = _load_yaml(
        signer_policy_file,
        "external signer policy",
        errors,
    )

    if (
        summary_payload is None
        or envelope_payload is None
        or summary_schema is None
        or envelope_schema is None
        or signer_policy is None
    ):
        return report

    errors.extend(
        "external summary schema "
        f"validation failed: {message}"
        for message in _schema_errors(
            summary_payload,
            summary_schema,
        )
    )

    errors.extend(
        "external summary envelope schema "
        f"validation failed: {message}"
        for message in _schema_errors(
            envelope_payload,
            envelope_schema,
        )
    )

    summary_digest = _sha256(
        summary,
        "external summary",
        errors,
    )
    envelope_digest = _sha256(
        verification_envelope,
        (
            "external summary "
            "verification envelope"
        ),
        errors,
    )

    report["summary"] = {
        "path": _relative(
            repo_root,
            summary,
        ),
        "sha256": summary_digest,
        "schema_version": (
            summary_payload.get(
                "schema_version"
            )
        ),
        "summary_id": summary_payload.get(
            "summary_id"
        ),
    }

    report["envelope"] = {
        "path": _relative(
            repo_root,
            verification_envelope,
        ),
        "sha256": envelope_digest,
        "schema_version": (
            envelope_payload.get(
                "schema_version"
            )
        ),
        "envelope_id": (
            envelope_payload.get(
                "envelope_id"
            )
        ),
    }

    summary_ref = _section(
        envelope_payload,
        "summary_ref",
        "external summary envelope",
        errors,
    )
    declared_digest = _section(
        envelope_payload,
        "summary_digest",
        "external summary envelope",
        errors,
    )
    envelope_signing = _section(
        envelope_payload,
        "signing",
        "external summary envelope",
        errors,
    )
    verification = _section(
        envelope_payload,
        "verification",
        "external summary envelope",
        errors,
    )
    policy_context = _section(
        envelope_payload,
        "policy_context",
        "external summary envelope",
        errors,
    )
    summary_signing = _section(
        summary_payload,
        "signing",
        "external summary",
        errors,
    )
    summary_tool = _section(
        summary_payload,
        "tool",
        "external summary",
        errors,
    )
    summary_result = _section(
        summary_payload,
        "result",
        "external summary",
        errors,
    )

    summary_relative = _relative(
        repo_root,
        summary,
    )

    if (
        summary_ref.get("uri")
        != summary_relative
    ):
        errors.append(
            "external summary envelope "
            "summary_ref.uri must match the "
            "canonical summary path"
        )

    if (
        summary_ref.get("schema_version")
        != SUMMARY_SCHEMA_VERSION
    ):
        errors.append(
            "external summary envelope "
            "summary_ref.schema_version must be "
            f"{SUMMARY_SCHEMA_VERSION!r}"
        )

    if (
        summary_ref.get("summary_id")
        != summary_payload.get("summary_id")
    ):
        errors.append(
            "external summary envelope "
            "summary_ref.summary_id must match "
            "the wrapped summary"
        )

    if (
        declared_digest.get("algorithm")
        != "sha256"
    ):
        errors.append(
            "external summary envelope "
            "summary_digest.algorithm must be "
            "'sha256'"
        )

    if (
        summary_digest is not None
        and declared_digest.get("value")
        != summary_digest
    ):
        errors.append(
            "external summary envelope "
            "summary digest mismatch"
        )

    mode = envelope_signing.get("mode")
    identity = envelope_signing.get(
        "identity"
    )
    release_contribution = (
        policy_context.get(
            "release_contribution"
        )
    )
    tool_name = summary_tool.get("name")

    if (
        summary_signing.get("mode")
        != mode
        or summary_signing.get("identity")
        != identity
    ):
        errors.append(
            "summary and verification-envelope "
            "signing identity/mode must match"
        )

    if (
        verification.get("verified")
        is not True
    ):
        errors.append(
            "external summary envelope "
            "verification.verified must be "
            "literal true"
        )

    if (
        policy_context.get(
            "fold_in_allowed"
        )
        is not True
    ):
        errors.append(
            "external summary envelope "
            "policy_context.fold_in_allowed "
            "must be literal true"
        )

    if (
        release_contribution
        != "required"
        or summary_result.get(
            "release_contribution"
        )
        != "required"
    ):
        errors.append(
            "summary and envelope release "
            "contribution must both be "
            "'required'"
        )

    if (
        policy_context.get(
            "signer_policy_ref"
        )
        != SIGNER_POLICY_PATH
    ):
        errors.append(
            "external summary envelope "
            "signer_policy_ref must use the "
            "canonical signer policy"
        )

    if (
        policy_context.get(
            "threshold_policy_ref"
        )
        != THRESHOLD_POLICY_PATH
    ):
        errors.append(
            "external summary envelope "
            "threshold_policy_ref must use the "
            "canonical threshold policy"
        )

    if not _is_non_empty_text(tool_name):
        errors.append(
            "external summary tool.name "
            "must be non-empty"
        )

    if not _is_non_empty_text(mode):
        errors.append(
            "external summary signing.mode "
            "must be non-empty"
        )

    if not _is_non_empty_text(identity):
        errors.append(
            "external summary signing.identity "
            "must be non-empty"
        )

    if (
        isinstance(tool_name, str)
        and isinstance(mode, str)
        and isinstance(identity, str)
        and isinstance(
            release_contribution,
            str,
        )
    ):
        _match_signer_policy(
            policy=signer_policy,
            tool_name=tool_name,
            mode=mode,
            identity=identity,
            release_contribution=(
                release_contribution
            ),
            errors=errors,
        )

    if mode != GITHUB_ATTESTATION_MODE:
        errors.append(
            "release-grade external evidence "
            "verification currently supports "
            "only 'github-attestation'"
        )

    identity_repository: str | None = None
    signer_workflow: str | None = None

    if isinstance(identity, str):
        (
            identity_repository,
            signer_workflow,
        ) = _identity_to_signer_workflow(
            identity,
            errors,
        )

    if (
        identity_repository is not None
        and identity_repository
        != expected_repository
    ):
        errors.append(
            "signer identity repository must "
            "match the expected repository"
        )

    bundle_uri = envelope_signing.get(
        "bundle_uri"
    )
    bundle_path: Path | None = None

    if not _is_non_empty_text(bundle_uri):
        errors.append(
            "GitHub attestation envelope "
            "signing.bundle_uri must be "
            "non-empty"
        )
    else:
        bundle_path = _external_file(
            repo_root=repo_root,
            external_root=external_root,
            supplied=Path(
                str(bundle_uri).strip()
            ),
            label=(
                "GitHub attestation bundle"
            ),
            errors=errors,
        )

    report["signer"] = {
        "mode": mode,
        "identity": identity,
        "repository": identity_repository,
        "signer_workflow": signer_workflow,
        "policy_path": (
            SIGNER_POLICY_PATH
        ),
    }

    if errors:
        return report

    assert bundle_path is not None
    assert signer_workflow is not None
    assert summary_digest is not None

    gh_path = shutil.which(
        gh_executable
    )

    if gh_path is None:
        errors.append(
            "GitHub CLI executable 'gh' "
            "was not found"
        )
        return report

    command = [
        gh_path,
        "attestation",
        "verify",
        str(summary),
        "--repo",
        expected_repository,
        "--bundle",
        str(bundle_path),
        "--signer-workflow",
        signer_workflow,
        "--source-digest",
        expected_source_digest.lower(),
        "--predicate-type",
        SLSA_PROVENANCE_V1,
        "--cert-oidc-issuer",
        GITHUB_OIDC_ISSUER,
        "--format",
        "json",
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=120,
        )

    except (
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        errors.append(
            "GitHub attestation verification "
            f"could not be executed: {exc}"
        )
        return report

    if completed.returncode != 0:
        errors.append(
            "GitHub attestation verification "
            "failed"
            + (
                f": {completed.stderr.strip()}"
                if completed.stderr.strip()
                else ""
            )
        )
        return report

    try:
        verification_output = json.loads(
            completed.stdout,
            object_pairs_hook=_json_object,
            parse_constant=_nonfinite,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(
            "GitHub attestation verification "
            f"output is not valid JSON: {exc}"
        )
        return report

    if (
        not isinstance(
            verification_output,
            list,
        )
        or not verification_output
    ):
        errors.append(
            "GitHub attestation verification "
            "must return a non-empty JSON array"
        )
        return report

    report["attestation"] = {
        "backend": "gh-attestation",
        "verified": True,
        "summary_sha256": summary_digest,
        "bundle_path": _relative(
            repo_root,
            bundle_path,
        ),
        "command_contract": {
            "repository": expected_repository,
            "signer_workflow": (
                signer_workflow
            ),
            "source_digest": (
                expected_source_digest.lower()
            ),
            "predicate_type": (
                SLSA_PROVENANCE_V1
            ),
            "oidc_issuer": (
                GITHUB_OIDC_ISSUER
            ),
        },
        "verified_attestation_count": len(
            verification_output
        ),
    }

    report["status"] = "verified"
    return report


def _write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
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


def main(
    argv: list[str] | None = None,
) -> int:
    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    parser = argparse.ArgumentParser(
        description=(
            "Verify a release-grade external "
            "summary and its GitHub "
            "attestation envelope."
        )
    )

    parser.add_argument(
        "--repo-root",
        required=True,
    )
    parser.add_argument(
        "--summary",
        required=True,
    )
    parser.add_argument(
        "--envelope",
        required=True,
    )
    parser.add_argument(
        "--summary-schema",
        default=SUMMARY_SCHEMA_PATH,
    )
    parser.add_argument(
        "--envelope-schema",
        default=ENVELOPE_SCHEMA_PATH,
    )
    parser.add_argument(
        "--signer-policy",
        default=SIGNER_POLICY_PATH,
    )
    parser.add_argument(
        "--repository",
        required=True,
    )
    parser.add_argument(
        "--source-digest",
        required=True,
    )
    parser.add_argument(
        "--out",
        required=True,
    )

    args = parser.parse_args(argv)

    repo_root = Path(
        args.repo_root
    ).resolve()

    report = (
        verify_external_summary_attestation(
            repo_root=repo_root,
            summary_path=Path(
                args.summary
            ),
            envelope_path=Path(
                args.envelope
            ),
            summary_schema_path=Path(
                args.summary_schema
            ),
            envelope_schema_path=Path(
                args.envelope_schema
            ),
            signer_policy_path=Path(
                args.signer_policy
            ),
            expected_repository=(
                args.repository
            ),
            expected_source_digest=(
                args.source_digest
            ),
        )
    )

    out_path = Path(args.out)

    if not out_path.is_absolute():
        out_path = (
            repo_root / out_path
        )

    _write_json(
        out_path,
        report,
    )

    if report["status"] != "verified":
        print(
            "ERRORS (fail-closed):",
            file=sys.stderr,
        )

        for error in report["errors"]:
            print(
                f" - {error}",
                file=sys.stderr,
            )

        print(
            f"Verification report written to "
            f"{out_path}",
            file=sys.stderr,
        )
        return 1

    print(
        "OK: external summary attestation "
        "verified"
    )
    print(
        f"Verification report written to "
        f"{out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
