#!/usr/bin/env python3
"""
Generate a small top-level summary from a PULSE status.json.

Design goals:
- Deterministic output (sorted gates, stable formatting).
- Fail-open by default: this is a reporting helper used by snapshot flows.
  Core fail-closed checks are handled elsewhere (schema validation + check_gates).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime
from typing import Any


def gh_warn(msg: str) -> None:
    print(f"::warning::{msg}")


def safe_read_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        gh_warn(f"Failed to read/parse JSON at {path}: {e}")
        return None


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: pathlib.Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--status", required=True, help="Path to artifacts/status.json")
    ap.add_argument("--out_md", default="", help="Optional output path for Markdown summary")
    ap.add_argument("--out_json", default="", help="Optional output path for JSON summary")
    args = ap.parse_args()

    status_path = pathlib.Path(args.status)
    if not status_path.exists():
        gh_warn(f"status.json not found at {status_path}; skipping summary generation.")
        return 0

    status = safe_read_json(status_path)
    if not isinstance(status, dict):
        gh_warn("status.json is not a JSON object; skipping summary generation.")
        return 0

    version = str(status.get("version", "") or "")
    created_utc = str(status.get("created_utc", "") or "")
    gates = status.get("gates") or {}
    metrics = status.get("metrics") or {}

    if not isinstance(gates, dict):
        gates = {}
    if not isinstance(metrics, dict):
        metrics = {}

    run_mode = str(metrics.get("run_mode", "") or "").strip().lower()

    gate_items = []
    for k in sorted(gates.keys(), key=lambda x: str(x)):
        v = gates.get(k)
        gate_items.append((str(k), bool(v is True)))

    total = len(gate_items)
    passed = sum(1 for _, ok in gate_items if ok)
    failed = total - passed
    failing = [k for k, ok in gate_items if not ok]

    external = status.get("external")
    external_all_pass = None
    if isinstance(external, dict):
        external_all_pass = external.get("all_pass")
    # also tolerate top-level mirror if present
    if external_all_pass is None:
        external_all_pass = status.get("external_all_pass")

    refusal_delta_pass = status.get("refusal_delta_pass")

    summary_json = {
        "schema": "pulse_status_summary_v1",
        "generated_utc": datetime.utcnow().isoformat() + "Z",
        "status_path": str(status_path),
        "version": version,
        "created_utc": created_utc,
        "run_mode": run_mode,
        "gates": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "all_pass": (failed == 0 and total > 0),
            "failing": failing,
        },
        "signals": {
            "external_all_pass": external_all_pass,
            "refusal_delta_pass": refusal_delta_pass,
        },
    }

    # Output locations default to sibling files next to status.json
    out_dir = status_path.parent
    out_md = pathlib.Path(args.out_md) if args.out_md else (out_dir / "status_summary.md")
    out_js = pathlib.Path(args.out_json) if args.out_json else (out_dir / "status_summary.json")

    md_lines = []
    md_lines.append("# PULSE status summary")
    md_lines.append("")
    md_lines.append(f"- **version:** `{version}`")
    md_lines.append(f"- **created_utc:** `{created_utc}`")
    md_lines.append(f"- **metrics.run_mode:** `{run_mode}`")
    md_lines.append("")
    md_lines.append("## Gates")
    md_lines.append(f"- total: **{total}**")
    md_lines.append(f"- passed: **{passed}**")
    md_lines.append(f"- failed: **{failed}**")
    md_lines.append(f"- all_pass: **{str(summary_json['gates']['all_pass']).lower()}**")
    if failing:
        md_lines.append("")
        md_lines.append("### Failing gates")
        for g in failing:
            md_lines.append(f"- `{g}`")
    md_lines.append("")
    md_lines.append("## Signals")
    md_lines.append(f"- external_all_pass: `{external_all_pass}`")
    md_lines.append(f"- refusal_delta_pass: `{refusal_delta_pass}`")
    md_lines.append("")

    write_text(out_md, "\n".join(md_lines) + "\n")
    write_json(out_js, summary_json)

    print(f"OK: wrote {out_md}")
    print(f"OK: wrote {out_js}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
