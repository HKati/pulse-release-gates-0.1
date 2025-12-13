#!/usr/bin/env python3
"""
epf_hazard_inspect.py

CLI helper to inspect EPF hazard JSONL logs (epf_hazard_log.jsonl).

Summaries:
- hazard zones + E distribution
- feature-mode provenance (active ratio, sources, top feature_keys, anomalies)

NEW (Step 11):
- snapshot coverage hotspot summary from snapshot_current:
    * snapshot_event_count
    * unique_features
    * mean/median keys per snapshot
    * coverage_top_missing list

Read-only and fail-open: skips malformed lines.
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
    script_path = pathlib.Path(__file__).resolve()
    pack_root = script_path.parents[1]
    return pack_root / "artifacts" / "epf_hazard_log.jsonl"


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Inspect EPF hazard log and summarize hazard + feature-mode provenance + snapshot coverage."
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
        "--coverage-top",
        type=int,
        default=15,
        help="Top-N most-missing snapshot features to list (default: 15).",
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
    return bool(keys)


def _derive_feature_mode_source(hazard: Mapping[str, Any], keys: List[str]) -> str:
    s = _safe_str(hazard.get("feature_mode_source"))
    if s:
        return s
    return "legacy_unknown" if keys else "none"


def _extract_T_scaled(hazard: Mapping[str, Any]) -> Optional[bool]:
    return _safe_bool(hazard.get("T_scaled"))


def _extract_zone(hazard: Mapping[str, Any]) -> str:
    return _safe_str(hazard.get("zone")) or "UNKNOWN"


def _extract_E(hazard: Mapping[str, Any]) -> Optional[float]:
    return _safe_float(hazard.get("E"))


def _extract_timestamp(ev: Mapping[str, Any]) -> str:
    return _safe_str(ev.get("timestamp")) or "UNKNOWN_TIME"


def _extract_gate_id(ev: Mapping[str, Any]) -> str:
    return _safe_str(ev.get("gate_id")) or "UNKNOWN"


# ---------------------------------------------------------------------------
# NEW: snapshot coverage collection
# ---------------------------------------------------------------------------

def _flatten_snapshot_leaf_keys(m: Mapping[str, Any], prefix: str = "") -> List[str]:
    keys: List[str] = []
    for k in sorted(m.keys(), key=lambda x: str(x)):
        v = m.get(k)
        path = f"{prefix}.{k}" if prefix else str(k)

        if isinstance(v, Mapping):
            keys.extend(_flatten_snapshot_leaf_keys(v, prefix=path))
            continue

        if _safe_float(v) is not None:
            keys.append(path)
            continue

    return keys


def collect_snapshot_coverage(entries: List[Dict[str, Any]]) -> Tuple[int, Counter, List[int]]:
    snapshot_event_count = 0
    present_counts: Counter = Counter()
    keys_per_event: List[int] = []

    for ev in entries:
        snap = ev.get("snapshot_current")
        if not isinstance(snap, Mapping):
            continue

        snapshot_event_count += 1

        ks = set(_flatten_snapshot_leaf_keys(snap, prefix=""))
        keys_per_event.append(len(ks))
        for k in ks:
            present_counts[k] += 1

    return snapshot_event_count, present_counts, keys_per_event


def build_snapshot_coverage_summary(
    *,
    snapshot_event_count: int,
    present_counts: Counter,
    keys_per_event: List[int],
    coverage_top: int,
) -> Dict[str, Any]:
    if snapshot_event_count <= 0:
        return {
            "snapshot_event_count": 0,
            "unique_features": 0,
            "mean_keys_per_event": 0.0,
            "median_keys_per_event": 0.0,
            "coverage_top_missing": [],
        }

    unique_features = len(present_counts)

    mean_keys = statistics.mean(keys_per_event) if keys_per_event else 0.0
    median_keys = statistics.median(keys_per_event) if keys_per_event else 0.0

    rows = []
    for k, present in present_counts.items():
        present_i = int(present)
        missing_i = int(snapshot_event_count - present_i)
        if missing_i <= 0:
            continue
        cov = present_i / float(snapshot_event_count)
        rows.append((missing_i, cov, str(k), present_i))

    # Sort by most missing, then lowest coverage, then key
    rows.sort(key=lambda t: (-t[0], t[1], t[2]))

    top_n = max(0, int(coverage_top))
    top_missing = []
    for (missing_i, cov, k, present_i) in rows[:top_n]:
        top_missing.append({
            "key": k,
            "present": present_i,
            "missing": missing_i,
            "coverage": float(cov),
        })

    return {
        "snapshot_event_count": int(snapshot_event_count),
        "unique_features": int(unique_features),
        "mean_keys_per_event": float(mean_keys),
        "median_keys_per_event": float(median_keys),
        "coverage_top_missing": top_missing,
    }


# ---------------------------------------------------------------------------
# Main summary builder
# ---------------------------------------------------------------------------

def build_summary(entries: List[Dict[str, Any]], *, top_k: int = 10, coverage_top: int = 15) -> Dict[str, Any]:
    zones = Counter()
    E_values: List[float] = []

    feature_active_count = 0
    feature_source_counts = Counter()
    feature_key_counts = Counter()
    t_scaled_counts = Counter()
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

        if active and not keys:
            anomalies.append({
                "type": "active_true_but_no_keys",
                "gate_id": gate_id,
                "timestamp": ts,
                "source": source,
            })
        if (not active) and keys:
            anomalies.append({
                "type": "keys_present_but_active_false",
                "gate_id": gate_id,
                "timestamp": ts,
                "source": source,
                "key_count": len(keys),
            })
        if (not keys) and source not in ("none", "legacy_unknown"):
            anomalies.append({
                "type": "source_non_none_but_no_keys",
                "gate_id": gate_id,
                "timestamp": ts,
                "source": source,
            })

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

    # Step 11: snapshot coverage (snapshot_current)
    snap_n, snap_present_counts, keys_per_event = collect_snapshot_coverage(entries)
    snapshot_coverage = build_snapshot_coverage_summary(
        snapshot_event_count=snap_n,
        present_counts=snap_present_counts,
        keys_per_event=keys_per_event,
        coverage_top=int(coverage_top),
    )

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
        "snapshot_coverage": snapshot_coverage,
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

    # Step 11: snapshot coverage block
    sc = summary.get("snapshot_coverage", {}) or {}
    snap_n = int(sc.get("snapshot_event_count", 0) or 0)
    if snap_n > 0:
        print("\n=== Snapshot coverage (snapshot_current) ===")
        print(f"  snapshot events: {snap_n}")
        print(f"  unique features: {int(sc.get('unique_features', 0) or 0)}")
        print(f"  mean keys/event: {float(sc.get('mean_keys_per_event', 0.0) or 0.0):.1f}")
        print(f"  median keys/event: {float(sc.get('median_keys_per_event', 0.0) or 0.0):.1f}")

        top_missing = sc.get("coverage_top_missing", []) or []
        if top_missing:
            print("  top missing features:")
            for row in top_missing[:10]:
                print(
                    f"    - {row.get('key')}: coverage={float(row.get('coverage', 0.0)):.2f} "
                    f"(present={int(row.get('present', 0))}, missing={int(row.get('missing', 0))})"
                )
            if len(top_missing) > 10:
                print(f"    ... +{len(top_missing) - 10} more")

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

    summary = build_summary(entries, top_k=int(args.top_k), coverage_top=int(args.coverage_top))

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
