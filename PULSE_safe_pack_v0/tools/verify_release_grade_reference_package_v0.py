#!/usr/bin/env python3
"""Verify a complete release-grade reference package.

The verifier is read-only and non-authorizing. It checks package structure,
digest inventory replay, required evidence presence, run identity consistency,
and core evidence-chain bindings.

It does not:
- produce or modify evidence;
- build recorded candidates;
- verify recorded evidence as an authority source;
- materialize gates;
- call check_gates.py;
- authorize release.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any


REPORT_SCHEMA_VERSION = "release_grade_reference_package_verification_v0"
TOOL_VERSION = "0.1.0"

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
RUN_KEY_RE = re.compile(
    r"^GITHUB_RUN_ID=([1-9][0-9]*)\|"
    r"GITHUB_RUN_ATTEMPT=([1-9][0-9]*)\|"
    r"GITHUB_WORKFLOW=.+$"
)

AUTHORITY_BOUNDARY = {
    "read_only": True,
    "creates_release_authority": False,
    "authorizes_release": False,
    "blocks_release": False,
    "materializes_status": False,
    "materializes_release_required": False,
    "verifies_recorded_release_evidence_as_authority": False,
    "replaces_check_gates": False,
    "package_acceptance_only": True,
}

REQUIRED_FILES: tuple[str, ...] = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/external/llamaguard_raw.jsonl",
    "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    "artifacts/external/llamaguard_summary.json",
    "artifacts/external/llamaguard_summary.bundle.json",
    "artifacts/external/llamaguard_summary.envelope.json",
    "artifacts/external/llamaguard_attestation_verifier_v1.json",
    "artifacts/status.json",
    "artifacts/release_decision_v0.json",
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/release_authority_v0.json",
    "artifacts/report_card.html",
)

REQUIRED_DIRS: tuple[str, ...] = (
    "artifacts/recorded_release_candidates",
    "release-authority-audit-bundle",
)

JSON_FILES: tuple[str, ...] = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    "artifacts/external/llamaguard_summary.json",
    "artifacts/external/llamaguard_summary.bundle.json",
    "artifacts/external/llamaguard_summary.envelope.json",
    "artifacts/external/llamaguard_attestation_verifier_v1.json",
    "artifacts/status.json",
    "artifacts/release_decision_v0.json",
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/release_authority_v0.json",
)

EXTERNAL_PATHS = {
    "raw": "artifacts/external/llamaguard_raw.jsonl",
    "evaluator_manifest": "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    "summary": "artifacts/external/llamaguard_summary.json",
    "bundle": "artifacts/external/llamaguard_summary.bundle.json",
    "envelope": "artifacts/external/llamaguard_summary.envelope.json",
    "attestation_report": "artifacts/external/llamaguard_attestation_verifier_v1.json",
}


class VerificationError(ValueError):
    """Strict package verification error."""


class StrictJsonError(VerificationError):
    """Strict JSON parsing error."""


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key {key!r}")

        result[key] = value

    return result


def _bad_constant(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON constant {value!r}")


def _finite_tree(value: Any, label: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise VerificationError(f"{label} contains a non-finite number")
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite_tree(item, f"{label}[{index}]")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            _finite_tree(item, f"{label}.{key}")
        return

    raise VerificationError(f"{label} contains unsupported JSON value")


def _load_json(path: Path, label: str) -> Any:
    _require_file(path, label)

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_pairs,
            parse_constant=_bad_constant,
        )

    except VerificationError:
        raise

    except Exception as exc:
        raise VerificationError(f"{label} is not valid JSON: {exc}") from exc

    _finite_tree(payload, label)
    return payload


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    payload = _load_json(path, label)

    if not isinstance(payload, dict):
        raise VerificationError(f"{label} must be a JSON object")

    return payload


def _resolve(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(str(path))))


def _require_package_dir(path: Path) -> Path:
    resolved = _resolve(path)

    if resolved.is_symlink() or not resolved.is_dir():
        raise VerificationError(
            f"package_dir must be a non-symlink directory: {resolved}"
        )

    return resolved


def _package_path(package_dir: Path, relative: str) -> Path:
    path = _resolve(package_dir / relative)

    try:
        path.relative_to(package_dir)

    except ValueError as exc:
        raise VerificationError(f"package path escapes root: {relative}") from exc

    return path


def _require_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise VerificationError(
            f"{label} must be a regular non-symlink file: {path}"
        )


def _require_dir(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_dir():
        raise VerificationError(
            f"{label} must be a non-symlink directory: {path}"
        )


def _sha256(path: Path) -> str:
    _require_file(path, f"SHA-256 input {path}")
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _iter_files(package_dir: Path) -> list[Path]:
    files: list[Path] = []

    for path in package_dir.rglob("*"):
        if path.is_symlink():
            raise VerificationError(f"package must not contain symlinks: {path}")

        if path.is_file():
            files.append(path)

    return sorted(files, key=lambda item: item.relative_to(package_dir).as_posix())


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    _require_file(path, label)
    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8", errors="strict") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue

            try:
                record = json.loads(
                    raw,
                    object_pairs_hook=_json_pairs,
                    parse_constant=_bad_constant,
                )

            except VerificationError:
                raise

            except Exception as exc:
                raise VerificationError(
                    f"{label} line {line_number} is not valid JSON: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise VerificationError(
                    f"{label} line {line_number} must be a JSON object"
                )

            _finite_tree(record, f"{label} line {line_number}")
            records.append(record)

    if not records:
        raise VerificationError(f"{label} must contain at least one JSONL record")

    return records


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _now_utc() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _check(
    checks: list[dict[str, Any]],
    errors: list[str],
    check_id: str,
    condition: bool,
    details: str,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "passed": bool(condition),
            "details": details,
        }
    )

    if not condition:
        errors.append(f"{check_id}: {details}")


def _deep_get(value: Any, path: tuple[str, ...]) -> Any:
    current = value

    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)

    return current


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return None


def _expected_identity(
    *,
    repository: str,
    git_sha: str,
    workflow_ref: str,
    run_id: str,
    run_attempt: str,
    run_key: str,
) -> dict[str, str]:
    repository = repository.strip()
    git_sha = git_sha.strip().lower()
    workflow_ref = workflow_ref.strip()
    run_id = run_id.strip()
    run_attempt = run_attempt.strip()
    run_key = run_key.strip()

    if repository.count("/") != 1:
        raise VerificationError("repository must use owner/name form")

    if not GIT_SHA_RE.fullmatch(git_sha):
        raise VerificationError("git_sha must be a concrete 40-hex SHA")

    if f"{repository}/.github/workflows/" not in workflow_ref or "@" not in workflow_ref:
        raise VerificationError(
            "workflow_ref must identify the exact repository workflow and ref"
        )

    if not run_id.isdecimal() or int(run_id) < 1:
        raise VerificationError("run_id must be a positive decimal string")

    if not run_attempt.isdecimal() or int(run_attempt) < 1:
        raise VerificationError("run_attempt must be a positive decimal string")

    match = RUN_KEY_RE.fullmatch(run_key)
    if not match:
        raise VerificationError("run_key must use canonical GitHub run identity form")

    if match.group(1) != run_id or match.group(2) != run_attempt:
        raise VerificationError("run_key run ID/attempt must match CLI identity")

    return {
        "repository": repository,
        "git_sha": git_sha,
        "workflow_ref": workflow_ref,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "run_key": run_key,
    }


def _verify_required_surface(
    *,
    package_dir: Path,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    for relative in REQUIRED_FILES:
        path = _package_path(package_dir, relative)
        ok = path.is_file() and not path.is_symlink()
        _check(
            checks,
            errors,
            f"required_file:{relative}",
            ok,
            f"required regular file {relative}",
        )

    for relative in REQUIRED_DIRS:
        path = _package_path(package_dir, relative)
        ok = path.is_dir() and not path.is_symlink() and any(
            item.is_file() for item in path.rglob("*")
        )
        _check(
            checks,
            errors,
            f"required_dir:{relative}",
            ok,
            f"required non-empty non-symlink directory {relative}",
        )


def _verify_digest_inventory(
    *,
    package_dir: Path,
    inventory: dict[str, Any],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    _check(
        checks,
        errors,
        "digest_inventory.schema",
        inventory.get("schema_version")
        == "release_grade_reference_package_digest_inventory_v0",
        "digest inventory schema_version is release_grade_reference_package_digest_inventory_v0",
    )
    _check(
        checks,
        errors,
        "digest_inventory.algorithm",
        inventory.get("algorithm") == "sha256",
        "digest inventory algorithm is sha256",
    )

    files = inventory.get("files")
    if not isinstance(files, list) or not files:
        _check(
            checks,
            errors,
            "digest_inventory.files",
            False,
            "digest inventory files must be a non-empty array",
        )
        return

    seen: dict[str, dict[str, Any]] = {}
    duplicate = False

    for index, item in enumerate(files):
        if not isinstance(item, dict):
            _check(
                checks,
                errors,
                f"digest_inventory.files[{index}]",
                False,
                "digest inventory entry must be an object",
            )
            continue

        relative = item.get("path")
        digest = item.get("sha256")
        size = item.get("size_bytes")

        if not isinstance(relative, str) or not relative or relative.startswith("/"):
            _check(
                checks,
                errors,
                f"digest_inventory.path[{index}]",
                False,
                "digest inventory path must be relative",
            )
            continue

        if relative in seen:
            duplicate = True

        seen[relative] = item

        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            _check(
                checks,
                errors,
                f"digest_inventory.sha256[{relative}]",
                False,
                f"{relative} has invalid sha256",
            )
            continue

        if not isinstance(size, int) or size < 0:
            _check(
                checks,
                errors,
                f"digest_inventory.size[{relative}]",
                False,
                f"{relative} has invalid size",
            )
            continue

        path = _package_path(package_dir, relative)
        if not path.is_file() or path.is_symlink():
            _check(
                checks,
                errors,
                f"digest_inventory.file_present:{relative}",
                False,
                f"{relative} listed in inventory is missing or symlinked",
            )
            continue

        actual_digest = _sha256(path)
        actual_size = path.stat().st_size
        _check(
            checks,
            errors,
            f"digest_inventory.digest:{relative}",
            actual_digest == digest.lower(),
            f"{relative} digest matches inventory",
        )
        _check(
            checks,
            errors,
            f"digest_inventory.size_bytes:{relative}",
            actual_size == size,
            f"{relative} size matches inventory",
        )

    _check(
        checks,
        errors,
        "digest_inventory.unique_paths",
        not duplicate,
        "digest inventory has unique paths",
    )

    actual_files = {
        path.relative_to(package_dir).as_posix()
        for path in _iter_files(package_dir)
        if path.relative_to(package_dir).as_posix()
        != "package_digest_inventory_v0.json"
    }
    listed_files = set(seen)

    _check(
        checks,
        errors,
        "digest_inventory.file_count",
        inventory.get("file_count") == len(files),
        "digest inventory file_count equals listed file count",
    )
    _check(
        checks,
        errors,
        "digest_inventory.no_missing_files",
        actual_files == listed_files,
        "digest inventory exactly covers package files except itself",
    )


def _verify_metadata(
    *,
    metadata: dict[str, Any],
    expected: dict[str, str],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    expected_run_id = int(expected["run_id"])
    expected_run_attempt = int(expected["run_attempt"])

    comparisons = {
        "repository": expected["repository"],
        "git_sha": expected["git_sha"],
        "workflow_ref": expected["workflow_ref"],
        "run_key": expected["run_key"],
    }

    for key, expected_value in comparisons.items():
        actual = metadata.get(key)
        if key == "git_sha" and isinstance(actual, str):
            actual = actual.lower()

        _check(
            checks,
            errors,
            f"metadata.{key}",
            actual == expected_value,
            f"run metadata {key} matches expected identity",
        )

    _check(
        checks,
        errors,
        "metadata.run_id",
        metadata.get("run_id") == expected_run_id,
        "run metadata run_id matches expected identity",
    )
    _check(
        checks,
        errors,
        "metadata.run_attempt",
        metadata.get("run_attempt") == expected_run_attempt,
        "run metadata run_attempt matches expected identity",
    )
    _check(
        checks,
        errors,
        "metadata.authority_boundary",
        isinstance(metadata.get("authority_boundary"), dict)
        and metadata["authority_boundary"].get("authorizes_release") is False
        and metadata["authority_boundary"].get("package_only") is True,
        "run metadata authority boundary is non-authorizing package-only",
    )


def _verify_json_well_formed(
    *,
    package_dir: Path,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}

    for relative in JSON_FILES:
        path = _package_path(package_dir, relative)
        try:
            payload = _load_json_object(path, relative)
            loaded[relative] = payload
            ok = True
            details = f"{relative} is strict JSON object"
        except VerificationError as exc:
            ok = False
            details = str(exc)

        _check(checks, errors, f"json:{relative}", ok, details)

    return loaded


def _check_identity_value(
    *,
    checks: list[dict[str, Any]],
    errors: list[str],
    check_id: str,
    actual: Any,
    expected: str,
    details: str,
    lower: bool = False,
) -> None:
    text = _as_text(actual)

    if text is not None and lower:
        text = text.lower()

    _check(checks, errors, check_id, text == expected, details)


def _verify_known_run_bindings(
    *,
    package_dir: Path,
    loaded: dict[str, dict[str, Any]],
    expected: dict[str, str],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    raw_records = _read_jsonl(
        _package_path(package_dir, EXTERNAL_PATHS["raw"]),
        "LlamaGuard raw evidence",
    )
    _check(
        checks,
        errors,
        "llamaguard.raw.record_count",
        len(raw_records) > 0,
        "LlamaGuard raw evidence has at least one record",
    )

    for index, record in enumerate(raw_records):
        run = record.get("run")
        if not isinstance(run, dict):
            _check(
                checks,
                errors,
                f"llamaguard.raw[{index}].run",
                False,
                "raw LlamaGuard record has run object",
            )
            continue

        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id=f"llamaguard.raw[{index}].repository",
            actual=run.get("repository"),
            expected=expected["repository"],
            details="raw LlamaGuard record repository matches package identity",
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id=f"llamaguard.raw[{index}].git_sha",
            actual=run.get("git_sha"),
            expected=expected["git_sha"],
            details="raw LlamaGuard record git_sha matches package identity",
            lower=True,
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id=f"llamaguard.raw[{index}].run_key",
            actual=run.get("run_key"),
            expected=expected["run_key"],
            details="raw LlamaGuard record run_key matches package identity",
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id=f"llamaguard.raw[{index}].workflow_ref",
            actual=run.get("workflow_ref"),
            expected=expected["workflow_ref"],
            details="raw LlamaGuard record workflow_ref matches package identity",
        )

    evaluator = loaded.get(EXTERNAL_PATHS["evaluator_manifest"], {})
    evaluator_run = evaluator.get("run")
    if isinstance(evaluator_run, dict):
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.evaluator.repository",
            actual=evaluator_run.get("repository"),
            expected=expected["repository"],
            details="evaluator manifest repository matches package identity",
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.evaluator.git_sha",
            actual=evaluator_run.get("git_sha"),
            expected=expected["git_sha"],
            details="evaluator manifest git_sha matches package identity",
            lower=True,
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.evaluator.run_key",
            actual=evaluator_run.get("run_key"),
            expected=expected["run_key"],
            details="evaluator manifest run_key matches package identity",
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.evaluator.workflow_ref",
            actual=evaluator_run.get("workflow_ref"),
            expected=expected["workflow_ref"],
            details="evaluator manifest workflow_ref matches package identity",
        )
    else:
        _check(
            checks,
            errors,
            "llamaguard.evaluator.run",
            False,
            "evaluator manifest has run object",
        )

    summary = loaded.get(EXTERNAL_PATHS["summary"], {})
    summary_extensions = summary.get("extensions")
    if isinstance(summary_extensions, dict):
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.summary.repository",
            actual=summary_extensions.get("repository"),
            expected=expected["repository"],
            details="summary repository matches package identity",
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.summary.source_commit",
            actual=summary_extensions.get("source_commit"),
            expected=expected["git_sha"],
            details="summary source_commit matches package identity",
            lower=True,
        )
    else:
        _check(
            checks,
            errors,
            "llamaguard.summary.extensions",
            False,
            "summary has extensions object",
        )

    summary_run = summary.get("run")
    if isinstance(summary_run, dict):
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.summary.run_key",
            actual=summary_run.get("run_id"),
            expected=expected["run_key"],
            details="summary run_id stores canonical run_key",
        )

    envelope = loaded.get(EXTERNAL_PATHS["envelope"], {})
    envelope_extensions = envelope.get("extensions")
    if isinstance(envelope_extensions, dict):
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.envelope.repository",
            actual=envelope_extensions.get("repository"),
            expected=expected["repository"],
            details="envelope repository matches package identity",
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.envelope.source_commit",
            actual=envelope_extensions.get("source_commit"),
            expected=expected["git_sha"],
            details="envelope source_commit matches package identity",
            lower=True,
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="llamaguard.envelope.workflow_ref",
            actual=envelope_extensions.get("workflow_ref"),
            expected=expected["workflow_ref"],
            details="envelope workflow_ref matches package identity",
        )
    else:
        _check(
            checks,
            errors,
            "llamaguard.envelope.extensions",
            False,
            "envelope has extensions object",
        )


def _verify_external_bindings(
    *,
    package_dir: Path,
    loaded: dict[str, dict[str, Any]],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    raw_path = _package_path(package_dir, EXTERNAL_PATHS["raw"])
    evaluator_path = _package_path(package_dir, EXTERNAL_PATHS["evaluator_manifest"])
    summary_path = _package_path(package_dir, EXTERNAL_PATHS["summary"])
    bundle_path = _package_path(package_dir, EXTERNAL_PATHS["bundle"])
    envelope_path = _package_path(package_dir, EXTERNAL_PATHS["envelope"])

    summary = loaded.get(EXTERNAL_PATHS["summary"], {})
    evidence = summary.get("evidence")
    if isinstance(evidence, dict):
        raw_uri = evidence.get("raw_artifact_uri")
        raw_digest = evidence.get("raw_artifact_digest")
        _check(
            checks,
            errors,
            "llamaguard.summary.raw_path",
            raw_uri in (
                "PULSE_safe_pack_v0/artifacts/external/llamaguard_raw.jsonl",
                EXTERNAL_PATHS["raw"],
            ),
            "summary raw_artifact_uri identifies LlamaGuard raw evidence",
        )
        _check(
            checks,
            errors,
            "llamaguard.summary.raw_digest",
            raw_digest == _sha256(raw_path),
            "summary raw_artifact_digest matches packaged raw evidence",
        )

    summary_extensions = summary.get("extensions")
    if isinstance(summary_extensions, dict):
        evaluator_digest = summary_extensions.get("evaluator_manifest_sha256")
        if evaluator_digest is None:
            evaluator_digest = summary_extensions.get("evaluator_sha256")
        if evaluator_digest is not None:
            _check(
                checks,
                errors,
                "llamaguard.summary.evaluator_digest",
                evaluator_digest == _sha256(evaluator_path),
                "summary evaluator digest matches packaged evaluator manifest",
            )

    envelope = loaded.get(EXTERNAL_PATHS["envelope"], {})
    summary_digest = envelope.get("summary_digest")
    if isinstance(summary_digest, dict):
        _check(
            checks,
            errors,
            "llamaguard.envelope.summary_digest",
            summary_digest.get("value") == _sha256(summary_path)
            and summary_digest.get("algorithm") == "sha256",
            "envelope summary digest matches packaged summary",
        )
    else:
        _check(
            checks,
            errors,
            "llamaguard.envelope.summary_digest",
            False,
            "envelope has summary_digest object",
        )

    signing = envelope.get("signing")
    if isinstance(signing, dict):
        bundle_uri = signing.get("bundle_uri")
        _check(
            checks,
            errors,
            "llamaguard.envelope.bundle_uri",
            bundle_uri in (
                "PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.bundle.json",
                EXTERNAL_PATHS["bundle"],
            ),
            "envelope bundle_uri identifies packaged attestation bundle",
        )
    else:
        _check(
            checks,
            errors,
            "llamaguard.envelope.signing",
            False,
            "envelope has signing object",
        )

    envelope_extensions = envelope.get("extensions")
    if isinstance(envelope_extensions, dict):
        bundle_digest = envelope_extensions.get("bundle_sha256")
        if bundle_digest is not None:
            _check(
                checks,
                errors,
                "llamaguard.envelope.bundle_sha256",
                bundle_digest == _sha256(bundle_path),
                "envelope bundle_sha256 matches packaged bundle",
            )

        raw_digest = envelope_extensions.get("raw_evidence_sha256")
        if raw_digest is not None:
            _check(
                checks,
                errors,
                "llamaguard.envelope.raw_evidence_sha256",
                raw_digest == _sha256(raw_path),
                "envelope raw_evidence_sha256 matches packaged raw evidence",
            )

    attestation = loaded.get(EXTERNAL_PATHS["attestation_report"], {})
    _check(
        checks,
        errors,
        "llamaguard.attestation_report.status",
        attestation.get("status") == "verified",
        "LlamaGuard attestation verifier report status is verified",
    )
    report_errors = attestation.get("errors")
    _check(
        checks,
        errors,
        "llamaguard.attestation_report.errors",
        isinstance(report_errors, list) and not report_errors,
        "LlamaGuard attestation verifier report has no errors",
    )

    report_summary = attestation.get("summary")
    if isinstance(report_summary, dict):
        _check(
            checks,
            errors,
            "llamaguard.attestation_report.summary_digest",
            report_summary.get("sha256") == _sha256(summary_path),
            "attestation report summary digest matches packaged summary",
        )

    report_envelope = attestation.get("envelope")
    if isinstance(report_envelope, dict):
        _check(
            checks,
            errors,
            "llamaguard.attestation_report.envelope_digest",
            report_envelope.get("sha256") == _sha256(envelope_path),
            "attestation report envelope digest matches packaged envelope",
        )


def _verify_candidate_chain(
    *,
    package_dir: Path,
    loaded: dict[str, dict[str, Any]],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    candidate_dir = _package_path(package_dir, "artifacts/recorded_release_candidates")
    candidates = [
        path
        for path in candidate_dir.rglob("*.json")
        if path.is_file() and not path.is_symlink()
    ]
    _check(
        checks,
        errors,
        "recorded_candidates.non_empty",
        bool(candidates),
        "recorded_release_candidates contains at least one JSON candidate",
    )

    for candidate in sorted(candidates, key=lambda item: item.as_posix()):
        relative = candidate.relative_to(package_dir).as_posix()
        payload = _load_json_object(candidate, relative)
        _check(
            checks,
            errors,
            f"recorded_candidate.validation:{relative}",
            isinstance(payload.get("validation"), dict)
            and payload["validation"].get("status") == "passed",
            f"{relative} has passed validation status",
        )
        _check(
            checks,
            errors,
            f"recorded_candidate.authority_boundary:{relative}",
            isinstance(payload.get("authority_boundary"), dict)
            and payload["authority_boundary"].get("creates_release_authority") is False
            and payload["authority_boundary"].get("eligible_without_verifier") is False,
            f"{relative} remains non-authorizing without verifier",
        )

    verifier = loaded.get("artifacts/recorded_release_evidence_verifier_v0.json", {})
    verifier_status = verifier.get("status") or verifier.get("decision")
    _check(
        checks,
        errors,
        "recorded_verifier.status",
        verifier_status in ("VERIFIED", "verified", "passed"),
        "recorded release evidence verifier reports a verified/passed status",
    )

    verifier_errors = verifier.get("errors")
    if verifier_errors is not None:
        _check(
            checks,
            errors,
            "recorded_verifier.errors",
            isinstance(verifier_errors, list) and not verifier_errors,
            "recorded release evidence verifier has no errors",
        )

    manifest = loaded.get("artifacts/release_evidence_input_manifest_v0.json", {})
    _check(
        checks,
        errors,
        "input_manifest.object",
        isinstance(manifest, dict) and bool(manifest),
        "release evidence input manifest is a non-empty object",
    )

    index = loaded.get("artifacts/recorded_release_candidate_index_v0.json", {})
    _check(
        checks,
        errors,
        "candidate_index.object",
        isinstance(index, dict) and bool(index),
        "recorded release candidate index is a non-empty object",
    )


def _verify_status_and_sidecars(
    *,
    loaded: dict[str, dict[str, Any]],
    expected: dict[str, str],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    status = loaded.get("artifacts/status.json", {})
    baseline = loaded.get("artifacts/status_baseline.json", {})

    status_metrics = status.get("metrics")
    baseline_metrics = baseline.get("metrics")

    if isinstance(status_metrics, dict):
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="status.git_sha",
            actual=status_metrics.get("git_sha"),
            expected=expected["git_sha"],
            details="final status metrics.git_sha matches package identity",
            lower=True,
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="status.run_key",
            actual=status_metrics.get("run_key"),
            expected=expected["run_key"],
            details="final status metrics.run_key matches package identity",
        )
    else:
        _check(
            checks,
            errors,
            "status.metrics",
            False,
            "final status has metrics object",
        )

    if isinstance(baseline_metrics, dict):
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="baseline.git_sha",
            actual=baseline_metrics.get("git_sha"),
            expected=expected["git_sha"],
            details="baseline status metrics.git_sha matches package identity",
            lower=True,
        )
        _check_identity_value(
            checks=checks,
            errors=errors,
            check_id="baseline.run_key",
            actual=baseline_metrics.get("run_key"),
            expected=expected["run_key"],
            details="baseline status metrics.run_key matches package identity",
        )
    else:
        _check(
            checks,
            errors,
            "baseline.metrics",
            False,
            "baseline status has metrics object",
        )

    release_decision = loaded.get("artifacts/release_decision_v0.json", {})
    _check(
        checks,
        errors,
        "release_decision.object",
        isinstance(release_decision, dict) and bool(release_decision),
        "release decision sidecar is present as non-empty object",
    )

    provenance = loaded.get("artifacts/artifact_provenance_binding_v0.json", {})
    _check(
        checks,
        errors,
        "artifact_provenance_binding.object",
        isinstance(provenance, dict) and bool(provenance),
        "artifact provenance binding is present as non-empty object",
    )

    authority = loaded.get("artifacts/release_authority_v0.json", {})
    _check(
        checks,
        errors,
        "release_authority_manifest.object",
        isinstance(authority, dict) and bool(authority),
        "release authority manifest is present as non-empty object",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify a complete release-grade reference package."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--git-sha", default=os.getenv("GITHUB_SHA"))
    parser.add_argument("--workflow-ref", default=os.getenv("GITHUB_WORKFLOW_REF"))
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID"))
    parser.add_argument("--run-attempt", default=os.getenv("GITHUB_RUN_ATTEMPT"))
    parser.add_argument("--run-key", default=os.getenv("PULSE_RUN_KEY"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    package_dir: Path | None = None

    try:
        repo_root = _resolve(Path(args.repo_root))
        if repo_root.is_symlink() or not repo_root.is_dir():
            raise VerificationError(f"repo-root must be a directory: {repo_root}")

        package_dir = _require_package_dir(Path(args.package_dir))
        expected = _expected_identity(
            repository=str(args.repository or ""),
            git_sha=str(args.git_sha or ""),
            workflow_ref=str(args.workflow_ref or ""),
            run_id=str(args.run_id or ""),
            run_attempt=str(args.run_attempt or ""),
            run_key=str(args.run_key or ""),
        )

        _verify_required_surface(
            package_dir=package_dir,
            checks=checks,
            errors=errors,
        )
        loaded = _verify_json_well_formed(
            package_dir=package_dir,
            checks=checks,
            errors=errors,
        )

        inventory = loaded.get("package_digest_inventory_v0.json")
        if inventory is not None:
            _verify_digest_inventory(
                package_dir=package_dir,
                inventory=inventory,
                checks=checks,
                errors=errors,
            )

        metadata = loaded.get("run_metadata_v0.json")
        if metadata is not None:
            _verify_metadata(
                metadata=metadata,
                expected=expected,
                checks=checks,
                errors=errors,
            )

        _verify_known_run_bindings(
            package_dir=package_dir,
            loaded=loaded,
            expected=expected,
            checks=checks,
            errors=errors,
        )
        _verify_external_bindings(
            package_dir=package_dir,
            loaded=loaded,
            checks=checks,
            errors=errors,
        )
        _verify_candidate_chain(
            package_dir=package_dir,
            loaded=loaded,
            checks=checks,
            errors=errors,
        )
        _verify_status_and_sidecars(
            loaded=loaded,
            expected=expected,
            checks=checks,
            errors=errors,
        )

    except VerificationError as exc:
        errors.append(str(exc))

    except Exception as exc:  # noqa: BLE001
        errors.append(f"unexpected verification failure: {exc}")

    status = "verified" if not errors else "failed"
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": status,
        "verified": status == "verified",
        "checked_utc": _now_utc(),
        "tool": {
            "name": "verify_release_grade_reference_package_v0.py",
            "version": TOOL_VERSION,
        },
        "package": {
            "path": str(package_dir) if package_dir is not None else str(args.package_dir),
        },
        "checks": checks,
        "errors": errors,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
    }

    out_path = _resolve(Path(args.out))
    _write_report(out_path, report)

    if errors:
        print(f"ERROR: package verification failed with {len(errors)} error(s)")
        for item in errors[:20]:
            print(f" - {item}")
        if len(errors) > 20:
            print(f" - ... {len(errors) - 20} more")
        print(f"Report written to {out_path}")
        return 1

    print(f"OK: complete release-grade reference package verified: {package_dir}")
    print(f"Report written to {out_path}")
    print("Authority boundary: package verified != release authorized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
