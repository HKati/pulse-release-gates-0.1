#!/usr/bin/env python3
"""Assemble a complete release-grade reference package.

This tool copies already-produced runtime artifacts into a fresh package
directory, writes run metadata, and writes a package digest inventory.

It does not:
- produce external evidence;
- verify external attestations;
- build recorded candidates;
- verify recorded release evidence;
- materialize gates;
- call check_gates.py;
- create release authority.

The package is a preservation and review surface only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "release_grade_reference_package_v0"
METADATA_SCHEMA_VERSION = "release_grade_reference_package_run_metadata_v0"
DIGEST_INVENTORY_SCHEMA_VERSION = "release_grade_reference_package_digest_inventory_v0"
TOOL_VERSION = "0.1.0"

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
RUN_KEY_RE = re.compile(
    r"^GITHUB_RUN_ID=[1-9][0-9]*\|"
    r"GITHUB_RUN_ATTEMPT=[1-9][0-9]*\|"
    r"GITHUB_WORKFLOW=.+$"
)

AUTHORITY_BOUNDARY = {
    "creates_release_authority": False,
    "authorizes_release": False,
    "blocks_release": False,
    "materializes_status": False,
    "materializes_release_required": False,
    "verifies_recorded_release_evidence": False,
    "replaces_check_gates": False,
    "package_only": True,
}

ARTIFACT_FILES: tuple[tuple[str, str, str], ...] = (
    (
        "recorded_path",
        "required_gate_evidence_v0.json",
        "artifacts/required_gate_evidence_v0.json",
    ),
    (
        "recorded_path",
        "status_baseline.json",
        "artifacts/status_baseline.json",
    ),
    (
        "recorded_path",
        "recorded_release_candidate_index_v0.json",
        "artifacts/recorded_release_candidate_index_v0.json",
    ),
    (
        "recorded_path",
        "release_evidence_input_manifest_v0.json",
        "artifacts/release_evidence_input_manifest_v0.json",
    ),
    (
        "recorded_path",
        "recorded_release_evidence_verifier_v0.json",
        "artifacts/recorded_release_evidence_verifier_v0.json",
    ),
    (
        "recorded_path",
        "llamaguard_raw.jsonl",
        "artifacts/external/llamaguard_raw.jsonl",
    ),
    (
        "recorded_path",
        "llamaguard_evaluator_manifest_v0.json",
        "artifacts/external/llamaguard_evaluator_manifest_v0.json",
    ),
    (
        "recorded_path",
        "llamaguard_summary.json",
        "artifacts/external/llamaguard_summary.json",
    ),
    (
        "recorded_path",
        "llamaguard_summary.bundle.json",
        "artifacts/external/llamaguard_summary.bundle.json",
    ),
    (
        "recorded_path",
        "llamaguard_summary.envelope.json",
        "artifacts/external/llamaguard_summary.envelope.json",
    ),
    (
        "recorded_path",
        "llamaguard_attestation_verifier_v1.json",
        "artifacts/external/llamaguard_attestation_verifier_v1.json",
    ),
    (
        "recorded_path",
        "status.json",
        "artifacts/status.json",
    ),
    (
        "pulse_report",
        "release_decision_v0.json",
        "artifacts/release_decision_v0.json",
    ),
    (
        "artifact_binding",
        "artifact_provenance_binding_v0.json",
        "artifacts/artifact_provenance_binding_v0.json",
    ),
    (
        "pulse_report",
        "release_authority_v0.json",
        "artifacts/release_authority_v0.json",
    ),
    (
        "pulse_report",
        "report_card.html",
        "artifacts/report_card.html",
    ),
)


class AssemblyError(ValueError):
    """Fail-closed package assembly error."""


def _utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssemblyError(f"{label} must be a non-empty string")

    return value.strip()


def _normalize_utc(value: Any, label: str) -> str:
    text = _require_text(value, label)
    parsed = text[:-1] + "+00:00" if text.endswith("Z") else text

    try:
        stamp = dt.datetime.fromisoformat(parsed)

    except ValueError as exc:
        raise AssemblyError(f"{label} must be ISO-8601") from exc

    if stamp.tzinfo is None:
        raise AssemblyError(f"{label} must include a timezone")

    return (
        stamp.astimezone(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _resolve_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(str(path))))


def _require_directory(path: Path, label: str) -> Path:
    resolved = _resolve_path(path)

    if resolved.is_symlink() or not resolved.is_dir():
        raise AssemblyError(
            f"{label} must be a directory and not a symlink: {resolved}"
        )

    return resolved


def _reject_symlink_components(path: Path, label: str) -> None:
    resolved = _resolve_path(path)

    # Walk only through existing components. The final output directory may not
    # exist yet, so checking parents is sufficient for output paths.
    current = Path(resolved.anchor) if resolved.is_absolute() else Path()

    parts = resolved.parts
    if resolved.is_absolute() and parts:
        parts = parts[1:]

    for part in parts:
        current = current / part

        if current.exists() or current.is_symlink():
            if current.is_symlink():
                raise AssemblyError(
                    f"{label} must not traverse a symlink: {current}"
                )


def _require_regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise AssemblyError(
            f"{label} must be a regular non-symlink file: {path}"
        )


def _sha256(path: Path) -> str:
    _require_regular_file(path, f"SHA-256 input {path}")
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _copy_file(source: Path, destination: Path, label: str) -> None:
    _require_regular_file(source, label)
    _reject_symlink_components(source, label)

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() or destination.is_symlink():
        raise AssemblyError(f"destination already exists: {destination}")

    shutil.copy2(source, destination)
    _require_regular_file(destination, f"copied {label}")


def _copy_tree(source: Path, destination: Path, label: str) -> None:
    source = _require_directory(source, label)
    _reject_symlink_components(source, label)

    if destination.exists() or destination.is_symlink():
        raise AssemblyError(f"destination already exists: {destination}")

    file_count = 0

    for path in source.rglob("*"):
        if path.is_symlink():
            raise AssemblyError(
                f"{label} must not contain symlinks: {path}"
            )

        if path.is_file():
            file_count += 1

    if file_count == 0:
        raise AssemblyError(f"{label} must contain at least one file")

    shutil.copytree(source, destination, symlinks=False)

    for path in destination.rglob("*"):
        if path.is_symlink():
            raise AssemblyError(
                f"copied {label} must not contain symlinks: {path}"
            )


def _iter_regular_files(root: Path) -> list[Path]:
    result: list[Path] = []

    for path in root.rglob("*"):
        if path.is_symlink():
            raise AssemblyError(
                f"package must not contain symlinks: {path}"
            )

        if path.is_file():
            result.append(path)

    return sorted(
        result,
        key=lambda item: item.relative_to(root).as_posix(),
    )


def _find_unique_file(
    root: Path,
    basename: str,
    label: str,
) -> Path:
    root = _require_directory(root, label)
    matches = [
        path
        for path in root.rglob(basename)
        if path.name == basename and path.is_file() and not path.is_symlink()
    ]

    if not matches:
        raise AssemblyError(f"{label} is missing required file {basename!r}")

    if len(matches) == 1:
        return matches[0]

    preferred_suffixes = (
        f"PULSE_safe_pack_v0/artifacts/{basename}",
        f"artifacts/{basename}",
        f"external/{basename}",
        f"artifacts/external/{basename}",
    )

    preferred = [
        path
        for path in matches
        if any(path.as_posix().endswith(suffix) for suffix in preferred_suffixes)
    ]

    if len(preferred) == 1:
        return preferred[0]

    joined = ", ".join(path.as_posix() for path in matches)
    raise AssemblyError(
        f"{label} has ambiguous file matches for {basename!r}: {joined}"
    )


def _find_unique_directory(
    root: Path,
    dirname: str,
    label: str,
) -> Path:
    root = _require_directory(root, label)
    matches = [
        path
        for path in root.rglob(dirname)
        if path.name == dirname and path.is_dir() and not path.is_symlink()
    ]

    if not matches:
        raise AssemblyError(f"{label} is missing required directory {dirname!r}")

    if len(matches) == 1:
        return matches[0]

    preferred_suffixes = (
        f"PULSE_safe_pack_v0/artifacts/{dirname}",
        f"artifacts/{dirname}",
    )
    preferred = [
        path
        for path in matches
        if any(path.as_posix().endswith(suffix) for suffix in preferred_suffixes)
    ]

    if len(preferred) == 1:
        return preferred[0]

    joined = ", ".join(path.as_posix() for path in matches)
    raise AssemblyError(
        f"{label} has ambiguous directory matches for {dirname!r}: {joined}"
    )


def _select_input_roots(
    *,
    pulse_report_dir: Path,
    recorded_path_dir: Path,
    audit_bundle_dir: Path,
    artifact_binding_dir: Path,
) -> dict[str, Path]:
    return {
        "pulse_report": _require_directory(pulse_report_dir, "pulse-report input"),
        "recorded_path": _require_directory(recorded_path_dir, "recorded-path input"),
        "audit_bundle": _require_directory(audit_bundle_dir, "audit-bundle input"),
        "artifact_binding": _require_directory(
            artifact_binding_dir,
            "artifact-binding input",
        ),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    _require_regular_file(path, f"written JSON {path}")


def _write_run_metadata(
    path: Path,
    *,
    repository: str,
    git_sha: str,
    workflow_ref: str,
    run_id: str,
    run_attempt: str,
    run_key: str,
    release_candidate: str,
    created_utc: str,
    source_dirs: dict[str, Path],
) -> None:
    if repository.count("/") != 1:
        raise AssemblyError("repository must use owner/name form")

    if not GIT_SHA_RE.fullmatch(git_sha):
        raise AssemblyError("git_sha must be a concrete 40-hex SHA")

    if not run_id.isdecimal() or int(run_id) < 1:
        raise AssemblyError("run_id must be a positive decimal string")

    if not run_attempt.isdecimal() or int(run_attempt) < 1:
        raise AssemblyError("run_attempt must be a positive decimal string")

    if not RUN_KEY_RE.fullmatch(run_key):
        raise AssemblyError(
            "run_key must use the canonical GitHub run identity form"
        )

    metadata = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "package_schema_version": SCHEMA_VERSION,
        "package_role": "complete_release_grade_reference_package",
        "created_utc": created_utc,
        "repository": repository,
        "git_sha": git_sha.lower(),
        "workflow_ref": workflow_ref,
        "run_id": int(run_id),
        "run_attempt": int(run_attempt),
        "run_key": run_key,
        "release_candidate": release_candidate,
        "source_inputs": {
            key: str(value)
            for key, value in sorted(source_dirs.items())
        },
        "assembler": {
            "tool": "assemble_release_grade_reference_package_v0.py",
            "version": TOOL_VERSION,
        },
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
    }
    _write_json(path, metadata)


def _write_digest_inventory(path: Path, package_root: Path) -> None:
    files = []
    inventory_rel = path.relative_to(package_root).as_posix()

    for file_path in _iter_regular_files(package_root):
        relative = file_path.relative_to(package_root).as_posix()

        if relative == inventory_rel:
            continue

        stat = file_path.stat()
        files.append(
            {
                "path": relative,
                "sha256": _sha256(file_path),
                "size_bytes": stat.st_size,
            }
        )

    if not files:
        raise AssemblyError("package digest inventory would be empty")

    inventory = {
        "schema_version": DIGEST_INVENTORY_SCHEMA_VERSION,
        "algorithm": "sha256",
        "file_count": len(files),
        "files": files,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
    }
    _write_json(path, inventory)


def _stage_package(
    *,
    staging_dir: Path,
    roots: dict[str, Path],
) -> None:
    staging_dir.mkdir(parents=True, exist_ok=False)

    for root_key, basename, destination in ARTIFACT_FILES:
        source = _find_unique_file(
            roots[root_key],
            basename,
            f"{root_key} input",
        )
        _copy_file(
            source,
            staging_dir / destination,
            f"{root_key}:{basename}",
        )

    candidates = _find_unique_directory(
        roots["recorded_path"],
        "recorded_release_candidates",
        "recorded-path input",
    )
    _copy_tree(
        candidates,
        staging_dir / "artifacts/recorded_release_candidates",
        "recorded_release_candidates",
    )

    audit_root = roots["audit_bundle"]
    audit_candidates = [
        audit_root,
        *_safe_rglob_dirs(audit_root, "release-authority-audit-bundle"),
        *_safe_rglob_dirs(audit_root, "release_authority_audit_bundle"),
    ]

    selected_audit = None
    for candidate in audit_candidates:
        if not candidate.exists() or candidate.is_symlink() or not candidate.is_dir():
            continue

        if any(path.is_file() for path in candidate.rglob("*")):
            selected_audit = candidate
            break

    if selected_audit is None:
        raise AssemblyError(
            "audit-bundle input is missing a non-empty audit bundle directory"
        )

    _copy_tree(
        selected_audit,
        staging_dir / "release-authority-audit-bundle",
        "release-authority audit bundle",
    )


def _safe_rglob_dirs(root: Path, dirname: str) -> list[Path]:
    result: list[Path] = []

    for path in root.rglob(dirname):
        if path.is_symlink():
            raise AssemblyError(f"input must not contain symlink directory: {path}")

        if path.is_dir() and path.name == dirname:
            result.append(path)

    return result


def _prepare_output_parent(out_dir: Path) -> tuple[Path, Path]:
    out_dir = _resolve_path(out_dir)
    _reject_symlink_components(out_dir.parent, "output parent")

    if out_dir.exists() or out_dir.is_symlink():
        raise AssemblyError(
            f"output directory must be absent before assembly: {out_dir}"
        )

    out_dir.parent.mkdir(parents=True, exist_ok=True)

    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{out_dir.name}.",
            suffix=".tmp",
            dir=str(out_dir.parent),
        )
    )
    shutil.rmtree(staging)

    return out_dir, staging


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assemble a complete release-grade reference package."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--pulse-report-dir", required=True)
    parser.add_argument("--recorded-path-dir", required=True)
    parser.add_argument("--audit-bundle-dir", required=True)
    parser.add_argument("--artifact-binding-dir", required=True)
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--git-sha", default=os.getenv("GITHUB_SHA"))
    parser.add_argument("--workflow-ref", default=os.getenv("GITHUB_WORKFLOW_REF"))
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID"))
    parser.add_argument("--run-attempt", default=os.getenv("GITHUB_RUN_ATTEMPT"))
    parser.add_argument("--run-key", default=os.getenv("PULSE_RUN_KEY"))
    parser.add_argument(
        "--release-candidate",
        default=os.getenv("GITHUB_REF_NAME") or os.getenv("PULSE_RELEASE_CANDIDATE"),
    )
    parser.add_argument("--created-utc", default=_utc_now())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    staging_dir: Path | None = None

    try:
        repo_root = _require_directory(Path(args.repo_root), "repository root")
        out_dir, staging_dir = _prepare_output_parent(Path(args.out_dir))

        roots = _select_input_roots(
            pulse_report_dir=Path(args.pulse_report_dir),
            recorded_path_dir=Path(args.recorded_path_dir),
            audit_bundle_dir=Path(args.audit_bundle_dir),
            artifact_binding_dir=Path(args.artifact_binding_dir),
        )

        _stage_package(
            staging_dir=staging_dir,
            roots=roots,
        )

        run_metadata = staging_dir / "run_metadata_v0.json"
        digest_inventory = staging_dir / "package_digest_inventory_v0.json"

        _write_run_metadata(
            run_metadata,
            repository=_require_text(args.repository, "repository"),
            git_sha=_require_text(args.git_sha, "git_sha"),
            workflow_ref=_require_text(args.workflow_ref, "workflow_ref"),
            run_id=_require_text(args.run_id, "run_id"),
            run_attempt=_require_text(args.run_attempt, "run_attempt"),
            run_key=_require_text(args.run_key, "run_key"),
            release_candidate=_require_text(
                args.release_candidate,
                "release_candidate",
            ),
            created_utc=_normalize_utc(args.created_utc, "created_utc"),
            source_dirs=roots,
        )
        _write_digest_inventory(
            digest_inventory,
            staging_dir,
        )

        # Basic postconditions before publish.
        _require_regular_file(
            staging_dir / "run_metadata_v0.json",
            "run metadata",
        )
        _require_regular_file(
            staging_dir / "package_digest_inventory_v0.json",
            "package digest inventory",
        )

        if out_dir.exists() or out_dir.is_symlink():
            raise AssemblyError(
                f"output directory appeared during assembly: {out_dir}"
            )

        shutil.move(str(staging_dir), str(out_dir))
        staging_dir = None

    except AssemblyError as exc:
        if staging_dir is not None and staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)

        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    except Exception as exc:  # noqa: BLE001
        if staging_dir is not None and staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)

        print(f"ERROR: unexpected package assembly failure: {exc}", file=sys.stderr)
        return 1

    print(f"OK: complete release-grade reference package assembled at {out_dir}")
    print(
        "Authority boundary: package assembly preserves evidence only; "
        "it does not authorize release"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
