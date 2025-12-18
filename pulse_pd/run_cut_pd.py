"""
Run PULSE–PD v0 (cut-based) on a saved feature matrix.

Inputs
------
- X: .npz / .npy / .csv
- theta: .json / .yaml (YAML requires PyYAML)

Outputs (in --out directory)
----------------------------
- pd_scatter.png     (DS vs MI, colored by PI)
- pi_heatmap.png     (mean PI over 2 selected feature dimensions)
- pd_summary.json    (stats + top PI bins)
- pd_run_meta.json   (run metadata, schema-stable; inputs/params/artifacts/traceback fields)

Examples
--------
1) From numpy .npz:
  python pulse_pd/run_cut_pd.py \
    --x data/X.npz --x-key X \
    --theta pulse_pd/examples/theta_cuts_example.json \
    --dims 0 1 \
    --out pulse_pd/artifacts_run

2) From CSV (auto-detect header):
  python pulse_pd/run_cut_pd.py \
    --x data/features.csv \
    --theta pulse_pd/examples/theta_cuts_example.json \
    --dims 0 1 \
    --out pulse_pd/artifacts_run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import matplotlib.pyplot as plt
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "matplotlib is required for this runner. Install it with: pip install matplotlib"
    ) from e

from pulse_pd.cut_adapter import run_pd_from_cuts


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


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


def _looks_like_header(line: str) -> bool:
    toks = [t.strip() for t in line.strip().split(",") if t.strip()]
    if not toks:
        return False
    # If any token cannot be parsed as float, treat as header
    for t in toks:
        try:
            float(t)
        except Exception:
            return True
    return False


def load_X(path: str, x_key: Optional[str] = None) -> Tuple[np.ndarray, Optional[List[str]]]:
    """
    Load X from .npz / .npy / .csv.
    Returns (X, feature_names or None).
    """
    ext = os.path.splitext(path)[1].lower()

    if ext == ".npz":
        with np.load(path, allow_pickle=True) as z:
            keys = list(z.keys())
            if x_key and x_key in z:
                X = np.asarray(z[x_key], dtype=float)
            else:
                # Prefer "X" if present; else take first array
                if "X" in z:
                    X = np.asarray(z["X"], dtype=float)
                else:
                    if not keys:
                        raise ValueError("Empty .npz file")
                    X = np.asarray(z[keys[0]], dtype=float)

            feature_names = None
            # Optional: if feature_names stored in npz
            if "feature_names" in z:
                try:
                    fn = z["feature_names"]
                    if isinstance(fn, np.ndarray):
                        fn_list = [str(x) for x in fn.tolist()]
                        feature_names = fn_list
                except Exception:
                    feature_names = None

        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D; got {X.shape}")
        return X, feature_names

    if ext == ".npy":
        X = np.asarray(np.load(path, allow_pickle=False), dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D; got {X.shape}")
        return X, None

    if ext == ".csv":
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
        return X, feature_names

    raise ValueError(f"Unsupported X file extension '{ext}'. Use .npz / .npy / .csv")


def resolve_dim_index(
    dim: str, feature_names: Optional[List[str]], theta: Dict[str, Any], d: int
) -> int:
    """
    Resolve a dim selector to an integer column index.
    Accepts:
    - integer strings: "0"
    - feature names if feature_names is available (from CSV header or npz)
    - names via theta["feature_names"] if present
    """
    # 1) integer
    if dim.isdigit():
        j = int(dim)
        if j < 0 or j >= d:
            raise ValueError(f"Dim index out of range: {j} for d={d}")
        return j

    # 2) from loaded feature_names (CSV header or npz)
    if feature_names is not None and dim in feature_names:
        return int(feature_names.index(dim))

    # 3) from theta feature_names mapping/list
    fn = theta.get("feature_names", None)
    if isinstance(fn, dict) and dim in fn:
        j = int(fn[dim])
        if j < 0 or j >= d:
            raise ValueError(f"Dim '{dim}' maps to out-of-range index {j} for d={d}")
        return j
    if isinstance(fn, (list, tuple)) and dim in fn:
        j = int(list(fn).index(dim))
        if j < 0 or j >= d:
            raise ValueError(f"Dim '{dim}' maps to out-of-range index {j} for d={d}")
        return j

    raise ValueError(
        f"Cannot resolve dim '{dim}'. Use an integer index or provide feature names."
    )


def save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def plot_pd_scatter(ds: np.ndarray, mi: np.ndarray, pi: np.ndarray, out_path: str) -> None:
    plt.figure()
    sc = plt.scatter(ds, mi, c=pi, s=10)
    plt.xlabel("DS (Decision Stability)")
    plt.ylabel("MI (Model Inconsistency)")
    plt.title("PULSE–PD: Paradoxon Diagram (cut-based)")
    plt.colorbar(sc, label="PI (normalized)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_pi_heatmap(
    X: np.ndarray,
    pi: np.ndarray,
    jx: int,
    jy: int,
    out_path: str,
    bins: int = 60,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns (H_mean, xedges, yedges, H_cnt) for summary extraction.
    """
    x1 = X[:, jx]
    x2 = X[:, jy]

    x1_min, x1_max = np.percentile(x1, [1, 99])
    x2_min, x2_max = np.percentile(x2, [1, 99])

    H_sum, xedges, yedges = np.histogram2d(
        x1, x2, bins=bins, range=[[x1_min, x1_max], [x2_min, x2_max]], weights=pi
    )
    H_cnt, _, _ = np.histogram2d(
        x1, x2, bins=bins, range=[[x1_min, x1_max], [x2_min, x2_max]]
    )

    with np.errstate(invalid="ignore", divide="ignore"):
        H_mean = H_sum / H_cnt
    H_mean = np.nan_to_num(H_mean, nan=0.0, posinf=0.0, neginf=0.0)

    plt.figure()
    plt.imshow(
        H_mean.T,
        origin="lower",
        extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
        aspect="auto",
    )
    plt.xlabel(f"x[{jx}]")
    plt.ylabel(f"x[{jy}]")
    plt.title("PULSE–PD: Mean PI heatmap (cut-based)")
    plt.colorbar(label="Mean PI (normalized)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()

    return H_mean, xedges, yedges, H_cnt


def top_pi_bins(
    H_mean: np.ndarray,
    H_cnt: np.ndarray,
    xedges: np.ndarray,
    yedges: np.ndarray,
    topk: int = 10,
    min_count: int = 10,
) -> List[Dict[str, Any]]:
    """
    Extract top-K bins by mean PI, with a minimum event count per bin.
    Returns a list of dicts with bin ranges and stats.
    """
    bins_x = H_mean.shape[0]
    bins_y = H_mean.shape[1]

    candidates: List[Tuple[float, int, int]] = []
    for ix in range(bins_x):
        for iy in range(bins_y):
            c = int(H_cnt[ix, iy])
            if c < min_count:
                continue
            candidates.append((float(H_mean[ix, iy]), ix, iy))

    candidates.sort(key=lambda t: t[0], reverse=True)
    out: List[Dict[str, Any]] = []
    for val, ix, iy in candidates[:topk]:
        out.append(
            {
                "mean_pi": float(val),
                "count": int(H_cnt[ix, iy]),
                "x_bin": int(ix),
                "y_bin": int(iy),
                "x_range": [float(xedges[ix]), float(xedges[ix + 1])],
                "y_range": [float(yedges[iy]), float(yedges[iy + 1])],
            }
        )
    return out


def _pd_jsonable(x: Any) -> Any:
    # convert numpy scalars / Path to json-friendly values
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, np.generic):
        return x.item()
    return x


def _default_feature_names(d: int) -> List[str]:
    return [f"x{j}" for j in range(d)]


def _traceback_fields_present_npz(x_path: str, n: int) -> Dict[str, bool]:
    fields = {k: False for k in ("event_id", "run", "lumi", "event", "weight")}
    if not str(x_path).lower().endswith(".npz"):
        return fields
    try:
        with np.load(x_path, allow_pickle=True) as z:
            for k in list(fields.keys()):
                if k not in z:
                    continue
                arr = np.asarray(z[k])
                if arr.ndim == 1 and int(arr.shape[0]) == int(n):
                    fields[k] = True
    except Exception:
        # Never crash the runner because of meta inspection.
        return fields
    return fields


def write_pd_run_meta(
    *,
    out_dir: str,
    args: argparse.Namespace,
    X: np.ndarray,
    feature_names: Optional[List[str]],
    jx: int,
    jy: int,
    artifacts: Dict[str, str],
) -> str:
    n, d = X.shape

    if feature_names is None or len(feature_names) != d:
        fnames = _default_feature_names(d)
        fnames_source = "generated"
    else:
        fnames = [str(v) for v in feature_names]
        fnames_source = "input"

    tb = _traceback_fields_present_npz(args.x, int(n))

    meta = {
        "schema": "pulse_pd/pd_run_meta_v0",
        "tool": "pulse_pd.run_cut_pd",
        "argv": [str(a) for a in list(sys.argv)],
        "inputs": {
            "x": str(args.x),
            "x_key": getattr(args, "x_key", None),
            "theta": str(args.theta),
            "dims_requested": [str(args.dims[0]), str(args.dims[1])],
            "out": str(args.out),
        },
        "resolved": {
            "dims": {"x": int(jx), "y": int(jy)},
            "dim_names": {"x": fnames[int(jx)], "y": fnames[int(jy)]},
        },
        "params": {
            "ds_M": int(args.ds_M),
            "mi_models": int(args.mi_models),
            "mi_sigma": None if args.mi_sigma is None else float(args.mi_sigma),
            "gf_method": str(args.gf_method),
            "gf_K": int(args.gf_K),
            "gf_delta": float(args.gf_delta),
            "bins": int(args.bins),
            "topk": int(args.topk),
            "min_count": int(args.min_count),
            "seed": int(args.seed),
        },
        "data": {
            "n": int(n),
            "d": int(d),
            "feature_names": fnames,
            "feature_names_source": fnames_source,
        },
        "traceback_fields_present": tb,
        "artifacts": dict(artifacts),
    }

    out_path = Path(out_dir) / "pd_run_meta.json"
    out_path.write_text(
        json.dumps(meta, indent=2, sort_keys=True, default=_pd_jsonable),
        encoding="utf-8",
    )
    return str(out_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", required=True, help="Path to X (.npz/.npy/.csv)")
    ap.add_argument("--x-key", default=None, help="Key name for X inside .npz (optional)")
    ap.add_argument("--theta", required=True, help="Path to theta config (.json/.yaml)")
    ap.add_argument("--dims", nargs=2, required=True, help="Two dims for heatmap: indices or names")
    ap.add_argument("--out", default="pulse_pd/artifacts_run", help="Output directory")

    ap.add_argument("--ds-M", type=int, default=24, help="DS perturbation samples")
    ap.add_argument("--mi-models", type=int, default=7, help="Number of theta-ensemble models for MI")
    ap.add_argument("--mi-sigma", type=float, default=None, help="Sigma override for theta jitter (optional)")

    ap.add_argument("--gf-method", default="spsa", choices=["spsa", "finite_diff"], help="GF method")
    ap.add_argument("--gf-K", type=int, default=8, help="GF SPSA directions (if spsa)")
    ap.add_argument("--gf-delta", type=float, default=0.05, help="GF delta step size")

    ap.add_argument("--bins", type=int, default=60, help="Heatmap bins per dimension")
    ap.add_argument("--topk", type=int, default=10, help="Top PI bins to report")
    ap.add_argument("--min-count", type=int, default=10, help="Min events per bin to consider in top bins")

    ap.add_argument("--seed", type=int, default=0, help="RNG seed")
    args = ap.parse_args()

    ensure_dir(args.out)

    X, feature_names = load_X(args.x, x_key=args.x_key)
    theta = load_theta(args.theta)

    n, d = X.shape
    jx = resolve_dim_index(str(args.dims[0]), feature_names, theta, d)
    jy = resolve_dim_index(str(args.dims[1]), feature_names, theta, d)

    # Run PD metrics from cut-based theta
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
    pi = res["pi"]

    # Artifacts
    scatter_path = os.path.join(args.out, "pd_scatter.png")
    heatmap_path = os.path.join(args.out, "pi_heatmap.png")
    summary_path = os.path.join(args.out, "pd_summary.json")

    plot_pd_scatter(ds, mi, pi, scatter_path)
    H_mean, xedges, yedges, H_cnt = plot_pi_heatmap(
        X, pi, jx, jy, heatmap_path, bins=args.bins
    )

    top_bins = top_pi_bins(
        H_mean, H_cnt, xedges, yedges, topk=args.topk, min_count=args.min_count
    )

    summary = {
        "input": {
            "x_path": os.path.abspath(args.x),
            "theta_path": os.path.abspath(args.theta),
            "n": int(n),
            "d": int(d),
            "dims": {"x": int(jx), "y": int(jy)},
            "feature_names_present": bool(feature_names is not None),
        },
        "params": {
            "ds_M": int(args.ds_M),
            "mi_models": int(args.mi_models),
            "mi_sigma": None if args.mi_sigma is None else float(args.mi_sigma),
            "gf_method": str(args.gf_method),
            "gf_K": int(args.gf_K),
            "gf_delta": float(args.gf_delta),
            "seed": int(args.seed),
            "bins": int(args.bins),
        },
        "stats": {
            "ds": {
                "mean": float(np.mean(ds)),
                "p05": float(np.percentile(ds, 5)),
                "p50": float(np.percentile(ds, 50)),
                "p95": float(np.percentile(ds, 95)),
            },
            "mi": {
                "mean": float(np.mean(mi)),
                "p05": float(np.percentile(mi, 5)),
                "p50": float(np.percentile(mi, 50)),
                "p95": float(np.percentile(mi, 95)),
            },
            "gf": {
                "mean": float(np.mean(gf)),
                "p05": float(np.percentile(gf, 5)),
                "p50": float(np.percentile(gf, 50)),
                "p95": float(np.percentile(gf, 95)),
            },
            "pi": {
                "mean": float(np.mean(pi)),
                "p90": float(np.percentile(pi, 90)),
                "p99": float(np.percentile(pi, 99)),
            },
        },
        "top_pi_bins": top_bins,
        "artifacts": {
            "pd_scatter": os.path.basename(scatter_path),
            "pi_heatmap": os.path.basename(heatmap_path),
            "summary": os.path.basename(summary_path),
            "pd_run_meta": "pd_run_meta.json",
        },
    }

    save_json(summary_path, summary)

    artifacts_meta = {
        "pd_scatter_png": os.path.basename(scatter_path),
        "pi_heatmap_png": os.path.basename(heatmap_path),
        "pd_summary_json": os.path.basename(summary_path),
        "pd_run_meta_json": "pd_run_meta.json",
    }
    meta_path = write_pd_run_meta(
        out_dir=str(args.out),
        args=args,
        X=X,
        feature_names=feature_names,
        jx=jx,
        jy=jy,
        artifacts=artifacts_meta,
    )

    print("PULSE–PD run complete. Artifacts written to:", os.path.abspath(args.out))
    print(" -", scatter_path)
    print(" -", heatmap_path)
    print(" -", summary_path)
    print(" -", meta_path)
    if top_bins:
        print("Top PI bin (mean_pi, count, x_range, y_range):")
        b0 = top_bins[0]
        print(
            f"  mean_pi={b0['mean_pi']:.4f}, count={b0['count']}, "
            f"x={b0['x_range']}, y={b0['y_range']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
