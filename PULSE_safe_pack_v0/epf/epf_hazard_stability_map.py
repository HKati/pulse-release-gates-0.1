"""
epf_hazard_stability_map.py

Stability Map v0 for EPF hazard series.

Purpose (Grail-topology oriented):
  - Consume epf_hazard_log.jsonl (JSONL)
  - Build a per-gate "field state" summary from recent history
  - Classify regimes:
      stable         (GREEN)
      unstably_good  (AMBER, drift-dominant)
      unstably_bad   (AMBER, stability-loss dominant)
      hazard         (RED)

This is an artifact builder, not a gate.
Fail-open: parsing errors or missing files should not break CI tooling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
import json
import math
import statistics
from collections import defaultdict, deque


SCHEMA_STABILITY_MAP_V0 = "epf_hazard_stability_map_v0"

# This module lives under PULSE_safe_pack_v0/epf/
PACK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STABILITY_MAP_PATH = PACK_ROOT / "artifacts" / "epf_hazard_stability_map_v0.json"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percentile(values: List[float], p: float) -> float:
    if not values:
        raise ValueError("percentile of empty list")
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


def _safe_mean(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    return float(statistics.mean(xs))


def _isfinite_num(x: Any) -> bool:
    if not isinstance(x, (int, float)):
        return False
    return math.isfinite(float(x))


def _coerce_zone(z: Any) -> str:
    if not isinstance(z, str) or not z.strip():
        return "UNKNOWN"
    up = z.strip().upper()
    if up in ("GREEN", "AMBER", "RED"):
        return up
    return "UNKNOWN"


def _load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    out.append(obj)
    except OSError:
        return []
    return out


def _regime_from_last(last_zone: str, last_D: Optional[float], last_S: Optional[float]) -> Tuple[str, str]:
    """
    Regime classifier focused on topology, not alerts.

    For AMBER we refine into:
      - unstably_good: drift dominates stability-loss
      - unstably_bad : stability-loss dominates drift

    Drift proxy: D
    Stability-loss proxy: (1 - S)
    """
    z = _coerce_zone(last_zone)

    if z == "GREEN":
        return "stable", "GREEN: field stable (below warn regime)."
    if z == "RED":
        return "hazard", "RED: field unstable (hazard regime)."
    if z == "AMBER":
        d = float(last_D) if _isfinite_num(last_D) else 0.0
        s = float(last_S) if _isfinite_num(last_S) else 0.5
        s = max(0.0, min(1.0, s))
        drift_term = abs(d)
        stability_loss = abs(1.0 - s)

        if drift_term >= stability_loss:
            return "unstably_good", "AMBER: drift-dominant pre-hazard (moving but not collapsing)."
        return "unstably_bad", "AMBER: stability-loss dominant pre-hazard (collapse pressure)."

    return "unknown", "UNKNOWN zone: insufficient signal to classify regime."


def _summarize_tail(
    events: List[Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float], str]],
    *,
    tail: int,
) -> Dict[str, Any]:
    """
    events: list of (timestamp, E, T, S, D, zone) ordered oldest->newest
    """
    if not events:
        return {}

    tail_events = events[-tail:] if tail > 0 else list(events)

    zones = [_coerce_zone(z) for (_, _, _, _, _, z) in tail_events]
    zone_counts: Dict[str, int] = {"GREEN": 0, "AMBER": 0, "RED": 0, "UNKNOWN": 0}
    for z in zones:
        zone_counts[z] = zone_counts.get(z, 0) + 1

    E_vals: List[float] = [float(e) for (_, e, _, _, _, _) in tail_events if _isfinite_num(e)]
    T_vals: List[float] = [float(t) for (_, _, t, _, _, _) in tail_events if _isfinite_num(t)]
    S_vals: List[float] = [float(s) for (_, _, _, s, _, _) in tail_events if _isfinite_num(s)]
    D_vals: List[float] = [float(d) for (_, _, _, _, d, _) in tail_events if _isfinite_num(d)]

    last_ts, last_E, last_T, last_S, last_D, last_zone = tail_events[-1]
    regime, regime_reason = _regime_from_last(last_zone, last_D, last_S)

    # Simple directional delta on E (topology hint, not a predictor)
    E_delta = None
    if len(E_vals) >= 2:
        E_delta = float(E_vals[-1] - E_vals[0])

    def stats_block(xs: List[float]) -> Dict[str, Any]:
        if not xs:
            return {"count": 0}
        xs2 = list(xs)
        return {
            "count": int(len(xs2)),
            "min": float(min(xs2)),
            "max": float(max(xs2)),
            "mean": float(statistics.mean(xs2)),
            "p50": float(_percentile(xs2, 0.50)),
            "p90": float(_percentile(xs2, 0.90)),
            "p95": float(_percentile(xs2, 0.95)),
        }

    return {
        "tail_count": int(len(tail_events)),
        "last_timestamp": str(last_ts),
        "last_zone": str(_coerce_zone(last_zone)),
        "last_E": float(last_E) if _isfinite_num(last_E) else None,
        "last_T": float(last_T) if _isfinite_num(last_T) else None,
        "last_S": float(last_S) if _isfinite_num(last_S) else None,
        "last_D": float(last_D) if _isfinite_num(last_D) else None,
        "zone_counts_tail": zone_counts,
        "E_delta_tail": E_delta,
        "E_stats_tail": stats_block(E_vals),
        "T_stats_tail": stats_block(T_vals),
        "S_stats_tail": stats_block(S_vals),
        "D_stats_tail": stats_block(D_vals),
        "regime": str(regime),
        "regime_reason": str(regime_reason),
    }


def build_stability_map_from_log(
    log_path: Path,
    *,
    tail: int = 20,
    max_per_gate: int = 1000,
) -> Dict[str, Any]:
    """
    Build a stability map artifact from a hazard JSONL log.

    - tail controls how many recent events per gate to summarize
    - max_per_gate bounds memory if logs are large
    """
    # Keep bounded history per gate_id
    series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=int(max_per_gate)))

    for ev in _load_jsonl(log_path):
        gate_id = str(ev.get("gate_id", "UNKNOWN"))
        hazard = ev.get("hazard", {}) or {}

        ts = ev.get("timestamp")
        ts_s = str(ts) if isinstance(ts, (str, int, float)) else ""

        zone = hazard.get("zone")
        if zone is None:
            zone = hazard.get("hazard_zone")  # defensive (legacy)

        E = hazard.get("E")
        T = hazard.get("T")
        S = hazard.get("S")
        D = hazard.get("D")

        series[gate_id].append((ts_s, E, T, S, D, str(zone) if zone is not None else "UNKNOWN"))

    gates_out: Dict[str, Any] = {}
    for gate_id in sorted(series.keys()):
        events = list(series[gate_id])  # oldest->newest
        summary = _summarize_tail(events, tail=int(tail))
        summary["count"] = int(len(events))
        gates_out[str(gate_id)] = summary

    return {
        "schema": SCHEMA_STABILITY_MAP_V0,
        "created_utc": _utc_iso(),
        "log_path": str(log_path),
        "tail": int(tail),
        "max_per_gate": int(max_per_gate),
        "gates": gates_out,
    }


def write_stability_map(path: Path, artifact: Mapping[str, Any]) -> None:
    """
    Write stability map JSON artifact (fail-open).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(dict(artifact), f, indent=2, sort_keys=True)
    except OSError:
        return
