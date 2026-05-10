#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[1]

PACKAGE_MANIFEST_SCHEMA = (
    REPO_ROOT / "schemas" / "pulse_ref_release_reference_package_v0.schema.json"
)
PACKAGE_DIGESTS_SCHEMA = (
    REPO_ROOT / "schemas" / "pulse_ref_package_digests_v0.schema.json"
)


PACKAGE_MANIFEST_SCHEMA_PATH = "schemas/pulse_ref_release_reference_package_v0.schema.json"
PACKAGE_DIGESTS_SCHEMA_PATH = "schemas/pulse_ref_package_digests_v0.schema.json"


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


def _package_path(package_root: Path, rel_path: str) -> Path:
    return package_root / rel_path


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


def _digest_check(
    *,
    package_root: Path,
    artifact_path: str,
    expected_sha256: str,
    source: str,
    errors: list[str],
) -> dict[str, Any]:
    if not _is_safe_relative_path(artifact_path):
        message = f"unsafe artifact path: {artifact_path!r}"
        errors.append(message)
        return {
            "artifact_path": artifact_path if isinstance(artifact_path, str) else "<invalid>",
            "expected_sha256": expected_sha256,
            "actual_sha256": None,
            "ok": False,
            "source": source,
            "message": message,
        }

    actual_sha256 = _sha256_file(_package_path(package_root, artifact_path))
    ok = actual_sha256 == expected_sha256

    result: dict[str, Any] = {
        "artifact_path": artifact_path,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual_sha256,
        "ok": ok,
        "source": source,
    }

    if not ok:
        message = (
            f"{artifact_path} digest mismatch: "
            f"expected={expected_sha256} actual={actual_sha256}"
        )
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
                    errors.append("digest manifest artifacts must map string path to string sha256")
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
