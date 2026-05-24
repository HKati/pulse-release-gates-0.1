#!/usr/bin/env python3
"""Check the PULSE-REF evidence packet layout skeleton.

This checker validates the physical layout skeleton only.

It does not validate release-grade evidence.

It does not run the RA1 verifier.

It does not authorize, block, override, or create release authority.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

CANONICAL_PATHS = [
    "README.md",
    "package_manifest.json",
    "status/status.json",
    "policy/pulse_gate_policy_v0.yml",
    "policy/pulse_gate_registry_v0.yml",
    "gates/materialized_gate_sets.json",
    "ci/ci_outcome.json",
    "release_authority/release_authority_manifest.json",
    "audit/release_authority_audit_bundle/README.md",
    "audit/release_authority_audit_bundle/report_card.html",
    "audit/release_authority_audit_bundle/status.json",
    "audit/release_authority_audit_bundle/release_authority_manifest.json",
    "digests/package_digests.json",
    "handoff/operator_handoff_report.json",
    "publication/publication_snapshot.json",
    "field/field_point_authority_map_v0.json",
    "admissibility/evidence_fold_in_admissibility_v0.json",
    "external/summaries/README.md",
    "hpc/hpc_evidence_bundle_v0.json",
    "recognition/recognition_surface_drift_v0.json",
    "reconstruction/reconstruction_instructions.md",
]

JSON_PLACEHOLDER_PATHS = [
    rel_path
    for rel_path in CANONICAL_PATHS
    if rel_path.endswith(".json") and rel_path != "package_manifest.json"
]

YAML_PLACEHOLDER_PATHS = [
    "policy/pulse_gate_policy_v0.yml",
    "policy/pulse_gate_registry_v0.yml",
]


def _is_safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if "\\" in value:
        return False

    path = Path(value)

    if path.is_absolute():
        return False
    if any(part == ".." for part in path.parts):
        return False

    return True


def _load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path}: JSON parse failed: {exc}")
        return None

    if not isinstance(obj, dict):
        errors.append(f"{path}: JSON value must be an object")
        return None

    return obj
def _read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"{path}: text read failed: {exc}")
        return ""

ALLOWED_AUTHORITY_DISCLAIMER_PHRASES = [
    "does not authorize, block, override, or create release authority",
    "does not create release authority",
    "not release-grade evidence",
    "not a release-grade audit bundle",
    "not a release-grade report card",
    "does not satisfy release-grade external evidence requirements",
    "not reconstructable release-grade evidence",
]

CONTRADICTORY_AUTHORITY_PATTERNS = [
    (
         re.compile(r"\bcreates?\s+release[-\s]authority\b", re.IGNORECASE),
        "must not claim it creates release authority",
    ),
    (
         re.compile(r"\bcan\s+create\s+release[-\s]authority\b", re.IGNORECASE),
        "must not claim it can create release authority",
    ),
    (
         re.compile(r"\bmay\s+create\s+release[-\s]authority\b", re.IGNORECASE),
        "must not claim it may create release authority",
    ),
    (
         re.compile(r"\bwill\s+create\s+release[-\s]authority\b", re.IGNORECASE),
        "must not claim it will create release authority",
    ),
    (
        re.compile(r"\bis\s+release-grade\s+evidence\b", re.IGNORECASE),
        "must not claim it is release-grade evidence",
    ),
        re.compile(r"\bis\s+a\s+release-grade\s+audit\s+bundle\b", re.IGNORECASE),
        "must not claim it is a release-grade audit bundle",
    ),
    (
        re.compile(r"\bis\s+a\s+release-grade\s+report\s+card\b", re.IGNORECASE),
        "must not claim it is a release-grade report card",
    ),
    (
        re.compile(
            r"\bsatisfies\s+release-grade\s+external\s+evidence\s+requirements\b",
            re.IGNORECASE,
        ),
        "must not claim it satisfies release-grade external evidence requirements",
    ),
    (
         re.compile(
            r"\bis\s+reconstructable\s+release-grade\s+evidence\b",
            re.IGNORECASE,
        ),
        "must not claim it is reconstructable release-grade evidence",
    ),
]


def _load_yaml(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path}: YAML parse failed: {exc}")
        return None

    if not isinstance(obj, dict):
        errors.append(f"{path}: YAML value must be an object")
        return None

    return obj


def _text_without_allowed_disclaimers(text: str) -> str:
    lowered = text.lower()

    for phrase in ALLOWED_AUTHORITY_DISCLAIMER_PHRASES:
        lowered = lowered.replace(phrase.lower(), "")

    return lowered


def _check_no_contradictory_authority_claims(
    *,
    rel_path: str,
    text: str,
    errors: list[str],
) -> None:
    checked = _text_without_allowed_disclaimers(text)

    for pattern, message in CONTRADICTORY_AUTHORITY_PATTERNS:
        if pattern.search(checked):
            errors.append(
                f"{rel_path}: contradictory authority claim detected: {message}"
            )


def _package_file_inventory(packet_root: Path) -> set[str]:
    files: set[str] = set()

    for path in packet_root.rglob("*"):
        if not (path.is_file() or path.is_symlink()):
            continue
        files.add(path.relative_to(packet_root).as_posix())

    return files


def _check_regular_file(packet_root: Path, rel_path: str, errors: list[str]) -> None:
    path = packet_root / rel_path

    if path.is_symlink():
        errors.append(f"{rel_path}: must be a regular file, found symlink")
        return

    if not path.is_file():
        errors.append(f"{rel_path}: missing or not a regular file")


def _check_authority_boundary(
    *,
    rel_path: str,
    obj: dict[str, Any],
    errors: list[str],
) -> None:
    if obj.get("creates_release_authority") is not False:
        errors.append(f"{rel_path}: must set creates_release_authority=false")

    boundary = obj.get("authority_boundary")
    if boundary is not None:
        if not isinstance(boundary, dict):
            errors.append(f"{rel_path}: authority_boundary must be an object")
            return

        if boundary.get("creates_release_authority") is not False:
            errors.append(
                f"{rel_path}: authority_boundary.creates_release_authority must be false"
            )


def _check_package_manifest(packet_root: Path, errors: list[str]) -> None:
    rel_path = "package_manifest.json"
    manifest = _load_json(packet_root / rel_path, errors)

    if manifest is None:
        return

    expected_fields = {
        "schema": "pulse_ref_evidence_packet_layout_skeleton_v0",
        "fixture_type": "layout_skeleton",
        "package_id": "pulse-ref-layout-skeleton-v0",
        "release_grade_evidence": False,
        "creates_release_authority": False,
    }

    for key, expected in expected_fields.items():
        if manifest.get(key) != expected:
            errors.append(
                f"{rel_path}: {key} must be {expected!r}, "
                f"found {manifest.get(key)!r}"
            )

    _check_authority_boundary(rel_path=rel_path, obj=manifest, errors=errors)

    canonical_paths = manifest.get("canonical_paths")
    if not isinstance(canonical_paths, list):
        errors.append(f"{rel_path}: canonical_paths must be an array")
        return

    if not all(isinstance(item, str) for item in canonical_paths):
        errors.append(f"{rel_path}: canonical_paths must contain only strings")
        return

    unsafe = [
        item
        for item in canonical_paths
        if not _is_safe_relative_path(item)
    ]
    if unsafe:
        errors.append(f"{rel_path}: unsafe canonical paths: {', '.join(unsafe)}")

    duplicates = sorted(
        {
            item
            for item in canonical_paths
            if canonical_paths.count(item) > 1
        }
    )
    if duplicates:
        errors.append(f"{rel_path}: duplicate canonical paths: {', '.join(duplicates)}")

    expected = set(CANONICAL_PATHS)
    actual = set(canonical_paths)

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    if missing or unexpected:
        detail: list[str] = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if unexpected:
            detail.append("unexpected: " + ", ".join(unexpected))
        errors.append(f"{rel_path}: canonical_paths mismatch ({'; '.join(detail)})")


def _check_json_placeholders(packet_root: Path, errors: list[str]) -> None:
    for rel_path in JSON_PLACEHOLDER_PATHS:
        obj = _load_json(packet_root / rel_path, errors)

        if obj is None:
            continue

        expected_fields = {
            "schema": "pulse_ref_evidence_packet_layout_placeholder_v0",
            "fixture_type": "layout_skeleton_placeholder",
            "release_grade_evidence": False,
            "creates_release_authority": False,
            "placeholder_path": rel_path,
        }

        for key, expected in expected_fields.items():
            if obj.get(key) != expected:
                errors.append(
                    f"{rel_path}: {key} must be {expected!r}, "
                    f"found {obj.get(key)!r}"
                )

        _check_authority_boundary(rel_path=rel_path, obj=obj, errors=errors)


def _check_yaml_placeholders(packet_root: Path, errors: list[str]) -> None:
    for rel_path in YAML_PLACEHOLDER_PATHS:
        obj = _load_yaml(packet_root / rel_path, errors)

        if obj is None:
            continue

        expected_fields = {
            "schema": "pulse_ref_evidence_packet_layout_placeholder_v0",
            "fixture_type": "layout_skeleton_placeholder",
            "release_grade_evidence": False,
            "creates_release_authority": False,
            "placeholder_path": rel_path,
        }

        for key, expected in expected_fields.items():
            if obj.get(key) != expected:
                errors.append(
                    f"{rel_path}: {key} must be {expected!r}, "
                    f"found {obj.get(key)!r}"
                )

        boundary = obj.get("authority_boundary")
        if not isinstance(boundary, dict):
            errors.append(f"{rel_path}: authority_boundary must be an object")
        elif boundary.get("creates_release_authority") is not False:
            errors.append(
                f"{rel_path}: authority_boundary.creates_release_authority must be false"
            )

        _check_authority_boundary(rel_path=rel_path, obj=obj, errors=errors)


def _check_readme_boundaries(packet_root: Path, errors: list[str]) -> None:
    root_readme_path = "README.md"
    root_readme = _read_text(packet_root / root_readme_path, errors)

    root_required = [
        "layout skeleton fixture",
        "not release-grade evidence",
        "does not authorize, block, override, or create release authority",
        "recorded release evidence",
        "status.json",
        "declared gate policy",
        "materialized required gate set",
        "strict fail-closed CI gate enforcement",
    ]

    for token in root_required:
        if token not in root_readme:
            errors.append(f"{root_readme_path}: missing authority-boundary token: {token}")

    _check_no_contradictory_authority_claims(
        rel_path=root_readme_path,
        text=root_readme,
        errors=errors,
    )

    audit_readme_path = "audit/release_authority_audit_bundle/README.md"
    audit_readme = _read_text(packet_root / audit_readme_path, errors)

    audit_required = [
        "not a release-grade audit bundle",
        "does not create release authority",
    ]

    for token in audit_required:
        if token not in audit_readme:
            errors.append(f"{audit_readme_path}: missing token: {token}")

    _check_no_contradictory_authority_claims(
        rel_path=audit_readme_path,
        text=audit_readme,
        errors=errors,
    )

    external_readme_path = "external/summaries/README.md"
    external_readme = _read_text(packet_root / external_readme_path, errors)

    external_required = [
        "does not contain canonical detector evidence",
        "does not satisfy release-grade external evidence requirements",
    ]

    for token in external_required:
        if token not in external_readme:
            errors.append(f"{external_readme_path}: missing token: {token}")

    _check_no_contradictory_authority_claims(
        rel_path=external_readme_path,
        text=external_readme,
        errors=errors,
    )

    reconstruction_path = "reconstruction/reconstruction_instructions.md"
    reconstruction = _read_text(packet_root / reconstruction_path, errors)

    reconstruction_required = [
        "This skeleton is not reconstructable release-grade evidence.",
        "This skeleton does not create release authority.",
    ]

    for token in reconstruction_required:
        if token not in reconstruction:
            errors.append(f"{reconstruction_path}: missing token: {token}")

    _check_no_contradictory_authority_claims(
        rel_path=reconstruction_path,
        text=reconstruction,
        errors=errors,
    )


def _check_report_card_placeholder(packet_root: Path, errors: list[str]) -> None:
    rel_path = "audit/release_authority_audit_bundle/report_card.html"
    text = _read_text(packet_root / rel_path, errors)

    required = [
        "not a release-grade report card",
        "does not create release authority",
    ]

    for token in required:
        if token not in text:
            errors.append(f"{rel_path}: missing token: {token}")

    _check_no_contradictory_authority_claims(
        rel_path=rel_path,
        text=text,
        errors=errors,
    )


def check_packet_root(packet_root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not packet_root.is_dir():
        return False, [f"packet root missing or not a directory: {packet_root}"]

    inventory = _package_file_inventory(packet_root)

    expected = set(CANONICAL_PATHS)
    actual = set(inventory)

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    if missing:
        errors.append("missing canonical paths: " + ", ".join(missing))

    if unexpected:
        errors.append("unexpected files in skeleton: " + ", ".join(unexpected))

    for rel_path in CANONICAL_PATHS:
        _check_regular_file(packet_root, rel_path, errors)

    _check_package_manifest(packet_root, errors)
    _check_json_placeholders(packet_root, errors)
    _check_yaml_placeholders(packet_root, errors)
    _check_readme_boundaries(packet_root, errors)
    _check_report_card_placeholder(packet_root, errors)

    return errors == [], errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a PULSE-REF evidence packet layout skeleton."
    )
    parser.add_argument(
        "--packet-root",
        required=True,
        help="Path to pulse_ref_evidence_packet_v0 skeleton root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    ok, errors = check_packet_root(Path(args.packet_root))

    if not ok:
        print("ERROR: PULSE-REF evidence packet layout skeleton check failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"OK: PULSE-REF evidence packet layout skeleton valid: {args.packet_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
