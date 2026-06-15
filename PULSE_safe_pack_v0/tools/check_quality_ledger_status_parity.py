#!/usr/bin/env python3
"""Check that the PULSE Quality Ledger matches the final status.json.

This tool is a public reader-surface parity guard. It does not make,
replace, or promote release-authority decisions. It only verifies that an
already-rendered Quality Ledger reflects the provided status.json artefact.

Gate truth rule:
    expected ledger status = PASS iff status["gates"][gate_id] is True
    expected ledger status = FAIL otherwise
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Mapping, Sequence


PASS_FAIL = {"PASS", "FAIL"}


def _collapse_ws(value: Any) -> str:
    return " ".join(unescape(str(value)).split())


class _TableCellParser(HTMLParser):
    """Dependency-free table text extractor for Quality Ledger HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: List[List[str]] = []
        self._in_row = False
        self._in_cell = False
        self._row: List[str] = []
        self._cell_parts: List[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: Sequence[tuple[str, str | None]],
    ) -> None:
        del attrs
        tag = tag.lower()
        if tag == "tr":
            self._in_row = True
            self._row = []
            self._cell_parts = []
            self._in_cell = False
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._in_row and self._in_cell and tag in {"td", "th"}:
            self._row.append(_collapse_ws("".join(self._cell_parts)))
            self._cell_parts = []
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if any(cell for cell in self._row):
                self.rows.append(list(self._row))
            self._row = []
            self._cell_parts = []
            self._in_row = False
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)


def _load_json_object(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected top-level JSON object in {path}")
    return obj


def _extract_rows(html: str) -> List[List[str]]:
    parser = _TableCellParser()
    parser.feed(html)
    parser.close()
    return parser.rows


def _clean_key(value: str) -> str:
    key = _collapse_ws(value)
    if len(key) >= 2 and key.startswith("`") and key.endswith("`"):
        key = key[1:-1].strip()
    return key


def _row_values(rows: Sequence[Sequence[str]]) -> DefaultDict[str, List[str]]:
    values: DefaultDict[str, List[str]] = defaultdict(list)
    for row in rows:
        if len(row) < 2:
            continue
        key = _clean_key(row[0])
        val = _collapse_ws(row[1])
        if key:
            values[key].append(val)
    return values


def _gate_status_values(
    values: Mapping[str, Sequence[str]],
    gate_id: str,
) -> List[str]:
    return [v for v in values.get(gate_id, []) if v in PASS_FAIL]


def _expected_gate_status(raw_value: Any) -> str:
    return "PASS" if raw_value is True else "FAIL"


def parity_errors(status: Mapping[str, Any], ledger_html: str) -> List[str]:
    """Return reader-surface parity errors.

    This function is intentionally side-effect free for direct unit testing.
    """

    errors: List[str] = []

    if "PULSE Quality Ledger" not in ledger_html:
        errors.append("ledger title marker missing: PULSE Quality Ledger")

    gates_raw = status.get("gates")
    if not isinstance(gates_raw, dict):
        return errors + ["status.json is missing object field: gates"]

    metrics_raw = status.get("metrics")
    metrics = metrics_raw if isinstance(metrics_raw, dict) else {}

    rows = _extract_rows(ledger_html)
    values = _row_values(rows)

    if not values:
        errors.append("no two-column table rows found in Quality Ledger HTML")

    for raw_gate_id, raw_value in sorted(
        gates_raw.items(),
        key=lambda item: str(item[0]),
    ):
        gate_id = str(raw_gate_id)
        expected = _expected_gate_status(raw_value)
        actual_values = _gate_status_values(values, gate_id)

        if not actual_values:
            errors.append(
                f"gate row missing or has no PASS/FAIL status: {gate_id} "
                f"(expected {expected})"
            )
            continue

        unique_values = sorted(set(actual_values))
        if len(unique_values) > 1:
            errors.append(
                f"gate row has conflicting statuses: {gate_id} "
                f"(values={unique_values}, expected {expected})"
            )
            continue

        actual = unique_values[0]
        if actual != expected:
            errors.append(
                f"gate status mismatch: {gate_id} "
                f"(ledger={actual}, status.gates expected {expected})"
            )

    identity_fields = [
        ("created_utc", status.get("created_utc")),
        ("metrics.git_sha", metrics.get("git_sha")),
        ("metrics.run_key", metrics.get("run_key")),
    ]

    for field, expected_raw in identity_fields:
        if expected_raw is None or str(expected_raw).strip() == "":
            continue

        expected = _collapse_ws(expected_raw)
        actual_values = [_collapse_ws(v) for v in values.get(field, [])]

        if not actual_values:
            errors.append(f"run identity field missing from ledger: {field}")
            continue

        if expected not in actual_values:
            errors.append(
                f"run identity mismatch: {field} "
                f"(ledger={actual_values}, status={expected!r})"
            )

    return errors


def check_paths(status_path: Path, ledger_path: Path) -> List[str]:
    status = _load_json_object(status_path)
    ledger_html = ledger_path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    return parity_errors(status, ledger_html)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail closed when Quality Ledger gate rows do not match "
            "status.json['gates'] for the same run identity."
        )
    )
    parser.add_argument("--status", required=True, help="Path to status.json")
    parser.add_argument(
        "--ledger",
        required=True,
        help="Path to report_card.html",
    )
    args = parser.parse_args(argv)

    status_path = Path(args.status)
    ledger_path = Path(args.ledger)

    errors = check_paths(status_path, ledger_path)
    if errors:
        print("ERROR: Quality Ledger status parity failed.")
        print(f"status: {status_path}")
        print(f"ledger: {ledger_path}")
        for err in errors:
            print(f" - {err}")
        return 1

    print("OK: Quality Ledger status parity matches status.json")
    print(f"status: {status_path}")
    print(f"ledger: {ledger_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
