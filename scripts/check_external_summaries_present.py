#!/usr/bin/env python3
"""
Fail-closed presence + parseability check for external detector summaries.

Strict semantics:
- Only *_summary.json and *_summary.jsonl count as external detector evidence.
  (Avoid accepting unrelated JSON files as "presence".)

Supports:
- .json  (single JSON object)
- .jsonl (JSON per line)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_METRIC_KEYS = ("value", "rate", "violation_rate", "attack_detect_rate")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def read_jsonl(path: Path) -> list[object]:
    out: list[object] = []
    with path.open("r", encoding="utf-8", errors="strict") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}: invalid JSON on line {i}: {e}") from e
    return out


def has_any_metric_key(obj: object, metric_keys: tuple[str, ...]) -> bool:
    if isinstance(obj, dict):
        return any(k in obj for k in metric_keys)
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict) and any(k in item for k in metric_keys):
                return True
    return False


def iter_candidate_files(external_dir: Path) -> Iterable[Path]:
    # Strict: only detector summaries count as evidence.
    return sorted(external_dir.glob("*_summary.json")) + sorted(external_dir.glob("*_summary.jsonl"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--external_dir", required=True, help="Directory containing external summary artefacts.")
    p.add_argument(
        "--required",
        action="append",
        default=[],
        help="Required summary filename (repeatable). Example: --required llamaguard_summary.json",
    )
    p.add_argument(
        "--require_metric_key",
        action="store_true",
        help=f"Require at least one metric key in each summary (default keys: {DEFAULT_METRIC_KEYS}).",
    )
    p.add_argument(
        "--metric_keys",
        nargs="*",
        default=list(DEFAULT_METRIC_KEYS),
        help="Override metric keys checked by --require_metric_key.",
    )
    args = p.parse_args()

    external_dir = Path(args.external_dir)
    errors: list[str] = []

    if not external_dir.exists() or not external_dir.is_dir():
        errors.append(f"external_dir missing or not a directory: {external_dir}")

    metric_keys = tuple(args.metric_keys)

    files: list[Path] = []
    if not errors:
        if args.required:
            files = [external_dir / name for name in args.required]
        else:
            files = list(iter_candidate_files(external_dir))
            if not files:
                errors.append(
                    f"No external detector summaries found in: {external_dir} "
                    "(expected at least one *_summary.json or *_summary.jsonl)"
                )

    # presence + parseability (+ optional schema-ish check)
    for f in files:
        if not f.exists():
            errors.append(f"Missing required summary: {f}")
            continue

        try:
            if f.suffix.lower() == ".jsonl":
                obj = read_jsonl(f)
            else:
                obj = read_json(f)
        except Exception as e:
            errors.append(f"Unparseable summary: {f} ({e})")
            continue

        if args.require_metric_key:
            if not has_any_metric_key(obj, metric_keys):
                errors.append(
                    f"Summary has no expected metric key {metric_keys}: {f} "
                    "(use --metric_keys to customize or omit --require_metric_key)"
                )

    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: external summaries present and parseable ({len(files)} file(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
