#!/usr/bin/env python3
"""Fail-closed presence + parseability check for external detector summaries.

Strict release semantics:
- decoy files such as foo_summary.json must not count as external detector evidence;
- canonical detector summary filenames count;
- --required can override the canonical list with explicit expected filenames;
- --require_metric_key accepts either:
  - a legacy flat metric key at the summary-object level; or
  - a canonical external_summary_v1 metrics[] entry carrying key + value.
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
    return json.loads(
        path.read_text(
            encoding="utf-8",
            errors="strict",
        )
    )


def read_jsonl(path: Path) -> list[object]:
    out: list[object] = []

    with path.open(
        "r",
        encoding="utf-8",
        errors="strict",
    ) as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}: invalid JSON on line {line_no}: {exc}"
                ) from exc

    return out


def _has_legacy_metric_key(
    obj: dict[str, object],
    metric_keys: tuple[str, ...],
) -> bool:
    """Return whether a legacy flat summary carries a known metric key."""

    return any(
        key in obj
        for key in metric_keys
    )


def _has_canonical_metric_entry(
    obj: dict[str, object],
) -> bool:
    """Recognize an external_summary_v1-style metrics[] carrier.

    This precheck intentionally does not replace schema validation.

    It establishes only that at least one declared metric object carries:

    - a non-empty metric key; and
    - a value field.

    Full shape and type validation remains the responsibility of the
    canonical external summary schema.
    """

    metrics = obj.get("metrics")

    if not isinstance(metrics, list) or not metrics:
        return False

    for metric in metrics:
        if not isinstance(metric, dict):
            continue

        metric_key = metric.get("key")

        if (
            isinstance(metric_key, str)
            and metric_key.strip()
            and "value" in metric
        ):
            return True

    return False


def _dict_has_metric_carrier(
    obj: dict[str, object],
    metric_keys: tuple[str, ...],
) -> bool:
    """Recognize either an accepted legacy or canonical metric carrier."""

    return (
        _has_legacy_metric_key(
            obj,
            metric_keys,
        )
        or _has_canonical_metric_entry(obj)
    )


def has_any_metric_key(
    obj: object,
    metric_keys: tuple[str, ...],
) -> bool:
    """Accept legacy flat summaries and canonical metrics[] summaries."""

    if isinstance(obj, dict):
        return _dict_has_metric_carrier(
            obj,
            metric_keys,
        )

    if isinstance(obj, list):
        return any(
            isinstance(item, dict)
            and _dict_has_metric_carrier(
                item,
                metric_keys,
            )
            for item in obj
        )

    return False


def iter_candidate_files(
    external_dir: Path,
) -> Iterable[Path]:
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
        description=(
            "Fail-closed external detector summary precheck."
        )
    )

    parser.add_argument(
        "--external_dir",
        required=True,
        help=(
            "Directory containing external detector "
            "summary artifacts."
        ),
    )

    parser.add_argument(
        "--required",
        action="append",
        default=[],
        help=(
            "Required summary filename. "
            "Repeat for multiple files."
        ),
    )

    parser.add_argument(
        "--require_metric_key",
        action="store_true",
        help=(
            "Require a legacy flat metric key or a canonical "
            "metrics[] entry carrying key + value in each "
            "accepted summary."
        ),
    )

    parser.add_argument(
        "--metric_keys",
        nargs="*",
        default=list(DEFAULT_METRIC_KEYS),
        help=(
            "Override legacy flat metric keys checked by "
            "--require_metric_key."
        ),
    )

    args = parser.parse_args()

    external_dir = Path(args.external_dir)
    metric_keys = tuple(args.metric_keys)

    errors: list[str] = []

    if (
        not external_dir.exists()
        or not external_dir.is_dir()
    ):
        errors.append(
            "external_dir missing or not a directory: "
            f"{external_dir}"
        )

    files: list[Path] = []

    if not errors:
        if args.required:
            files = [
                external_dir / filename
                for filename in args.required
            ]
        else:
            files = list(
                iter_candidate_files(external_dir)
            )

        if not files:
            errors.append(
                "No canonical external detector summaries "
                f"found in: {external_dir} "
                "(expected one of: "
                f"{', '.join(CANONICAL_SUMMARY_FILENAMES)})"
            )

    for path in files:
        if not path.exists():
            errors.append(
                f"Missing required summary: {path}"
            )
            continue

        try:
            obj = parse_summary(path)
        except Exception as exc:
            errors.append(
                f"Unparseable summary: {path} ({exc})"
            )
            continue

        if (
            args.require_metric_key
            and not has_any_metric_key(
                obj,
                metric_keys,
            )
        ):
            errors.append(
                "Summary has no accepted metric carrier "
                f"(legacy keys {metric_keys} or canonical "
                "metrics[] entry with non-empty 'key' and "
                f"present 'value'): {path}"
            )

    if errors:
        print(
            "ERRORS (fail-closed):",
            file=sys.stderr,
        )

        for error in errors:
            print(
                f" - {error}",
                file=sys.stderr,
            )

        return 1

    print(
        "OK: canonical external summaries present and "
        f"parseable ({len(files)} file(s))."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
