"""
PULSE–PD v0 toy demo.

Generates a synthetic 2D dataset, defines a small ensemble of simple logistic
"models" to produce:
- DS (Decision Stability) w.r.t. threshold perturbations
- MI (Model Inconsistency) across an ensemble
- GF (Gate Friction) via SPSA gradient-norm estimate
- PI (Paradox Index)

Outputs:
- paradox_scatter.png  (DS vs MI, colored by PI)
- pi_heatmap.png       (mean PI over feature space bins)
- toy_summary.json     (basic summary stats)

Run:
  python pulse_pd/demo_toy.py --out pulse_pd/artifacts --n 5000 --seed 0
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np

# Matplotlib is only used here (not required by pd.py).
try:
    import matplotlib.pyplot as plt
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "matplotlib is required for this demo. Install it with: pip install matplotlib"
    ) from e

from pulse_pd.pd import compute_ds, compute_mi, compute_gf, compute_pi


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


@dataclass(frozen=True)
class LogisticModel:
    w: np.ndarray  # shape (d,)
    b: float = 0.0

    def prob(self, X: np.ndarray, theta: Any = None) -> np.ndarray:
        z = X @ self.w + self.b
        return sigmoid(z)


def make_synthetic_data(n: int, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create a mixture of two Gaussians (signal/background).
    Returns X (n,2) and y (n,) in {0,1}.
    """
    rng = np.random.default_rng(seed)

    n_sig = n // 2
    n_bkg = n - n_sig

    # Background cluster
    mu_b = np.array([-1.0, -0.5], dtype=float)
    cov_b = np.array([[1.0, 0.2], [0.2, 0.8]], dtype=float)

    # Signal cluster (slightly offset)
    mu_s = np.array([1.2, 0.8], dtype=float)
    cov_s = np.array([[0.9, -0.15], [-0.15, 0.9]], dtype=float)

    Xb = rng.multivariate_normal(mu_b, cov_b, size=n_bkg)
    Xs = rng.multivariate_normal(mu_s, cov_s, size=n_sig)

    X = np.vstack([Xb, Xs])
    y = np.concatenate([np.zeros(n_bkg, dtype=int), np.ones(n_sig, dtype=int)])

    # Shuffle
    idx = rng.permutation(n)
    return X[idx], y[idx]


def make_model_ensemble(seed: int) -> List[LogisticModel]:
    """
    Create a small ensemble with slightly different weights/biases.
    This produces MI signal (disagreement) near boundaries.
    """
    rng = np.random.default_rng(seed)

    base_w = np.array([1.25, 0.85], dtype=float)
    base_b = -0.10

    models: List[LogisticModel] = []
    for _ in range(5):
        w = base_w + rng.normal(0.0, 0.18, size=base_w.shape)
        b = base_b + float(rng.normal(0.0, 0.12))
        models.append(LogisticModel(w=w, b=b))
    return models


def decision_from_prob(prob_fn, tau: float):
    def _dec(X: np.ndarray, theta: Dict[str, Any]) -> np.ndarray:
        # theta contains tau; tau argument is used only as fallback
        t = float(theta.get("tau", tau)) if isinstance(theta, dict) else float(tau)
        p = prob_fn(X, theta)
        return (p > t).astype(int)

    return _dec


def eps_sampler_threshold(theta: Dict[str, Any], rng: np.random.Generator) -> Dict[str, Any]:
    """
    Perturb only the decision threshold tau.
    """
    tau0 = float(theta["tau"])
    # Small perturbation scale: v0 default
    tau_p = float(np.clip(tau0 + rng.normal(0.0, 0.02), 0.05, 0.95))
    return {**theta, "tau": tau_p}


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def paradox_scatter_plot(ds: np.ndarray, mi: np.ndarray, pi: np.ndarray, out_path: str) -> None:
    plt.figure()
    sc = plt.scatter(ds, mi, c=pi, s=10)
    plt.xlabel("DS (Decision Stability)")
    plt.ylabel("MI (Model Inconsistency)")
    plt.title("PULSE–PD v0: Paradoxon Diagram (toy)")
    plt.colorbar(sc, label="PI (normalized)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def pi_heatmap_plot(X: np.ndarray, pi: np.ndarray, out_path: str, bins: int = 60) -> None:
    """
    Mean PI over 2D feature space bins using histogram2d with weights.
    """
    x1 = X[:, 0]
    x2 = X[:, 1]

    # Bin edges
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
    # Note: histogram2d returns [xbin, ybin] grid; transpose for imshow orientation
    plt.imshow(
        H_mean.T,
        origin="lower",
        extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
        aspect="auto",
    )
    plt.xlabel("x1")
    plt.ylabel("x2")
    plt.title("PULSE–PD v0: Mean PI heatmap (toy)")
    plt.colorbar(label="Mean PI (normalized)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="pulse_pd/artifacts", help="Output directory for artifacts")
    ap.add_argument("--n", type=int, default=5000, help="Number of samples")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed")
    ap.add_argument("--tau", type=float, default=0.5, help="Decision threshold")
    ap.add_argument("--ds_M", type=int, default=24, help="Number of theta perturbations for DS")
    ap.add_argument("--gf_K", type=int, default=8, help="Number of SPSA directions for GF")
    ap.add_argument("--gf_delta", type=float, default=0.05, help="SPSA step size for GF")
    args = ap.parse_args()

    ensure_dir(args.out)

    # 1) Data
    X, y = make_synthetic_data(args.n, args.seed)

    # 2) Models (ensemble)
    models = make_model_ensemble(args.seed + 123)

    # 3) Define prob/decision for DS and GF using the first model as "baseline"
    base_model = models[0]

    def base_prob(X_: np.ndarray, theta: Any) -> np.ndarray:
        return base_model.prob(X_, theta)

    decision_fn = decision_from_prob(base_prob, tau=args.tau)

    theta = {"tau": float(args.tau)}

    # 4) DS
    ds = compute_ds(
        decision_fn=decision_fn,
        X=X,
        theta=theta,
        eps_sampler=eps_sampler_threshold,
        M=args.ds_M,
        seed=args.seed,
    )

    # 5) MI (variance across model probabilities)
    prob_fn_list = [(lambda m: (lambda X_, th: m.prob(X_, th)))(m) for m in models]
    mi = compute_mi(prob_fn_list=prob_fn_list, X=X, theta=None)

    # 6) GF (SPSA estimate of gradient norm)
    gf = compute_gf(
        prob_fn=base_prob,
        X=X,
        theta=None,
        method="spsa",
        K=args.gf_K,
        delta=args.gf_delta,
        seed=args.seed,
        clip_prob=True,
    )

    # 7) PI
    pi = compute_pi(ds=ds, mi=mi, gf=gf, normalize=True)

    # 8) Save artifacts
    paradox_scatter_plot(ds, mi, pi, os.path.join(args.out, "paradox_scatter.png"))
    pi_heatmap_plot(X, pi, os.path.join(args.out, "pi_heatmap.png"), bins=60)

    summary = {
        "n": int(X.shape[0]),
        "seed": int(args.seed),
        "theta": theta,
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
        "artifacts": {
            "paradox_scatter": "paradox_scatter.png",
            "pi_heatmap": "pi_heatmap.png",
            "summary": "toy_summary.json",
        },
    }
    save_json(os.path.join(args.out, "toy_summary.json"), summary)

    print("Wrote artifacts to:", os.path.abspath(args.out))
    print(" - paradox_scatter.png")
    print(" - pi_heatmap.png")
    print(" - toy_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
