#!/usr/bin/env python3
"""Fail-closed presence + parseability check for external detector summaries.

Strict release semantics:
- decoy files such as foo_summary.json must not count as external detector evidence;
- canonical detector summary filenames count;
- --required can override the canonical list with explicit expected filenames;
- --require_metric_key checks that each accepted file contains at least one metric key.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable


CANONICAL_SUMMARY_FILENAMES = (
    "llamaguard_summary.json",
    "llamaguard_summary.jsonl",
    "promptguard_summary.json",
    "promptguard_summary.jsonl",
    "garak_summary.json",
    "garak_summary.jsonl",
    "azure_eval_summary.json",
    "azure_eval_summary.jsonl",
    "promptfoo_summary.json",
    "promptfoo_summary.jsonl",
    "deepeval_summary.json",
    "deepeval_summary.jsonl",
)

DEFAULT_METRIC_KEYS = (
    "value",
    "rate",
    "violation_rate",
    "attack_detect_rate",
    "azure_indirect_jailbreak_rate",
    "fail_rate",
    "new_critical",
    "failure_rates",
)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def read_jsonl(path: Path) -> list[object]:
    out: list[object] = []
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: invalid JSON on line {line_no}: {exc}") from exc
    return out


def has_any_metric_key(obj: object, metric_keys: tuple[str, ...]) -> bool:
    if isinstance(obj, dict):
        return any(key in obj for key in metric_keys)

    if isinstance(obj, list):
        return any(
            isinstance(item, dict) and any(key in item for key in metric_keys)
            for item in obj
        )

    return False


def iter_candidate_files(external_dir: Path) -> Iterable[Path]:
    for filename in CANONICAL_SUMMARY_FILENAMES:
        path = external_dir / filename
        if path.exists():
            yield path


def parse_summary(path: Path) -> object:
    if path.suffix.lower() == ".jsonl":
        return read_jsonl(path)
    return read_json(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed external detector summary precheck."
    )
    parser.add_argument(
        "--external_dir",
        required=True,
        help="Directory containing external detector summary artifacts.",
    )
    parser.add_argument(
        "--required",
        action="append",
        default=[],
        help="Required summary filename. Repeat for multiple files.",
    )
    parser.add_argument(
        "--require_metric_key",
        action="store_true",
        help="Require at least one expected metric key in each accepted summary.",
    )
    parser.add_argument(
        "--metric_keys",
        nargs="*",
        default=list(DEFAULT_METRIC_KEYS),
        help="Override metric keys checked by --require_metric_key.",
    )
    args = parser.parse_args()

    external_dir = Path(args.external_dir)
    metric_keys = tuple(args.metric_keys)
    errors: list[str] = []

    if not external_dir.exists() or not external_dir.is_dir():
        errors.append(f"external_dir missing or not a directory: {external_dir}")

    files: list[Path] = []
    if not errors:
        if args.required:
            files = [external_dir / filename for filename in args.required]
        else:
            files = list(iter_candidate_files(external_dir))

        if not files:
            errors.append(
                f"No canonical external detector summaries found in: {external_dir} "
                f"(expected one of: {', '.join(CANONICAL_SUMMARY_FILENAMES)})"
            )

    for path in files:
        if not path.exists():
            errors.append(f"Missing required summary: {path}")
            continue

        try:
            obj = parse_summary(path)
        except Exception as exc:
            errors.append(f"Unparseable summary: {path} ({exc})")
            continue

        if args.require_metric_key and not has_any_metric_key(obj, metric_keys):
            errors.append(
                f"Summary has no expected metric key {metric_keys}: {path}"
            )

    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print(f"OK: canonical external summaries present and parseable ({len(files)} file(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
