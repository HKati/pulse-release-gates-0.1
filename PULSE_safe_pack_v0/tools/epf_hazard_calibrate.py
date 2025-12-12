#!/usr/bin/env python3
"""
epf_hazard_calibrate.py

Offline helper to calibrate EPF hazard thresholds (warn / crit)
from an epf_hazard_log.jsonl file.

Idea:
- take the observed distribution of E per gate_id,
- choose warn / crit as percentiles (e.g. warn=P85, crit=P97),
- so only the top tail becomes AMBER / RED.

Also (Relational Grail groundwork):
- optionally fit robust per-feature scalers (median/MAD) from snapshot_current
  values in the hazard JSONL log, and emit them under "feature_scalers" in the
  output JSON artifact when sample counts are sufficient.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping
import json
import math
import pathlib
import statistics
import sys
from typing import Any, DefaultDict, Dict, Iterable, List, Tuple

# Import robust scaler primitives.
# Support both:
#   - module execution: python -m PULSE_safe_pack_v0.epf.epf_hazard_calibrate
#   - script execution: python PULSE_safe_pack_v0/epf/epf_hazard_calibrate.py
if __package__:
    from .epf_hazard_features import RobustScaler, FeatureScalersArtifactV0
else:
    from epf_hazard_features import RobustScaler, FeatureScalersArtifactV0


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate EPF hazard thresholds from epf_hazard_log.jsonl."
    )
    parser.add_argument(
        "--log",
        type=pathlib.Path,
        default=None,
        help=(
            "Path to epf_hazard_log.jsonl. "
            "Defaults to PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl."
        ),
    )
    parser.add_argument(
        "--warn-p",
        type=float,
        default=0.85,
        help="Percentile for warn_threshold in [0,1] (default: 0.85).",
    )
    parser.add_argument(
        "--crit-p",
        type=float,
        default=0.97,
        help="Percentile for crit_threshold in [0,1] (default: 0.97).",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=20,
        help=(
            "Minimum number of E samples per gate to emit per-gate thresholds "
            "(default: 20). This also guards feature scaler emission."
        ),
    )
    parser.add_argument(
        "--out-json",
        type=pathlib.Path,
        default=None,
        help="Optional path to write suggested thresholds as JSON.",
    )
    return parser.parse_args(argv)


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
            entries.append(obj)
    return entries


def collect_E_by_gate(entries: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    by_gate: Dict[str, List[float]] = {}
    for ev in entries:
        gate_id = str(ev.get("gate_id", "UNKNOWN"))
        hazard = ev.get("hazard", {})
        E = hazard.get("E")
        if isinstance(E, (int, float)):
            by_gate.setdefault(gate_id, []).append(float(E))
    return by_gate


def _flatten_numeric_mapping_dotted(
    m: Mapping[str, object],
    *,
    prefix: str = "",
) -> Iterable[Tuple[str, float]]:
    """
    Deterministically flatten a nested mapping into (dotted_key, float_value) pairs.

    The hazard adapter already sanitizes snapshots to numeric-only, but we remain
    defensive here:
      - accepts finite int/float/bool
      - accepts numeric strings
      - ignores non-finite and non-numeric values

    Keys are traversed in deterministic order (sorted by str(k)).
    """
    for k in sorted(m.keys(), key=lambda x: str(x)):
        v = m.get(k)
        key = f"{prefix}.{k}" if prefix else str(k)

        if isinstance(v, Mapping):
            yield from _flatten_numeric_mapping_dotted(v, prefix=key)
            continue

        if isinstance(v, bool):
            yield (key, 1.0 if v else 0.0)
            continue

        if isinstance(v, (int, float)):
            x = float(v)
            if math.isfinite(x):
                yield (key, x)
            continue

        if isinstance(v, str):
            try:
                x = float(v.strip())
                if math.isfinite(x):
                    yield (key, x)
            except Exception:
                pass
            continue

        continue


def collect_feature_values_from_entries(
    entries: List[Dict[str, Any]],
) -> Tuple[int, DefaultDict[str, List[float]], Dict[str, int]]:
    """
    Collect numeric feature values from snapshot_current across entries.

    Returns:
        snapshot_event_count: number of entries that contain snapshot_current mapping
        feature_values: dotted_key -> list of values
        feature_present_counts: dotted_key -> number of entries where the key was present
    """
    snapshot_event_count = 0
    feature_values: DefaultDict[str, List[float]] = defaultdict(list)
    feature_present_counts: Dict[str, int] = {}

    for ev in entries:
        snap_cur = ev.get("snapshot_current")
        if not isinstance(snap_cur, Mapping):
            continue

        snapshot_event_count += 1

        for dotted_key, val in _flatten_numeric_mapping_dotted(snap_cur):
            feature_values[dotted_key].append(val)
            feature_present_counts[dotted_key] = feature_present_counts.get(dotted_key, 0) + 1

    return snapshot_event_count, feature_values, feature_present_counts


def percentile(values: List[float], p: float) -> float:
    """
    Simple percentile with linear interpolation between order stats.
    p is in [0,1].
    """
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


def global_stats(values: List[float]) -> Dict[str, float]:
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


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    if not (0.0 <= args.warn_p < args.crit_p <= 1.0):
        print(
            f"invalid percentiles: require 0 <= warn_p < crit_p <= 1, "
            f"got warn_p={args.warn_p}, crit_p={args.crit_p}",
            file=sys.stderr,
        )
        return 1

    if args.min_samples <= 0:
        print(f"invalid --min-samples: {args.min_samples}", file=sys.stderr)
        return 1

    # Default log path = pack_root/artifacts/epf_hazard_log.jsonl
    if args.log is not None:
        log_path = args.log
    else:
        script_path = pathlib.Path(__file__).resolve()
        pack_root = script_path.parents[1]
        log_path = pack_root / "artifacts" / "epf_hazard_log.jsonl"

    if not log_path.exists():
        print(f"hazard log not found: {log_path}", file=sys.stderr)
        return 1

    entries = load_entries(log_path)
    if not entries:
        print(f"no entries found in log: {log_path}", file=sys.stderr)
        return 1

    by_gate = collect_E_by_gate(entries)

    # Flatten all E values for global thresholds.
    all_E: List[float] = [e for values in by_gate.values() for e in values]
    if not all_E:
        print("no numeric E values found in log", file=sys.stderr)
        return 1

    # Collect feature values for robust scalers (from snapshot_current).
    snapshot_event_count, feature_values, feature_present_counts = collect_feature_values_from_entries(entries)

    print(f"Loaded {len(entries)} log entries from {log_path}")
    print(f"Gates with numeric E: {len(by_gate)}")
    if snapshot_event_count > 0:
        print(f"Entries with snapshot_current: {snapshot_event_count}")
    print()

    gstats = global_stats(all_E)
    global_warn = percentile(all_E, args.warn_p)
    global_crit = percentile(all_E, args.crit_p)

    print("=== Global E statistics ===")
    for k in ["count", "min", "max", "mean", "p50", "p85", "p95", "p97", "p99"]:
        v = gstats[k]
        print(f"  {k:>5}: {v:.4f}" if isinstance(v, float) else f"  {k:>5}: {v}")

    print()
    print(
        f"Suggested GLOBAL thresholds "
        f"(warn_p={args.warn_p:.3f}, crit_p={args.crit_p:.3f}):"
    )
    print(f"  warn_threshold ≈ {global_warn:.4f}")
    print(f"  crit_threshold ≈ {global_crit:.4f}")
    print()

    per_gate_thresholds: Dict[str, Dict[str, float]] = {}

    print("=== Per-gate suggestions (only gates with enough samples) ===")
    for gate_id, values in sorted(by_gate.items()):
        if len(values) < args.min_samples:
            continue
        w = percentile(values, args.warn_p)
        c = percentile(values, args.crit_p)
        per_gate_thresholds[gate_id] = {
            "warn_threshold": w,
            "crit_threshold": c,
            "count": len(values),
        }
        print(
            f"[{gate_id}] n={len(values):4d}  "
            f"warn≈{w:.4f}  crit≈{c:.4f}  "
            f"E_min={min(values):.4f}  E_max={max(values):.4f}"
        )

    # Fit robust feature scalers if enough snapshot-bearing events exist.
    feature_scalers_payload: Dict[str, Any] = {}
    if snapshot_event_count >= args.min_samples and feature_values:
        scalers: Dict[str, RobustScaler] = {}

        for key in sorted(feature_values.keys()):
            vals = feature_values[key]
            if len(vals) < args.min_samples:
                continue
            try:
                scalers[key] = RobustScaler.fit(vals)
            except ValueError:
                continue

        if scalers:
            missing: Dict[str, int] = {}
            for key in sorted(scalers.keys()):
                missing[key] = int(snapshot_event_count - feature_present_counts.get(key, 0))

            artifact = FeatureScalersArtifactV0(
                count=int(snapshot_event_count),
                missing=missing,
                features=scalers,
            )
            feature_scalers_payload = artifact.to_dict()

    if args.out_json is not None:
        payload: Dict[str, Any] = {
            "log_path": str(log_path),
            "warn_p": args.warn_p,
            "crit_p": args.crit_p,
            "global": {
                "warn_threshold": global_warn,
                "crit_threshold": global_crit,
                "stats": gstats,
            },
            "per_gate": per_gate_thresholds,
        }

        # Additive: only include feature_scalers if computed.
        if feature_scalers_payload:
            payload["feature_scalers"] = feature_scalers_payload

        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        with args.out_json.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)

        print()
        print(f"Wrote JSON suggestions to {args.out_json}")
        if feature_scalers_payload:
            n_feats = len(feature_scalers_payload.get("features", {}))
            print(f"Included feature_scalers for {n_feats} feature(s)")
        elif snapshot_event_count > 0:
            print(
                f"Feature scalers not included (need >= {args.min_samples} snapshot-bearing entries "
                f"and per-feature samples)"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
