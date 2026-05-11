#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
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
        required = list(policy["gates"]["required"])
        release_required = list(policy["gates"]["release_required"])
    except Exception as exc:
        return _cross_check_result(
            name="materialized_gate_sets_match_policy",
            ok=False,
            path=policy_path,
            message=f"packaged policy does not expose required gate sets: {exc}",
            errors=errors,
        )

    effective = _unique_preserve_order(required + release_required)

    mismatches: list[str] = []

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
        if sets.get("required") != required:
            mismatches.append("sets.required does not match packaged policy gates.required")
        if sets.get("release_required") != release_required:
            mismatches.append(
                "sets.release_required does not match packaged policy gates.release_required"
            )

    if gate_sets.get("effective_required_gates") != effective:
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

    if not isinstance(effective_required_gates, list):
        failures.append("effective_required_gates must be an array")
        effective_required_gates = []

    missing = [
        gate_id
        for gate_id in effective_required_gates
        if gate_id not in gates
    ]
    false_gates = [
        gate_id
        for gate_id in effective_required_gates
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
