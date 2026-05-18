#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]

PACKAGE_MANIFEST_SCHEMA = (
    REPO_ROOT / "schemas" / "pulse_ref_release_reference_package_v0.schema.json"
)
PACKAGE_DIGESTS_SCHEMA = (
    REPO_ROOT / "schemas" / "pulse_ref_package_digests_v0.schema.json"
)
MATERIALIZED_GATE_SETS_SCHEMA = (
    REPO_ROOT / "schemas" / "pulse_ref_materialized_gate_sets_v0.schema.json"
)
OPERATOR_HANDOFF_REPORT_SCHEMA = (
    REPO_ROOT / "schemas" / "pulse_ref_operator_handoff_report_v0.schema.json"
)
RELEASE_AUTHORITY_SCHEMA = REPO_ROOT / "schemas" / "release_authority_v0.schema.json"
CI_OUTCOME_SCHEMA = REPO_ROOT / "schemas" / "pulse_ref_ci_outcome_v0.schema.json"
PUBLICATION_SNAPSHOT_SCHEMA = (
    REPO_ROOT / "schemas" / "pulse_ref_publication_snapshot_v0.schema.json"
)

PACKAGE_MANIFEST_SCHEMA_PATH = "schemas/pulse_ref_release_reference_package_v0.schema.json"
PACKAGE_DIGESTS_SCHEMA_PATH = "schemas/pulse_ref_package_digests_v0.schema.json"
MATERIALIZED_GATE_SETS_SCHEMA_PATH = (
    "schemas/pulse_ref_materialized_gate_sets_v0.schema.json"
)
OPERATOR_HANDOFF_REPORT_SCHEMA_PATH = (
    "schemas/pulse_ref_operator_handoff_report_v0.schema.json"
)
RELEASE_AUTHORITY_SCHEMA_PATH = "schemas/release_authority_v0.schema.json"
CI_OUTCOME_SCHEMA_PATH = "schemas/pulse_ref_ci_outcome_v0.schema.json"
PUBLICATION_SNAPSHOT_SCHEMA_PATH = (
    "schemas/pulse_ref_publication_snapshot_v0.schema.json"
)

ARTIFACT_REF_FIELDS = [
    "status_artifact",
    "gate_policy",
    "gate_registry",
    "materialized_gate_sets",
    "operator_handoff_report",
    "release_authority_manifest",
    "ci_outcome",
    "publication_snapshot",
    "package_digests",
]

CANONICAL_RA1_ARTIFACT_PATHS = {
    "status_artifact": "status/status.json",
    "gate_policy": "policy/pulse_gate_policy_v0.yml",
    "gate_registry": "policy/pulse_gate_registry_v0.yml",
    "materialized_gate_sets": "gates/materialized_gate_sets.json",
    "operator_handoff_report": "handoff/operator_handoff_report.json",
    "release_authority_manifest": "release_authority/release_authority_manifest.json",
    "ci_outcome": "ci/ci_outcome.json",
    "publication_snapshot": "publication/publication_snapshot.json",
    "package_digests": "digests/package_digests.json",
}

ARTIFACT_SCHEMA_TARGETS = [
    (
        "materialized_gate_sets",
        MATERIALIZED_GATE_SETS_SCHEMA_PATH,
        MATERIALIZED_GATE_SETS_SCHEMA,
    ),
    (
        "operator_handoff_report",
        OPERATOR_HANDOFF_REPORT_SCHEMA_PATH,
        OPERATOR_HANDOFF_REPORT_SCHEMA,
    ),
    (
        "release_authority_manifest",
        RELEASE_AUTHORITY_SCHEMA_PATH,
        RELEASE_AUTHORITY_SCHEMA,
    ),
    (
        "ci_outcome",
        CI_OUTCOME_SCHEMA_PATH,
        CI_OUTCOME_SCHEMA,
    ),
    (
        "publication_snapshot",
        PUBLICATION_SNAPSHOT_SCHEMA_PATH,
        PUBLICATION_SNAPSHOT_SCHEMA,
    ),
]

GATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


def _safe_value(value: Any) -> str:
    try:
        rendered = repr(value)
    except Exception:
        rendered = f"<unrepresentable {type(value).__name__}>"

    if len(rendered) > 160:
        return rendered[:157] + "..."

    return rendered


def _is_gate_id(value: Any) -> bool:
    return isinstance(value, str) and bool(GATE_ID_RE.fullmatch(value))


def _validate_gate_id_array(
    *,
    name: str,
    value: Any,
    failures: list[str],
) -> list[str] | None:
    if not isinstance(value, list):
        failures.append(f"{name} must be an array of gate ID strings")
        return None

    out: list[str] = []
    seen: set[str] = set()

    for index, item in enumerate(value):
        if not _is_gate_id(item):
            failures.append(
                f"{name}[{index}] must be a string gate ID, found "
                f"{type(item).__name__}: {_safe_value(item)}"
            )
            continue

        if item in seen:
            failures.append(f"{name}[{index}] duplicates gate ID {item!r}")
            continue

        seen.add(item)
        out.append(item)

    return out if not failures else None


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


def _is_safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not value:
        return False
    if "\\" in value:
        return False

    path = Path(value)

    if path.is_absolute():
        return False
    if any(part == ".." for part in path.parts):
        return False

    return True


def _report_safe_path(value: Any) -> str:
    return value if _is_safe_relative_path(value) else "_invalid_artifact_path"


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _report_safe_sha256(value: Any) -> str:
    return value if _is_sha256(value) else "0" * 64


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)

    return out


def _resolve_package_artifact(
    package_root: Path,
    artifact_path: str,
) -> tuple[Path | None, str | None]:
    if not _is_safe_relative_path(artifact_path):
        return None, f"unsafe artifact path: {artifact_path!r}"

    try:
        resolved_root = package_root.resolve(strict=True)
    except FileNotFoundError:
        return None, f"package root does not exist: {package_root}"

    candidate = resolved_root / artifact_path

    try:
        resolved_candidate = candidate.resolve(strict=True)
    except FileNotFoundError:
        return candidate, None
    except OSError as exc:
        return None, f"could not resolve artifact path {artifact_path!r}: {exc}"

    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return None, (
            f"artifact path {artifact_path!r} resolves outside package root: "
            f"{resolved_candidate}"
        )

    return resolved_candidate, None


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, str(exc)

    if not isinstance(obj, dict):
        return None, "JSON value is not an object"

    return obj, None


def _schema_errors(instance: dict[str, Any], schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )

    return [
        f"{list(error.absolute_path)}: {error.message}"
        for error in errors
    ]


def _schema_check(
    *,
    artifact_path: str,
    schema_path: str,
    instance: dict[str, Any] | None,
    schema_file: Path,
    errors: list[str],
) -> dict[str, Any]:
    if instance is None:
        message = f"{artifact_path} could not be loaded as a JSON object"
        errors.append(message)
        return {
            "artifact_path": artifact_path,
            "schema_path": schema_path,
            "ok": False,
            "message": message,
        }

    schema_failures = _schema_errors(instance, schema_file)

    if schema_failures:
        message = "; ".join(schema_failures)
        errors.append(f"{artifact_path} schema validation failed: {message}")
        return {
            "artifact_path": artifact_path,
            "schema_path": schema_path,
            "ok": False,
            "message": message,
        }

    return {
        "artifact_path": artifact_path,
        "schema_path": schema_path,
        "ok": True,
    }


def _load_package_json_artifact(
    package_root: Path,
    rel_path: str,
) -> tuple[dict[str, Any] | None, str | None]:
    artifact_file, path_error = _resolve_package_artifact(package_root, rel_path)

    if path_error is not None:
        return None, path_error
    if artifact_file is None:
        return None, f"artifact path could not be resolved: {rel_path}"

    return _read_json(artifact_file)


def _manifest_artifact_path(
    manifest: dict[str, Any],
    field: str,
) -> str | None:
    artifact_ref = manifest.get(field)

    if not isinstance(artifact_ref, dict):
        return None

    rel_path = artifact_ref.get("path")

    return rel_path if isinstance(rel_path, str) else None


def _digest_check(
    *,
    package_root: Path,
    artifact_path: str,
    expected_sha256: str,
    source: str,
    errors: list[str],
) -> dict[str, Any]:
    report_expected_sha256 = _report_safe_sha256(expected_sha256)
    expected_sha256_valid = _is_sha256(expected_sha256)

    artifact_file, path_error = _resolve_package_artifact(package_root, artifact_path)

    actual_sha256 = _sha256_file(artifact_file) if artifact_file is not None else None

    ok = (
        path_error is None
        and expected_sha256_valid
        and actual_sha256 == expected_sha256
    )

    result: dict[str, Any] = {
        "artifact_path": _report_safe_path(artifact_path),
        "expected_sha256": report_expected_sha256,
        "actual_sha256": actual_sha256,
        "ok": ok,
        "source": source,
    }

    messages: list[str] = []

    if path_error is not None:
        messages.append(path_error)

    if not expected_sha256_valid:
        messages.append(
            f"{artifact_path} expected_sha256 is not a lowercase SHA-256 digest: "
            f"{expected_sha256!r}"
        )

    if path_error is None and expected_sha256_valid and actual_sha256 != expected_sha256:
        messages.append(
            f"{artifact_path} digest mismatch: "
            f"expected={expected_sha256} actual={actual_sha256}"
        )

    if messages:
        message = "; ".join(messages)
        errors.append(message)
        result["message"] = message

    return result


def _check_package_id_consistency(
    *,
    manifest: dict[str, Any] | None,
    digests: dict[str, Any] | None,
    errors: list[str],
) -> dict[str, Any]:
    if manifest is None or digests is None:
        return {
            "name": "package_id_consistency",
            "ok": False,
            "message": "package manifest or digest manifest missing",
        }

    manifest_package_id = manifest.get("package_id")
    digest_package_id = digests.get("package_id")

    ok = digest_package_id in (None, manifest_package_id)

    result: dict[str, Any] = {
        "name": "package_id_consistency",
        "ok": ok,
        "path": "digests/package_digests.json",
    }

    if not ok:
        message = (
            "package_id mismatch between package_manifest.json and "
            "digests/package_digests.json"
        )
        errors.append(message)
        result["message"] = message

    return result


def _check_authority_boundary(
    *,
    name: str,
    path: str,
    creates_release_authority: Any,
    errors: list[str],
) -> dict[str, Any]:
    ok = creates_release_authority is False

    result: dict[str, Any] = {
        "name": name,
        "ok": ok,
        "path": path,
    }

    if not ok:
        message = f"{path} must not create release authority"
        errors.append(message)
        result["message"] = message

    return result


def _cross_check_result(
    *,
    name: str,
    ok: bool,
    path: str,
    message: str | None = None,
    errors: list[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "ok": ok,
        "path": _report_safe_path(path),
    }

    if not ok:
        error_message = message or f"{name} failed"
        errors.append(error_message)
        result["message"] = error_message

    return result


def _check_materialized_gate_sets_match_policy(
    *,
    package_root: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    policy_path = _manifest_artifact_path(manifest, "gate_policy")
    gate_sets_path = _manifest_artifact_path(manifest, "materialized_gate_sets")

    if policy_path is None or gate_sets_path is None:
        return _cross_check_result(
            name="materialized_gate_sets_match_policy",
            ok=False,
            path="gates/materialized_gate_sets.json",
            message="package manifest must reference gate_policy and materialized_gate_sets",
            errors=errors,
        )

    policy_file, policy_path_error = _resolve_package_artifact(package_root, policy_path)
    if policy_path_error is not None or policy_file is None:
        return _cross_check_result(
            name="materialized_gate_sets_match_policy",
            ok=False,
            path=policy_path,
            message=policy_path_error or f"could not resolve policy path: {policy_path}",
            errors=errors,
        )

    gate_sets, gate_sets_error = _load_package_json_artifact(package_root, gate_sets_path)
    if gate_sets_error is not None or gate_sets is None:
        return _cross_check_result(
            name="materialized_gate_sets_match_policy",
            ok=False,
            path=gate_sets_path,
            message=gate_sets_error or f"could not load gate sets: {gate_sets_path}",
            errors=errors,
        )

    try:
        policy = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return _cross_check_result(
            name="materialized_gate_sets_match_policy",
            ok=False,
            path=policy_path,
            message=f"could not load packaged policy YAML: {exc}",
            errors=errors,
        )

    try:
        policy_gates = policy["gates"]
        raw_required = policy_gates["required"]
        raw_release_required = policy_gates["release_required"]
    except Exception as exc:
        return _cross_check_result(
            name="materialized_gate_sets_match_policy",
            ok=False,
            path=policy_path,
            message=f"packaged policy does not expose required gate sets: {exc}",
            errors=errors,
        )

    mismatches: list[str] = []
    required = _validate_gate_id_array(
        name="policy.gates.required",
        value=raw_required,
        failures=mismatches,
    )
    release_required = _validate_gate_id_array(
        name="policy.gates.release_required",
        value=raw_release_required,
        failures=mismatches,
    )

    effective: list[str] | None = None
    if required is not None and release_required is not None:
        effective = _unique_preserve_order(required + release_required)

    if gate_sets.get("policy_path") != policy_path:
        mismatches.append(
            f"policy_path mismatch: expected {policy_path!r}, "
            f"found {gate_sets.get('policy_path')!r}"
        )

    policy_sha = _sha256_file(policy_file)
    if gate_sets.get("policy_sha256") != policy_sha:
        mismatches.append(
            f"policy_sha256 mismatch: expected {policy_sha!r}, "
            f"found {gate_sets.get('policy_sha256')!r}"
        )

    sets = gate_sets.get("sets")
    if not isinstance(sets, dict):
        mismatches.append("materialized gate sets must contain object-valued sets")
    else:
            materialized_required = _validate_gate_id_array(
            name="materialized_gate_sets.sets.required",
            value=sets.get("required"),
            failures=mismatches,
        )
        materialized_release_required = _validate_gate_id_array(
            name="materialized_gate_sets.sets.release_required",
            value=sets.get("release_required"),
            failures=mismatches,
        )

        if required is not None and materialized_required is not None:
            if materialized_required != required:
                mismatches.append("sets.required does not match packaged policy gates.required")

        if release_required is not None and materialized_release_required is not None:
            if materialized_release_required != release_required:
                mismatches.append(
                    "sets.release_required does not match packaged policy gates.release_required"
                )

    materialized_effective = _validate_gate_id_array(
        name="materialized_gate_sets.effective_required_gates",
        value=gate_sets.get("effective_required_gates"),
        failures=mismatches,
    )

    if effective is not None and materialized_effective is not None:
        if materialized_effective != effective:
            mismatches.append(
                "effective_required_gates does not equal ordered required + release_required"
            )

    return _cross_check_result(
        name="materialized_gate_sets_match_policy",
        ok=mismatches == [],
        path=gate_sets_path,
        message="; ".join(mismatches) if mismatches else None,
        errors=errors,
    )


def _check_status_satisfies_effective_required_gates(
    *,
    package_root: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    status_path = _manifest_artifact_path(manifest, "status_artifact")
    gate_sets_path = _manifest_artifact_path(manifest, "materialized_gate_sets")

    if status_path is None or gate_sets_path is None:
        return _cross_check_result(
            name="status_satisfies_effective_required_gates",
            ok=False,
            path="status/status.json",
            message="package manifest must reference status_artifact and materialized_gate_sets",
            errors=errors,
        )

    status, status_error = _load_package_json_artifact(package_root, status_path)
    if status_error is not None or status is None:
        return _cross_check_result(
            name="status_satisfies_effective_required_gates",
            ok=False,
            path=status_path,
            message=status_error or f"could not load status artifact: {status_path}",
            errors=errors,
        )

    gate_sets, gate_sets_error = _load_package_json_artifact(package_root, gate_sets_path)
    if gate_sets_error is not None or gate_sets is None:
        return _cross_check_result(
            name="status_satisfies_effective_required_gates",
            ok=False,
            path=gate_sets_path,
            message=gate_sets_error or f"could not load gate sets: {gate_sets_path}",
            errors=errors,
        )

    metrics = status.get("metrics")
    diagnostics = status.get("diagnostics")
    gates = status.get("gates")
    effective_required_gates = gate_sets.get("effective_required_gates")

    failures: list[str] = []

    run_mode = metrics.get("run_mode") if isinstance(metrics, dict) else None
    if run_mode != "prod":
        failures.append(f"status metrics.run_mode must be 'prod', found {run_mode!r}")

    gates_stubbed = (
        diagnostics.get("gates_stubbed")
        if isinstance(diagnostics, dict)
        else None
    )
    if gates_stubbed is not False:
        failures.append(
            f"status diagnostics.gates_stubbed must be false, found {gates_stubbed!r}"
        )

    if not isinstance(gates, dict):
        failures.append("status gates must be an object")
        gates = {}

        effective_required_gate_ids = _validate_gate_id_array(
        name="materialized_gate_sets.effective_required_gates",
        value=effective_required_gates,
        failures=failures,
    )

        if effective_required_gate_ids is not None:
        missing = [
            gate_id
            for gate_id in effective_required_gate_ids
            if gate_id not in gates
        ]
        false_gates = [
            gate_id
            for gate_id in effective_required_gate_ids
            if gates.get(gate_id) is not True
        ]

        if missing:
            failures.append(f"missing effective required gates: {', '.join(missing)}")
        if false_gates:
            failures.append(f"false effective required gates: {', '.join(false_gates)}")

    return _cross_check_result(
        name="status_satisfies_effective_required_gates",
        ok=failures == [],
        path=status_path,
        message="; ".join(failures) if failures else None,
        errors=errors,
    )


def _check_handoff_matches_status_and_gate_sets(
    *,
    package_root: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    handoff_path = _manifest_artifact_path(manifest, "operator_handoff_report")
    status_path = _manifest_artifact_path(manifest, "status_artifact")
    gate_sets_path = _manifest_artifact_path(manifest, "materialized_gate_sets")

    if handoff_path is None or status_path is None or gate_sets_path is None:
        return _cross_check_result(
            name="handoff_matches_status_and_gate_sets",
            ok=False,
            path="handoff/operator_handoff_report.json",
            message=(
                "package manifest must reference operator_handoff_report, "
                "status_artifact, and materialized_gate_sets"
            ),
            errors=errors,
        )

    handoff, handoff_error = _load_package_json_artifact(package_root, handoff_path)
    if handoff_error is not None or handoff is None:
        return _cross_check_result(
            name="handoff_matches_status_and_gate_sets",
            ok=False,
            path=handoff_path,
            message=handoff_error or f"could not load handoff artifact: {handoff_path}",
            errors=errors,
        )

    gate_sets, gate_sets_error = _load_package_json_artifact(package_root, gate_sets_path)
    if gate_sets_error is not None or gate_sets is None:
        return _cross_check_result(
            name="handoff_matches_status_and_gate_sets",
            ok=False,
            path=gate_sets_path,
            message=gate_sets_error or f"could not load gate sets: {gate_sets_path}",
            errors=errors,
        )

    status_file, status_path_error = _resolve_package_artifact(package_root, status_path)
    if status_path_error is not None or status_file is None:
        return _cross_check_result(
            name="handoff_matches_status_and_gate_sets",
            ok=False,
            path=status_path,
            message=status_path_error or f"could not resolve status path: {status_path}",
            errors=errors,
        )

    status_sha = _sha256_file(status_file)
    failures: list[str] = []

    if handoff.get("ok") is not True:
        failures.append(f"handoff ok must be true, found {handoff.get('ok')!r}")

    if handoff.get("gate_mode") != "release-grade":
        failures.append(
            f"handoff gate_mode must be 'release-grade', found {handoff.get('gate_mode')!r}"
        )

    status_source = handoff.get("status_source")
    if not isinstance(status_source, dict):
        failures.append("handoff status_source must be an object")
        status_source = {}

    if status_source.get("mode") != "existing":
        failures.append(
            f"handoff status_source.mode must be 'existing', "
            f"found {status_source.get('mode')!r}"
        )

    if status_source.get("status_path") != status_path:
        failures.append(
            f"handoff status_source.status_path mismatch: "
            f"expected {status_path!r}, found {status_source.get('status_path')!r}"
        )

    for field in (
        "status_sha256_before_run",
        "status_sha256_after_generation",
        "status_sha256_after_run",
    ):
        if status_source.get(field) != status_sha:
            failures.append(
                f"handoff status_source.{field} mismatch: "
                f"expected {status_sha!r}, found {status_source.get(field)!r}"
            )

    sets = gate_sets.get("sets")
    if not isinstance(sets, dict):
        failures.append("materialized gate sets must contain object-valued sets")
        sets = {}

    if handoff.get("materialized_gate_sets") != sets:
        failures.append("handoff materialized_gate_sets does not match package gate sets")

    if handoff.get("effective_required_gates") != gate_sets.get("effective_required_gates"):
        failures.append(
            "handoff effective_required_gates does not match package gate sets"
        )

    boundary = handoff.get("authority_boundary")
    creates_release_authority = (
        boundary.get("creates_release_authority")
        if isinstance(boundary, dict)
        else None
    )
    if creates_release_authority is not False:
        failures.append(
            "handoff authority_boundary.creates_release_authority must be false"
        )

    return _cross_check_result(
        name="handoff_matches_status_and_gate_sets",
        ok=failures == [],
        path=handoff_path,
        message="; ".join(failures) if failures else None,
        errors=errors,
    )

def _check_release_authority_manifest_matches_package_core(
    *,
    package_root: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    release_authority_path = _manifest_artifact_path(
        manifest,
        "release_authority_manifest",
    )
    status_path = _manifest_artifact_path(manifest, "status_artifact")
    policy_path = _manifest_artifact_path(manifest, "gate_policy")
    registry_path = _manifest_artifact_path(manifest, "gate_registry")
    gate_sets_path = _manifest_artifact_path(manifest, "materialized_gate_sets")

    if (
        release_authority_path is None
        or status_path is None
        or policy_path is None
        or registry_path is None
        or gate_sets_path is None
    ):
        return _cross_check_result(
            name="release_authority_manifest_matches_package_core",
            ok=False,
            path="release_authority/release_authority_manifest.json",
            message=(
                "package manifest must reference release_authority_manifest, "
                "status_artifact, gate_policy, gate_registry, and materialized_gate_sets"
            ),
            errors=errors,
        )

    release_authority, release_authority_error = _load_package_json_artifact(
        package_root,
        release_authority_path,
    )
    if release_authority_error is not None or release_authority is None:
        return _cross_check_result(
            name="release_authority_manifest_matches_package_core",
            ok=False,
            path=release_authority_path,
            message=(
                release_authority_error
                or f"could not load release authority artifact: {release_authority_path}"
            ),
            errors=errors,
        )

    gate_sets, gate_sets_error = _load_package_json_artifact(package_root, gate_sets_path)
    if gate_sets_error is not None or gate_sets is None:
        return _cross_check_result(
            name="release_authority_manifest_matches_package_core",
            ok=False,
            path=gate_sets_path,
            message=gate_sets_error or f"could not load gate sets: {gate_sets_path}",
            errors=errors,
        )

    status_file, status_error = _resolve_package_artifact(package_root, status_path)
    policy_file, policy_error = _resolve_package_artifact(package_root, policy_path)
    registry_file, registry_error = _resolve_package_artifact(package_root, registry_path)

    if status_error is not None or status_file is None:
        return _cross_check_result(
            name="release_authority_manifest_matches_package_core",
            ok=False,
            path=status_path,
            message=status_error or f"could not resolve status path: {status_path}",
            errors=errors,
        )

    if policy_error is not None or policy_file is None:
        return _cross_check_result(
            name="release_authority_manifest_matches_package_core",
            ok=False,
            path=policy_path,
            message=policy_error or f"could not resolve policy path: {policy_path}",
            errors=errors,
        )

    if registry_error is not None or registry_file is None:
        return _cross_check_result(
            name="release_authority_manifest_matches_package_core",
            ok=False,
            path=registry_path,
            message=registry_error or f"could not resolve registry path: {registry_path}",
            errors=errors,
        )

    status_sha = _sha256_file(status_file)
    policy_sha = _sha256_file(policy_file)
    registry_sha = _sha256_file(registry_file)

    failures: list[str] = []

    run_identity = release_authority.get("run_identity")
    if not isinstance(run_identity, dict):
        failures.append("release authority run_identity must be an object")
        run_identity = {}

    if run_identity.get("run_mode") != "prod":
        failures.append(
            f"release authority run_identity.run_mode must be 'prod', "
            f"found {run_identity.get('run_mode')!r}"
        )

    inputs = release_authority.get("inputs")
    if not isinstance(inputs, dict):
        failures.append("release authority inputs must be an object")
        inputs = {}

    status_input = inputs.get("status_json")
    if not isinstance(status_input, dict):
        failures.append("release authority inputs.status_json must be an object")
        status_input = {}

    if status_input.get("path") != status_path:
        failures.append(
            f"inputs.status_json.path mismatch: expected {status_path!r}, "
            f"found {status_input.get('path')!r}"
        )
    if status_input.get("sha256") != status_sha:
        failures.append(
            f"inputs.status_json.sha256 mismatch: expected {status_sha!r}, "
            f"found {status_input.get('sha256')!r}"
        )

    policy_input = inputs.get("gate_policy")
    if not isinstance(policy_input, dict):
        failures.append("release authority inputs.gate_policy must be an object")
        policy_input = {}

    if policy_input.get("path") != policy_path:
        failures.append(
            f"inputs.gate_policy.path mismatch: expected {policy_path!r}, "
            f"found {policy_input.get('path')!r}"
        )
    if policy_input.get("sha256") != policy_sha:
        failures.append(
            f"inputs.gate_policy.sha256 mismatch: expected {policy_sha!r}, "
            f"found {policy_input.get('sha256')!r}"
        )

    registry_input = inputs.get("gate_registry")
    if not isinstance(registry_input, dict):
        failures.append("release authority inputs.gate_registry must be an object")
        registry_input = {}

    if registry_input.get("path") != registry_path:
        failures.append(
            f"inputs.gate_registry.path mismatch: expected {registry_path!r}, "
            f"found {registry_input.get('path')!r}"
        )
    if registry_input.get("sha256") != registry_sha:
        failures.append(
            f"inputs.gate_registry.sha256 mismatch: expected {registry_sha!r}, "
            f"found {registry_input.get('sha256')!r}"
        )

    authority = release_authority.get("authority")
    if not isinstance(authority, dict):
        failures.append("release authority authority must be an object")
        authority = {}

    effective_required_gates = gate_sets.get("effective_required_gates")
        effective_required_gate_ids = _validate_gate_id_array(
        name="package gate_sets.effective_required_gates",
        value=effective_required_gates,
        failures=failures,
    )
    if effective_required_gate_ids is None:
        effective_required_gate_ids = []

    if authority.get("policy_set") != "required+release_required":
        failures.append(
            f"authority.policy_set must be 'required+release_required', "
            f"found {authority.get('policy_set')!r}"
        )

    if authority.get("release_required_materialized") is not True:
        failures.append("authority.release_required_materialized must be true")

        authority_effective_required_gates = _validate_gate_id_array(
        name="release_authority.authority.effective_required_gates",
        value=authority.get("effective_required_gates"),
        failures=failures,
    )

    if authority_effective_required_gates is not None:
        if authority_effective_required_gates != effective_required_gate_ids:
            failures.append(
                "authority.effective_required_gates does not match package gate sets"
            )

    evaluation = release_authority.get("evaluation")
    if not isinstance(evaluation, dict):
        failures.append("release authority evaluation must be an object")
        evaluation = {}

    required_gate_results = evaluation.get("required_gate_results")
    if not isinstance(required_gate_results, dict):
        failures.append("evaluation.required_gate_results must be an object")
        required_gate_results = {}

    expected_results = {gate_id: True for gate_id in effective_required_gate_ids}

    if required_gate_results != expected_results:
        failures.append(
            "evaluation.required_gate_results does not match effective required gates"
        )

    if evaluation.get("failed_required_gates") != []:
        failures.append(
            f"evaluation.failed_required_gates must be [], "
            f"found {evaluation.get('failed_required_gates')!r}"
        )

    if evaluation.get("missing_required_gates") != []:
        failures.append(
            f"evaluation.missing_required_gates must be [], "
            f"found {evaluation.get('missing_required_gates')!r}"
        )

    decision = release_authority.get("decision")
    if not isinstance(decision, dict):
        failures.append("release authority decision must be an object")
        decision = {}

    if decision.get("state") != "PASS":
        failures.append(
            f"decision.state must be 'PASS', found {decision.get('state')!r}"
        )

    if decision.get("fail_closed") is not True:
        failures.append("decision.fail_closed must be true")

    diagnostics = release_authority.get("diagnostics")
    if not isinstance(diagnostics, dict):
        failures.append("release authority diagnostics must be an object")
        diagnostics = {}

    if diagnostics.get("shadow_surfaces_non_normative") is not True:
        failures.append("diagnostics.shadow_surfaces_non_normative must be true")

    return _cross_check_result(
        name="release_authority_manifest_matches_package_core",
        ok=failures == [],
        path=release_authority_path,
        message="; ".join(failures) if failures else None,
        errors=errors,
    )

def _check_ci_outcome_and_publication_match_release_identity(
    *,
    package_root: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    ci_outcome_path = _manifest_artifact_path(manifest, "ci_outcome")
    publication_path = _manifest_artifact_path(manifest, "publication_snapshot")
    release_authority_path = _manifest_artifact_path(
        manifest,
        "release_authority_manifest",
    )

    if (
        ci_outcome_path is None
        or publication_path is None
        or release_authority_path is None
    ):
        return _cross_check_result(
            name="ci_outcome_and_publication_match_release_identity",
            ok=False,
            path="ci/ci_outcome.json",
            message=(
                "package manifest must reference ci_outcome, "
                "publication_snapshot, and release_authority_manifest"
            ),
            errors=errors,
        )

    ci_outcome, ci_error = _load_package_json_artifact(package_root, ci_outcome_path)
    if ci_error is not None or ci_outcome is None:
        return _cross_check_result(
            name="ci_outcome_and_publication_match_release_identity",
            ok=False,
            path=ci_outcome_path,
            message=ci_error or f"could not load CI outcome artifact: {ci_outcome_path}",
            errors=errors,
        )

    publication, publication_error = _load_package_json_artifact(
        package_root,
        publication_path,
    )
    if publication_error is not None or publication is None:
        return _cross_check_result(
            name="ci_outcome_and_publication_match_release_identity",
            ok=False,
            path=publication_path,
            message=(
                publication_error
                or f"could not load publication snapshot artifact: {publication_path}"
            ),
            errors=errors,
        )

    release_authority, release_authority_error = _load_package_json_artifact(
        package_root,
        release_authority_path,
    )
    if release_authority_error is not None or release_authority is None:
        return _cross_check_result(
            name="ci_outcome_and_publication_match_release_identity",
            ok=False,
            path=release_authority_path,
            message=(
                release_authority_error
                or f"could not load release authority artifact: {release_authority_path}"
            ),
            errors=errors,
        )

    failures: list[str] = []

    if ci_outcome.get("provider") != "github_actions":
        failures.append(
            f"ci_outcome.provider must be 'github_actions', "
            f"found {ci_outcome.get('provider')!r}"
        )

    if ci_outcome.get("gate_check_conclusion") != "success":
        failures.append(
            f"ci_outcome.gate_check_conclusion must be 'success', "
            f"found {ci_outcome.get('gate_check_conclusion')!r}"
        )

    run_attempt = ci_outcome.get("run_attempt")
    if not isinstance(run_attempt, int) or run_attempt < 1:
        failures.append(
            f"ci_outcome.run_attempt must be an integer >= 1, found {run_attempt!r}"
        )

    ci_boundary = ci_outcome.get("authority_boundary")
    ci_creates_release_authority = (
        ci_boundary.get("creates_release_authority")
        if isinstance(ci_boundary, dict)
        else None
    )
    if ci_creates_release_authority is not False:
        failures.append(
            "ci_outcome authority_boundary.creates_release_authority must be false"
        )

    run_identity = release_authority.get("run_identity")
    if not isinstance(run_identity, dict):
        failures.append("release authority run_identity must be an object")
        run_identity = {}

    if str(ci_outcome.get("run_id")) != str(run_identity.get("run_id")):
        failures.append(
            f"ci_outcome.run_id mismatch: expected {run_identity.get('run_id')!r}, "
            f"found {ci_outcome.get('run_id')!r}"
        )

    if str(ci_outcome.get("run_attempt")) != str(run_identity.get("attempt")):
        failures.append(
            f"ci_outcome.run_attempt mismatch: expected {run_identity.get('attempt')!r}, "
            f"found {ci_outcome.get('run_attempt')!r}"
        )

    if ci_outcome.get("commit_sha") != run_identity.get("git_sha"):
        failures.append(
            f"ci_outcome.commit_sha mismatch: expected {run_identity.get('git_sha')!r}, "
            f"found {ci_outcome.get('commit_sha')!r}"
        )

    if publication.get("creates_release_authority") is not False:
        failures.append("publication_snapshot.creates_release_authority must be false")

    if publication.get("git_sha") != ci_outcome.get("commit_sha"):
        failures.append(
            f"publication_snapshot.git_sha mismatch: "
            f"expected {ci_outcome.get('commit_sha')!r}, "
            f"found {publication.get('git_sha')!r}"
        )

    if publication.get("ci_outcome_url") != ci_outcome.get("run_url"):
        failures.append(
            f"publication_snapshot.ci_outcome_url mismatch: "
            f"expected {ci_outcome.get('run_url')!r}, "
            f"found {publication.get('ci_outcome_url')!r}"
        )

    manifest_package_id = manifest.get("package_id")
    if (
        isinstance(manifest_package_id, str)
        and publication.get("package_id") != manifest_package_id
    ):
        failures.append(
            f"publication_snapshot.package_id mismatch: "
            f"expected {manifest_package_id!r}, found {publication.get('package_id')!r}"
        )
        
    manifest_run_key = manifest.get("run_key")
    if isinstance(manifest_run_key, str) and publication.get("run_key") != manifest_run_key:
        failures.append(
            f"publication_snapshot.run_key mismatch: "
            f"expected {manifest_run_key!r}, found {publication.get('run_key')!r}"
        )

    return _cross_check_result(
        name="ci_outcome_and_publication_match_release_identity",
        ok=failures == [],
        path=ci_outcome_path,
        message="; ".join(failures) if failures else None,
        errors=errors,
    )


def _check_package_digests_cover_manifest_payload(
    *,
    package_root: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    digests_path = _manifest_artifact_path(manifest, "package_digests")

    if digests_path is None:
        return _cross_check_result(
            name="package_digests_cover_manifest_payload",
            ok=False,
            path="digests/package_digests.json",
            message="package manifest must reference package_digests",
            errors=errors,
        )

    digests, digests_error = _load_package_json_artifact(package_root, digests_path)
    if digests_error is not None or digests is None:
        return _cross_check_result(
            name="package_digests_cover_manifest_payload",
            ok=False,
            path=digests_path,
            message=digests_error or f"could not load digest manifest: {digests_path}",
            errors=errors,
        )

    artifacts = digests.get("artifacts")
    if not isinstance(artifacts, dict):
        return _cross_check_result(
            name="package_digests_cover_manifest_payload",
            ok=False,
            path=digests_path,
            message="package_digests artifacts must be an object",
            errors=errors,
        )

    expected_paths: list[str] = ["README.md"]

    for field in ARTIFACT_REF_FIELDS:
        if field == "package_digests":
            continue

        rel_path = _manifest_artifact_path(manifest, field)
        if rel_path is not None:
            expected_paths.append(rel_path)

    expected = set(expected_paths)
    actual = set(artifacts.keys())

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    failures: list[str] = []

    if missing:
        failures.append(
            "package_digests missing expected payload artifacts: " + ", ".join(missing)
        )

    if unexpected:
        failures.append(
            "package_digests contains unexpected artifact entries: "
            + ", ".join(unexpected)
        )

    return _cross_check_result(
        name="package_digests_cover_manifest_payload",
        ok=failures == [],
        path=digests_path,
        message="; ".join(failures) if failures else None,
        errors=errors,
    )

def _package_file_inventory(package_root: Path) -> set[str]:
    files: set[str] = set()

    for path in package_root.rglob("*"):
        if not (path.is_file() or path.is_symlink()):
            continue

        files.add(path.relative_to(package_root).as_posix())

    return files


def _check_package_inventory_matches_manifest(
    *,
    package_root: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    expected: set[str] = {
        "README.md",
        "package_manifest.json",
    }
    failures: list[str] = []

    for field in ARTIFACT_REF_FIELDS:
        rel_path = _manifest_artifact_path(manifest, field)

        if rel_path is None:
            continue

        if not _is_safe_relative_path(rel_path):
            failures.append(
                f"manifest field {field} has unsafe artifact path: {rel_path!r}"
            )
            continue

        expected.add(rel_path)

    actual = _package_file_inventory(package_root)

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    if missing:
        failures.append("package inventory missing expected files: " + ", ".join(missing))

    if unexpected:
        failures.append(
            "package inventory contains unexpected files: " + ", ".join(unexpected)
        )

    return _cross_check_result(
        name="package_inventory_matches_manifest",
        ok=failures == [],
        path="package_manifest.json",
        message="; ".join(failures) if failures else None,
        errors=errors,
    )

def _check_package_payload_files_are_regular_files(
    *,
    package_root: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    expected_paths: list[str] = [
        "README.md",
        "package_manifest.json",
    ]

    for field in ARTIFACT_REF_FIELDS:
        rel_path = _manifest_artifact_path(manifest, field)

        if rel_path is not None:
            expected_paths.append(rel_path)

    failures: list[str] = []

    for rel_path in sorted(set(expected_paths)):
        if not _is_safe_relative_path(rel_path):
            failures.append(f"unsafe package payload path: {rel_path!r}")
            continue

        artifact_path = package_root / rel_path

        if artifact_path.is_symlink():
            failures.append(
                f"package payload artifact must be a regular file, found symlink: {rel_path}"
            )
            continue

        if not artifact_path.is_file():
            failures.append(
                f"package payload artifact missing or not a regular file: {rel_path}"
            )

    return _cross_check_result(
        name="package_payload_files_are_regular_files",
        ok=failures == [],
        path="package_manifest.json",
        message="; ".join(failures) if failures else None,
        errors=errors,
    )


def _check_package_manifest_uses_canonical_layout(
    *,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    failures: list[str] = []

    for field, expected_path in CANONICAL_RA1_ARTIFACT_PATHS.items():
        rel_path = _manifest_artifact_path(manifest, field)

        if rel_path is None:
            failures.append(f"package manifest missing {field}.path")
            continue

        if rel_path != expected_path:
            failures.append(
                f"{field} path mismatch: expected {expected_path!r}, found {rel_path!r}"
            )

    return _cross_check_result(
        name="package_manifest_uses_canonical_layout",
        ok=failures == [],
        path="package_manifest.json",
        message="; ".join(failures) if failures else None,
        errors=errors,
    )

def _is_git_sha(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != 40:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _check_package_identity_matches_release_surfaces(
    *,
    package_root: Path,
    manifest: dict[str, Any],
    digests: dict[str, Any] | None,
    errors: list[str],
) -> dict[str, Any]:
    package_id = manifest.get("package_id")
    run_key = manifest.get("run_key")
    git_sha = manifest.get("git_sha")

    failures: list[str] = []

    if not isinstance(package_id, str) or not package_id:
        failures.append("package_manifest.package_id must be a non-empty string")

    if not isinstance(run_key, str) or not run_key:
        failures.append("package_manifest.run_key must be a non-empty string")

    if not _is_git_sha(git_sha):
        failures.append("package_manifest.git_sha must be a 40-character lowercase git SHA")

    if isinstance(digests, dict):
        digest_package_id = digests.get("package_id")
        if not isinstance(digest_package_id, str) or not digest_package_id:
            failures.append("package_digests.package_id must be a non-empty string")
        elif digest_package_id != package_id:
            failures.append(
                f"package_digests.package_id mismatch: "
                f"expected {package_id!r}, found {digest_package_id!r}"
            )
    else:
        failures.append("package_digests must be available for package identity check")

    release_authority_path = _manifest_artifact_path(
        manifest,
        "release_authority_manifest",
    )
    ci_outcome_path = _manifest_artifact_path(manifest, "ci_outcome")
    publication_path = _manifest_artifact_path(manifest, "publication_snapshot")

    release_authority: dict[str, Any] | None = None
    ci_outcome: dict[str, Any] | None = None
    publication: dict[str, Any] | None = None

    if release_authority_path is None:
        failures.append("package manifest must reference release_authority_manifest")
    else:
        release_authority, release_authority_error = _load_package_json_artifact(
            package_root,
            release_authority_path,
        )
        if release_authority_error is not None or release_authority is None:
            failures.append(
                release_authority_error
                or f"could not load release authority artifact: {release_authority_path}"
            )

    if ci_outcome_path is None:
        failures.append("package manifest must reference ci_outcome")
    else:
        ci_outcome, ci_error = _load_package_json_artifact(
            package_root,
            ci_outcome_path,
        )
        if ci_error is not None or ci_outcome is None:
            failures.append(
                ci_error or f"could not load CI outcome artifact: {ci_outcome_path}"
            )

    if publication_path is None:
        failures.append("package manifest must reference publication_snapshot")
    else:
        publication, publication_error = _load_package_json_artifact(
            package_root,
            publication_path,
        )
        if publication_error is not None or publication is None:
            failures.append(
                publication_error
                or f"could not load publication snapshot artifact: {publication_path}"
            )

    if release_authority is not None:
        run_identity = release_authority.get("run_identity")
        if not isinstance(run_identity, dict):
            failures.append("release_authority.run_identity must be an object")
            run_identity = {}

        if isinstance(git_sha, str) and run_identity.get("git_sha") != git_sha:
            failures.append(
                f"package_manifest.git_sha mismatch with "
                f"release_authority.run_identity.git_sha: "
                f"expected {git_sha!r}, found {run_identity.get('git_sha')!r}"
            )

    if ci_outcome is not None and isinstance(git_sha, str):
        if ci_outcome.get("commit_sha") != git_sha:
            failures.append(
                f"package_manifest.git_sha mismatch with ci_outcome.commit_sha: "
                f"expected {git_sha!r}, found {ci_outcome.get('commit_sha')!r}"
            )

    if publication is not None:
        if isinstance(package_id, str) and publication.get("package_id") != package_id:
            failures.append(
                f"package_manifest.package_id mismatch with "
                f"publication_snapshot.package_id: "
                f"expected {package_id!r}, found {publication.get('package_id')!r}"
            )

        if isinstance(run_key, str) and publication.get("run_key") != run_key:
            failures.append(
                f"package_manifest.run_key mismatch with publication_snapshot.run_key: "
                f"expected {run_key!r}, found {publication.get('run_key')!r}"
            )

        if isinstance(git_sha, str) and publication.get("git_sha") != git_sha:
            failures.append(
                f"package_manifest.git_sha mismatch with publication_snapshot.git_sha: "
                f"expected {git_sha!r}, found {publication.get('git_sha')!r}"
            )

    return _cross_check_result(
        name="package_identity_matches_release_surfaces",
        ok=failures == [],
        path="package_manifest.json",
        message="; ".join(failures) if failures else None,
        errors=errors,
    )


def verify_package(package_root: Path) -> dict[str, Any]:
    package_root = package_root.resolve()

    errors: list[str] = []
    warnings: list[str] = []
    schemas_validated: list[dict[str, Any]] = []
    artifact_digests_checked: list[dict[str, Any]] = []
    cross_artifact_checks: list[dict[str, Any]] = []

    manifest_path = package_root / "package_manifest.json"
    digests_path = package_root / "digests" / "package_digests.json"

    manifest, manifest_error = _read_json(manifest_path)
    if manifest_error is not None:
        errors.append(f"package_manifest.json parse error: {manifest_error}")

    digests, digests_error = _read_json(digests_path)
    if digests_error is not None:
        errors.append(f"digests/package_digests.json parse error: {digests_error}")

    schemas_validated.append(
        _schema_check(
            artifact_path="package_manifest.json",
            schema_path=PACKAGE_MANIFEST_SCHEMA_PATH,
            instance=manifest,
            schema_file=PACKAGE_MANIFEST_SCHEMA,
            errors=errors,
        )
    )
    schemas_validated.append(
        _schema_check(
            artifact_path="digests/package_digests.json",
            schema_path=PACKAGE_DIGESTS_SCHEMA_PATH,
            instance=digests,
            schema_file=PACKAGE_DIGESTS_SCHEMA,
            errors=errors,
        )
    )

    if manifest is not None:
        for field in ARTIFACT_REF_FIELDS:
            if field not in manifest:
                continue

            artifact_ref = manifest.get(field)
            if not isinstance(artifact_ref, dict):
                errors.append(f"{field} must be an artifact reference object")
                continue

            rel_path = artifact_ref.get("path")
            expected_sha256 = artifact_ref.get("sha256")

            if not isinstance(rel_path, str) or not isinstance(expected_sha256, str):
                errors.append(f"{field} must contain string path and sha256")
                continue

            artifact_digests_checked.append(
                _digest_check(
                    package_root=package_root,
                    artifact_path=rel_path,
                    expected_sha256=expected_sha256,
                    source="package_manifest",
                    errors=errors,
                )
            )

        for field, schema_path, schema_file in ARTIFACT_SCHEMA_TARGETS:
            artifact_ref = manifest.get(field)

            if not isinstance(artifact_ref, dict):
                continue

            rel_path = artifact_ref.get("path")

            if not isinstance(rel_path, str):
                message = f"{field} must contain string path"
                errors.append(message)
                schemas_validated.append(
                    {
                        "artifact_path": "_invalid_artifact_path",
                        "schema_path": schema_path,
                        "ok": False,
                        "message": message,
                    }
                )
                continue

            artifact_obj, artifact_error = _load_package_json_artifact(
                package_root,
                rel_path,
            )

            if artifact_error is not None:
                schemas_validated.append(
                    {
                        "artifact_path": _report_safe_path(rel_path),
                        "schema_path": schema_path,
                        "ok": False,
                        "message": artifact_error,
                    }
                )
                errors.append(f"{rel_path} could not be loaded: {artifact_error}")
                continue

            schemas_validated.append(
                _schema_check(
                    artifact_path=_report_safe_path(rel_path),
                    schema_path=schema_path,
                    instance=artifact_obj,
                    schema_file=schema_file,
                    errors=errors,
                )
            )

        cross_artifact_checks.append(
            _check_materialized_gate_sets_match_policy(
                package_root=package_root,
                manifest=manifest,
                errors=errors,
            )
        )
        cross_artifact_checks.append(
            _check_status_satisfies_effective_required_gates(
                package_root=package_root,
                manifest=manifest,
                errors=errors,
            )
        )
        cross_artifact_checks.append(
            _check_handoff_matches_status_and_gate_sets(
                package_root=package_root,
                manifest=manifest,
                errors=errors,
            )
        )
        cross_artifact_checks.append(
            _check_release_authority_manifest_matches_package_core(
                package_root=package_root,
                manifest=manifest,
                errors=errors,
            )
        )
        cross_artifact_checks.append(
            _check_ci_outcome_and_publication_match_release_identity(
                package_root=package_root,
                manifest=manifest,
                errors=errors,
            )
        )
        cross_artifact_checks.append(
            _check_package_digests_cover_manifest_payload(
                package_root=package_root,
                manifest=manifest,
                errors=errors,
            )
        )
        cross_artifact_checks.append(
            _check_package_inventory_matches_manifest(
                package_root=package_root,
                manifest=manifest,
                errors=errors,
            )
        )
        cross_artifact_checks.append(
            _check_package_payload_files_are_regular_files(
                package_root=package_root,
                manifest=manifest,
                errors=errors,
            )
        )
        cross_artifact_checks.append(
            _check_package_manifest_uses_canonical_layout(
                manifest=manifest,
                errors=errors,
            )
        )
        cross_artifact_checks.append(
            _check_package_identity_matches_release_surfaces(
                package_root=package_root,
                manifest=manifest,
                digests=digests,
                errors=errors,
            )
        )

        authority_boundary = manifest.get("authority_boundary")
        creates_release_authority = (
            authority_boundary.get("creates_release_authority")
            if isinstance(authority_boundary, dict)
            else None
        )
        cross_artifact_checks.append(
            _check_authority_boundary(
                name="package_manifest_authority_boundary",
                path="package_manifest.json",
                creates_release_authority=creates_release_authority,
                errors=errors,
            )
        )

    if digests is not None:
        artifacts = digests.get("artifacts")
        if isinstance(artifacts, dict):
            for rel_path, expected_sha256 in artifacts.items():
                if not isinstance(rel_path, str) or not isinstance(expected_sha256, str):
                    errors.append(
                        "digest manifest artifacts must map string path to string sha256"
                    )
                    continue

                artifact_digests_checked.append(
                    _digest_check(
                        package_root=package_root,
                        artifact_path=rel_path,
                        expected_sha256=expected_sha256,
                        source="package_digests",
                        errors=errors,
                    )
                )

        authority_boundary = digests.get("authority_boundary")
        creates_release_authority = (
            authority_boundary.get("creates_release_authority")
            if isinstance(authority_boundary, dict)
            else None
        )
        cross_artifact_checks.append(
            _check_authority_boundary(
                name="package_digests_authority_boundary",
                path="digests/package_digests.json",
                creates_release_authority=creates_release_authority,
                errors=errors,
            )
        )

    cross_artifact_checks.append(
        _check_package_id_consistency(
            manifest=manifest,
            digests=digests,
            errors=errors,
        )
    )

    report: dict[str, Any] = {
        "schema": "pulse_ref_package_verifier_report_v0",
        "ok": len(errors) == 0,
        "package_root": str(package_root),
        "checked_utc": _utc_now(),
        "schemas_validated": schemas_validated,
        "artifact_digests_checked": artifact_digests_checked,
        "cross_artifact_checks": cross_artifact_checks,
        "warnings": warnings,
        "errors": errors,
        "authority_boundary": {
            "verifier_role": "external_reconstruction_check",
            "creates_release_authority": False,
        },
    }

    if manifest is not None:
        for key in ("package_id", "run_key", "git_sha"):
            value = manifest.get(key)
            if isinstance(value, str):
                report[key] = value

    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a PULSE-REF RA1 release-reference package."
    )
    parser.add_argument(
        "--package-root",
        required=True,
        help="Path to the RA1 package root.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path to write the verifier report JSON.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    package_root = Path(args.package_root)
    out_path = Path(args.out)

    report = verify_package(package_root)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, sort_keys=True))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
