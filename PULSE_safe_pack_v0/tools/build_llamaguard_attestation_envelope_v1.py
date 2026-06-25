#!/usr/bin/env python3
"""Persist and envelope the current-run LlamaGuard GitHub attestation.

Mechanical path:

    canonical llamaguard_summary.json
    -> actions/attest Sigstore bundle
    -> canonical persisted bundle
    -> external_summary_envelope_v1
    -> check_external_summary_attestation_v1.py replay

This builder does not verify the attestation cryptographically, admit a
recorded-release candidate, materialize gates, modify status.json, replace
check_gates.py, or create release authority. Cryptographic verification remains
the responsibility of check_external_summary_attestation_v1.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


BUILDER_ID = "pulse_llamaguard_attestation_envelope_builder_v1"
BUILDER_VERSION = "1.0.0"

TOOL_REL = (
    "PULSE_safe_pack_v0/tools/"
    "build_llamaguard_attestation_envelope_v1.py"
)
SUMMARY_REL = (
    "PULSE_safe_pack_v0/artifacts/external/"
    "llamaguard_summary.json"
)
RAW_REL = (
    "PULSE_safe_pack_v0/artifacts/external/"
    "llamaguard_raw.jsonl"
)
EVALUATOR_MANIFEST_REL = (
    "PULSE_safe_pack_v0/artifacts/external/"
    "llamaguard_evaluator_manifest_v0.json"
)
DATASET_REL = (
    "PULSE_safe_pack_v0/examples/"
    "llamaguard_current_run_cases_v0.jsonl"
)
BUNDLE_REL = (
    "PULSE_safe_pack_v0/artifacts/external/"
    "llamaguard_summary.bundle.json"
)
ENVELOPE_REL = (
    "PULSE_safe_pack_v0/artifacts/external/"
    "llamaguard_summary.envelope.json"
)
VERIFIER_REPORT_REL = (
    "PULSE_safe_pack_v0/artifacts/external/"
    "llamaguard_attestation_verifier_v1.json"
)

SUMMARY_SCHEMA_REL = "schemas/external_summary_v1.schema.json"
ENVELOPE_SCHEMA_REL = (
    "schemas/external_summary_envelope_v1.schema.json"
)
SIGNER_POLICY_REL = "policy/external_signers_v1.yml"
THRESHOLD_POLICY_REL = (
    "PULSE_safe_pack_v0/profiles/"
    "external_thresholds.yaml"
)
VERIFIER_REL = (
    "PULSE_safe_pack_v0/tools/"
    "check_external_summary_attestation_v1.py"
)
WORKFLOW_REL = ".github/workflows/pulse_ci.yml"

EXPECTED_REPOSITORY = "HKati/pulse-release-gates-0.1"
EXPECTED_SIGNER_IDENTITY = (
    "repo:HKati/pulse-release-gates-0.1:"
    "workflow:.github/workflows/pulse_ci.yml"
)
EXPECTED_TOOL_NAME = "llamaguard"
EXPECTED_THRESHOLD_KEY = "llamaguard_violation_rate_max"
EXPECTED_SIGNING_MODE = "github-attestation"

SUMMARY_SCHEMA_VERSION = "external_summary_v1"
ENVELOPE_SCHEMA_VERSION = "external_summary_envelope_v1"

GITHUB_OIDC_ISSUER = (
    "https://token.actions.githubusercontent.com"
)
SLSA_PROVENANCE_V1 = (
    "https://slsa.dev/provenance/v1"
)

AUTHORITY_BOUNDARY = (
    "This external summary envelope does not define release authority. "
    "It records digest, signer, verification, and policy context for "
    "external evidence before any policy-controlled fold-in to status.json."
)

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ATTESTATION_ID_RE = re.compile(r"^[1-9][0-9]*$")
ACTION_REF_RE = re.compile(
    r"^actions/attest@[0-9a-f]{40}$"
)


class EnvelopeError(ValueError):
    """Fail-closed LlamaGuard attestation-envelope error."""


class UniqueJsonError(EnvelopeError):
    """Strict JSON parse error."""


def _json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise UniqueJsonError(
                f"duplicate JSON key {key!r}"
            )

        result[key] = value

    return result


def _reject_nonfinite(value: str) -> None:
    raise UniqueJsonError(
        f"non-finite JSON constant {value!r}"
    )


def _require_finite_json_tree(
    value: Any,
    label: str,
) -> None:
    if (
        value is None
        or isinstance(value, (str, bool, int))
    ):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise EnvelopeError(
                f"{label} contains a non-finite number"
            )

        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_finite_json_tree(
                item,
                f"{label}[{index}]",
            )

        return

    if isinstance(value, dict):
        for key, item in value.items():
            _require_finite_json_tree(
                item,
                f"{label}.{key}",
            )

        return

    raise EnvelopeError(
        f"{label} contains an unsupported JSON value"
    )


def _require_text(
    value: Any,
    label: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnvelopeError(
            f"{label} must be a non-empty string"
        )

    return value.strip()


def _require_object(
    parent: dict[str, Any],
    key: str,
    label: str,
) -> dict[str, Any]:
    value = parent.get(key)

    if not isinstance(value, dict):
        raise EnvelopeError(
            f"{label}.{key} must be an object"
        )

    return value


def _resolve_lexically(
    repo_root: Path,
    supplied: Path,
) -> Path:
    candidate = (
        supplied
        if supplied.is_absolute()
        else repo_root / supplied
    )

    return Path(os.path.abspath(candidate))


def _require_canonical_path(
    repo_root: Path,
    supplied: Path,
    expected_relative: str,
    label: str,
) -> Path:
    actual = _resolve_lexically(
        repo_root,
        supplied,
    )
    expected = _resolve_lexically(
        repo_root,
        Path(expected_relative),
    )

    if actual != expected:
        raise EnvelopeError(
            f"{label} must use canonical path {expected}"
        )

    try:
        actual.relative_to(repo_root)

    except ValueError as exc:
        raise EnvelopeError(
            f"{label} escapes repository root"
        ) from exc

    return actual


def _reject_symlink_components(
    repo_root: Path,
    path: Path,
    label: str,
) -> None:
    try:
        relative = path.relative_to(repo_root)

    except ValueError as exc:
        raise EnvelopeError(
            f"{label} escapes repository root"
        ) from exc

    current = repo_root

    for part in relative.parts:
        current = current / part

        if current.is_symlink():
            raise EnvelopeError(
                f"{label} must not traverse a symlink: "
                f"{current}"
            )


def _require_regular_file(
    path: Path,
    label: str,
) -> None:
    if path.is_symlink() or not path.is_file():
        raise EnvelopeError(
            f"{label} must be a regular non-symlink file: "
            f"{path}"
        )


def _repo_relative(
    repo_root: Path,
    path: Path,
) -> str:
    try:
        return path.relative_to(repo_root).as_posix()

    except ValueError as exc:
        raise EnvelopeError(
            f"path escapes repository root: {path}"
        ) from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    _require_regular_file(
        path,
        f"SHA-256 input {path}",
    )
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _load_json_object(
    path: Path,
    label: str,
) -> dict[str, Any]:
    _require_regular_file(path, label)

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_object,
            parse_constant=_reject_nonfinite,
        )

    except EnvelopeError:
        raise

    except Exception as exc:
        raise EnvelopeError(
            f"{label} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise EnvelopeError(
            f"{label} must be a JSON object"
        )

    _require_finite_json_tree(payload, label)
    return payload


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


def _load_checked_schema(
    path: Path,
    label: str,
) -> dict[str, Any]:
    schema = _load_json_object(path, label)

    try:
        Draft202012Validator.check_schema(schema)

    except Exception as exc:
        raise EnvelopeError(
            f"{label} is not a valid Draft 2020-12 "
            f"schema: {exc}"
        ) from exc

    return schema


def _validate_schema(
    payload: dict[str, Any],
    schema: dict[str, Any],
    label: str,
) -> None:
    errors = _schema_errors(payload, schema)

    if errors:
        raise EnvelopeError(
            f"{label} failed schema validation:\n - "
            + "\n - ".join(errors)
        )


def _parse_utc(
    value: Any,
    label: str,
) -> tuple[str, dt.datetime]:
    text = _require_text(value, label)
    parse_value = (
        text[:-1] + "+00:00"
        if text.endswith("Z")
        else text
    )

    try:
        timestamp = dt.datetime.fromisoformat(
            parse_value
        )

    except ValueError as exc:
        raise EnvelopeError(
            f"{label} must be an ISO-8601 date-time"
        ) from exc

    if timestamp.tzinfo is None:
        raise EnvelopeError(
            f"{label} must include a timezone"
        )

    normalized_dt = timestamp.astimezone(
        dt.timezone.utc
    ).replace(microsecond=0)
    normalized_text = (
        normalized_dt.isoformat(
            timespec="seconds"
        )
        .replace("+00:00", "Z")
    )

    return normalized_text, normalized_dt


def _git_head(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

    except Exception as exc:
        raise EnvelopeError(
            f"could not read checked-out git HEAD: {exc}"
        ) from exc

    head = completed.stdout.strip().lower()

    if not GIT_SHA_RE.fullmatch(head):
        raise EnvelopeError(
            "checked-out git HEAD is not a concrete "
            "40-hex SHA"
        )

    return head


def _remove_generated_paths(
    paths: list[Path],
) -> None:
    for path in paths:
        if not path.exists() and not path.is_symlink():
            continue

        if path.is_dir() and not path.is_symlink():
            raise EnvelopeError(
                f"generated output path is a directory: "
                f"{path}"
            )

        path.unlink()


def _clear_temporary_outputs(
    external_dir: Path,
) -> None:
    if not external_dir.exists():
        return

    if external_dir.is_symlink():
        raise EnvelopeError(
            "external evidence directory must not "
            "be a symlink"
        )

    patterns = (
        ".llamaguard_summary.bundle.*.tmp",
        ".llamaguard_summary.envelope.*.tmp",
    )

    for pattern in patterns:
        for path in external_dir.glob(pattern):
            if path.is_dir() and not path.is_symlink():
                raise EnvelopeError(
                    "temporary attestation output is "
                    f"a directory: {path}"
                )

            path.unlink()


def _write_bytes_atomic(
    path: Path,
    payload: bytes,
    prefix: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    descriptor, temp_name = tempfile.mkstemp(
        prefix=prefix,
        suffix=".tmp",
        dir=str(path.parent),
    )
    temp_path = Path(temp_name)

    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temp_path, path)

    except Exception:
        if temp_path.exists():
            temp_path.unlink()

        raise


def _write_json_atomic(
    path: Path,
    payload: dict[str, Any],
) -> None:
    encoded = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")

    _write_bytes_atomic(
        path,
        encoded,
        ".llamaguard_summary.envelope.",
    )


def _persist_bundle(
    source: Path,
    destination: Path,
) -> tuple[dict[str, Any], str]:
    _require_regular_file(
        source,
        "actions/attest bundle output",
    )

    if source.resolve() == destination.resolve():
        raise EnvelopeError(
            "actions/attest bundle source must differ "
            "from the canonical persisted bundle path"
        )

    source_bytes = source.read_bytes()

    if not source_bytes:
        raise EnvelopeError(
            "actions/attest bundle output must not be empty"
        )

    try:
        bundle = json.loads(
            source_bytes.decode("utf-8"),
            object_pairs_hook=_json_object,
            parse_constant=_reject_nonfinite,
        )

    except EnvelopeError:
        raise

    except Exception as exc:
        raise EnvelopeError(
            "actions/attest bundle output is not valid "
            f"UTF-8 JSON: {exc}"
        ) from exc

    if not isinstance(bundle, dict) or not bundle:
        raise EnvelopeError(
            "actions/attest bundle output must be a "
            "non-empty JSON object"
        )

    _require_finite_json_tree(
        bundle,
        "actions/attest bundle output",
    )

    _write_bytes_atomic(
        destination,
        source_bytes,
        ".llamaguard_summary.bundle.",
    )

    if destination.read_bytes() != source_bytes:
        raise EnvelopeError(
            "persisted attestation bundle bytes do not "
            "match the actions/attest output"
        )

    return bundle, _sha256_file(destination)


def _validate_repository(value: Any) -> str:
    repository = _require_text(
        value,
        "repository",
    )

    if repository != EXPECTED_REPOSITORY:
        raise EnvelopeError(
            "repository must match the canonical "
            f"repository {EXPECTED_REPOSITORY!r}"
        )

    return repository


def _validate_source_digest(value: Any) -> str:
    source_digest = _require_text(
        value,
        "source_digest",
    ).lower()

    if not GIT_SHA_RE.fullmatch(source_digest):
        raise EnvelopeError(
            "source_digest must be a concrete "
            "40-hex git SHA"
        )

    return source_digest


def _validate_signer_identity(value: Any) -> str:
    identity = _require_text(
        value,
        "signer_identity",
    )

    if identity != EXPECTED_SIGNER_IDENTITY:
        raise EnvelopeError(
            "signer_identity must match the exact "
            "PULSE CI workflow identity"
        )

    if any(
        token in identity
        for token in ("*", "?", "[", "]")
    ):
        raise EnvelopeError(
            "signer_identity must not contain wildcards"
        )

    return identity


def _validate_workflow_ref(
    value: Any,
    repository: str,
) -> str:
    workflow_ref = _require_text(
        value,
        "workflow_ref",
    )
    expected_prefix = (
        f"{repository}/{WORKFLOW_REL}@"
    )

    if not workflow_ref.startswith(expected_prefix):
        raise EnvelopeError(
            "workflow_ref must identify the exact "
            f"{WORKFLOW_REL} workflow"
        )

    source_ref = workflow_ref[
        len(expected_prefix):
    ]

    if (
        not source_ref
        or "\n" in source_ref
        or "\r" in source_ref
    ):
        raise EnvelopeError(
            "workflow_ref must include a concrete "
            "source ref"
        )

    return workflow_ref


def _validate_attestation_metadata(
    *,
    repository: str,
    attestation_id: Any,
    attestation_url: Any,
    action_ref: Any,
) -> tuple[str, str, str]:
    identifier = _require_text(
        attestation_id,
        "attestation_id",
    )

    if not ATTESTATION_ID_RE.fullmatch(identifier):
        raise EnvelopeError(
            "attestation_id must be a positive "
            "decimal GitHub attestation ID"
        )

    url = _require_text(
        attestation_url,
        "attestation_url",
    )
    expected_url = (
        f"https://github.com/{repository}/"
        f"attestations/{identifier}"
    )

    if url != expected_url:
        raise EnvelopeError(
            "attestation_url must match the canonical "
            "repository and attestation ID"
        )

    pinned_action = _require_text(
        action_ref,
        "attestation_action_ref",
    ).lower()

    if not ACTION_REF_RE.fullmatch(pinned_action):
        raise EnvelopeError(
            "attestation_action_ref must use "
            "'actions/attest@<40-hex-commit>' form"
        )

    return identifier, url, pinned_action


def _validate_summary(
    *,
    repo_root: Path,
    summary: dict[str, Any],
    source_digest: str,
    repository: str,
    signer_identity: str,
    verified_at: dt.datetime,
    raw_path: Path,
    dataset_path: Path,
    evaluator_manifest_path: Path,
) -> dict[str, Any]:
    if (
        summary.get("schema_version")
        != SUMMARY_SCHEMA_VERSION
    ):
        raise EnvelopeError(
            "summary.schema_version must be "
            f"{SUMMARY_SCHEMA_VERSION!r}"
        )

    summary_id = _require_text(
        summary.get("summary_id"),
        "summary.summary_id",
    )
    tool = _require_object(
        summary,
        "tool",
        "summary",
    )
    run = _require_object(
        summary,
        "run",
        "summary",
    )
    subject = _require_object(
        summary,
        "subject",
        "summary",
    )
    threshold_ref = _require_object(
        summary,
        "threshold_ref",
        "summary",
    )
    evidence = _require_object(
        summary,
        "evidence",
        "summary",
    )
    signing = _require_object(
        summary,
        "signing",
        "summary",
    )
    result = _require_object(
        summary,
        "result",
        "summary",
    )
    extensions = _require_object(
        summary,
        "extensions",
        "summary",
    )

    if tool.get("name") != EXPECTED_TOOL_NAME:
        raise EnvelopeError(
            "summary.tool.name must be 'llamaguard'"
        )

    generated_at_text, generated_at = _parse_utc(
        run.get("generated_at"),
        "summary.run.generated_at",
    )

    if generated_at > verified_at:
        raise EnvelopeError(
            "summary.run.generated_at must not be "
            "later than verified_at"
        )

    dataset_sha256 = _sha256_file(dataset_path)

    if (
        run.get("dataset_digest")
        != dataset_sha256
    ):
        raise EnvelopeError(
            "summary.run.dataset_digest does not "
            "match the canonical case set"
        )

    expected_subject_digest = _sha256_bytes(
        source_digest.encode("utf-8")
    )

    if (
        subject.get("kind")
        != "release_candidate"
        or subject.get("digest_algorithm")
        != "sha256"
        or subject.get("digest")
        != expected_subject_digest
    ):
        raise EnvelopeError(
            "summary subject is not bound to the "
            "current source commit"
        )

    raw_relative = _repo_relative(
        repo_root,
        raw_path,
    )
    raw_sha256 = _sha256_file(raw_path)

    if (
        evidence.get("raw_artifact_uri")
        != raw_relative
        or evidence.get("raw_artifact_digest")
        != raw_sha256
    ):
        raise EnvelopeError(
            "summary raw-evidence binding mismatch"
        )

    if (
        signing.get("mode")
        != EXPECTED_SIGNING_MODE
        or signing.get("identity")
        != signer_identity
    ):
        raise EnvelopeError(
            "summary signing mode or exact identity "
            "does not match the attestation path"
        )

    if (
        result.get("passed") is not True
        or result.get("release_contribution")
        != "required"
    ):
        raise EnvelopeError(
            "summary must be passing and declare "
            "required release contribution"
        )

    if (
        threshold_ref.get("key")
        != EXPECTED_THRESHOLD_KEY
        or threshold_ref.get("uri")
        != THRESHOLD_POLICY_REL
    ):
        raise EnvelopeError(
            "summary threshold binding mismatch"
        )

    if (
        extensions.get("repository")
        != repository
        or extensions.get("source_commit")
        != source_digest
        or extensions.get("dataset_path")
        != _repo_relative(
            repo_root,
            dataset_path,
        )
        or extensions.get("evaluator_source")
        != _repo_relative(
            repo_root,
            evaluator_manifest_path,
        )
    ):
        raise EnvelopeError(
            "summary repository, source, dataset, or "
            "evaluator binding mismatch"
        )

    metrics = summary.get("metrics")

    if not isinstance(metrics, list):
        raise EnvelopeError(
            "summary.metrics must be an array"
        )

    matching_metrics = [
        metric
        for metric in metrics
        if (
            isinstance(metric, dict)
            and metric.get("key")
            == "llamaguard_violation_rate"
        )
    ]

    if (
        len(matching_metrics) != 1
        or matching_metrics[0].get("passed")
        is not True
    ):
        raise EnvelopeError(
            "summary must contain exactly one passing "
            "llamaguard_violation_rate metric"
        )

    return {
        "summary_id": summary_id,
        "generated_at": generated_at_text,
        "dataset_sha256": dataset_sha256,
        "raw_sha256": raw_sha256,
        "evaluator_manifest_sha256": (
            _sha256_file(evaluator_manifest_path)
        ),
        "subject_sha256": expected_subject_digest,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Persist the actions/attest Sigstore bundle "
            "and build the canonical LlamaGuard "
            "external-summary envelope."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=".",
    )
    parser.add_argument(
        "--summary",
        default=SUMMARY_REL,
    )
    parser.add_argument(
        "--raw-evidence",
        default=RAW_REL,
    )
    parser.add_argument(
        "--dataset",
        default=DATASET_REL,
    )
    parser.add_argument(
        "--evaluator-manifest",
        default=EVALUATOR_MANIFEST_REL,
    )
    parser.add_argument(
        "--bundle-source",
        required=True,
    )
    parser.add_argument(
        "--bundle-out",
        default=BUNDLE_REL,
    )
    parser.add_argument(
        "--out",
        default=ENVELOPE_REL,
    )
    parser.add_argument(
        "--summary-schema",
        default=SUMMARY_SCHEMA_REL,
    )
    parser.add_argument(
        "--envelope-schema",
        default=ENVELOPE_SCHEMA_REL,
    )
    parser.add_argument(
        "--signer-policy",
        default=SIGNER_POLICY_REL,
    )
    parser.add_argument(
        "--threshold-policy",
        default=THRESHOLD_POLICY_REL,
    )
    parser.add_argument(
        "--verifier",
        default=VERIFIER_REL,
    )
    parser.add_argument(
        "--workflow",
        default=WORKFLOW_REL,
    )
    parser.add_argument(
        "--repository",
        default=os.getenv("GITHUB_REPOSITORY"),
    )
    parser.add_argument(
        "--source-digest",
        default=os.getenv("GITHUB_SHA"),
    )
    parser.add_argument(
        "--workflow-ref",
        default=os.getenv("GITHUB_WORKFLOW_REF"),
    )
    parser.add_argument(
        "--signer-identity",
        default=os.getenv(
            "PULSE_EXTERNAL_SIGNER_IDENTITY"
        ),
    )
    parser.add_argument(
        "--verified-at",
        default=os.getenv(
            "PULSE_ATTESTATION_VERIFIED_AT"
        ),
    )
    parser.add_argument(
        "--attestation-id",
        required=True,
    )
    parser.add_argument(
        "--attestation-url",
        required=True,
    )
    parser.add_argument(
        "--attestation-action-ref",
        required=True,
    )

    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    repo_root: Path | None = None
    generated_paths: list[Path] = []

    try:
        repo_root = Path(
            args.repo_root
        ).resolve()

        if not repo_root.is_dir():
            raise EnvelopeError(
                f"repository root is not a directory: "
                f"{repo_root}"
            )

        summary_path = _require_canonical_path(
            repo_root,
            Path(args.summary),
            SUMMARY_REL,
            "canonical LlamaGuard summary",
        )
        raw_path = _require_canonical_path(
            repo_root,
            Path(args.raw_evidence),
            RAW_REL,
            "canonical LlamaGuard raw evidence",
        )
        dataset_path = _require_canonical_path(
            repo_root,
            Path(args.dataset),
            DATASET_REL,
            "canonical LlamaGuard case set",
        )
        evaluator_manifest_path = (
            _require_canonical_path(
                repo_root,
                Path(args.evaluator_manifest),
                EVALUATOR_MANIFEST_REL,
                "canonical evaluator manifest",
            )
        )
        bundle_path = _require_canonical_path(
            repo_root,
            Path(args.bundle_out),
            BUNDLE_REL,
            "canonical attestation bundle",
        )
        envelope_path = _require_canonical_path(
            repo_root,
            Path(args.out),
            ENVELOPE_REL,
            "canonical external-summary envelope",
        )
        report_path = _require_canonical_path(
            repo_root,
            Path(VERIFIER_REPORT_REL),
            VERIFIER_REPORT_REL,
            "canonical attestation verifier report",
        )
        summary_schema_path = (
            _require_canonical_path(
                repo_root,
                Path(args.summary_schema),
                SUMMARY_SCHEMA_REL,
                "canonical external-summary schema",
            )
        )
        envelope_schema_path = (
            _require_canonical_path(
                repo_root,
                Path(args.envelope_schema),
                ENVELOPE_SCHEMA_REL,
                "canonical envelope schema",
            )
        )
        signer_policy_path = (
            _require_canonical_path(
                repo_root,
                Path(args.signer_policy),
                SIGNER_POLICY_REL,
                "canonical signer policy",
            )
        )
        threshold_policy_path = (
            _require_canonical_path(
                repo_root,
                Path(args.threshold_policy),
                THRESHOLD_POLICY_REL,
                "canonical threshold policy",
            )
        )
        verifier_path = _require_canonical_path(
            repo_root,
            Path(args.verifier),
            VERIFIER_REL,
            "canonical replay verifier",
        )
        workflow_path = _require_canonical_path(
            repo_root,
            Path(args.workflow),
            WORKFLOW_REL,
            "exact PULSE CI workflow",
        )
        tool_path = _require_canonical_path(
            repo_root,
            Path(TOOL_REL),
            TOOL_REL,
            "envelope builder",
        )

        repository_paths = (
            summary_path,
            raw_path,
            dataset_path,
            evaluator_manifest_path,
            bundle_path,
            envelope_path,
            report_path,
            summary_schema_path,
            envelope_schema_path,
            signer_policy_path,
            threshold_policy_path,
            verifier_path,
            workflow_path,
            tool_path,
        )

        for path in repository_paths:
            _reject_symlink_components(
                repo_root,
                path,
                "attestation-envelope path",
            )

        external_dir = bundle_path.parent
        generated_paths = [
            bundle_path,
            envelope_path,
            report_path,
        ]

        _remove_generated_paths(generated_paths)
        _clear_temporary_outputs(external_dir)

        for path, label in (
            (summary_path, "canonical LlamaGuard summary"),
            (raw_path, "canonical LlamaGuard raw evidence"),
            (dataset_path, "canonical LlamaGuard case set"),
            (
                evaluator_manifest_path,
                "canonical evaluator manifest",
            ),
            (
                summary_schema_path,
                "canonical external-summary schema",
            ),
            (
                envelope_schema_path,
                "canonical envelope schema",
            ),
            (signer_policy_path, "canonical signer policy"),
            (
                threshold_policy_path,
                "canonical threshold policy",
            ),
            (verifier_path, "canonical replay verifier"),
            (workflow_path, "exact PULSE CI workflow"),
            (tool_path, "envelope builder"),
        ):
            _require_regular_file(path, label)

        actual_tool_path = Path(__file__).resolve()

        if actual_tool_path != tool_path.resolve():
            raise EnvelopeError(
                "envelope builder must execute from "
                f"the canonical path {tool_path}"
            )

        repository = _validate_repository(
            args.repository
        )
        source_digest = _validate_source_digest(
            args.source_digest
        )
        checked_out_head = _git_head(repo_root)

        if checked_out_head != source_digest:
            raise EnvelopeError(
                "source_digest does not match checked-out "
                f"HEAD: {source_digest} != {checked_out_head}"
            )

        signer_identity = _validate_signer_identity(
            args.signer_identity
        )
        workflow_ref = _validate_workflow_ref(
            args.workflow_ref,
            repository,
        )
        verified_at_text, verified_at = _parse_utc(
            args.verified_at,
            "verified_at",
        )
        (
            attestation_id,
            attestation_url,
            attestation_action_ref,
        ) = _validate_attestation_metadata(
            repository=repository,
            attestation_id=args.attestation_id,
            attestation_url=args.attestation_url,
            action_ref=args.attestation_action_ref,
        )

        summary_schema = _load_checked_schema(
            summary_schema_path,
            "external-summary schema",
        )
        envelope_schema = _load_checked_schema(
            envelope_schema_path,
            "external-summary envelope schema",
        )
        summary = _load_json_object(
            summary_path,
            "canonical LlamaGuard summary",
        )
        _validate_schema(
            summary,
            summary_schema,
            "canonical LlamaGuard summary",
        )
        summary_binding = _validate_summary(
            repo_root=repo_root,
            summary=summary,
            source_digest=source_digest,
            repository=repository,
            signer_identity=signer_identity,
            verified_at=verified_at,
            raw_path=raw_path,
            dataset_path=dataset_path,
            evaluator_manifest_path=(
                evaluator_manifest_path
            ),
        )

        bundle_source = Path(
            args.bundle_source
        ).resolve()
        _, bundle_sha256 = _persist_bundle(
            bundle_source,
            bundle_path,
        )

        summary_sha256 = _sha256_file(
            summary_path
        )
        tool_sha256 = _sha256_file(tool_path)
        signer_policy_sha256 = _sha256_file(
            signer_policy_path
        )
        threshold_policy_sha256 = _sha256_file(
            threshold_policy_path
        )
        verifier_sha256 = _sha256_file(
            verifier_path
        )
        workflow_sha256 = _sha256_file(
            workflow_path
        )

        envelope_id = (
            "pulse_external_llamaguard_attestation_"
            f"{source_digest[:12]}_"
            f"{summary_sha256[:12]}"
        )

        envelope: dict[str, Any] = {
            "schema_version": (
                ENVELOPE_SCHEMA_VERSION
            ),
            "envelope_id": envelope_id,
            "summary_ref": {
                "uri": _repo_relative(
                    repo_root,
                    summary_path,
                ),
                "schema_version": (
                    SUMMARY_SCHEMA_VERSION
                ),
                "summary_id": (
                    summary_binding["summary_id"]
                ),
            },
            "summary_digest": {
                "algorithm": "sha256",
                "value": summary_sha256,
            },
            "signing": {
                "mode": EXPECTED_SIGNING_MODE,
                "identity": signer_identity,
                "issuer": GITHUB_OIDC_ISSUER,
                "bundle_uri": _repo_relative(
                    repo_root,
                    bundle_path,
                ),
            },
            "verification": {
                "verified": True,
                "verified_at": verified_at_text,
                "verifier": {
                    "name": "actions/attest",
                    "version": (
                        attestation_action_ref
                    ),
                },
                "result_reason": (
                    "The pinned GitHub attestation "
                    "action returned an attestation ID, "
                    "canonical URL, and Sigstore bundle "
                    "for the exact summary. Independent "
                    "cryptographic replay by "
                    "check_external_summary_attestation_"
                    "v1.py remains required before "
                    "recorded-release admission."
                ),
            },
            "policy_context": {
                "signer_policy_ref": (
                    SIGNER_POLICY_REL
                ),
                "threshold_policy_ref": (
                    THRESHOLD_POLICY_REL
                ),
                "release_contribution": "required",
                "fold_in_allowed": True,
            },
            "authority_boundary": (
                AUTHORITY_BOUNDARY
            ),
            "extensions": {
                "repository": repository,
                "source_commit": source_digest,
                "workflow_path": WORKFLOW_REL,
                "workflow_ref": workflow_ref,
                "signer_workflow": (
                    f"github.com/{repository}/"
                    f"{WORKFLOW_REL}"
                ),
                "predicate_type": (
                    SLSA_PROVENANCE_V1
                ),
                "oidc_issuer": (
                    GITHUB_OIDC_ISSUER
                ),
                "attestation_id": attestation_id,
                "attestation_url": attestation_url,
                "bundle_sha256": bundle_sha256,
                "summary_sha256": summary_sha256,
                "raw_evidence_sha256": (
                    summary_binding["raw_sha256"]
                ),
                "dataset_sha256": (
                    summary_binding[
                        "dataset_sha256"
                    ]
                ),
                "evaluator_manifest_sha256": (
                    summary_binding[
                        "evaluator_manifest_sha256"
                    ]
                ),
                "subject_sha256": (
                    summary_binding["subject_sha256"]
                ),
                "signer_policy_sha256": (
                    signer_policy_sha256
                ),
                "threshold_policy_sha256": (
                    threshold_policy_sha256
                ),
                "workflow_sha256": (
                    workflow_sha256
                ),
                "envelope_builder": {
                    "id": BUILDER_ID,
                    "version": BUILDER_VERSION,
                    "path": TOOL_REL,
                    "sha256": tool_sha256,
                },
                "canonical_replay_verifier": {
                    "path": VERIFIER_REL,
                    "sha256": verifier_sha256,
                    "required": True,
                },
                "producer_boundary": {
                    "creates_release_authority": False,
                    "materializes_status": False,
                    "materializes_release_required": False,
                    "replaces_check_gates": False,
                },
            },
        }

        _validate_schema(
            envelope,
            envelope_schema,
            "generated external-summary envelope",
        )
        _write_json_atomic(
            envelope_path,
            envelope,
        )

        persisted = _load_json_object(
            envelope_path,
            "persisted external-summary envelope",
        )
        _validate_schema(
            persisted,
            envelope_schema,
            "persisted external-summary envelope",
        )

        if persisted != envelope:
            raise EnvelopeError(
                "persisted envelope does not match "
                "the validated in-memory envelope"
            )

    except EnvelopeError as exc:
        if generated_paths:
            try:
                _remove_generated_paths(
                    generated_paths
                )

            except Exception:
                pass

        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 1

    except Exception as exc:  # noqa: BLE001
        if generated_paths:
            try:
                _remove_generated_paths(
                    generated_paths
                )

            except Exception:
                pass

        print(
            "ERROR: unexpected attestation-envelope "
            f"failure: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        "OK: canonical LlamaGuard Sigstore bundle "
        f"written to {bundle_path}"
    )
    print(
        "OK: canonical LlamaGuard external-summary "
        f"envelope written to {envelope_path}"
    )
    print(
        "Envelope binding: "
        f"summary_sha256={summary_sha256} "
        f"bundle_sha256={bundle_sha256} "
        f"source_commit={source_digest}"
    )
    print(
        "Authority boundary: verified envelope "
        "eligibility does not authorize release"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
