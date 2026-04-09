#!/usr/bin/env python3
"""
PULSE fold_relational_gain_shadow.py

Fold a Shadow-only relational gain artifact into status.json under:

    status["meta"]["relational_gain_shadow"]

Rules:
- additive only (when artifact exists)
- non-normative
- all-or-nothing
- absence is neutral if --if-present is used
- must not modify gates.*

Note on --if-present:
- if artifact is missing, stale meta.relational_gain_shadow is removed
- all other status/meta content is preserved
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


ALLOWED_VERDICTS = {"PASS", "WARN", "FAIL"}
EXPECTED_CHECKER_VERSION = "relational_gain_v0"


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _fail(msg: str) -> None:
    _eprint(f"[X] {msg}")
    raise SystemExit(2)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _fail(f"file not found: {path}")
    except json.JSONDecodeError as e:
        _fail(f"invalid JSON at {path}: {e}")
    except OSError as e:
        _fail(f"failed to read {path}: {e}")

    if not isinstance(data, dict):
        _fail(f"expected JSON object at {path}")

    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as e:
        _fail(f"failed to write {path}: {e}")


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _read_required_number(container: dict[str, Any], key: str) -> float:
    value = container.get(key)
    if not _is_finite_number(value):
        _fail(f"expected '{key}' to be a finite number")
    return float(value)


def _read_required_nonnegative_int(container: dict[str, Any], key: str) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        _fail(f"expected '{key}' to be an integer")
    if value < 0:
        _fail(f"expected '{key}' to be >= 0")
    return value


def _sha256_file(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as e:
        _fail(f"failed to read bytes for sha256 from {path}: {e}")
    return hashlib.sha256(raw).hexdigest()


def _build_fold_in(
    shadow_artifact: dict[str, Any],
    shadow_artifact_path: Path,
) -> dict[str, Any]:
    checker_version = shadow_artifact.get("checker_version")
    if checker_version != EXPECTED_CHECKER_VERSION:
        _fail(
            "shadow artifact has unexpected 'checker_version': "
            f"expected '{EXPECTED_CHECKER_VERSION}', got {checker_version!r}"
        )

    verdict = shadow_artifact.get("verdict")
    if verdict not in ALLOWED_VERDICTS:
        _fail("shadow artifact is missing a valid 'verdict'")

    metrics = shadow_artifact.get("metrics")
    if not isinstance(metrics, dict):
        _fail("shadow artifact is missing a valid 'metrics' object")

    max_edge_gain = _read_required_number(metrics, "max_edge_gain")
    max_cycle_gain = _read_required_number(metrics, "max_cycle_gain")
    warn_threshold = _read_required_number(metrics, "warn_threshold")
    checked_edges = _read_required_nonnegative_int(metrics, "checked_edges")
    checked_cycles = _read_required_nonnegative_int(metrics, "checked_cycles")

    return {
        "verdict": verdict,
        "max_edge_gain": max_edge_gain,
        "max_cycle_gain": max_cycle_gain,
        "warn_threshold": warn_threshold,
        "checked_edges": checked_edges,
        "checked_cycles": checked_cycles,
        "artifact": {
            "path": str(shadow_artifact_path),
            "sha256": _sha256_file(shadow_artifact_path),
        },
    }


def _fold_into_status(
    status_payload: dict[str, Any],
    fold_in: dict[str, Any],
) -> dict[str, Any]:
    out = dict(status_payload)

    meta = out.get("meta")
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        _fail("status.json field 'meta' must be an object if present")

    if "gates" in fold_in:
        _fail("fold-in must not introduce gates.* content")

    meta_out = dict(meta)
    meta_out["relational_gain_shadow"] = fold_in
    out["meta"] = meta_out
    return out


def _drop_existing_fold_in(status_payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(status_payload)

    meta = out.get("meta")
    if meta is None:
        return out
    if not isinstance(meta, dict):
        _fail("status.json field 'meta' must be an object if present")

    if "relational_gain_shadow" not in meta:
        return out

    meta_out = dict(meta)
    meta_out.pop("relational_gain_shadow", None)

    if meta_out:
        out["meta"] = meta_out
    else:
        out.pop("meta", None)

    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fold a Shadow-only relational gain artifact into status.json "
            "under meta.relational_gain_shadow."
        )
    )
    parser.add_argument(
        "--status",
        required=True,
        help="Path to the input status.json",
    )
    parser.add_argument(
        "--shadow-artifact",
        required=True,
        help="Path to the relational gain shadow artifact JSON",
    )
    parser.add_argument(
        "--out",
        help="Optional output path. If omitted, writes back to --status in place.",
    )
    parser.add_argument(
        "--if-present",
        action="store_true",
        help=(
            "If the shadow artifact is missing, remove stale "
            "meta.relational_gain_shadow and exit 0 instead of failing."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    status_path = Path(args.status)
    shadow_artifact_path = Path(args.shadow_artifact)
    out_path = Path(args.out) if args.out else status_path

    status_payload = _load_json(status_path)

    if not shadow_artifact_path.exists():
        if args.if_present:
            cleaned_status = _drop_existing_fold_in(status_payload)
            _write_json(out_path, cleaned_status)
            return 0
        _fail(f"shadow artifact not found: {shadow_artifact_path}")

    shadow_artifact = _load_json(shadow_artifact_path)
    fold_in = _build_fold_in(shadow_artifact, shadow_artifact_path)
    updated_status = _fold_into_status(status_payload, fold_in)
    _write_json(out_path, updated_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
