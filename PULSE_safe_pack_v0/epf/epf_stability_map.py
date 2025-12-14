"""
epf_stability_map.py

Stability Map v0 — field-first topological map builder for EPF hazard series.

Purpose:
  - Read epf_hazard_log.jsonl (append-only series)
  - Extract last N points for a gate_id
  - Derive a simple topology label per point:
        stably_good / unstably_good / stably_bad / unstably_bad / unknown
    where baseline_ok is inferred from snapshot_current gate leaves (if present).
  - Emit a compact JSON artifact (epf_stability_map_v0.json) under artifacts/.

Design stance (Grail-hű):
  - This is a MAP (regimes), not an alert system.
  - Fail-open: missing/older logs still produce a valid artifact.

Schema:
  {
    "schema": "epf_stability_map_v0",
    "created_utc": "...",
    "gate_id": "...",
    "source_log": "...",
    "window": {"max_points": 60, "points": 12},
    "stats": {...},
    "points": [
      {"timestamp": "...", "E": ..., "T": ..., "S": ..., "D": ...,
       "zone": "GREEN", "baseline_ok": true, "topology_region": "stably_good",
       "feature_mode_active": false, "feature_mode_source": "none", "feature_count": 0,
       "git_sha": "...", "run_key": "..."}
    ]
  }
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union
import json
import logging
import math
import statistics

LOG = logging.getLogger(__name__)

STABILITY_MAP_SCHEMA_V0 = "epf_stability_map_v0"
DEFAULT_STABILITY_MAP_FILENAME = "epf_stability_map_v0.json"
DEFAULT_MAX_POINTS = 60


def compute_topology_region(baseline_ok: Optional[bool], zone: str) -> str:
    """
    Topological regime label from baseline_ok (deterministic gates) and hazard zone.

    baseline_ok:
      True  -> deterministic gates OK
      False -> deterministic gates fail
      None  -> unknown (insufficient info)

    zone:
      GREEN / AMBER / RED (unknown strings tolerated)
    """
    z = str(zone or "").upper().strip()
    if baseline_ok is None:
        return "unknown"

    if baseline_ok is True and z == "GREEN":
        return "stably_good"
    if baseline_ok is True and z in ("AMBER", "RED"):
        return "unstably_good"
    if baseline_ok is False and z == "GREEN":
        return "stably_bad"
    if baseline_ok is False and z in ("AMBER", "RED"):
        return "unstably_bad"
    return "unknown"


def _coerce_finite_float(x: Any) -> Optional[float]:
    if x is None:
        return None
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


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """
    Read a JSONL file defensively. Invalid lines are skipped.
    """
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
    except OSError as exc:  # pragma: no cover
        LOG.warning("Failed to read stability map source log %s: %s", path, exc)
        return []

    return out


def _extract_gate_leaves_from_snapshot(snapshot_current: Any) -> Dict[str, float]:
    """
    Extract gate leaves from snapshot_current.

    Expected shape (from adapter snapshot logging):
      - mapping with flat dotted keys such as:
          "gates.pass_controls_refusal": 1.0
      - possibly nested mappings (we remain defensive)

    Returns:
      dict[str, float] where keys are dotted gate keys, values are floats.
    """
    if not isinstance(snapshot_current, Mapping):
        return {}

    gates: Dict[str, float] = {}

    def walk(m: Mapping[str, Any], prefix: str = "") -> None:
        for k in sorted(m.keys(), key=lambda x: str(x)):
            key = str(k)
            path = f"{prefix}.{key}" if prefix else key
            v = m.get(k)
            if isinstance(v, Mapping):
                walk(v, prefix=path)
                continue
            fv = _coerce_finite_float(v)
            if fv is None:
                continue
            if path.startswith("gates."):
                gates[path] = float(fv)

    walk(snapshot_current)
    return gates


def _baseline_ok_from_snapshot(snapshot_current: Any) -> Tuple[Optional[bool], int, int]:
    """
    Infer baseline gate OK from snapshot_current gates.* values.

    Returns:
      (baseline_ok, pass_count, fail_count)

    Rules:
      - if no gate leaves found -> baseline_ok=None
      - treat value >= 0.5 as PASS
      - ignore gates.epf_hazard_ok if present (shadow gate)
    """
    gates = _extract_gate_leaves_from_snapshot(snapshot_current)
    if not gates:
        return None, 0, 0

    pass_n = 0
    fail_n = 0
    for k, v in gates.items():
        if k == "gates.epf_hazard_ok":
            continue
        if float(v) >= 0.5:
            pass_n += 1
        else:
            fail_n += 1

    if pass_n == 0 and fail_n == 0:
        return None, 0, 0

    return (fail_n == 0), pass_n, fail_n


def _safe_str(x: Any) -> Optional[str]:
    if not isinstance(x, str):
        return None
    s = x.strip()
    return s if s else None


def build_stability_map_from_log(
    *,
    log_path: Union[str, Path],
    gate_id: str,
    created_utc: str,
    max_points: int = DEFAULT_MAX_POINTS,
) -> Dict[str, Any]:
    """
    Build Stability Map payload from hazard log for a single gate_id.
    """
    lp = Path(log_path)
    entries = _read_jsonl(lp)

    # Filter to series (gate_id)
    series: List[Dict[str, Any]] = []
    for ev in entries:
        if str(ev.get("gate_id", "")) == str(gate_id):
            series.append(ev)

    if max_points > 0:
        series = series[-int(max_points) :]

    points: List[Dict[str, Any]] = []
    zone_counts: Dict[str, int] = {}
    topo_counts: Dict[str, int] = {}

    Es: List[float] = []
    Ts: List[float] = []

    for ev in series:
        hazard = ev.get("hazard", {}) or {}
        if not isinstance(hazard, Mapping):
            continue

        ts = _safe_str(ev.get("timestamp")) or ""

        E = _coerce_finite_float(hazard.get("E"))
        T = _coerce_finite_float(hazard.get("T"))
        S = _coerce_finite_float(hazard.get("S"))
        D = _coerce_finite_float(hazard.get("D"))

        zone = str(hazard.get("zone", "UNKNOWN")).upper().strip() or "UNKNOWN"

        baseline_ok, pass_n, fail_n = _baseline_ok_from_snapshot(ev.get("snapshot_current"))
        topo = compute_topology_region(baseline_ok, zone)

        fm_active = hazard.get("feature_mode_active")
        if not isinstance(fm_active, bool):
            # Fail-open for older logs: infer from feature_keys
            keys_raw = hazard.get("feature_keys")
            fm_active = bool(keys_raw) if isinstance(keys_raw, list) else False

        fm_source = hazard.get("feature_mode_source")
        if not isinstance(fm_source, str) or not fm_source.strip():
            fm_source = "unknown" if fm_active else "none"

        feature_keys = hazard.get("feature_keys")
        feature_count = 0
        if isinstance(feature_keys, list):
            feature_count = len([1 for k in feature_keys if str(k).strip()])

        # Optional meta provenance
        meta = ev.get("meta", {}) or {}
        git_sha = _safe_str(meta.get("git_sha")) if isinstance(meta, Mapping) else None
        run_key = _safe_str(meta.get("run_key")) if isinstance(meta, Mapping) else None

        pt: Dict[str, Any] = {
            "timestamp": ts,
            "zone": zone,
            "baseline_ok": baseline_ok,
            "baseline_pass": int(pass_n),
            "baseline_fail": int(fail_n),
            "topology_region": topo,
            "feature_mode_active": bool(fm_active),
            "feature_mode_source": str(fm_source),
            "feature_count": int(feature_count),
        }
        if E is not None:
            pt["E"] = float(E)
            Es.append(float(E))
        if T is not None:
            pt["T"] = float(T)
            Ts.append(float(T))
        if S is not None:
            pt["S"] = float(S)
        if D is not None:
            pt["D"] = float(D)

        if git_sha:
            pt["git_sha"] = git_sha
        if run_key:
            pt["run_key"] = run_key

        points.append(pt)

        zone_counts[zone] = zone_counts.get(zone, 0) + 1
        topo_counts[topo] = topo_counts.get(topo, 0) + 1

    stats: Dict[str, Any] = {
        "zones": dict(sorted(zone_counts.items(), key=lambda kv: kv[0])),
        "topology": dict(sorted(topo_counts.items(), key=lambda kv: kv[0])),
    }

    if Es:
        stats["E"] = {
            "count": len(Es),
            "min": min(Es),
            "max": max(Es),
            "mean": statistics.mean(Es),
        }
    if Ts:
        stats["T"] = {
            "count": len(Ts),
            "min": min(Ts),
            "max": max(Ts),
            "mean": statistics.mean(Ts),
        }

    payload: Dict[str, Any] = {
        "schema": STABILITY_MAP_SCHEMA_V0,
        "created_utc": str(created_utc),
        "gate_id": str(gate_id),
        "source_log": str(lp),
        "window": {
            "max_points": int(max_points),
            "points": int(len(points)),
        },
        "stats": stats,
        "points": points,
    }

    # Convenience: attach latest point (if any)
    if points:
        payload["latest"] = points[-1]

    return payload


def write_stability_map(
    *,
    log_path: Union[str, Path],
    out_path: Union[str, Path],
    gate_id: str,
    created_utc: str,
    max_points: int = DEFAULT_MAX_POINTS,
) -> Dict[str, Any]:
    """
    Build and write Stability Map JSON artifact.

    Returns the payload (even if write fails).
    """
    payload = build_stability_map_from_log(
        log_path=log_path,
        gate_id=gate_id,
        created_utc=created_utc,
        max_points=max_points,
    )

    op = Path(out_path)
    try:
        op.parent.mkdir(parents=True, exist_ok=True)
        with op.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
    except OSError as exc:  # pragma: no cover
        LOG.warning("Failed to write stability map %s: %s", op, exc)

    return payload
