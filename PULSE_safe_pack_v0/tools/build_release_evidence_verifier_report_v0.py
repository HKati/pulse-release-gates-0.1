#!/usr/bin/env python3
"""Build a fail-closed release_evidence_verifier_report_v0 artifact.

This is the first trusted release-evidence verifier skeleton.

It intentionally never emits VERIFIED.
It does not materialize gates.
It does not write status.json.
It does not replace check_gates.py.
It does not reopen --release-grade-materialized.

The output is a FAILED verifier report that can be schema-validated and
relation-integrity checked.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

try:
    import jsonschema
except Exception:  # pragma: no cover
    jsonschema = None


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.check_release_evidence_input_manifest_v0 import (  # noqa: E402
    check_release_evidence_input_manifest,
)
from PULSE_safe_pack_v0.tools.check_release_evidence_verifier_report_v0 import (  # noqa: E402
    check_release_evidence_verifier_report,
)


SCHEMA_VERSION = "release_evidence_verifier_report_v0"
VERIFIER_ID = "pulse_release_evidence_verifier_v0"
VERIFIER_VERSION = "0.1.0"

VALID_EVIDENCE_KINDS = {
    "detector_evidence",
    "detector_materialization_report",
    "external_detector_summary",
    "refusal_delta_evidence",
    "provenance_record",
    "policy_reference",
    "registry_reference",
}

# Stage D failure-only candidate validation diagnostics.
#
# This mapping is intentionally empty in v0. Tests may monkeypatch it to
# exercise controlled-schema failure paths.
#
# Successful candidate schema validation is not represented by this builder.
# If success must be represented later, that requires a separate schema PR
# with explicitly non-promotional diagnostic semantics.
CANDIDATE_SCHEMA_VERSION_TO_PATH: dict[str, str] = {}


def _utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _repo_relative_or_input(path: pathlib.Path, raw: str) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return raw


def _git_sha() -> str | None:
    env_sha = os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA")
    if isinstance(env_sha, str) and env_sha.strip():
        candidate = env_sha.strip()
        if len(candidate) == 40 and all(
            c in "0123456789abcdefABCDEF" for c in candidate
        ):
            return candidate

    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None

    if len(out) == 40 and all(c in "0123456789abcdefABCDEF" for c in out):
        return out

    return None


def _run_key() -> str | None:
    parts: list[str] = []

    for key in (
        "GITHUB_RUN_ID",
        "GITHUB_RUN_NUMBER",
        "GITHUB_WORKFLOW",
        "CI_PIPELINE_ID",
        "BUILD_BUILDID",
    ):
        value = os.getenv(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{key}={value.strip()}")

    return "|".join(parts) if parts else None


def _load_json_schema_hint(path: pathlib.Path) -> str | None:
    if path.suffix.lower() not in {".json", ".jsonl"}:
        return None

    if path.suffix.lower() == ".jsonl":
        return None

    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(obj, dict):
        return None

    for key in ("schema_version", "schema"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _load_json_object(path: pathlib.Path, *, label: str) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"{label} is not valid JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")

    return obj


class DuplicateKeyError(ValueError):
    """Raised when JSON parsing sees a duplicate object key."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        out[key] = value

    return out


def _load_json_object_rejecting_duplicate_keys(
    path: pathlib.Path,
    *,
    label: str,
) -> dict[str, Any]:
    try:
        obj = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except DuplicateKeyError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"{label} is not valid JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")

    return obj


def _candidate_validation_error(
    *,
    code: str,
    message: str,
    instance_path: str | None = None,
    schema_path: str | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
    }

    if instance_path is not None:
        error["instance_path"] = instance_path

    if schema_path is not None:
        error["schema_path"] = schema_path

    return error


def _candidate_schema_validation_diagnostic(
    *,
    status: str,
    schema_version: str | None,
    schema_path: str | None,
    errors: list[dict[str, Any]] | None = None,
    duplicate_key_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {
        "status": status,
        "schema_version": schema_version,
        "schema_path": schema_path,
    }

    if errors:
        diagnostic["errors"] = errors

    if duplicate_key_validation is not None:
        diagnostic["duplicate_key_validation"] = duplicate_key_validation

    return diagnostic


def _normalize_git_sha(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    if not stripped:
        return None

    return stripped.lower()


def _git_sha_equal(left: Any, right: Any) -> bool:
    return _normalize_git_sha(left) == _normalize_git_sha(right)


def _parse_evidence_arg(raw: str) -> tuple[str, pathlib.Path, str]:
    if "=" not in raw:
        raise ValueError(
            "evidence arguments must use KIND=PATH format, "
            "for example detector_evidence=artifacts/detectors/report.json"
        )

    kind, path_raw = raw.split("=", 1)
    kind = kind.strip()
    path_raw = path_raw.strip()

    if kind not in VALID_EVIDENCE_KINDS:
        allowed = ", ".join(sorted(VALID_EVIDENCE_KINDS))
        raise ValueError(f"unsupported evidence kind {kind!r}; expected one of: {allowed}")

    if not path_raw:
        raise ValueError("evidence path must be non-empty")

    path = pathlib.Path(path_raw)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()

    return kind, path, path_raw


def _evidence_input(
    *,
    kind: str,
    path: pathlib.Path,
    raw_path: str,
    git_sha: str | None,
    run_key: str | None,
    provenance_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"candidate evidence file not found: {path}")

    provenance = {
        "observed_by": VERIFIER_ID,
        "trusted": False,
        "verification_status": "not_verified",
        "note": "candidate input recorded by fail-closed verifier skeleton",
    }

    if provenance_extra:
        provenance.update(provenance_extra)

    return {
        "kind": kind,
        "path": _repo_relative_or_input(path, raw_path),
        "sha256": _sha256_file(path),
        "schema_version": _load_json_schema_hint(path),
        "subject_binding": {
            "git_sha": git_sha,
            "run_key": run_key,
        },
        "provenance": provenance,
    }


def _policy_binding_from_paths(policy_path: pathlib.Path) -> dict[str, Any]:
    return {
        "policy_path": _repo_relative_or_input(policy_path, str(policy_path)),
        "policy_sha256": _sha256_file(policy_path) if policy_path.exists() else None,
        "policy_set": "required+release_required",
    }


def _registry_binding_from_paths(registry_path: pathlib.Path) -> dict[str, Any]:
    return {
        "registry_path": _repo_relative_or_input(registry_path, str(registry_path)),
        "registry_sha256": _sha256_file(registry_path) if registry_path.exists() else None,
    }


def _validate_and_load_input_manifest(path: pathlib.Path) -> dict[str, Any]:
    errors = check_release_evidence_input_manifest(path)
    if errors:
        joined = "\n - ".join(errors)
        raise ValueError(
            "release evidence input manifest failed validation:\n"
            f" - {joined}"
        )

    return _load_json_object(path, label="release evidence input manifest")


def _candidate_path(raw_path: str, manifest_path: pathlib.Path) -> pathlib.Path:
    candidate = pathlib.Path(raw_path)

    if candidate.is_absolute():
        return candidate.resolve()

    repo_candidate = (REPO_ROOT / candidate).resolve()
    if repo_candidate.exists():
        return repo_candidate

    return (manifest_path.parent / candidate).resolve()


def _candidate_schema_validation_from_manifest_entry(
    *,
    evidence_id: str,
    entry: dict[str, Any],
    resolved_path: pathlib.Path,
) -> dict[str, Any] | None:
    """Return failure-only candidate schema validation diagnostics.

    This is Stage D failure/unavailable diagnostic visibility only.

    It does not represent successful candidate schema validation.
    It does not verify evidence.
    It does not create trust.
    It does not satisfy relation bindings.
    It does not materialize gates.
    """

    schema_version_raw = entry.get("schema_version")
    schema_version = (
        schema_version_raw.strip()
        if isinstance(schema_version_raw, str) and schema_version_raw.strip()
        else None
    )

    try:
        candidate_obj = _load_json_object_rejecting_duplicate_keys(
            resolved_path,
            label=f"candidate evidence {evidence_id}",
        )
    except DuplicateKeyError as exc:
        error = _candidate_validation_error(
            code="candidate_duplicate_key",
            message=str(exc),
            instance_path="/",
        )
        return _candidate_schema_validation_diagnostic(
            status="failed",
            schema_version=schema_version,
            schema_path=None,
            errors=[
                error,
            ],
            duplicate_key_validation={
                "status": "failed",
                "errors": [
                    error,
                ],
            },
        )
    except ValueError as exc:
        return _candidate_schema_validation_diagnostic(
            status="failed",
            schema_version=schema_version,
            schema_path=None,
            errors=[
                _candidate_validation_error(
                    code="candidate_parse_failed",
                    message=str(exc),
                    instance_path="/",
                )
            ],
        )

    if not schema_version:
        return _candidate_schema_validation_diagnostic(
            status="unavailable",
            schema_version=None,
            schema_path=None,
            errors=[
                _candidate_validation_error(
                    code="candidate_schema_unavailable",
                    message=(
                        "candidate schema_version is missing; "
                        "candidate validation remains unavailable"
                    ),
                )
            ],
        )

    schema_rel = CANDIDATE_SCHEMA_VERSION_TO_PATH.get(schema_version)

    if not schema_rel:
        return _candidate_schema_validation_diagnostic(
            status="unavailable",
            schema_version=schema_version,
            schema_path=None,
            errors=[
                _candidate_validation_error(
                    code="candidate_schema_unavailable",
                    message=(
                        "candidate schema version has no controlled schema "
                        f"path mapping: {schema_version}"
                    ),
                )
            ],
        )

    schema_path = pathlib.Path(schema_rel)
    if not schema_path.is_absolute():
        schema_path = (REPO_ROOT / schema_path).resolve()
    else:
        schema_path = schema_path.resolve()

    schema_path_display = _repo_relative_or_input(schema_path, str(schema_path))

    if not schema_path.exists() or not schema_path.is_file():
        return _candidate_schema_validation_diagnostic(
            status="unavailable",
            schema_version=schema_version,
            schema_path=schema_path_display,
            errors=[
                _candidate_validation_error(
                    code="candidate_schema_unavailable",
                    message=f"candidate schema file is unavailable: {schema_path}",
                    schema_path=schema_path_display,
                )
            ],
        )

    try:
        schema_obj = _load_json_object_rejecting_duplicate_keys(
            schema_path,
            label=f"candidate schema {schema_version}",
        )
    except Exception as exc:  # noqa: BLE001
        return _candidate_schema_validation_diagnostic(
            status="failed",
            schema_version=schema_version,
            schema_path=schema_path_display,
            errors=[
                _candidate_validation_error(
                    code="candidate_schema_invalid",
                    message=str(exc),
                    schema_path=schema_path_display,
                )
            ],
        )

    if jsonschema is None:
        return _candidate_schema_validation_diagnostic(
            status="unavailable",
            schema_version=schema_version,
            schema_path=schema_path_display,
            errors=[
                _candidate_validation_error(
                    code="candidate_validator_unavailable",
                    message=(
                        "jsonschema is required for candidate schema validation; "
                        "partial fallback validation is not allowed"
                    ),
                    schema_path=schema_path_display,
                )
            ],
        )

    try:
        jsonschema.Draft202012Validator.check_schema(schema_obj)
    except Exception as exc:  # noqa: BLE001
        return _candidate_schema_validation_diagnostic(
            status="failed",
            schema_version=schema_version,
            schema_path=schema_path_display,
            errors=[
                _candidate_validation_error(
                    code="candidate_schema_invalid",
                    message=str(exc),
                    schema_path=schema_path_display,
                )
            ],
        )

    try:
        jsonschema.Draft202012Validator(schema_obj).validate(candidate_obj)
    except jsonschema.ValidationError as exc:
        return _candidate_schema_validation_diagnostic(
            status="failed",
            schema_version=schema_version,
            schema_path=schema_path_display,
            errors=[
                _candidate_validation_error(
                    code="candidate_schema_validation_failed",
                    message=exc.message,
                    instance_path="/" + "/".join(str(part) for part in exc.path),
                    schema_path=schema_path_display,
                )
            ],
        )
    except Exception as exc:  # noqa: BLE001
        return _candidate_schema_validation_diagnostic(
            status="failed",
            schema_version=schema_version,
            schema_path=schema_path_display,
            errors=[
                _candidate_validation_error(
                    code="candidate_partial_validation_rejected",
                    message=(
                        "candidate schema validation could not complete; "
                        f"partial validation is rejected: {exc}"
                    ),
                    schema_path=schema_path_display,
                )
            ],
        )

    # Current schema has no non-promotional success status.
    # Successful candidate schema validation is intentionally not represented
    # in this Stage D failure-only implementation split.
    return None


def _evidence_inputs_from_manifest(
    *,
    manifest: dict[str, Any],
    manifest_path: pathlib.Path,
    git_sha: str | None,
    run_key: str | None,
    failed_checks: list[str],
    warnings: list[str],
) -> list[dict[str, Any]]:
    candidate_evidence = manifest.get("candidate_evidence")
    if not isinstance(candidate_evidence, dict):
        failed_checks.append("input manifest has no candidate_evidence object")
        return []

    manifest_run_identity = manifest.get("run_identity")
    run_identity = manifest_run_identity if isinstance(manifest_run_identity, dict) else {}

    manifest_subject = manifest.get("subject")
    subject = manifest_subject if isinstance(manifest_subject, dict) else {}

    manifest_run_git_sha = run_identity.get("git_sha")
    manifest_run_key = run_identity.get("run_key")
    manifest_subject_commit_sha = subject.get("commit_sha")

    # These are the effective identities emitted into the verifier report.
    # Explicit --commit-sha / --run-key CLI overrides can differ from the input
    # manifest identity, so subject/run binding must be checked against the
    # report identity as well as the manifest-declared identity.
    report_subject_commit_sha = git_sha
    report_run_git_sha = git_sha
    report_run_key = run_key

    out: list[dict[str, Any]] = []

    for evidence_id, entry in sorted(
        candidate_evidence.items(),
        key=lambda item: str(item[0]),
    ):
        if not isinstance(entry, dict):
            failed_checks.append(f"candidate evidence entry is not an object: {evidence_id}")
            continue

        kind = entry.get("kind")
        raw_path = entry.get("path")
        expected_sha256 = entry.get("expected_sha256")

        subject_binding_raw = entry.get("subject_binding")
        subject_binding = subject_binding_raw if isinstance(subject_binding_raw, dict) else {}

        candidate_subject_git_sha = subject_binding.get("git_sha")
        candidate_subject_run_key = subject_binding.get("run_key")

        subject_git_sha_matches_subject_commit = _git_sha_equal(
            candidate_subject_git_sha,
            manifest_subject_commit_sha,
        )
        subject_git_sha_matches_run_identity = _git_sha_equal(
            candidate_subject_git_sha,
            manifest_run_git_sha,
        )
        run_key_matches_run_identity = candidate_subject_run_key == manifest_run_key

        subject_git_sha_matches_report_subject_commit = _git_sha_equal(
            candidate_subject_git_sha,
            report_subject_commit_sha,
        )
        subject_git_sha_matches_report_run_identity = _git_sha_equal(
            candidate_subject_git_sha,
            report_run_git_sha,
        )
        run_key_matches_report_run_identity = candidate_subject_run_key == report_run_key

        if not (
            subject_git_sha_matches_subject_commit
            and subject_git_sha_matches_report_subject_commit
        ):
            failed_checks.append(
                "candidate evidence subject git_sha mismatch against subject commit: "
                f"{evidence_id}"
            )

        if not (
            subject_git_sha_matches_run_identity
            and subject_git_sha_matches_report_run_identity
        ):
            failed_checks.append(
                "candidate evidence subject git_sha mismatch against run identity: "
                f"{evidence_id}"
            )

        if not (run_key_matches_run_identity and run_key_matches_report_run_identity):
            failed_checks.append(
                "candidate evidence run_key mismatch against run identity: "
                f"{evidence_id}"
            )

        if not isinstance(kind, str) or kind not in VALID_EVIDENCE_KINDS:
            failed_checks.append(f"candidate evidence has unsupported kind: {evidence_id}")
            continue

        if not isinstance(raw_path, str) or not raw_path.strip():
            failed_checks.append(f"candidate evidence path is missing: {evidence_id}")
            continue

        resolved_path = _candidate_path(raw_path.strip(), manifest_path)

        if not resolved_path.exists() or not resolved_path.is_file():
            failed_checks.append(
                f"candidate evidence declared by manifest is missing: "
                f"{evidence_id} -> {raw_path}"
            )
            continue

        actual_sha256 = _sha256_file(resolved_path)
        sha_matches = actual_sha256 == expected_sha256

        if not sha_matches:
            failed_checks.append(f"candidate evidence digest mismatch: {evidence_id}")

        candidate_schema_validation = _candidate_schema_validation_from_manifest_entry(
            evidence_id=str(evidence_id),
            entry=entry,
            resolved_path=resolved_path,
        )

        provenance_extra: dict[str, Any] = {
            "source_manifest": _repo_relative_or_input(
                manifest_path,
                str(manifest_path),
            ),
            "source_manifest_id": manifest.get("manifest_id"),
            "candidate_evidence_id": evidence_id,
            "expected_sha256": expected_sha256,
            "actual_sha256_matches_expected": sha_matches,
            "candidate_subject_git_sha": candidate_subject_git_sha,
            "candidate_subject_run_key": candidate_subject_run_key,
            "manifest_subject_commit_sha": manifest_subject_commit_sha,
            "manifest_run_identity_git_sha": manifest_run_git_sha,
            "manifest_run_identity_run_key": manifest_run_key,
            "report_subject_commit_sha": report_subject_commit_sha,
            "report_run_identity_git_sha": report_run_git_sha,
            "report_run_identity_run_key": report_run_key,
            "subject_git_sha_matches_subject_commit": (
                subject_git_sha_matches_subject_commit
            ),
            "subject_git_sha_matches_run_identity": (
                subject_git_sha_matches_run_identity
            ),
            "run_key_matches_run_identity": run_key_matches_run_identity,
            "subject_git_sha_matches_report_subject_commit": (
                subject_git_sha_matches_report_subject_commit
            ),
            "subject_git_sha_matches_report_run_identity": (
                subject_git_sha_matches_report_run_identity
            ),
            "run_key_matches_report_run_identity": (
                run_key_matches_report_run_identity
            ),
        }

        if candidate_schema_validation is not None:
            provenance_extra["candidate_schema_validation"] = (
                candidate_schema_validation
            )

        try:
            out.append(
                _evidence_input(
                    kind=kind,
                    path=resolved_path,
                    raw_path=raw_path.strip(),
                    git_sha=(
                        str(candidate_subject_git_sha)
                        if isinstance(candidate_subject_git_sha, str)
                        else None
                    ),
                    run_key=(
                        str(candidate_subject_run_key)
                        if isinstance(candidate_subject_run_key, str)
                        else None
                    ),
                    provenance_extra=provenance_extra,
                )
            )
        except Exception as exc:  # noqa: BLE001
            failed_checks.append(
                f"candidate evidence could not be recorded: {evidence_id}: {exc}"
            )

    if out:
        warnings.append(
            "candidate evidence inputs were recorded from input manifest, "
            "but verifier skeleton does not verify them"
        )

    return out


def _record_manifest_expectation_comparison(
    *,
    manifest: dict[str, Any],
    recorded_evidence_inputs: list[dict[str, Any]],
    failed_checks: list[str],
    warnings: list[str],
) -> None:
    """Record explicit pending expectation state from an input manifest.

    This does not verify evidence.
    This does not satisfy relations.
    This does not materialize gates.

    It only makes the pre-materialization gap visible in the FAILED report.
    """

    candidate_evidence = manifest.get("candidate_evidence")
    expected_relations = manifest.get("expected_relation_bindings")
    expected_gates = manifest.get("expected_gate_materialization")

    candidate_map = candidate_evidence if isinstance(candidate_evidence, dict) else {}
    relation_map = expected_relations if isinstance(expected_relations, dict) else {}
    gate_map = expected_gates if isinstance(expected_gates, dict) else {}

    recorded_candidate_ids = {
        provenance.get("candidate_evidence_id")
        for item in recorded_evidence_inputs
        if isinstance(item, dict)
        for provenance in [item.get("provenance")]
        if isinstance(provenance, dict)
    }

    warnings.append(
        "input manifest expectation comparison is fail-closed and descriptive only"
    )
    warnings.append(
        "input manifest declares "
        f"{len(candidate_map)} candidate evidence item(s), "
        f"{len(relation_map)} expected relation binding(s), and "
        f"{len(gate_map)} expected gate materialization item(s)"
    )

    for evidence_id in sorted(candidate_map.keys(), key=str):
        if evidence_id not in recorded_candidate_ids:
            failed_checks.append(
                f"expected candidate evidence not recorded: {evidence_id}"
            )
        else:
            failed_checks.append(
                f"expected candidate evidence recorded but not verified: {evidence_id}"
            )

    for relation_id, relation in sorted(relation_map.items(), key=lambda item: str(item[0])):
        failed_checks.append(
            f"expected relation binding pending verification: {relation_id}"
        )

        if not isinstance(relation, dict):
            continue

        source_evidence_id = relation.get("source_evidence_id")
        if source_evidence_id not in candidate_map:
            failed_checks.append(
                f"expected relation binding references missing candidate evidence: "
                f"{relation_id} -> {source_evidence_id}"
            )

        expected_gate_id = relation.get("expected_gate_id")
        if expected_gate_id is not None and expected_gate_id not in gate_map:
            failed_checks.append(
                f"expected relation binding references missing expected gate: "
                f"{relation_id} -> {expected_gate_id}"
            )

    for gate_id, gate in sorted(gate_map.items(), key=lambda item: str(item[0])):
        failed_checks.append(
            f"expected gate materialization pending verification: {gate_id}"
        )

        if not isinstance(gate, dict):
            continue

        for evidence_id in gate.get("candidate_evidence_ids", []):
            if evidence_id not in candidate_map:
                failed_checks.append(
                    f"expected gate materialization references missing candidate "
                    f"evidence: {gate_id} -> {evidence_id}"
                )
            elif evidence_id not in recorded_candidate_ids:
                failed_checks.append(
                    f"expected gate materialization candidate evidence not recorded: "
                    f"{gate_id} -> {evidence_id}"
                )

        for relation_id in gate.get("relation_binding_ids", []):
            if relation_id not in relation_map:
                failed_checks.append(
                    f"expected gate materialization references missing expected "
                    f"relation: {gate_id} -> {relation_id}"
                )


def build_report(
    *,
    policy_path: pathlib.Path,
    registry_path: pathlib.Path,
    repository: str | None,
    commit_sha: str | None,
    run_key: str | None,
    release_candidate: str | None,
    evidence_args: list[str],
    input_manifest_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    evidence_inputs: list[dict[str, Any]] = []
    warnings: list[str] = []
    manifest: dict[str, Any] | None = None

    if input_manifest_path is not None:
        manifest = _validate_and_load_input_manifest(input_manifest_path)

        manifest_run_identity = manifest.get("run_identity")
        if isinstance(manifest_run_identity, dict):
            commit_sha = commit_sha or manifest_run_identity.get("git_sha")
            run_key = run_key or manifest_run_identity.get("run_key")

        manifest_subject = manifest.get("subject")
        if isinstance(manifest_subject, dict):
            repository = repository or manifest_subject.get("repository")
            release_candidate = release_candidate or manifest_subject.get(
                "release_candidate"
            )
            commit_sha = commit_sha or manifest_subject.get("commit_sha")

    failed_checks = [
        "trusted release-evidence verifier skeleton does not verify evidence yet",
        "no verified relation bindings present",
        "no gate materialization performed",
    ]

    if manifest is not None and input_manifest_path is not None:
        evidence_inputs.extend(
            _evidence_inputs_from_manifest(
                manifest=manifest,
                manifest_path=input_manifest_path,
                git_sha=commit_sha,
                run_key=run_key,
                failed_checks=failed_checks,
                warnings=warnings,
            )
        )
        _record_manifest_expectation_comparison(
            manifest=manifest,
            recorded_evidence_inputs=evidence_inputs,
            failed_checks=failed_checks,
            warnings=warnings,
        )
        failed_checks.append(
            "input manifest expectations are recorded only; verification is not implemented"
        )
        failed_checks.append(
            "input manifest expected relation bindings are not verified by skeleton"
        )
        failed_checks.append(
            "input manifest expected gate materialization bindings are not materialized by skeleton"
        )
    else:
        for raw in evidence_args:
            kind, evidence_path, raw_path = _parse_evidence_arg(raw)
            evidence_inputs.append(
                _evidence_input(
                    kind=kind,
                    path=evidence_path,
                    raw_path=raw_path,
                    git_sha=commit_sha,
                    run_key=run_key,
                )
            )

    if not evidence_inputs:
        if manifest is None and not evidence_args:
            failed_checks.append("no candidate evidence inputs were supplied")
        else:
            failed_checks.append("no candidate evidence inputs were recorded")
    else:
        failed_checks.append(
            "candidate evidence inputs are recorded only; verification is not implemented"
        )

    policy_binding = _policy_binding_from_paths(policy_path)
    registry_binding = _registry_binding_from_paths(registry_path)

    if isinstance(manifest, dict):
        manifest_policy = manifest.get("policy_binding")
        if isinstance(manifest_policy, dict):
            policy_binding = {
                "policy_path": manifest_policy.get("policy_path"),
                "policy_sha256": manifest_policy.get("policy_sha256"),
                "policy_set": manifest_policy.get("policy_set"),
            }

        manifest_registry = manifest.get("registry_binding")
        if isinstance(manifest_registry, dict):
            registry_binding = {
                "registry_path": manifest_registry.get("registry_path"),
                "registry_sha256": manifest_registry.get("registry_sha256"),
            }

    return {
        "schema_version": SCHEMA_VERSION,
        "created_utc": _utc_now(),
        "verifier_id": VERIFIER_ID,
        "verifier_version": VERIFIER_VERSION,
        "verifier_decision": "FAILED",
        "run_identity": {
            "run_mode": "prod",
            "run_key": run_key,
            "git_sha": commit_sha,
        },
        "subject": {
            "repository": repository,
            "commit_sha": commit_sha,
            "release_candidate": release_candidate,
        },
        "policy_binding": policy_binding,
        "registry_binding": registry_binding,
        "evidence_inputs": evidence_inputs,
        "verified_artifacts": [],
        "relation_bindings": [],
        "gate_materialization": {},
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a fail-closed release_evidence_verifier_report_v0 artifact."
    )
    parser.add_argument(
        "--out",
        default="PULSE_safe_pack_v0/artifacts/release_evidence_verifier_report_v0.json",
        help="Output path for release_evidence_verifier_report_v0.json.",
    )
    parser.add_argument(
        "--input-manifest",
        default=None,
        help=(
            "Optional release_evidence_input_manifest_v0 JSON file. "
            "Manifest expectations are validated and recorded, but not verified."
        ),
    )
    parser.add_argument(
        "--policy",
        default="pulse_gate_policy_v0.yml",
        help="Declared gate policy path.",
    )
    parser.add_argument(
        "--registry",
        default="pulse_gate_registry_v0.yml",
        help="Gate registry path.",
    )
    parser.add_argument(
        "--repository",
        default=os.getenv("GITHUB_REPOSITORY"),
        help="Repository subject, if known.",
    )
    parser.add_argument(
        "--commit-sha",
        default=None,
        help=(
            "Subject commit SHA. When --input-manifest is omitted, defaults to "
            "CI/git discovery when available. With --input-manifest, an explicit "
            "value overrides the manifest identity."
        ),
    )
    parser.add_argument(
        "--run-key",
        default=None,
        help=(
            "Run identity key. When --input-manifest is omitted, defaults to CI "
            "environment discovery when available. With --input-manifest, an "
            "explicit value overrides the manifest identity."
        ),
    )
    parser.add_argument(
        "--release-candidate",
        default=None,
        help="Optional release candidate identifier.",
    )
    parser.add_argument(
        "--evidence",
        action="append",
        default=[],
        metavar="KIND=PATH",
        help=(
            "Candidate evidence input to record without trusting it. "
            "May be supplied multiple times. Cannot be combined with --input-manifest."
        ),
    )

    args = parser.parse_args()

    if args.input_manifest and args.evidence:
        print(
            "ERROR: --input-manifest cannot be combined with --evidence; "
            "use one candidate input source",
            file=sys.stderr,
        )
        return 1

    input_manifest_path: pathlib.Path | None = None
    if args.input_manifest:
        input_manifest_path = pathlib.Path(args.input_manifest)
        if not input_manifest_path.is_absolute():
            input_manifest_path = (REPO_ROOT / input_manifest_path).resolve()
        else:
            input_manifest_path = input_manifest_path.resolve()

    commit_sha = args.commit_sha
    run_key = args.run_key

    if input_manifest_path is None:
        commit_sha = commit_sha or _git_sha()
        run_key = run_key or _run_key()

    try:
        report = build_report(
            policy_path=(
                (REPO_ROOT / args.policy).resolve()
                if not pathlib.Path(args.policy).is_absolute()
                else pathlib.Path(args.policy).resolve()
            ),
            registry_path=(
                (REPO_ROOT / args.registry).resolve()
                if not pathlib.Path(args.registry).is_absolute()
                else pathlib.Path(args.registry).resolve()
            ),
            repository=args.repository,
            commit_sha=commit_sha,
            run_key=run_key,
            release_candidate=args.release_candidate,
            evidence_args=list(args.evidence or []),
            input_manifest_path=input_manifest_path,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out_path = pathlib.Path(args.out)
    if not out_path.is_absolute():
        out_path = (REPO_ROOT / out_path).resolve()

    write_json(out_path, report)

    errors = check_release_evidence_verifier_report(out_path)
    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print(f"OK: wrote fail-closed release evidence verifier report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
