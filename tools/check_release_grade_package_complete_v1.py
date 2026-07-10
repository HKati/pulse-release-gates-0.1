#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any


TOOL_NAME = "check_release_grade_package_complete_v1"
SCHEMA_VERSION = "release_grade_package_completeness_v1"
TOOL_VERSION = "0.1.0"

REQUIRED_FILES: tuple[str, ...] = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/status.json",
    "artifacts/release_decision_v0.json",
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/release_authority_v0.json",
    "artifacts/report_card.html",
    "artifacts/slsa/slsa_vsa_trusted_producer_input_packet_v0.json",
    "artifacts/slsa/slsa_vsa_trusted_evidence_producer_report_v0.json",
)

REQUIRED_DIRS: tuple[str, ...] = (
    "artifacts/recorded_release_candidates",
    "release-authority-audit-bundle",
)

JSON_OBJECT_FILES: tuple[str, ...] = (
    "package_digest_inventory_v0.json",
    "run_metadata_v0.json",
    "artifacts/required_gate_evidence_v0.json",
    "artifacts/status_baseline.json",
    "artifacts/recorded_release_candidate_index_v0.json",
    "artifacts/release_evidence_input_manifest_v0.json",
    "artifacts/recorded_release_evidence_verifier_v0.json",
    "artifacts/status.json",
    "artifacts/release_decision_v0.json",
    "artifacts/artifact_provenance_binding_v0.json",
    "artifacts/release_authority_v0.json",
    "artifacts/slsa/slsa_vsa_trusted_producer_input_packet_v0.json",
    "artifacts/slsa/slsa_vsa_trusted_evidence_producer_report_v0.json",
)

SLSA_PACKET_PATH = "artifacts/slsa/slsa_vsa_trusted_producer_input_packet_v0.json"
SLSA_REPORT_PATH = "artifacts/slsa/slsa_vsa_trusted_evidence_producer_report_v0.json"

STUB_MARKERS = (
    "todo",
    "tbd",
    "stub",
    "placeholder",
    "not implemented",
    "replace-me",
    "fill me",
    "example.invalid",
)

AUTHORITY_BOUNDARY = {
    "read_only": True,
    "authorizes_release": False,
    "blocks_release": False,
    "creates_release_authority": False,
    "materializes_status": False,
    "materializes_required_gates": False,
    "calls_check_gates": False,
    "package_completeness_only": True,
}


class CompletenessError(ValueError):
    """Release-grade completeness check error."""


class StrictJsonError(CompletenessError):
    """Strict JSON parse error."""


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
            raise CompletenessError(f"{label} contains non-finite number")
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite_tree(item, f"{label}[{index}]")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            _finite_tree(item, f"{label}.{key}")
        return

    raise CompletenessError(f"{label} contains unsupported JSON value")


def _resolve(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(str(path))))


def _require_package_dir(path: Path) -> Path:
    resolved = _resolve(path)

    if resolved.is_symlink() or not resolved.is_dir():
        raise CompletenessError(f"package_dir must be a non-symlink directory: {resolved}")

    return resolved


def _package_path(package_dir: Path, relative: str) -> Path:
    path = _resolve(package_dir / relative)

    try:
        path.relative_to(package_dir)
    except ValueError as exc:
        raise CompletenessError(f"package path escapes root: {relative}") from exc

    return path


def _load_json(path: Path, label: str) -> Any:
    if path.is_symlink() or not path.is_file():
        raise CompletenessError(f"{label} must be a regular non-symlink file")

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_pairs,
            parse_constant=_bad_constant,
        )
    except CompletenessError:
        raise
    except Exception as exc:
        raise CompletenessError(f"{label} is not valid JSON: {exc}") from exc

    _finite_tree(payload, label)
    return payload


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    payload = _load_json(path, label)

    if not isinstance(payload, dict):
        raise CompletenessError(f"{label} must be a JSON object")

    return payload


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise CompletenessError(f"SHA-256 input must be a regular file: {path}")

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _iter_package_files(package_dir: Path) -> list[Path]:
    files: list[Path] = []

    for path in package_dir.rglob("*"):
        if path.is_symlink():
            raise CompletenessError(f"package must not contain symlinks: {path}")

        if path.is_file():
            files.append(path)

    return sorted(files, key=lambda item: item.relative_to(package_dir).as_posix())


def _check(
    checks: list[dict[str, Any]],
    errors: list[str],
    check_id: str,
    condition: bool,
    details: str,
) -> None:
    passed = bool(condition)
    checks.append(
        {
            "check_id": check_id,
            "passed": passed,
            "details": details,
        }
    )

    if not passed:
        errors.append(f"{check_id}: {details}")


def _nested_get(value: Any, path: tuple[str, ...]) -> Any:
    cursor = value

    for key in path:
        if not isinstance(cursor, dict):
            return None

        cursor = cursor.get(key)

    return cursor


def _iter_string_values(value: Any, path: str = "$") -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []

    if isinstance(value, str):
        values.append((path, value))
        return values

    if isinstance(value, list):
        for index, item in enumerate(value):
            values.extend(_iter_string_values(item, f"{path}[{index}]"))
        return values

    if isinstance(value, dict):
        for key, item in value.items():
            values.extend(_iter_string_values(item, f"{path}.{key}"))
        return values

    return values


def _stub_marker_hits(value: str) -> list[str]:
    lowered = value.lower()
    return [marker for marker in STUB_MARKERS if marker in lowered]


def _verify_required_surface(
    *,
    package_dir: Path,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    for relative in REQUIRED_FILES:
        path = _package_path(package_dir, relative)
        exists = path.is_file() and not path.is_symlink()
        _check(
            checks,
            errors,
            f"required_file:{relative}",
            exists,
            f"{relative} is present as a regular file",
        )

        if exists:
            _check(
                checks,
                errors,
                f"non_empty_file:{relative}",
                path.stat().st_size > 0,
                f"{relative} is non-empty",
            )

    for relative in REQUIRED_DIRS:
        path = _package_path(package_dir, relative)
        exists = path.is_dir() and not path.is_symlink()
        has_files = exists and any(item.is_file() for item in path.rglob("*"))
        _check(
            checks,
            errors,
            f"required_dir:{relative}",
            exists and has_files,
            f"{relative} is present as a non-empty non-symlink directory",
        )


def _verify_json_objects(
    *,
    package_dir: Path,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}

    for relative in JSON_OBJECT_FILES:
        path = _package_path(package_dir, relative)

        try:
            payload = _load_json_object(path, relative)
            loaded[relative] = payload
            _check(
                checks,
                errors,
                f"json_object:{relative}",
                True,
                f"{relative} is a strict JSON object",
            )

            stub_hits: list[str] = []
            for json_path, text in _iter_string_values(payload):
                for marker in _stub_marker_hits(text):
                    stub_hits.append(f"{json_path} contains {marker!r}")

            _check(
                checks,
                errors,
                f"non_stub_json:{relative}",
                not stub_hits,
                f"{relative} contains no stub/placeholder markers",
            )

            if stub_hits:
                for hit in stub_hits[:20]:
                    errors.append(f"non_stub_json:{relative}: {hit}")

        except CompletenessError as exc:
            _check(
                checks,
                errors,
                f"json_object:{relative}",
                False,
                str(exc),
            )

    return loaded


def _verify_report_card(
    *,
    package_dir: Path,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    relative = "artifacts/report_card.html"
    path = _package_path(package_dir, relative)

    if not path.is_file() or path.is_symlink():
        return

    text = path.read_text(encoding="utf-8")
    hits = _stub_marker_hits(text)

    _check(
        checks,
        errors,
        "report_card.non_stub",
        not hits,
        "report_card.html contains no stub/placeholder markers",
    )


def _verify_digest_inventory(
    *,
    package_dir: Path,
    inventory: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if inventory is None:
        _check(
            checks,
            errors,
            "digest_inventory.present",
            False,
            "package digest inventory is present",
        )
        return

    _check(
        checks,
        errors,
        "digest_inventory.schema_version",
        inventory.get("schema_version") == "release_grade_reference_package_digest_inventory_v0",
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
    duplicate_seen = False

    for index, item in enumerate(files):
        if not isinstance(item, dict):
            _check(
                checks,
                errors,
                f"digest_inventory.entry:{index}",
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
                f"digest_inventory.path:{index}",
                False,
                "digest inventory path must be a relative string",
            )
            continue

        if relative in seen:
            duplicate_seen = True

        seen[relative] = item

        if not isinstance(digest, str) or len(digest) != 64:
            _check(
                checks,
                errors,
                f"digest_inventory.sha256:{relative}",
                False,
                f"{relative} has invalid sha256 field",
            )
            continue

        if not all(char in "0123456789abcdefABCDEF" for char in digest):
            _check(
                checks,
                errors,
                f"digest_inventory.sha256:{relative}",
                False,
                f"{relative} sha256 field is not hex",
            )
            continue

        if not isinstance(size, int) or size < 0:
            _check(
                checks,
                errors,
                f"digest_inventory.size:{relative}",
                False,
                f"{relative} has invalid size_bytes",
            )
            continue

        try:
            path = _package_path(package_dir, relative)
        except CompletenessError as exc:
            _check(
                checks,
                errors,
                f"digest_inventory.path_safe:{relative}",
                False,
                str(exc),
            )
            continue

        if not path.is_file() or path.is_symlink():
            _check(
                checks,
                errors,
                f"digest_inventory.file_present:{relative}",
                False,
                f"{relative} is listed but missing or symlinked",
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
        not duplicate_seen,
        "digest inventory has unique paths",
    )

    actual_files = {
        path.relative_to(package_dir).as_posix()
        for path in _iter_package_files(package_dir)
        if path.relative_to(package_dir).as_posix() != "package_digest_inventory_v0.json"
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
        "digest_inventory.exact_coverage",
        actual_files == listed_files,
        "digest inventory exactly covers package files except itself",
    )


def _verify_recorded_candidates(
    *,
    package_dir: Path,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    candidate_dir = _package_path(package_dir, "artifacts/recorded_release_candidates")
    if not candidate_dir.is_dir() or candidate_dir.is_symlink():
        return

    candidates = sorted(
        path
        for path in candidate_dir.rglob("*.json")
        if path.is_file() and not path.is_symlink()
    )

    _check(
        checks,
        errors,
        "recorded_candidates.non_empty",
        bool(candidates),
        "recorded_release_candidates contains at least one JSON candidate",
    )

    for candidate in candidates:
        relative = candidate.relative_to(package_dir).as_posix()

        try:
            payload = _load_json_object(candidate, relative)
            _check(
                checks,
                errors,
                f"recorded_candidate.json:{relative}",
                True,
                f"{relative} is strict JSON object",
            )
        except CompletenessError as exc:
            _check(
                checks,
                errors,
                f"recorded_candidate.json:{relative}",
                False,
                str(exc),
            )
            continue

        validation = payload.get("validation")
        _check(
            checks,
            errors,
            f"recorded_candidate.validation:{relative}",
            isinstance(validation, dict)
            and validation.get("status") in {"passed", "verified", "accepted"},
            f"{relative} has passed/verified validation status",
        )


def _verify_slsa_trusted_producer_chain(
    *,
    loaded: dict[str, dict[str, Any]],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    packet = loaded.get(SLSA_PACKET_PATH)
    report = loaded.get(SLSA_REPORT_PATH)

    if packet is None or report is None:
        _check(
            checks,
            errors,
            "slsa_vsa.packet_report.present",
            False,
            "trusted producer input packet and report are both present",
        )
        return

    _check(
        checks,
        errors,
        "slsa_vsa.packet.schema_version",
        packet.get("schema_version") == "slsa_vsa_trusted_producer_input_packet_v0",
        "trusted producer input packet schema_version is v0",
    )
    _check(
        checks,
        errors,
        "slsa_vsa.packet.packet_type",
        packet.get("packet_type") == "slsa_vsa_trusted_producer_input_packet",
        "trusted producer input packet packet_type is correct",
    )
    _check(
        checks,
        errors,
        "slsa_vsa.packet.recorded_signal_mode",
        packet.get("recorded_signal_mode") == "recorded_signal_only",
        "trusted producer input packet uses recorded_signal_only",
    )
    _check(
        checks,
        errors,
        "slsa_vsa.packet.candidate_set",
        packet.get("candidate_set") == "slsa_vsa_recorded_intake_candidate",
        "trusted producer input packet candidate_set is recorded-intake candidate",
    )

    _check(
        checks,
        errors,
        "slsa_vsa.report.schema_version",
        report.get("schema_version") == "slsa_vsa_trusted_evidence_producer_report_v0",
        "trusted producer report schema_version is v0",
    )
    _check(
        checks,
        errors,
        "slsa_vsa.report.report_type",
        report.get("report_type") == "slsa_vsa_trusted_evidence_producer_report",
        "trusted producer report report_type is correct",
    )
    _check(
        checks,
        errors,
        "slsa_vsa.report.accepted",
        report.get("ok") is True
        and report.get("producer_decision") == "TRUSTED_EVIDENCE_ACCEPTED"
        and report.get("failed_checks") == [],
        "trusted producer report is accepted with no failed checks",
    )
    _check(
        checks,
        errors,
        "slsa_vsa.report.recorded_signal_mode",
        report.get("recorded_signal_mode") == "recorded_signal_only",
        "trusted producer report uses recorded_signal_only",
    )
    _check(
        checks,
        errors,
        "slsa_vsa.report.candidate_set",
        report.get("candidate_set") == "slsa_vsa_recorded_intake_candidate",
        "trusted producer report candidate_set is recorded-intake candidate",
    )

    packet_run_key = _nested_get(packet, ("run_binding", "current_run_key"))
    report_run_key = _nested_get(report, ("run_binding", "current_run_key"))
    _check(
        checks,
        errors,
        "slsa_vsa.current_run_key",
        isinstance(packet_run_key, str) and packet_run_key == report_run_key,
        "trusted producer packet/report current_run_key matches",
    )

    packet_commit = _nested_get(packet, ("run_binding", "commit_sha"))
    report_commit = _nested_get(report, ("run_binding", "commit_sha"))
    _check(
        checks,
        errors,
        "slsa_vsa.commit_sha",
        isinstance(packet_commit, str) and packet_commit == report_commit,
        "trusted producer packet/report commit_sha matches",
    )

    packet_candidate = _nested_get(packet, ("run_binding", "release_candidate_id"))
    report_candidate = _nested_get(report, ("run_binding", "release_candidate_id"))
    _check(
        checks,
        errors,
        "slsa_vsa.release_candidate_id",
        isinstance(packet_candidate, str) and packet_candidate == report_candidate,
        "trusted producer packet/report release_candidate_id matches",
    )

    packet_subject_sha = _nested_get(packet, ("artifact_binding", "subject_sha256"))
    report_subject_sha = _nested_get(report, ("artifact_binding", "subject_sha256"))
    packet_artifact_sha = _nested_get(packet, ("artifact_binding", "artifact_digest_sha256"))
    report_artifact_sha = _nested_get(report, ("artifact_binding", "artifact_digest_sha256"))
    _check(
        checks,
        errors,
        "slsa_vsa.artifact_digest",
        isinstance(packet_subject_sha, str)
        and packet_subject_sha == packet_artifact_sha
        and packet_subject_sha == report_subject_sha
        and packet_subject_sha == report_artifact_sha,
        "trusted producer packet/report artifact digest binding matches",
    )

    packet_policy_id = _nested_get(packet, ("policy_binding", "expected_policy_id"))
    report_policy_id = _nested_get(report, ("policy_binding", "expected_policy_id"))
    packet_policy_sha = _nested_get(packet, ("policy_binding", "expected_policy_sha256"))
    report_policy_sha = _nested_get(report, ("policy_binding", "expected_policy_sha256"))
    _check(
        checks,
        errors,
        "slsa_vsa.policy_binding",
        isinstance(packet_policy_id, str)
        and packet_policy_id == report_policy_id
        and isinstance(packet_policy_sha, str)
        and packet_policy_sha == report_policy_sha
        and report.get("policy_binding", {}).get("policy_digest_matches") is True,
        "trusted producer packet/report policy binding matches and report confirms digest",
    )

    packet_verifier = _nested_get(packet, ("verifier_binding", "expected_verifier_id"))
    report_verifier = _nested_get(report, ("verifier_binding", "expected_verifier_id"))
    _check(
        checks,
        errors,
        "slsa_vsa.verifier_binding",
        isinstance(packet_verifier, str)
        and packet_verifier == report_verifier
        and report.get("verifier_binding", {}).get("verifier_trusted") is True,
        "trusted producer packet/report verifier binding matches and report trusts verifier",
    )

    packet_level = packet.get("expected_verified_level")
    report_level = _nested_get(report, ("evidence", "expected_verified_level"))
    _check(
        checks,
        errors,
        "slsa_vsa.verified_level",
        isinstance(packet_level, str)
        and packet_level == report_level
        and report.get("evidence", {}).get("verified_level_ok") is True,
        "trusted producer packet/report expected verified level matches and is accepted",
    )

    packet_time = _nested_get(packet, ("freshness", "expected_time_verified"))
    report_time_ok = _nested_get(report, ("freshness", "time_verified_current_run_match"))
    _check(
        checks,
        errors,
        "slsa_vsa.freshness",
        isinstance(packet_time, str)
        and report.get("freshness", {}).get("freshness_result") == "fresh_current_run"
        and report.get("freshness", {}).get("current_run_binding_ok") is True
        and report_time_ok is True,
        "trusted producer report confirms fresh current-run evidence",
    )


def _make_report(
    *,
    package_dir: Path,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    failed = [check for check in checks if not check.get("passed", False)]

    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
        },
        "ok": not errors,
        "status": "complete" if not errors else "incomplete",
        "package": {
            "path": str(package_dir),
        },
        "summary": {
            "required_files": len(REQUIRED_FILES),
            "required_dirs": len(REQUIRED_DIRS),
            "checks_total": len(checks),
            "checks_failed": len(failed),
        },
        "checks": checks,
        "errors": errors,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
    }


def check_package(package_dir: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    resolved_package_dir = _resolve(package_dir)

    try:
        resolved_package_dir = _require_package_dir(package_dir)
        _verify_required_surface(
            package_dir=resolved_package_dir,
            checks=checks,
            errors=errors,
        )
        loaded = _verify_json_objects(
            package_dir=resolved_package_dir,
            checks=checks,
            errors=errors,
        )
        _verify_report_card(
            package_dir=resolved_package_dir,
            checks=checks,
            errors=errors,
        )
        _verify_digest_inventory(
            package_dir=resolved_package_dir,
            inventory=loaded.get("package_digest_inventory_v0.json"),
            checks=checks,
            errors=errors,
        )
        _verify_recorded_candidates(
            package_dir=resolved_package_dir,
            checks=checks,
            errors=errors,
        )
        _verify_slsa_trusted_producer_chain(
            loaded=loaded,
            checks=checks,
            errors=errors,
        )

    except CompletenessError as exc:
        errors.append(str(exc))

    except Exception as exc:  # noqa: BLE001
        errors.append(f"unexpected completeness failure: {exc}")

    return _make_report(
        package_dir=resolved_package_dir,
        checks=checks,
        errors=errors,
    )


def _render(data: dict[str, Any]) -> str:
    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render(report), encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check release-grade package structural completeness."
    )
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--output")
    return parser


def _output_refused_report(package_dir: Path, output: Path, reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
        },
        "ok": False,
        "status": "output_refused",
        "package": {
            "path": str(package_dir),
        },
        "summary": {
            "required_files": len(REQUIRED_FILES),
            "required_dirs": len(REQUIRED_DIRS),
            "checks_total": 0,
            "checks_failed": 1,
        },
        "checks": [],
        "errors": [reason],
        "output": {
            "path": str(output),
        },
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    package_dir = _resolve(Path(args.package_dir))
    output = _resolve(Path(args.output)) if args.output else None

    if output is not None and output.name == "status.json":
        report = _output_refused_report(
            package_dir,
            output,
            "refusing_to_write_status_json",
        )
        sys.stdout.write(_render(report))
        return 2

    if output is not None:
        try:
            output.relative_to(package_dir)
            report = _output_refused_report(
                package_dir,
                output,
                "refusing_to_write_inside_package_dir",
            )
            sys.stdout.write(_render(report))
            return 2
        except ValueError:
            pass

    report = check_package(package_dir)
    sys.stdout.write(_render(report))

    if output is not None:
        _write_report(output, report)

    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
