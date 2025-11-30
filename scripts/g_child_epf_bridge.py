#!/usr/bin/env python
"""
g_child_epf_bridge.py

Bridge overlay between the G-field, EPF status and Paradox summary.
CI-neutral, used only for governance and diagnostic purposes.
"""

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, List, Set


def _load_optional(path_str: str) -> Any:
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_file():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _extract_gate_ids(obj: Any) -> List[str]:
    """
    Nagyon óvatos, generikus gate-id gyűjtés epf_paradox_summary-ből.
    Nem feltételez konkrét sémát, csak megpróbál id / gate_id kulcsokat felszedni.
    """
    ids: Set[str] = set()

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("gate_id", "id", "gate") and isinstance(v, str):
                    ids.add(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(obj)
    return sorted(ids)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bridge overlay for G-field, EPF status and Paradox summary."
    )
    parser.add_argument("--g-field", required=True, help="Path to g_field_v0.json.")
    parser.add_argument(
        "--status-baseline",
        required=False,
        help="Optional path to status_baseline.json from EPF workflow.",
    )
    parser.add_argument(
        "--status-epf",
        required=False,
        help="Optional path to status_epf.json from EPF workflow.",
    )
    parser.add_argument(
        "--paradox-summary",
        required=False,
        help="Optional path to epf_paradox_summary.json.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for g_epf_overlay_v0.json.",
    )
    args = parser.parse_args()

    g_field = _load_optional(args.g_field)
    if g_field is None:
        raise SystemExit(f"[ERROR] g_field_v0.json not found: {args.g_field}")

    status_baseline = _load_optional(args.status_baseline) if args.status_baseline else None
    status_epf = _load_optional(args.status_epf) if args.status_epf else None
    paradox_summary = _load_optional(args.paradox_summary) if args.paradox_summary else None

    paradox_gate_ids: List[str] = []
    if paradox_summary is not None:
        paradox_gate_ids = _extract_gate_ids(paradox_summary)

    # Próbáljuk meg kiszedni azokat a G-pontokat, amelyeknek id-je paradox-gate-id-vel egyezik
    g_points = g_field.get("points", []) if isinstance(g_field, dict) else []
    g_on_paradox: List[Dict[str, Any]] = []
    if paradox_gate_ids and isinstance(g_points, list):
        ids_set = set(paradox_gate_ids)
        for p in g_points:
            pid = str(p.get("id", ""))
            if pid in ids_set:
                g_on_paradox.append(p)

    created_at = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    overlay = {
        "version": "g_epf_overlay_v0",
        "created_at": created_at,
        "g_field": g_field,
        "status_baseline": status_baseline,
        "status_epf": status_epf,
        "epf_paradox_summary": paradox_summary,
        "diagnostics": {
            "paradox_gate_ids": paradox_gate_ids,
            "g_points_on_paradox_gates": g_on_paradox,
        },
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(overlay, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
