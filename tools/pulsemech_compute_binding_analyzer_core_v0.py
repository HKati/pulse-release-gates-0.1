#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


TOOL_ID = "build_pulsemech_compute_binding_report_v0"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "pulsemech_compute_binding_report_v0"
REPORT_TYPE = "pulsemech_compute_binding_report"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
DEFAULT_PRESERVATION_DIR = ROOT / "preservation" / "pulse_ci_6066"
DEFAULT_MANIFEST = DEFAULT_PRESERVATION_DIR / "PRESERVATION_MANIFEST_v0.json"
DEFAULT_README = DEFAULT_PRESERVATION_DIR / "README.md"
DEFAULT_SHA256SUMS = DEFAULT_PRESERVATION_DIR / "SHA256SUMS"
DEFAULT_SCHEMA = ROOT / "schemas" / "pulsemech_compute_binding_report_v0.schema.json"
DEFAULT_VALIDATOR = ROOT / "tools" / "check_pulsemech_compute_binding_report_v0.py"
DEFAULT_GATE_POLICY = ROOT / "pulse_gate_policy_v0.yml"
DEFAULT_GATE_REGISTRY = ROOT / "pulse_gate_registry_v0.yml"
DEFAULT_PULSE_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"

ARCHIVE_DISPLAY_PATH = "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
PRESERVATION_MANIFEST_DISPLAY_PATH = (
    "preservation/pulse_ci_6066/PRESERVATION_MANIFEST_v0.json"
)

EXPECTED_ARCHIVE_SHA256 = (
    "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
)
EXPECTED_ARCHIVE_SIZE = 44660
EXPECTED_SOURCE_COMMIT = "46b639706e23f80fe296a8893be18e2b5ab21f7e"
EXPECTED_RUN_ID = 29249887581
EXPECTED_RUN_NUMBER = 6066
EXPECTED_RUN_ATTEMPT = 1
EXPECTED_WORKFLOW = "PULSE CI"
EXPECTED_REPOSITORY = "HKati/pulse-release-gates-0.1"
EXPECTED_RUN_KEY = (
    "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|"
    "GITHUB_WORKFLOW=PULSE CI"
)
EXPECTED_ANALYSIS_RUN_KEY = (
    "OFFLINE_ANALYSIS=pulsemech-compute-binding-fixed-source-6066-v0"
)

OUTER_PREFIX = "pulse-ci-6066-preservation-v0/"
ORIGINAL_PREFIX = OUTER_PREFIX + "original-github-artifacts/"
COMPLETE_PACKAGE_NAME = "complete-release-grade-reference-package-29249887581-1.zip"
COMPLETENESS_ARCHIVE_NAME = "release-grade-package-completeness-29249887581-1.zip"
VERIFICATION_ARCHIVE_NAME = (
    "release-grade-reference-package-verification-29249887581-1.zip"
)

EXPECTED_ARTIFACTS: dict[str, dict[str, Any]] = {
    COMPLETE_PACKAGE_NAME: {
        "artifact_id": 8278987946,
        "role": "complete_release_grade_reference_package",
        "sha256": (
            "0549ea28c30dfdf6bc44a36a50fef3c21500a7ed1d9d58f448eaa1593ce3d264"
        ),
        "size_bytes": 44880,
    },
    COMPLETENESS_ARCHIVE_NAME: {
        "artifact_id": 8278994595,
        "role": "structural_package_completeness_report",
        "sha256": (
            "827ee63e902ba1770639302ef52b46d2064e7f097903b1f8520afb26a306749d"
        ),
        "size_bytes": 2044,
    },
    VERIFICATION_ARCHIVE_NAME: {
        "artifact_id": 8278995165,
        "role": "independent_package_verification_report",
        "sha256": (
            "c5dcc93eb17fe166a575e7a83ab1f364f44504e3c53105213202752592094c85"
        ),
        "size_bytes": 2418,
    },
}

EXPECTED_OUTER_MEMBERS = {
    OUTER_PREFIX + "PRESERVATION_MANIFEST_v0.json",
    OUTER_PREFIX + "README.md",
    OUTER_PREFIX + "SHA256SUMS",
    *{ORIGINAL_PREFIX + name for name in EXPECTED_ARTIFACTS},
}

COMPLETE_PACKAGE_REQUIRED_MEMBERS = {
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/external/llamaguard_summary.json",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/recorded_release_candidates/detector_materialization.json",
    "artifacts/recorded_release_candidates/external_llamaguard.json",
    "artifacts/recorded_release_candidates/refusal_delta_summary.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/release_authority_v0.json",
    "artifacts/release_decision_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/report_card.html",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status.json",
    "artifacts/status_baseline.json",
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
}

AUTHORITATIVE_MUTATION_CLASSES = {
    "release_evidence",
    "candidate_state",
    "verifier_state",
    "materialized_gate_set",
    "final_status",
    "release_decision",
}

ROLE_TO_COMPLETE_CLASS = {
    "transition": "transition_bound",
    "evidence": "evidence_bound",
    "preservation": "preservation_bound",
    "advisory": "advisory_bound",
}

SUMMARY_COUNT_FIELDS = {
    "transition_bound": "transition_bound_nodes",
    "evidence_bound": "evidence_bound_nodes",
    "preservation_bound": "preservation_bound_nodes",
    "advisory_bound": "advisory_bound_nodes",
    "unbound": "unbound_nodes",
    "unknown": "unknown_nodes",
}


class BuilderError(RuntimeError):
    pass


class StrictJsonError(ValueError):
    pass


@dataclass(frozen=True)
class ObservedBundle:
    archive_path: Path
    archive_sha256: str
    archive_size: int
    manifest_path: Path
    manifest_bytes: bytes
    manifest: dict[str, Any]
    readme_path: Path
    readme_bytes: bytes
    sha256sums_path: Path
    sha256sums_bytes: bytes
    sha256sums: dict[str, str]
    artifact_archives: dict[str, bytes]
    complete_package_members: dict[str, bytes]
    package_inventory: dict[str, Any]
    package_inventory_rows: dict[str, dict[str, Any]]
    completeness_report_bytes: bytes
    completeness_report: dict[str, Any]
    verification_report_bytes: bytes
    verification_report: dict[str, Any]


# ---------------------------------------------------------------------------
# Strict parsing and immutable-carrier verification
# ---------------------------------------------------------------------------


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON value: {value}")


def load_json_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        loaded = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except Exception as exc:
        raise BuilderError(f"{label}_json_invalid: {exc}") from exc

    if not isinstance(loaded, dict):
        raise BuilderError(f"{label}_not_object")
    return loaded


def render_json(data: dict[str, Any]) -> str:
    return (
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def same_target(left: Path, right: Path) -> bool:
    try:
        if left.resolve() == right.resolve():
            return True
    except OSError:
        pass

    try:
        if left.exists() and right.exists() and left.samefile(right):
            return True
    except OSError:
        pass

    return False


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except (OSError, ValueError):
        return False


def reject_unsafe_output(
    output: Path | None,
    *,
    archive: Path,
    manifest: Path,
    readme: Path,
    sha256sums: Path,
    schema: Path,
    validator: Path,
) -> None:
    if output is None:
        return

    protected = (
        archive,
        manifest,
        readme,
        sha256sums,
        schema,
        validator,
        DEFAULT_GATE_POLICY,
        DEFAULT_GATE_REGISTRY,
        DEFAULT_PULSE_WORKFLOW,
    )
    for path in protected:
        if same_target(output, path):
            raise BuilderError(f"refusing_to_overwrite_input: {path}")

    if output.name in {"status.json", "release_decision_v0.json"}:
        raise BuilderError(f"refusing_authority_surface_output: {output.name}")

    preservation_dir = manifest.parent
    if is_within(output, preservation_dir):
        raise BuilderError(
            "refusing_output_inside_preservation_directory: "
            f"{output}"
        )

    cursor = output
    while True:
        if cursor.is_symlink():
            raise BuilderError(f"refusing_symlink_output_path: {cursor}")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent


def safe_zip_members(
    zf: zipfile.ZipFile,
    *,
    label: str,
) -> dict[str, zipfile.ZipInfo]:
    infos = zf.infolist()
    names = [info.filename for info in infos]

    if len(names) != len(set(names)):
        raise BuilderError(f"{label}_duplicate_member")

    corrupt = zf.testzip()
    if corrupt is not None:
        raise BuilderError(f"{label}_crc_failure: {corrupt}")

    result: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        name = info.filename
        path = PurePosixPath(name)
        mode = info.external_attr >> 16

        if not name:
            raise BuilderError(f"{label}_empty_member_name")
        if "\\" in name:
            raise BuilderError(f"{label}_backslash_member: {name}")
        if path.is_absolute() or ".." in path.parts:
            raise BuilderError(f"{label}_unsafe_member_path: {name}")
        if info.is_dir():
            raise BuilderError(f"{label}_directory_member: {name}")
        if stat.S_ISLNK(mode):
            raise BuilderError(f"{label}_symlink_member: {name}")
        if info.flag_bits & 0x1:
            raise BuilderError(f"{label}_encrypted_member: {name}")

        result[name] = info

    return result


def parse_sha256sums(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        digest, separator, relative = line.partition("  ")
        if separator != "  ":
            raise BuilderError(f"sha256sums_invalid_line: {raw_line!r}")
        if len(digest) != 64:
            raise BuilderError(f"sha256sums_invalid_digest_length: {relative}")
        try:
            int(digest, 16)
        except ValueError as exc:
            raise BuilderError(
                f"sha256sums_invalid_digest_hex: {relative}"
            ) from exc
        if relative in entries:
            raise BuilderError(f"sha256sums_duplicate_path: {relative}")
        entries[relative] = digest.lower()
    return entries


def read_single_member_archive(
    payload: bytes,
    *,
    expected_member: str,
    label: str,
) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as zf:
            members = safe_zip_members(zf, label=label)
            if set(members) != {expected_member}:
                raise BuilderError(
                    f"{label}_member_set_mismatch: "
                    f"{sorted(members)}"
                )
            return zf.read(expected_member)
    except zipfile.BadZipFile as exc:
        raise BuilderError(f"{label}_invalid_zip: {exc}") from exc


def require_equal(actual: Any, expected: Any, *, label: str) -> None:
    if actual != expected:
        raise BuilderError(
            f"{label}_mismatch: actual={actual!r} expected={expected!r}"
        )


def validate_preservation_manifest(manifest: dict[str, Any]) -> None:
    require_equal(
        manifest.get("schema_id"),
        "pulse_ci_release_grade_artifact_preservation_manifest_v0",
        label="manifest_schema_id",
    )
    require_equal(manifest.get("schema_version"), "0.1.0", label="manifest_schema_version")
    require_equal(manifest.get("repository"), EXPECTED_REPOSITORY, label="manifest_repository")
    require_equal(manifest.get("workflow"), EXPECTED_WORKFLOW, label="manifest_workflow")
    require_equal(manifest.get("workflow_run_id"), EXPECTED_RUN_ID, label="manifest_run_id")
    require_equal(
        manifest.get("workflow_run_number"),
        EXPECTED_RUN_NUMBER,
        label="manifest_run_number",
    )
    require_equal(
        manifest.get("workflow_run_attempt"),
        EXPECTED_RUN_ATTEMPT,
        label="manifest_run_attempt",
    )
    require_equal(
        manifest.get("source_commit"),
        EXPECTED_SOURCE_COMMIT,
        label="manifest_source_commit",
    )
    require_equal(manifest.get("source_ref"), "refs/heads/main", label="manifest_source_ref")
    require_equal(manifest.get("run_mode"), "prod", label="manifest_run_mode")
    require_equal(
        manifest.get("active_policy_sets"),
        ["required", "release_required"],
        label="manifest_active_policy_sets",
    )
    require_equal(manifest.get("primary_gate_result"), "allow", label="manifest_primary_result")
    require_equal(manifest.get("release_decision"), "PROD-PASS", label="manifest_release_decision")

    boundary = manifest.get("authority_boundary")
    require_equal(
        boundary,
        {
            "alters_preserved_artifacts": False,
            "creates_release_authority": False,
            "preservation_copy_only": True,
            "replaces_original_github_attestations": False,
            "replaces_primary_ci_decision": False,
        },
        label="manifest_authority_boundary",
    )

    records = manifest.get("github_artifacts")
    if not isinstance(records, list):
        raise BuilderError("manifest_github_artifacts_not_array")

    indexed: dict[str, dict[str, Any]] = {}
    for raw in records:
        if not isinstance(raw, dict):
            raise BuilderError("manifest_artifact_record_not_object")
        name = raw.get("file_name")
        if not isinstance(name, str) or not name:
            raise BuilderError("manifest_artifact_file_name_missing")
        if name in indexed:
            raise BuilderError(f"manifest_duplicate_artifact: {name}")
        indexed[name] = raw

    require_equal(set(indexed), set(EXPECTED_ARTIFACTS), label="manifest_artifact_names")

    for name, expected in EXPECTED_ARTIFACTS.items():
        record = indexed[name]
        require_equal(record.get("artifact_id"), expected["artifact_id"], label=f"{name}_artifact_id")
        require_equal(record.get("role"), expected["role"], label=f"{name}_role")
        require_equal(record.get("size_bytes"), expected["size_bytes"], label=f"{name}_size")
        require_equal(record.get("downloaded_size_bytes"), expected["size_bytes"], label=f"{name}_downloaded_size")
        require_equal(record.get("github_sha256"), expected["sha256"], label=f"{name}_github_sha")
        require_equal(record.get("downloaded_sha256"), expected["sha256"], label=f"{name}_downloaded_sha")
        require_equal(record.get("github_digest_match"), True, label=f"{name}_digest_match")
        require_equal(record.get("github_size_match"), True, label=f"{name}_size_match")

    local = manifest.get("local_verification")
    if not isinstance(local, dict):
        raise BuilderError("manifest_local_verification_not_object")
    required_true = (
        "all_outer_artifact_digests_match_github",
        "all_outer_artifact_sizes_match_github",
        "structural_completeness_ok",
        "independent_verification_verified",
    )
    for field in required_true:
        require_equal(local.get(field), True, label=f"manifest_local_{field}")
    require_equal(local.get("complete_package_zip_members"), 24, label="manifest_package_members")
    require_equal(local.get("complete_package_inventory_entries"), 23, label="manifest_inventory_entries")
    require_equal(local.get("complete_package_inventory_errors"), [], label="manifest_inventory_errors")
    require_equal(
        local.get("complete_package_unlisted_members_excluding_inventory"),
        [],
        label="manifest_unlisted_members",
    )
    require_equal(local.get("structural_completeness_status"), "complete", label="manifest_completeness_status")
    require_equal(local.get("structural_completeness_checks_total"), 135, label="manifest_completeness_checks")
    require_equal(local.get("structural_completeness_checks_failed"), 0, label="manifest_completeness_failures")
    require_equal(local.get("independent_verification_status"), "verified", label="manifest_verification_status")
    require_equal(local.get("independent_verification_checks_total"), 157, label="manifest_verification_checks")
    require_equal(local.get("independent_verification_errors"), [], label="manifest_verification_errors")


def validate_package_inventory(
    members: dict[str, bytes],
    inventory: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    require_equal(
        inventory.get("schema_version"),
        "release_grade_reference_package_digest_inventory_v0",
        label="package_inventory_schema",
    )
    require_equal(inventory.get("algorithm"), "sha256", label="package_inventory_algorithm")
    rows = inventory.get("files")
    if not isinstance(rows, list):
        raise BuilderError("package_inventory_files_not_array")
    require_equal(inventory.get("file_count"), len(rows), label="package_inventory_file_count")

    indexed: dict[str, dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            raise BuilderError("package_inventory_row_not_object")
        path = raw.get("path")
        digest = raw.get("sha256")
        size = raw.get("size_bytes")
        if not isinstance(path, str) or not path:
            raise BuilderError("package_inventory_path_missing")
        if path in indexed:
            raise BuilderError(f"package_inventory_duplicate_path: {path}")
        if path not in members:
            raise BuilderError(f"package_inventory_member_missing: {path}")
        payload = members[path]
        require_equal(len(payload), size, label=f"package_inventory_size:{path}")
        require_equal(sha256_bytes(payload), digest, label=f"package_inventory_sha:{path}")
        indexed[path] = raw

    expected_members = set(indexed) | {"package_digest_inventory_v0.json"}
    require_equal(set(members), expected_members, label="complete_package_member_set")
    missing_required = sorted(COMPLETE_PACKAGE_REQUIRED_MEMBERS - set(members))
    if missing_required:
        raise BuilderError(
            "complete_package_required_members_missing: "
            + ", ".join(missing_required)
        )
    return indexed


def load_observed_bundle(
    *,
    archive_path: Path,
    manifest_path: Path,
    readme_path: Path,
    sha256sums_path: Path,
    expected_archive_sha256: str,
    expected_archive_size: int,
) -> ObservedBundle:
    for path in (archive_path, manifest_path, readme_path, sha256sums_path):
        if not path.is_file():
            raise BuilderError(f"required_input_missing: {path}")
        if path.is_symlink():
            raise BuilderError(f"required_input_is_symlink: {path}")

    archive_size = archive_path.stat().st_size
    archive_sha = sha256_file(archive_path)
    require_equal(archive_size, expected_archive_size, label="preservation_archive_size")
    require_equal(archive_sha, expected_archive_sha256, label="preservation_archive_sha256")

    manifest_bytes = manifest_path.read_bytes()
    readme_bytes = readme_path.read_bytes()
    sha256sums_bytes = sha256sums_path.read_bytes()

    try:
        with zipfile.ZipFile(archive_path, "r") as outer:
            outer_members = safe_zip_members(outer, label="preservation_archive")
            require_equal(set(outer_members), EXPECTED_OUTER_MEMBERS, label="preservation_archive_members")

            require_equal(
                outer.read(OUTER_PREFIX + "PRESERVATION_MANIFEST_v0.json"),
                manifest_bytes,
                label="visible_manifest_bytes",
            )
            require_equal(
                outer.read(OUTER_PREFIX + "README.md"),
                readme_bytes,
                label="visible_readme_bytes",
            )
            require_equal(
                outer.read(OUTER_PREFIX + "SHA256SUMS"),
                sha256sums_bytes,
                label="visible_sha256sums_bytes",
            )

            artifact_archives = {
                name: outer.read(ORIGINAL_PREFIX + name)
                for name in EXPECTED_ARTIFACTS
            }
    except zipfile.BadZipFile as exc:
        raise BuilderError(f"preservation_archive_invalid_zip: {exc}") from exc

    manifest = load_json_bytes(manifest_bytes, label="preservation_manifest")
    validate_preservation_manifest(manifest)

    sums = parse_sha256sums(sha256sums_bytes.decode("utf-8"))
    expected_sums = {
        "PRESERVATION_MANIFEST_v0.json": sha256_bytes(manifest_bytes),
        "README.md": sha256_bytes(readme_bytes),
        **{
            "original-github-artifacts/" + name: expected["sha256"]
            for name, expected in EXPECTED_ARTIFACTS.items()
        },
    }
    require_equal(sums, expected_sums, label="visible_sha256sums")

    for name, expected in EXPECTED_ARTIFACTS.items():
        payload = artifact_archives[name]
        require_equal(len(payload), expected["size_bytes"], label=f"artifact_size:{name}")
        require_equal(sha256_bytes(payload), expected["sha256"], label=f"artifact_sha256:{name}")

    complete_payload = artifact_archives[COMPLETE_PACKAGE_NAME]
    try:
        with zipfile.ZipFile(io.BytesIO(complete_payload), "r") as package:
            package_infos = safe_zip_members(package, label="complete_package")
            complete_members = {
                name: package.read(name)
                for name in package_infos
            }
    except zipfile.BadZipFile as exc:
        raise BuilderError(f"complete_package_invalid_zip: {exc}") from exc

    inventory = load_json_bytes(
        complete_members["package_digest_inventory_v0.json"],
        label="package_inventory",
    )
    inventory_rows = validate_package_inventory(complete_members, inventory)

    completeness_bytes = read_single_member_archive(
        artifact_archives[COMPLETENESS_ARCHIVE_NAME],
        expected_member="release_grade_package_completeness_v1.json",
        label="package_completeness_archive",
    )
    completeness = load_json_bytes(
        completeness_bytes,
        label="package_completeness_report",
    )
    require_equal(completeness.get("schema_version"), "release_grade_package_completeness_v1", label="completeness_schema")
    require_equal(completeness.get("status"), "complete", label="completeness_status")
    require_equal(completeness.get("ok"), True, label="completeness_ok")
    require_equal(completeness.get("errors"), [], label="completeness_errors")
    require_equal(
        completeness.get("summary"),
        {
            "checks_total": 135,
            "checks_failed": 0,
            "required_files": 18,
            "required_dirs": 2,
        },
        label="completeness_summary",
    )
    checks = completeness.get("checks")
    if not isinstance(checks, list) or len(checks) != 135:
        raise BuilderError("completeness_checks_invalid")
    if not all(isinstance(check, dict) and check.get("passed") is True for check in checks):
        raise BuilderError("completeness_check_failed")

    verification_bytes = read_single_member_archive(
        artifact_archives[VERIFICATION_ARCHIVE_NAME],
        expected_member="release_grade_reference_package_verification_v0.json",
        label="package_verification_archive",
    )
    verification = load_json_bytes(
        verification_bytes,
        label="package_verification_report",
    )
    require_equal(
        verification.get("schema_version"),
        "release_grade_reference_package_verification_v0",
        label="verification_schema",
    )
    require_equal(verification.get("status"), "verified", label="verification_status")
    require_equal(verification.get("verified"), True, label="verification_verified")
    require_equal(verification.get("errors"), [], label="verification_errors")
    verification_checks = verification.get("checks")
    if not isinstance(verification_checks, list) or len(verification_checks) != 157:
        raise BuilderError("verification_checks_invalid")
    if not all(
        isinstance(check, dict) and check.get("passed") is True
        for check in verification_checks
    ):
        raise BuilderError("verification_check_failed")

    # Re-read the immutable subject carrier after all analysis work.
    require_equal(archive_path.stat().st_size, archive_size, label="archive_size_after_analysis")
    require_equal(sha256_file(archive_path), archive_sha, label="archive_sha_after_analysis")

    return ObservedBundle(
        archive_path=archive_path,
        archive_sha256=archive_sha,
        archive_size=archive_size,
        manifest_path=manifest_path,
        manifest_bytes=manifest_bytes,
        manifest=manifest,
        readme_path=readme_path,
        readme_bytes=readme_bytes,
        sha256sums_path=sha256sums_path,
        sha256sums_bytes=sha256sums_bytes,
        sha256sums=sums,
        artifact_archives=artifact_archives,
        complete_package_members=complete_members,
        package_inventory=inventory,
        package_inventory_rows=inventory_rows,
        completeness_report_bytes=completeness_bytes,
        completeness_report=completeness,
        verification_report_bytes=verification_bytes,
        verification_report=verification,
    )


# ---------------------------------------------------------------------------
# Artifact-observed graph construction
# ---------------------------------------------------------------------------


def package_json(bundle: ObservedBundle, path: str) -> dict[str, Any]:
    try:
        payload = bundle.complete_package_members[path]
    except KeyError as exc:
        raise BuilderError(f"package_member_missing: {path}") from exc
    return load_json_bytes(payload, label=path.replace("/", "_"))


def package_record(bundle: ObservedBundle, path: str) -> dict[str, Any]:
    try:
        return bundle.package_inventory_rows[path]
    except KeyError as exc:
        raise BuilderError(f"package_inventory_record_missing: {path}") from exc


def package_uri(path: str) -> str:
    return f"{COMPLETE_PACKAGE_NAME}!/{path}"


def outer_artifact_uri(name: str) -> str:
    return (
        "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip!/"
        + ORIGINAL_PREFIX
        + name
    )


def schema_identity(data: dict[str, Any], fallback: str | None = None) -> str | None:
    for key in ("schema_version", "schema", "schema_id"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return fallback


def source_identity(
    *,
    source_kind: str,
    path_or_uri: str | None,
    revision: str | None,
    sha256: str | None,
) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        "source_path_or_uri": path_or_uri,
        "source_revision": revision,
        "source_sha256": sha256,
    }


def run_binding(
    *,
    subject_run_key: str,
    analysis_run_key: str,
    scope: str,
) -> dict[str, Any]:
    if scope == "subject":
        return {
            "execution_run_key": subject_run_key,
            "subject_run_key": subject_run_key,
            "binding_mode": "current_subject_run",
            "binding_complete": True,
        }
    return {
        "execution_run_key": analysis_run_key,
        "subject_run_key": subject_run_key,
        "binding_mode": "offline_observer",
        "binding_complete": True,
    }


def expected_binding_class(*, role: str, status: str, scope: str) -> str:
    if scope == "analysis_observer" or role == "observer":
        return "observer"
    if status == "complete":
        return ROLE_TO_COMPLETE_CLASS[role]
    if status == "none":
        return "unbound"
    return "unknown"


def make_compute_node(
    *,
    node_id: str,
    node_type: str,
    scope: str,
    role: str,
    status: str,
    source: dict[str, Any],
    subject_run_key: str,
    analysis_run_key: str,
    inputs: Iterable[str],
    outputs: Iterable[str],
    mutation_authority: str,
    observed_mutation: bool,
) -> dict[str, Any]:
    binding_class = expected_binding_class(role=role, status=status, scope=scope)
    observed_classes = (
        [mutation_authority]
        if observed_mutation and mutation_authority != "none"
        else []
    )
    authoritative_observed = bool(
        set(observed_classes) & AUTHORITATIVE_MUTATION_CLASSES
    )
    return {
        "node_id": node_id,
        "node_type": node_type,
        "execution_scope": scope,
        "declared_role": role,
        "binding_status": status,
        "binding_class": binding_class,
        "source_identity": source,
        "run_binding": run_binding(
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            scope=scope,
        ),
        "input_state_ids": sorted(set(inputs)),
        "output_state_ids": sorted(set(outputs)),
        "mutation_authority": mutation_authority,
        "observed_mutation_classes": sorted(observed_classes),
        "unbound_authoritative_mutation": (
            authoritative_observed and status != "complete"
        ),
        "resource_usage": {},
        "flags": {
            "duplicate_candidate": False,
            "mutation_authority_present": mutation_authority != "none",
            "cross_run_input_present": False,
            "mutable_source_reference": source.get("source_sha256") is None,
            "resource_measurement_partial": False,
        },
    }


def make_state_node(
    *,
    state_id: str,
    state_type: str,
    path_or_uri: str,
    sha256: str | None,
    size_bytes: int | None,
    schema_id: str | None,
    producer_node_id: str | None,
    subject_run_key: str,
    release_candidate_id: str | None,
    policy_relation: str | None,
    gate_relation: str | None,
    authority_bearing: bool,
) -> dict[str, Any]:
    return {
        "state_id": state_id,
        "state_type": state_type,
        "path_or_uri": path_or_uri,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "schema_identity": schema_id,
        "producer_node_id": producer_node_id,
        "subject_run_key": subject_run_key,
        "release_candidate_id": release_candidate_id,
        "policy_relation": policy_relation,
        "gate_relation": gate_relation,
        "authority_bearing": authority_bearing,
    }


def make_edge(
    *,
    edge_id: str,
    from_id: str,
    to_id: str,
    edge_type: str,
    digest: str,
    notes: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "edge_id": edge_id,
        "from_id": from_id,
        "to_id": to_id,
        "edge_type": edge_type,
        "declared": True,
        "observed": True,
        "binding_status": "complete",
        "evidence_digests": [digest],
        "notes": sorted(set(notes)),
    }


def finding(
    *,
    finding_id: str,
    severity: str,
    message: str,
    node_id: str | None = None,
    state_id: str | None = None,
    edge_id: str | None = None,
    evidence_refs: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "node_id": node_id,
        "state_id": state_id,
        "edge_id": edge_id,
        "message": message,
        "evidence_refs": sorted(set(evidence_refs)),
    }


def build_report(
    bundle: ObservedBundle,
    *,
    analysis_run_key: str,
    builder_source_sha256: str,
    analyzer_core_source_sha256: str | None = None,
) -> dict[str, Any]:
    if analyzer_core_source_sha256 is None:
        analyzer_core_source_sha256 = sha256_file(Path(__file__))

    manifest = bundle.manifest
    members = bundle.complete_package_members

    run_metadata = package_json(bundle, "run_metadata_v0.json")
    required_evidence = package_json(bundle, "artifacts/required_gate_evidence_v0.json")
    status_baseline = package_json(bundle, "artifacts/status_baseline.json")
    final_status = package_json(bundle, "artifacts/status.json")
    candidate_index = package_json(bundle, "artifacts/recorded_release_candidate_index_v0.json")
    candidate_detector = package_json(
        bundle,
        "artifacts/recorded_release_candidates/detector_materialization.json",
    )
    candidate_external = package_json(
        bundle,
        "artifacts/recorded_release_candidates/external_llamaguard.json",
    )
    candidate_refusal = package_json(
        bundle,
        "artifacts/recorded_release_candidates/refusal_delta_summary.json",
    )
    evidence_manifest = package_json(
        bundle,
        "artifacts/release_evidence_input_manifest_v0.json",
    )
    verifier_report = package_json(
        bundle,
        "artifacts/recorded_release_evidence_verifier_v0.json",
    )
    release_decision = package_json(bundle, "artifacts/release_decision_v0.json")
    release_authority = package_json(bundle, "artifacts/release_authority_v0.json")
    artifact_binding = package_json(
        bundle,
        "artifacts/artifact_provenance_binding_v0.json",
    )
    external_summary = package_json(
        bundle,
        "artifacts/external/llamaguard_summary.json",
    )
    external_evaluator_manifest = package_json(
        bundle,
        "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    )
    external_envelope = package_json(
        bundle,
        "artifacts/external/llamaguard_summary.envelope.json",
    )
    external_attestation_verifier = package_json(
        bundle,
        "artifacts/external/llamaguard_attestation_verifier_v1.json",
    )

    subject_run_key = run_metadata.get("run_key")
    require_equal(subject_run_key, EXPECTED_RUN_KEY, label="run_metadata_run_key")
    require_equal(run_metadata.get("repository"), EXPECTED_REPOSITORY, label="run_metadata_repository")
    require_equal(run_metadata.get("run_id"), EXPECTED_RUN_ID, label="run_metadata_run_id")
    require_equal(run_metadata.get("run_attempt"), EXPECTED_RUN_ATTEMPT, label="run_metadata_run_attempt")
    require_equal(run_metadata.get("git_sha"), EXPECTED_SOURCE_COMMIT, label="run_metadata_git_sha")
    require_equal(run_metadata.get("release_candidate"), "main", label="run_metadata_release_candidate")

    policy_sha = release_decision.get("policy_sha256")
    policy_id = release_authority.get("inputs", {}).get("gate_policy", {}).get("policy_id")
    registry_sha = release_authority.get("inputs", {}).get("gate_registry", {}).get("sha256")
    materialized_sha = (
        artifact_binding.get("authority_carrier", {})
        .get("workflow_effective_required_gate_set", {})
        .get("sha256")
    )
    strict_result_sha = (
        artifact_binding.get("authority_carrier", {})
        .get("strict_ci_gate_enforcement", {})
        .get("sha256")
    )

    for value, label in (
        (policy_sha, "policy_sha"),
        (policy_id, "policy_id"),
        (registry_sha, "registry_sha"),
        (materialized_sha, "materialized_gate_set_sha"),
        (strict_result_sha, "strict_result_sha"),
    ):
        if not isinstance(value, str) or not value:
            raise BuilderError(f"{label}_missing")

    status_record = package_record(bundle, "artifacts/status.json")
    status_baseline_record = package_record(bundle, "artifacts/status_baseline.json")
    decision_record = package_record(bundle, "artifacts/release_decision_v0.json")
    required_record = package_record(bundle, "artifacts/required_gate_evidence_v0.json")
    candidate_index_record = package_record(
        bundle,
        "artifacts/recorded_release_candidate_index_v0.json",
    )
    candidate_detector_record = package_record(
        bundle,
        "artifacts/recorded_release_candidates/detector_materialization.json",
    )
    candidate_external_record = package_record(
        bundle,
        "artifacts/recorded_release_candidates/external_llamaguard.json",
    )
    candidate_refusal_record = package_record(
        bundle,
        "artifacts/recorded_release_candidates/refusal_delta_summary.json",
    )
    evidence_manifest_record = package_record(
        bundle,
        "artifacts/release_evidence_input_manifest_v0.json",
    )
    verifier_record = package_record(
        bundle,
        "artifacts/recorded_release_evidence_verifier_v0.json",
    )
    release_authority_record = package_record(
        bundle,
        "artifacts/release_authority_v0.json",
    )
    artifact_binding_record = package_record(
        bundle,
        "artifacts/artifact_provenance_binding_v0.json",
    )
    report_card_record = package_record(bundle, "artifacts/report_card.html")
    external_summary_record = package_record(
        bundle,
        "artifacts/external/llamaguard_summary.json",
    )
    external_raw_record = package_record(
        bundle,
        "artifacts/external/llamaguard_raw.jsonl",
    )
    external_evaluator_manifest_record = package_record(
        bundle,
        "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    )
    external_bundle_record = package_record(
        bundle,
        "artifacts/external/llamaguard_summary.bundle.json",
    )
    external_envelope_record = package_record(
        bundle,
        "artifacts/external/llamaguard_summary.envelope.json",
    )
    external_attestation_verifier_record = package_record(
        bundle,
        "artifacts/external/llamaguard_attestation_verifier_v1.json",
    )
    package_inventory_bytes = members["package_digest_inventory_v0.json"]
    run_metadata_bytes = members["run_metadata_v0.json"]

    require_equal(release_decision.get("git_sha"), EXPECTED_SOURCE_COMMIT, label="decision_git_sha")
    require_equal(release_decision.get("status_sha256"), status_record["sha256"], label="decision_status_sha")
    require_equal(final_status.get("metrics", {}).get("run_key"), EXPECTED_RUN_KEY, label="status_run_key")
    require_equal(final_status.get("metrics", {}).get("git_sha"), EXPECTED_SOURCE_COMMIT, label="status_git_sha")
    require_equal(verifier_report.get("run_identity", {}).get("run_key"), EXPECTED_RUN_KEY, label="verifier_run_key")
    require_equal(verifier_report.get("status"), "verified", label="verifier_status")
    require_equal(verifier_report.get("errors"), [], label="verifier_errors")

    decision_value = (
        "ALLOW"
        if release_decision.get("required_gates_passed") is True
        and release_decision.get("release_level") == "PROD-PASS"
        else "BLOCK"
    )

    release_candidate = str(run_metadata["release_candidate"])

    # External digests that are recorded but whose source bytes are not part of
    # the preserved complete package remain state identities with unknown size.
    external_thresholds_sha = candidate_index["source_bindings"]["external_thresholds"]["sha256"]
    refusal_source_sha = candidate_refusal["raw_evidence_binding"]["sha256"]
    external_dataset_sha = external_evaluator_manifest["dataset"]["sha256"]
    external_signer_policy_sha = external_envelope["extensions"]["signer_policy_sha256"]
    external_workflow_sha = external_envelope["extensions"]["workflow_sha256"]
    external_adapter_sha = external_summary["extensions"]["adapter_sha256"]
    external_envelope_builder = external_envelope["extensions"]["envelope_builder"]
    external_replay_verifier = external_envelope["extensions"]["canonical_replay_verifier"]
    external_attest_action = external_envelope["verification"]["verifier"]["version"]

    states: list[dict[str, Any]] = [
        make_state_node(
            state_id="state:artifact-binding",
            state_type="manifest",
            path_or_uri=package_uri("artifacts/artifact_provenance_binding_v0.json"),
            sha256=artifact_binding_record["sha256"],
            size_bytes=artifact_binding_record["size_bytes"],
            schema_id=schema_identity(artifact_binding),
            producer_node_id="compute:artifact-binding-builder",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=str(policy_id),
            gate_relation=None,
            authority_bearing=False,
        ),
        make_state_node(
            state_id="state:candidate-detector",
            state_type="candidate_state",
            path_or_uri=package_uri("artifacts/recorded_release_candidates/detector_materialization.json"),
            sha256=candidate_detector_record["sha256"],
            size_bytes=candidate_detector_record["size_bytes"],
            schema_id=schema_identity(candidate_detector),
            producer_node_id="compute:recorded-candidate-builder",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="release_required",
            gate_relation="detectors_materialized_ok",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:candidate-external",
            state_type="candidate_state",
            path_or_uri=package_uri("artifacts/recorded_release_candidates/external_llamaguard.json"),
            sha256=candidate_external_record["sha256"],
            size_bytes=candidate_external_record["size_bytes"],
            schema_id=schema_identity(candidate_external),
            producer_node_id="compute:recorded-candidate-builder",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="release_required",
            gate_relation="external_all_pass+external_summaries_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:candidate-index",
            state_type="candidate_state",
            path_or_uri=package_uri("artifacts/recorded_release_candidate_index_v0.json"),
            sha256=candidate_index_record["sha256"],
            size_bytes=candidate_index_record["size_bytes"],
            schema_id=schema_identity(candidate_index),
            producer_node_id="compute:recorded-candidate-builder",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="required+release_required",
            gate_relation=None,
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:candidate-refusal",
            state_type="candidate_state",
            path_or_uri=package_uri("artifacts/recorded_release_candidates/refusal_delta_summary.json"),
            sha256=candidate_refusal_record["sha256"],
            size_bytes=candidate_refusal_record["size_bytes"],
            schema_id=schema_identity(candidate_refusal),
            producer_node_id="compute:recorded-candidate-builder",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="release_required",
            gate_relation="refusal_delta_evidence_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:complete-package",
            state_type="package",
            path_or_uri=outer_artifact_uri(COMPLETE_PACKAGE_NAME),
            sha256=EXPECTED_ARTIFACTS[COMPLETE_PACKAGE_NAME]["sha256"],
            size_bytes=EXPECTED_ARTIFACTS[COMPLETE_PACKAGE_NAME]["size_bytes"],
            schema_id=str(run_metadata.get("package_schema_version")),
            producer_node_id="compute:package-assembler",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=None,
            gate_relation=None,
            authority_bearing=False,
        ),
        make_state_node(
            state_id="state:evidence-manifest",
            state_type="manifest",
            path_or_uri=package_uri("artifacts/release_evidence_input_manifest_v0.json"),
            sha256=evidence_manifest_record["sha256"],
            size_bytes=evidence_manifest_record["size_bytes"],
            schema_id=schema_identity(evidence_manifest),
            producer_node_id="compute:evidence-manifest-builder",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="required+release_required",
            gate_relation=None,
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:external-attestation-bundle",
            state_type="attestation",
            path_or_uri=package_uri("artifacts/external/llamaguard_summary.bundle.json"),
            sha256=external_bundle_record["sha256"],
            size_bytes=external_bundle_record["size_bytes"],
            schema_id="sigstore_bundle_v0",
            producer_node_id="compute:github-attestation",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="policy/external_signers_v1.yml",
            gate_relation="external_all_pass+external_summaries_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:external-attestation-verifier",
            state_type="verifier_report",
            path_or_uri=package_uri("artifacts/external/llamaguard_attestation_verifier_v1.json"),
            sha256=external_attestation_verifier_record["sha256"],
            size_bytes=external_attestation_verifier_record["size_bytes"],
            schema_id=schema_identity(external_attestation_verifier),
            producer_node_id="compute:external-attestation-verifier",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="policy/external_signers_v1.yml",
            gate_relation="external_all_pass+external_summaries_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:external-evaluator-manifest",
            state_type="manifest",
            path_or_uri=package_uri("artifacts/external/llamaguard_evaluator_manifest_v0.json"),
            sha256=external_evaluator_manifest_record["sha256"],
            size_bytes=external_evaluator_manifest_record["size_bytes"],
            schema_id=schema_identity(external_evaluator_manifest),
            producer_node_id="compute:llamaguard-runtime",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="external-thresholds-v0",
            gate_relation="external_all_pass+external_summaries_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:external-summary-envelope",
            state_type="attestation",
            path_or_uri=package_uri("artifacts/external/llamaguard_summary.envelope.json"),
            sha256=external_envelope_record["sha256"],
            size_bytes=external_envelope_record["size_bytes"],
            schema_id=schema_identity(external_envelope),
            producer_node_id="compute:external-envelope-builder",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="policy/external_signers_v1.yml",
            gate_relation="external_all_pass+external_summaries_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:external-raw-evidence",
            state_type="release_evidence",
            path_or_uri=package_uri("artifacts/external/llamaguard_raw.jsonl"),
            sha256=external_raw_record["sha256"],
            size_bytes=external_raw_record["size_bytes"],
            schema_id="llamaguard_raw_jsonl_v0",
            producer_node_id="compute:llamaguard-runtime",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="external-thresholds-v0",
            gate_relation="external_all_pass+external_summaries_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:external-signer-policy",
            state_type="policy",
            path_or_uri=str(external_envelope["policy_context"]["signer_policy_ref"]),
            sha256=str(external_signer_policy_sha),
            size_bytes=None,
            schema_id="external_signers_v1",
            producer_node_id=None,
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="external-signer-policy-v1",
            gate_relation="external_all_pass+external_summaries_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:external-workflow-source",
            state_type="manifest",
            path_or_uri=str(external_envelope["extensions"]["workflow_path"]),
            sha256=str(external_workflow_sha),
            size_bytes=None,
            schema_id="github_actions_workflow",
            producer_node_id=None,
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="external-signer-policy-v1",
            gate_relation="external_all_pass+external_summaries_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:llamaguard-dataset",
            state_type="release_evidence",
            path_or_uri=str(external_evaluator_manifest["dataset"]["path"]),
            sha256=str(external_dataset_sha),
            size_bytes=None,
            schema_id="llamaguard_current_run_cases_v0",
            producer_node_id=None,
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="external-thresholds-v0",
            gate_relation="external_all_pass",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:external-summary",
            state_type="release_evidence",
            path_or_uri=package_uri("artifacts/external/llamaguard_summary.json"),
            sha256=external_summary_record["sha256"],
            size_bytes=external_summary_record["size_bytes"],
            schema_id=schema_identity(external_summary),
            producer_node_id="compute:llamaguard-summary-adapter",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="policy/external_signers_v1.yml",
            gate_relation="external_all_pass+external_summaries_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:external-thresholds",
            state_type="policy",
            path_or_uri=str(candidate_index["source_bindings"]["external_thresholds"]["path"]),
            sha256=str(external_thresholds_sha),
            size_bytes=None,
            schema_id=None,
            producer_node_id=None,
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="external-thresholds-v0",
            gate_relation="external_all_pass",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:final-status",
            state_type="status_artifact",
            path_or_uri=package_uri("artifacts/status.json"),
            sha256=status_record["sha256"],
            size_bytes=status_record["size_bytes"],
            schema_id="status_v1",
            producer_node_id="compute:release-required-materializer",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=str(policy_id),
            gate_relation="required+release_required",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:independent-verification",
            state_type="preservation_record",
            path_or_uri=outer_artifact_uri(VERIFICATION_ARCHIVE_NAME) + "!/release_grade_reference_package_verification_v0.json",
            sha256=sha256_bytes(bundle.verification_report_bytes),
            size_bytes=len(bundle.verification_report_bytes),
            schema_id=schema_identity(bundle.verification_report),
            producer_node_id="compute:package-verifier",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=None,
            gate_relation=None,
            authority_bearing=False,
        ),
        make_state_node(
            state_id="state:materialized-gate-set",
            state_type="materialized_gate_set",
            path_or_uri="inline:artifact_provenance_binding_v0.authority_carrier.workflow_effective_required_gate_set",
            sha256=str(materialized_sha),
            size_bytes=None,
            schema_id="workflow_effective_required_gate_set_v0",
            producer_node_id="compute:release-required-materializer",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=str(policy_id),
            gate_relation="required+release_required",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:package-completeness",
            state_type="preservation_record",
            path_or_uri=outer_artifact_uri(COMPLETENESS_ARCHIVE_NAME) + "!/release_grade_package_completeness_v1.json",
            sha256=sha256_bytes(bundle.completeness_report_bytes),
            size_bytes=len(bundle.completeness_report_bytes),
            schema_id=schema_identity(bundle.completeness_report),
            producer_node_id="compute:package-completeness-checker",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=None,
            gate_relation=None,
            authority_bearing=False,
        ),
        make_state_node(
            state_id="state:package-inventory",
            state_type="manifest",
            path_or_uri=package_uri("package_digest_inventory_v0.json"),
            sha256=sha256_bytes(package_inventory_bytes),
            size_bytes=len(package_inventory_bytes),
            schema_id=schema_identity(bundle.package_inventory),
            producer_node_id="compute:package-assembler",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=None,
            gate_relation=None,
            authority_bearing=False,
        ),
        make_state_node(
            state_id="state:policy",
            state_type="policy",
            path_or_uri=str(release_decision.get("policy_path")),
            sha256=str(policy_sha),
            size_bytes=None,
            schema_id=str(policy_id),
            producer_node_id=None,
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=str(policy_id),
            gate_relation=None,
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:preservation-manifest",
            state_type="preservation_record",
            path_or_uri=PRESERVATION_MANIFEST_DISPLAY_PATH,
            sha256=sha256_bytes(bundle.manifest_bytes),
            size_bytes=len(bundle.manifest_bytes),
            schema_id=schema_identity(manifest),
            producer_node_id=None,
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=None,
            gate_relation=None,
            authority_bearing=False,
        ),
        make_state_node(
            state_id="state:recorded-verifier-report",
            state_type="verifier_report",
            path_or_uri=package_uri("artifacts/recorded_release_evidence_verifier_v0.json"),
            sha256=verifier_record["sha256"],
            size_bytes=verifier_record["size_bytes"],
            schema_id=schema_identity(verifier_report),
            producer_node_id="compute:recorded-evidence-verifier",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="required+release_required",
            gate_relation="release_required",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:refusal-delta-source",
            state_type="release_evidence",
            path_or_uri=str(candidate_refusal["raw_evidence_binding"]["path"]),
            sha256=str(refusal_source_sha),
            size_bytes=None,
            schema_id=candidate_refusal["raw_evidence_binding"].get("schema_version"),
            producer_node_id=None,
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=None,
            gate_relation="refusal_delta_evidence_present",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:registry",
            state_type="manifest",
            path_or_uri=str(release_authority["inputs"]["gate_registry"]["path"]),
            sha256=str(registry_sha),
            size_bytes=None,
            schema_id=str(release_authority["inputs"]["gate_registry"]["version"]),
            producer_node_id=None,
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=None,
            gate_relation=None,
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:release-authority-manifest",
            state_type="reader_surface",
            path_or_uri=package_uri("artifacts/release_authority_v0.json"),
            sha256=release_authority_record["sha256"],
            size_bytes=release_authority_record["size_bytes"],
            schema_id=schema_identity(release_authority),
            producer_node_id="compute:release-authority-manifest-builder",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=str(policy_id),
            gate_relation="required+release_required",
            authority_bearing=False,
        ),
        make_state_node(
            state_id="state:release-decision",
            state_type="decision_artifact",
            path_or_uri=package_uri("artifacts/release_decision_v0.json"),
            sha256=decision_record["sha256"],
            size_bytes=decision_record["size_bytes"],
            schema_id=schema_identity(release_decision),
            producer_node_id="compute:release-decision-materializer",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=str(policy_id),
            gate_relation="required+release_required",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:report-card",
            state_type="reader_surface",
            path_or_uri=package_uri("artifacts/report_card.html"),
            sha256=report_card_record["sha256"],
            size_bytes=report_card_record["size_bytes"],
            schema_id="text/html",
            producer_node_id=None,
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=None,
            gate_relation=None,
            authority_bearing=False,
        ),
        make_state_node(
            state_id="state:required-gate-evidence",
            state_type="release_evidence",
            path_or_uri=package_uri("artifacts/required_gate_evidence_v0.json"),
            sha256=required_record["sha256"],
            size_bytes=required_record["size_bytes"],
            schema_id=schema_identity(required_evidence),
            producer_node_id="compute:required-gate-evaluator",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="required",
            gate_relation="required",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:status-baseline",
            state_type="candidate_state",
            path_or_uri=package_uri("artifacts/status_baseline.json"),
            sha256=status_baseline_record["sha256"],
            size_bytes=status_baseline_record["size_bytes"],
            schema_id="status_v1",
            producer_node_id="compute:candidate-status-builder",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation="required",
            gate_relation="required",
            authority_bearing=True,
        ),
        make_state_node(
            state_id="state:strict-gate-result",
            state_type="decision_artifact",
            path_or_uri="inline:artifact_provenance_binding_v0.authority_carrier.strict_ci_gate_enforcement",
            sha256=str(strict_result_sha),
            size_bytes=None,
            schema_id="strict_ci_gate_enforcement_v0",
            producer_node_id="compute:check-gates",
            subject_run_key=subject_run_key,
            release_candidate_id=release_candidate,
            policy_relation=str(policy_id),
            gate_relation="required+release_required",
            authority_bearing=True,
        ),
    ]

    required_producer = required_evidence["producer"]
    candidate_source = candidate_detector["provenance"]
    check_gates_source = release_authority["evaluation"]
    decision_producer_name = release_decision.get("producer", {}).get("name")
    artifact_binding_producer_name = artifact_binding.get("producer", {}).get("name")
    assembler_name = run_metadata.get("assembler", {}).get("tool")
    completeness_tool = bundle.completeness_report.get("tool", {}).get("name")
    verification_tool = bundle.verification_report.get("tool", {}).get("name")

    nodes: list[dict[str, Any]] = [
        make_compute_node(
            node_id="compute:artifact-binding-builder",
            node_type="artifact_builder",
            scope="subject",
            role="preservation",
            status="partial",
            source=source_identity(
                source_kind="unknown",
                path_or_uri=str(artifact_binding_producer_name) if artifact_binding_producer_name else None,
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:final-status",
                "state:materialized-gate-set",
                "state:policy",
                "state:release-authority-manifest",
                "state:release-decision",
                "state:report-card",
                "state:strict-gate-result",
            ],
            outputs=["state:artifact-binding"],
            mutation_authority="preservation_output",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:candidate-status-builder",
            node_type="artifact_builder",
            scope="subject",
            role="transition",
            status="complete",
            source=source_identity(
                source_kind="repository_file",
                path_or_uri=str(status_baseline["metrics"]["candidate_status_builder_path"]),
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=str(status_baseline["metrics"]["candidate_status_builder_sha256"]),
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=["state:policy", "state:registry", "state:required-gate-evidence"],
            outputs=["state:status-baseline"],
            mutation_authority="candidate_state",
            observed_mutation=True,
        ),
        make_compute_node(
            node_id="compute:check-gates",
            node_type="local_tool_execution",
            scope="subject",
            role="transition",
            status="complete",
            source=source_identity(
                source_kind="repository_file",
                path_or_uri="PULSE_safe_pack_v0/tools/check_gates.py",
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=str(check_gates_source["evaluator_sha256"]),
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:final-status",
                "state:materialized-gate-set",
                "state:policy",
                "state:registry",
            ],
            outputs=["state:strict-gate-result"],
            mutation_authority="release_decision",
            observed_mutation=True,
        ),
        make_compute_node(
            node_id="compute:evidence-manifest-builder",
            node_type="artifact_builder",
            scope="subject",
            role="evidence",
            status="partial",
            source=source_identity(
                source_kind="unknown",
                path_or_uri=None,
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:candidate-detector",
                "state:candidate-external",
                "state:candidate-refusal",
                "state:policy",
                "state:registry",
            ],
            outputs=["state:evidence-manifest"],
            mutation_authority="release_evidence",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:external-attestation-verifier",
            node_type="verifier_execution",
            scope="subject",
            role="evidence",
            status="complete",
            source=source_identity(
                source_kind="repository_file",
                path_or_uri=str(external_replay_verifier["path"]),
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=str(external_replay_verifier["sha256"]),
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:external-attestation-bundle",
                "state:external-signer-policy",
                "state:external-summary",
                "state:external-summary-envelope",
                "state:external-workflow-source",
            ],
            outputs=["state:external-attestation-verifier"],
            mutation_authority="verifier_state",
            observed_mutation=True,
        ),
        make_compute_node(
            node_id="compute:external-envelope-builder",
            node_type="artifact_builder",
            scope="subject",
            role="evidence",
            status="complete",
            source=source_identity(
                source_kind="repository_file",
                path_or_uri=str(external_envelope_builder["path"]),
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=str(external_envelope_builder["sha256"]),
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:external-attestation-bundle",
                "state:external-signer-policy",
                "state:external-summary",
                "state:external-thresholds",
                "state:external-workflow-source",
            ],
            outputs=["state:external-summary-envelope"],
            mutation_authority="release_evidence",
            observed_mutation=True,
        ),
        make_compute_node(
            node_id="compute:github-attestation",
            node_type="external_service_call",
            scope="subject",
            role="evidence",
            status="partial",
            source=source_identity(
                source_kind="action",
                path_or_uri="actions/attest",
                revision=str(external_attest_action).split("@", 1)[-1],
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:external-summary",
                "state:external-workflow-source",
            ],
            outputs=["state:external-attestation-bundle"],
            mutation_authority="release_evidence",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:llamaguard-runtime",
            node_type="model_inference",
            scope="subject",
            role="evidence",
            status="partial",
            source=source_identity(
                source_kind="repository_file",
                path_or_uri=str(external_evaluator_manifest["producer"]["path"]),
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=str(external_evaluator_manifest["producer"]["sha256"]),
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=["state:llamaguard-dataset"],
            outputs=[
                "state:external-evaluator-manifest",
                "state:external-raw-evidence",
            ],
            mutation_authority="release_evidence",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:llamaguard-summary-adapter",
            node_type="artifact_builder",
            scope="subject",
            role="evidence",
            status="complete",
            source=source_identity(
                source_kind="repository_file",
                path_or_uri="PULSE_safe_pack_v0/tools/adapters/llamaguard_ingest.py",
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=str(external_adapter_sha),
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:external-evaluator-manifest",
                "state:external-raw-evidence",
                "state:external-thresholds",
                "state:llamaguard-dataset",
            ],
            outputs=["state:external-summary"],
            mutation_authority="release_evidence",
            observed_mutation=True,
        ),
        make_compute_node(
            node_id="compute:offline-observer",
            node_type="report_builder",
            scope="analysis_observer",
            role="observer",
            status="complete",
            source=source_identity(
                source_kind="repository_file",
                path_or_uri="tools/pulsemech_compute_binding_analyzer_core_v0.py",
                revision=TOOL_VERSION,
                sha256=analyzer_core_source_sha256,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:artifact-binding",
                "state:complete-package",
                "state:final-status",
                "state:independent-verification",
                "state:package-completeness",
                "state:package-inventory",
                "state:preservation-manifest",
                "state:release-decision",
            ],
            outputs=[],
            mutation_authority="none",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:package-assembler",
            node_type="artifact_builder",
            scope="subject",
            role="preservation",
            status="partial",
            source=source_identity(
                source_kind="unknown",
                path_or_uri=str(assembler_name) if assembler_name else None,
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:artifact-binding",
                "state:candidate-index",
                "state:final-status",
                "state:recorded-verifier-report",
                "state:release-authority-manifest",
                "state:release-decision",
                "state:report-card",
            ],
            outputs=["state:complete-package", "state:package-inventory"],
            mutation_authority="preservation_output",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:package-completeness-checker",
            node_type="package_verifier",
            scope="subject",
            role="preservation",
            status="partial",
            source=source_identity(
                source_kind="unknown",
                path_or_uri=str(completeness_tool) if completeness_tool else None,
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=["state:complete-package"],
            outputs=["state:package-completeness"],
            mutation_authority="preservation_output",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:package-verifier",
            node_type="package_verifier",
            scope="subject",
            role="preservation",
            status="partial",
            source=source_identity(
                source_kind="unknown",
                path_or_uri=str(verification_tool) if verification_tool else None,
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=["state:complete-package"],
            outputs=["state:independent-verification"],
            mutation_authority="preservation_output",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:recorded-candidate-builder",
            node_type="artifact_builder",
            scope="subject",
            role="evidence",
            status="complete",
            source=source_identity(
                source_kind="repository_file",
                path_or_uri=str(candidate_source["tool_path"]),
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=str(candidate_source["tool_sha256"]),
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:external-attestation-bundle",
                "state:external-attestation-verifier",
                "state:external-raw-evidence",
                "state:external-signer-policy",
                "state:external-summary",
                "state:external-summary-envelope",
                "state:external-thresholds",
                "state:policy",
                "state:refusal-delta-source",
                "state:registry",
                "state:required-gate-evidence",
                "state:status-baseline",
            ],
            outputs=[
                "state:candidate-detector",
                "state:candidate-external",
                "state:candidate-index",
                "state:candidate-refusal",
            ],
            mutation_authority="candidate_state",
            observed_mutation=True,
        ),
        make_compute_node(
            node_id="compute:recorded-evidence-verifier",
            node_type="verifier_execution",
            scope="subject",
            role="evidence",
            status="partial",
            source=source_identity(
                source_kind="unknown",
                path_or_uri=None,
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:candidate-detector",
                "state:candidate-external",
                "state:candidate-refusal",
                "state:evidence-manifest",
                "state:policy",
                "state:registry",
            ],
            outputs=["state:recorded-verifier-report"],
            mutation_authority="verifier_state",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:release-authority-manifest-builder",
            node_type="report_builder",
            scope="subject",
            role="advisory",
            status="partial",
            source=source_identity(
                source_kind="unknown",
                path_or_uri=None,
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:final-status",
                "state:materialized-gate-set",
                "state:policy",
                "state:registry",
                "state:strict-gate-result",
            ],
            outputs=["state:release-authority-manifest"],
            mutation_authority="advisory_output",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:release-decision-materializer",
            node_type="artifact_builder",
            scope="subject",
            role="transition",
            status="partial",
            source=source_identity(
                source_kind="unknown",
                path_or_uri=str(decision_producer_name) if decision_producer_name else None,
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=[
                "state:final-status",
                "state:materialized-gate-set",
                "state:policy",
                "state:strict-gate-result",
            ],
            outputs=["state:release-decision"],
            mutation_authority="release_decision",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:release-required-materializer",
            node_type="materializer_execution",
            scope="subject",
            role="transition",
            status="partial",
            source=source_identity(
                source_kind="unknown",
                path_or_uri=None,
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=None,
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=["state:policy", "state:recorded-verifier-report", "state:status-baseline"],
            outputs=["state:final-status", "state:materialized-gate-set"],
            mutation_authority="final_status",
            observed_mutation=False,
        ),
        make_compute_node(
            node_id="compute:required-gate-evaluator",
            node_type="verifier_execution",
            scope="subject",
            role="evidence",
            status="partial",
            source=source_identity(
                source_kind="repository_file",
                path_or_uri=str(required_producer["tool_path"]),
                revision=EXPECTED_SOURCE_COMMIT,
                sha256=str(required_producer["tool_sha256"]),
            ),
            subject_run_key=subject_run_key,
            analysis_run_key=analysis_run_key,
            inputs=["state:policy", "state:registry"],
            outputs=["state:required-gate-evidence"],
            mutation_authority="release_evidence",
            observed_mutation=False,
        ),
    ]

    states_by_id = {state["state_id"]: state for state in states}
    if len(states_by_id) != len(states):
        raise BuilderError("internal_duplicate_state_id")

    # Build exact observed state/compute relations. The edge digest is always the
    # digest of the state carried by the edge.
    relation_specs: list[tuple[str, str, str]] = []
    input_edge_types: dict[tuple[str, str], str] = {
        ("compute:check-gates", "state:final-status"): "enforces",
        ("compute:check-gates", "state:materialized-gate-set"): "enforces",
        ("compute:check-gates", "state:policy"): "enforces",
        ("compute:check-gates", "state:registry"): "enforces",
        ("compute:package-completeness-checker", "state:complete-package"): "verifies",
        ("compute:package-verifier", "state:complete-package"): "verifies",
        ("compute:recorded-evidence-verifier", "state:candidate-detector"): "verifies",
        ("compute:recorded-evidence-verifier", "state:candidate-external"): "verifies",
        ("compute:recorded-evidence-verifier", "state:candidate-refusal"): "verifies",
        ("compute:recorded-evidence-verifier", "state:evidence-manifest"): "verifies",
        ("compute:recorded-evidence-verifier", "state:policy"): "verifies",
        ("compute:recorded-evidence-verifier", "state:registry"): "verifies",
    }
    output_edge_types: dict[tuple[str, str], str] = {
        ("compute:release-required-materializer", "state:materialized-gate-set"): "materializes",
        ("compute:release-required-materializer", "state:final-status"): "folds",
        ("compute:release-authority-manifest-builder", "state:release-authority-manifest"): "publishes",
        ("compute:artifact-binding-builder", "state:artifact-binding"): "preserves",
        ("compute:package-assembler", "state:complete-package"): "preserves",
        ("compute:package-assembler", "state:package-inventory"): "preserves",
        ("compute:package-completeness-checker", "state:package-completeness"): "preserves",
        ("compute:package-verifier", "state:independent-verification"): "preserves",
    }

    for node in nodes:
        node_id = node["node_id"]
        for state_id in node["input_state_ids"]:
            relation_specs.append(
                (state_id, node_id, input_edge_types.get((node_id, state_id), "reads"))
            )
        for state_id in node["output_state_ids"]:
            relation_specs.append(
                (node_id, state_id, output_edge_types.get((node_id, state_id), "produces"))
            )

    relation_specs = sorted(set(relation_specs))
    edges: list[dict[str, Any]] = []
    for index, (from_id, to_id, edge_type) in enumerate(relation_specs, start=1):
        state_id = from_id if from_id.startswith("state:") else to_id
        digest = states_by_id[state_id].get("sha256")
        if not isinstance(digest, str):
            raise BuilderError(f"observed_edge_state_digest_missing: {state_id}")
        edges.append(
            make_edge(
                edge_id=f"edge:{index:03d}",
                from_id=from_id,
                to_id=to_id,
                edge_type=edge_type,
                digest=digest,
            )
        )

    findings: list[dict[str, Any]] = []
    for node in nodes:
        if node["execution_scope"] != "subject":
            continue
        source = node["source_identity"]
        if source.get("source_path_or_uri") is None:
            findings.append(
                finding(
                    finding_id="compute_source_identity_missing",
                    severity="advisory",
                    node_id=node["node_id"],
                    message=(
                        "The preserved package does not record an exact source "
                        "path or URI for this subject-run compute node."
                    ),
                    evidence_refs=[node["node_id"] + ".source_identity"],
                )
            )
        if source.get("source_sha256") is None:
            findings.append(
                finding(
                    finding_id="compute_source_digest_missing",
                    severity="advisory",
                    node_id=node["node_id"],
                    message=(
                        "The preserved package does not record an exact source "
                        "digest for this subject-run compute node."
                    ),
                    evidence_refs=[node["node_id"] + ".source_identity"],
                )
            )
        if node["binding_class"] == "unknown":
            findings.append(
                finding(
                    finding_id="unknown_compute_binding",
                    severity="advisory",
                    node_id=node["node_id"],
                    message=(
                        "The artifact-observed package preserves this compute "
                        "relation only partially; runtime or source evidence is "
                        "required for complete binding."
                    ),
                    evidence_refs=node["input_state_ids"] + node["output_state_ids"],
                )
            )

    findings.append(
        finding(
            finding_id="required_gate_source_unresolved",
            severity="advisory",
            node_id="compute:required-gate-evaluator",
            message=(
                "The complete package preserves the aggregated required-gate "
                "evidence report, but not every underlying evaluation input and "
                "execution record needed for a complete runtime binding."
            ),
            evidence_refs=[
                "state:required-gate-evidence",
                "artifacts/required_gate_evidence_v0.json:gates",
            ],
        )
    )
    findings.append(
        finding(
            finding_id="declared_binding_not_observed",
            severity="advisory",
            node_id="compute:llamaguard-runtime",
            message=(
                "The preserved evaluator manifest records the exact model ID and "
                "revision but not a content digest for the model artifact; the "
                "model-inference input binding therefore remains partial."
            ),
            evidence_refs=[
                "state:external-evaluator-manifest",
                "artifacts/external/llamaguard_evaluator_manifest_v0.json:model",
            ],
        )
    )
    findings.append(
        finding(
            finding_id="resource_measurement_missing",
            severity="advisory",
            message=(
                "The preserved artifact package does not contain per-node compute "
                "resource measurements; resource_summary.axes is therefore empty."
            ),
            evidence_refs=["resource_summary.axes"],
        )
    )

    # Deterministic ordering required by the report validator.
    nodes = sorted(nodes, key=lambda item: item["node_id"])
    states = sorted(states, key=lambda item: item["state_id"])
    edges = sorted(edges, key=lambda item: item["edge_id"])
    findings = sorted(
        findings,
        key=lambda item: (
            item["finding_id"],
            item["node_id"] or "",
            item["state_id"] or "",
            item["edge_id"] or "",
            item["message"],
        ),
    )

    subject_nodes = [node for node in nodes if node["execution_scope"] == "subject"]
    observer_nodes = [node for node in nodes if node["execution_scope"] == "analysis_observer"]
    class_counts = Counter(node["binding_class"] for node in subject_nodes)

    core_decision_nodes = {
        "compute:candidate-status-builder",
        "compute:recorded-candidate-builder",
        "compute:evidence-manifest-builder",
        "compute:recorded-evidence-verifier",
        "compute:release-required-materializer",
        "compute:check-gates",
        "compute:release-decision-materializer",
    }
    node_by_id = {node["node_id"]: node for node in nodes}
    decision_closure_complete = all(
        node_by_id[node_id]["binding_status"] == "complete"
        for node_id in core_decision_nodes
    )
    authority_binding_complete = all(
        node["binding_status"] == "complete"
        for node in subject_nodes
        if node["mutation_authority"] in AUTHORITATIVE_MUTATION_CLASSES
    ) and not any(
        node["unbound_authoritative_mutation"] for node in subject_nodes
    )

    inputs = [
        {
            "role": "artifact_binding",
            "path_or_uri": package_uri("artifacts/artifact_provenance_binding_v0.json"),
            "sha256": artifact_binding_record["sha256"],
            "size_bytes": artifact_binding_record["size_bytes"],
        },
        {
            "role": "candidate_record",
            "path_or_uri": package_uri("artifacts/recorded_release_candidate_index_v0.json"),
            "sha256": candidate_index_record["sha256"],
            "size_bytes": candidate_index_record["size_bytes"],
        },
        {
            "role": "evidence_manifest",
            "path_or_uri": package_uri("artifacts/release_evidence_input_manifest_v0.json"),
            "sha256": evidence_manifest_record["sha256"],
            "size_bytes": evidence_manifest_record["size_bytes"],
        },
        {
            "role": "other",
            "path_or_uri": package_uri("artifacts/external/llamaguard_attestation_verifier_v1.json"),
            "sha256": external_attestation_verifier_record["sha256"],
            "size_bytes": external_attestation_verifier_record["size_bytes"],
        },
        {
            "role": "other",
            "path_or_uri": package_uri("artifacts/external/llamaguard_evaluator_manifest_v0.json"),
            "sha256": external_evaluator_manifest_record["sha256"],
            "size_bytes": external_evaluator_manifest_record["size_bytes"],
        },
        {
            "role": "other",
            "path_or_uri": package_uri("artifacts/external/llamaguard_raw.jsonl"),
            "sha256": external_raw_record["sha256"],
            "size_bytes": external_raw_record["size_bytes"],
        },
        {
            "role": "other",
            "path_or_uri": package_uri("artifacts/external/llamaguard_summary.bundle.json"),
            "sha256": external_bundle_record["sha256"],
            "size_bytes": external_bundle_record["size_bytes"],
        },
        {
            "role": "other",
            "path_or_uri": package_uri("artifacts/external/llamaguard_summary.envelope.json"),
            "sha256": external_envelope_record["sha256"],
            "size_bytes": external_envelope_record["size_bytes"],
        },
        {
            "role": "final_status",
            "path_or_uri": package_uri("artifacts/status.json"),
            "sha256": status_record["sha256"],
            "size_bytes": status_record["size_bytes"],
        },
        {
            "role": "independent_verification_report",
            "path_or_uri": outer_artifact_uri(VERIFICATION_ARCHIVE_NAME) + "!/release_grade_reference_package_verification_v0.json",
            "sha256": sha256_bytes(bundle.verification_report_bytes),
            "size_bytes": len(bundle.verification_report_bytes),
        },
        {
            "role": "other",
            "path_or_uri": ARCHIVE_DISPLAY_PATH,
            "sha256": bundle.archive_sha256,
            "size_bytes": bundle.archive_size,
        },
        {
            "role": "other",
            "path_or_uri": outer_artifact_uri(COMPLETE_PACKAGE_NAME),
            "sha256": EXPECTED_ARTIFACTS[COMPLETE_PACKAGE_NAME]["sha256"],
            "size_bytes": EXPECTED_ARTIFACTS[COMPLETE_PACKAGE_NAME]["size_bytes"],
        },
        {
            "role": "other",
            "path_or_uri": package_uri("artifacts/required_gate_evidence_v0.json"),
            "sha256": required_record["sha256"],
            "size_bytes": required_record["size_bytes"],
        },
        {
            "role": "package_completeness_report",
            "path_or_uri": outer_artifact_uri(COMPLETENESS_ARCHIVE_NAME) + "!/release_grade_package_completeness_v1.json",
            "sha256": sha256_bytes(bundle.completeness_report_bytes),
            "size_bytes": len(bundle.completeness_report_bytes),
        },
        {
            "role": "package_inventory",
            "path_or_uri": package_uri("package_digest_inventory_v0.json"),
            "sha256": sha256_bytes(package_inventory_bytes),
            "size_bytes": len(package_inventory_bytes),
        },
        {
            "role": "preservation_manifest",
            "path_or_uri": PRESERVATION_MANIFEST_DISPLAY_PATH,
            "sha256": sha256_bytes(bundle.manifest_bytes),
            "size_bytes": len(bundle.manifest_bytes),
        },
        {
            "role": "release_decision",
            "path_or_uri": package_uri("artifacts/release_decision_v0.json"),
            "sha256": decision_record["sha256"],
            "size_bytes": decision_record["size_bytes"],
        },
        {
            "role": "run_metadata",
            "path_or_uri": package_uri("run_metadata_v0.json"),
            "sha256": sha256_bytes(run_metadata_bytes),
            "size_bytes": len(run_metadata_bytes),
        },
        {
            "role": "verifier_report",
            "path_or_uri": package_uri("artifacts/recorded_release_evidence_verifier_v0.json"),
            "sha256": verifier_record["sha256"],
            "size_bytes": verifier_record["size_bytes"],
        },
    ]
    inputs = sorted(
        inputs,
        key=lambda item: (item["role"], item["path_or_uri"], item["sha256"]),
    )

    summary = {
        "subject_compute_nodes": len(subject_nodes),
        "observer_nodes": len(observer_nodes),
        **{
            field: class_counts.get(binding_class, 0)
            for binding_class, field in SUMMARY_COUNT_FIELDS.items()
        },
        "unbound_authoritative_mutation_count": sum(
            1
            for node in subject_nodes
            if node["unbound_authoritative_mutation"] is True
        ),
        "decision_closure_complete": decision_closure_complete,
        "authority_binding_complete": authority_binding_complete,
        "resource_measurement_status": "none",
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "report_type": REPORT_TYPE,
        "record_status": "observed",
        "tool": {
            "id": TOOL_ID,
            "version": TOOL_VERSION,
            "source_sha256": builder_source_sha256,
        },
        "analysis_boundary": {
            "analysis_level": "artifact_observed",
            "subject_run_key": subject_run_key,
            "analysis_run_key": analysis_run_key,
            "observer_in_subject_totals": False,
        },
        "subject": {
            "repository": EXPECTED_REPOSITORY,
            "workflow": EXPECTED_WORKFLOW,
            "workflow_run_id": EXPECTED_RUN_ID,
            "workflow_run_number": EXPECTED_RUN_NUMBER,
            "workflow_run_attempt": EXPECTED_RUN_ATTEMPT,
            "source_commit": EXPECTED_SOURCE_COMMIT,
            "release_candidate_id": release_candidate,
            "run_mode": str(manifest["run_mode"]),
            "active_policy_sets": sorted(release_decision["active_gate_sets"]),
            "policy_id": str(policy_id),
            "policy_sha256": str(policy_sha),
            "materialized_gate_set_sha256": str(materialized_sha),
            "final_status_sha256": status_record["sha256"],
            "release_decision_sha256": decision_record["sha256"],
            "decision": decision_value,
        },
        "inputs": inputs,
        "compute_nodes": nodes,
        "state_nodes": states,
        "edges": edges,
        "resource_summary": {"axes": {}},
        "summary": summary,
        "findings": findings,
        "errors": [],
        "ok": True,
    }


# ---------------------------------------------------------------------------
# Existing contract validator integration
# ---------------------------------------------------------------------------


def validate_generated_report(
    *,
    schema_path: Path,
    validator_path: Path,
    rendered_report: str,
) -> dict[str, Any]:
    if not schema_path.is_file():
        raise BuilderError(f"schema_missing: {schema_path}")
    if not validator_path.is_file():
        raise BuilderError(f"validator_missing: {validator_path}")

    with tempfile.TemporaryDirectory(prefix="pulsemech-compute-binding-") as raw_tmp:
        tmp = Path(raw_tmp)
        report_path = tmp / "pulsemech_compute_binding_report_v0.json"
        report_path.write_text(rendered_report, encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(validator_path),
                "--schema",
                str(schema_path),
                "--report",
                str(report_path),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if result.stderr and "Traceback" in result.stderr:
            raise BuilderError(
                "validator_traceback: " + result.stderr.strip()
            )

        try:
            diagnostic = json.loads(
                result.stdout,
                object_pairs_hook=reject_duplicate_keys,
                parse_constant=reject_non_finite,
            )
        except Exception as exc:
            raise BuilderError(
                "validator_diagnostic_invalid: "
                f"returncode={result.returncode} stdout={result.stdout!r} "
                f"stderr={result.stderr!r}"
            ) from exc

        if (
            result.returncode != 0
            or not isinstance(diagnostic, dict)
            or diagnostic.get("ok") is not True
        ):
            raise BuilderError(
                "generated_report_rejected: "
                + json.dumps(diagnostic, sort_keys=True)
            )

        return diagnostic


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic, fixed-source, offline, read-only "
            "PULSEmech compute-binding report from the preserved PULSE CI "
            "#6066 release-grade package."
        )
    )
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--readme", default=str(DEFAULT_README))
    parser.add_argument("--sha256sums", default=str(DEFAULT_SHA256SUMS))
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--validator", default=str(DEFAULT_VALIDATOR))
    parser.add_argument(
        "--analysis-run-key",
        default=EXPECTED_ANALYSIS_RUN_KEY,
        help="Explicit deterministic identity for the offline analysis run.",
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON path outside the preserved subject package.",
    )
    return parser.parse_args()


def main(
    *,
    producer_source_path: Path | None = None,
    analyzer_core_source_sha256: str | None = None,
) -> int:
    args = parse_args()

    archive = Path(args.archive)
    manifest = Path(args.manifest)
    readme = Path(args.readme)
    sha256sums = Path(args.sha256sums)
    schema = Path(args.schema)
    validator = Path(args.validator)
    output = Path(args.output) if args.output else None

    try:
        reject_unsafe_output(
            output,
            archive=archive,
            manifest=manifest,
            readme=readme,
            sha256sums=sha256sums,
            schema=schema,
            validator=validator,
        )

        if not args.analysis_run_key or args.analysis_run_key == EXPECTED_RUN_KEY:
            raise BuilderError("analysis_run_key_invalid_or_matches_subject")

        bundle = load_observed_bundle(
            archive_path=archive,
            manifest_path=manifest,
            readme_path=readme,
            sha256sums_path=sha256sums,
            expected_archive_sha256=EXPECTED_ARCHIVE_SHA256,
            expected_archive_size=EXPECTED_ARCHIVE_SIZE,
        )

        producer_path = producer_source_path or Path(__file__)
        builder_source_sha = sha256_file(producer_path)
        core_source_sha = (
            analyzer_core_source_sha256
            or sha256_file(Path(__file__))
        )
        report = build_report(
            bundle,
            analysis_run_key=str(args.analysis_run_key),
            builder_source_sha256=builder_source_sha,
            analyzer_core_source_sha256=core_source_sha,
        )
        rendered = render_json(report)

        validate_generated_report(
            schema_path=schema,
            validator_path=validator,
            rendered_report=rendered,
        )

        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")

        sys.stdout.write(rendered)
        return 0

    except BuilderError as exc:
        diagnostic = {
            "tool": TOOL_ID,
            "ok": False,
            "errors": [str(exc)],
        }
        sys.stderr.write(render_json(diagnostic))
        return 1
    except Exception as exc:
        diagnostic = {
            "tool": TOOL_ID,
            "ok": False,
            "errors": [f"unexpected_error: {exc}"],
        }
        sys.stderr.write(render_json(diagnostic))
        return 2


class RuntimeIndexError(ValueError):
    """Contradictory or unusable input to runtime evidence indexing."""


@dataclass(frozen=True)
class RuntimePacketSource:
    locator: str
    data: bytes


_SUBJECT_FIELDS = (
    "repository", "workflow_name", "workflow_run_id", "workflow_run_number",
    "workflow_run_attempt", "subject_run_key", "source_commit",
    "release_candidate_id", "run_mode", "active_policy_sets",
)
_NUMERIC_SUBJECT_FIELDS = frozenset({
    "workflow_run_id", "workflow_run_number", "workflow_run_attempt",
})
_RECORD_KINDS = {
    "executions": ("execution_id", "execution:"),
    "state_observations": ("state_id", "state:"),
    "external_calls": ("call_id", "call:"),
    "model_inferences": ("inference_id", "inference:"),
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_RECORD_SUFFIX = re.compile(r"[A-Za-z0-9._:/@+-]+\Z")
_OBSERVER_SCOPES = frozenset({"analysis_observer", "observation_collector"})


def _runtime_canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise RuntimeIndexError("runtime_value_not_canonicalizable") from exc


def _runtime_copy(value: Any) -> Any:
    return json.loads(_runtime_canonical(value))


def _runtime_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _runtime_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeIndexError(f"{label}_not_object")
    return value


def _runtime_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeIndexError(f"{label}_not_nonempty_string")
    return value


def _runtime_nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise RuntimeIndexError(f"{label}_not_nonnegative_integer")
    return value


def _runtime_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise RuntimeIndexError(f"{label}_not_string_list")
    if len(value) != len(set(value)):
        raise RuntimeIndexError(f"{label}_contains_duplicates")
    return list(value)


def _runtime_load(data: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise RuntimeIndexError("runtime_packet_duplicate_json_key")
            result[key] = value
        return result

    def nonfinite(_text: str) -> None:
        raise RuntimeIndexError("runtime_packet_nonfinite_number")

    if type(data) is not bytes:
        raise RuntimeIndexError("runtime_packet_requires_immutable_bytes")
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
            parse_constant=nonfinite,
        )
    except RuntimeIndexError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise RuntimeIndexError("runtime_packet_json_invalid") from exc
    document = _runtime_object(value, "runtime_packet")
    _runtime_canonical(document)  # Also rejects overflowed floating-point values.
    return document


def _runtime_subject(value: Any) -> dict[str, Any]:
    subject = _runtime_object(value, "runtime_subject")
    projected: dict[str, Any] = {}
    for field in _SUBJECT_FIELDS:
        item = subject.get(field)
        if field in _NUMERIC_SUBJECT_FIELDS:
            _runtime_nonnegative_int(item, f"subject_{field}")
            if item == 0:
                raise RuntimeIndexError(f"subject_{field}_must_be_positive")
        elif field == "active_policy_sets":
            _runtime_string_list(item, "subject_active_policy_sets")
            if not item:
                raise RuntimeIndexError("subject_active_policy_sets_empty")
        else:
            _runtime_text(item, f"subject_{field}")
        projected[field] = _runtime_copy(item)
    if not _SHA40.fullmatch(projected["source_commit"]):
        raise RuntimeIndexError("subject_source_commit_invalid")
    return projected


def _runtime_authority(value: Any, source_commit: str) -> dict[str, Any]:
    authority = _runtime_object(value, "runtime_authority_inputs")
    if set(authority) != {"workflow", "policy", "gate_registry"}:
        raise RuntimeIndexError("runtime_authority_roles_mismatch")
    for role in sorted(authority):
        row = _runtime_object(authority[role], f"authority_{role}")
        if set(row) != {"role", "path", "source_commit", "sha256"}:
            raise RuntimeIndexError("runtime_authority_descriptor_fields_mismatch")
        if row["role"] != role or row["source_commit"] != source_commit:
            raise RuntimeIndexError("runtime_authority_source_mismatch")
        _runtime_text(row["path"], f"authority_{role}_path")
        if not isinstance(row["sha256"], str) or not _SHA256.fullmatch(row["sha256"]):
            raise RuntimeIndexError("runtime_authority_digest_invalid")
    return _runtime_copy(authority)


def _runtime_record_id(value: Any, prefix: str) -> str:
    identifier = _runtime_text(value, "runtime_record_id")
    if not identifier.startswith(prefix) or not _RECORD_SUFFIX.fullmatch(
        identifier[len(prefix):]
    ):
        raise RuntimeIndexError("runtime_record_id_invalid")
    return identifier


def index_runtime_packet_sources(
    sources: Iterable[RuntimePacketSource], *, expected_subject: dict[str, Any],
    expected_authority_inputs: dict[str, Any],
) -> dict[str, Any]:
    """Index exact packet bytes without inventing terminal observation closure.

    expected_subject and expected_authority_inputs come from independently
    verified subject/context inputs, never from the first runtime packet itself.
    This function checks descriptor agreement, NOT historical source authenticity.
    The caller must separately run the unchanged runtime packet validator on the
    same immutable input bytes. No caller-provided parsed packet is accepted.
    """
    subject = _runtime_subject(expected_subject)
    authority = _runtime_authority(expected_authority_inputs, subject["source_commit"])
    parsed: list[tuple[RuntimePacketSource, dict[str, Any], str]] = []
    locators: set[str] = set()
    ids: set[str] = set()
    sequences: set[int] = set()
    statuses: set[str] = set()
    for source in sources:
        if not isinstance(source, RuntimePacketSource):
            raise RuntimeIndexError("runtime_packet_source_type_invalid")
        locator = _runtime_text(source.locator, "runtime_source_locator")
        if locator in locators:
            raise RuntimeIndexError("runtime_source_locator_duplicate")
        locators.add(locator)
        packet = _runtime_load(source.data)
        if packet.get("schema_version") != "pulsemech_compute_runtime_observation_packet_v0":
            raise RuntimeIndexError("runtime_packet_schema_identity_mismatch")
        if packet.get("packet_type") != "pulsemech_compute_runtime_observation_packet":
            raise RuntimeIndexError("runtime_packet_type_mismatch")
        status = packet.get("record_status")
        if status not in {"example", "observed"}:
            raise RuntimeIndexError("runtime_packet_record_status_invalid")
        statuses.add(status)
        if packet.get("ok") is not True or packet.get("errors") != []:
            raise RuntimeIndexError("runtime_packet_reports_failure")
        if _runtime_subject(packet.get("subject")) != subject:
            raise RuntimeIndexError("runtime_packet_subject_context_mismatch")
        if _runtime_authority(packet.get("authority_inputs"), subject["source_commit"]) != authority:
            raise RuntimeIndexError("runtime_packet_authority_context_mismatch")
        identity = _runtime_object(packet.get("packet_identity"), "packet_identity")
        identifier = _runtime_record_id(identity.get("packet_id"), "runtime-observation:")
        sequence = _runtime_nonnegative_int(identity.get("packet_sequence"), "packet_sequence")
        if identity.get("subject_run_key") != subject["subject_run_key"]:
            raise RuntimeIndexError("runtime_packet_identity_subject_mismatch")
        if identifier in ids or sequence in sequences:
            raise RuntimeIndexError("runtime_packet_duplicate_identity_or_sequence")
        ids.add(identifier)
        sequences.add(sequence)
        previous = identity.get("previous_packet_sha256")
        if sequence == 0:
            if previous is not None:
                raise RuntimeIndexError("runtime_root_predecessor_not_null")
        elif not isinstance(previous, str) or not _SHA256.fullmatch(previous):
            raise RuntimeIndexError("runtime_predecessor_digest_invalid")
        parsed.append((source, packet, _runtime_sha(source.data)))
    if not parsed:
        raise RuntimeIndexError("runtime_packet_set_empty")
    if len(statuses) != 1:
        raise RuntimeIndexError("runtime_packet_mixed_record_status")
    parsed.sort(key=lambda item: item[1]["packet_identity"]["packet_sequence"])
    all_digests = {digest for _, _, digest in parsed}
    previous_sequence: int | None = None
    previous_digest: str | None = None
    missing_ranges: list[dict[str, int]] = []
    inventory: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {name: {} for name in _RECORD_KINDS}
    collectors: list[dict[str, Any]] = []
    for source, packet, digest in parsed:
        identity = packet["packet_identity"]
        sequence = identity["packet_sequence"]
        predecessor = identity["previous_packet_sha256"]
        expected_sequence = 0 if previous_sequence is None else previous_sequence + 1
        if sequence != expected_sequence:
            missing_ranges.append({"first_sequence": expected_sequence, "last_sequence": sequence - 1})
            if predecessor in all_digests:
                raise RuntimeIndexError("runtime_predecessor_contradicts_sequence_gap")
        elif previous_sequence is not None and predecessor != previous_digest:
            raise RuntimeIndexError("runtime_predecessor_digest_mismatch")
        previous_sequence, previous_digest = sequence, digest
        coverage = _runtime_object(packet.get("coverage"), "runtime_coverage")
        overall = coverage.get("coverage_status")
        if overall not in {"complete", "partial", "unknown"}:
            raise RuntimeIndexError("runtime_overall_coverage_invalid")
        inventory.append({
            "source_locator": source.locator, "sha256": digest,
            "size_bytes": len(source.data), "packet_id": identity["packet_id"],
            "packet_sequence": sequence, "previous_packet_sha256": predecessor,
            "overall_coverage_status": overall,
        })
        for kind, (key, prefix) in _RECORD_KINDS.items():
            rows = packet.get(kind)
            if not isinstance(rows, list):
                raise RuntimeIndexError(f"runtime_{kind}_not_array")
            within_packet: set[str] = set()
            for position, value in enumerate(rows):
                row = _runtime_object(value, f"runtime_{kind}_record")
                identifier = _runtime_record_id(row.get(key), prefix)
                if identifier in within_packet:
                    raise RuntimeIndexError("runtime_duplicate_record_within_packet")
                within_packet.add(identifier)
                reference = {"packet_sha256": digest, "json_pointer": f"/{kind}/{position}"}
                old = records[kind].get(identifier)
                if old is None:
                    records[kind][identifier] = {"record": _runtime_copy(row), "source_refs": [reference]}
                else:
                    if _runtime_canonical(old["record"]) != _runtime_canonical(row):
                        raise RuntimeIndexError("runtime_conflicting_repeated_record")
                    old["source_refs"].append(reference)
        boundary = _runtime_object(packet.get("observation_boundary"), "runtime_observation_boundary")
        if boundary.get("subject_run_key") != subject["subject_run_key"]:
            raise RuntimeIndexError("runtime_boundary_subject_mismatch")
        if boundary.get("observer_in_subject_totals") is not False:
            raise RuntimeIndexError("runtime_observer_in_subject_totals")
        collector_id = _runtime_record_id(boundary.get("collector_execution_id"), "execution:")
        collector = next((r for r in packet["executions"] if r["execution_id"] == collector_id), None)
        if collector is None or collector.get("execution_scope") != "observation_collector":
            raise RuntimeIndexError("runtime_collector_identity_or_scope_mismatch")
        binding = _runtime_object(collector.get("run_binding"), "runtime_collector_binding")
        if binding.get("execution_run_key") != boundary.get("collector_run_key"):
            raise RuntimeIndexError("runtime_collector_run_key_mismatch")
        producer = _runtime_object(packet.get("producer"), "runtime_producer")
        if producer.get("producer_execution_id") != collector_id:
            raise RuntimeIndexError("runtime_producer_collector_mismatch")
        collectors.append({
            "packet_sha256": digest, "collector_execution_id": collector_id,
            "collector_run_key": boundary["collector_run_key"],
            "producer": _runtime_copy(producer),
            "observation_boundary": _runtime_copy(boundary),
        })
    execution_rows = {key: item["record"] for key, item in records["executions"].items()}
    state_rows = {key: item["record"] for key, item in records["state_observations"].items()}
    for identifier, execution in execution_rows.items():
        scope = execution.get("execution_scope")
        if scope not in _OBSERVER_SCOPES | {"subject"}:
            raise RuntimeIndexError("runtime_execution_scope_invalid")
        binding = _runtime_object(execution.get("run_binding"), "runtime_execution_binding")
        if binding.get("subject_run_key") != subject["subject_run_key"] or binding.get("binding_complete") is not True:
            raise RuntimeIndexError("runtime_execution_subject_binding_incomplete")
        if scope == "subject" and (
            binding.get("execution_run_key") != subject["subject_run_key"]
            or binding.get("binding_mode") != "current_subject_run"
            or execution.get("declared_role") == "observer"
        ):
            raise RuntimeIndexError("runtime_subject_observer_mixing")
        if scope in _OBSERVER_SCOPES and execution.get("declared_role") != "observer":
            raise RuntimeIndexError("runtime_observer_role_mismatch")
        parent_id = execution.get("parent_execution_id")
        if parent_id is not None:
            parent = execution_rows.get(parent_id)
            if parent is None or parent_id == identifier:
                raise RuntimeIndexError("runtime_parent_missing_or_self")
            if parent.get("execution_scope") != scope:
                raise RuntimeIndexError("runtime_parent_scope_mismatch")
        for field in ("input_state_ids", "output_state_ids"):
            linked = _runtime_string_list(execution.get(field), f"runtime_{field}")
            if any(state_id not in state_rows for state_id in linked):
                raise RuntimeIndexError("runtime_execution_state_missing")
    # Reject arbitrary parent cycles, including cycles longer than two nodes.
    completed: set[str] = set()
    for identifier in sorted(execution_rows):
        path: set[str] = set()
        cursor: str | None = identifier
        while cursor is not None and cursor not in completed:
            if cursor in path:
                raise RuntimeIndexError("runtime_parent_cycle")
            path.add(cursor)
            cursor = execution_rows[cursor].get("parent_execution_id")
        completed.update(path)
    # v0 permits a producer to record internal/request state as well as
    # exported outputs. Preserve that declaration without inventing an output.
    related_by_execution = {rid: set(row["input_state_ids"]) | set(row["output_state_ids"])
                            for rid, row in execution_rows.items()}
    for kind in ("external_calls", "model_inferences"):
        for entry in records[kind].values():
            row = entry["record"]
            parent = row.get("parent_execution_id")
            if parent in related_by_execution:
                ins, outs = runtime_activity_io(kind, row)
                related_by_execution[parent].update(ins)
                related_by_execution[parent].update(outs)
    for identifier, state in state_rows.items():
        if state.get("subject_run_key") != subject["subject_run_key"]:
            raise RuntimeIndexError("runtime_state_subject_mismatch")
        producer_id = state.get("producer_execution_id")
        if producer_id is not None and (
            producer_id not in execution_rows or identifier not in related_by_execution[producer_id]
        ):
            raise RuntimeIndexError("runtime_state_producer_mismatch")
    for kind in ("external_calls", "model_inferences"):
        for entry in records[kind].values():
            if entry["record"].get("parent_execution_id") not in execution_rows:
                raise RuntimeIndexError("runtime_activity_parent_missing")
    for kind in records:
        records[kind] = dict(sorted(records[kind].items()))
        for entry in records[kind].values():
            entry["source_refs"].sort(key=lambda item: (item["packet_sha256"], item["json_pointer"]))
    return {
        "internal_profile": "pulsemech_runtime_packet_index_v0",
        "record_status": next(iter(statuses)), "subject_context": subject,
        "authority_inputs": authority, "packet_inventory": inventory,
        "supplied_sequence_status": "rooted_contiguous" if not missing_ranges else "incomplete",
        "missing_sequence_ranges": missing_ranges,
        # No terminal closure proof exists in the v0 packet identity itself.
        "terminal_observation_extent": "unknown", "records": records,
        "collectors": collectors,
        "counts": {
            "subject_execution_occurrences": sum(r["execution_scope"] == "subject" for r in execution_rows.values()),
            "observer_execution_occurrences": sum(r["execution_scope"] in _OBSERVER_SCOPES for r in execution_rows.values()),
            "unique_state_records": len(state_rows),
            "supplied_packet_count": len(inventory),
        },
    }


def _runtime_exact_source(identity: Any) -> bool:
    if not isinstance(identity, dict) or identity.get("identity_status") != "exact":
        return False
    kind = identity.get("source_kind")
    path = identity.get("source_path_or_uri")
    digest = identity.get("source_sha256")
    if kind == "repository_file":
        revision = identity.get("source_revision")
        return (isinstance(path, str) and bool(path) and isinstance(revision, str)
                and bool(_SHA40.fullmatch(revision)) and isinstance(digest, str)
                and bool(_SHA256.fullmatch(digest)))
    if kind == "github_action":
        commit = identity.get("action_commit_sha")
        return (isinstance(identity.get("action_repository"), str)
                and bool(identity["action_repository"])
                and isinstance(identity.get("action_ref"), str)
                and bool(identity["action_ref"]) and isinstance(commit, str)
                and bool(_SHA40.fullmatch(commit)))
    if kind == "container_image":
        image_digest = identity.get("container_image_digest")
        return (isinstance(path, str) and bool(path) and isinstance(image_digest, str)
                and image_digest.startswith("sha256:")
                and bool(_SHA256.fullmatch(image_digest[7:])))
    return (kind in {"builtin", "external_service", "model"}
            and isinstance(path, str) and bool(path) and isinstance(digest, str)
            and bool(_SHA256.fullmatch(digest)))



def _runtime_qualifying_execution(record: dict[str, Any], subject_key: str) -> bool:
    """Require a recorded executed invocation, not a skipped platform entry.

    A recorded failure may have consumed inputs; success or exit zero is not a
    prerequisite. Unsupported or incomplete outcomes remain unresolved here.
    """
    binding = record.get("run_binding", {})
    result = record.get("result", {})
    command = record.get("command_identity", {})
    return (
        record.get("execution_scope") == "subject"
        and record.get("capture_status") == "complete"
        and _runtime_exact_source(record.get("source_identity"))
        and binding.get("binding_complete") is True
        and binding.get("subject_run_key") == subject_key
        and binding.get("execution_run_key") == subject_key
        and binding.get("binding_mode") == "current_subject_run"
        and isinstance(result, dict)
        and result.get("lifecycle_status") == "completed"
        and result.get("result_status") == "complete"
        and result.get("outcome") in {"success", "failure"}
        and isinstance(command, dict)
        and command.get("command_kind") not in {None, "unknown"}
        and all(isinstance(command.get(key), str) and _SHA256.fullmatch(command[key])
                for key in ("command_sha256", "arguments_sha256"))
    )


def assess_runtime_output_consumption(
    index: dict[str, Any], *, producer_execution_id: str,
    required_output_state_ids: list[str],
    required_consumer_execution_ids: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Assess EVERY required output using subject-consumer evidence only.

    Requirement applicability must come from the bound plan before calling this
    function. Empty requirements are not inferred from an empty observed list.
    A missing consumer stays unresolved; absence is never proved here.
    This direct-execution view intentionally excludes call/inference consumers.
    It delegates consumer qualification to the same typed consumption index
    used by runtime reports; typed relations use runtime_consumption_map().
    """
    required = _runtime_string_list(required_output_state_ids, "required_outputs")
    expected_consumers: dict[str, list[str]] = {}
    if required_consumer_execution_ids is not None:
        if not isinstance(required_consumer_execution_ids, Mapping):
            raise RuntimeIndexError("required_consumers_not_mapping")
        if not set(required_consumer_execution_ids).issubset(required):
            raise RuntimeIndexError("required_consumer_state_not_required")
        for state_id, consumer_ids in required_consumer_execution_ids.items():
            ids = _runtime_string_list(consumer_ids, "required_consumer_ids")
            for identifier in ids:
                _runtime_record_id(identifier, "execution:")
            expected_consumers[state_id] = sorted(ids)
    subject_key = index["subject_context"]["subject_run_key"]
    executions = index["records"]["executions"]
    states = index["records"]["state_observations"]
    producer_entry = executions.get(producer_execution_id)
    if producer_entry is None:
        raise RuntimeIndexError("runtime_required_producer_missing")
    producer = producer_entry["record"]
    if producer.get("execution_scope") != "subject":
        raise RuntimeIndexError("runtime_required_producer_is_observer")
    direct_index = {**index, "records": {**index["records"], "external_calls": {}, "model_inferences": {}}}
    qualified_consumers = runtime_consumption_map(direct_index)
    results: dict[str, Any] = {}
    for state_id in sorted(required):
        entry = states.get(state_id)
        state = entry["record"] if entry is not None else {}
        reasons: set[str] = set()
        consumers: list[str] = []
        refs: list[dict[str, Any]] = []
        if not state:
            reasons.add("required_state_unavailable")
        digest = state.get("sha256")
        if (state.get("content_status") != "exact_digest"
                or not isinstance(digest, str) or not _SHA256.fullmatch(digest)
                or type(state.get("size_bytes")) is not int or state["size_bytes"] < 0):
            reasons.add("exact_state_content_unavailable")
        if (state.get("producer_execution_id") != producer_execution_id
                or state_id not in producer.get("output_state_ids", [])):
            reasons.add("runtime_production_unresolved")
        if not _runtime_qualifying_execution(producer, subject_key):
            reasons.add("producer_execution_binding_unresolved")
        for identifier in qualified_consumers.get(state_id, []):
            if identifier != producer_execution_id:
                consumers.append(identifier)
                refs.extend(_runtime_copy(executions[identifier]["source_refs"]))
        missing_expected = sorted(set(expected_consumers.get(state_id, [])) - set(consumers))
        if missing_expected:
            reasons.add("required_consumer_execution_unresolved")
        if not consumers:
            reasons.add("qualifying_subject_consumption_unresolved")
        if entry is not None:
            refs.extend(_runtime_copy(entry["source_refs"]))
        refs.extend(_runtime_copy(producer_entry["source_refs"]))
        unique_refs = {_runtime_canonical(ref): ref for ref in refs}
        results[state_id] = {
            "status": "observed" if not reasons else "unresolved",
            "consumer_execution_ids": consumers,
            "required_consumer_execution_ids": expected_consumers.get(state_id, []),
            "unresolved_required_consumer_execution_ids": missing_expected,
            "unresolved_reasons": sorted(reasons),
            "source_refs": [unique_refs[key] for key in sorted(unique_refs)],
        }
    return {
        "status": "not_applicable" if not required else
                  "observed" if all(row["status"] == "observed" for row in results.values()) else
                  "unresolved",
        "required_outputs": results,
    }


# ---------------------------------------------------------------------------
# Source-bound runtime report construction. No filesystem reads on this path.
# ---------------------------------------------------------------------------

RUNTIME_REPORT_PROFILE = "pulsemech_runtime_report_binding_v0"
RUNTIME_COMPARISON_PROFILE = "pulsemech_runtime_comparison_v0"


def runtime_context_from_subject_input(packet: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Translate verified subject descriptors without normalizing policy order."""
    subject = _runtime_subject(packet["subject"])
    authority = {}
    for role in ("workflow", "policy", "gate_registry"):
        source = packet["authority_sources"][role]
        authority[role] = {
            "role": role, "path": source["path_or_uri"],
            "source_commit": source["source_revision"], "sha256": source["sha256"],
        }
    return subject, _runtime_authority(authority, subject["source_commit"])


def runtime_graph_id(prefix: str, subject: dict[str, Any], kind: str, identifier: str) -> str:
    # Full digest; identity includes the occurrence, not its display name/content.
    return prefix + ":runtime:" + _runtime_sha(_runtime_canonical([
        subject, kind, identifier,
    ]))


def runtime_activity_io(kind: str, row: dict[str, Any]) -> tuple[list[str], list[str]]:
    if kind == "executions":
        return row["input_state_ids"], row["output_state_ids"]
    if kind == "external_calls":
        return row["request"]["payload"]["state_ids"], row["response"]["payload"]["state_ids"]
    return row["request"]["input_state_ids"], row["response"]["output_state_ids"]


def runtime_activity_context(index: dict[str, Any], kind: str, row: dict[str, Any]) -> dict[str, Any]:
    return row if kind == "executions" else index["records"]["executions"][row["parent_execution_id"]]["record"]


def runtime_activity_is_recorded(index: dict[str, Any], kind: str, row: dict[str, Any]) -> bool:
    """Recorded invocation only; failure may consume input, skipped never does.

    Service content identity and token usage are different axes from request
    consumption. A recorded request need not prove exact provider code identity.
    """
    context = runtime_activity_context(index, kind, row)
    key = index["subject_context"]["subject_run_key"]
    if not _runtime_qualifying_execution(context, key):
        return False
    if kind == "executions":
        return True
    result = row["result"]
    if (row["subject_run_key"] != key or row["capture_status"] != "complete"
            or result["lifecycle_status"] != "completed"
            or result["outcome"] not in {"success", "failure"}
            or result["result_status"] != "complete"):
        return False
    if kind == "external_calls":
        return row["request"]["payload"]["capture_status"] == "exact_digest"
    return bool(row["request"]["request_metadata_sha256"])


def runtime_exact_state(row: dict[str, Any]) -> bool:
    return (row["content_status"] == "exact_digest"
            and isinstance(row["sha256"], str) and bool(_SHA256.fullmatch(row["sha256"]))
            and type(row["size_bytes"]) is int and row["size_bytes"] >= 0)


def runtime_consumption_map(index: dict[str, Any]) -> dict[str, list[str]]:
    """Each state retains its own qualified subject consumers; no any-state fold."""
    consumers: dict[str, list[str]] = {sid: [] for sid in index["records"]["state_observations"]}
    for kind in ("executions", "external_calls", "model_inferences"):
        for identifier, entry in index["records"][kind].items():
            row = entry["record"]
            if not runtime_activity_is_recorded(index, kind, row):
                continue
            parent = identifier if kind == "executions" else row["parent_execution_id"]
            for sid in runtime_activity_io(kind, row)[0]:
                state = index["records"]["state_observations"][sid]["record"]
                if runtime_exact_state(state) and state["producer_execution_id"] not in {identifier, parent}:
                    consumers[sid].append(identifier)
    return {sid: sorted(set(ids)) for sid, ids in sorted(consumers.items())}


def runtime_recorded_output_classes(index: dict[str, Any], kind: str, row: dict[str, Any]) -> list[str]:
    """Permission and an unresolved output declaration are not observed writes."""
    if not runtime_activity_is_recorded(index, kind, row):
        return []
    parent = row["execution_id"] if kind == "executions" else row["parent_execution_id"]
    classes = set()
    for sid in runtime_activity_io(kind, row)[1]:
        state = index["records"]["state_observations"][sid]["record"]
        if runtime_exact_state(state) and state["producer_execution_id"] == parent and state["mutation_class"] != "none":
            classes.add(state["mutation_class"])
    return sorted(classes)


def runtime_extent_and_relations(index: dict[str, Any], extent_bytes: bytes | None) -> dict[str, Any]:
    """No v0 observed packet can attest its own full observation extent.

    A separately supplied example-only boundary enables positive contract tests.
    It is NEVER accepted as an observed/full-run extent. Its requirement lists
    precede and are compared with the recorded lists, not generated from them.
    """
    result = {"extent_status": "unknown", "relational_coverage_status": "partial",
              "extent_sha256": None, "extent_size_bytes": None,
              "unresolved_reasons": ["observation_extent_unavailable"]}
    if extent_bytes is None:
        return result
    extent = _runtime_load(extent_bytes)
    if index["record_status"] != "example" or extent.get("profile") != "synthetic_runtime_extent_v0":
        raise RuntimeIndexError("runtime_extent_observed_profile_not_supported")
    if set(extent) != {"profile", "record_status", "subject_context", "requirements", "terminal_packet_sha256"}:
        raise RuntimeIndexError("runtime_extent_fields_invalid")
    if extent["record_status"] != "example" or extent["subject_context"] != index["subject_context"]:
        raise RuntimeIndexError("runtime_extent_subject_or_status_mismatch")
    requirements = extent["requirements"]
    if not isinstance(requirements, dict) or not requirements:
        raise RuntimeIndexError("runtime_extent_requirements_empty")
    result.update(extent_sha256=_runtime_sha(extent_bytes), extent_size_bytes=len(extent_bytes))
    actual = {}
    for kind in ("executions", "external_calls", "model_inferences"):
        for rid, entry in index["records"][kind].items():
            row = entry["record"]
            if runtime_activity_context(index, kind, row)["execution_scope"] == "subject":
                actual[rid] = (kind, row)
    reasons = set()
    if set(requirements) != set(actual):
        reasons.add("execution_extent_mismatch")
    if (index["supplied_sequence_status"] != "rooted_contiguous"
            or extent["terminal_packet_sha256"] != index["packet_inventory"][-1]["sha256"]):
        reasons.add("terminal_packet_extent_mismatch")
    consumers = runtime_consumption_map(index)
    for rid, req in requirements.items():
        if not isinstance(req, dict) or set(req) != {"input_state_ids", "output_state_ids", "required_consumers"}:
            raise RuntimeIndexError("runtime_extent_requirement_fields_invalid")
        ins = _runtime_string_list(req["input_state_ids"], "extent_inputs")
        outs = _runtime_string_list(req["output_state_ids"], "extent_outputs")
        cr = req["required_consumers"]
        if not isinstance(cr, dict) or set(cr) != set(outs):
            raise RuntimeIndexError("runtime_extent_output_consumer_partition_invalid")
        for sid, ids in cr.items():
            _runtime_string_list(ids, "extent_consumers")
            if not ids or any(i not in requirements or i == rid for i in ids):
                raise RuntimeIndexError("runtime_extent_consumer_not_in_extent")
        if rid not in actual:
            continue
        kind, row = actual[rid]
        ai, ao = runtime_activity_io(kind, row)
        if set(ai) != set(ins) or set(ao) != set(outs):
            reasons.add("runtime_io_extent_mismatch")
        if not runtime_activity_is_recorded(index, kind, row):
            reasons.add("execution_observation_unresolved")
        context = runtime_activity_context(index, kind, row)
        if context["declared_role"] == "unknown":
            reasons.add("declared_role_unavailable")
        if kind == "external_calls":
            # v0 service identity has no immutable implementation content pin.
            reasons.add("external_service_content_identity_unavailable")
        if kind == "model_inferences" and row["model_identity"]["model_content_digest_status"] != "exact_digest":
            reasons.add("model_content_identity_unavailable")
        for sid in set(ins + outs):
            state = index["records"]["state_observations"].get(sid, {}).get("record")
            if state is None or not runtime_exact_state(state):
                reasons.add("state_content_unavailable")
        for sid in outs:
            state = index["records"]["state_observations"].get(sid, {}).get("record", {})
            parent = rid if kind == "executions" else row["parent_execution_id"]
            if state.get("producer_execution_id") != parent:
                reasons.add("state_production_unresolved")
            if not set(cr[sid]).issubset(consumers.get(sid, [])):
                reasons.add("required_output_consumption_unresolved")
    result["extent_status"] = "complete" if not reasons.intersection({"execution_extent_mismatch", "terminal_packet_extent_mismatch"}) else "partial"
    result["relational_coverage_status"] = "complete" if not reasons else "partial"
    result["unresolved_reasons"] = sorted(reasons)
    return result


def runtime_source_projection(kind: str, row: dict[str, Any]) -> dict[str, Any]:
    """The compact graph view never overwrites the full source record in binding."""
    if kind == "executions":
        src = row["source_identity"]
        source_kind = src["source_kind"]
        if source_kind == "github_action":
            return source_identity(source_kind="action", path_or_uri=src["action_repository"],
                                   revision=src["action_commit_sha"] or src["action_ref"], sha256=None)
        if source_kind == "container_image":
            return source_identity(source_kind=source_kind, path_or_uri=src["source_path_or_uri"],
                                   revision=src["container_image_digest"], sha256=src["source_sha256"])
        return source_identity(source_kind=source_kind, path_or_uri=src["source_path_or_uri"],
                               revision=src["source_revision"], sha256=src["source_sha256"])
    if kind == "external_calls":
        src = row["service_identity"]
        return source_identity(source_kind="external_service", path_or_uri=src["endpoint_origin"] or src["service_name"],
                               revision=src["api_version"], sha256=None)
    src = row["model_identity"]
    return source_identity(source_kind="model", path_or_uri=src["model_id"],
                           revision=src["model_revision"], sha256=src["model_sha256"])


def build_runtime_report(
    *, baseline_bytes: bytes, subject_input_bytes: bytes, carrier_bytes: bytes,
    packet_sources: Iterable[RuntimePacketSource], entrypoint_sha256: str,
    analyzer_sha256: str, extent_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Construct the runtime projection; upstream validation belongs to bridge.

    The original artifact graph remains separately identifiable and unchanged.
    New nodes do not imply measured resources or terminal observation closure.
    """
    baseline = _runtime_load(baseline_bytes)
    subject_input = _runtime_load(subject_input_bytes)
    context, authority = runtime_context_from_subject_input(subject_input)
    if baseline["analysis_boundary"]["analysis_level"] != "artifact_observed" or "runtime_binding" in baseline:
        raise RuntimeIndexError("runtime_baseline_not_artifact_observed")
    bs = baseline["subject"]
    for key in _SUBJECT_FIELDS:
        expected = context[key]
        if key == "workflow_name": actual = bs["workflow"]
        elif key == "subject_run_key": actual = baseline["analysis_boundary"][key]
        elif key == "active_policy_sets": actual, expected = bs[key], sorted(expected)
        else: actual = bs[key]
        if actual != expected:
            raise RuntimeIndexError("runtime_baseline_subject_mismatch:" + key)
    if baseline.get("ok") is not True or baseline.get("errors") != []:
        raise RuntimeIndexError("runtime_baseline_not_valid")
    for field in ("policy_id", "policy_sha256", "materialized_gate_set_sha256",
                  "final_status_sha256", "release_decision_sha256", "decision"):
        if baseline["subject"].get(field) != subject_input["subject"].get(field):
            raise RuntimeIndexError("runtime_baseline_authority_mismatch:" + field)
    if (baseline["subject"]["policy_sha256"] != authority["policy"]["sha256"]
            or subject_input["carrier"]["sha256"] != _runtime_sha(carrier_bytes)
            or subject_input["carrier"]["size_bytes"] != len(carrier_bytes)):
        raise RuntimeIndexError("runtime_baseline_carrier_or_policy_mismatch")
    sources = list(packet_sources)
    index = index_runtime_packet_sources(sources, expected_subject=context, expected_authority_inputs=authority)
    if index["record_status"] != baseline["record_status"] or subject_input["record_status"] != baseline["record_status"]:
        raise RuntimeIndexError("runtime_baseline_record_status_mismatch")
    for digest in (entrypoint_sha256, analyzer_sha256):
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise RuntimeIndexError("runtime_construction_source_invalid")
    records = index["records"]
    # Cross-record relation coherence, beyond references to existing IDs.
    for kind, idfield in (("external_calls", "external_call_ids"), ("model_inferences", "model_inference_ids")):
        for rid, entry in records[kind].items():
            row = entry["record"]
            parent = records["executions"][row["parent_execution_id"]]["record"]
            if row["subject_run_key"] != context["subject_run_key"] or rid not in parent[idfield]:
                raise RuntimeIndexError("runtime_activity_parent_binding_mismatch")
            for sid in sum((list(x) for x in runtime_activity_io(kind, row)), []):
                if sid not in records["state_observations"]:
                    raise RuntimeIndexError("runtime_activity_state_missing")
    report = _runtime_copy(baseline)
    node_ids = {rid: runtime_graph_id("compute", context, kind, rid)
                for kind in ("executions", "external_calls", "model_inferences") for rid in records[kind]}
    state_ids = {rid: runtime_graph_id("state", context, "state_observations", rid)
                 for rid in records["state_observations"]}
    edges_origin = {e["edge_id"]: {"evidence_kind": "artifact_observed", "source_refs": []}
                    for e in baseline["edges"]}
    correspondence = {"executions": {}, "states": {}}
    consumers = runtime_consumption_map(index)
    source_nodes = {}
    for kind in ("executions", "external_calls", "model_inferences"):
        for rid, entry in records[kind].items():
            row = entry["record"]
            parent = runtime_activity_context(index, kind, row)
            ins, outs = runtime_activity_io(kind, row)
            source = runtime_source_projection(kind, row)
            # Conservative per-node binding; graph identity is not runtime closure.
            status = "partial"
            if parent["source_identity"]["identity_status"] == "unknown": status = "unknown"
            node_type = row["execution_kind"] if kind == "executions" else ("external_service_call" if kind == "external_calls" else "model_inference")
            node = make_compute_node(
                node_id=node_ids[rid], node_type=node_type, scope=parent["execution_scope"],
                role=parent["declared_role"], status=status, source=source,
                subject_run_key=context["subject_run_key"], analysis_run_key=report["analysis_boundary"]["analysis_run_key"],
                inputs=[state_ids[i] for i in ins], outputs=[state_ids[i] for i in outs],
                mutation_authority=parent["permitted_mutation_authority"], observed_mutation=False,
            )
            node["run_binding"] = _runtime_copy(parent["run_binding"])
            node["runtime_origin"] = {"record_kind": kind, "record_id": rid}
            node["flags"]["resource_measurement_partial"] = bool(baseline["resource_summary"]["axes"])
            # Actual mutations derive from recorded outputs, not permission.
            muts = runtime_recorded_output_classes(index, kind, row)
            node["observed_mutation_classes"] = muts
            node["unbound_authoritative_mutation"] = bool(set(muts) & AUTHORITATIVE_MUTATION_CLASSES)
            report["compute_nodes"].append(node)
            source_nodes[rid] = node
            correspondence["executions"][rid] = {"node_id": node_ids[rid], "artifact_node_ids": [],
                                                   "status": "unresolved"}
    for rid, entry in records["state_observations"].items():
        row = entry["record"]
        producer = row["producer_execution_id"]
        state = make_state_node(
            state_id=state_ids[rid], state_type=row["state_type"],
            path_or_uri=row["path_or_uri"] or ("runtime-state:" + rid),
            sha256=row["sha256"], size_bytes=row["size_bytes"], schema_id=row["schema_identity"],
            producer_node_id=(node_ids.get(producer) if producer is not None and rid in records["executions"][producer]["record"]["output_state_ids"] else None),
            subject_run_key=row["subject_run_key"],
            release_candidate_id=row["release_candidate_id"], policy_relation=None, gate_relation=None,
            authority_bearing=row["authority_bearing"],
        )
        state["runtime_origin"] = {"record_kind": "state_observations", "record_id": rid}
        report["state_nodes"].append(state)
        matches = []
        if row["path_or_uri"] is not None and runtime_exact_state(row):
            for old in baseline["state_nodes"]:
                if (old["path_or_uri"] == row["path_or_uri"] and old["state_type"] == row["state_type"]
                        and old["sha256"] == row["sha256"] and old["subject_run_key"] == row["subject_run_key"]
                        and old["release_candidate_id"] == row["release_candidate_id"]
                        and old["authority_bearing"] == row["authority_bearing"]
                        and old["size_bytes"] in {None, row["size_bytes"]}):
                    matches.append(old["state_id"])
        correspondence["states"][rid] = {"state_id": state_ids[rid], "artifact_state_ids": sorted(matches),
                                           "status": "matched" if len(matches) == 1 else "unresolved"}
    for kind in ("executions", "external_calls", "model_inferences"):
        for rid, entry in records[kind].items():
            row = entry["record"]
            ins, outs = runtime_activity_io(kind, row)
            for direction, ids in (("reads", ins), ("produces", outs)):
                for sid in sorted(set(ids)):
                    state = records["state_observations"][sid]["record"]
                    from_id, to_id = ((state_ids[sid], node_ids[rid]) if direction == "reads" else (node_ids[rid], state_ids[sid]))
                    eid = runtime_graph_id("edge", context, direction, rid + "|" + sid)
                    observed = runtime_activity_is_recorded(index, kind, row) and runtime_exact_state(state)
                    if direction == "produces":
                        producer = rid if kind == "executions" else row["parent_execution_id"]
                        observed = observed and state["producer_execution_id"] == producer
                    refs = entry["source_refs"] + records["state_observations"][sid]["source_refs"]
                    refs = {_runtime_canonical(r): r for r in refs}
                    report["edges"].append({
                        "edge_id": eid, "from_id": from_id, "to_id": to_id, "edge_type": direction,
                        "declared": True, "observed": observed, "binding_status": "complete" if observed else "partial",
                        "evidence_digests": sorted({r["packet_sha256"] for r in refs.values()} | ({state["sha256"]} if state["sha256"] else set())),
                        "notes": ["runtime_recorded_relation" if observed else "runtime_relation_unresolved"],
                    })
                    edges_origin[eid] = {"evidence_kind": "runtime_recorded" if observed else "runtime_unresolved",
                                         "source_refs": [refs[r] for r in sorted(refs)]}
    for name, key in (("compute_nodes", "node_id"), ("state_nodes", "state_id"), ("edges", "edge_id")):
        report[name].sort(key=lambda r: r[key])
        if len(report[name]) != len({r[key] for r in report[name]}):
            raise RuntimeIndexError("runtime_graph_identity_collision")
    subject_nodes = [n for n in report["compute_nodes"] if n["execution_scope"] == "subject"]
    counts = Counter(n["binding_class"] for n in subject_nodes)
    report["summary"].update({"subject_compute_nodes": len(subject_nodes),
        "observer_nodes": sum(n["execution_scope"] in _OBSERVER_SCOPES for n in report["compute_nodes"]),
        "decision_closure_complete": False, "authority_binding_complete": False,
        "unbound_authoritative_mutation_count": sum(n["unbound_authoritative_mutation"] is True for n in subject_nodes),
        **{field: counts.get(cls, 0) for cls, field in SUMMARY_COUNT_FIELDS.items()}})
    coverage = runtime_extent_and_relations(index, extent_bytes)
    report["analysis_boundary"]["analysis_level"] = "runtime_observed"
    report["tool"] = {"id": "build_pulsemech_compute_binding_report_from_subject_input_v0",
                      "version": "0.3.0", "source_sha256": entrypoint_sha256}
    resources = []
    by_digest = {_runtime_sha(s.data): _runtime_load(s.data) for s in sources}
    for item in index["packet_inventory"]:
        p = by_digest[item["sha256"]]
        resources.append({"packet_sha256": item["sha256"], "coverage": _runtime_copy(p["coverage"]),
                          "measurements": _runtime_copy(p["resource_measurements"])})
    report["runtime_binding"] = {
        "profile": RUNTIME_REPORT_PROFILE,
        "baseline_report": {"sha256": _runtime_sha(baseline_bytes), "size_bytes": len(baseline_bytes)},
        "subject_input": {"sha256": _runtime_sha(subject_input_bytes), "size_bytes": len(subject_input_bytes)},
        "carrier": {"sha256": _runtime_sha(carrier_bytes), "size_bytes": len(carrier_bytes)},
        "construction": {"entrypoint_sha256": entrypoint_sha256, "analyzer_sha256": analyzer_sha256},
        "index": index, "correspondence": correspondence, "edge_origins": dict(sorted(edges_origin.items())),
        "coverage": coverage, "resource_coverage": resources,
        "extent": _runtime_load(extent_bytes) if extent_bytes is not None else None,
    }
    # A separate validation step checks these declarations against exact inputs.
    return report


if __name__ == "__main__":
    raise SystemExit(main())
