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

Feature allowlist:
- optional --feature-allowlist constrains which dotted keys are considered for
  feature_scalers emission, and is written into the output JSON as "feature_allowlist".

NEW (Step 4): coverage + recommendations
- compute per-feature coverage across snapshot-bearing entries:
    coverage = present_count / snapshot_event_count
- emit "feature_coverage" into the artifact (optionally restricted by allowlist)
- emit "recommended_features" (stable, deterministic) based on:
    * scaler exists for the feature (robust scaler fitted)
    * coverage >= recommend_min_coverage
    * limited to recommend_max_features
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
# This tool is often executed as a script from PULSE_safe_pack_v0/tools/,
# where tools/ is not a Python package. To keep the CLI usable even for
# --help, we:
#   1) try absolute import first
#   2) if that fails, add the repo root (parent of PULSE_safe_pack_v0/) to sys.path
#      and retry.
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


def _parse_feature_allowlist(raw: str) -> List[str]:
    """
    Parse comma-separated feature allowlist into a sorted unique list.
    """
    if raw is None:
        return []
    items = [x.strip() for x in str(raw).split(",")]
    items = [x for x in items if x]
    return sorted(set(items))


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
        "--feature-allowlist",
        type=str,
        default="",
        help=(
            "Optional comma-separated list of dotted feature keys to allow for "
            "feature_scalers emission and to persist into the calibration JSON "
            'artifact as "feature_allowlist". Example: "RDSI,external.fail_rate".'
        ),
    )
    parser.add_argument(
        "--recommend-min-coverage",
        type=float,
        default=0.95,
        help=(
            "Minimum per-feature coverage (present_count / snapshot_event_count) "
            "required to be included in recommended_features (default: 0.95)."
        ),
    )
    parser.add_argument(
        "--recommend-max-features",
        type=int,
        default=64,
        help="Maximum number of recommended_features to emit (default: 64).",
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


def _build_feature_coverage(
    *,
    snapshot_event_count: int,
    feature_values: Mapping[str, List[float]],
    feature_present_counts: Mapping[str, int],
    restrict_keys: Optional[List[str]] = None,
) -> Dict[str, Dict[str, float]]:
    """
    Build per-feature coverage statistics.

    Output per key:
      - present_count (int)
      - missing_count (int)
      - coverage (float in [0,1])
      - value_count (int)
    """
    if snapshot_event_count <= 0:
        return {}

    if restrict_keys is not None:
        keys = list(restrict_keys)
    else:
        keys = sorted(set(feature_present_counts.keys()) | set(feature_values.keys()))

    out: Dict[str, Dict[str, float]] = {}
    for k in sorted(set(keys)):
        present = int(feature_present_counts.get(k, 0))
        missing = int(snapshot_event_count - present)
        cov = float(present) / float(snapshot_event_count) if snapshot_event_count > 0 else 0.0
        vcount = int(len(feature_values.get(k, [])))
        out[k] = {
            "present_count": present,
            "missing_count": missing,
            "coverage": cov,
            "value_count": vcount,
        }
    return out


def _select_recommended_features(
    *,
    feature_coverage: Mapping[str, Mapping[str, float]],
    scaler_keys: List[str],
    min_coverage: float,
    max_features: int,
) -> List[str]:
    """
    Select recommended features deterministically.

    Criteria:
      - feature has a fitted scaler (must be in scaler_keys)
      - coverage >= min_coverage

    Sorting:
      - higher coverage first
      - higher present_count next
      - then lexicographic key
    """
    if max_features <= 0:
        return []

    scaler_set = set(scaler_keys)
    candidates: List[str] = []
    for k in scaler_keys:
        cov = feature_coverage.get(k, {})
        c = cov.get("coverage")
        if isinstance(c, (int, float)) and float(c) >= float(min_coverage):
            candidates.append(k)

    def _sort_key(k: str):
        cov = feature_coverage.get(k, {})
        coverage = float(cov.get("coverage", 0.0))
        present = int(cov.get("present_count", 0))
        return (-coverage, -present, k)

    candidates = sorted(set(candidates), key=_sort_key)
    return candidates[:max_features]


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

    if not (0.0 <= args.recommend_min_coverage <= 1.0):
        print(f"invalid --recommend-min-coverage: {args.recommend_min_coverage}", file=sys.stderr)
        return 1

    if args.recommend_max_features <= 0:
        print(f"invalid --recommend-max-features: {args.recommend_max_features}", file=sys.stderr)
        return 1

    feature_allowlist = _parse_feature_allowlist(args.feature_allowlist)
    allowset = set(feature_allowlist)

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

    # Coverage keys:
    # - if allowlist provided -> report coverage for allowlist keys (even if absent)
    # - else -> report coverage for observed keys
    restrict_coverage_keys: Optional[List[str]] = None
    if allowset:
        restrict_coverage_keys = sorted(allowset)

    feature_coverage = _build_feature_coverage(
        snapshot_event_count=snapshot_event_count,
        feature_values=feature_values,
        feature_present_counts=feature_present_counts,
        restrict_keys=restrict_coverage_keys,
    )

    print(f"Loaded {len(entries)} log entries from {log_path}")
    print(f"Gates with numeric E: {len(by_gate)}")
    if snapshot_event_count > 0:
        print(f"Entries with snapshot_current: {snapshot_event_count}")
    if feature_allowlist:
        print(f"Feature allowlist enabled: {len(feature_allowlist)} key(s)")
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
    fitted_scaler_keys: List[str] = []

    if snapshot_event_count >= args.min_samples and feature_values:
        scalers: Dict[str, RobustScaler] = {}

        for key in sorted(feature_values.keys()):
            if allowset and key not in allowset:
                continue
            vals = feature_values[key]
            if len(vals) < args.min_samples:
                continue
            try:
                scalers[key] = RobustScaler.fit(vals)
            except ValueError:
                continue

        if scalers:
            fitted_scaler_keys = sorted(scalers.keys())

            missing: Dict[str, int] = {}
            for key in fitted_scaler_keys:
                missing[key] = int(snapshot_event_count - feature_present_counts.get(key, 0))

            artifact = FeatureScalersArtifactV0(
                count=int(snapshot_event_count),
                missing=missing,
                features=scalers,
            )
            feature_scalers_payload = artifact.to_dict()

    # Recommended features are derived from (fitted scalers) ∩ (coverage threshold).
    recommended_features: List[str] = []
    if snapshot_event_count > 0 and fitted_scaler_keys and feature_coverage:
        recommended_features = _select_recommended_features(
            feature_coverage=feature_coverage,
            scaler_keys=fitted_scaler_keys,
            min_coverage=float(args.recommend_min_coverage),
            max_features=int(args.recommend_max_features),
        )

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

        # Additive: persist allowlist if provided.
        if feature_allowlist:
            payload["feature_allowlist"] = feature_allowlist

        # Additive: feature coverage + recommendation knobs (only if snapshots exist)
        if snapshot_event_count > 0:
            payload["feature_coverage"] = feature_coverage
            payload["recommendation"] = {
                "min_coverage": float(args.recommend_min_coverage),
                "max_features": int(args.recommend_max_features),
            }
            payload["recommended_features"] = recommended_features

        # Additive: only include feature_scalers if computed.
        if feature_scalers_payload:
            payload["feature_scalers"] = feature_scalers_payload

        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        with args.out_json.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)

        print()
        print(f"Wrote JSON suggestions to {args.out_json}")

        if snapshot_event_count > 0:
            print(
                f"Computed feature_coverage for {len(feature_coverage)} feature(s) "
                f"(snapshot_event_count={snapshot_event_count})"
            )
            print(
                f"Recommended_features: {len(recommended_features)} "
                f"(min_coverage={args.recommend_min_coverage:.2f}, max={args.recommend_max_features})"
            )

        if feature_allowlist:
            print(f"Included feature_allowlist with {len(feature_allowlist)} key(s)")

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
