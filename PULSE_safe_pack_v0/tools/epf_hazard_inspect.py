#!/usr/bin/env python3
"""
epf_hazard_inspect.py

CLI helper to inspect EPF hazard JSONL logs (epf_hazard_log.jsonl).

Focus:
- summarize hazard E distribution + zone counts
- show recent tail of events
- NEW (Step 9): feature-mode provenance analytics:
    * feature_mode_active ratio
    * feature_mode_source distribution
    * top feature_keys frequency
    * anomalies (inconsistent combinations)

This tool is read-only and fail-open in parsing (skips malformed lines).
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


def _default_log_path() -> pathlib.Path:
    # This file lives in PULSE_safe_pack_v0/tools/
    # pack_root = .../PULSE_safe_pack_v0
    script_path = pathlib.Path(__file__).resolve()
    pack_root = script_path.parents[1]
    return pack_root / "artifacts" / "epf_hazard_log.jsonl"


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Inspect EPF hazard log (epf_hazard_log.jsonl) and summarize hazard + feature-mode provenance."
    )
    p.add_argument(
        "--log",
        type=pathlib.Path,
        default=None,
        help="Path to epf_hazard_log.jsonl (default: PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl).",
    )
    p.add_argument(
        "--gate",
        action="append",
        default=None,
        help="Filter to a gate_id (repeatable). If omitted, includes all.",
    )
    p.add_argument(
        "--tail",
        type=int,
        default=20,
        help="Show last N events (default: 20). Use 0 to disable.",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Top-K feature keys to list by frequency (default: 10).",
    )
    p.add_argument(
        "--per-gate",
        action="store_true",
        help="Also print a per-gate summary table (can be long).",
    )
    p.add_argument(
        "--out-json",
        type=pathlib.Path,
        default=None,
        help="Optional path to write the computed summary as JSON.",
    )
    return p.parse_args(argv)


def _safe_float(x: Any) -> Optional[float]:
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    if isinstance(x, (int, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    if isinstance(x, str):
        try:
            v = float(x.strip())
            return v if math.isfinite(v) else None
        except Exception:
            return None
    return None


def _safe_bool(x: Any) -> Optional[bool]:
    if isinstance(x, bool):
        return x
    return None


def _safe_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def load_entries(path: pathlib.Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                entries.append(obj)
    return entries


def filter_entries(entries: List[Dict[str, Any]], gate_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    if not gate_ids:
        return entries
    wanted = set(str(g).strip() for g in gate_ids if str(g).strip())
    if not wanted:
        return entries
    out: List[Dict[str, Any]] = []
    for ev in entries:
        gid = _safe_str(ev.get("gate_id")) or "UNKNOWN"
        if gid in wanted:
            out.append(ev)
    return out


def percentile(values: List[float], p: float) -> float:
    if not values:
        raise ValueError("cannot compute percentile of empty list")
    vs = sorted(values)
    if p <= 0.0:
        return vs[0]
    if p >= 1.0:
        return vs[-1]
    k = (len(vs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vs[f]
    frac = k - f
    return vs[f] + (vs[c] - vs[f]) * frac


def summarize_E(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "p50": percentile(values, 0.50),
        "p85": percentile(values, 0.85),
        "p95": percentile(values, 0.95),
        "p97": percentile(values, 0.97),
        "p99": percentile(values, 0.99),
    }


def _extract_feature_keys(hazard: Mapping[str, Any]) -> List[str]:
    raw = hazard.get("feature_keys")
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for x in raw:
        s = _safe_str(x)
        if s:
            out.append(s)
    return out


def _derive_feature_mode_active(hazard: Mapping[str, Any], keys: List[str]) -> bool:
    b = _safe_bool(hazard.get("feature_mode_active"))
    if b is not None:
        return bool(b)
    # backwards-compatible: if the field doesn't exist, infer from keys
    return bool(keys)


def _derive_feature_mode_source(hazard: Mapping[str, Any], keys: List[str]) -> str:
    s = _safe_str(hazard.get("feature_mode_source"))
    if s:
        return s
    # legacy logs without this field
    return "legacy_unknown" if keys else "none"


def _extract_T_scaled(hazard: Mapping[str, Any]) -> Optional[bool]:
    b = _safe_bool(hazard.get("T_scaled"))
    return b


def _extract_zone(hazard: Mapping[str, Any]) -> str:
    z = _safe_str(hazard.get("zone"))
    return z or "UNKNOWN"


def _extract_E(hazard: Mapping[str, Any]) -> Optional[float]:
    return _safe_float(hazard.get("E"))


def _extract_timestamp(ev: Mapping[str, Any]) -> str:
    return _safe_str(ev.get("timestamp")) or "UNKNOWN_TIME"


def _extract_gate_id(ev: Mapping[str, Any]) -> str:
    return _safe_str(ev.get("gate_id")) or "UNKNOWN"


def build_summary(entries: List[Dict[str, Any]], top_k: int = 10) -> Dict[str, Any]:
    zones = Counter()
    E_values: List[float] = []

    feature_active_count = 0
    feature_source_counts = Counter()
    feature_key_counts = Counter()
    t_scaled_counts = Counter()  # True/False
    seen_t_scaled_field = False

    anomalies: List[Dict[str, Any]] = []

    per_gate = defaultdict(lambda: {
        "count": 0,
        "zones": Counter(),
        "E": [],
        "feature_active": 0,
        "sources": Counter(),
    })

    for ev in entries:
        hazard = ev.get("hazard", {}) or {}
        if not isinstance(hazard, Mapping):
            continue

        gate_id = _extract_gate_id(ev)
        ts = _extract_timestamp(ev)

        zone = _extract_zone(hazard)
        zones[zone] += 1

        E = _extract_E(hazard)
        if E is not None:
            E_values.append(E)

        keys = _extract_feature_keys(hazard)
        active = _derive_feature_mode_active(hazard, keys)
        source = _derive_feature_mode_source(hazard, keys)

        if active:
            feature_active_count += 1

        feature_source_counts[source] += 1

        for k in keys:
            feature_key_counts[k] += 1

        t_scaled = _extract_T_scaled(hazard)
        if t_scaled is not None:
            seen_t_scaled_field = True
            t_scaled_counts[bool(t_scaled)] += 1

        # Anomaly checks (helpful for debugging)
        # 1) active True but no keys
        if active and not keys:
            anomalies.append({
                "type": "active_true_but_no_keys",
                "gate_id": gate_id,
                "timestamp": ts,
                "source": source,
            })
        # 2) keys exist but active False (inconsistent unless caller forces)
        if (not active) and keys:
            anomalies.append({
                "type": "keys_present_but_active_false",
                "gate_id": gate_id,
                "timestamp": ts,
                "source": source,
                "key_count": len(keys),
            })
        # 3) source indicates something but keys empty (common error class)
        if (not keys) and source not in ("none", "legacy_unknown"):
            anomalies.append({
                "type": "source_non_none_but_no_keys",
                "gate_id": gate_id,
                "timestamp": ts,
                "source": source,
            })

        # per-gate accumulation
        pg = per_gate[gate_id]
        pg["count"] += 1
        pg["zones"][zone] += 1
        if E is not None:
            pg["E"].append(E)
        if active:
            pg["feature_active"] += 1
        pg["sources"][source] += 1

    total = len(entries)
    E_stats = summarize_E(E_values)

    top_features = feature_key_counts.most_common(max(0, int(top_k)))

    feature_active_ratio = (feature_active_count / total) if total > 0 else 0.0

    source_dist = []
    for src, cnt in feature_source_counts.most_common():
        source_dist.append({
            "source": src,
            "count": int(cnt),
            "ratio": (cnt / total) if total > 0 else 0.0,
        })

    t_scaled_summary = None
    if seen_t_scaled_field:
        t_scaled_summary = {
            "scaled_true": int(t_scaled_counts.get(True, 0)),
            "scaled_false": int(t_scaled_counts.get(False, 0)),
            "scaled_ratio": (t_scaled_counts.get(True, 0) / total) if total > 0 else 0.0,
        }

    per_gate_summary = {}
    for gid, pg in per_gate.items():
        n = int(pg["count"])
        Es = list(pg["E"])
        pg_E = summarize_E(Es)
        per_gate_summary[gid] = {
            "count": n,
            "zones": dict(pg["zones"]),
            "E": pg_E,
            "feature_active_ratio": (pg["feature_active"] / n) if n > 0 else 0.0,
            "sources": dict(pg["sources"]),
        }

    return {
        "entries_total": int(total),
        "zones": dict(zones),
        "E": E_stats,
        "feature_mode": {
            "active_count": int(feature_active_count),
            "active_ratio": float(feature_active_ratio),
            "sources": source_dist,
            "top_feature_keys": [{"key": k, "count": int(c)} for (k, c) in top_features],
        },
        "T_scaled": t_scaled_summary,
        "anomalies": anomalies,
        "per_gate": per_gate_summary,
    }


def print_summary_human(summary: Dict[str, Any], *, tail_events: List[Dict[str, Any]], show_per_gate: bool) -> None:
    total = int(summary.get("entries_total", 0) or 0)

    print("=== EPF hazard log inspector ===")
    print(f"Entries: {total}")

    zones = summary.get("zones", {}) or {}
    if zones:
        print("\n=== Zone counts ===")
        for z, c in sorted(zones.items(), key=lambda kv: (-int(kv[1]), kv[0])):
            print(f"  {z:>8}: {int(c)}")

    E = summary.get("E", {}) or {}
    if int(E.get("count", 0) or 0) > 0:
        print("\n=== E distribution ===")
        for k in ["count", "min", "max", "mean", "p50", "p85", "p95", "p97", "p99"]:
            v = E.get(k)
            if isinstance(v, float):
                print(f"  {k:>5}: {v:.4f}")
            else:
                print(f"  {k:>5}: {v}")

    fm = summary.get("feature_mode", {}) or {}
    print("\n=== Feature mode (Relational Grail) ===")
    active_count = int(fm.get("active_count", 0) or 0)
    active_ratio = float(fm.get("active_ratio", 0.0) or 0.0)
    print(f"  active: {active_count}/{total} ({active_ratio*100:.1f}%)")

    sources = fm.get("sources", []) or []
    if sources:
        print("  source distribution:")
        for row in sources:
            src = str(row.get("source", "UNKNOWN"))
            cnt = int(row.get("count", 0) or 0)
            ratio = float(row.get("ratio", 0.0) or 0.0)
            print(f"    - {src}: {cnt} ({ratio*100:.1f}%)")

    top_keys = fm.get("top_feature_keys", []) or []
    if top_keys:
        print("  top feature keys:")
        for row in top_keys:
            k = str(row.get("key", ""))
            c = int(row.get("count", 0) or 0)
            print(f"    - {k}: {c}")

    t_scaled = summary.get("T_scaled")
    if isinstance(t_scaled, dict):
        print("\n=== Scaling ===")
        t_true = int(t_scaled.get("scaled_true", 0) or 0)
        t_false = int(t_scaled.get("scaled_false", 0) or 0)
        ratio = float(t_scaled.get("scaled_ratio", 0.0) or 0.0)
        print(f"  T_scaled: true={t_true} false={t_false} ({ratio*100:.1f}% true)")

    anomalies = summary.get("anomalies", []) or []
    if anomalies:
        print("\n=== Anomalies (first 10) ===")
        for a in anomalies[:10]:
            print(
                f"  - {a.get('type')} gate={a.get('gate_id')} ts={a.get('timestamp')} source={a.get('source')}"
            )
        if len(anomalies) > 10:
            print(f"  ... +{len(anomalies) - 10} more")

    if tail_events:
        print("\n=== Recent events (tail) ===")
        for ev in tail_events:
            hazard = ev.get("hazard", {}) or {}
            gid = _extract_gate_id(ev)
            ts = _extract_timestamp(ev)
            zone = _extract_zone(hazard)
            E = _extract_E(hazard)
            keys = _extract_feature_keys(hazard)
            active = _derive_feature_mode_active(hazard, keys)
            source = _derive_feature_mode_source(hazard, keys)
            e_str = f"{E:.4f}" if isinstance(E, float) else "n/a"
            print(
                f"  - {ts} gate={gid} zone={zone} E={e_str} "
                f"feature_mode={'ON' if active else 'OFF'} source={source} keys={len(keys)}"
            )

    if show_per_gate:
        pg = summary.get("per_gate", {}) or {}
        if pg:
            print("\n=== Per-gate summary (sorted by count desc) ===")
            rows = []
            for gid, row in pg.items():
                n = int(row.get("count", 0) or 0)
                zones = row.get("zones", {}) or {}
                red = int(zones.get("RED", 0) or 0)
                amber = int(zones.get("AMBER", 0) or 0)
                green = int(zones.get("GREEN", 0) or 0)
                E = row.get("E", {}) or {}
                p95 = E.get("p95")
                p95s = f"{float(p95):.4f}" if isinstance(p95, float) else "n/a"
                far = float(row.get("feature_active_ratio", 0.0) or 0.0)
                rows.append((n, gid, red, amber, green, p95s, far))
            rows.sort(key=lambda x: (-x[0], x[1]))

            print("  count  gate_id                         RED  AMBER  GREEN   E_p95   feat_active%")
            for (n, gid, red, amber, green, p95s, far) in rows:
                print(f"  {n:5d}  {gid:<30} {red:4d} {amber:6d} {green:6d}  {p95s:>7}   {far*100:10.1f}")


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    log_path = args.log if args.log is not None else _default_log_path()
    if not log_path.exists():
        print(f"hazard log not found: {log_path}", file=sys.stderr)
        return 1

    entries = load_entries(log_path)
    entries = filter_entries(entries, args.gate)

    summary = build_summary(entries, top_k=int(args.top_k))

    tail_n = int(args.tail)
    tail_events: List[Dict[str, Any]] = []
    if tail_n > 0 and entries:
        tail_events = entries[-tail_n:]

    print_summary_human(summary, tail_events=tail_events, show_per_gate=bool(args.per_gate))

    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        with args.out_json.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, sort_keys=True)
        print(f"\nWrote JSON summary to {args.out_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
