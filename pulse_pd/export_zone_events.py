"""
Export per-zone top Paradox Index (PI) events to CSV (traceback-ready).

Inputs:
- X: .npz / .npy / .csv
- theta: .json / .yaml (YAML optional via PyYAML)
- zones: pd_zones_v0.jsonl (one JSON object per line)

Output:
- CSV with columns:
  - zone_rank, zone_id, x_dim, y_dim, x_min, x_max, y_min, y_max, zone_count
  - idx
  - optional meta columns if present in NPZ: event_id, run, lumi, event, weight
    (if event_id is missing but run/lumi/event are present, event_id is generated as "run:lumi:event")
  - pi_raw, pi_norm, ds, mi, gf
  - (optional) feature columns

Example:
  python -m pulse_pd.export_zone_events \
    --x pulse_pd/examples/X_toy_ci.npz \
    --theta pulse_pd/examples/theta_cuts_example.json \
    --zones pulse_pd/artifacts_ci/pd_zones_v0.jsonl \
    --out pulse_pd/artifacts_ci/pd_zone_events_v0.csv \
    --topn-per-zone 20 \
    --sort-by pi_norm
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from pulse_pd.cut_adapter import run_pd_from_cuts
from pulse_pd.pd import compute_pi


def _looks_like_header(line: str) -> bool:
    toks = [t.strip() for t in line.strip().split(",") if t.strip()]
    if not toks:
        return False
    for t in toks:
        try:
            float(t)
        except Exception:
            return True
    return False


def load_theta(path: str) -> Dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "PyYAML is required to load YAML theta files. Install with: pip install pyyaml"
            ) from e
        with open(path, "r", encoding="utf-8") as f:
            obj = yaml.safe_load(f)
        if not isinstance(obj, dict):
            raise ValueError("theta file must parse to a dict")
        return obj

    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError("theta JSON must be an object/dict")
    return obj


def load_X(
    path: str, x_key: Optional[str] = None
) -> Tuple[np.ndarray, Optional[List[str]], Dict[str, np.ndarray]]:
    """
    Load X from .npz / .npy / .csv.
    Returns (X, feature_names or None, meta dict).

    meta dict is populated only for NPZ, and may include:
    - event_id
    - run, lumi, event
    - weight
    """
    ext = os.path.splitext(path)[1].lower()
    meta: Dict[str, np.ndarray] = {}

    if ext == ".npz":
        with np.load(path, allow_pickle=True) as z:
            keys = list(z.keys())

            if x_key is not None:
                if x_key in z:
                    X = np.asarray(z[x_key], dtype=float)
                else:
                    raise ValueError(
                        f"--x-key '{x_key}' not found in NPZ: {path}. "
                        f"Available keys: {sorted(keys)}"
                    )
            else:
                if "X" in z:
                    X = np.asarray(z["X"], dtype=float)
                else:
                    if not keys:
                        raise ValueError("Empty .npz file")
                    X = np.asarray(z[keys[0]], dtype=float)

            feature_names = None
            if "feature_names" in z:
                try:
                    fn = z["feature_names"]
                    if isinstance(fn, np.ndarray):
                        feature_names = [str(v) for v in fn.tolist()]
                except Exception:
                    feature_names = None

            n = int(X.shape[0]) if X.ndim >= 1 else 0
            for k in ("event_id", "run", "lumi", "event", "weight"):
                if k in z:
                    arr = np.asarray(z[k])
                    if arr.ndim == 1 and arr.shape[0] == n:
                        meta[k] = arr

        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D; got {X.shape}")
        return X, feature_names, meta

    if ext == ".npy":
        X = np.asarray(np.load(path, allow_pickle=False), dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D; got {X.shape}")
        return X, None, meta

    if ext == ".csv":
        # Numeric-only CSV expected.
        with open(path, "r", encoding="utf-8") as f:
            first = f.readline()
        has_header = _looks_like_header(first)

        if has_header:
            names = [t.strip() for t in first.strip().split(",")]
            X = np.loadtxt(path, delimiter=",", skiprows=1)
            feature_names = names
        else:
            X = np.loadtxt(path, delimiter=",")
            feature_names = None

        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D; got {X.shape}")
        return X, feature_names, meta

    raise ValueError(f"Unsupported X file extension '{ext}'. Use .npz / .npy / .csv")


def default_feature_names(d: int) -> List[str]:
    return [f"x{j}" for j in range(d)]


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _format_meta_value(v: Any) -> Any:
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="replace")
    return v


def _backfill_event_id(meta: Dict[str, np.ndarray], n: int) -> None:
    if "event_id" in meta and meta["event_id"].ndim == 1 and meta["event_id"].shape[0] == n:
        return
    have_triplet = all(
        k in meta and meta[k].ndim == 1 and meta[k].shape[0] == n for k in ("run", "lumi", "event")
    )
    if not have_triplet:
        return

    run = meta["run"]
    lumi = meta["lumi"]
    event = meta["event"]
    meta["event_id"] = np.asarray(
        [f"{int(r)}:{int(l)}:{int(e)}" for r, l, e in zip(run, lumi, event)],
        dtype=str,
    )


def choose_score(
    name: str,
    pi_raw: np.ndarray,
    pi_norm: np.ndarray,
    ds: np.ndarray,
    mi: np.ndarray,
    gf: np.ndarray,
) -> np.ndarray:
    name = name.strip().lower()
    if name == "pi_raw":
        return pi_raw
    if name == "pi_norm":
        return pi_norm
    if name == "gf":
        return gf
    if name == "mi":
        return mi
    if name == "1-ds":
        return 1.0 - ds
    raise ValueError("Unknown --sort-by. Use one of: pi_raw, pi_norm, gf, mi, 1-ds")


def _top_indices_subset(indices: np.ndarray, score: np.ndarray, topn: int) -> np.ndarray:
    indices = np.asarray(indices, dtype=int)
    m = int(indices.shape[0])
    if m == 0:
        return indices

    topn = max(1, min(int(topn), m))

    s = np.asarray(score[indices], dtype=float).copy()
    s[~np.isfinite(s)] = -np.inf

    if topn == m:
        order = np.argsort(-s)
        return indices[order]

    part = np.argpartition(-s, topn - 1)[:topn]
    order = part[np.argsort(-s[part])]
    return indices[order]


def _read_zones_jsonl(path: str) -> List[Dict[str, Any]]:
    zones: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if not isinstance(obj, dict):
                raise ValueError(f"Zone line {ln} is not a JSON object")
            zones.append(obj)

    # Stable order: prefer explicit rank, else keep file order.
    def _rank_key(z: Dict[str, Any], i: int) -> Tuple[int, int]:
        r = z.get("rank")
        try:
            rr = int(r)
        except Exception:
            rr = 10**9
        return (rr, i)

    zones_sorted = sorted(list(enumerate(zones)), key=lambda t: _rank_key(t[1], t[0]))
    return [z for _, z in zones_sorted]


def _parse_zone(z: Dict[str, Any]) -> Tuple[int, str, int, int, float, float, float, float]:
    # returns: (rank, zone_id, jx, jy, x0, x1, y0, y1)
    if "zone_id" not in z:
        raise ValueError(f"Zone missing 'zone_id': keys={sorted(z.keys())}")
    zone_id = str(z["zone_id"])

    rank = z.get("rank", None)
    try:
        rank_i = int(rank) if rank is not None else 0
    except Exception:
        rank_i = 0

    dims = z.get("dims", {}) or {}
    if not isinstance(dims, dict):
        raise ValueError(f"Zone dims must be object: zone_id={zone_id}")
    if "x" not in dims or "y" not in dims:
        raise ValueError(f"Zone dims missing x/y: zone_id={zone_id}")
    jx = int(dims["x"])
    jy = int(dims["y"])

    ranges = z.get("ranges", {}) or {}
    if not isinstance(ranges, dict):
        raise ValueError(f"Zone ranges must be object: zone_id={zone_id}")
    if "x" not in ranges or "y" not in ranges:
        raise ValueError(f"Zone ranges missing x/y: zone_id={zone_id}")

    xr = ranges["x"]
    yr = ranges["y"]
    if not (isinstance(xr, (list, tuple)) and len(xr) == 2):
        raise ValueError(f"Zone x range invalid: zone_id={zone_id}")
    if not (isinstance(yr, (list, tuple)) and len(yr) == 2):
        raise ValueError(f"Zone y range invalid: zone_id={zone_id}")

    x0, x1 = float(xr[0]), float(xr[1])
    y0, y1 = float(yr[0]), float(yr[1])

    # normalize ordering
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0

    return rank_i, zone_id, jx, jy, x0, x1, y0, y1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", required=True, help="Path to X (.npz/.npy/.csv)")
    ap.add_argument("--x-key", default=None, help="Key name for X inside .npz (optional)")
    ap.add_argument("--theta", required=True, help="Path to theta config (.json/.yaml)")
    ap.add_argument("--zones", required=True, help="Path to pd_zones_v0.jsonl")
    ap.add_argument("--out", required=True, help="Output CSV path")

    ap.add_argument("--topn-per-zone", type=int, default=20, help="Top events per zone to export")
    ap.add_argument("--max-zones", type=int, default=None, help="Optional limit on number of zones")
    ap.add_argument("--sort-by", default="pi_norm", help="Ranking score: pi_raw/pi_norm/gf/mi/1-ds")
    ap.add_argument("--no-features", action="store_true", help="Do not include raw feature columns in CSV")

    ap.add_argument("--ds-M", type=int, default=24, help="DS perturbation samples")
    ap.add_argument("--mi-models", type=int, default=7, help="Theta-ensemble size for MI")
    ap.add_argument("--mi-sigma", type=float, default=None, help="Sigma override for MI theta jitter (optional)")
    ap.add_argument("--gf-method", default="spsa", choices=["spsa", "finite_diff"], help="GF method")
    ap.add_argument("--gf-K", type=int, default=8, help="GF SPSA directions (if spsa)")
    ap.add_argument("--gf-delta", type=float, default=0.05, help="GF delta step size")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed")

    args = ap.parse_args()

    X, fnames, meta = load_X(args.x, x_key=args.x_key)
    theta = load_theta(args.theta)

    n, d = X.shape
    if fnames is None or len(fnames) != d:
        fnames = default_feature_names(d)

    # Ensure traceback-ready event_id if possible
    _backfill_event_id(meta, n)

    # Compute PD metrics
    res = run_pd_from_cuts(
        X,
        theta,
        feature_names=fnames,
        ds_M=args.ds_M,
        mi_models=args.mi_models,
        mi_sigma=args.mi_sigma,
        gf_method=args.gf_method,
        gf_K=args.gf_K,
        gf_delta=args.gf_delta,
        seed=args.seed,
        normalize_pi=True,
    )

    ds = res["ds"]
    mi = res["mi"]
    gf = res["gf"]

    pi_raw = compute_pi(ds=ds, mi=mi, gf=gf, normalize=False)
    pi_norm = compute_pi(ds=ds, mi=mi, gf=gf, normalize=True)

    score = choose_score(args.sort_by, pi_raw, pi_norm, ds, mi, gf)

    zones_raw = _read_zones_jsonl(args.zones)
    if args.max_zones is not None:
        zones_raw = zones_raw[: max(0, int(args.max_zones))]

    # Determine meta columns to export
    meta_cols: List[str] = []
    for k in ("event_id", "run", "lumi", "event", "weight"):
        if k in meta and meta[k].ndim == 1 and meta[k].shape[0] == n:
            meta_cols.append(k)

    base_cols = [
        "zone_rank",
        "zone_id",
        "x_dim",
        "y_dim",
        "x_min",
        "x_max",
        "y_min",
        "y_max",
        "zone_count",
        "idx",
    ]
    metric_cols = ["pi_raw", "pi_norm", "ds", "mi", "gf"]
    feature_cols = [] if args.no_features else list(fnames)

    header = base_cols + meta_cols + metric_cols + feature_cols

    ensure_parent_dir(args.out)

    total_rows = 0
    zones_with_rows = 0

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)

        for z in zones_raw:
            rank, zone_id, jx, jy, x0, x1, y0, y1 = _parse_zone(z)

            if jx < 0 or jx >= d or jy < 0 or jy >= d:
                raise ValueError(
                    f"Zone dims out of range for d={d}: zone_id={zone_id} dims=({jx},{jy})"
                )

            # Filter events inside zone (half-open interval to match histogram binning)
            xv = X[:, jx]
            yv = X[:, jy]
            mask = (xv >= x0) & (xv < x1) & (yv >= y0) & (yv < y1)
            idx_in_zone = np.where(mask)[0]
            zone_count = int(idx_in_zone.shape[0])
            if zone_count == 0:
                continue

            chosen = _top_indices_subset(idx_in_zone, score, args.topn_per_zone)
            if chosen.shape[0] == 0:
                continue

            zones_with_rows += 1

            for i in chosen:
                row_base = [
                    int(rank),
                    str(zone_id),
                    int(jx),
                    int(jy),
                    float(x0),
                    float(x1),
                    float(y0),
                    float(y1),
                    int(zone_count),
                    int(i),
                ]

                meta_vals = [_format_meta_value(meta[k][i]) for k in meta_cols]

                row_metrics = [
                    float(pi_raw[i]),
                    float(pi_norm[i]),
                    float(ds[i]),
                    float(mi[i]),
                    float(gf[i]),
                ]

                if args.no_features:
                    row_feats: List[Any] = []
                else:
                    row_feats = [float(v) for v in X[i, :].tolist()]

                w.writerow(row_base + meta_vals + row_metrics + row_feats)
                total_rows += 1

    print("Wrote:", os.path.abspath(args.out))
    print(f"Zones: {len(zones_raw)}  zones_with_rows={zones_with_rows}")
    print(f"Rows: {total_rows}  (topn_per_zone={args.topn_per_zone}, sort_by={args.sort_by})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
