#!/usr/bin/env python3
"""Validate schema-aligned PULSE-REF packet artifacts.

This checker validates canonical packet artifact payloads against the existing
PULSE-REF schemas and performs lightweight cross-checks needed before future
schema-aligned builder work.

It does not create release authority.

It does not validate release-grade evidence.

It does not run RA1.

It checks packet artifact shape and reconstruction readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_TARGETS = {
    "package_manifest.json": "schemas/pulse_ref_release_reference_package_v0.schema.json",
    "gates/materialized_gate_sets.json": "schemas/pulse_ref_materialized_gate_sets_v0.schema.json",
    "handoff/operator_handoff_report.json": "schemas/pulse_ref_operator_handoff_report_v0.schema.json",
    "ci/ci_outcome.json": "schemas/pulse_ref_ci_outcome_v0.schema.json",
    "digests/package_digests.json": "schemas/pulse_ref_package_digests_v0.schema.json",
}

OPTIONAL_SCHEMA_TARGETS = {
    "publication/publication_snapshot.json": "schemas/pulse_ref_publication_snapshot_v0.schema.json",
}

RELEASE_AUTHORITY_CHECKER = (
    ROOT / "PULSE_safe_pack_v0" / "tools" / "check_release_authority_manifest_v0.py"
)
RELEASE_AUTHORITY_SCHEMA = ROOT / "schemas" / "release_authority_v0.schema.json"


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} did not contain a JSON object")
    return data


def _load_schema(path: Path) -> dict[str, Any]:
    return _load_json(path)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_json_schema(
    instance_path: Path,
    schema_path: Path,
    display_path: str,
) -> list[str]:
    schema = _load_schema(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    instance = _load_json(instance_path)
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )

    return [
        f"{display_path}: {list(error.absolute_path)}: {error.message}"
        for error in errors
    ]


def _validate_release_authority_manifest(packet_root: Path) -> list[str]:
    manifest_path = packet_root / "release_authority" / "release_authority_manifest.json"

    result = subprocess.run(
        [
            sys.executable,
            str(RELEASE_AUTHORITY_CHECKER),
            "--manifest",
            str(manifest_path),
            "--schema",
            str(RELEASE_AUTHORITY_SCHEMA),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode == 0:
        return []

    return [
        "release_authority/release_authority_manifest.json: "
        + (result.stderr.strip() or result.stdout.strip() or "release authority check failed")
    ]


def _validate_required_paths(packet_root: Path) -> list[str]:
    required = sorted(
        set(SCHEMA_TARGETS)
        | {
            "status/status.json",
            "policy/pulse_gate_policy_v0.yml",
            "policy/pulse_gate_registry_v0.yml",
            "release_authority/release_authority_manifest.json",
        }
    )

    errors: list[str] = []
    for rel_path in required:
        if not (packet_root / rel_path).is_file():
            errors.append(f"missing required packet artifact: {rel_path}")

    return errors


def _validate_schema_targets(packet_root: Path) -> list[str]:
    errors: list[str] = []

    for rel_path, schema_rel in SCHEMA_TARGETS.items():
        artifact = packet_root / rel_path
        if not artifact.is_file():
            continue
        errors.extend(_validate_json_schema(artifact, ROOT / schema_rel, rel_path))

    for rel_path, schema_rel in OPTIONAL_SCHEMA_TARGETS.items():
        artifact = packet_root / rel_path
        if artifact.is_file():
            errors.extend(_validate_json_schema(artifact, ROOT / schema_rel, rel_path))

    if (packet_root / "release_authority/release_authority_manifest.json").is_file():
        errors.extend(_validate_release_authority_manifest(packet_root))

    return errors


def _validate_policy_derived_materialized_gates(packet_root: Path) -> list[str]:
    errors: list[str] = []

    policy_path = packet_root / "policy/pulse_gate_policy_v0.yml"
    gate_sets_path = packet_root / "gates/materialized_gate_sets.json"

    if not policy_path.is_file() or not gate_sets_path.is_file():
        return errors

    # Reuse the repository policy materializer instead of reimplementing the
    # policy contract here.
    def materialize(gate_set: str) -> list[str]:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "policy_to_require_args.py"),
                "--policy",
                str(policy_path),
                "--set",
                gate_set,
                "--format",
                "newline",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr.strip() or result.stdout.strip())
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    try:
        required = materialize("required")
        release_required = materialize("release_required")
    except AssertionError as exc:
        return [f"policy materialization failed: {exc}"]

    gate_sets = _load_json(gate_sets_path)

    expected_effective = list(dict.fromkeys(required + release_required))

    if gate_sets.get("policy_path") != "policy/pulse_gate_policy_v0.yml":
        errors.append("gates/materialized_gate_sets.json: policy_path mismatch")

    if gate_sets.get("policy_sha256") != _sha256_file(policy_path):
        errors.append("gates/materialized_gate_sets.json: policy_sha256 mismatch")

    sets = gate_sets.get("sets")
    if not isinstance(sets, dict):
        errors.append("gates/materialized_gate_sets.json: sets must be object")
        return errors

    if sets.get("required") != required:
        errors.append("gates/materialized_gate_sets.json: required set is not policy-derived")

    if sets.get("release_required") != release_required:
        errors.append("gates/materialized_gate_sets.json: release_required set is not policy-derived")

    if gate_sets.get("effective_required_gates") != expected_effective:
        errors.append("gates/materialized_gate_sets.json: effective_required_gates mismatch")

    return errors


def _validate_artifact_ref(
    *,
    packet_root: Path,
    ref: Any,
    field: str,
    optional: bool,
) -> list[str]:
    errors: list[str] = []

    label = "optional artifact ref" if optional else "artifact ref"

    if not isinstance(ref, dict):
        errors.append(f"package_manifest.json: invalid {label} {field}")
        return errors

    rel_path = ref.get("path")
    expected_sha = ref.get("sha256")

    if not isinstance(rel_path, str) or not isinstance(expected_sha, str):
        errors.append(f"package_manifest.json: invalid {label} {field}")
        return errors

    artifact = packet_root / rel_path
    if not artifact.is_file():
        errors.append(
            f"package_manifest.json: {label} {field} points to missing {rel_path}"
        )
        return errors

    actual_sha = _sha256_file(artifact)
    if actual_sha != expected_sha:
        errors.append(f"package_manifest.json: sha256 mismatch for {field}")

    return errors


def _is_safe_packet_relative_path(rel_path: str) -> bool:
    if not rel_path:
        return False

    if "\\" in rel_path:
        return False

    path = Path(rel_path)

    if path.is_absolute():
        return False

    return ".." not in path.parts


def _validate_artifact_ref(
    *,
    packet_root: Path,
    ref: Any,
    field: str,
    optional: bool,
    expected_path: str | None = None,
) -> list[str]:
    errors: list[str] = []

    label = "optional artifact ref" if optional else "artifact ref"

    if not isinstance(ref, dict):
        errors.append(f"package_manifest.json: invalid {label} {field}")
        return errors

    rel_path = ref.get("path")
    expected_sha = ref.get("sha256")

    if not isinstance(rel_path, str) or not isinstance(expected_sha, str):
        errors.append(f"package_manifest.json: invalid {label} {field}")
        return errors

    if not _is_safe_packet_relative_path(rel_path):
        errors.append(f"package_manifest.json: unsafe {label} {field} path {rel_path!r}")
        return errors

    if expected_path is not None and rel_path != expected_path:
        errors.append(
            f"package_manifest.json: {field} must reference canonical path "
            f"{expected_path}, got {rel_path}"
        )
        return errors

    packet_root_resolved = packet_root.resolve()
    artifact = (packet_root_resolved / rel_path).resolve()

    try:
        artifact.relative_to(packet_root_resolved)
    except ValueError:
        errors.append(f"package_manifest.json: unsafe {label} {field} path {rel_path!r}")
        return errors

    if not artifact.is_file():
        errors.append(
            f"package_manifest.json: {label} {field} points to missing {rel_path}"
        )
        return errors

    actual_sha = _sha256_file(artifact)
    if actual_sha != expected_sha:
        errors.append(f"package_manifest.json: sha256 mismatch for {field}")

    return errors


def _validate_package_manifest_refs(packet_root: Path) -> list[str]:
    manifest_path = packet_root / "package_manifest.json"
    if not manifest_path.is_file():
        return []

    manifest = _load_json(manifest_path)

    ref_fields = [
        "status_artifact",
        "gate_policy",
        "gate_registry",
        "materialized_gate_sets",
        "operator_handoff_report",
        "release_authority_manifest",
        "ci_outcome",
        "package_digests",
    ]

    optional_ref_fields = {
        "publication_snapshot": "publication/publication_snapshot.json",
    }

    errors: list[str] = []

    for field in ref_fields:
        ref = manifest.get(field)
        if not isinstance(ref, dict):
            errors.append(f"package_manifest.json: missing artifact ref {field}")
            continue

        errors.extend(
            _validate_artifact_ref(
                packet_root=packet_root,
                ref=ref,
                field=field,
                optional=False,
            )
        )

    for field, expected_path in optional_ref_fields.items():
        if field not in manifest:
            continue

        errors.extend(
            _validate_artifact_ref(
                packet_root=packet_root,
                ref=manifest.get(field),
                field=field,
                optional=True,
                expected_path=expected_path,
            )
        )

    return errors



def _validate_package_digest_refs(packet_root: Path) -> list[str]:
    digest_path = packet_root / "digests/package_digests.json"
    if not digest_path.is_file():
        return []

    digest_manifest = _load_json(digest_path)
    artifacts = digest_manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return ["digests/package_digests.json: artifacts must be object"]

    errors: list[str] = []
    for rel_path, expected_sha in artifacts.items():
        if not isinstance(rel_path, str) or not isinstance(expected_sha, str):
            errors.append("digests/package_digests.json: artifacts entries must be path -> sha256")
            continue

        artifact = packet_root / rel_path
        if not artifact.is_file():
            errors.append(f"digests/package_digests.json: missing artifact {rel_path}")
            continue

        if _sha256_file(artifact) != expected_sha:
            errors.append(f"digests/package_digests.json: sha256 mismatch for {rel_path}")

    return errors


def validate(packet_root: Path) -> list[str]:
    errors: list[str] = []

    errors.extend(_validate_required_paths(packet_root))
    errors.extend(_validate_schema_targets(packet_root))
    errors.extend(_validate_policy_derived_materialized_gates(packet_root))
    errors.extend(_validate_package_manifest_refs(packet_root))
    errors.extend(_validate_package_digest_refs(packet_root))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", required=True, type=Path)
    args = parser.parse_args()

    packet_root = args.packet_root.resolve()
    errors = validate(packet_root)

    if errors:
        print("ERROR: PULSE-REF schema-aligned packet validation failed")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OK: PULSE-REF schema-aligned packet artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
