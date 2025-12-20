#!/usr/bin/env python3
"""
paradox_field_adapter_v0 — minimal, stdlib-only generator for paradox_field_v0.json.

Goal (v0):
  - Create a schema-aligned *skeleton* artefact so the paradox layer exists
    as a stable interface, even before atom extraction is implemented.

Output:
  { "paradox_field_v0": { "meta": {...}, "atoms": [] } }

Determinism:
  - By default, no wall-clock timestamp is emitted.
  - You can include a timestamp explicitly via --created-at or --emit-created-at-now.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from typing import Any, Dict, Optional


def _sha1_file(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _mkdirp_for_file(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


def _require_file(path: str, label: str) -> None:
    if not os.path.isfile(path):
        raise SystemExit(f"[paradox_field_adapter_v0] {label} not found: {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate paradox_field_v0.json (skeleton v0).")
    ap.add_argument("--status", default="", help="Optional status.json path (adds sha1/meta).")
    ap.add_argument("--g-field", default="", help="Optional g_field_v0.json path (adds sha1/meta).")
    ap.add_argument(
        "--out",
        default="PULSE_safe_pack_v0/artifacts/paradox_field_v0.json",
        help="Output path for paradox_field_v0.json",
    )

    # Deterministic by default: do not emit current time unless asked.
    ap.add_argument(
        "--created-at",
        type=int,
        default=None,
        help="Optional unix timestamp to include in meta (deterministic if set).",
    )
    ap.add_argument(
        "--emit-created-at-now",
        action="store_true",
        help="Include current unix time in meta (non-deterministic).",
    )

    args = ap.parse_args()

    meta: Dict[str, Any] = {
        "tool": "scripts/paradox_field_adapter_v0.py",
        "version": "v0",
    }

    if args.created_at is not None:
        meta["created_at"] = int(args.created_at)
    elif args.emit_created_at_now:
        meta["created_at"] = int(time.time())

    if args.status:
        _require_file(args.status, "status.json")
        meta["status_path"] = args.status
        meta["status_sha1"] = _sha1_file(args.status)

    if args.g_field:
        _require_file(args.g_field, "g_field_v0.json")
        meta["g_field_path"] = args.g_field
        meta["g_field_sha1"] = _sha1_file(args.g_field)

    out_obj = {
        "paradox_field_v0": {
            "meta": meta,
            "atoms": [],
        }
    }

    _mkdirp_for_file(args.out)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, indent=2, ensure_ascii=False, sort_keys=True)

    print(f"[paradox_field_adapter_v0] wrote: {args.out}")


if __name__ == "__main__":
    main()
