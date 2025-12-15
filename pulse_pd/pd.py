"""
PULSE–PD (Paradoxon Diagram) v0 core metrics.

This module implements three meta-metrics measured at the decision moment:
- DS: Decision Stability
- MI: Model Inconsistency
- GF: Gate Friction (decision boundary "tension")

And a derived Paradox Index:
- PI

Design goals:
- minimal dependencies (NumPy only)
- model-agnostic (black-box functions)
- deterministic by default (fixed RNG seed unless provided)

Expected callable signatures
----------------------------
decision_fn(X, theta) -> array-like of shape (n,)
    Returns a hard decision per sample (0/1, False/True).

prob_fn(X, theta) -> array-like of shape (n,)
    Returns a probability-like score per sample (float).

eps_sampler(...) -> theta_perturbed
    Returns a perturbed theta used to probe decision stability (DS).
    The sampler can have different signatures; we attempt to call it in a
    flexible way (see _call_eps_sampler).

X is expected to be array-like of shape (n_samples, n_features).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np


ArrayLike = Union[np.ndarray, Sequence[float], Sequence[Sequence[float]]]


def _as_2d_float(X: ArrayLike) -> np.ndarray:
    """Convert X to a 2D float numpy array."""
    x = np.asarray(X, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if x.ndim != 2:
        raise ValueError(f"X must be 1D or 2D; got shape {x.shape}")
    return x


def _to_1d(a: Any, n: int, dtype=float) -> np.ndarray:
    """
    Convert a model output to a 1D array of length n.

    Accepts scalar, (n,), (n,1), (1,n).
    """
    arr = np.asarray(a)
    if arr.ndim == 0:
        arr = np.full((n,), arr, dtype=dtype)
    else:
        arr = arr.astype(dtype, copy=False)
        if arr.ndim == 2:
            if arr.shape == (n, 1):
                arr = arr[:, 0]
            elif arr.shape == (1, n):
                arr = arr[0, :]
        if arr.ndim != 1:
            raise ValueError(f"Output must be 1D (or scalar); got shape {arr.shape}")
        if arr.shape[0] != n:
            raise ValueError(f"Output length mismatch: expected {n}, got {arr.shape[0]}")
    return arr


def _as_label(y: Any, n: int) -> np.ndarray:
    """Convert output to boolean labels of shape (n,)."""
    yy = _to_1d(y, n, dtype=float)
    # Accept typical 0/1 or any numeric -> bool
    return (yy > 0.5)


def _call_eps_sampler(
    eps_sampler: Callable[..., Any],
    theta: Any,
    rng: np.random.Generator,
) -> Any:
    """
    Call eps_sampler in a flexible way.

    Supported call patterns (first that works wins):
    - eps_sampler(theta, rng)
    - eps_sampler(theta)
    - eps_sampler(rng)
    - eps_sampler()
    """
    # Try (theta, rng)
    try:
        return eps_sampler(theta, rng)
    except TypeError:
        pass

    # Try (theta,)
    try:
        return eps_sampler(theta)
    except TypeError:
        pass

    # Try (rng,)
    try:
        return eps_sampler(rng)
    except TypeError:
        pass

    # Try ()
    return eps_sampler()


def compute_ds(
    decision_fn: Callable[[np.ndarray, Any], Any],
    X: ArrayLike,
    theta: Any,
    eps_sampler: Callable[..., Any],
    M: int,
    *,
    seed: int = 0,
) -> np.ndarray:
    """
    Decision Stability (DS) per sample.

    DS(x) = 1 - P( yhat(x, theta + eps) != yhat(x, theta) )

    Implementation:
    - sample M perturbations via eps_sampler -> theta_perturbed
    - evaluate decision_fn(X, theta_perturbed)
    - DS is 1 - mismatch_rate

    Parameters
    ----------
    decision_fn:
        Callable(X, theta) -> 0/1 decisions (or booleans).
    X:
        Features (n_samples, n_features).
    theta:
        Decision parameters (cuts, thresholds, etc.).
    eps_sampler:
        Callable producing perturbed theta.
    M:
        Number of perturbation samples.
    seed:
        RNG seed used for determinism.

    Returns
    -------
    ds : np.ndarray of shape (n_samples,)
    """
    if M <= 0:
        raise ValueError("M must be >= 1")

    x = _as_2d_float(X)
    n = x.shape[0]

    rng = np.random.default_rng(seed)

    y0 = _as_label(decision_fn(x, theta), n)
    mismatches = np.zeros(n, dtype=float)

    for _ in range(M):
        theta_p = _call_eps_sampler(eps_sampler, theta, rng)
        yk = _as_label(decision_fn(x, theta_p), n)
        mismatches += (yk != y0)

    ds = 1.0 - (mismatches / float(M))
    return ds


def compute_mi(
    prob_fn_list: Sequence[Callable[[np.ndarray, Any], Any]],
    X: ArrayLike,
    theta: Any,
) -> np.ndarray:
    """
    Model Inconsistency (MI) per sample.

    v0 definition:
        MI(x) = Var_i( p_i(x) )

    Notes:
    - If you only have hard decisions, you can pass functions that output 0/1;
      the variance is still meaningful (but coarser).
    - Using probability-like outputs typically yields smoother signals.

    Parameters
    ----------
    prob_fn_list:
        List of model scoring functions prob_fn(X, theta) -> floats.
    X:
        Features (n_samples, n_features).
    theta:
        Shared parameters (optional; pass None if not used).

    Returns
    -------
    mi : np.ndarray of shape (n_samples,)
    """
    if not prob_fn_list:
        raise ValueError("prob_fn_list must contain at least one model")

    x = _as_2d_float(X)
    n = x.shape[0]

    preds: List[np.ndarray] = []
    for fn in prob_fn_list:
        p = _to_1d(fn(x, theta), n, dtype=float)
        preds.append(p)

    stack = np.stack(preds, axis=0)  # (n_models, n_samples)
    mi = np.var(stack, axis=0, ddof=0)
    return mi


def compute_gf(
    prob_fn: Callable[[np.ndarray, Any], Any],
    X: ArrayLike,
    theta: Any,
    method: str = "spsa",
    K: int = 8,
    delta: float = 1e-2,
    *,
    seed: int = 0,
    clip_prob: bool = True,
) -> np.ndarray:
    """
    Gate Friction (GF): magnitude of sensitivity of prob_fn to small changes in X.

    v0 target:
        GF(x) = ||∇_x p(x)||

    Methods
    -------
    - "spsa" (default): black-box gradient norm estimate using random Rademacher directions.
    - "finite_diff": full coordinate finite differences (slow; useful for very low dimension).

    Parameters
    ----------
    prob_fn:
        Callable(X, theta) -> probability-like score per sample.
    X:
        Features (n_samples, n_features).
    theta:
        Parameters forwarded to prob_fn.
    method:
        "spsa" or "finite_diff".
    K:
        Number of random directions for SPSA (typical v0: 4..16).
    delta:
        Step size in feature space for finite differences / SPSA.
    seed:
        RNG seed for determinism (SPSA).
    clip_prob:
        If True, clamp prob_fn outputs into [0,1] before differencing.

    Returns
    -------
    gf : np.ndarray of shape (n_samples,)
    """
    if delta <= 0:
        raise ValueError("delta must be > 0")

    x = _as_2d_float(X)
    n, d = x.shape

    def _p(xx: np.ndarray) -> np.ndarray:
        p = _to_1d(prob_fn(xx, theta), n, dtype=float)
        if clip_prob:
            p = np.clip(p, 0.0, 1.0)
        return p

    if method.lower() == "finite_diff":
        # Full coordinate finite differences: O(d) model calls.
        gradsq = np.zeros(n, dtype=float)
        for j in range(d):
            ej = np.zeros((1, d), dtype=float)
            ej[0, j] = 1.0
            p_plus = _p(x + delta * ej)
            p_minus = _p(x - delta * ej)
            deriv = (p_plus - p_minus) / (2.0 * delta)
            gradsq += deriv * deriv
        return np.sqrt(gradsq)

    if method.lower() != "spsa":
        raise ValueError(f"Unknown method '{method}'. Use 'spsa' or 'finite_diff'.")

    if K <= 0:
        raise ValueError("K must be >= 1 for SPSA")

    rng = np.random.default_rng(seed)
    dsq_sum = np.zeros(n, dtype=float)

    # SPSA directional derivatives in random ±1 directions.
    for _ in range(K):
        v = rng.choice([-1.0, 1.0], size=(n, d), replace=True)
        p_plus = _p(x + delta * v)
        p_minus = _p(x - delta * v)
        ddir = (p_plus - p_minus) / (2.0 * delta)  # approx v·∇p
        dsq_sum += ddir * ddir

    gf = np.sqrt(dsq_sum / float(K))
    return gf


def _robust_minmax(x: np.ndarray, lo_q: float = 5.0, hi_q: float = 95.0) -> np.ndarray:
    """
    Robust min-max scaling to [0,1] using quantiles.
    Keeps outliers from dominating visualization.
    """
    finite = x[np.isfinite(x)]
    if finite.size == 0:
        return np.zeros_like(x)

    lo, hi = np.percentile(finite, [lo_q, hi_q])
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros_like(x)

    y = (x - lo) / (hi - lo)
    return np.clip(y, 0.0, 1.0)


def compute_pi(
    ds: ArrayLike,
    mi: ArrayLike,
    gf: ArrayLike,
    normalize: bool = True,
) -> np.ndarray:
    """
    Paradox Index (PI).

    v0 definition:
        PI_raw = (1 - DS) * MI * GF

    Practical v0 handling:
    - apply log1p to GF to prevent extreme scaling
    - optionally robust-scale PI into [0,1] for plotting (normalize=True)

    Parameters
    ----------
    ds, mi, gf:
        Arrays of shape (n_samples,).
    normalize:
        If True: returns PI normalized to [0,1] (robust quantile scaling).
        If False: returns PI_raw (with log1p(GF) applied).

    Returns
    -------
    pi : np.ndarray of shape (n_samples,)
    """
    ds_arr = np.asarray(ds, dtype=float).reshape(-1)
    mi_arr = np.asarray(mi, dtype=float).reshape(-1)
    gf_arr = np.asarray(gf, dtype=float).reshape(-1)

    if not (ds_arr.shape == mi_arr.shape == gf_arr.shape):
        raise ValueError(
            f"Shape mismatch: ds{ds_arr.shape}, mi{mi_arr.shape}, gf{gf_arr.shape}"
        )

    # Stabilize GF scaling
    gf_stable = np.log1p(np.maximum(gf_arr, 0.0))

    pi_raw = (1.0 - ds_arr) * mi_arr * gf_stable

    if normalize:
        return _robust_minmax(pi_raw)

    return pi_raw
