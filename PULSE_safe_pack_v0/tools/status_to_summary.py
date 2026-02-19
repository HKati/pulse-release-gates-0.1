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


def _as_bool_or_none(x: Any) -> bool | None:
    return x if isinstance(x, bool) else None


def is_pass(v: Any) -> bool:
    # True-only PASS: fail-closed megjelenítés
    return v is True


def build_gate_flags(status: dict[str, Any]) -> list[dict[str, Any]]:
    gates = status.get("gates") or {}
    if not isinstance(gates, dict):
        gates = {}

    out: list[dict[str, Any]] = []
    for gate_id in sorted((str(k) for k in gates.keys()), key=lambda x: x):
        v = gates.get(gate_id)
        out.append(
            {
                "gate_id": gate_id,
                "value": v,
                "flag": "PASS" if is_pass(v) else "FAIL",
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--status", required=True, help="Path to artifacts/status.json")
    ap.add_argument("--out_md", default="", help="Optional output path for Markdown summary")
    ap.add_argument("--out_json", default="", help="Optional output path for JSON summary")
    ap.add_argument(
        "--gate-flags-json",
        action="store_true",
        help="Emit gate flags as JSON to stdout (deterministic; True-only PASS).",
    )
    args = ap.parse_args()

    status_path = pathlib.Path(args.status)
    if not status_path.exists():
        gh_warn(f"status.json not found at {status_path}; skipping summary generation.")
        return 0

    status = safe_read_json(status_path)
    if not isinstance(status, dict):
        gh_warn("status.json is not a JSON object; skipping summary generation.")
        return 0

    if args.gate_flags_json:
        rows = build_gate_flags(status)
        payload = {
            "counts": {
                "total": len(rows),
                "pass": sum(1 for r in rows if r["flag"] == "PASS"),
                "fail": sum(1 for r in rows if r["flag"] == "FAIL"),
            },
            "gate_flags": rows,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    version = str(status.get("version", "") or "")
    created_utc = str(status.get("created_utc", "") or "")

    gates = status.get("gates") or {}
    metrics = status.get("metrics") or {}
    external = status.get("external") or {}

    if not isinstance(gates, dict):
        gates = {}
    if not isinstance(metrics, dict):
        metrics = {}
    if not isinstance(external, dict):
        external = {}

    run_mode = str(metrics.get("run_mode", "") or "").strip().lower()

    # Deterministic gate list
    gate_items: list[tuple[str, bool]] = []
    for k in sorted(gates.keys(), key=lambda x: str(x)):
        v = gates.get(k)
        gate_items.append((str(k), bool(v is True)))

    total = len(gate_items)
    passed = sum(1 for _, ok in gate_items if ok)
    failed = total - passed
    failing = [k for k, ok in gate_items if not ok]

    # ---------------------------------------------------------------------
    # Canonical signals: prefer status.gates.* (contract-aligned),
    # then fall back to status.external / top-level mirrors if present.
    # ---------------------------------------------------------------------

    # Prefer gates.* (contract-first), then external.all_pass, then top-level mirrors
    external_all_pass = _as_bool_or_none(gates.get("external_all_pass"))
    if external_all_pass is None:
        external_all_pass = _as_bool_or_none(external.get("all_pass"))
    if external_all_pass is None:
        external_all_pass = _as_bool_or_none(status.get("external_all_pass"))

    refusal_delta_pass = _as_bool_or_none(gates.get("refusal_delta_pass"))
    if refusal_delta_pass is None:
        refusal_delta_pass = _as_bool_or_none(status.get("refusal_delta_pass"))

    summary_json: dict[str, Any] = {
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

    md_lines: list[str] = []
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
