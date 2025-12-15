"""
Generate a synthetic feature matrix X for testing the cut-based PD runner.

Outputs a .npz containing:
- X (n, 2)
- feature_names (["x1", "x2"])
- y (optional labels for sanity checks; not required by the runner)

Run:
  python pulse_pd/examples/make_toy_X.py --out pulse_pd/examples/X_toy.npz --n 5000 --seed 0
"""

from __future__ import annotations

import argparse
import os
import numpy as np


def make_synthetic_data(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Mixture of two Gaussians (background + signal-like cluster).
    Returns X (n,2) and y (n,) in {0,1}.
    """
    rng = np.random.default_rng(seed)

    n_sig = n // 2
    n_bkg = n - n_sig

    mu_b = np.array([-1.0, -0.5], dtype=float)
    cov_b = np.array([[1.0, 0.2], [0.2, 0.8]], dtype=float)

    mu_s = np.array([1.2, 0.8], dtype=float)
    cov_s = np.array([[0.9, -0.15], [-0.15, 0.9]], dtype=float)

    Xb = rng.multivariate_normal(mu_b, cov_b, size=n_bkg)
    Xs = rng.multivariate_normal(mu_s, cov_s, size=n_sig)

    X = np.vstack([Xb, Xs])
    y = np.concatenate([np.zeros(n_bkg, dtype=int), np.ones(n_sig, dtype=int)])

    idx = rng.permutation(n)
    return X[idx], y[idx]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="pulse_pd/examples/X_toy.npz", help="Output .npz path")
    ap.add_argument("--n", type=int, default=5000, help="Number of samples")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed")
    args = ap.parse_args()

    X, y = make_synthetic_data(args.n, args.seed)
    feature_names = np.array(["x1", "x2"], dtype=object)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    np.savez(args.out, X=X, y=y, feature_names=feature_names)

    print("Wrote:", os.path.abspath(args.out))
    print(" - X:", X.shape)
    print(" - y:", y.shape)
    print(" - feature_names:", feature_names.tolist())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
