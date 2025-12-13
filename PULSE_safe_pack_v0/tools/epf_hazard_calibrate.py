#!/usr/bin/env python3
"""
epf_hazard_calibrate.py

Offline helper to calibrate EPF hazard thresholds (warn / crit)
from an epf_hazard_log.jsonl file.

Idea:
- take the observed distribution of E per gate_id,
- choose warn / crit as percentiles (e.g. warn=P85, crit=P97),
- so only the top tail becomes AMBER / RED.

Relational Grail groundwork:
- optionally fit robust per-feature scalers (median/MAD) from snapshot_current
  values in the hazard JSONL log, and emit them under "feature_scalers" in the
  output JSON artifact when sample counts are sufficient.
- emit a deterministic "recommended_features" list (bounded, coverage-aware).

NEW (Step 11):
- emit feature coverage diagnostics:
    * feature_coverage: per-feature present/missing/coverage ratio
    * feature_coverage_top_missing: top-N most-missing features (debug hotspot list)
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

# ---------------------------------------------------------------------------
# Import robust scaler primitives (script-safe import)
# ---------------------------------------------------------------------------

def _ensure_repo_root_on_syspath() -> None:
    here = pathlib.Path(__file__).resolve()
    for p in (here,) + tuple(here.parents):
        if p.name == "PULSE_safe_pack_v0":
            repo_root = p.parent
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
            return


try:
    from PULSE_safe_pack_v0.epf.epf_hazard_features import RobustScaler, FeatureScalersArtifactV0
except ModuleNotFoundError:
    _ensure_repo_root_on_syspath()
    from PULSE_safe_pack_v0.epf.epf_hazard_features import RobustScaler, FeatureScalersArtifactV0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate EPF hazard thresholds and optional feature scalers from epf_hazard_log.jsonl."
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
            "(default: 20). This also guards scaler fitting."
        ),
    )
    parser.add_argument(
        "--out-json",
        type=pathlib.Path,
        default=None,
        help="Optional path to write suggested thresholds as JSON.",
    )

    # Recommendation knobs (support both old and new flag spellings)
    parser.add_argument(
        "--recommend-min-coverage",
        "--min-coverage",
        dest="recommend_min_coverage",
        type=float,
        default=0.80,
        help="Minimum coverage ratio in [0,1] for a feature to be recommended (default: 0.80).",
    )
    parser.add_argument(
        "--recommend-max-features",
        "--max-features",
        dest="recommend_max_features",
        type=int,
        default=64,
        help="Maximum number of recommended features to emit (default: 64).",
    )

    # NEW: coverage hotspot list size
    parser.add_argument(
        "--coverage-top",
        type=int,
        default=20,
        help="Top-N most-missing snapshot features to report in the artifact (default: 20).",
    )

    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# JSONL parsing
# ---------------------------------------------------------------------------

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


def collect_E_by_gate(entries: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    by_gate: Dict[str, List[float]] = {}
    for ev in entries:
        gate_id = str(ev.get("gate_id", "UNKNOWN"))
        hazard = ev.get("hazard", {})
        if not isinstance(hazard, dict):
            continue
        E = hazard.get("E")
        if isinstance(E, (int, float)) and math.isfinite(float(E)):
            by_gate.setdefault(gate_id, []).append(float(E))
    return by_gate


# ---------------------------------------------------------------------------
# Snapshot feature collection (dotted keys)
# ---------------------------------------------------------------------------

def _flatten_numeric_mapping_dotted(
    m: Mapping[str, object],
    *,
    prefix: str = "",
) -> Iterable[Tuple[str, float]]:
    """
    Deterministically flatten a nested mapping into (dotted_key, float_value).

    Defensive parsing:
      - bool -> 0/1
      - finite int/float
      - numeric strings
      - ignore other types / non-finite

    Traversal is deterministic: sorted by str(key).
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


def collect_feature_values_from_entries(
    entries: List[Dict[str, Any]],
) -> Tuple[int, DefaultDict[str, List[float]], Dict[str, int]]:
    """
    Collect numeric feature values from snapshot_current across entries.

    Returns:
        snapshot_event_count: #entries that contain snapshot_current mapping
        feature_values: dotted_key -> list of values
        feature_present_counts: dotted_key -> #entries where key was present
    """
    snapshot_event_count = 0
    feature_values: DefaultDict[str, List[float]] = defaultdict(list)
    feature_present_counts: Dict[str, int] = {}

    for ev in entries:
        snap_cur = ev.get("snapshot_current")
        if not isinstance(snap_cur, Mapping):
            continue

        snapshot_event_count += 1

        # count each dotted key once per event for presence
        present_keys = set()
        for dotted_key, val in _flatten_numeric_mapping_dotted(snap_cur):
            feature_values[dotted_key].append(val)
            present_keys.add(dotted_key)

        for k in present_keys:
            feature_present_counts[k] = feature_present_counts.get(k, 0) + 1

    return snapshot_event_count, feature_values, feature_present_counts


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

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


def _iqr(values: List[float]) -> float:
    if not values:
        return 0.0
    return max(0.0, percentile(values, 0.75) - percentile(values, 0.25))


# ---------------------------------------------------------------------------
# Recommendation + coverage
# ---------------------------------------------------------------------------

def recommend_features(
    *,
    scaler_keys: List[str],
    feature_values: Mapping[str, List[float]],
    feature_present_counts: Mapping[str, int],
    snapshot_event_count: int,
    max_features: int,
    min_coverage: float,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Deterministically recommend a bounded feature set for autowire.

    Strategy:
      1) filter by coverage >= min_coverage
      2) rank by (coverage desc, IQR desc, key asc)
      3) if empty but scalers exist -> fallback to top by the same ranking without coverage filter
    """
    max_features_i = int(max_features)
    if max_features_i <= 0 or snapshot_event_count <= 0:
        return [], {
            "max_features": max_features_i,
            "min_coverage": float(min_coverage),
            "snapshot_event_count": int(snapshot_event_count),
            "candidates": 0,
            "selected": 0,
            "fallback_used": False,
        }

    base = []
    for k in sorted(set(map(str, scaler_keys))):
        vals = feature_values.get(k)
        if not isinstance(vals, list) or not vals:
            continue
        present = int(feature_present_counts.get(k, 0))
        cov = present / float(snapshot_event_count)
        spread = _iqr(vals)
        base.append((k, cov, spread, present))

    if not base:
        return [], {
            "max_features": max_features_i,
            "min_coverage": float(min_coverage),
            "snapshot_event_count": int(snapshot_event_count),
            "candidates": 0,
            "selected": 0,
            "fallback_used": False,
        }

    min_cov = float(min_coverage)
    if not (0.0 <= min_cov <= 1.0):
        min_cov = 0.0

    filtered = [(k, cov, spread, present) for (k, cov, spread, present) in base if cov >= min_cov]

    def rank_key(t: Tuple[str, float, float, int]) -> Tuple[float, float, str]:
        k, cov, spread, _present = t
        return (-cov, -spread, k)

    fallback_used = False
    cand = filtered
    if not cand:
        cand = base
        fallback_used = True

    cand_sorted = sorted(cand, key=rank_key)
    selected = cand_sorted[:max_features_i]
    recommended = [k for (k, _cov, _spread, _present) in selected]

    meta = {
        "max_features": max_features_i,
        "min_coverage": float(min_coverage),
        "snapshot_event_count": int(snapshot_event_count),
        "candidates": int(len(base)),
        "selected": int(len(recommended)),
        "fallback_used": bool(fallback_used),
        "selected_min_coverage": float(min(cov for (_k, cov, _s, _p) in selected)) if selected else 0.0,
    }
    return recommended, meta


def build_feature_coverage(
    *,
    feature_present_counts: Mapping[str, int],
    snapshot_event_count: int,
) -> Dict[str, Dict[str, Any]]:
    """
    Build per-feature coverage mapping: present/missing/coverage.
    """
    out: Dict[str, Dict[str, Any]] = {}
    if snapshot_event_count <= 0:
        return out

    for k in sorted(feature_present_counts.keys()):
        present = int(feature_present_counts.get(k, 0))
        missing = int(snapshot_event_count - present)
        cov = present / float(snapshot_event_count)
        out[str(k)] = {
            "present": present,
            "missing": missing,
            "coverage": float(cov),
        }
    return out


def top_missing_features(
    *,
    feature_coverage: Mapping[str, Mapping[str, Any]],
    top_n: int,
) -> List[Dict[str, Any]]:
    """
    Return top-N most-missing features from feature_coverage mapping.
    """
    n = max(0, int(top_n))
    rows = []
    for k, v in feature_coverage.items():
        missing = v.get("missing", 0)
        present = v.get("present", 0)
        cov = v.get("coverage", 0.0)
        try:
            missing_i = int(missing)
            present_i = int(present)
            cov_f = float(cov)
        except Exception:
            continue
        if missing_i <= 0:
            continue
        rows.append((missing_i, cov_f, str(k), present_i))

    # Sort: most missing first, then lowest coverage, then key
    rows.sort(key=lambda t: (-t[0], t[1], t[2]))

    out = []
    for (missing_i, cov_f, k, present_i) in rows[:n]:
        out.append({
            "key": k,
            "present": present_i,
            "missing": missing_i,
            "coverage": cov_f,
        })
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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

    if args.recommend_max_features <= 0:
        print(f"invalid --recommend-max-features/--max-features: {args.recommend_max_features}", file=sys.stderr)
        return 1

    if not (0.0 <= args.recommend_min_coverage <= 1.0):
        print(
            f"invalid --recommend-min-coverage/--min-coverage: {args.recommend_min_coverage} (must be in [0,1])",
            file=sys.stderr,
        )
        return 1

    if args.coverage_top < 0:
        print(f"invalid --coverage-top: {args.coverage_top}", file=sys.stderr)
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

    all_E: List[float] = [e for values in by_gate.values() for e in values]
    if not all_E:
        print("no numeric E values found in log", file=sys.stderr)
        return 1

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

    feature_scalers_payload: Dict[str, Any] = {}
    recommended_features: List[str] = []
    recommendation_meta: Dict[str, Any] = {}

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
                present = int(feature_present_counts.get(key, 0))
                missing[key] = int(snapshot_event_count - present)

            artifact = FeatureScalersArtifactV0(
                count=int(snapshot_event_count),
                missing=missing,
                features=scalers,
            )
            feature_scalers_payload = artifact.to_dict()

            recommended_features, recommendation_meta = recommend_features(
                scaler_keys=sorted(scalers.keys()),
                feature_values=feature_values,
                feature_present_counts=feature_present_counts,
                snapshot_event_count=snapshot_event_count,
                max_features=int(args.recommend_max_features),
                min_coverage=float(args.recommend_min_coverage),
            )

    # Step 11: compute coverage always (if we have snapshot-bearing entries)
    feature_coverage: Dict[str, Dict[str, Any]] = {}
    feature_coverage_top_missing: List[Dict[str, Any]] = []
    if snapshot_event_count > 0:
        feature_coverage = build_feature_coverage(
            feature_present_counts=feature_present_counts,
            snapshot_event_count=snapshot_event_count,
        )
        feature_coverage_top_missing = top_missing_features(
            feature_coverage=feature_coverage,
            top_n=int(args.coverage_top),
        )

    # Optional artifact output
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

        if feature_scalers_payload:
            payload["feature_scalers"] = feature_scalers_payload

        # Keep coverage independent from scalers (it helps debug snapshot policy even before scalers stabilize)
        if feature_coverage:
            payload["feature_coverage"] = feature_coverage
            payload["feature_coverage_top_missing"] = feature_coverage_top_missing
            payload["feature_coverage_summary"] = {
                "snapshot_event_count": int(snapshot_event_count),
                "unique_features": int(len(feature_coverage)),
                "coverage_top": int(args.coverage_top),
            }

        if feature_scalers_payload and recommended_features:
            payload["recommended_features"] = list(recommended_features)

            # Two names for compatibility: recommendation + recommended_features_meta
            payload["recommendation"] = {
                "min_coverage": float(args.recommend_min_coverage),
                "max_features": int(args.recommend_max_features),
                **{k: v for k, v in recommendation_meta.items() if k not in ("min_coverage", "max_features")},
            }
            payload["recommended_features_meta"] = dict(payload["recommendation"])

        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        with args.out_json.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)

        print()
        print(f"Wrote JSON suggestions to {args.out_json}")

        if feature_scalers_payload:
            n_feats = len(feature_scalers_payload.get("features", {}))
            print(f"Included feature_scalers for {n_feats} feature(s)")

        if feature_coverage:
            print(
                f"Included feature_coverage: unique={len(feature_coverage)} "
                f"(snapshot_events={snapshot_event_count}, top_missing={len(feature_coverage_top_missing)})"
            )

        if feature_scalers_payload and recommended_features:
            fb = bool(payload["recommendation"].get("fallback_used", False))
            print(
                f"Included recommended_features: n={len(recommended_features)} "
                f"(max={args.recommend_max_features}, min_coverage={args.recommend_min_coverage:.2f}, fallback_used={fb})"
            )

    # Also print a quick hotspot section to stdout (useful even without --out-json)
    if feature_coverage_top_missing:
        print()
        print("=== Snapshot coverage hotspots (top missing) ===")
        for row in feature_coverage_top_missing[: min(10, len(feature_coverage_top_missing))]:
            print(
                f"  - {row['key']}: coverage={row['coverage']:.2f} "
                f"(present={row['present']}, missing={row['missing']})"
            )
        if len(feature_coverage_top_missing) > 10:
            print(f"  ... +{len(feature_coverage_top_missing) - 10} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
