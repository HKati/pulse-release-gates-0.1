"""
Export top Paradox Index (PI) events to CSV for inspection.

This script is matplotlib-free (NumPy + stdlib only), so it works in minimal
environments and is Windows-friendly.

Inputs:
- X: .npz / .npy / .csv
- theta: .json / .yaml (YAML optional via PyYAML)

Outputs:
- CSV with columns:
  - idx
  - optional meta columns if present in NPZ: event_id, run, lumi, event, weight
  - pi_raw, pi_norm, ds, mi, gf
  - <feature columns>

Example:
  python -m pulse_pd.export_top_pi_events \
    --x pulse_pd/examples/X_toy.npz \
    --theta pulse_pd/examples/theta_cuts_example.json \
    --out pulse_pd/artifacts_run/top_pi_events.csv \
    --topn 200
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from typing import Any, Dict, List, Optional, Tuple

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


def load_X(path: str, x_key: Optional[str] = None) -> Tuple[np.ndarray, Optional[List[str]], Dict[str, np.ndarray]]:
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

            # Fail-fast: if --x-key is provided, it must exist.
            if x_key is not None:
                if x_key in z:
                    X = np.asarray(z[x_key], dtype=float)
                else:
                    raise ValueError(
                        f"--x-key '{x_key}' not found in NPZ: {path}. "
                        f"Available keys: {sorted(keys)}"
                    )
            else:
                # Prefer "X" if present; else take first array
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

            # Optional meta keys for traceback (only keep if length matches n)
            # NOTE: We cannot validate lengths until X is known.
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
        # numeric-only CSV expected
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


def top_indices(score: np.ndarray, topn: int) -> np.ndarray:
    n = score.shape[0]
    topn = max(1, min(int(topn), n))

    s = np.asarray(score, dtype=float).copy()
    s[~np.isfinite(s)] = -np.inf

    if topn == n:
        return np.argsort(-s)

    idx_part = np.argpartition(-s, topn - 1)[:topn]
    return idx_part[np.argsort(-s[idx_part])]


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _format_meta_value(v: Any) -> Any:
    # numpy scalar -> python scalar
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="replace")
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", required=True, help="Path to X (.npz/.npy/.csv)")
    ap.add_argument("--x-key", default=None, help="Key name for X inside .npz (optional)")
    ap.add_argument("--theta", required=True, help="Path to theta config (.json/.yaml)")
    ap.add_argument("--out", required=True, help="Output CSV path")

    ap.add_argument("--topn", type=int, default=200, help="Number of top events to export")
    ap.add_argument("--sort-by", default="pi_raw", help="Ranking score: pi_raw/pi_norm/gf/mi/1-ds")

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

    res = run_pd_from_cuts(
        X,
        theta,
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

    # Export both raw and normalized PI
    pi_raw = compute_pi(ds=ds, mi=mi, gf=gf, normalize=False)
    pi_norm = compute_pi(ds=ds, mi=mi, gf=gf, normalize=True)

    score = choose_score(args.sort_by, pi_raw, pi_norm, ds, mi, gf)
    idx = top_indices(score, args.topn)

    ensure_parent_dir(args.out)

    # Include meta cols if present (and length matches n)
    meta_cols: List[str] = []
    for k in ("event_id", "run", "lumi", "event", "weight"):
        if k in meta and meta[k].ndim == 1 and meta[k].shape[0] == n:
            meta_cols.append(k)

    header = ["idx"] + meta_cols + ["pi_raw", "pi_norm", "ds", "mi", "gf"] + fnames

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for i in idx:
            meta_vals = [_format_meta_value(meta[k][i]) for k in meta_cols]
            row = (
                [int(i)]
                + meta_vals
                + [
                    float(pi_raw[i]),
                    float(pi_norm[i]),
                    float(ds[i]),
                    float(mi[i]),
                    float(gf[i]),
                ]
                + [float(v) for v in X[i, :].tolist()]
            )
            w.writerow(row)

    print("Exported:", os.path.abspath(args.out))
    print(f"Rows: {len(idx)} / {n}  (sorted by {args.sort_by})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
