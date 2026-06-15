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
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Mapping, Sequence


PASS_FAIL = {"PASS", "FAIL"}


def _collapse_ws(value: Any) -> str:
    return " ".join(unescape(str(value)).split())


def _clean_key(value: str) -> str:
    key = _collapse_ws(value)
    if len(key) >= 2 and key.startswith("`") and key.endswith("`"):
        key = key[1:-1].strip()
    return key


@dataclass(frozen=True)
class _HtmlTable:
    section: str
    rows: List[List[str]]


class _QualityLedgerHTMLParser(HTMLParser):
    """Dependency-free table extractor with section context."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: List[_HtmlTable] = []

        self._current_section = ""
        self._heading_tag: str | None = None
        self._heading_parts: List[str] = []

        self._in_table = False
        self._table_section = ""
        self._table_rows: List[List[str]] = []

        self._in_row = False
        self._row: List[str] = []

        self._in_cell = False
        self._cell_parts: List[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: Sequence[tuple[str, str | None]],
    ) -> None:
        del attrs
        tag = tag.lower()

        if tag in {"h2", "h3"}:
            self._heading_tag = tag
            self._heading_parts = []
            return

        if tag == "table":
            self._in_table = True
            self._table_section = self._current_section
            self._table_rows = []
            return

        if self._in_table and tag == "tr":
            self._in_row = True
            self._row = []
            return

        if self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []
            return

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if self._heading_tag == tag:
            heading = _collapse_ws("".join(self._heading_parts))
            if heading:
                self._current_section = heading
            self._heading_tag = None
            self._heading_parts = []
            return

        if self._in_row and self._in_cell and tag in {"td", "th"}:
            self._row.append(_collapse_ws("".join(self._cell_parts)))
            self._cell_parts = []
            self._in_cell = False
            return

        if self._in_table and tag == "tr":
            if any(cell for cell in self._row):
                self._table_rows.append(list(self._row))
            self._row = []
            self._in_row = False
            self._in_cell = False
            self._cell_parts = []
            return

        if self._in_table and tag == "table":
            self.tables.append(
                _HtmlTable(
                    section=self._table_section,
                    rows=list(self._table_rows),
                )
            )
            self._in_table = False
            self._table_section = ""
            self._table_rows = []
            self._in_row = False
            self._row = []
            self._in_cell = False
            self._cell_parts = []
            return

    def handle_data(self, data: str) -> None:
        if self._heading_tag is not None:
            self._heading_parts.append(data)
        if self._in_cell:
            self._cell_parts.append(data)


def _load_json_object(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected top-level JSON object in {path}")
    return obj


def _extract_tables(html: str) -> List[_HtmlTable]:
    parser = _QualityLedgerHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.tables


def _has_header(
    table: _HtmlTable,
    expected: Sequence[str],
) -> bool:
    expected_clean = [_collapse_ws(item) for item in expected]
    width = len(expected_clean)

    for row in table.rows:
        if len(row) < width:
            continue
        candidate = [_collapse_ws(cell) for cell in row[:width]]
        if candidate == expected_clean:
            return True

    return False


def _is_gate_table(table: _HtmlTable) -> bool:
    section = _collapse_ws(table.section).lower()
    return "gates" in section and _has_header(table, ["Gate", "Status"])


def _is_traceability_table(table: _HtmlTable) -> bool:
    section = _collapse_ws(table.section).lower()
    return section == "traceability" and _has_header(table, ["Field", "Value"])


def _gate_status_values(
    tables: Sequence[_HtmlTable],
) -> DefaultDict[str, List[str]]:
    values: DefaultDict[str, List[str]] = defaultdict(list)

    for table in tables:
        if not _is_gate_table(table):
            continue

        for row in table.rows:
            if len(row) < 2:
                continue

            key = _clean_key(row[0])
            value = _collapse_ws(row[1])

            if key == "Gate" and value == "Status":
                continue

            if key and value in PASS_FAIL:
                values[key].append(value)

    return values


def _traceability_values(
    tables: Sequence[_HtmlTable],
) -> DefaultDict[str, List[str]]:
    values: DefaultDict[str, List[str]] = defaultdict(list)

    for table in tables:
        if not _is_traceability_table(table):
            continue

        for row in table.rows:
            if len(row) < 2:
                continue

            key = _clean_key(row[0])
            value = _collapse_ws(row[1])

            if key == "Field" and value == "Value":
                continue

            if key:
                values[key].append(value)

    return values


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

    status_gates: Dict[str, Any] = {}
    for raw_gate_id, raw_value in gates_raw.items():
        gate_id = str(raw_gate_id)
        if gate_id in status_gates:
            errors.append(f"duplicate normalized gate id in status.gates: {gate_id}")
        status_gates[gate_id] = raw_value

    metrics_raw = status.get("metrics")
    metrics = metrics_raw if isinstance(metrics_raw, dict) else {}

    tables = _extract_tables(ledger_html)
    gate_values = _gate_status_values(tables)
    trace_values = _traceability_values(tables)

    if not any(_is_gate_table(table) for table in tables):
        errors.append("no Gate/Status table found in Quality Ledger HTML")

    if not any(_is_traceability_table(table) for table in tables):
        errors.append("no Traceability Field/Value table found in Quality Ledger HTML")

    status_gate_ids = set(status_gates)
    ledger_gate_ids = set(gate_values)

    for stale_gate_id in sorted(ledger_gate_ids - status_gate_ids):
        errors.append(
            "stale gate row present in ledger but absent from "
            f"status.gates: {stale_gate_id}"
        )

    for gate_id in sorted(status_gate_ids):
        expected = _expected_gate_status(status_gates[gate_id])
        actual_values = list(gate_values.get(gate_id, []))

        if not actual_values:
            errors.append(
                f"gate row missing or has no PASS/FAIL status: {gate_id} "
                f"(expected {expected})"
            )
            continue

        if len(actual_values) != 1:
            errors.append(
                f"gate row must appear exactly once: {gate_id} "
                f"(values={actual_values}, expected {expected})"
            )
            continue

        actual = actual_values[0]
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
        actual_values = [_collapse_ws(v) for v in trace_values.get(field, [])]

        if not actual_values:
            errors.append(f"run identity field missing from ledger: {field}")
            continue

        if len(actual_values) != 1:
            errors.append(
                f"run identity field must appear exactly once: {field} "
                f"(ledger={actual_values}, status={expected!r})"
            )
            continue

        actual = actual_values[0]
        if actual != expected:
            errors.append(
                f"run identity mismatch: {field} "
                f"(ledger={actual!r}, status={expected!r})"
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
