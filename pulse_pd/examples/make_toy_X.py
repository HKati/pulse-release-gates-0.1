"""
Generate a synthetic feature matrix X for testing the cut-based PD runner.

Outputs a .npz containing:
- X (n, 2)
- feature_names (["x1", "x2"])
- y (optional labels for sanity checks; not required by the runner)
- run, lumi, event (HEP-style identifiers)
- event_id (string identifier "run:lumi:event")
- weight (optional event weights)

Run:
  python pulse_pd/examples/make_toy_X.py --out pulse_pd/examples/X_toy.npz --n 5000 --seed 0

Or as a module:
  python -m pulse_pd.examples.make_toy_X --out pulse_pd/examples/X_toy.npz --n 5000 --seed 0
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


def make_event_ids(n: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Deterministic, HEP-like identifiers:
    - run: constant per file (derived from seed)
    - lumi: increments in blocks
    - event: strictly increasing unique id
    - event_id: "run:lumi:event" as string
    """
    # Keep deterministic but "HEP-looking"
    run_number = 320000 + (seed % 1000)
    run = np.full(n, run_number, dtype=np.int64)

    # lumi sections: 1..ceil(n/250)
    block = 250
    lumi = (np.arange(n, dtype=np.int64) // block) + 1

    # event numbers: unique increasing
    event = np.arange(n, dtype=np.int64) + 1

    event_id = np.array([f"{run_number}:{int(l)}:{int(e)}" for l, e in zip(lumi, event)], dtype=object)
    return run, lumi, event, event_id


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="pulse_pd/examples/X_toy.npz", help="Output .npz path")
    ap.add_argument("--n", type=int, default=5000, help="Number of samples")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed")
    args = ap.parse_args()

    X, y = make_synthetic_data(args.n, args.seed)
    feature_names = np.array(["x1", "x2"], dtype=object)

    run, lumi, event, event_id = make_event_ids(args.n, args.seed)

    rng = np.random.default_rng(args.seed)
    # Optional weights: close to 1.0, deterministic by seed
    weight = rng.uniform(0.8, 1.2, size=args.n).astype(float)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    np.savez(
        args.out,
        X=X,
        y=y,
        feature_names=feature_names,
        run=run,
        lumi=lumi,
        event=event,
        event_id=event_id,
        weight=weight,
    )

    print("Wrote:", os.path.abspath(args.out))
    print("Keys: X, y, feature_names, run, lumi, event, event_id, weight")
    print(" - X:", X.shape)
    print(" - y:", y.shape)
    print(" - feature_names:", feature_names.tolist())
    print(" - run/lumi/event:", run.shape, lumi.shape, event.shape)
    print(" - event_id:", event_id.shape)
    print(" - weight:", weight.shape)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
