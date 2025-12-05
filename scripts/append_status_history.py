#!/usr/bin/env python3
"""
append_status_history.py

Append a PULSE status.json snapshot to a JSONL history file.

Each line in the history file is a single JSON object with the shape:

    {
        "run_id": "<string>",
        "timestamp": "<ISO 8601 UTC>",
        "status": { ... original status.json content ... }
    }

The script is intentionally small and dependency-free so it can be called
from CI at the end of a PULSE run, for example:

    python scripts/append_status_history.py \
        --status PULSE_safe_pack_v0/artifacts/status.json \
        --output logs/status_history.jsonl \
        --run-id "${{ github.run_id }}"

If --run-id is not provided, the script will try to reuse an existing
`run_id` from the status file (if present) or fall back to a timestamp-
based ID.
"""

import argparse
import datetime as _dt
import json
import os
import sys
from typing import Any, Dict


def _default_status_path() -> str:
    """
    Return a reasonable default for the status.json path.

    We default to PULSE_safe_pack_v0/artifacts/status.json, which is the
    standard location for the safe-pack in most integrations.
    """
    return os.path.join("PULSE_safe_pack_v0", "artifacts", "status.json")


def _parse_args(argv: Any = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append a PULSE status.json snapshot to a JSONL history file."
    )

    parser.add_argument(
        "--status",
        type=str,
        default=_default_status_path(),
        help=(
            "Path to status.json produced by PULSE. "
            "Defaults to PULSE_safe_pack_v0/artifacts/status.json."
        ),
    )

    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join("logs", "status_history.jsonl"),
        help=(
            "Path to the JSONL history file to append to. "
            "Defaults to logs/status_history.jsonl."
        ),
    )

    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help=(
            "Optional explicit run_id to use in the history record. "
            "If not provided, the script will try status['run_id'] or "
            "fall back to a timestamp-based ID."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "If set, do not write to disk; just print the record that "
            "would be appended."
        ),
    )

    return parser.parse_args(argv)


def _load_status(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"status file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"failed to parse JSON from {path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"expected object at top-level in {path}, got {type(data)}")

    return data


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _derive_run_id(explicit: str, status: Dict[str, Any], timestamp: str) -> str:
    if explicit:
        return explicit

    # Try to reuse a run_id from the status.json if present.
    existing = status.get("run_id")
    if isinstance(existing, str) and existing.strip():
        return existing.strip()

    # Fallback: timestamp-based ID.
    return f"run-{timestamp.replace(':', '').replace('-', '').replace('+', '')}"


def main(argv: Any = None) -> int:
    args = _parse_args(argv)

    try:
        status = _load_status(args.status)
    except Exception as exc:  # noqa: BLE001
        print(f"[append_status_history] ERROR: {exc}", file=sys.stderr)
        return 1

    # Always use UTC for history timestamps.
    now = _dt.datetime.now(tz=_dt.timezone.utc)
    timestamp = now.isoformat(timespec="seconds")

    run_id = _derive_run_id(args.run_id, status, timestamp)

    record: Dict[str, Any] = {
        "run_id": run_id,
        "timestamp": timestamp,
        "status": status,
    }

    if args.dry_run:
        print(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2))
        return 0

    try:
        _ensure_parent_dir(args.output)
        with open(args.output, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            f.write("\n")
    except Exception as exc:  # noqa: BLE001
        print(f"[append_status_history] ERROR writing to {args.output}: {exc}", file=sys.stderr)
        return 1

    print(
        f"[append_status_history] Appended run_id={run_id} "
        f"from {args.status} to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
