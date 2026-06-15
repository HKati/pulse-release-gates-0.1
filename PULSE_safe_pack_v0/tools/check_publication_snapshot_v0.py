#!/usr/bin/env python3
"""Verify publication_snapshot_v0.json for the Pages publication surface.

This checker is audit-only publication-surface binding.

It does not make, replace, or promote release-authority decisions.
It only verifies that the published reader-surface files match the
publication snapshot generated from the CI artifact root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


SCHEMA_ID = "pulse_publication_snapshot_v0"
AUTHORITY_BOUNDARY = "audit_only_publication_surface_binding"

SNAPSHOT_NAME = "publication_snapshot_v0.json"
STATUS_NAME = "status.json"
LEDGER_NAME = "report_card.html"
INDEX_NAME = "index.html"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)

    if not isinstance(obj, dict):
        raise ValueError(f"Expected top-level JSON object in {path}")

    return obj


def _string_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _file_entry(
    snapshot: Mapping[str, Any],
    filename: str,
) -> Any:
    files = snapshot.get("files")
    if not isinstance(files, dict):
        return None

    direct = files.get(filename)
    if direct is not None:
        return direct

    for entry in files.values():
        if not isinstance(entry, dict):
            continue

        raw_path = entry.get("path") or entry.get("name")
        if raw_path is None:
            continue

        raw_path_text = str(raw_path)
        if raw_path_text == filename or Path(raw_path_text).name == filename:
            return entry

    return None


def _digest_entry(
    snapshot: Mapping[str, Any],
    filename: str,
) -> str | None:
    entry = _file_entry(snapshot, filename)

    if isinstance(entry, str):
        return entry

    if isinstance(entry, dict):
        for key in ("sha256", "digest_sha256", "digest"):
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def _status_run_identity(status: Mapping[str, Any]) -> Dict[str, str]:
    metrics_raw = status.get("metrics")
    metrics = metrics_raw if isinstance(metrics_raw, dict) else {}

    return {
        "created_utc": _string_or_empty(status.get("created_utc")),
        "metrics.git_sha": _string_or_empty(metrics.get("git_sha")),
        "metrics.run_key": _string_or_empty(metrics.get("run_key")),
    }


def _snapshot_run_identity(snapshot: Mapping[str, Any]) -> Dict[str, str]:
    raw = snapshot.get("run_identity")
    if not isinstance(raw, dict):
        return {}

    return {
        "created_utc": _string_or_empty(raw.get("created_utc")),
        "metrics.git_sha": _string_or_empty(
            raw.get("metrics.git_sha", raw.get("git_sha"))
        ),
        "metrics.run_key": _string_or_empty(
            raw.get("metrics.run_key", raw.get("run_key"))
        ),
    }


def publication_snapshot_errors(
    snapshot: Mapping[str, Any],
    status: Mapping[str, Any],
    *,
    status_path: Path,
    ledger_path: Path,
    index_path: Path | None = None,
) -> List[str]:
    errors: List[str] = []

    schema_id = snapshot.get("schema_id")
    if schema_id != SCHEMA_ID:
        errors.append(
            "schema_id mismatch: "
            f"snapshot={schema_id!r}, expected={SCHEMA_ID!r}"
        )

    authority_boundary = snapshot.get("authority_boundary")
    if authority_boundary != AUTHORITY_BOUNDARY:
        errors.append(
            "authority_boundary mismatch: "
            f"snapshot={authority_boundary!r}, expected={AUTHORITY_BOUNDARY!r}"
        )

    if snapshot.get("release_authority_claim") is not False:
        errors.append(
            "publication snapshot must set release_authority_claim to false"
        )

    expected_status_sha = _digest_entry(snapshot, STATUS_NAME)
    if not expected_status_sha:
        errors.append(f"snapshot missing sha256 entry for {STATUS_NAME}")
    else:
        actual_status_sha = _sha256(status_path)
        if actual_status_sha != expected_status_sha:
            errors.append(
                f"digest mismatch: {STATUS_NAME} "
                f"(snapshot={expected_status_sha}, actual={actual_status_sha})"
            )

    expected_ledger_sha = _digest_entry(snapshot, LEDGER_NAME)
    if not expected_ledger_sha:
        errors.append(f"snapshot missing sha256 entry for {LEDGER_NAME}")
    else:
        actual_ledger_sha = _sha256(ledger_path)
        if actual_ledger_sha != expected_ledger_sha:
            errors.append(
                f"digest mismatch: {LEDGER_NAME} "
                f"(snapshot={expected_ledger_sha}, actual={actual_ledger_sha})"
            )

    expected_identity = _status_run_identity(status)
    snapshot_identity = _snapshot_run_identity(snapshot)

    if not snapshot_identity:
        errors.append("snapshot missing object field: run_identity")
    else:
        for field, expected in expected_identity.items():
            actual = snapshot_identity.get(field, "")
            if actual != expected:
                errors.append(
                    f"run identity mismatch: {field} "
                    f"(snapshot={actual!r}, status={expected!r})"
                )

    if index_path is not None and index_path.exists():
        index_sha = _sha256(index_path)
        ledger_sha = _sha256(ledger_path)
        if index_sha != ledger_sha:
            errors.append(
                f"{INDEX_NAME} does not match {LEDGER_NAME} "
                f"(index_sha256={index_sha}, ledger_sha256={ledger_sha})"
            )

    return errors


def check_paths(
    *,
    snapshot_path: Path,
    status_path: Path,
    ledger_path: Path,
    index_path: Path | None = None,
) -> List[str]:
    errors: List[str] = []

    required_paths = [
        ("publication snapshot", snapshot_path),
        ("status", status_path),
        ("ledger", ledger_path),
    ]

    for label, path in required_paths:
        if not path.exists():
            errors.append(f"{label} file missing: {path}")

    if errors:
        return errors

    snapshot = _load_json_object(snapshot_path)
    status = _load_json_object(status_path)

    return publication_snapshot_errors(
        snapshot,
        status,
        status_path=status_path,
        ledger_path=ledger_path,
        index_path=index_path,
    )


def _resolve_paths(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> tuple[Path, Path, Path, Path | None]:
    if args.root:
        root = Path(args.root)
        snapshot_path = Path(args.snapshot) if args.snapshot else root / SNAPSHOT_NAME
        status_path = Path(args.status) if args.status else root / STATUS_NAME
        ledger_path = Path(args.ledger) if args.ledger else root / LEDGER_NAME
        index_path = Path(args.index) if args.index else root / INDEX_NAME
        return snapshot_path, status_path, ledger_path, index_path

    missing = [
        name
        for name, value in [
            ("--snapshot", args.snapshot),
            ("--status", args.status),
            ("--ledger", args.ledger),
        ]
        if not value
    ]
    if missing:
        parser.error(
            "Either provide --root or provide explicit paths: "
            + ", ".join(missing)
        )

    snapshot_path = Path(args.snapshot)
    status_path = Path(args.status)
    ledger_path = Path(args.ledger)
    index_path = Path(args.index) if args.index else None

    return snapshot_path, status_path, ledger_path, index_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail closed when published status/report/index files do not "
            "match publication_snapshot_v0.json."
        )
    )
    parser.add_argument(
        "--root",
        help=(
            "Publication root containing publication_snapshot_v0.json, "
            "status.json, report_card.html, and optionally index.html."
        ),
    )
    parser.add_argument("--snapshot", help="Path to publication_snapshot_v0.json")
    parser.add_argument("--status", help="Path to status.json")
    parser.add_argument("--ledger", help="Path to report_card.html")
    parser.add_argument("--index", help="Optional path to index.html")

    args = parser.parse_args(argv)

    snapshot_path, status_path, ledger_path, index_path = _resolve_paths(
        args,
        parser,
    )

    try:
        errors = check_paths(
            snapshot_path=snapshot_path,
            status_path=status_path,
            ledger_path=ledger_path,
            index_path=index_path,
        )
    except Exception as exc:  # pragma: no cover - CLI fail-closed path
        print("ERROR: publication snapshot check crashed.")
        print(f" - {type(exc).__name__}: {exc}")
        return 1

    if errors:
        print("ERROR: publication snapshot check failed.")
        print(f"snapshot: {snapshot_path}")
        print(f"status: {status_path}")
        print(f"ledger: {ledger_path}")
        if index_path is not None:
            print(f"index: {index_path}")
        for err in errors:
            print(f" - {err}")
        return 1

    print("OK: publication snapshot matches published files")
    print(f"snapshot: {snapshot_path}")
    print(f"status: {status_path}")
    print(f"ledger: {ledger_path}")
    if index_path is not None and index_path.exists():
        print(f"index: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
